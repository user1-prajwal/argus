"""Enumerations for the ARGUS World module."""

from __future__ import annotations

from enum import Enum


class CellType(str, Enum):
    """The category a single grid cell belongs to.

    A cell's type is derived at query time from whichever world entity
    (if any) currently occupies that position. ``NO_FLY_ZONE`` is part of
    the Version 1 cell taxonomy per docs/world-model.md but has no
    corresponding ``add_*`` method in docs/world-api.md, so it cannot yet
    be produced by any public operation. It is kept in the enum for
    completeness and forward compatibility.
    """

    EMPTY = "Empty"
    OBSTACLE = "Obstacle"
    MISSION_ZONE = "MissionZone"
    CHARGING_STATION = "ChargingStation"
    SPAWN_POINT = "SpawnPoint"
    NO_FLY_ZONE = "NoFlyZone"