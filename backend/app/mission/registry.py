"""The MissionRegistry class: the single source of truth for mission
state.

MissionRegistry stores and updates Mission records. It performs no
planning, task allocation, or scheduling, and has no dependency on the
World module or the Agent module beyond reusing the Capability enum as
a shared vocabulary type -- see docs/mission-model.md and
docs/mission-api.md for the full specification this module implements.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from .enums import MissionPriority, MissionStatus
from .exceptions import DuplicateMissionError, MissionNotFoundError
from .mission import Mission


class MissionRegistry:
    """A collection of missions, keyed by id.

    Only the methods documented in docs/mission-api.md are public.
    Mission instances are immutable value objects; every state change
    goes through one of this class's update methods, which replace the
    stored Mission with a new instance rather than mutating it.

    MissionRegistry has no dependency on the World module, and no
    dependency on the Agent module beyond the Capability enum type.
    Matching agents to missions, and keeping assigned_agent_ids
    consistent with a live Agent registry, is the responsibility of a
    future Planning Engine.
    """

    def __init__(self) -> None:
        """Create a new, empty mission registry."""
        self._missions: dict[str, Mission] = {}

    # ------------------------------------------------------------------
    # Public API (docs/mission-api.md, "Public API")
    # ------------------------------------------------------------------

    def add_mission(self, mission: Mission) -> None:
        """Register a new mission.

        Args:
            mission: The mission to add.

        Raises:
            TypeError: If mission is not a Mission instance.
            DuplicateMissionError: If a mission with this id already
                exists.
        """
        if not isinstance(mission, Mission):
            raise TypeError("mission must be a Mission instance")
        if mission.id in self._missions:
            raise DuplicateMissionError(f"Mission id '{mission.id}' already exists")
        self._missions[mission.id] = mission

    def remove_mission(self, mission_id: str) -> None:
        """Remove a mission by id.

        Args:
            mission_id: Id of the mission to remove.

        Raises:
            TypeError: If mission_id is not a string.
            MissionNotFoundError: If no mission with this id exists.
        """
        if not isinstance(mission_id, str):
            raise TypeError("mission_id must be a string")
        if mission_id not in self._missions:
            raise MissionNotFoundError(f"Mission id '{mission_id}' does not exist")
        del self._missions[mission_id]

    def get_mission(self, mission_id: str) -> Mission:
        """Return the mission with the given id.

        Args:
            mission_id: Id of the mission to retrieve.

        Returns:
            The current Mission state.

        Raises:
            TypeError: If mission_id is not a string.
            MissionNotFoundError: If no mission with this id exists.
        """
        if not isinstance(mission_id, str):
            raise TypeError("mission_id must be a string")
        if mission_id not in self._missions:
            raise MissionNotFoundError(f"Mission id '{mission_id}' does not exist")
        return self._missions[mission_id]

    def update_status(self, mission_id: str, status: MissionStatus) -> None:
        """Update a mission's status.

        No particular transition order is enforced -- see
        docs/mission-model.md, "Status".

        Args:
            mission_id: Id of the mission to update.
            status: New status.

        Raises:
            TypeError: If status is not a MissionStatus.
            MissionNotFoundError: If no mission with this id exists.
        """
        mission = self.get_mission(mission_id)
        if not isinstance(status, MissionStatus):
            raise TypeError(f"status must be a MissionStatus, got {type(status).__name__}")
        self._missions[mission_id] = self._replace(mission, status=status)

    def assign_agents(self, mission_id: str, agent_ids: Iterable[str]) -> None:
        """Replace the mission's assigned agent ids with the given set.

        This replaces the entire assigned_agent_ids set -- see
        docs/mission-api.md, "Assign Agents". To add or remove specific
        agents, pass the full desired set of ids. Not validated against
        any Agent registry -- see docs/mission-model.md, "Assigned
        Agents".

        Args:
            mission_id: Id of the mission to update.
            agent_ids: The complete new set of assigned agent ids.

        Raises:
            TypeError: If agent_ids is a single string, is not
                iterable, or contains a non-string element.
            ValueError: If any agent id is empty.
            MissionNotFoundError: If no mission with this id exists.
        """
        mission = self.get_mission(mission_id)
        if isinstance(agent_ids, str):
            raise TypeError("agent_ids must be an iterable of strings, not a single string")
        try:
            candidate_ids = list(agent_ids)
        except TypeError as exc:
            raise TypeError("agent_ids must be an iterable of strings") from exc
        for agent_id in candidate_ids:
            if not isinstance(agent_id, str):
                raise TypeError(
                    f"agent_ids must contain only strings, got {type(agent_id).__name__}"
                )
            if not agent_id:
                raise ValueError("agent_ids must not contain empty strings")
        self._missions[mission_id] = self._replace(
            mission, assigned_agent_ids=frozenset(candidate_ids)
        )

    def clear_agents(self, mission_id: str) -> None:
        """Clear all agents currently assigned to a mission.

        Equivalent to assign_agents(mission_id, frozenset()).

        Args:
            mission_id: Id of the mission to update.

        Raises:
            MissionNotFoundError: If no mission with this id exists.
        """
        mission = self.get_mission(mission_id)
        self._missions[mission_id] = self._replace(mission, assigned_agent_ids=frozenset())

    def list_missions(self) -> list[Mission]:
        """Return every registered mission.

        Returns:
            All registered missions, in no particular order.
        """
        return list(self._missions.values())

    def mission_summary(self) -> dict[str, int | dict[str, int]]:
        """Return aggregate counts describing the current registry state.

        Returns:
            A dict with keys "total" (int), "status" (a dict of counts
            keyed by each MissionStatus value, lowercased), and
            "priority" (a dict of counts keyed by each MissionPriority
            value, lowercased).
        """
        status_counts = {status.value.lower(): 0 for status in MissionStatus}
        priority_counts = {priority.value.lower(): 0 for priority in MissionPriority}
        for mission in self._missions.values():
            status_counts[mission.status.value.lower()] += 1
            priority_counts[mission.priority.value.lower()] += 1
        return {
            "total": len(self._missions),
            "status": status_counts,
            "priority": priority_counts,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _replace(mission: Mission, **changes: object) -> Mission:
        """Return a new Mission with the given fields replaced.

        Mission is immutable, so every update produces a new instance
        via dataclasses.replace() rather than mutating the stored one.
        This re-runs Mission.__post_init__ validation on the result.

        created_at has init=False, so dataclasses.replace() would
        otherwise silently recompute it via its default_factory. It is
        explicitly restored here so a mission's original creation time
        is preserved across every update.
        """
        updated = replace(mission, **changes)
        object.__setattr__(updated, "created_at", mission.created_at)
        return updated