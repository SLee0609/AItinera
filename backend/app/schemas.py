"""API request and response models. JSON uses camelCase to match `frontend/src/types.ts`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

MIN_DAYS = 1
MAX_DAYS = 7
MAX_CITY_LENGTH = 100


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ItineraryRequest(CamelModel):
    city: str = Field(min_length=1, max_length=MAX_CITY_LENGTH)
    days: int = Field(ge=MIN_DAYS, le=MAX_DAYS, strict=True)

    @field_validator("city", mode="before")
    @classmethod
    def strip_city(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class LatLng(CamelModel):
    lat: float
    lng: float


class Stop(CamelModel):
    place_id: str
    name: str
    description: str
    visit_minutes: int
    location: LatLng


class Leg(CamelModel):
    duration_minutes: int
    polyline: str | None = None


class DayPlan(CamelModel):
    day: int
    title: str | None = None
    stops: list[Stop]
    legs: list[Leg]
    travel_minutes: int


class Itinerary(CamelModel):
    city: str
    travel_mode: Literal["TRANSIT"] = "TRANSIT"
    day_plans: list[DayPlan]
    optimized_travel_minutes: int
    naive_travel_minutes: int
