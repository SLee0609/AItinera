"""Step 4: transit travel times between the pairs the algorithm needs, and route lines for the map."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, time, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from ..algorithm.geo import Point, walking_estimate_s
from . import google_http

log = logging.getLogger(__name__)

MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
MATRIX_FIELDS = "originIndex,destinationIndex,duration,condition,status"
ROUTE_FIELDS = "routes.polyline.encodedPolyline"
# Routes API limit for TRANSIT route matrices.
MAX_TRANSIT_ELEMENTS = 100
DEPARTURE_HOUR = 10


def departure_time(tz: str, now: datetime | None = None) -> datetime:
    """The next weekday at 10:00 in the city's time zone, so transit schedules are typical."""
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    day = (now or datetime.now(UTC)).astimezone(zone).date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.combine(day, time(DEPARTURE_HOUR), tzinfo=zone)


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_duration(value: str) -> float:
    """Routes API durations look like "754s"."""
    return float(value.rstrip("s"))


def requests_by_origin(pairs: Iterable[tuple[int, int]]) -> list[tuple[int, list[int]]]:
    """One request per origin, with only the destinations it needs, so no self-pairs are billed."""
    by_origin: dict[int, list[int]] = defaultdict(list)
    for a, b in sorted(pairs):
        by_origin[a].append(b)
    out = []
    for origin, dests in sorted(by_origin.items()):
        for i in range(0, len(dests), MAX_TRANSIT_ELEMENTS):
            out.append((origin, dests[i : i + MAX_TRANSIT_ELEMENTS]))
    return out


async def transit_times(
    client: httpx.AsyncClient,
    api_key: str,
    points: Sequence[Point],
    pairs: Iterable[tuple[int, int]],
    departure: datetime,
    concurrency: int = 8,
) -> dict[tuple[int, int], float]:
    """Directed transit time in seconds for each pair. Pairs without a transit route get a walking estimate."""
    pairs = set(pairs)
    semaphore = asyncio.Semaphore(concurrency)
    times: dict[tuple[int, int], float] = {}

    async def fetch(origin: int, dests: list[int]) -> None:
        body = {
            "origins": [{"waypoint": {"location": google_http.lat_lng(points[origin])}}],
            "destinations": [{"waypoint": {"location": google_http.lat_lng(points[d])}} for d in dests],
            "travelMode": "TRANSIT",
            "departureTime": rfc3339(departure),
        }
        async with semaphore:
            elements = await google_http.post(client, MATRIX_URL, api_key, MATRIX_FIELDS, body)
        for el in elements or []:
            # Proto3 JSON leaves out zero values, so a missing index means 0.
            dest = dests[el.get("destinationIndex", 0)]
            if el.get("condition") == "ROUTE_EXISTS" and not el.get("status", {}).get("code") and "duration" in el:
                times[(origin, dest)] = parse_duration(el["duration"])

    await asyncio.gather(*(fetch(o, d) for o, d in requests_by_origin(pairs)))

    missing = pairs - times.keys()
    for a, b in missing:
        times[(a, b)] = walking_estimate_s(points[a], points[b])
    log.info("Route matrix: %d elements, %d without a transit route (walking estimate)", len(pairs), len(missing))
    return times


async def leg_polyline(
    client: httpx.AsyncClient, api_key: str, a: Point, b: Point, departure: datetime
) -> str | None:
    body = {
        "origin": {"location": google_http.lat_lng(a)},
        "destination": {"location": google_http.lat_lng(b)},
        "travelMode": "TRANSIT",
        "departureTime": rfc3339(departure),
    }
    try:
        data = await google_http.post(client, ROUTES_URL, api_key, ROUTE_FIELDS, body)
    except Exception as err:  # a missing line only falls back to a straight segment on the map
        log.warning("computeRoutes failed: %r", err)
        return None
    routes = data.get("routes") or []
    return routes[0].get("polyline", {}).get("encodedPolyline") if routes else None


async def leg_polylines(
    client: httpx.AsyncClient,
    api_key: str,
    points: Sequence[Point],
    orders: Sequence[Sequence[int]],
    departure: datetime,
    concurrency: int = 8,
) -> list[list[str | None]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(a: int, b: int) -> str | None:
        async with semaphore:
            return await leg_polyline(client, api_key, points[a], points[b], departure)

    legs = [list(pairwise(order)) for order in orders]
    flat = await asyncio.gather(*(one(a, b) for day in legs for a, b in day))
    out, i = [], 0
    for day in legs:
        out.append(list(flat[i : i + len(day)]))
        i += len(day)
    return out
