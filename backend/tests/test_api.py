from itertools import pairwise

import pytest
from fastapi.testclient import TestClient

from app import main, pipeline
from app.algorithm.geo import walking_estimate_s
from app.config import Settings, get_settings
from app.errors import CityNotFound, NotEnoughAttractions, PlanningTimeout, UpstreamError
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


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_itinerary_shape_matches_frontend_types(client, fake_google):
    response = client.post("/api/itinerary", json={"city": "  Paris ", "days": 3})
    assert response.status_code == 200, response.text
    body = response.json()

    # Field names from frontend/src/types.ts.
    assert set(body) == {"city", "travelMode", "dayPlans", "optimizedTravelMinutes", "naiveTravelMinutes"}
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
