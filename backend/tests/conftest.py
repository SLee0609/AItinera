import pytest

from app.algorithm.geo import Point, Viewport
from app.services.places import Attraction, CityPlace

# Same sample as frontend/src/api/mock.ts, in the LLM's priority order.
PARIS = [
    ("arc", "Arc de Triomphe", 60, "Étoile", 48.8738, 2.2950),
    ("eiffel", "Eiffel Tower", 120, "Champ de Mars", 48.8584, 2.2945),
    ("louvre", "Louvre Museum", 180, "Louvre", 48.8606, 2.3376),
    ("notredame", "Notre-Dame", 60, "Île de la Cité", 48.8530, 2.3499),
    ("sacrecoeur", "Sacré-Cœur", 120, "Montmartre", 48.8867, 2.3431),
    ("orsay", "Musée d'Orsay", 150, "Saint-Germain", 48.8600, 2.3266),
    ("chapelle", "Sainte-Chapelle", 45, "Île de la Cité", 48.8554, 2.3450),
    ("pompidou", "Centre Pompidou", 120, "Le Marais", 48.8607, 2.3522),
    ("pantheon", "Panthéon & Luxembourg", 90, "Latin Quarter", 48.8462, 2.3464),
    ("canal", "Canal Saint-Martin", 60, "Canal Saint-Martin", 48.8710, 2.3657),
    ("marais", "Le Marais", 90, "Le Marais", 48.8556, 2.3655),
    ("vosges", "Place des Vosges", 45, "Le Marais", 48.8556, 2.3660),
]


@pytest.fixture
def paris_city() -> CityPlace:
    return CityPlace(
        name="Paris, France",
        center=Point(48.8566, 2.3522),
        viewport=Viewport(Point(48.8156, 2.2241), Point(48.9022, 2.4699)),
        time_zone="Europe/Paris",
    )


@pytest.fixture
def paris_attractions() -> list[Attraction]:
    return [
        Attraction(
            place_id=f"id-{key}",
            name=name,
            description=f"About {name}.",
            visit_minutes=visit,
            neighborhood=hood,
            location=Point(lat, lng),
        )
        for key, name, visit, hood, lat, lng in PARIS
    ]
