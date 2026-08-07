"""The PlanningEngine class: matches available agents to pending missions.

PlanningEngine is the first ARGUS module that contains decision-making
logic. It reads World, Agent, and Mission state through their existing
public APIs and produces planning decisions, mutating Agent and Mission
state only through AgentRegistry's and MissionRegistry's existing public
methods. It never mutates World state, and it owns no persistent state of
its own -- see docs/planning-model.md and docs/planning-api.md for the
full specification this module implements.
"""

from __future__ import annotations

from app.agent import Agent, AgentActivity, AgentNotFoundError, AgentRegistry, HealthStatus
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.world import World

# Per docs/planning-model.md, "Plan": pending missions are considered
# highest priority first. Lower number = processed earlier.
_PRIORITY_ORDER: dict[MissionPriority, int] = {
    MissionPriority.CRITICAL: 0,
    MissionPriority.HIGH: 1,
    MissionPriority.MEDIUM: 2,
    MissionPriority.LOW: 3,
}

PlanningResult = dict[str, str | None]


def _is_available(agent: Agent) -> bool:
    """An agent is available when it is ONLINE and IDLE.

    See docs/planning-model.md, "Availability and Eligibility".
    """
    return agent.health_status is HealthStatus.ONLINE and agent.activity is AgentActivity.IDLE


def _is_eligible(agent: Agent, mission: Mission) -> bool:
    """An agent is eligible for a mission when it is available and its
    capabilities are a superset of the mission's required_capabilities.

    See docs/planning-model.md, "Availability and Eligibility".
    """
    return _is_available(agent) and mission.required_capabilities <= agent.capabilities


def _select_agent(candidates: list[Agent]) -> Agent | None:
    """Pick the most appropriate agent from a list of eligible candidates.

    Prefers higher battery_level, then lower id as a deterministic
    tie-break. Not a prediction of battery usage, and not a distance or
    path calculation -- see docs/planning-model.md, "Assignment
    Selection".

    Returns None if candidates is empty.
    """
    if not candidates:
        return None
    return min(candidates, key=lambda agent: (-agent.battery_level, agent.id))


class PlanningEngine:
    """Matches available agents to pending missions.

    A PlanningEngine is bound to one World, one AgentRegistry, and one
    MissionRegistry at construction. It holds no other state -- every
    call reads their current state and acts on it immediately.

    The Planning Engine does not own application state. Future modules
    such as a Simulation Engine may invoke it through this public API.

    Version 1's matching logic only reads from the Agent and Mission
    Models. It does not read from the World Model -- the dependency on
    World is accepted at construction for forward compatibility, not
    exercised by any Version 1 responsibility.
    """

    def __init__(self, world: World, agents: AgentRegistry, missions: MissionRegistry) -> None:
        """Create a Planning Engine bound to a specific World,
        AgentRegistry, and MissionRegistry.

        Args:
            world: The World this engine is associated with. Not read by
                any Version 1 responsibility.
            agents: The AgentRegistry to find available agents in and
                update agent activity through.
            missions: The MissionRegistry to find pending missions in and
                update mission status through.

        Raises:
            TypeError: If world, agents, or missions is not an instance
                of the expected type.
        """
        if not isinstance(world, World):
            raise TypeError(f"world must be a World instance, got {type(world).__name__}")
        if not isinstance(agents, AgentRegistry):
            raise TypeError(
                f"agents must be an AgentRegistry instance, got {type(agents).__name__}"
            )
        if not isinstance(missions, MissionRegistry):
            raise TypeError(
                f"missions must be a MissionRegistry instance, got {type(missions).__name__}"
            )
        self._world = world
        self._agents = agents
        self._missions = missions

    # ------------------------------------------------------------------
    # Public API (docs/planning-api.md, "Public API")
    # ------------------------------------------------------------------

    def plan(self) -> list[PlanningResult]:
        """Attempt to assign an agent to every pending mission.

        Considers every PENDING mission, highest priority first, and
        attempts to assign the most appropriate available agent to each.
        An agent successfully assigned during this call is no longer
        available for the remaining missions in the same call, since
        assignment updates its activity immediately.

        Version 1 assigns at most one agent per mission -- "no eligible
        agent" is a normal, non-error outcome, reported as
        assigned_agent_id: None.

        Returns:
            One result per pending mission considered, in the order
            processed: {"mission_id": ..., "assigned_agent_id": ... or
            None}.
        """
        pending = [
            mission
            for mission in self._missions.list_missions()
            if mission.status is MissionStatus.PENDING
        ]
        pending.sort(key=lambda mission: _PRIORITY_ORDER[mission.priority])
        return [self._attempt_assignment(mission) for mission in pending]

    def assign_mission(self, mission_id: str) -> PlanningResult:
        """Attempt to assign the most appropriate available agent to a
        single mission.

        Only missions in the PENDING state are eligible for assignment.
        If the mission is in any other state, no assignment is
        performed and assigned_agent_id is None -- this is not an
        error. This does not release any agent the mission may already
        have; use replan() for that.

        Args:
            mission_id: Id of the mission to assign an agent to.

        Returns:
            {"mission_id": ..., "assigned_agent_id": ... or None}.

        Raises:
            MissionNotFoundError: If no mission with this id exists.
        """
        mission = self._missions.get_mission(mission_id)
        if mission.status is not MissionStatus.PENDING:
            return {"mission_id": mission.id, "assigned_agent_id": None}
        return self._attempt_assignment(mission)

    def replan(self, mission_id: str) -> PlanningResult:
        """Release a mission's current assignment, if any, and attempt a
        fresh assignment.

        Reverts any previously assigned agent to activity IDLE with no
        current mission, and the mission itself to status PENDING, then
        attempts assignment exactly like assign_mission().

        Args:
            mission_id: Id of the mission to replan.

        Returns:
            {"mission_id": ..., "assigned_agent_id": ... or None}.

        Raises:
            MissionNotFoundError: If no mission with this id exists.
        """
        mission = self._missions.get_mission(mission_id)
        self._release(mission)
        mission = self._missions.get_mission(mission_id)
        return self._attempt_assignment(mission)

    def planning_summary(self) -> dict[str, int]:
        """Return aggregate counts describing the current planning picture.

        Returns:
            A dict with keys "pending_missions", "available_agents",
            "assignable_missions" (pending missions with at least one
            currently eligible agent), and "unassignable_missions" (the
            rest).
        """
        pending_missions = [
            mission
            for mission in self._missions.list_missions()
            if mission.status is MissionStatus.PENDING
        ]
        agents = self._agents.list_agents()
        available_agents = [agent for agent in agents if _is_available(agent)]

        assignable = sum(
            1
            for mission in pending_missions
            if any(_is_eligible(agent, mission) for agent in agents)
        )

        return {
            "pending_missions": len(pending_missions),
            "available_agents": len(available_agents),
            "assignable_missions": assignable,
            "unassignable_missions": len(pending_missions) - assignable,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _attempt_assignment(self, mission: Mission) -> PlanningResult:
        """Try to assign one eligible agent to a mission.

        Callers must ensure mission.status is MissionStatus.PENDING
        before calling this -- it does not check status itself.
        """
        candidates = [
            agent for agent in self._agents.list_agents() if _is_eligible(agent, mission)
        ]
        selected = _select_agent(candidates)
        if selected is None:
            return {"mission_id": mission.id, "assigned_agent_id": None}

        self._missions.assign_agents(mission.id, {selected.id})
        self._missions.update_status(mission.id, MissionStatus.ASSIGNED)
        self._agents.assign_mission(selected.id, mission.id)
        self._agents.update_activity(selected.id, AgentActivity.ASSIGNED)

        return {"mission_id": mission.id, "assigned_agent_id": selected.id}

    def _release(self, mission: Mission) -> None:
        """Release a mission's current assignment, if any.

        Reverts every currently assigned agent to activity IDLE with no
        current mission, then reverts the mission itself to status
        PENDING with no assigned agents. Agents that no longer exist in
        the AgentRegistry are skipped rather than raising.
        """
        for agent_id in mission.assigned_agent_ids:
            try:
                agent = self._agents.get_agent(agent_id)
            except AgentNotFoundError:
                continue
            self._agents.update_activity(agent.id, AgentActivity.IDLE)
            self._agents.clear_mission(agent.id)
        self._missions.clear_agents(mission.id)
        self._missions.update_status(mission.id, MissionStatus.PENDING)