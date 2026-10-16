import random
from itertools import pairwise, permutations

import pytest

from app.algorithm.baseline import (
    baseline_pairs,
    fastest_plan,
    naive_days,
    naive_travel_minutes,
    route_minutes,
    split_evenly,
)
from app.algorithm.clustering import (
    assign_remaining,
    distance_matrix,
    estimated_travel,
    partition_into_days,
    refine,
    select_seeds,
    travel_estimator,
)
from app.algorithm.geo import Point, Viewport, haversine_m, walking_estimate_s
from app.algorithm.ordering import best_order, intra_day_pairs, path_cost


def line_points(n: int) -> list[Point]:
    """Points 1 km apart going east along the equator."""
    return [Point(0.0, i * 0.008993) for i in range(n)]


def grid_points(xy: list[tuple[int, int]]) -> list[Point]:
    """Points on a 1 km grid near the equator: x east, y north."""
    return [Point(y * 0.008993, x * 0.008993) for x, y in xy]


# --- geo -------------------------------------------------------------------------------------------------


def test_haversine_known_distance():
    # Eiffel Tower to Arc de Triomphe is about 1.7 km.
    assert haversine_m(Point(48.8584, 2.2945), Point(48.8738, 2.2950)) == pytest.approx(1713, abs=20)


def test_walking_estimate_is_slower_than_straight_line():
    a, b = line_points(2)
    assert walking_estimate_s(a, b) == pytest.approx(1000 * 1.3 / 1.25, rel=0.01)


def test_viewport_padding_and_antimeridian():
    v = Viewport(Point(0, 0), Point(1, 1))
    assert not v.contains(Point(1.05, 0.5))
    assert v.padded(10).contains(Point(1.05, 0.5))
    fiji = Viewport(Point(-20, 177), Point(-15, -178))
    assert fiji.contains(Point(-17, 179.5)) and fiji.contains(Point(-17, -179))
    assert not fiji.contains(Point(-17, 0))


# --- clustering ------------------------------------------------------------------------------------------


def test_seeds_are_spread_out():
    dist = distance_matrix(line_points(10))
    assert sorted(select_seeds(dist, 2)) == [0, 9]
    assert sorted(select_seeds(dist, 3)) == [0, 4, 9]
    assert select_seeds(dist, 2, first=4) == [4, 9]


def test_estimated_travel_small_groups_and_lines():
    dist = distance_matrix(line_points(5))
    assert estimated_travel([], dist) == 0.0
    assert estimated_travel([3], dist) == 0.0
    # Visiting points on a line costs the distance between its ends, whatever the input order.
    assert estimated_travel([4, 0, 2], dist) == pytest.approx(4000, rel=0.01)


def test_estimated_travel_matches_brute_force():
    rng = random.Random(0)
    pts = [Point(rng.uniform(0, 0.05), rng.uniform(0, 0.05)) for _ in range(7)]
    dist = distance_matrix(pts)
    brute = min(sum(dist[a][b] for a, b in pairwise(p)) for p in permutations(range(7)))
    assert estimated_travel(range(7), dist) == pytest.approx(brute)


def test_refine_never_breaks_limits_or_adds_travel():
    rng = random.Random(1)
    for _ in range(30):
        n, days = 12, 3
        pts = [Point(rng.uniform(0, 0.1), rng.uniform(0, 0.1)) for _ in range(n)]
        visit = [rng.choice([60, 90, 120, 180]) for _ in range(n)]
        dist, cap = distance_matrix(pts), sum(visit) / days * 1.25
        travel = travel_estimator(dist)
        start = assign_remaining(dist, visit, select_seeds(dist, days), 5, 1.25)
        groups = refine(start, visit, 5, cap, travel)
        assert sorted(i for g in groups for i in g) == list(range(n))
        assert all(1 <= len(g) <= 5 for g in groups)
        limit = max(cap, *(sum(visit[i] for i in s) for s in start))
        assert all(sum(visit[i] for i in g) <= limit for g in groups)
        assert sum(travel(g) for g in groups) <= sum(travel(g) for g in start)


def test_partition_assigns_every_attraction_once(paris_attractions):
    points = [a.location for a in paris_attractions]
    visit = [a.visit_minutes for a in paris_attractions]
    groups = partition_into_days(points, visit, 3)
    assert len(groups) == 3
    assert sorted(i for g in groups for i in g) == list(range(len(points)))
    assert groups[0][0] == 0  # day 1 holds the top-ranked attraction
    assert groups == partition_into_days(points, visit, 3)  # deterministic


def test_partition_keeps_neighbors_together(paris_attractions):
    points = [a.location for a in paris_attractions]
    groups = partition_into_days(points, [a.visit_minutes for a in paris_attractions], 3)
    day_of = {i: d for d, g in enumerate(groups) for i in g}
    names = {a.name: i for i, a in enumerate(paris_attractions)}
    assert day_of[names["Le Marais"]] == day_of[names["Place des Vosges"]]
    assert day_of[names["Notre-Dame"]] == day_of[names["Sainte-Chapelle"]]


def test_partition_splits_far_apart_clusters():
    # Sites 0, 1, 3 are in the west (x <= 1 km) and 2, 4, 5 in the east (x >= 3 km).
    pts = grid_points([(1, 5), (0, 3), (5, 5), (1, 6), (5, 3), (3, 5)])
    dist = distance_matrix(pts)
    # The greedy start alone mixes them: west sites 1 and 3 share a day with site 4, 5 km east.
    assert sorted(map(sorted, assign_remaining(dist, [60] * 6, select_seeds(dist, 2), 8, 1.25))) == [
        [0, 2, 5],
        [1, 3, 4],
    ]
    assert partition_into_days(pts, [60] * 6, 2) == [[0, 1, 3], [2, 4, 5]]


def test_partition_balances_workload():
    # Two tight clusters of 4, plus 4 more points next to cluster A: pure proximity would overload A.
    cluster_a, cluster_b = line_points(4), [Point(1.0, p.lng) for p in line_points(4)]
    pts = cluster_a + cluster_b + [Point(0.001, 0.03 + i * 0.001) for i in range(4)]
    visit = [60] * len(pts)
    groups = partition_into_days(pts, visit, 2, max_stops=8, tolerance=1.25)
    loads = [sum(visit[i] for i in g) for g in groups]
    assert max(loads) <= sum(visit) / 2 * 1.25


def test_partition_respects_max_stops():
    pts = line_points(12)
    groups = partition_into_days(pts, [30] * 12, 2, max_stops=6, tolerance=10)
    assert [len(g) for g in groups] == [6, 6]


def test_single_day_and_invalid_inputs():
    assert partition_into_days(line_points(3), [60] * 3, 1) == [[0, 1, 2]]
    with pytest.raises(ValueError):
        partition_into_days(line_points(2), [60] * 2, 3)
    with pytest.raises(ValueError):
        partition_into_days(line_points(10), [60] * 10, 1, max_stops=8)


# --- ordering --------------------------------------------------------------------------------------------


def line_times(n: int, forward: float = 10, backward: float = 10) -> dict[tuple[int, int], float]:
    return {(a, b): abs(a - b) * (forward if b > a else backward) for a in range(n) for b in range(n) if a != b}


def test_best_order_on_a_line():
    order, cost = best_order([2, 0, 3, 1], line_times(4))
    assert (order, cost) == ([0, 1, 2, 3], 30)  # tie with [3, 2, 1, 0] resolves lexicographically


def test_best_order_uses_direction():
    order, cost = best_order(range(4), line_times(4, forward=10, backward=4))
    assert (order, cost) == ([3, 2, 1, 0], 12)


def test_best_order_beats_every_other_order():
    times = {(a, b): float((a * 7 + b * 13) % 11 + 1) for a in range(5) for b in range(5) if a != b}
    _, cost = best_order(range(5), times)
    assert cost == min(path_cost(p, times) for p in permutations(range(5)))


def test_small_groups():
    assert best_order([4], {}) == ([4], 0.0)
    assert best_order([], {}) == ([], 0.0)


def test_intra_day_pairs():
    assert intra_day_pairs([[0, 1], [2]]) == {(0, 1), (1, 0)}


# --- baseline --------------------------------------------------------------------------------------------


def test_split_evenly():
    assert split_evenly(11, 3) == [4, 4, 3]
    assert split_evenly(4, 4) == [1, 1, 1, 1]
    assert naive_days(5, 2) == [[0, 1, 2], [3, 4]]


def test_baseline_pairs_and_minutes():
    assert baseline_pairs(5, 2) == {(0, 1), (1, 2), (3, 4)}
    times = {(0, 1): 89.0, (1, 2): 150.0, (3, 4): 31.0}  # 1.48, 2.5, 0.52 minutes
    assert naive_travel_minutes(5, 2, times) == 1 + 2 + 1


def test_route_minutes_rounds_per_leg():
    times = {(0, 1): 89.0, (1, 2): 89.0}  # 1.48 minutes each
    assert route_minutes([[0, 1, 2], [3]], times) == 1 + 1


# Naive days for 4 stops over 2 days are [0, 1] and [2, 3]; the optimized plan pairs them differently.
OPTIMIZED = [[0, 2], [1, 3]]


def test_fastest_plan_keeps_optimized_when_it_travels_less():
    times = {(0, 2): 60.0, (1, 3): 60.0, (0, 1): 600.0, (2, 3): 600.0}
    assert fastest_plan(OPTIMIZED, 4, 2, times) == OPTIMIZED


def test_fastest_plan_falls_back_to_naive_when_it_travels_less():
    times = {(0, 2): 600.0, (1, 3): 600.0, (0, 1): 60.0, (2, 3): 60.0}
    assert fastest_plan(OPTIMIZED, 4, 2, times) == [[0, 1], [2, 3]]


def test_fastest_plan_keeps_optimized_on_a_tie():
    # 89 s and 150 s legs round to the same minutes (1 + 2 = 3 per plan).
    times = {(0, 2): 89.0, (1, 3): 150.0, (0, 1): 150.0, (2, 3): 89.0}
    assert fastest_plan(OPTIMIZED, 4, 2, times) == OPTIMIZED
