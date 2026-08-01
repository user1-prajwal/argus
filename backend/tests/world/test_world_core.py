"""Tests for World construction, properties, and get_cell/is_walkable
baseline behavior on an empty world."""

from __future__ import annotations

import pytest

from app.world import Cell, CellType, World


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------


def test_construct_valid_world() -> None:
    w = World(width=100, height=100)

    assert w.width == 100
    assert w.height == 100


@pytest.mark.parametrize("width,height", [(0, 10), (10, 0), (-1, 10), (10, -1)])
def test_construct_rejects_non_positive_dimensions(width: int, height: int) -> None:
    with pytest.raises(ValueError):
        World(width=width, height=height)


@pytest.mark.parametrize("width,height", [(1.5, 10), (10, "10"), (None, 10)])
def test_construct_rejects_non_int_dimensions(width: object, height: object) -> None:
    with pytest.raises(TypeError):
        World(width=width, height=height)  # type: ignore[arg-type]


def test_construct_rejects_bool_dimensions() -> None:
    # bool is a subclass of int in Python; must not be silently accepted.
    with pytest.raises(TypeError):
        World(width=True, height=10)


def test_width_height_are_read_only() -> None:
    w = World(width=5, height=5)

    with pytest.raises(AttributeError):
        w.width = 10  # type: ignore[misc]


# ----------------------------------------------------------------------
# get_cell
# ----------------------------------------------------------------------


def test_get_cell_returns_empty_by_default(world: World) -> None:
    cell = world.get_cell(0, 0)

    assert cell == Cell(x=0, y=0, cell_type=CellType.EMPTY)


def test_get_cell_raises_value_error_outside_world(world: World) -> None:
    with pytest.raises(ValueError):
        world.get_cell(10, 0)  # width is 10, so x=10 is out of range

    with pytest.raises(ValueError):
        world.get_cell(0, 10)

    with pytest.raises(ValueError):
        world.get_cell(-1, 0)

    with pytest.raises(ValueError):
        world.get_cell(0, -1)


def test_get_cell_raises_type_error_for_non_int_coordinates(world: World) -> None:
    with pytest.raises(TypeError):
        world.get_cell(1.5, 0)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        world.get_cell(0, "0")  # type: ignore[arg-type]


def test_get_cell_at_corners_of_world(world: World) -> None:
    assert world.get_cell(0, 0).cell_type is CellType.EMPTY
    assert world.get_cell(9, 9).cell_type is CellType.EMPTY  # width=height=10


def test_get_cell_on_single_cell_world(tiny_world: World) -> None:
    assert tiny_world.get_cell(0, 0).cell_type is CellType.EMPTY

    with pytest.raises(ValueError):
        tiny_world.get_cell(1, 0)


# ----------------------------------------------------------------------
# is_walkable baseline (obstacle/occupied-specific cases live in their
# own test files)
# ----------------------------------------------------------------------


def test_is_walkable_true_on_empty_cell(world: World) -> None:
    assert world.is_walkable(5, 5) is True


def test_is_walkable_false_outside_world(world: World) -> None:
    assert world.is_walkable(10, 0) is False
    assert world.is_walkable(0, 10) is False
    assert world.is_walkable(-1, 0) is False
    assert world.is_walkable(0, -1) is False


def test_is_walkable_never_raises_for_wrong_type(world: World) -> None:
    # Per docs/world-api.md, is_walkable always returns a bool.
    assert world.is_walkable("0", 0) is False  # type: ignore[arg-type]
    assert world.is_walkable(0, None) is False  # type: ignore[arg-type]
    assert world.is_walkable(1.5, 1.5) is False  # type: ignore[arg-type]
    assert world.is_walkable(True, 0) is False


def test_is_walkable_on_single_cell_world(tiny_world: World) -> None:
    assert tiny_world.is_walkable(0, 0) is True
    assert tiny_world.is_walkable(1, 0) is False
    assert tiny_world.is_walkable(-1, 0) is False