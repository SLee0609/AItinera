"""The naive itinerary used as a reference: attractions in the LLM's order, cut into consecutive days."""

from collections.abc import Sequence
from itertools import pairwise

from .ordering import TravelTimes


def split_evenly(n: int, k: int) -> list[int]:
    """Chunk sizes for n items in k chunks, differing by at most one (larger chunks first)."""
    base, extra = divmod(n, k)
    return [base + 1] * extra + [base] * (k - extra)


def naive_days(n: int, days: int) -> list[list[int]]:
    chunks, start = [], 0
    for size in split_evenly(n, days):
        chunks.append(list(range(start, start + size)))
        start += size
    return chunks


def baseline_pairs(n: int, days: int) -> set[tuple[int, int]]:
    """Consecutive pairs within each naive day: the travel times the baseline needs."""
    return {(a, b) for day in naive_days(n, days) for a, b in pairwise(day)}


def route_minutes(orders: Sequence[Sequence[int]], times: TravelTimes) -> int:
    """Total travel of the day routes, rounded per leg like the API response so totals are comparable."""
    return sum(round(times[(a, b)] / 60) for order in orders for a, b in pairwise(order))


def naive_travel_minutes(n: int, days: int, times: TravelTimes) -> int:
    return route_minutes(naive_days(n, days), times)


def fastest_plan(orders: Sequence[Sequence[int]], n: int, days: int, times: TravelTimes) -> list[list[int]]:
    """The optimized day routes, or the naive ones when those travel less.

    Days are partitioned with straight-line estimates but scored with real transit times, so the
    naive plan can occasionally win; the itinerary should never be slower than its baseline. Ties
    keep the optimized plan.
    """
    naive = naive_days(n, days)
    return naive if route_minutes(naive, times) < route_minutes(orders, times) else [list(o) for o in orders]
