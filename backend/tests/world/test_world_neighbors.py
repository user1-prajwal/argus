"""Tests for World.get_neighbors."""

from __future__ import annotations

from app.world import Obstacle, World


def test_get_neighbors_interior_cell_returns_four_in_up_down_left_right_order(
    world: World,
) -> None:
    neighbors = world.get_neighbors(5, 5)
    coords = [(n.x, n.y) for n in neighbors]

    # Up (+y), Down (-y), Left (-x), Right (+x), per docs/world-model.md.
    assert coords == [(5, 6), (5, 4), (4, 5), (6, 5)]


def test_get_neighbors_corner_cell_returns_only_two(world: World) -> None:
    neighbors = world.get_neighbors(0, 0)
    coords = {(n.x, n.y) for n in neighbors}

    assert coords == {(0, 1), (1, 0)}


def test_get_neighbors_edge_cell_returns_only_three(world: World) -> None:
    neighbors = world.get_neighbors(0, 5)
    coords = {(n.x, n.y) for n in neighbors}

    assert coords == {(0, 6), (0, 4), (1, 5)}


def test_get_neighbors_excludes_diagonals(world: World) -> None:
    neighbors = world.get_neighbors(5, 5)
    coords = {(n.x, n.y) for n in neighbors}

    assert (6, 6) not in coords
    assert (4, 4) not in coords
    assert (6, 4) not in coords
    assert (4, 6) not in coords


def test_get_neighbors_on_single_cell_world_is_empty(tiny_world: World) -> None:
    assert tiny_world.get_neighbors(0, 0) == []


def test_get_neighbors_never_raises_for_out_of_bounds_source(world: World) -> None:
    # Per docs/world-api.md, get_neighbors has no documented Raises
    # section (unlike get_cell) -- an invalid source simply yields no
    # neighbors.
    assert world.get_neighbors(999, 999) == []
    assert world.get_neighbors(-1, -1) == []


def test_get_neighbors_never_raises_for_wrong_type_source(world: World) -> None:
    assert world.get_neighbors("5", 5) == []  # type: ignore[arg-type]
    assert world.get_neighbors(5, None) == []  # type: ignore[arg-type]


def test_get_neighbors_returns_cell_objects_reflecting_current_state(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=5, y=6, type="Tree"))

    neighbors = world.get_neighbors(5, 5)
    coords = {(n.x, n.y) for n in neighbors}

    assert (5, 6) not in coords
    assert coords == {(5, 4), (4, 5), (6, 5)}