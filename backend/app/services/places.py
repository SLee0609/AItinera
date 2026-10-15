"""Step 2: resolve the city and match each candidate attraction to a real place.

Each lookup is a Text Search that returns IDs only (free), then a Place Details request for the
chosen ID with the cheapest field set that covers what we need.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ..algorithm.geo import Point, Viewport, around
from ..errors import CityNotFound, NotEnoughAttractions
from . import google_http
from .gemini import Candidate

log = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Place Details Pro (timeZone is a Pro field); billed once per request, for the city.
CITY_FIELDS = "id,formattedAddress,location,viewport,types,timeZone"
# Place Details Essentials.
ATTRACTION_FIELDS = "id,location,types"

CITY_TYPES = {
    "locality",
    "postal_town",
    "administrative_area_level_1",
    "administrative_area_level_2",
    "administrative_area_level_3",
    "colloquial_area",
}
# A match with one of these types is a region, not an attraction.
REGION_TYPES = CITY_TYPES | {"country", "postal_code"}

DETAILS_TRIES_PER_CANDIDATE = 2
DEFAULT_CITY_RADIUS_KM = 15.0


@dataclass(frozen=True)
class CityPlace:
    name: str
    center: Point
    viewport: Viewport
    time_zone: str


@dataclass(frozen=True)
class Attraction:
    place_id: str
    name: str
    description: str
    visit_minutes: int
    neighborhood: str
    location: Point


def _point(raw: dict[str, Any]) -> Point:
    return Point(raw["latitude"], raw["longitude"])


def _rectangle(v: Viewport) -> dict[str, Any]:
    return {
        "low": {"latitude": v.low.lat, "longitude": v.low.lng},
        "high": {"latitude": v.high.lat, "longitude": v.high.lng},
    }


async def search_ids(
    client: httpx.AsyncClient, api_key: str, query: str, page_size: int, bias: Viewport | None = None
) -> list[str]:
    body: dict[str, Any] = {"textQuery": query, "pageSize": page_size}
    if bias is not None:
        body["locationBias"] = {"rectangle": _rectangle(bias)}
    data = await google_http.post(client, SEARCH_URL, api_key, "places.id", body)
    return [p["id"] for p in data.get("places", []) if p.get("id")]


async def place_details(client: httpx.AsyncClient, api_key: str, place_id: str, fields: str) -> dict | None:
    return await google_http.get(client, DETAILS_URL.format(place_id=place_id), api_key, fields)


async def resolve_city(client: httpx.AsyncClient, api_key: str, query: str) -> CityPlace:
    ids = await search_ids(client, api_key, query, page_size=1)
    details = await place_details(client, api_key, ids[0], CITY_FIELDS) if ids else None
    if not details or not CITY_TYPES & set(details.get("types", [])) or "location" not in details:
        raise CityNotFound(query)
    center = _point(details["location"])
    viewport = (
        Viewport(_point(details["viewport"]["low"]), _point(details["viewport"]["high"]))
        if "viewport" in details
        else around(center, DEFAULT_CITY_RADIUS_KM)
    )
    return CityPlace(
        name=details.get("formattedAddress") or query,
        center=center,
        viewport=viewport,
        time_zone=details.get("timeZone", {}).get("id", "UTC"),
    )


def is_confident_match(details: dict, area: Viewport) -> bool:
    if "location" not in details or REGION_TYPES & set(details.get("types", [])):
        return False
    return area.contains(_point(details["location"]))


async def resolve_attraction(
    client: httpx.AsyncClient, api_key: str, candidate: Candidate, city: CityPlace, area: Viewport
) -> Attraction | None:
    ids = await search_ids(client, api_key, f"{candidate.name}, {city.name}", page_size=3, bias=city.viewport)
    for place_id in ids[:DETAILS_TRIES_PER_CANDIDATE]:
        details = await place_details(client, api_key, place_id, ATTRACTION_FIELDS)
        if details and is_confident_match(details, area):
            return Attraction(
                place_id=details.get("id", place_id),
                name=candidate.name,
                description=candidate.description,
                visit_minutes=candidate.visit_minutes,
                neighborhood=candidate.neighborhood,
                location=_point(details["location"]),
            )
    log.info("No confident match for %r in %s", candidate.name, city.name)
    return None


async def resolve_attractions(
    client: httpx.AsyncClient,
    api_key: str,
    candidates: list[Candidate],
    city: CityPlace,
    *,
    target: int,
    days: int,
    padding_km: float,
    concurrency: int = 8,
) -> list[Attraction]:
    """Resolves candidates in priority order until `target` unique places are verified.

    Works in waves: the first wave covers the top `target` candidates, and each later wave covers
    only as many spares as there are rejections, so spares are looked up (and billed) only when needed.
    """
    area = city.viewport.padded(padding_km)
    semaphore = asyncio.Semaphore(concurrency)
    results: list[Attraction | None] = []

    async def one(c: Candidate) -> Attraction | None:
        async with semaphore:
            return await resolve_attraction(client, api_key, c, city, area)

    def kept() -> list[Attraction]:
        seen: set[str] = set()
        out = []
        for a in results:
            if a is not None and a.place_id not in seen:
                seen.add(a.place_id)
                out.append(a)
        return out

    while len(kept()) < target and len(results) < len(candidates):
        need = target - len(kept())
        wave = candidates[len(results) : len(results) + need]
        results.extend(await asyncio.gather(*(one(c) for c in wave)))

    attractions = kept()[:target]
    if len(attractions) < days:
        raise NotEnoughAttractions(city.name, days)
    return attractions
