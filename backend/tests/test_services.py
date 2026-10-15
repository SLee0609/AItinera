import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.algorithm.geo import Point
from app.errors import CityNotFound, NotEnoughAttractions, UpstreamError
from app.services import gemini, places, routes
from app.services.gemini import Candidate

DETAILS_RE = r"https://places\.googleapis\.com/v1/places/(?P<pid>[^/:]+)$"


# --- routes ----------------------------------------------------------------------------------------------


def test_departure_time_skips_weekend():
    friday_afternoon = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
    dep = routes.departure_time("Europe/Paris", now=friday_afternoon)
    assert dep.isoformat() == "2026-10-19T10:00:00+02:00"
    assert routes.rfc3339(dep) == "2026-10-19T08:00:00Z"
    assert routes.departure_time("Not/AZone", now=friday_afternoon).tzinfo is not None


def test_requests_by_origin_chunks_and_skips_self():
    reqs = routes.requests_by_origin({(0, 1), (0, 2), (1, 0)})
    assert reqs == [(0, [1, 2]), (1, [0])]
    big = routes.requests_by_origin({(0, b) for b in range(1, 151)})
    assert [len(d) for _, d in big] == [100, 50]


@respx.mock
async def test_transit_times_maps_indices_and_falls_back():
    def matrix(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["X-Goog-FieldMask"] == routes.MATRIX_FIELDS
        assert body["travelMode"] == "TRANSIT" and body["departureTime"].endswith("Z")
        assert len(body["origins"]) == 1
        # Destination index 0 is omitted, as in real proto3 JSON responses.
        return httpx.Response(
            200,
            json=[
                {"condition": "ROUTE_EXISTS", "duration": "600s"},
                {"destinationIndex": 1, "condition": "ROUTE_NOT_FOUND"},
            ],
        )

    respx.post(routes.MATRIX_URL).mock(side_effect=matrix)
    pts = [Point(0, 0), Point(0, 0.009), Point(0, 0.018)]
    async with httpx.AsyncClient() as client:
        times = await routes.transit_times(client, "k", pts, {(0, 1), (0, 2)}, datetime.now(UTC))
    assert times[(0, 1)] == 600
    assert times[(0, 2)] == pytest.approx(2000 * 1.3 / 1.25, rel=0.02)  # walking estimate


@respx.mock
async def test_transit_times_raises_on_http_error():
    respx.post(routes.MATRIX_URL).mock(return_value=httpx.Response(403, json={"error": "denied"}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError):
            await routes.transit_times(client, "k", [Point(0, 0), Point(0, 1)], {(0, 1)}, datetime.now(UTC))


@respx.mock
async def test_leg_polylines_tolerates_failures():
    responses = iter(
        [
            httpx.Response(200, json={"routes": [{"polyline": {"encodedPolyline": "abc"}}]}),
            httpx.Response(500),
            httpx.Response(200, json={}),
        ]
    )
    respx.post(routes.ROUTES_URL).mock(side_effect=lambda _: next(responses))
    pts = [Point(0, i * 0.01) for i in range(4)]
    async with httpx.AsyncClient() as client:
        lines = await routes.leg_polylines(client, "k", pts, [[0, 1, 2], [3]], datetime.now(UTC), concurrency=1)
    assert lines == [["abc", None], []]


# --- places ----------------------------------------------------------------------------------------------


def city_details(types=("locality", "political")):
    return {
        "id": "paris",
        "formattedAddress": "Paris, France",
        "location": {"latitude": 48.8566, "longitude": 2.3522},
        "viewport": {
            "low": {"latitude": 48.8156, "longitude": 2.2241},
            "high": {"latitude": 48.9022, "longitude": 2.4699},
        },
        "types": list(types),
        "timeZone": {"id": "Europe/Paris"},
    }


@respx.mock
async def test_resolve_city():
    respx.post(places.SEARCH_URL).mock(return_value=httpx.Response(200, json={"places": [{"id": "paris"}]}))
    respx.get(url__regex=DETAILS_RE).mock(return_value=httpx.Response(200, json=city_details()))
    async with httpx.AsyncClient() as client:
        city = await places.resolve_city(client, "k", "paris")
    assert city.name == "Paris, France" and city.time_zone == "Europe/Paris"
    assert city.viewport.contains(Point(48.8584, 2.2945))


@respx.mock
@pytest.mark.parametrize(
    "search, details",
    [
        ({}, None),
        ({"places": [{"id": "x"}]}, city_details(types=("tourist_attraction",))),
    ],
)
async def test_resolve_city_not_found(search, details):
    respx.post(places.SEARCH_URL).mock(return_value=httpx.Response(200, json=search))
    respx.get(url__regex=DETAILS_RE).mock(return_value=httpx.Response(200, json=details))
    async with httpx.AsyncClient() as client:
        with pytest.raises(CityNotFound):
            await places.resolve_city(client, "k", "Atlantis")


def candidate(name: str) -> Candidate:
    return Candidate(name=name, description="d", visit_minutes=60, neighborhood="n")


def fake_places(locations: dict[str, tuple[float, float] | None], types: dict[str, list[str]] | None = None):
    """Search returns `id-<name>` for each query; details return the given location."""
    searched: list[str] = []

    def search(request: httpx.Request) -> httpx.Response:
        name = json.loads(request.content)["textQuery"].split(",")[0]
        searched.append(name)
        return httpx.Response(200, json={"places": [{"id": f"id-{name}"}]})

    def details(request: httpx.Request, pid: str) -> httpx.Response:
        name = pid.removeprefix("id-")
        loc = locations[name]
        if loc is None:
            return httpx.Response(404)
        dedupe = name.split("~")[0]  # "Louvre~2" resolves to the same place as "Louvre"
        return httpx.Response(
            200,
            json={
                "id": f"id-{dedupe}",
                "location": {"latitude": loc[0], "longitude": loc[1]},
                "types": (types or {}).get(name, ["tourist_attraction"]),
            },
        )

    respx.post(places.SEARCH_URL).mock(side_effect=search)
    respx.get(url__regex=DETAILS_RE).mock(side_effect=details)
    return searched


@respx.mock
async def test_resolve_attractions_replaces_rejects_and_dedupes(paris_city):
    searched = fake_places(
        {
            "Louvre": (48.8606, 2.3376),
            "Louvre~2": (48.8606, 2.3376),  # duplicate place
            "Faraway": (40.0, 3.0),  # outside the city
            "Paris": (48.85, 2.35),  # the city itself
            "Orsay": (48.86, 2.3266),
            "Missing": None,
            "Eiffel": (48.8584, 2.2945),
            "Unused": (48.85, 2.30),
        },
        types={"Paris": ["locality", "political"]},
    )
    names = ["Louvre", "Louvre~2", "Faraway", "Paris", "Orsay", "Missing", "Eiffel", "Unused"]
    async with httpx.AsyncClient() as client:
        result = await places.resolve_attractions(
            client, "k", [candidate(n) for n in names], paris_city, target=3, days=1, padding_km=10
        )
    assert [a.name for a in result] == ["Louvre", "Orsay", "Eiffel"]
    assert "Unused" not in searched  # spares are only looked up when needed


@respx.mock
async def test_resolve_attractions_not_enough(paris_city):
    fake_places({"A": (40.0, 3.0), "B": None})
    async with httpx.AsyncClient() as client:
        with pytest.raises(NotEnoughAttractions):
            await places.resolve_attractions(
                client, "k", [candidate("A"), candidate("B")], paris_city, target=4, days=1, padding_km=10
            )


# --- gemini ----------------------------------------------------------------------------------------------


def test_clean_candidates():
    raw = [
        Candidate(name="  Louvre   Museum ", description="Big\nmuseum.", visit_minutes=900, neighborhood=" 1st "),
        Candidate(name="louvre museum", description="dup", visit_minutes=60, neighborhood=""),
        Candidate(name=" ", description="empty", visit_minutes=60, neighborhood=""),
        Candidate(name="Kiosk", description="x" * 300, visit_minutes=1, neighborhood=""),
    ]
    out = gemini.clean_candidates(raw)
    assert [c.name for c in out] == ["Louvre Museum", "Kiosk"]
    assert out[0].visit_minutes == 360 and out[0].description == "Big museum." and out[0].neighborhood == "1st"
    assert out[1].visit_minutes == 15 and len(out[1].description) == 200


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.closed = False

        async def generate_content(**kwargs):
            self.calls += 1
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        async def aclose():
            self.closed = True

        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content), aclose=aclose)


def gemini_response(text: str):
    return SimpleNamespace(parsed=None, text=text)


async def test_suggest_attractions_retries_then_succeeds(monkeypatch):
    fake = FakeClient(
        [
            RuntimeError("503"),
            gemini_response(
                '[{"name":"Louvre","description":"d","visit_minutes":120,"neighborhood":"1st"},'
                '{"name":"Orsay","description":"d","visit_minutes":90,"neighborhood":"7th"}]'
            ),
        ]
    )
    monkeypatch.setattr(gemini.genai, "Client", lambda **_: fake)
    out = await gemini.suggest_attractions(
        api_key="k", model="m", thinking_level="low", city="Paris", days=1, count=1
    )
    assert [c.name for c in out] == ["Louvre"] and fake.calls == 2 and fake.closed


async def test_suggest_attractions_gives_up(monkeypatch):
    fake = FakeClient([gemini_response("not json"), gemini_response("[]")])
    monkeypatch.setattr(gemini.genai, "Client", lambda **_: fake)
    with pytest.raises(UpstreamError):
        await gemini.suggest_attractions(api_key="k", model="m", thinking_level="", city="X", days=1, count=4)
