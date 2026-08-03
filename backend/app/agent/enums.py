"""Enumerations for the ARGUS Agent module."""

from __future__ import annotations

from enum import Enum


class PlatformType(str, Enum):
    """The kind of physical platform an agent represents.

    Descriptive only in Version 1 -- see docs/agent-model.md, "Agent
    Identity". Does not affect validation or behavior.
    """

    DRONE = "DRONE"
    GROUND_ROBOT = "GROUND_ROBOT"
    AUTONOMOUS_VEHICLE = "AUTONOMOUS_VEHICLE"
    MARINE_VEHICLE = "MARINE_VEHICLE"


class Capability(str, Enum):
    """A sensing or functional capability an agent may have.

    Descriptive only in Version 1 -- see docs/agent-model.md,
    "Capabilities". Does not affect movement or validation behavior.
    """

    THERMAL_CAMERA = "thermal_camera"
    STANDARD_CAMERA = "standard_camera"
    LIDAR = "lidar"
    GPS = "gps"


class HealthStatus(str, Enum):
    """Whether an agent is operating normally.

    Independent of AgentActivity -- see docs/agent-model.md, "Health
    Status".
    """

    ONLINE = "ONLINE"
    FAILED = "FAILED"
    OFFLINE = "OFFLINE"


class AgentActivity(str, Enum):
    """What an agent is currently doing.

    Independent of HealthStatus -- see docs/agent-model.md, "Agent
    Activity".
    """

    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    EXECUTING_MISSION = "EXECUTING_MISSION"
    RETURNING = "RETURNING"
    CHARGING = "CHARGING"