"""Step 3: split attractions into days with the least estimated travel and similar amounts of sightseeing.

Distances are straight-line (haversine), so this step makes no API calls. Attractions are
identified by their index, which is also their priority rank (0 = most important).

Each start (one per possible first seed) builds days greedily, then local search moves and swaps
attractions between days while that shortens the total estimated travel. The best start wins.
"""

import math
from collections.abc import Callable, Sequence
from itertools import combinations

from .geo import Point, haversine_m

# A move must shorten the total estimated travel by more than this, so float noise can't make it cycle.
MIN_GAIN_M = 1.0

# Estimated travel of a day, in metres, for a group of attraction indices.
TravelEstimator = Callable[[Sequence[int]], float]


def distance_matrix(points: Sequence[Point]) -> list[list[float]]:
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist[i][j] = dist[j][i] = haversine_m(points[i], points[j])
    return dist


def estimated_travel(group: Sequence[int], dist: Sequence[Sequence[float]]) -> float:
    """Length of the shortest open path through the group (no return to the start), in metres.

    Held-Karp dynamic programming over subsets: O(2^m · m²), fine for the at most 8 stops in a day.
    """
    stops = sorted(group)
    m = len(stops)
    if m <= 1:
        return 0.0
    # best[mask][j]: shortest path that visits exactly the stops in `mask` and ends at stop j.
    best = [[math.inf] * m for _ in range(1 << m)]
    for j in range(m):
        best[1 << j][j] = 0.0
    for mask in range(1, 1 << m):
        row = best[mask]
        for j in range(m):
            if row[j] == math.inf:
                continue
            from_j = dist[stops[j]]
            for nxt in range(m):
                if mask & (1 << nxt):
                    continue
                cost = row[j] + from_j[stops[nxt]]
                if cost < best[mask | (1 << nxt)][nxt]:
                    best[mask | (1 << nxt)][nxt] = cost
    return min(best[-1])


def travel_estimator(dist: Sequence[Sequence[float]]) -> TravelEstimator:
    """`estimated_travel` memoized by group, since local search evaluates the same days repeatedly."""
    cache: dict[frozenset[int], float] = {}

    def travel(group: Sequence[int]) -> float:
        key = frozenset(group)
        if key not in cache:
            cache[key] = estimated_travel(group, dist)
        return cache[key]

    return travel


def select_seeds(dist: Sequence[Sequence[float]], k: int, first: int | None = None) -> list[int]:
    """Farthest-point selection: one anchor attraction per day, spread across the city.

    The first seed is `first`, or by default the attraction with the largest total distance to all
    others. Each next seed is the attraction farthest from its nearest chosen seed. Ties go to the
    lower index.
    """
    n = len(dist)
    if first is None:
        first = max(range(n), key=lambda i: (sum(dist[i]), -i))
    seeds = [first]
    nearest = list(dist[first])
    while len(seeds) < k:
        nxt = max((i for i in range(n) if i not in seeds), key=lambda i: (nearest[i], -i))
        seeds.append(nxt)
        nearest = [min(nearest[i], dist[nxt][i]) for i in range(n)]
    return seeds


def assign_remaining(
    dist: Sequence[Sequence[float]],
    visit_minutes: Sequence[int],
    seeds: Sequence[int],
    max_stops: int,
    tolerance: float,
) -> list[list[int]]:
    """Greedily grow each seed's day, closest attraction first, without overloading any day.

    A day is full when its visit time would exceed `tolerance` × the average per day, or when it
    has `max_stops` stops. Closeness is the distance to the nearest attraction already in the day.
    """
    n, k = len(dist), len(seeds)
    groups = [[s] for s in seeds]
    load = [visit_minutes[s] for s in seeds]
    cap = sum(visit_minutes) / k * tolerance
    unassigned = sorted(set(range(n)) - set(seeds))
    # nearest[i][g]: distance from attraction i to the closest member of day g.
    nearest = {i: [dist[i][s] for s in seeds] for i in unassigned}

    while unassigned:
        best: tuple[float, int, int] | None = None
        for i in unassigned:
            for g in range(k):
                if len(groups[g]) < max_stops and load[g] + visit_minutes[i] <= cap:
                    cand = (nearest[i][g], i, g)
                    if best is None or cand < best:
                        best = cand
        if best is None:
            # No day has room under the time cap: use the least-loaded day that still has stops left.
            g = min((g for g in range(k) if len(groups[g]) < max_stops), key=lambda g: (load[g], g))
            i = min(unassigned, key=lambda i: (nearest[i][g], i))
        else:
            _, i, g = best

        groups[g].append(i)
        load[g] += visit_minutes[i]
        unassigned.remove(i)
        del nearest[i]
        for j in unassigned:
            nearest[j][g] = min(nearest[j][g], dist[j][i])

    return groups


def refine(
    groups: Sequence[Sequence[int]],
    visit_minutes: Sequence[int],
    max_stops: int,
    cap: float,
    travel: TravelEstimator,
) -> list[list[int]]:
    """Local search: move or swap attractions between days while that shortens the total estimated travel.

    Moves keep every day non-empty, within `max_stops`, and within `cap` minutes of sightseeing (a day
    already over the cap may swap as long as its load doesn't grow). Attractions are tried in index
    order and the first improving move is taken, so the result is deterministic. Each move shortens
    the total by more than `MIN_GAIN_M`, so the search always ends.
    """
    groups = [sorted(g) for g in groups]
    load = [sum(visit_minutes[i] for i in g) for g in groups]
    cost = [travel(g) for g in groups]
    day = {i: d for d, g in enumerate(groups) for i in g}

    def apply(a: int, new_a: list[int], b: int, new_b: list[int]) -> None:
        for d, g in ((a, sorted(new_a)), (b, sorted(new_b))):
            groups[d], load[d], cost[d] = g, sum(visit_minutes[i] for i in g), travel(g)
            for i in g:
                day[i] = d

    improved = True
    while improved:
        improved = False
        # Relocate one attraction to another day.
        for i in sorted(day):
            a = day[i]
            if len(groups[a]) == 1:
                continue
            rest = [x for x in groups[a] if x != i]
            for b in range(len(groups)):
                if b == a or len(groups[b]) >= max_stops or load[b] + visit_minutes[i] > cap:
                    continue
                grown = [*groups[b], i]
                if cost[a] + cost[b] - travel(rest) - travel(grown) > MIN_GAIN_M:
                    apply(a, rest, b, grown)
                    improved = True
                    break
        # Swap two attractions on different days.
        for i, j in combinations(sorted(day), 2):
            a, b = day[i], day[j]
            if a == b:
                continue
            load_a = load[a] - visit_minutes[i] + visit_minutes[j]
            load_b = load[b] - visit_minutes[j] + visit_minutes[i]
            if load_a > max(cap, load[a]) or load_b > max(cap, load[b]):
                continue
            new_a = [x for x in groups[a] if x != i] + [j]
            new_b = [x for x in groups[b] if x != j] + [i]
            if cost[a] + cost[b] - travel(new_a) - travel(new_b) > MIN_GAIN_M:
                apply(a, new_a, b, new_b)
                improved = True

    return groups


def order_days(groups: Sequence[Sequence[int]]) -> list[list[int]]:
    """Day 1 holds the top-ranked attraction, then by each day's best-ranked attraction."""
    return sorted((sorted(g) for g in groups), key=min)


def partition_into_days(
    points: Sequence[Point],
    visit_minutes: Sequence[int],
    days: int,
    max_stops: int = 8,
    tolerance: float = 1.25,
) -> list[list[int]]:
    n = len(points)
    if n < days:
        raise ValueError(f"Need at least {days} attractions, got {n}")
    if n > days * max_stops:
        raise ValueError(f"{n} attractions don't fit in {days} days of at most {max_stops} stops")
    if days == 1:
        return [list(range(n))]
    dist = distance_matrix(points)
    travel = travel_estimator(dist)
    cap = sum(visit_minutes) / days * tolerance
    best: list[list[int]] = []
    best_total = math.inf
    tried: set[frozenset[int]] = set()
    for first in range(n):
        seeds = select_seeds(dist, days, first)
        if frozenset(seeds) in tried:
            continue
        tried.add(frozenset(seeds))
        start = assign_remaining(dist, visit_minutes, seeds, max_stops, tolerance)
        groups = refine(start, visit_minutes, max_stops, cap, travel)
        total = sum(travel(g) for g in groups)
        if total < best_total - MIN_GAIN_M:  # ties keep the earlier start
            best, best_total = groups, total
    return order_days(best)
