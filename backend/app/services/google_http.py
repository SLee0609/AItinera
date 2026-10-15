"""Shared helpers for Google Maps Platform REST calls (Places API (New), Routes API)."""

import logging
from typing import Any

import httpx

from ..errors import UpstreamError

log = logging.getLogger(__name__)


def _headers(api_key: str, field_mask: str) -> dict[str, str]:
    return {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": field_mask}


async def post(client: httpx.AsyncClient, url: str, api_key: str, field_mask: str, body: dict[str, Any]) -> Any:
    try:
        response = await client.post(url, json=body, headers=_headers(api_key, field_mask))
    except httpx.HTTPError as err:
        raise UpstreamError(f"POST {url}: {err!r}") from err
    return _parse(response)


async def get(client: httpx.AsyncClient, url: str, api_key: str, field_mask: str) -> Any | None:
    """Returns None when the resource doesn't exist (404)."""
    try:
        response = await client.get(url, headers=_headers(api_key, field_mask))
    except httpx.HTTPError as err:
        raise UpstreamError(f"GET {url}: {err!r}") from err
    if response.status_code == 404:
        return None
    return _parse(response)


def _parse(response: httpx.Response) -> Any:
    if response.status_code >= 400:
        log.error(
            "Google API %s %s returned %s: %s",
            response.request.method,
            response.request.url.path,
            response.status_code,
            response.text[:500],
        )
        raise UpstreamError(f"{response.request.url.path}: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as err:
        raise UpstreamError(f"{response.request.url.path}: invalid JSON") from err


def lat_lng(point: Any) -> dict[str, dict[str, float]]:
    """`{"latLng": {...}}` location object used by the Routes API."""
    return {"latLng": {"latitude": point.lat, "longitude": point.lng}}
