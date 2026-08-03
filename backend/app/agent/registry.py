"""The AgentRegistry class: the single source of truth for agent state.

AgentRegistry stores and updates Agent records. It performs no planning,
task allocation, or path-finding logic, and has no dependency on the
World module -- see docs/agent-model.md and docs/agent-api.md for the
full specification this module implements.
"""

from __future__ import annotations

from dataclasses import replace

from .agent import Agent
from .enums import AgentActivity, HealthStatus
from .exceptions import AgentNotFoundError, DuplicateAgentError


class AgentRegistry:
    """A collection of agents, keyed by id.

    Only the methods documented in docs/agent-api.md are public. Agent
    instances are immutable value objects; every state change goes
    through one of this class's update methods, which replace the
    stored Agent with a new instance rather than mutating it.

    AgentRegistry has no dependency on the World module. Keeping an
    agent's position in sync with the World's occupancy state is the
    responsibility of a future Simulation/Orchestrator module.
    """

    def __init__(self) -> None:
        """Create a new, empty agent registry."""
        self._agents: dict[str, Agent] = {}

    # ------------------------------------------------------------------
    # Public API (docs/agent-api.md, "Public API")
    # ------------------------------------------------------------------

    def add_agent(self, agent: Agent) -> None:
        """Register a new agent.

        Args:
            agent: The agent to add.

        Raises:
            TypeError: If agent is not an Agent instance.
            DuplicateAgentError: If an agent with this id already exists.
        """
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent instance")
        if agent.id in self._agents:
            raise DuplicateAgentError(f"Agent id '{agent.id}' already exists")
        self._agents[agent.id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent by id.

        Args:
            agent_id: Id of the agent to remove.

        Raises:
            TypeError: If agent_id is not a string.
            AgentNotFoundError: If no agent with this id exists.
        """
        if not isinstance(agent_id, str):
            raise TypeError("agent_id must be a string")
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent id '{agent_id}' does not exist")
        del self._agents[agent_id]

    def get_agent(self, agent_id: str) -> Agent:
        """Return the agent with the given id.

        Args:
            agent_id: Id of the agent to retrieve.

        Returns:
            The current Agent state.

        Raises:
            TypeError: If agent_id is not a string.
            AgentNotFoundError: If no agent with this id exists.
        """
        if not isinstance(agent_id, str):
            raise TypeError("agent_id must be a string")
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent id '{agent_id}' does not exist")
        return self._agents[agent_id]

    def update_position(self, agent_id: str, x: int, y: int) -> None:
        """Update an agent's position.

        Args:
            agent_id: Id of the agent to update.
            x: New east-west coordinate.
            y: New north-south coordinate.

        Raises:
            TypeError: If x or y is not an int.
            ValueError: If x or y is negative.
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        if not isinstance(x, int) or isinstance(x, bool):
            raise TypeError(f"x must be an int, got {type(x).__name__}")
        if not isinstance(y, int) or isinstance(y, bool):
            raise TypeError(f"y must be an int, got {type(y).__name__}")
        if x < 0 or y < 0:
            raise ValueError(f"Position ({x}, {y}) must have non-negative coordinates")
        self._agents[agent_id] = self._replace(agent, x=x, y=y)

    def update_battery(self, agent_id: str, battery_level: int) -> None:
        """Update an agent's battery level.

        Args:
            agent_id: Id of the agent to update.
            battery_level: New battery level, 0-100.

        Raises:
            TypeError: If battery_level is not an int.
            ValueError: If battery_level is outside 0-100.
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        if not isinstance(battery_level, int) or isinstance(battery_level, bool):
            raise TypeError(
                f"battery_level must be an int, got {type(battery_level).__name__}"
            )
        if not (0 <= battery_level <= 100):
            raise ValueError("battery_level must be between 0 and 100")
        self._agents[agent_id] = self._replace(agent, battery_level=battery_level)

    def update_health_status(self, agent_id: str, health_status: HealthStatus) -> None:
        """Update an agent's health status.

        Independent of activity -- see docs/agent-model.md, "Health
        Status".

        Args:
            agent_id: Id of the agent to update.
            health_status: New health status.

        Raises:
            TypeError: If health_status is not a HealthStatus.
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        if not isinstance(health_status, HealthStatus):
            raise TypeError(
                f"health_status must be a HealthStatus, got {type(health_status).__name__}"
            )
        self._agents[agent_id] = self._replace(agent, health_status=health_status)

    def update_activity(self, agent_id: str, activity: AgentActivity) -> None:
        """Update an agent's activity.

        Independent of health_status -- see docs/agent-model.md, "Agent
        Activity".

        Args:
            agent_id: Id of the agent to update.
            activity: New activity.

        Raises:
            TypeError: If activity is not an AgentActivity.
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        if not isinstance(activity, AgentActivity):
            raise TypeError(
                f"activity must be an AgentActivity, got {type(activity).__name__}"
            )
        self._agents[agent_id] = self._replace(agent, activity=activity)

    def assign_mission(self, agent_id: str, mission_id: str) -> None:
        """Set the mission an agent is currently associated with.

        Not validated against any Mission module, and not required to be
        consistent with activity -- see docs/agent-model.md, "Current
        Mission".

        Args:
            agent_id: Id of the agent to update.
            mission_id: Id of the mission to assign.

        Raises:
            TypeError: If mission_id is not a string.
            ValueError: If mission_id is empty.
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        if not isinstance(mission_id, str):
            raise TypeError(f"mission_id must be a string, got {type(mission_id).__name__}")
        if not mission_id:
            raise ValueError("mission_id must not be empty")
        self._agents[agent_id] = self._replace(agent, current_mission_id=mission_id)

    def clear_mission(self, agent_id: str) -> None:
        """Clear the mission an agent is currently associated with.

        Args:
            agent_id: Id of the agent to update.

        Raises:
            AgentNotFoundError: If no agent with this id exists.
        """
        agent = self.get_agent(agent_id)
        self._agents[agent_id] = self._replace(agent, current_mission_id=None)

    def list_agents(self) -> list[Agent]:
        """Return every registered agent.

        Returns:
            All registered agents, in no particular order.
        """
        return list(self._agents.values())

    def agent_summary(self) -> dict[str, int | dict[str, int]]:
        """Return aggregate counts describing the current registry state.

        Returns:
            A dict with keys "total" (int), "health_status" (a dict of
            counts keyed by each HealthStatus value, lowercased), and
            "activity" (a dict of counts keyed by each AgentActivity
            value, lowercased).
        """
        health_counts = {status.value.lower(): 0 for status in HealthStatus}
        activity_counts = {activity.value.lower(): 0 for activity in AgentActivity}
        for agent in self._agents.values():
            health_counts[agent.health_status.value.lower()] += 1
            activity_counts[agent.activity.value.lower()] += 1
        return {
            "total": len(self._agents),
            "health_status": health_counts,
            "activity": activity_counts,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _replace(agent: Agent, **changes: object) -> Agent:
        """Return a new Agent with the given fields replaced.

        Agent is immutable, so every update produces a new instance via
        dataclasses.replace() rather than mutating the stored one. This
        re-runs Agent.__post_init__ validation on the result.

        registered_at has init=False, so dataclasses.replace() would
        otherwise silently recompute it via its default_factory. It is
        explicitly restored here so an agent's original registration
        time is preserved across every update.
        """
        updated = replace(agent, **changes)
        object.__setattr__(updated, "registered_at", agent.registered_at)
        return updated