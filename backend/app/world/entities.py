"""Immutable value objects that can be placed into the World.

None of these classes contain behavior beyond constructor validation. They
only describe data, matching the World Model's design principle that the
module never performs planning or business logic (see
docs/world-model.md, "Design Principles").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Obstacle:
    """A single obstacle occupying one grid cell.

    Attributes:
        id: Unique identifier for this obstacle.
        x: East-west coordinate of the obstacle.
        y: North-south coordinate of the obstacle.
        type: Descriptive label only (e.g. "Building", "Tree", "Water",
            "Mountain", "Wall"). Purely informational in Version 1 -- every
            obstacle, regardless of type, is equally non-walkable.
    """

    id: str
    x: int
    y: int
    type: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Obstacle id must not be empty")
        if not self.type:
            raise ValueError("Obstacle type must not be empty")
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"Obstacle position ({self.x}, {self.y}) must have "
                "non-negative coordinates"
            )


@dataclass(frozen=True)
class SpawnPoint:
    """A location where agents enter the world.

    Attributes:
        id: Unique identifier for this spawn point.
        x: East-west coordinate of the spawn point.
        y: North-south coordinate of the spawn point.
    """

    id: str
    x: int
    y: int

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("SpawnPoint id must not be empty")
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"SpawnPoint position ({self.x}, {self.y}) must have "
                "non-negative coordinates"
            )


@dataclass(frozen=True)
class ChargingStation:
    """A location where agents can recharge.

    Version 1 assumes instant charging, so ``occupied_slots`` is stored
    data only -- the World module applies no charging-time business logic
    to it.

    Attributes:
        id: Unique identifier for this charging station.
        x: East-west coordinate of the charging station.
        y: North-south coordinate of the charging station.
        capacity: Maximum number of agents that can occupy this station
            at once. Must be a positive integer.
        occupied_slots: Number of slots currently in use. Defaults to 0.
    """

    id: str
    x: int
    y: int
    capacity: int
    occupied_slots: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("ChargingStation id must not be empty")
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"ChargingStation position ({self.x}, {self.y}) must have "
                "non-negative coordinates"
            )
        if self.capacity <= 0:
            raise ValueError("ChargingStation capacity must be a positive integer")
        if not (0 <= self.occupied_slots <= self.capacity):
            raise ValueError(
                "ChargingStation occupied_slots must be between 0 and capacity"
            )


@dataclass(frozen=True)
class MissionZone:
    """An area, expressed as an explicit set of grid cells, assigned to a mission.

    Version 1 represents zone shape as an explicit list of cells rather
    than a polygon, keeping overlap and containment checks simple,
    deterministic, and easy to validate.

    Attributes:
        id: Unique identifier for this mission zone.
        name: Human-readable name.
        priority: Relative priority of this zone. No fixed range is
            enforced by the World module.
        cells: The non-empty set of (x, y) grid cells that make up this
            zone. Normalized to a frozenset regardless of the iterable
            passed in.
        mission_id: Identifier of the mission this zone belongs to. A
            single mission may own multiple mission zones.
    """

    id: str
    name: str
    priority: int
    cells: frozenset[tuple[int, int]]
    mission_id: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("MissionZone id must not be empty")
        if not self.name:
            raise ValueError("MissionZone name must not be empty")
        if not self.mission_id:
            raise ValueError("MissionZone mission_id must not be empty")

        normalized_cells = frozenset(self.cells)
        if not normalized_cells:
            raise ValueError("MissionZone cells must not be empty")
        for x, y in normalized_cells:
            if x < 0 or y < 0:
                raise ValueError(
                    f"MissionZone cell ({x}, {y}) must have non-negative "
                    "coordinates"
                )
        # cells must be a frozenset; normalize whatever iterable was
        # passed in. Required because the dataclass is frozen.
        object.__setattr__(self, "cells", normalized_cells)