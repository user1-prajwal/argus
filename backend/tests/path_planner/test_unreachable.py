"""Tests for PathPlanner.find_path when no route exists.

Per docs/path-planner-api.md, "no route exists" is never an error --
find_path returns None.
"""

from __future__ import annotations

from app.path_planner import PathPlanner
from app.world import Obstacle, World


def test_find_path_returns_none_when_goal_is_walled_off(
    world: World, planner: PathPlanner
) -> None:
    # (4, 4) is a corner of a 5x5 world, so it has only two neighbors
    # within bounds: (3, 4) and (4, 3). Blocking both fully encloses it.
    world.add_obstacle(Obstacle(id="o1", x=3, y=4, type="Wall"))
    world.add_obstacle(Obstacle(id="o2", x=4, y=3, type="Wall"))

    route = planner.find_path(0, 0, 4, 4)

    assert route is None


def test_find_path_returns_none_when_start_is_not_walkable(
    world: World, planner: PathPlanner
) -> None:
    world.add_obstacle(Obstacle(id="o1", x=0, y=0, type="Building"))

    route = planner.find_path(0, 0, 4, 4)

    assert route is None


def test_find_path_returns_none_when_goal_is_not_walkable(
    world: World, planner: PathPlanner
) -> None:
    world.add_obstacle(Obstacle(id="o1", x=4, y=4, type="Building"))

    route = planner.find_path(0, 0, 4, 4)

    assert route is None


def test_find_path_returns_none_when_start_equals_goal_but_is_not_walkable(
    world: World, planner: PathPlanner
) -> None:
    # Being "already there" does not help if the cell itself is blocked.
    world.add_obstacle(Obstacle(id="o1", x=2, y=2, type="Building"))

    route = planner.find_path(2, 2, 2, 2)

    assert route is None


def test_find_path_returns_none_when_no_route_exists_at_all(
    world: World, planner: PathPlanner
) -> None:
    # An unbroken wall along x=2 splits the 5x5 world in half.
    for y in range(5):
        world.add_obstacle(Obstacle(id=f"wall-{y}", x=2, y=y, type="Wall"))

    route = planner.find_path(0, 0, 4, 4)

    assert route is None


def test_find_path_finds_route_when_wall_has_one_gap(
    world: World, planner: PathPlanner
) -> None:
    # Same wall as above, but leave a single gap at y=2.
    for y in range(5):
        if y != 2:
            world.add_obstacle(Obstacle(id=f"wall-{y}", x=2, y=y, type="Wall"))

    route = planner.find_path(0, 0, 4, 4)

    assert route is not None
    assert (2, 2) in route.cells


def test_find_path_none_does_not_raise_for_an_otherwise_valid_query(
    world: World, planner: PathPlanner
) -> None:
    # In-bounds, correctly typed coordinates with no route available
    # must return None quietly, not raise.
    for y in range(5):
        world.add_obstacle(Obstacle(id=f"wall-{y}", x=2, y=y, type="Wall"))

    result = planner.find_path(0, 0, 4, 4)

    assert result is None