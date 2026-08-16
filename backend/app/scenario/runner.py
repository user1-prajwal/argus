"""ScenarioRunner: an end-to-end integration/demo layer for ARGUS.

ScenarioRunner does not implement any new planning, routing, or
simulation logic. It only assembles the existing World, AgentRegistry,
MissionRegistry, PlanningEngine, PathPlanner, and SimulationEngine into
one meaningful run -- calling PlanningEngine.plan() once, then stepping
SimulationEngine until nothing is left actively executing or a safe
maximum tick count is reached -- and reports what happened in a
structured form a future dashboard could visualize.

build_demo_scenario() is example content only: a concrete World, set of
agents, and set of missions assembled to demonstrate obstacle routing,
capability matching, mission priority, and the battery safety check.
ScenarioRunner itself works with any World, AgentRegistry, and
MissionRegistry -- nothing about it depends on this specific content.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent import (
    Agent,
    AgentActivity,
    AgentRegistry,
    Capability,
    HealthStatus,
    PlatformType,
)
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner
from app.planning import PlanningEngine, PlanningResult
from app.simulation import SimulationEngine
from app.world import Obstacle, World

DEFAULT_MAX_TICKS = 200

# Matches app.simulation.engine.StepResult exactly, without importing
# past SimulationEngine's public surface -- see
# docs/simulation-api.md, "Purpose": "only the SimulationEngine class
# should be used by other modules."
StepResult = dict[str, int | list[str]]


@dataclass(frozen=True)
class ScenarioResult:
    """The full, structured outcome of one scenario run.

    Every field is produced directly by one of the existing modules'
    own public methods, or a straightforward aggregation of them --
    ScenarioRunner adds no planning or execution data of its own.

    Attributes:
        planning_results: The list PlanningEngine.plan() returned.
        tick_results: Every SimulationEngine.step() result, in order.
        ticks_run: The number of ticks actually executed (len of
            tick_results).
        terminated_reason: "no_active_agents" if the run stopped
            because nothing was left executing or returning, or
            "max_ticks_reached" if the safe tick cap was hit first.
        final_agents: Every agent's state at the end of the run.
        final_missions: Every mission's state at the end of the run.
        completed_mission_ids: Ids of missions that ended COMPLETED.
        failed_mission_ids: Ids of missions that ended FAILED.
        agent_summary: AgentRegistry.agent_summary() at the end.
        mission_summary: MissionRegistry.mission_summary() at the end.
        simulation_summary: SimulationEngine.simulation_summary() at
            the end.
    """

    planning_results: list[PlanningResult]
    tick_results: list[StepResult]
    ticks_run: int
    terminated_reason: str
    final_agents: list[Agent]
    final_missions: list[Mission]
    completed_mission_ids: list[str]
    failed_mission_ids: list[str]
    agent_summary: dict[str, int | dict[str, int]]
    mission_summary: dict[str, int | dict[str, int]]
    simulation_summary: dict[str, int]


class ScenarioRunner:
    """Runs one scenario over an already-assembled World, AgentRegistry,
    MissionRegistry, PlanningEngine, PathPlanner, and SimulationEngine.

    ScenarioRunner is an integration/demo layer, not another planning
    algorithm. It calls PlanningEngine.plan() exactly once, then calls
    SimulationEngine.step() until nothing is left actively executing
    or returning, or a safe maximum tick count is reached, and reports
    the result. It holds no state of its own beyond the six objects it
    was constructed with.
    """

    def __init__(
        self,
        world: World,
        agents: AgentRegistry,
        missions: MissionRegistry,
        planning_engine: PlanningEngine,
        path_planner: PathPlanner,
        simulation_engine: SimulationEngine,
    ) -> None:
        """Bind a ScenarioRunner to an already-assembled set of modules.

        Args:
            world: The World the scenario takes place in.
            agents: The AgentRegistry holding every agent in play.
            missions: The MissionRegistry holding every mission in play.
            planning_engine: The PlanningEngine bound to the same
                world, agents, and missions.
            path_planner: The PathPlanner bound to the same world.
            simulation_engine: The SimulationEngine bound to the same
                world, agents, missions, and path_planner.

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
        if not isinstance(planning_engine, PlanningEngine):
            raise TypeError(
                f"planning_engine must be a PlanningEngine instance, "
                f"got {type(planning_engine).__name__}"
            )
        if not isinstance(path_planner, PathPlanner):
            raise TypeError(
                f"path_planner must be a PathPlanner instance, got {type(path_planner).__name__}"
            )
        if not isinstance(simulation_engine, SimulationEngine):
            raise TypeError(
                f"simulation_engine must be a SimulationEngine instance, "
                f"got {type(simulation_engine).__name__}"
            )

        self._world = world
        self._agents = agents
        self._missions = missions
        self._planning_engine = planning_engine
        self._path_planner = path_planner
        self._simulation_engine = simulation_engine

    def run(self, max_ticks: int = DEFAULT_MAX_TICKS) -> ScenarioResult:
        """Plan once, then simulate until settled or max_ticks is reached.

        Args:
            max_ticks: The maximum number of simulation ticks to run.
                A safety cap only -- most scenarios settle well before
                this.

        Returns:
            A ScenarioResult describing the full run.

        Raises:
            TypeError: If max_ticks is not an int.
            ValueError: If max_ticks is not a positive integer.
        """
        if not isinstance(max_ticks, int) or isinstance(max_ticks, bool):
            raise TypeError(f"max_ticks must be an int, got {type(max_ticks).__name__}")
        if max_ticks <= 0:
            raise ValueError("max_ticks must be a positive integer")

        planning_results = self._planning_engine.plan()

        tick_results: list[StepResult] = []
        while len(tick_results) < max_ticks and not self._is_settled():
            tick_results.append(self._simulation_engine.step())

        terminated_reason = "no_active_agents" if self._is_settled() else "max_ticks_reached"

        final_missions = self._missions.list_missions()
        completed_mission_ids = [
            mission.id for mission in final_missions if mission.status is MissionStatus.COMPLETED
        ]
        failed_mission_ids = [
            mission.id for mission in final_missions if mission.status is MissionStatus.FAILED
        ]

        return ScenarioResult(
            planning_results=planning_results,
            tick_results=tick_results,
            ticks_run=len(tick_results),
            terminated_reason=terminated_reason,
            final_agents=self._agents.list_agents(),
            final_missions=final_missions,
            completed_mission_ids=completed_mission_ids,
            failed_mission_ids=failed_mission_ids,
            agent_summary=self._agents.agent_summary(),
            mission_summary=self._missions.mission_summary(),
            simulation_summary=self._simulation_engine.simulation_summary(),
        )

    def _is_settled(self) -> bool:
        """True when nothing is executing, returning, or still waiting
        to be picked up by SimulationEngine.

        Right after PlanningEngine.plan(), every assigned agent's
        activity is ASSIGNED, not yet EXECUTING_MISSION -- that
        transition only happens inside SimulationEngine.step()'s own
        pickup phase. Checking simulation_summary() alone would report
        "settled" before a single tick has run, so this also checks
        for any mission still sitting in ASSIGNED.
        """
        summary = self._simulation_engine.simulation_summary()
        if summary["agents_executing"] > 0 or summary["agents_returning"] > 0:
            return False
        return not any(
            mission.status is MissionStatus.ASSIGNED for mission in self._missions.list_missions()
        )


def build_demo_scenario() -> ScenarioRunner:
    """Assemble a complete, meaningful ARGUS scenario for demonstration.

    Builds a 12x12 World with a partial wall (forcing real obstacle
    routing for two of the four agents), four agents with different
    platform types, positions, capabilities, and battery levels, and
    four missions with different priorities, target cells, and
    capability requirements -- then wires up AgentRegistry,
    MissionRegistry, PlanningEngine, PathPlanner, and SimulationEngine
    around them.

    This scenario is deliberately designed so PlanningEngine.plan()
    produces a deterministic, explainable outcome: a CRITICAL,
    capability-unrestricted mission claims the highest-battery agent;
    two capability-specific missions each go to the one agent that
    qualifies; and a low-priority mission is left to the one
    remaining, low-battery agent, which SimulationEngine's round-trip
    safety check then correctly refuses to send anywhere.

    This is example content only -- ScenarioRunner works with any
    World, agents, and missions, not just this one.

    Returns:
        A ScenarioRunner ready to have run() called on it.
    """
    world = World(width=12, height=12)
    for y in range(9):
        world.add_obstacle(Obstacle(id=f"wall-{y}", x=6, y=y, type="Wall"))

    agents = AgentRegistry()
    agents.add_agent(
        Agent(
            id="drone-thermal",
            platform_type=PlatformType.DRONE,
            x=0,
            y=0,
            battery_level=90,
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.IDLE,
            capabilities=frozenset({Capability.THERMAL_CAMERA}),
        )
    )
    agents.add_agent(
        Agent(
            id="drone-lidar",
            platform_type=PlatformType.DRONE,
            x=0,
            y=11,
            battery_level=95,
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.IDLE,
            capabilities=frozenset({Capability.LIDAR}),
        )
    )
    agents.add_agent(
        Agent(
            id="generalist",
            platform_type=PlatformType.GROUND_ROBOT,
            x=5,
            y=5,
            battery_level=100,
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.IDLE,
            capabilities=frozenset(),
        )
    )
    agents.add_agent(
        Agent(
            id="low-battery-unit",
            platform_type=PlatformType.AUTONOMOUS_VEHICLE,
            x=11,
            y=0,
            battery_level=8,
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.IDLE,
            capabilities=frozenset(),
        )
    )

    missions = MissionRegistry()
    missions.add_mission(
        Mission(
            id="open-recon",
            name="Open Area Recon",
            description="General reconnaissance; no special sensor required.",
            priority=MissionPriority.CRITICAL,
            status=MissionStatus.PENDING,
            target_cells=frozenset({(3, 3)}),
        )
    )
    missions.add_mission(
        Mission(
            id="thermal-survey",
            name="Thermal Survey",
            description="Requires a thermal camera.",
            priority=MissionPriority.HIGH,
            status=MissionStatus.PENDING,
            target_cells=frozenset({(9, 3)}),
            required_capabilities=frozenset({Capability.THERMAL_CAMERA}),
        )
    )
    missions.add_mission(
        Mission(
            id="lidar-survey",
            name="LIDAR Survey",
            description="Requires LIDAR.",
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.PENDING,
            target_cells=frozenset({(9, 9)}),
            required_capabilities=frozenset({Capability.LIDAR}),
        )
    )
    missions.add_mission(
        Mission(
            id="distant-patrol",
            name="Distant Patrol",
            description="Far from most agents; battery may not be enough for the round trip.",
            priority=MissionPriority.LOW,
            status=MissionStatus.PENDING,
            target_cells=frozenset({(11, 11)}),
        )
    )

    planning_engine = PlanningEngine(world, agents, missions)
    path_planner = PathPlanner(world)
    simulation_engine = SimulationEngine(world, agents, missions, path_planner)

    return ScenarioRunner(world, agents, missions, planning_engine, path_planner, simulation_engine)