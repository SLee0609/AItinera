"""Step 5: find the visiting order with the least travel time within each day."""

from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise, permutations

# Directed travel time in seconds, keyed by (from_index, to_index).
TravelTimes = Mapping[tuple[int, int], float]


def path_cost(order: Sequence[int], times: TravelTimes) -> float:
    return sum(times[(a, b)] for a, b in pairwise(order))


def best_order(group: Iterable[int], times: TravelTimes) -> tuple[list[int], float]:
    """Brute force over every order, as an open path (no return to the start).

    Permutations of the sorted group come out in lexicographic order and only a strictly lower
    cost replaces the best, so ties resolve to the lexicographically first order.
    """
    stops = sorted(group)
    if len(stops) <= 1:
        return stops, 0.0
    best: tuple[int, ...] = tuple(stops)
    best_cost = path_cost(best, times)
    for order in permutations(stops):
        cost = path_cost(order, times)
        if cost < best_cost:
            best, best_cost = order, cost
    return list(best), best_cost


def intra_day_pairs(groups: Iterable[Sequence[int]]) -> set[tuple[int, int]]:
    """Every ordered pair of different stops in the same day: what `best_order` needs."""
    return {(a, b) for g in groups for a in g for b in g if a != b}
