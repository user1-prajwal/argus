"""Custom exceptions for the ARGUS World module."""

from __future__ import annotations


class WorldError(Exception):
    """Base class for all World module errors."""


class DuplicateObstacleError(WorldError):
    """Raised when adding an obstacle whose id is already registered."""


class ObstacleNotFoundError(WorldError):
    """Raised when removing an obstacle id that is not registered."""


class DuplicateSpawnPointError(WorldError):
    """Raised when adding a spawn point whose id is already registered."""


class DuplicateChargingStationError(WorldError):
    """Raised when adding a charging station whose id is already registered."""


class DuplicateMissionZoneError(WorldError):
    """Raised when adding a mission zone whose id is already registered."""
    