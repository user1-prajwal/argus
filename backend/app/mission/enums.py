"""Enumerations for the ARGUS Mission module."""

from __future__ import annotations

from enum import Enum


class MissionPriority(str, Enum):
    """How urgent a mission is.

    Fixed at creation in Version 1 -- see docs/mission-model.md,
    "Priority". Does not affect how missions are stored or queried.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MissionStatus(str, Enum):
    """Where a mission is in its lifecycle.

    See docs/mission-model.md, "Status". No particular transition order
    is enforced.
    """

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"