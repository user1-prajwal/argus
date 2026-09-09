"""The SimulationEngine class: advances a running multi-agent simulation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.agent import Agent, AgentActivity, AgentNotFoundError, AgentRegistry, HealthStatus
from app.mission import Mission, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner, Route
from app.world import World

_MOVE_COST = 1

Position = tuple[int, int]
StepResult = dict[str, "int | list[str]"]


@dataclass(frozen=True)
class _Execution:
    mission_id: str | None
    route: Route | None
    progress: int
    launch_position: Position


class SimulationEngine:
    def __init__(
        self,
        world: World,
        agents: AgentRegistry,
        missions: MissionRegistry,
        path_planner: PathPlanner,
    ) -> None:
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

        # Mark every registered agent's starting cell as occupied, so
        # World.is_walkable (and therefore every other agent's route
        # planning and per-tick movement) is aware of it from tick 0 --
        # not only once that agent begins actively executing a
        # mission. Without this, an agent that has not yet started
        # executing (still IDLE, or a mission that fails at pickup and
        # releases it back to IDLE) was invisible to World's occupancy
        # tracking, since _occupy_cell was previously only ever called
        # from _begin_execution. That allowed a second agent to route
        # directly onto the first agent's stationary position -- a
        # real collision the project's multi-drone requirement does
        # not allow. This is the smallest fix that closes that gap
        # without changing per-tick movement, battery, health, or
        # mission-completion logic, all of which are unmodified.
        #
        # Two agents may legitimately share a starting cell (nothing
        # in Agent/AgentRegistry prevents it, and earlier project
        # phases did not either) -- in that case the cell is occupied
        # once, not per agent; World._occupy_cell already treats
        # "already occupied" as a normal state to guard against here,
        # not something to propagate as a construction-time error for
        # a scenario that was previously accepted without complaint.
        for agent in self._agents.list_agents():
            if not self._world._is_occupied(agent.x, agent.y):
                try:
                    self._world._occupy_cell(agent.x, agent.y)
                except ValueError:
                    # Position is an obstacle cell or otherwise
                    # unoccupiable -- leave it alone rather than fail
                    # construction; per-tick movement already handles
                    # an agent whose own state doesn't perfectly match
                    # World (e.g. AgentNotFoundError paths elsewhere)
                    # without raising, and this preserves that same
                    # tolerance for a pre-existing, out-of-band agent
                    # position at construction time.
                    pass

    def step(self) -> StepResult:
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

    def get_active_route(self, agent_id: str) -> Route | None:
        execution = self._executions.get(agent_id)
        if execution is None:
            return None
        return execution.route

    def _pick_up_assigned_missions(self, result: StepResult) -> None:
        for mission in self._missions.list_missions():
            if mission.status is MissionStatus.ASSIGNED:
                self._begin_execution(mission, result)

    def _begin_execution(self, mission: Mission, result: StepResult) -> None:
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
        # The agent's own current cell is already marked occupied (see
        # __init__ -- every registered agent's starting cell is
        # occupied from construction, not only once it begins
        # executing). World.is_walkable would otherwise see the
        # agent's own start cell as unwalkable and refuse to route it
        # anywhere -- the same problem _find_path_from_agent already
        # solves for a return trip, solved here the same way:
        # release and immediately re-occupy around the two find_path
        # calls, with nothing else running in between (SimulationEngine
        # advances agents one at a time within a single tick), so the
        # cell is never actually left free for another agent to claim.
        self._world._release_cell(agent.x, agent.y)
        try:
            outbound = self._path_planner.find_path(agent.x, agent.y, target[0], target[1])
            if outbound is None:
                self._fail_mission(mission, agent, result)
                return

            return_route = self._path_planner.find_path(target[0], target[1], agent.x, agent.y)
            if (
                return_route is None
                or agent.battery_level < outbound.length + return_route.length
            ):
                self._fail_mission(mission, agent, result)
                return
        finally:
            self._world._occupy_cell(agent.x, agent.y)

        self._missions.update_status(mission.id, MissionStatus.IN_PROGRESS)
        self._agents.update_activity(agent.id, AgentActivity.EXECUTING_MISSION)
        execution = _Execution(
            mission_id=mission.id,
            route=outbound,
            progress=0,
            launch_position=(agent.x, agent.y),
        )
        if outbound.length == 0:
            self._handle_arrival(agent.id, execution, result)
        else:
            self._executions[agent.id] = execution

    def _fail_mission(self, mission: Mission, agent: Agent | None, result: StepResult) -> None:
        self._missions.update_status(mission.id, MissionStatus.FAILED)
        if agent is not None:
            self._agents.update_activity(agent.id, AgentActivity.IDLE)
            self._agents.clear_mission(agent.id)
        result["failed_missions"].append(mission.id)

    def _nearest_target_cell(self, agent: Agent, mission: Mission) -> Position:
        return min(
            mission.target_cells,
            key=lambda cell: (abs(cell[0] - agent.x) + abs(cell[1] - agent.y), cell[0], cell[1]),
        )

    def _advance_one(self, agent_id: str, result: StepResult) -> None:
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
        self._world._release_cell(agent.x, agent.y)
        if execution.mission_id is not None:
            self._missions.update_status(execution.mission_id, MissionStatus.FAILED)
            result["failed_missions"].append(execution.mission_id)
        self._executions.pop(agent.id, None)

    def _retry_route(self, agent: Agent, execution: _Execution, result: StepResult) -> None:
        route = self._find_path_from_agent(agent, execution.launch_position)
        if route is None:
            result["waiting"].append(agent.id)
            return
        self._executions[agent.id] = replace(execution, route=route, progress=0)

    def _handle_arrival(self, agent_id: str, execution: _Execution, result: StepResult) -> None:
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
        self._world._release_cell(agent.x, agent.y)
        try:
            return self._path_planner.find_path(agent.x, agent.y, goal[0], goal[1])
        finally:
            self._world._occupy_cell(agent.x, agent.y)
