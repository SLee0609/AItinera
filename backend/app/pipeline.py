"""Runs the itinerary algorithm end to end and builds the API response."""

import asyncio
import logging
from collections import Counter
from collections.abc import Sequence
from itertools import pairwise

import httpx

from .algorithm.baseline import baseline_pairs, naive_travel_minutes
from .algorithm.clustering import partition_into_days
from .algorithm.ordering import TravelTimes, best_order, intra_day_pairs
from .config import Settings
from .errors import NotConfigured, PlanningTimeout
from .schemas import DayPlan, Itinerary, LatLng, Leg, Stop
from .services import gemini, places, routes
from .services.places import Attraction

log = logging.getLogger(__name__)

HTTP_TIMEOUT_S = 20.0


async def generate_itinerary(city: str, days: int, settings: Settings) -> Itinerary:
    if not settings.gemini_api_key or not settings.google_maps_server_key:
        raise NotConfigured()
    try:
        async with asyncio.timeout(settings.pipeline_timeout_s):
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
                return await _run(client, city, days, settings)
    except TimeoutError as err:
        raise PlanningTimeout() from err


async def _run(client: httpx.AsyncClient, query: str, days: int, s: Settings) -> Itinerary:
    key = s.google_maps_server_key

    # 1–2. City, candidate attractions, verified places.
    city = await places.resolve_city(client, key, query)
    candidates = await gemini.suggest_attractions(
        api_key=s.gemini_api_key,
        model=s.gemini_model,
        thinking_level=s.gemini_thinking_level,
        city=city.name,
        days=days,
        count=s.candidates_per_day * days,
    )
    attractions = await places.resolve_attractions(
        client,
        key,
        candidates,
        city,
        target=s.attractions_per_day * days,
        days=days,
        padding_km=s.city_padding_km,
    )
    points = [a.location for a in attractions]

    # 3. Partition into days by straight-line distance (no API calls).
    groups = partition_into_days(
        points, [a.visit_minutes for a in attractions], days, s.max_stops_per_day, s.balance_tolerance
    )

    # 4. Transit times for pairs within each day and for the naive baseline.
    departure = routes.departure_time(city.time_zone)
    pairs = intra_day_pairs(groups) | baseline_pairs(len(attractions), days)
    times = await routes.transit_times(client, key, points, pairs, departure)

    # 5. Best order within each day.
    orders = [best_order(g, times)[0] for g in groups]

    # 6. Route lines for the map (optional).
    polylines = (
        await routes.leg_polylines(client, key, points, orders, departure)
        if s.route_polylines
        else [[None] * max(len(o) - 1, 0) for o in orders]
    )

    log.info(
        "Planned %s for %d days: %d candidates, %d attractions, %d matrix elements",
        city.name,
        days,
        len(candidates),
        len(attractions),
        len(pairs),
    )
    return build_itinerary(city.name, attractions, orders, times, polylines, days)


def day_title(members: Sequence[Attraction]) -> str | None:
    """The one or two neighborhoods where the day spends the most time, such as "Montmartre & Le Marais"."""
    weights: Counter[str] = Counter()
    for a in members:
        if a.neighborhood:
            weights[a.neighborhood] += a.visit_minutes
    # Counter.most_common keeps first-seen order for ties.
    top = [name for name, _ in weights.most_common(2)]
    return " & ".join(top) or None


def build_itinerary(
    city: str,
    attractions: Sequence[Attraction],
    orders: Sequence[Sequence[int]],
    times: TravelTimes,
    polylines: Sequence[Sequence[str | None]],
    days: int,
) -> Itinerary:
    day_plans = []
    for n, (order, lines) in enumerate(zip(orders, polylines, strict=True), start=1):
        members = [attractions[i] for i in order]
        legs = [
            Leg(duration_minutes=round(times[(a, b)] / 60), polyline=line)
            for (a, b), line in zip(pairwise(order), lines, strict=True)
        ]
        day_plans.append(
            DayPlan(
                day=n,
                title=day_title(members),
                stops=[
                    Stop(
                        place_id=a.place_id,
                        name=a.name,
                        description=a.description,
                        visit_minutes=a.visit_minutes,
                        location=LatLng(lat=a.location.lat, lng=a.location.lng),
                    )
                    for a in members
                ],
                legs=legs,
                travel_minutes=sum(leg.duration_minutes for leg in legs),
            )
        )
    return Itinerary(
        city=city,
        day_plans=day_plans,
        optimized_travel_minutes=sum(d.travel_minutes for d in day_plans),
        naive_travel_minutes=naive_travel_minutes(len(attractions), days, times),
    )
