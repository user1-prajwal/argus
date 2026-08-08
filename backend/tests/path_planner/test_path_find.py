"""Tests for PathPlanner.find_path -- core pathfinding behavior."""

from __future__ import annotations

import dataclasses

import pytest

from app.path_planner import PathPlanner, Route
from app.world import Obstacle, World


def _is_four_directional_step(a: tuple[int, int], b: tuple[int, int]) -> bool:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx, dy) in {(1, 0), (0, 1)}


def test_find_path_straight_line(planner: PathPlanner) -> None:
    route = planner.find_path(0, 0, 3, 0)

    assert route is not None
    assert route.cells[0] == (0, 0)
    assert route.cells[-1] == (3, 0)
    assert route.length == 3


def test_find_path_start_equals_goal(planner: PathPlanner) -> None:
    route = planner.find_path(2, 2, 2, 2)

    assert route == Route(cells=((2, 2),), length=0)


def test_find_path_returns_shortest_length_in_open_grid(planner: PathPlanner) -> None:
    route = planner.find_path(0, 0, 2, 2)

    assert route is not None
    assert route.length == 4  # Manhattan distance in an open grid


def test_find_path_every_step_is_four_directional(planner: PathPlanner) -> None:
    route = planner.find_path(0, 0, 4, 4)

    assert route is not None
    for a, b in zip(route.cells, route.cells[1:]):
        assert _is_four_directional_step(a, b)


def test_find_path_cells_are_contiguous_start_to_goal(planner: PathPlanner) -> None:
    route = planner.find_path(0, 0, 4, 4)

    assert route is not None
    assert route.cells[0] == (0, 0)
    assert route.cells[-1] == (4, 4)
    assert len(route.cells) == route.length + 1


def test_find_path_detours_around_a_wall(world: World, planner: PathPlanner) -> None:
    # A wall across y=1 for x in [0, 3], leaving x=4 as the only gap.
    for x in range(4):
        world.add_obstacle(Obstacle(id=f"wall-{x}", x=x, y=1, type="Wall"))

    route = planner.find_path(0, 0, 0, 2)

    assert route is not None
    assert (0, 1) not in route.cells
    assert route.cells[0] == (0, 0)
    assert route.cells[-1] == (0, 2)


def test_find_path_treats_occupied_cells_as_impassable(world: World) -> None:
    # (1, 0) is the only route from (0, 0) to (2, 0) in a 1-row-tall
    # corridor -- occupy it and confirm the direct route is refused.
    corridor = World(width=3, height=1)
    corridor_planner = PathPlanner(corridor)
    # Private hook, reserved for a future Agent module -- calling it
    # directly here mirrors how World's own test suite exercises it.
    corridor._occupy_cell(1, 0)

    route = corridor_planner.find_path(0, 0, 2, 0)

    assert route is None


def test_route_is_immutable(planner: PathPlanner) -> None:
    route = planner.find_path(0, 0, 1, 0)
    assert route is not None

    with pytest.raises(dataclasses.FrozenInstanceError):
        route.length = 99  # type: ignore[misc]


def test_route_equality_is_value_based(planner: PathPlanner) -> None:
    first = planner.find_path(0, 0, 3, 0)
    second = planner.find_path(0, 0, 3, 0)

    assert first == second
    assert first is not second