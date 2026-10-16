from itertools import pairwise

import pytest
from fastapi.testclient import TestClient

from app import main, pipeline
from app.algorithm.geo import walking_estimate_s
from app.auth import current_user, optional_user
from app.config import Settings, get_settings
from app.errors import (
    CityNotFound,
    ItineraryNotFound,
    NotEnoughAttractions,
    NotSignedIn,
    PlanningTimeout,
    StorageError,
    UpstreamError,
)
from app.services import gemini, places, routes

SETTINGS = Settings(gemini_api_key="g", google_maps_server_key="m", _env_file=None)


@pytest.fixture
def client():
    main.app.dependency_overrides[get_settings] = lambda: SETTINGS
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def fake_google(monkeypatch, paris_city, paris_attractions):
    """Replaces every Google call with the Paris sample. Transit time = walking estimate."""
    calls = {}

    async def resolve_city(_client, _key, query):
        calls["city"] = query
        return paris_city

    async def suggest_attractions(**kwargs):
        calls["count"] = kwargs["count"]
        return []

    async def resolve_attractions(_client, _key, _candidates, _city, *, target, days, padding_km):
        calls["target"] = target
        return paris_attractions[:target]

    async def transit_times(_client, _key, points, pairs, _departure):
        calls["pairs"] = set(pairs)
        return {(a, b): walking_estimate_s(points[a], points[b]) for a, b in pairs}

    async def leg_polylines(_client, _key, _points, orders, _departure):
        return [[f"line{a}-{b}" for a, b in pairwise(o)] for o in orders]

    monkeypatch.setattr(places, "resolve_city", resolve_city)
    monkeypatch.setattr(gemini, "suggest_attractions", suggest_attractions)
    monkeypatch.setattr(places, "resolve_attractions", resolve_attractions)
    monkeypatch.setattr(routes, "transit_times", transit_times)
    monkeypatch.setattr(routes, "leg_polylines", leg_polylines)
    return calls


class FakeStore:
    """In-memory stand-in for app.services.supabase.Store."""

    def __init__(self):
        self.itineraries = {}
        self.saved = {}  # (user_id, itinerary_id) -> saved_at
        self.fail_inserts = False

    async def insert_itinerary(self, itinerary_id, query, days, data, created_by):
        if self.fail_inserts:
            raise StorageError("down")
        self.itineraries[itinerary_id] = {"query": query, "days": days, "data": data, "created_by": created_by}

    async def get_itinerary(self, itinerary_id):
        row = self.itineraries.get(itinerary_id)
        return row and row["data"]

    async def list_saved(self, user_id):
        rows = [(at, iid) for (uid, iid), at in self.saved.items() if uid == user_id]
        return [
            {
                "id": iid,
                "city": self.itineraries[iid]["data"]["city"],
                "days": self.itineraries[iid]["days"],
                "stop_count": sum(len(d["stops"]) for d in self.itineraries[iid]["data"]["dayPlans"]),
                "saved_at": at,
                "optimized_travel_minutes": self.itineraries[iid]["data"]["optimizedTravelMinutes"],
                "naive_travel_minutes": self.itineraries[iid]["data"]["naiveTravelMinutes"],
            }
            for at, iid in sorted(rows, reverse=True)
        ]

    async def is_saved(self, user_id, itinerary_id):
        return (user_id, itinerary_id) in self.saved

    async def save(self, user_id, itinerary_id):
        if itinerary_id not in self.itineraries:
            raise ItineraryNotFound()
        self.saved.setdefault((user_id, itinerary_id), f"2026-10-16T12:00:{len(self.saved):02d}+00:00")

    async def unsave(self, user_id, itinerary_id):
        self.saved.pop((user_id, itinerary_id), None)

    async def delete_user(self, user_id):
        # Mirrors the database: the user's saves cascade, their itineraries lose `created_by`.
        self.saved = {k: v for k, v in self.saved.items() if k[0] != user_id}
        for row in self.itineraries.values():
            if row["created_by"] == user_id:
                row["created_by"] = None


@pytest.fixture
def store(client):
    fake = FakeStore()
    main.app.dependency_overrides[main.get_store] = lambda: fake
    return fake


@pytest.fixture
def sign_in(client):
    """Call with a user ID to act as that user; None acts as a guest."""

    def act_as(user_id):
        def required():
            if user_id is None:
                raise NotSignedIn()
            return user_id

        main.app.dependency_overrides[current_user] = required
        main.app.dependency_overrides[optional_user] = lambda: user_id

    act_as(None)
    return act_as


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_itinerary_shape_matches_frontend_types(client, fake_google, store, sign_in):
    response = client.post("/api/itinerary", json={"city": "  Paris ", "days": 3})
    assert response.status_code == 200, response.text
    body = response.json()

    # Field names from frontend/src/types.ts.
    assert set(body) == {"id", "city", "travelMode", "dayPlans", "optimizedTravelMinutes", "naiveTravelMinutes"}
    assert body["travelMode"] == "TRANSIT" and body["city"] == "Paris, France"
    for day in body["dayPlans"]:
        assert set(day) <= {"day", "title", "stops", "legs", "travelMinutes"}
        assert len(day["legs"]) == len(day["stops"]) - 1
        assert day["travelMinutes"] == sum(leg["durationMinutes"] for leg in day["legs"])
        for stop in day["stops"]:
            assert set(stop) == {"placeId", "name", "description", "visitMinutes", "location"}
            assert set(stop["location"]) == {"lat", "lng"}
        for leg in day["legs"]:
            assert set(leg) == {"durationMinutes", "polyline"}
    assert [d["day"] for d in body["dayPlans"]] == [1, 2, 3]
    assert body["optimizedTravelMinutes"] == sum(d["travelMinutes"] for d in body["dayPlans"])

    # Every stop appears once; day 1 starts from the top-ranked attraction's group.
    names = [s["name"] for d in body["dayPlans"] for s in d["stops"]]
    assert len(names) == len(set(names)) == 12
    assert "Arc de Triomphe" in [s["name"] for s in body["dayPlans"][0]["stops"]]

    assert (fake_google["city"], fake_google["count"], fake_google["target"]) == ("Paris", 18, 12)


def test_only_needed_pairs_are_requested(client, fake_google):
    body = client.post("/api/itinerary", json={"city": "Paris", "days": 3}).json()
    intra = sum(len(d["stops"]) * (len(d["stops"]) - 1) for d in body["dayPlans"])
    baseline = 12 - 3  # consecutive pairs in 3 naive days of 4 stops
    assert intra <= len(fake_google["pairs"]) <= intra + baseline
    assert len(fake_google["pairs"]) < 12 * 11  # never the full matrix


def test_falls_back_to_naive_plan_when_it_travels_less(client, fake_google, monkeypatch, paris_attractions):
    def names_by_day(body):
        return [[s["name"] for s in d["stops"]] for d in body["dayPlans"]]

    naive = [[a.name for a in paris_attractions[i : i + 4]] for i in (0, 4, 8)]
    # With walking-estimate times the optimized plan differs from the naive one...
    assert names_by_day(client.post("/api/itinerary", json={"city": "Paris", "days": 3}).json()) != naive

    # ...but when the naive plan's legs are fast and every other leg is slow, the naive plan wins.
    naive_pairs = {(i, i + 1) for start in (0, 4, 8) for i in range(start, start + 3)}

    async def transit_times(_client, _key, _points, pairs, _departure):
        return {p: 60.0 if p in naive_pairs else 1800.0 for p in pairs}

    monkeypatch.setattr(routes, "transit_times", transit_times)
    body = client.post("/api/itinerary", json={"city": "Paris", "days": 3}).json()

    assert names_by_day(body) == naive
    assert body["optimizedTravelMinutes"] == body["naiveTravelMinutes"] == 9
    # Route lines are fetched for the plan that is returned.
    assert [leg["polyline"] for leg in body["dayPlans"][0]["legs"]] == ["line0-1", "line1-2", "line2-3"]


def test_polylines_can_be_disabled(client, fake_google):
    main.app.dependency_overrides[get_settings] = lambda: SETTINGS.model_copy(update={"route_polylines": False})
    body = client.post("/api/itinerary", json={"city": "Paris", "days": 2}).json()
    assert all("polyline" not in leg for d in body["dayPlans"] for leg in d["legs"])


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"city": "Paris", "days": 0}, "Trip length must be between 1 and 7 days."),
        ({"city": "Paris", "days": 8}, "Trip length must be between 1 and 7 days."),
        ({"city": "Paris", "days": "3"}, "Trip length must be between 1 and 7 days."),
        ({"city": "   ", "days": 3}, "Enter a city name of up to 100 characters."),
        ({"city": "x" * 101, "days": 3}, "Enter a city name of up to 100 characters."),
        ({}, "Trip length must be between 1 and 7 days."),
    ],
)
def test_validation_errors(client, payload, message):
    response = client.post("/api/itinerary", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": message}


@pytest.mark.parametrize(
    "error, status",
    [
        (CityNotFound("Atlantis"), 404),
        (NotEnoughAttractions("Smalltown", 5), 422),
        (UpstreamError("boom"), 502),
        (PlanningTimeout(), 504),
        (RuntimeError("bug"), 500),
    ],
)
def test_errors_return_detail_strings(monkeypatch, error, status):
    async def fail(*_args):
        raise error

    monkeypatch.setattr(main, "generate_itinerary", fail)
    main.app.dependency_overrides[get_settings] = lambda: SETTINGS
    response = TestClient(main.app, raise_server_exceptions=False).post(
        "/api/itinerary", json={"city": "Atlantis", "days": 5}
    )
    main.app.dependency_overrides.clear()
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)


def test_missing_keys_return_500(client):
    main.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    response = client.post("/api/itinerary", json={"city": "Paris", "days": 2})
    assert response.status_code == 500
    assert "isn't configured" in response.json()["detail"]


async def test_pipeline_timeout(monkeypatch):
    import asyncio

    async def slow(*_args, **_kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr(places, "resolve_city", slow)
    settings = SETTINGS.model_copy(update={"pipeline_timeout_s": 0.05})
    with pytest.raises(PlanningTimeout):
        await pipeline.generate_itinerary("Paris", 2, settings)


def test_day_title(paris_attractions):
    marais = [a for a in paris_attractions if a.neighborhood in {"Le Marais", "Île de la Cité"}]
    assert pipeline.day_title(marais) == "Le Marais & Île de la Cité"
    assert pipeline.day_title([]) is None


def test_generated_itineraries_are_stored_and_served_by_id(client, fake_google, store, sign_in):
    created = client.post("/api/itinerary", json={"city": " Paris ", "days": 3}).json()
    itinerary_id = created["id"]
    assert main.ITINERARY_ID.fullmatch(itinerary_id)

    row = store.itineraries[itinerary_id]
    assert (row["query"], row["days"], row["created_by"]) == ("Paris", 3, None)
    assert "id" not in row["data"]

    response = client.get(f"/api/itinerary/{itinerary_id}")
    assert response.status_code == 200
    assert response.json() == created


def test_signed_in_generations_record_the_creator(client, fake_google, store, sign_in):
    sign_in("user-1")
    itinerary_id = client.post("/api/itinerary", json={"city": "Paris", "days": 1}).json()["id"]
    assert store.itineraries[itinerary_id]["created_by"] == "user-1"


def test_storage_failure_still_returns_the_itinerary(client, fake_google, store, sign_in):
    store.fail_inserts = True
    response = client.post("/api/itinerary", json={"city": "Paris", "days": 2})
    assert response.status_code == 200
    assert "id" not in response.json()


def test_generation_works_without_supabase(client, fake_google):
    response = client.post("/api/itinerary", json={"city": "Paris", "days": 2})
    assert response.status_code == 200
    assert "id" not in response.json()


@pytest.mark.parametrize("itinerary_id", ["abcdefghijkl", "short", "abc,def.ghij", "a" * 13])
def test_unknown_itinerary_ids_are_not_found(client, store, itinerary_id):
    response = client.get(f"/api/itinerary/{itinerary_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": ItineraryNotFound().message}


def test_saved_endpoints_require_sign_in(client, store, sign_in):
    for method, path in [
        ("GET", "/api/saved"),
        ("GET", "/api/saved/abcdefghijkl"),
        ("PUT", "/api/saved/abcdefghijkl"),
        ("DELETE", "/api/saved/abcdefghijkl"),
        ("DELETE", "/api/account"),
    ]:
        response = client.request(method, path)
        assert response.status_code == 401, path
        assert response.json() == {"detail": "Sign in to save itineraries."}


def test_save_list_and_unsave(client, fake_google, store, sign_in):
    first = client.post("/api/itinerary", json={"city": "Paris", "days": 2}).json()
    second = client.post("/api/itinerary", json={"city": "Paris", "days": 3}).json()
    sign_in("user-1")

    assert client.get(f"/api/saved/{first['id']}").json() == {"saved": False}
    assert client.put(f"/api/saved/{first['id']}").json() == {"saved": True}
    assert client.put(f"/api/saved/{first['id']}").json() == {"saved": True}  # idempotent
    assert client.put(f"/api/saved/{second['id']}").json() == {"saved": True}
    assert client.get(f"/api/saved/{first['id']}").json() == {"saved": True}

    saved = client.get("/api/saved").json()
    assert [s["id"] for s in saved] == [second["id"], first["id"]]  # newest first
    # Field names from SavedItinerarySummary in frontend/src/types.ts.
    assert set(saved[0]) == {
        "id",
        "city",
        "days",
        "stopCount",
        "savedAt",
        "optimizedTravelMinutes",
        "naiveTravelMinutes",
    }
    assert saved[0]["days"] == 3 and saved[0]["optimizedTravelMinutes"] == second["optimizedTravelMinutes"]
    assert saved[0]["stopCount"] == sum(len(d["stops"]) for d in second["dayPlans"])

    # Other users don't see it.
    sign_in("user-2")
    assert client.get("/api/saved").json() == []

    sign_in("user-1")
    assert client.delete(f"/api/saved/{first['id']}").json() == {"saved": False}
    assert [s["id"] for s in client.get("/api/saved").json()] == [second["id"]]


def test_saving_an_unknown_itinerary_is_not_found(client, store, sign_in):
    sign_in("user-1")
    assert client.put("/api/saved/abcdefghijkl").status_code == 404
    assert client.put("/api/saved/bad").status_code == 404


def test_saved_endpoints_without_supabase_are_unavailable(client, sign_in):
    sign_in("user-1")
    response = client.get("/api/saved")
    assert response.status_code == 503
    assert response.json() == {"detail": StorageError().message}


def test_deleting_an_account_keeps_its_itineraries_for_others(client, fake_google, store, sign_in):
    sign_in("user-1")
    created = client.post("/api/itinerary", json={"city": "Paris", "days": 2}).json()
    client.put(f"/api/saved/{created['id']}")
    sign_in("user-2")
    client.put(f"/api/saved/{created['id']}")

    sign_in("user-1")
    response = client.delete("/api/account")
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # The share link still works, and user-2's save is untouched.
    assert client.get(f"/api/itinerary/{created['id']}").json() == created
    assert store.itineraries[created["id"]]["created_by"] is None
    sign_in("user-2")
    assert [s["id"] for s in client.get("/api/saved").json()] == [created["id"]]
