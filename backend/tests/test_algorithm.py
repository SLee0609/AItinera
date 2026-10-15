import pytest

from app.algorithm.baseline import baseline_pairs, naive_days, naive_travel_minutes, split_evenly
from app.algorithm.clustering import distance_matrix, partition_into_days, select_seeds
from app.algorithm.geo import Point, Viewport, haversine_m, walking_estimate_s
from app.algorithm.ordering import best_order, intra_day_pairs, path_cost


def line_points(n: int) -> list[Point]:
    """Points 1 km apart going east along the equator."""
    return [Point(0.0, i * 0.008993) for i in range(n)]


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
    from itertools import permutations

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
