"""The naive itinerary used as a reference: attractions in the LLM's order, cut into consecutive days."""

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


def naive_travel_minutes(n: int, days: int, times: TravelTimes) -> int:
    """Rounded per leg, like the optimized itinerary, so the two totals are comparable."""
    return sum(round(times[(a, b)] / 60) for day in naive_days(n, days) for a, b in pairwise(day))
