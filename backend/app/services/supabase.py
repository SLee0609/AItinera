"""Stored and saved itineraries in Supabase, through its REST API (PostgREST), and account deletion.

Uses the project's secret key, which bypasses row level security, so every query here must filter by the
signed-in user where it matters. IDs are validated by the caller before they reach a filter.
"""

import logging
from typing import Any

import httpx

from ..errors import ItineraryNotFound, StorageError

log = logging.getLogger(__name__)

# Postgres foreign key violation: the itinerary being saved doesn't exist.
FOREIGN_KEY_VIOLATION = "23503"

SAVED_SELECT = (
    "saved_at,itinerary:itineraries(id,city,days,"
    "optimized:data->optimizedTravelMinutes,naive:data->naiveTravelMinutes)"
)


class Store:
    def __init__(self, client: httpx.AsyncClient, base_url: str, secret_key: str):
        self._client = client
        self._rest = f"{base_url}/rest/v1"
        self._auth_admin = f"{base_url}/auth/v1/admin/users"
        self._headers = {"apikey": secret_key}
        # The Auth admin API also wants the key as a bearer token, as supabase-js sends it.
        self._admin_headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}

    async def insert_itinerary(
        self, itinerary_id: str, query: str, days: int, data: dict[str, Any], created_by: str | None
    ) -> None:
        row = {
            "id": itinerary_id,
            "query": query,
            "city": data["city"],
            "days": days,
            "data": data,
            "created_by": created_by,
        }
        await self._request("POST", "itineraries", json=row, prefer="return=minimal")

    async def get_itinerary(self, itinerary_id: str) -> dict[str, Any] | None:
        rows = await self._request("GET", "itineraries", params={"id": f"eq.{itinerary_id}", "select": "data"})
        return rows[0]["data"] if rows else None

    async def list_saved(self, user_id: str) -> list[dict[str, Any]]:
        """The user's saved itineraries, newest first, flattened to SavedItinerarySummary fields."""
        rows = await self._request(
            "GET",
            "saved_itineraries",
            params={"user_id": f"eq.{user_id}", "select": SAVED_SELECT, "order": "saved_at.desc"},
        )
        return [
            {
                "id": r["itinerary"]["id"],
                "city": r["itinerary"]["city"],
                "days": r["itinerary"]["days"],
                "saved_at": r["saved_at"],
                "optimized_travel_minutes": r["itinerary"]["optimized"],
                "naive_travel_minutes": r["itinerary"]["naive"],
            }
            for r in rows
            if r.get("itinerary")
        ]

    async def is_saved(self, user_id: str, itinerary_id: str) -> bool:
        rows = await self._request(
            "GET",
            "saved_itineraries",
            params={"user_id": f"eq.{user_id}", "itinerary_id": f"eq.{itinerary_id}", "select": "itinerary_id"},
        )
        return bool(rows)

    async def save(self, user_id: str, itinerary_id: str) -> None:
        """Idempotent: saving an itinerary twice keeps the first save."""
        await self._request(
            "POST",
            "saved_itineraries",
            json={"user_id": user_id, "itinerary_id": itinerary_id},
            prefer="resolution=ignore-duplicates,return=minimal",
        )

    async def unsave(self, user_id: str, itinerary_id: str) -> None:
        await self._request(
            "DELETE",
            "saved_itineraries",
            params={"user_id": f"eq.{user_id}", "itinerary_id": f"eq.{itinerary_id}"},
            prefer="return=minimal",
        )

    async def delete_user(self, user_id: str) -> None:
        """Deletes the Supabase Auth user. The database cascades to their profile and saved list; itineraries they
        generated stay as anonymous share links (`created_by` is set to null), so other users' saves keep working.
        Deleting a user who no longer exists counts as success."""
        url = f"{self._auth_admin}/{user_id}"
        try:
            response = await self._client.delete(url, headers=self._admin_headers)
        except httpx.HTTPError as err:
            raise StorageError(f"DELETE auth user: {err!r}") from err
        if response.status_code >= 400 and response.status_code != 404:
            raise StorageError(f"DELETE auth user returned {response.status_code}: {_json_or_text(response)}")

    async def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        url = f"{self._rest}/{table}"
        try:
            response = await self._client.request(method, url, params=params, json=json, headers=headers)
        except httpx.HTTPError as err:
            raise StorageError(f"{method} {table}: {err!r}") from err

        if response.status_code >= 400:
            body = _json_or_text(response)
            if isinstance(body, dict) and body.get("code") == FOREIGN_KEY_VIOLATION:
                raise ItineraryNotFound()
            raise StorageError(f"{method} {table} returned {response.status_code}: {body}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()


def _json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text[:500]
