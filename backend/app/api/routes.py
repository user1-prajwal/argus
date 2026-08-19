"""HTTP route handlers for the ARGUS API layer.

Every handler here calls an existing backend method and serializes the
result. No handler contains a planning, routing, or execution decision
-- see docs/api-spec.md, "Purpose".
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent import (
    Agent,
    AgentActivity,
    AgentRegistry,
    HealthStatus,
)
from app.agent.exceptions import AgentNotFoundError, DuplicateAgentError
from app.mission import Mission, MissionRegistry, MissionStatus
from app.mission.exceptions import DuplicateMissionError
from app.path_planner import PathPlanner
from app.planning import PlanningEngine
from app.simulation import SimulationEngine
from app.world import Obstacle, World
from app.world.exceptions import (
    DuplicateChargingStationError,
    DuplicateMissionZoneError,
    DuplicateObstacleError,
    DuplicateSpawnPointError,
)

from .schemas import (
    AgentOut,
    AgentRouteResponse,
    MetricsResponse,
    PlanningResultOut,
    RunRequest,
    RunResponse,
    ScenarioCreate,
    ScenarioCreateResponse,
    ScenarioStateResponse,
    StartResponse,
    StepResponse,
    WorldSummaryOut,
)
from .session import (
    PHASE_IN_PROGRESS,
    PHASE_NOT_STARTED,
    PHASE_SETTLED,
    Session,
    SessionStore,
)

router = APIRouter()
_store = SessionStore()


# ----------------------------------------------------------------------
# Helpers -- construction (POST /scenarios)
# ----------------------------------------------------------------------


def _build_world(payload: ScenarioCreate) -> World:
    world = World(width=payload.world.width, height=payload.world.height)
    for obstacle in payload.obstacles:
        world.add_obstacle(
            Obstacle(id=obstacle.id, x=obstacle.x, y=obstacle.y, type=obstacle.type)
        )
    return world


def _build_agents(payload: ScenarioCreate) -> AgentRegistry:
    registry = AgentRegistry()
    for agent_in in payload.agents:
        registry.add_agent(
            Agent(
                id=agent_in.id,
                platform_type=agent_in.platform_type,
                x=agent_in.x,
                y=agent_in.y,
                battery_level=agent_in.battery_level,
                health_status=HealthStatus.ONLINE,
                activity=AgentActivity.IDLE,
                capabilities=frozenset(agent_in.capabilities),
            )
        )
    return registry


def _build_missions(payload: ScenarioCreate) -> MissionRegistry:
    registry = MissionRegistry()
    for mission_in in payload.missions:
        registry.add_mission(
            Mission(
                id=mission_in.id,
                name=mission_in.name,
                description=mission_in.description,
                priority=mission_in.priority,
                status=MissionStatus.PENDING,
                target_cells=frozenset(mission_in.target_cells),
                required_capabilities=frozenset(mission_in.required_capabilities),
            )
        )
    return registry


# ----------------------------------------------------------------------
# Helpers -- serialization
# ----------------------------------------------------------------------


def _serialize_agent(agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        platform_type=agent.platform_type,
        x=agent.x,
        y=agent.y,
        battery_level=agent.battery_level,
        health_status=agent.health_status,
        activity=agent.activity,
        capabilities=sorted(agent.capabilities, key=lambda c: c.value),
        current_mission_id=agent.current_mission_id,
        registered_at=agent.registered_at,
    )


def _serialize_mission(mission: Mission) -> dict:
    return dict(
        id=mission.id,
        name=mission.name,
        description=mission.description,
        priority=mission.priority,
        status=mission.status,
        required_capabilities=sorted(
            mission.required_capabilities, key=lambda c: c.value
        ),
        target_cells=sorted(mission.target_cells),
        assigned_agent_ids=sorted(mission.assigned_agent_ids),
        created_at=mission.created_at,
    )


def _serialize_world_summary(world: World) -> WorldSummaryOut:
    return WorldSummaryOut(**world.world_summary())


def _get_session_or_404(session_id: str) -> Session:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session '{session_id}'")
    return session


# Exceptions raised by the existing World/Agent/Mission constructors and
# registries when request data fails *their* own validation (e.g. a
# non-positive world size, an empty mission name, a duplicate id). Per
# docs/api-spec.md, "Errors", this is exactly what 422 means for
# POST /scenarios: "matches the underlying dataclass's own validation."
# This is a translation boundary only -- it changes no backend
# behavior, it only maps an existing, already-correct exception to the
# HTTP status the spec requires. Listed as concrete types rather than a
# shared base class, since only these names are confirmed by the
# provided source (world/exceptions.py, and DuplicateAgentError /
# DuplicateMissionError per agent/registry.py's and
# mission/registry.py's own imports and the traceback each raises).
_SCENARIO_VALIDATION_ERRORS = (
    TypeError,
    ValueError,
    DuplicateObstacleError,
    DuplicateSpawnPointError,
    DuplicateChargingStationError,
    DuplicateMissionZoneError,
    DuplicateAgentError,
    DuplicateMissionError,
)


def _construct_scenario(
    payload: ScenarioCreate,
) -> tuple[World, AgentRegistry, MissionRegistry]:
    """Build World/AgentRegistry/MissionRegistry from a validated request.

    Wraps only the existing constructors' own validation errors as a
    422 -- see docs/api-spec.md, "Create Scenario": "422 ... matches
    the underlying dataclass's own validation." No other exception
    type is caught here.
    """
    try:
        world = _build_world(payload)
        agents = _build_agents(payload)
        missions = _build_missions(payload)
    except _SCENARIO_VALIDATION_ERRORS as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return world, agents, missions


# ----------------------------------------------------------------------
# POST /scenarios
# ----------------------------------------------------------------------


@router.post("/scenarios", response_model=ScenarioCreateResponse, status_code=200)
def create_scenario(payload: ScenarioCreate) -> ScenarioCreateResponse:
    world, agents, missions = _construct_scenario(payload)
    planning_engine = PlanningEngine(world, agents, missions)
    path_planner = PathPlanner(world)
    simulation_engine = SimulationEngine(world, agents, missions, path_planner)

    session = _store.create(
        world=world,
        agents=agents,
        missions=missions,
        planning_engine=planning_engine,
        path_planner=path_planner,
        simulation_engine=simulation_engine,
    )
    return ScenarioCreateResponse(session_id=session.session_id, phase=session.phase)


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}
# ----------------------------------------------------------------------


@router.get("/scenarios/{session_id}", response_model=ScenarioStateResponse)
def get_scenario(session_id: str) -> ScenarioStateResponse:
    session = _get_session_or_404(session_id)
    return ScenarioStateResponse(
        session_id=session.session_id,
        phase=session.phase,
        tick=session.simulation_engine.simulation_summary()["tick"],
        world=_serialize_world_summary(session.world),
        agents=[_serialize_agent(a) for a in session.agents.list_agents()],
        missions=[_serialize_mission(m) for m in session.missions.list_missions()],
        simulation_summary=session.simulation_engine.simulation_summary(),
    )


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/start
# ----------------------------------------------------------------------


@router.post("/scenarios/{session_id}/start", response_model=StartResponse)
def start_scenario(session_id: str) -> StartResponse:
    session = _get_session_or_404(session_id)
    if session.phase != PHASE_NOT_STARTED:
        raise HTTPException(
            status_code=409, detail="Session has already been started"
        )

    planning_results = session.planning_engine.plan()
    session.planning_results = planning_results
    session.phase = PHASE_IN_PROGRESS
    session.refresh_phase()

    return StartResponse(
        planning_results=[
            PlanningResultOut(
                mission_id=r["mission_id"], assigned_agent_id=r["assigned_agent_id"]
            )
            for r in planning_results
        ]
    )


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/step
# ----------------------------------------------------------------------


@router.post("/scenarios/{session_id}/step", response_model=StepResponse)
def step_scenario(session_id: str) -> StepResponse:
    session = _get_session_or_404(session_id)
    if session.phase == PHASE_NOT_STARTED:
        raise HTTPException(
            status_code=409, detail="Session has not been started yet"
        )
    if session.phase == PHASE_SETTLED:
        raise HTTPException(status_code=409, detail="Session has already settled")

    result = session.simulation_engine.step()
    session.tick_results.append(result)
    session.refresh_phase()

    return StepResponse(**result)


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/run
# ----------------------------------------------------------------------


@router.post("/scenarios/{session_id}/run", response_model=RunResponse)
def run_scenario(session_id: str, payload: RunRequest) -> RunResponse:
    session = _get_session_or_404(session_id)
    if session.phase == PHASE_NOT_STARTED:
        raise HTTPException(
            status_code=409, detail="Session has not been started yet"
        )
    if session.phase == PHASE_SETTLED:
        raise HTTPException(status_code=409, detail="Session has already settled")

    if not isinstance(payload.max_ticks, int) or isinstance(payload.max_ticks, bool):
        raise HTTPException(status_code=422, detail="max_ticks must be an int")
    if payload.max_ticks <= 0:
        raise HTTPException(
            status_code=422, detail="max_ticks must be a positive integer"
        )

    tick_results: list[dict] = []
    # Same settlement logic ScenarioRunner.run() already uses: step
    # until settled or max_ticks is reached.
    while len(tick_results) < payload.max_ticks and not session.is_settled():
        result = session.simulation_engine.step()
        session.tick_results.append(result)
        tick_results.append(result)

    session.refresh_phase()
    terminated_reason = (
        "no_active_agents" if session.is_settled() else "max_ticks_reached"
    )

    return RunResponse(
        ticks_run=len(tick_results),
        terminated_reason=terminated_reason,
        tick_results=[StepResponse(**r) for r in tick_results],
    )


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/metrics
# ----------------------------------------------------------------------


@router.get("/scenarios/{session_id}/metrics", response_model=MetricsResponse)
def get_metrics(session_id: str) -> MetricsResponse:
    session = _get_session_or_404(session_id)
    return MetricsResponse(
        agent_summary=session.agents.agent_summary(),
        mission_summary=session.missions.mission_summary(),
        simulation_summary=session.simulation_engine.simulation_summary(),
    )


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/agents/{agent_id}/route
# ----------------------------------------------------------------------


@router.get(
    "/scenarios/{session_id}/agents/{agent_id}/route",
    response_model=AgentRouteResponse,
)
def get_agent_route(session_id: str, agent_id: str) -> AgentRouteResponse:
    session = _get_session_or_404(session_id)

    # Confirms the agent itself exists (distinct from "no active
    # route") so an unknown agent id and an idle/unassigned agent both
    # 404, but for reasons the detail message can honestly tell apart.
    try:
        session.agents.get_agent(agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Unknown agent '{agent_id}'"
        ) from exc

    route = session.simulation_engine.get_active_route(agent_id)
    if route is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' has no active route",
        )

    return AgentRouteResponse(
        agent_id=agent_id, cells=list(route.cells), length=route.length
    )
