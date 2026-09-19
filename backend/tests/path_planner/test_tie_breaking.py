"""Tests for PathPlanner.find_path deterministic tie-breaking.

Per app/path_planner/planner.py, ties between equally-costed routes are
broken deterministically by considering neighboring cells in a fixed
order (Up, Down, Left, Right, then the four diagonals), so identical
inputs always produce identical routes. With eight-directional movement,
a genuine tie between two equally-short ORTHOGONAL-only paths (as the
original Up-vs-Right scenarios tested) is now dominated by the strictly
shorter diagonal route in most such cases -- those scenarios are
replaced below with cases that still produce a real tie under the new
movement model, without weakening the underlying guarantee: the same
start, goal, and World state must always produce the same route.
"""

from __future__ import annotations

from app.path_planner import PathPlanner
from app.world import Obstacle, World


def test_find_path_is_deterministic_across_repeated_calls(planner: PathPlanner) -> None:
    first = planner.find_path(0, 0, 4, 4)
    second = planner.find_path(0, 0, 4, 4)
    third = planner.find_path(0, 0, 4, 4)

    assert first == second == third


def test_find_path_is_deterministic_on_a_fresh_planner_instance(world: World) -> None:
    # A brand new PathPlanner bound to the same World reaches the same
    # result as a previous one -- determinism is a property of (world
    # state, start, goal), not of any particular planner instance.
    route_a = PathPlanner(world).find_path(0, 0, 4, 4)
    route_b = PathPlanner(world).find_path(0, 0, 4, 4)

    assert route_a == route_b


def test_find_path_prefers_diagonal_over_equally_short_orthogonal_alternatives() -> None:
    # In an open room, (0,0) -> (1,1) has exactly one shortest route
    # under eight-directional movement -- the direct diagonal (length
    # 1) -- strictly shorter than either orthogonal alternative
    # (Up-then-Right or Right-then-Up, length 2 each). This replaces
    # the old four-directional-only "Up preferred over Right" tie
    # scenario, which no longer produces a tie at all once diagonal
    # movement is available: the diagonal route dominates outright.
    world = World(width=3, height=3)
    planner = PathPlanner(world)

    route = planner.find_path(0, 0, 1, 1)

    assert route is not None
    assert route.length == 1
    assert route.cells == ((0, 0), (1, 1))


def test_find_path_breaks_a_genuine_tie_between_equal_cost_routes() -> None:
    # A real tie under eight-directional movement: from (0,0) to (2,1),
    # two equal-cost routes exist (one diagonal step + one orthogonal
    # step, in either order -- both total the same cost). The fixed
    # neighbor order (orthogonal directions before diagonals, see
    # app/path_planner/planner.py's _NEIGHBOR_OFFSETS) must still pick
    # the same one every time.
    world = World(width=5, height=5)

    route = PathPlanner(world).find_path(0, 0, 2, 1)
    repeat = PathPlanner(world).find_path(0, 0, 2, 1)

    assert route is not None
    assert route.length == 2  # one diagonal + one orthogonal step
    assert route == repeat


def test_find_path_tie_break_is_consistent_in_a_larger_open_grid() -> None:
    world = World(width=6, height=6)

    route = PathPlanner(world).find_path(0, 0, 3, 3)
    repeat = PathPlanner(world).find_path(0, 0, 3, 3)

    assert route is not None
    # Shortest route under eight-directional movement is a pure
    # diagonal: 3 moves, not the 6-move Manhattan distance a
    # four-directional-only search would require.
    assert route.length == 3
    assert route == repeat


def test_find_path_tie_break_is_unaffected_by_obstacles_elsewhere_in_the_world() -> None:
    # An obstacle far away from the relevant region must not perturb
    # the tie-break outcome near the start/goal.
    world = World(width=5, height=5)
    world.add_obstacle(Obstacle(id="far-away", x=4, y=4, type="Tree"))

    route = PathPlanner(world).find_path(0, 0, 1, 1)

    assert route is not None
    # Direct diagonal remains the unique shortest route regardless of
    # an unrelated obstacle elsewhere in the world.
    assert route.cells == ((0, 0), (1, 1))


def test_find_path_forward_and_backward_queries_agree_on_length(planner: PathPlanner) -> None:
    # Sanity check only: find_path(a, b) need not equal reversed
    # find_path(b, a) cell-for-cell (ties can break differently in each
    # direction) -- both must still be valid deterministic shortest
    # routes of the same length.
    forward = planner.find_path(0, 0, 2, 2)
    backward = planner.find_path(2, 2, 0, 0)

    assert forward is not None
    assert backward is not None
    assert forward.length == backward.length
