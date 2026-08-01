"""Tests for app.world.cell.Cell."""

from __future__ import annotations

import dataclasses

import pytest

from app.world import Cell, CellType


def test_cell_stores_fields() -> None:
    cell = Cell(x=3, y=4, cell_type=CellType.EMPTY)

    assert cell.x == 3
    assert cell.y == 4
    assert cell.cell_type is CellType.EMPTY


def test_cell_is_immutable() -> None:
    cell = Cell(x=0, y=0, cell_type=CellType.EMPTY)

    with pytest.raises(dataclasses.FrozenInstanceError):
        cell.x = 99  # type: ignore[misc]


def test_cell_equality_is_value_based() -> None:
    a = Cell(x=1, y=1, cell_type=CellType.OBSTACLE)
    b = Cell(x=1, y=1, cell_type=CellType.OBSTACLE)
    c = Cell(x=1, y=2, cell_type=CellType.OBSTACLE)

    assert a == b
    assert a != c