import json

import httpx
import pytest
import respx

from app.errors import ItineraryNotFound, StorageError
from app.services.supabase import Store

BASE = "https://proj.supabase.co"
REST = f"{BASE}/rest/v1"


@pytest.fixture
async def store():
    async with httpx.AsyncClient() as client:
        yield Store(client, BASE, "sb_secret_x")


@respx.mock
async def test_insert_itinerary_sends_row_with_secret_key(store):
    route = respx.post(f"{REST}/itineraries").mock(return_value=httpx.Response(201))
    await store.insert_itinerary("abcdefghijkl", "paris", 3, {"city": "Paris, France", "dayPlans": []}, None)

    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_secret_x"
    assert request.headers["Prefer"] == "return=minimal"
    assert json.loads(request.content) == {
        "id": "abcdefghijkl",
        "query": "paris",
        "city": "Paris, France",
        "days": 3,
        "data": {"city": "Paris, France", "dayPlans": []},
        "created_by": None,
    }


@respx.mock
async def test_get_itinerary(store):
    route = respx.get(f"{REST}/itineraries").mock(return_value=httpx.Response(200, json=[{"data": {"city": "X"}}]))
    assert await store.get_itinerary("abcdefghijkl") == {"city": "X"}
    assert route.calls.last.request.url.params["id"] == "eq.abcdefghijkl"

    route.mock(return_value=httpx.Response(200, json=[]))
    assert await store.get_itinerary("abcdefghijkl") is None


@respx.mock
async def test_list_saved_flattens_rows_and_filters_by_user(store):
    rows = [
        {
            "saved_at": "2026-10-16T12:00:00+00:00",
            "itinerary": {
                "id": "abcdefghijkl",
                "city": "Paris",
                "days": 3,
                "stops": 12,
                "optimized": 185,
                "naive": 290,
            },
        },
        {"saved_at": "2026-10-15T12:00:00+00:00", "itinerary": None},
    ]
    route = respx.get(f"{REST}/saved_itineraries").mock(return_value=httpx.Response(200, json=rows))
    assert await store.list_saved("user-1") == [
        {
            "id": "abcdefghijkl",
            "city": "Paris",
            "days": 3,
            "stop_count": 12,
            "saved_at": "2026-10-16T12:00:00+00:00",
            "optimized_travel_minutes": 185,
            "naive_travel_minutes": 290,
        }
    ]
    params = route.calls.last.request.url.params
    assert params["user_id"] == "eq.user-1"
    assert params["order"] == "saved_at.desc"
    assert "stops:stop_count" in params["select"]


@respx.mock
async def test_save_is_idempotent_and_unsave_filters_by_user(store):
    save = respx.post(f"{REST}/saved_itineraries").mock(return_value=httpx.Response(201))
    await store.save("user-1", "abcdefghijkl")
    assert "resolution=ignore-duplicates" in save.calls.last.request.headers["Prefer"]

    unsave = respx.delete(f"{REST}/saved_itineraries").mock(return_value=httpx.Response(204))
    await store.unsave("user-1", "abcdefghijkl")
    params = unsave.calls.last.request.url.params
    assert (params["user_id"], params["itinerary_id"]) == ("eq.user-1", "eq.abcdefghijkl")


@respx.mock
async def test_is_saved(store):
    respx.get(f"{REST}/saved_itineraries").mock(
        side_effect=[httpx.Response(200, json=[{"itinerary_id": "x"}]), httpx.Response(200, json=[])]
    )
    assert await store.is_saved("user-1", "abcdefghijkl") is True
    assert await store.is_saved("user-1", "abcdefghijkl") is False


@respx.mock
async def test_saving_a_missing_itinerary_is_not_found(store):
    respx.post(f"{REST}/saved_itineraries").mock(
        return_value=httpx.Response(409, json={"code": "23503", "message": "violates foreign key constraint"})
    )
    with pytest.raises(ItineraryNotFound):
        await store.save("user-1", "abcdefghijkl")


@respx.mock
async def test_http_and_network_failures_become_storage_errors(store):
    respx.get(f"{REST}/itineraries").mock(
        side_effect=[httpx.Response(401, json={"message": "Invalid API key"}), httpx.ConnectError("down")]
    )
    with pytest.raises(StorageError) as exc:
        await store.get_itinerary("abcdefghijkl")
    assert "401" in exc.value.detail
    with pytest.raises(StorageError) as exc:
        await store.get_itinerary("abcdefghijkl")
    assert "ConnectError" in exc.value.detail


@respx.mock
async def test_delete_user_calls_the_auth_admin_api(store):
    route = respx.delete(f"{BASE}/auth/v1/admin/users/user-1").mock(return_value=httpx.Response(200, json={}))
    await store.delete_user("user-1")
    headers = route.calls.last.request.headers
    assert headers["apikey"] == "sb_secret_x"
    assert headers["Authorization"] == "Bearer sb_secret_x"


@respx.mock
async def test_deleting_a_missing_user_succeeds_and_other_failures_raise(store):
    route = respx.delete(f"{BASE}/auth/v1/admin/users/user-1")
    route.mock(return_value=httpx.Response(404, json={"msg": "User not found"}))
    await store.delete_user("user-1")

    route.mock(return_value=httpx.Response(403, json={"msg": "not allowed"}))
    with pytest.raises(StorageError) as exc:
        await store.delete_user("user-1")
    assert "403" in exc.value.detail
