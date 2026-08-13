"""The SimulationEngine class: advances a running multi-agent simulation.

SimulationEngine connects World, Agent, Mission, and Path Planner into a
running simulation. It reads missions that are already ASSIGNED (by
whoever calls the Planning Engine externally), computes routes through
Path Planner, and advances agents one cell per tick -- draining battery,
respecting obstacles and occupied cells, and transitioning Mission and
Agent state as execution completes, fails, or waits.

SimulationEngine never decides which agent is assigned to which mission
(the Planning Engine's job) and never computes a route itself (the Path
Planner's job) -- see docs/simulation-model.md and docs/simulation-api.md
for the full specification this module implements.

This is a simulated software coordination layer, not a real drone/robot
control system.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.agent import Agent, AgentActivity, AgentNotFoundError, AgentRegistry, HealthStatus
from app.mission import Mission, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner, Route
from app.world import World

# Battery cost of a single move (one cell-to-cell step). Fixed and
# deterministic in Version 1 -- see docs/simulation-model.md, "Battery
# Model".
_MOVE_COST = 1

Position = tuple[int, int]
StepResult = dict[str, "int | list[str]"]


@dataclass(frozen=True)
class _Execution:
    """Internal bookkeeping for one actively-tracked agent.

    Not part of the public API -- see docs/simulation-model.md,
    "Simulation State".

    Attributes:
        mission_id: The mission this agent is working, or None while
            returning (the mission is already resolved by then).
        route: The route currently being followed, or None if a route
            still needs to be (re)computed -- see "_retry_route".
        progress: Index into route.cells; route.cells[progress] is the
            agent's current position. Meaningless while route is None.
        launch_position: Where the agent started before its outbound
            trip, and therefore where it returns to.
    """

    mission_id: str | None
    route: Route | None
    progress: int
    launch_position: Position


class SimulationEngine:
    """Advances a multi-agent simulation, one tick at a time.

    A SimulationEngine is bound to one World, one AgentRegistry, one
    MissionRegistry, and one PathPlanner at construction. Its only
    persistent state is its own execution bookkeeping (the current tick,
    and which route each actively-tracked agent is following) -- it
    never stores World, Agent, or Mission data itself.

    SimulationEngine does not depend on the Planning Engine and never
    assigns an agent to a mission. It only acts on missions that are
    already ASSIGNED.
    """

    def __init__(
        self,
        world: World,
        agents: AgentRegistry,
        missions: MissionRegistry,
        path_planner: PathPlanner,
    ) -> None:
        """Create a Simulation Engine bound to specific World, Agent,
        Mission, and Path Planner instances, starting at tick 0.

        Args:
            world: The World agents move through.
            agents: The AgentRegistry to read and update agent state in.
            missions: The MissionRegistry to read and update mission
                state in.
            path_planner: The PathPlanner used to compute every route.

        Raises:
            TypeError: If any argument is not an instance of the
                expected type.
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
        if not isinstance(path_planner, PathPlanner):
            raise TypeError(
                f"path_planner must be a PathPlanner instance, got {type(path_planner).__name__}"
            )

        self._world = world
        self._agents = agents
        self._missions = missions
        self._path_planner = path_planner

        self._tick = 0
        self._executions: dict[str, _Execution] = {}

    # ------------------------------------------------------------------
    # Public API (docs/simulation-api.md, "Public API")
    # ------------------------------------------------------------------

    def step(self) -> StepResult:
        """Advance the simulation by one tick.

        Newly ASSIGNED missions are picked up this tick (their agent
        does not move until the next tick -- see
        docs/simulation-model.md, "Execution Lifecycle": "Each
        subsequent tick, the agent advances"). Every agent already
        under active execution before this call advances by one cell.

        Returns:
            {"tick": int, "moved": [...], "waiting": [...],
            "completed_missions": [...], "failed_missions": [...],
            "returned_home": [...]}.
        """
        result: StepResult = {
            "tick": self._tick,
            "moved": [],
            "waiting": [],
            "completed_missions": [],
            "failed_missions": [],
            "returned_home": [],
        }

        already_tracked = list(self._executions.keys())
        self._pick_up_assigned_missions(result)

        for agent_id in already_tracked:
            if agent_id in self._executions:
                self._advance_one(agent_id, result)

        self._tick += 1
        return result

    def simulation_summary(self) -> dict[str, int]:
        """Return aggregate counts describing the current simulation state.

        Computed live from current World, Agent, and Mission state at
        call time -- see docs/simulation-api.md, "Simulation Summary".

        Returns:
            {"tick": int, "agents_executing": int,
            "agents_returning": int, "missions_in_progress": int,
            "missions_completed": int, "missions_failed": int}.
        """
        agents = self._agents.list_agents()
        missions = self._missions.list_missions()

        return {
            "tick": self._tick,
            "agents_executing": sum(
                1 for agent in agents if agent.activity is AgentActivity.EXECUTING_MISSION
            ),
            "agents_returning": sum(
                1 for agent in agents if agent.activity is AgentActivity.RETURNING
            ),
            "missions_in_progress": sum(
                1 for mission in missions if mission.status is MissionStatus.IN_PROGRESS
            ),
            "missions_completed": sum(
                1 for mission in missions if mission.status is MissionStatus.COMPLETED
            ),
            "missions_failed": sum(
                1 for mission in missions if mission.status is MissionStatus.FAILED
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers -- picking up newly ASSIGNED missions
    # ------------------------------------------------------------------

    def _pick_up_assigned_missions(self, result: StepResult) -> None:
        """Begin executing every mission with status ASSIGNED."""
        for mission in self._missions.list_missions():
            if mission.status is MissionStatus.ASSIGNED:
                self._begin_execution(mission, result)

    def _begin_execution(self, mission: Mission, result: StepResult) -> None:
        """Attempt to begin executing one newly-ASSIGNED mission.

        Runs the round-trip battery check (docs/simulation-model.md,
        "Battery Model"). On success, Mission becomes IN_PROGRESS and
        Agent becomes EXECUTING_MISSION. On failure, Mission becomes
        FAILED and the agent (if found) is released back to IDLE.
        """
        agent_id = next(iter(mission.assigned_agent_ids), None)
        if agent_id is None:
            self._fail_mission(mission, None, result)
            return

        try:
            agent = self._agents.get_agent(agent_id)
        except AgentNotFoundError:
            self._fail_mission(mission, None, result)
            return

        target = self._nearest_target_cell(agent, mission)
        outbound = self._path_planner.find_path(agent.x, agent.y, target[0], target[1])
        if outbound is None:
            self._fail_mission(mission, agent, result)
            return

        return_route = self._path_planner.find_path(target[0], target[1], agent.x, agent.y)
        if return_route is None or agent.battery_level < outbound.length + return_route.length:
            self._fail_mission(mission, agent, result)
            return

        self._missions.update_status(mission.id, MissionStatus.IN_PROGRESS)
        self._agents.update_activity(agent.id, AgentActivity.EXECUTING_MISSION)
        self._world._occupy_cell(agent.x, agent.y)
        execution = _Execution(
            mission_id=mission.id,
            route=outbound,
            progress=0,
            launch_position=(agent.x, agent.y),
        )
        if outbound.length == 0:
            # Agent is already standing on the target cell -- there is
            # no move to make before arriving, so resolve immediately
            # rather than tracking an execution with nowhere left to
            # advance to.
            self._handle_arrival(agent.id, execution, result)
        else:
            self._executions[agent.id] = execution

    def _fail_mission(self, mission: Mission, agent: Agent | None, result: StepResult) -> None:
        """Mark a mission FAILED and release its agent (if any) to IDLE."""
        self._missions.update_status(mission.id, MissionStatus.FAILED)
        if agent is not None:
            self._agents.update_activity(agent.id, AgentActivity.IDLE)
            self._agents.clear_mission(agent.id)
        result["failed_missions"].append(mission.id)

    def _nearest_target_cell(self, agent: Agent, mission: Mission) -> Position:
        """Pick the mission target cell closest to the agent by Manhattan
        distance, breaking ties by (x, y) for determinism.

        Version 1 uses this straight-line pre-filter rather than
        comparing actual Path Planner costs for every candidate cell --
        see docs/simulation-model.md, "Responsibilities".
        """
        return min(
            mission.target_cells,
            key=lambda cell: (abs(cell[0] - agent.x) + abs(cell[1] - agent.y), cell[0], cell[1]),
        )

    # ------------------------------------------------------------------
    # Private helpers -- per-tick movement
    # ------------------------------------------------------------------

    def _advance_one(self, agent_id: str, result: StepResult) -> None:
        """Advance one actively-tracked agent by at most one cell."""
        execution = self._executions[agent_id]

        try:
            agent = self._agents.get_agent(agent_id)
        except AgentNotFoundError:
            self._executions.pop(agent_id, None)
            return

        if agent.health_status is not HealthStatus.ONLINE:
            self._abort_due_to_health(agent, execution, result)
            return

        if execution.route is None:
            self._retry_route(agent, execution, result)
            return

        next_index = execution.progress + 1
        next_cell = execution.route.cells[next_index]

        if not self._world.is_walkable(*next_cell):
            result["waiting"].append(agent_id)
            return

        self._world._release_cell(agent.x, agent.y)
        self._world._occupy_cell(*next_cell)
        self._agents.update_position(agent_id, next_cell[0], next_cell[1])
        self._agents.update_battery(agent_id, agent.battery_level - _MOVE_COST)
        result["moved"].append(agent_id)

        if next_index == len(execution.route.cells) - 1:
            self._handle_arrival(agent_id, execution, result)
        else:
            self._executions[agent_id] = replace(execution, progress=next_index)

    def _abort_due_to_health(
        self, agent: Agent, execution: _Execution, result: StepResult
    ) -> None:
        """Stop tracking an agent whose health is no longer ONLINE.

        If it was still outbound, its mission fails. If it was
        returning, the mission already succeeded; the agent simply
        stops where it is.
        """
        self._world._release_cell(agent.x, agent.y)
        if execution.mission_id is not None:
            self._missions.update_status(execution.mission_id, MissionStatus.FAILED)
            result["failed_missions"].append(execution.mission_id)
        self._executions.pop(agent.id, None)

    def _retry_route(self, agent: Agent, execution: _Execution, result: StepResult) -> None:
        """Retry computing a route this agent needs (currently only
        used for a return trip that had no route on a previous tick --
        see docs/simulation-model.md, "Execution Lifecycle").
        """
        route = self._find_path_from_agent(agent, execution.launch_position)
        if route is None:
            result["waiting"].append(agent.id)
            return
        self._executions[agent.id] = replace(execution, route=route, progress=0)

    def _handle_arrival(self, agent_id: str, execution: _Execution, result: StepResult) -> None:
        """Handle an agent reaching the final cell of its current route."""
        if execution.mission_id is not None:
            self._missions.update_status(execution.mission_id, MissionStatus.COMPLETED)
            result["completed_missions"].append(execution.mission_id)
            self._begin_return(agent_id, execution, result)
        else:
            agent = self._agents.get_agent(agent_id)
            self._world._release_cell(agent.x, agent.y)
            self._agents.update_activity(agent_id, AgentActivity.IDLE)
            self._agents.clear_mission(agent_id)
            self._executions.pop(agent_id, None)
            result["returned_home"].append(agent_id)

    def _begin_return(self, agent_id: str, execution: _Execution, result: StepResult) -> None:
        """Start an agent's return trip after completing a mission."""
        agent = self._agents.get_agent(agent_id)

        if (agent.x, agent.y) == execution.launch_position:
            self._world._release_cell(agent.x, agent.y)
            self._agents.update_activity(agent_id, AgentActivity.IDLE)
            self._agents.clear_mission(agent_id)
            self._executions.pop(agent_id, None)
            result["returned_home"].append(agent_id)
            return

        self._agents.update_activity(agent_id, AgentActivity.RETURNING)
        self._agents.clear_mission(agent_id)

        return_route = self._find_path_from_agent(agent, execution.launch_position)
        if return_route is None:
            self._executions[agent_id] = _Execution(
                mission_id=None, route=None, progress=0, launch_position=execution.launch_position
            )
            result["waiting"].append(agent_id)
            return

        self._executions[agent_id] = _Execution(
            mission_id=None,
            route=return_route,
            progress=0,
            launch_position=execution.launch_position,
        )

    def _find_path_from_agent(self, agent: Agent, goal: Position) -> Route | None:
        """Compute a route from agent's current position to goal.

        World.is_walkable treats an agent's own current cell as
        occupied -- correctly, for every other agent's queries -- but
        Path Planner would then see this agent's own start cell as
        unwalkable and refuse to route it anywhere. Releasing and
        re-occupying around the call keeps this self-consistent
        without ever leaving the cell actually free for another agent
        to claim: nothing else runs between the release and the
        re-occupy, since SimulationEngine advances agents one at a
        time within a single tick.
        """
        self._world._release_cell(agent.x, agent.y)
        try:
            return self._path_planner.find_path(agent.x, agent.y, goal[0], goal[1])
        finally:
            self._world._occupy_cell(agent.x, agent.y)