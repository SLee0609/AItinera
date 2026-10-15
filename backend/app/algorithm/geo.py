import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000.0
WALKING_SPEED_MPS = 4.5 / 3.6
# Streets are rarely straight; scale straight-line distance to approximate a walking route.
WALKING_DETOUR_FACTOR = 1.3


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


@dataclass(frozen=True)
class Viewport:
    low: Point  # south-west corner
    high: Point  # north-east corner

    def padded(self, km: float) -> "Viewport":
        dlat = km / 111.32
        mid_lat = math.radians((self.low.lat + self.high.lat) / 2)
        dlng = km / (111.32 * max(math.cos(mid_lat), 0.01))
        return Viewport(
            Point(max(self.low.lat - dlat, -90.0), self.low.lng - dlng),
            Point(min(self.high.lat + dlat, 90.0), self.high.lng + dlng),
        )

    def contains(self, p: Point) -> bool:
        if not self.low.lat <= p.lat <= self.high.lat:
            return False
        low, high, lng = _wrap(self.low.lng), _wrap(self.high.lng), _wrap(p.lng)
        if low <= high:
            return low <= lng <= high
        return lng >= low or lng <= high  # viewport crosses the antimeridian


def _wrap(lng: float) -> float:
    return (lng + 180.0) % 360.0 - 180.0


def around(center: Point, km: float) -> Viewport:
    return Viewport(center, center).padded(km)


def haversine_m(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def walking_estimate_s(a: Point, b: Point) -> float:
    """Rough walking time, used when no transit route is available."""
    return haversine_m(a, b) * WALKING_DETOUR_FACTOR / WALKING_SPEED_MPS
