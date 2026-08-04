"""The Mission value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agent import Capability

from .enums import MissionPriority, MissionStatus


@dataclass(frozen=True)
class Mission:
    """An immutable snapshot of a single mission's state.

    A mission represents work that must be completed -- a search area,
    an inspection task, a delivery, or any other objective assigned to
    one or more agents. See docs/mission-model.md for the full
    specification.

    Attributes:
        id: Unique identifier for this mission.
        name: Human-readable name.
        description: Human-readable description of the work.
        priority: How urgent this mission is. Fixed at creation; there
            is no operation to change it afterward.
        status: Where this mission is in its lifecycle.
        target_cells: The non-empty set of (x, y) cells this mission
            covers. An independent representation, not the World
            Model's MissionZone. Fixed at creation.
        required_capabilities: The capabilities an agent needs to work
            this mission. Reuses the Capability enum from the Agent
            Model rather than defining a second one -- the one point
            of contact between the Mission Model and the Agent Model.
            Fixed at creation. Defaults to an empty frozenset.
        assigned_agent_ids: The ids of agents currently working this
            mission, stored as plain strings rather than Agent objects.
            Multiple agents may be assigned. Defaults to an empty
            frozenset.
        created_at: UTC timestamp of when this mission was created. Set
            automatically; cannot be supplied or changed by the caller.
    """

    id: str
    name: str
    description: str
    priority: MissionPriority
    status: MissionStatus
    target_cells: frozenset[tuple[int, int]]
    required_capabilities: frozenset[Capability] = field(default_factory=frozenset)
    assigned_agent_ids: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Mission id must not be empty")
        if not self.name:
            raise ValueError("Mission name must not be empty")
        if not self.description:
            raise ValueError("Mission description must not be empty")

        normalized_cells = frozenset(self.target_cells)
        if not normalized_cells:
            raise ValueError("Mission target_cells must not be empty")
        for x, y in normalized_cells:
            if x < 0 or y < 0:
                raise ValueError(
                    f"Mission target cell ({x}, {y}) must have non-negative coordinates"
                )
        object.__setattr__(self, "target_cells", normalized_cells)
        object.__setattr__(
            self, "required_capabilities", frozenset(self.required_capabilities)
        )
        object.__setattr__(
            self, "assigned_agent_ids", frozenset(self.assigned_agent_ids)
        )