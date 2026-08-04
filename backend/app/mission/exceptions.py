"""Custom exceptions for the ARGUS Mission module."""

from __future__ import annotations


class MissionError(Exception):
    """Base class for all Mission module errors."""


class DuplicateMissionError(MissionError):
    """Raised when adding a mission whose id is already registered."""


class MissionNotFoundError(MissionError):
    """Raised when looking up, updating, or removing a mission id that
    is not registered.
    """