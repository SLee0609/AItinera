"""Step 3: split attractions into geographically compact days with similar amounts of sightseeing.

Distances are straight-line (haversine), so this step makes no API calls. Attractions are
identified by their index, which is also their priority rank (0 = most important).
"""

from collections.abc import Sequence

from .geo import Point, haversine_m


def distance_matrix(points: Sequence[Point]) -> list[list[float]]:
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist[i][j] = dist[j][i] = haversine_m(points[i], points[j])
    return dist


def select_seeds(dist: Sequence[Sequence[float]], k: int) -> list[int]:
    """Farthest-point selection: one anchor attraction per day, spread across the city.

    The first seed is the attraction with the largest total distance to all others. Each
    next seed is the attraction farthest from its nearest chosen seed. Ties go to the lower index.
    """
    n = len(dist)
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
    seeds = select_seeds(dist, days)
    return order_days(assign_remaining(dist, visit_minutes, seeds, max_stops, tolerance))
