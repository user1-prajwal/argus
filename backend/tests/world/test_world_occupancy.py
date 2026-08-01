"""Tests for World's internal occupancy mechanism.

These hooks (``_occupy_cell`` / ``_release_cell`` / ``_is_occupied``) are
private and reserved for a future Agent module -- see docs/world-api.md,
"Only these methods are public. Everything else should be private." They
are still exercised directly here so that ``is_walkable``'s documented
"occupied" condition is verified as real behavior rather than dead code.
"""

from __future__ import annotations

import pytest

from app.world import Obstacle, World


def test_occupy_cell_makes_it_not_walkable(world: World) -> None:
    assert world.is_walkable(3, 3) is True

    world._occupy_cell(3, 3)

    assert world.is_walkable(3, 3) is False
    assert world._is_occupied(3, 3) is True


def test_release_cell_restores_walkability(world: World) -> None:
    world._occupy_cell(3, 3)
    world._release_cell(3, 3)

    assert world.is_walkable(3, 3) is True
    assert world._is_occupied(3, 3) is False


def test_release_cell_on_unoccupied_cell_is_a_no_op(world: World) -> None:
    world._release_cell(3, 3)  # must not raise

    assert world._is_occupied(3, 3) is False


def test_occupy_cell_twice_raises(world: World) -> None:
    world._occupy_cell(3, 3)

    with pytest.raises(ValueError):
        world._occupy_cell(3, 3)


def test_occupy_obstacle_cell_raises(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Tree"))

    with pytest.raises(ValueError):
        world._occupy_cell(2, 2)


def test_occupy_cell_out_of_bounds_raises(world: World) -> None:
    with pytest.raises(ValueError):
        world._occupy_cell(999, 999)


def test_occupy_cell_wrong_type_raises(world: World) -> None:
    with pytest.raises(TypeError):
        world._occupy_cell("3", 3)  # type: ignore[arg-type]


def test_occupied_cell_excluded_from_neighbors(world: World) -> None:
    world._occupy_cell(5, 6)

    neighbors = world.get_neighbors(5, 5)
    coords = {(n.x, n.y) for n in neighbors}

    assert (5, 6) not in coords