"""The Agent value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .enums import AgentActivity, Capability, HealthStatus, PlatformType


@dataclass(frozen=True)
class Agent:
    """An immutable snapshot of a single autonomous agent's state.

    A drone is only one example of an agent -- the same class represents
    ground robots, autonomous vehicles, and future platform types. See
    docs/agent-model.md for the full specification.

    Attributes:
        id: Unique identifier for this agent.
        platform_type: The kind of physical platform this agent
            represents. Descriptive only in Version 1; does not affect
            validation or behavior.
        x: East-west coordinate. Not validated against any world's
            width -- the Agent module has no dependency on the World
            module.
        y: North-south coordinate. Not validated against any world's
            height.
        battery_level: Current battery level, 0-100.
        health_status: Whether the agent is operating normally.
            Independent of activity.
        activity: What the agent is currently doing. Independent of
            health_status.
        capabilities: The sensing/functional capabilities this agent
            has. Fixed at registration; there is no operation to change
            it afterward.
        current_mission_id: Id of the mission this agent is currently
            associated with, or None if unassigned. Not validated
            against any Mission module, and not required to be
            consistent with activity.
        registered_at: UTC timestamp of when this agent was created. Set
            automatically; cannot be supplied or changed by the caller.
    """

    id: str
    platform_type: PlatformType
    x: int
    y: int
    battery_level: int
    health_status: HealthStatus
    activity: AgentActivity
    capabilities: frozenset[Capability]
    current_mission_id: str | None = None
    registered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Agent id must not be empty")
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"Agent position ({self.x}, {self.y}) must have non-negative coordinates"
            )
        if not (0 <= self.battery_level <= 100):
            raise ValueError("battery_level must be between 0 and 100")
        if self.current_mission_id is not None and not self.current_mission_id:
            raise ValueError("current_mission_id must not be an empty string")
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))