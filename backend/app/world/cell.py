"""The Cell value object."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import CellType


@dataclass(frozen=True)
class Cell:
    """An immutable snapshot of a single grid position.

    Cell instances are read-only by design: docs/world-api.md requires
    that other modules never directly modify Grid, Cell, or other
    internal classes. Freezing the dataclass enforces that at runtime.

    Attributes:
        x: East-west coordinate, 0 <= x < world width.
        y: North-south coordinate, 0 <= y < world height.
        cell_type: The category this position currently belongs to.
    """

    x: int
    y: int
    cell_type: CellType