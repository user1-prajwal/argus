"""Tests for PathPlanner.find_path deterministic tie-breaking.

Per docs/path-planner-api.md, ties between equally short routes are
broken deterministically by considering neighboring cells in a fixed
order (Up, Down, Left, Right), so identical inputs always produce
identical routes.
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


def test_find_path_prefers_up_when_multiple_equally_short_routes_exist() -> None:
    # In a small open room, (0,0) -> (1,1) has exactly two shortest
    # routes: Up-then-Right, and Right-then-Up. The documented tie-break
    # considers Up before Right, so Up-then-Right must win.
    world = World(width=3, height=3)
    planner = PathPlanner(world)

    route = planner.find_path(0, 0, 1, 1)

    assert route is not None
    assert route.length == 2
    assert route.cells == ((0, 0), (0, 1), (1, 1))


def test_find_path_tie_break_is_consistent_in_a_larger_open_grid() -> None:
    world = World(width=6, height=6)

    route = PathPlanner(world).find_path(0, 0, 3, 3)
    repeat = PathPlanner(world).find_path(0, 0, 3, 3)

    assert route is not None
    assert route.length == 6  # Manhattan distance in an open grid
    assert route == repeat


def test_find_path_tie_break_is_unaffected_by_obstacles_elsewhere_in_the_world() -> None:
    # An obstacle far away from the relevant region must not perturb
    # the tie-break outcome near the start/goal.
    world = World(width=5, height=5)
    world.add_obstacle(Obstacle(id="far-away", x=4, y=4, type="Tree"))

    route = PathPlanner(world).find_path(0, 0, 1, 1)

    assert route is not None
    assert route.cells == ((0, 0), (0, 1), (1, 1))


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