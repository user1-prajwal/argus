"""Pydantic request/response models for the ARGUS API layer.

Every field here mirrors an existing backend dataclass or enum field
one-for-one (see docs/api-model.md, "State Serialization"). This module
defines no new domain concepts -- it only shapes JSON in and out of the
existing World, Agent, Mission, Planning Engine, Path Planner,
Simulation Engine, and Scenario Runner objects.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.agent import AgentActivity, Capability, HealthStatus, PlatformType
from app.mission import MissionPriority, MissionStatus
from app.scenario.runner import DEFAULT_MAX_TICKS

# ----------------------------------------------------------------------
# POST /scenarios -- request body
# ----------------------------------------------------------------------


class WorldCreate(BaseModel):
    """Matches World.__init__(width, height)."""

    width: int
    height: int


class ObstacleCreate(BaseModel):
    """Matches the Obstacle dataclass fields."""

    id: str
    x: int
    y: int
    type: str


class AgentCreate(BaseModel):
    """Matches the Agent dataclass's init fields.

    health_status, activity, and current_mission_id are not accepted
    here: docs/api-spec.md says every field not shown gets the same
    default the underlying dataclass already uses, and this endpoint
    does not invent new defaults. Those three are left to Agent's own
    constructor defaults (health_status/activity are required by Agent,
    so ScenarioRunner's own convention -- ONLINE / IDLE -- is used as
    the create-time default, matching build_demo_scenario()).
    """

    id: str
    platform_type: PlatformType
    x: int
    y: int
    battery_level: int
    capabilities: list[Capability] = Field(default_factory=list)


class MissionCreate(BaseModel):
    """Matches the Mission dataclass's init fields.

    status is not accepted here: docs/api-spec.md requires every
    mission to start PENDING, since POST /scenarios never runs
    planning.
    """

    id: str
    name: str
    description: str
    priority: MissionPriority
    target_cells: list[tuple[int, int]]
    required_capabilities: list[Capability] = Field(default_factory=list)


class ScenarioCreate(BaseModel):
    """POST /scenarios request body."""

    world: WorldCreate
    obstacles: list[ObstacleCreate] = Field(default_factory=list)
    agents: list[AgentCreate] = Field(default_factory=list)
    missions: list[MissionCreate] = Field(default_factory=list)


# ----------------------------------------------------------------------
# POST /scenarios -- response body
# ----------------------------------------------------------------------


class ScenarioCreateResponse(BaseModel):
    session_id: str
    phase: str


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/run -- request body
# ----------------------------------------------------------------------


class RunRequest(BaseModel):
    max_ticks: int = DEFAULT_MAX_TICKS


# ----------------------------------------------------------------------
# Shared serialization of existing backend objects
# ----------------------------------------------------------------------


class AgentOut(BaseModel):
    """Agent -> JSON, field for field (docs/api-model.md, "State
    Serialization"). Enum fields serialize to their string value.
    """

    id: str
    platform_type: PlatformType
    x: int
    y: int
    battery_level: int
    health_status: HealthStatus
    activity: AgentActivity
    capabilities: list[Capability]
    current_mission_id: str | None
    registered_at: datetime


class MissionOut(BaseModel):
    """Mission -> JSON, field for field."""

    id: str
    name: str
    description: str
    priority: MissionPriority
    status: MissionStatus
    required_capabilities: list[Capability]
    target_cells: list[tuple[int, int]]
    assigned_agent_ids: list[str]
    created_at: datetime


class WorldSummaryOut(BaseModel):
    """Matches World.world_summary()'s own dict, field for field."""

    width: int
    height: int
    obstacles: int
    spawn_points: int
    charging_stations: int
    mission_zones: int


# ----------------------------------------------------------------------
# GET /scenarios/{session_id} -- response body
# ----------------------------------------------------------------------


class ScenarioStateResponse(BaseModel):
    session_id: str
    phase: str
    tick: int
    world: WorldSummaryOut
    agents: list[AgentOut]
    missions: list[MissionOut]
    simulation_summary: dict[str, int]


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/start -- response body
# ----------------------------------------------------------------------


class PlanningResultOut(BaseModel):
    mission_id: str
    assigned_agent_id: str | None


class StartResponse(BaseModel):
    planning_results: list[PlanningResultOut]


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/step -- response body
# ----------------------------------------------------------------------


class StepResponse(BaseModel):
    """Exactly the dict SimulationEngine.step() returned."""

    tick: int
    moved: list[str]
    waiting: list[str]
    completed_missions: list[str]
    failed_missions: list[str]
    returned_home: list[str]


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/run -- response body
# ----------------------------------------------------------------------


class RunResponse(BaseModel):
    ticks_run: int
    terminated_reason: str
    tick_results: list[StepResponse]


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/agents/{agent_id}/route -- response body
# ----------------------------------------------------------------------


class AgentRouteResponse(BaseModel):
    """Matches Route (app/path_planner/planner.py) field-for-field, as
    currently returned by SimulationEngine.get_active_route(agent_id) --
    not recomputed, not approximated.
    """

    agent_id: str
    cells: list[tuple[int, int]]
    length: int


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/metrics -- response body
# ----------------------------------------------------------------------


class MetricsResponse(BaseModel):
    agent_summary: dict[str, int | dict[str, int]]
    mission_summary: dict[str, int | dict[str, int]]
    simulation_summary: dict[str, int]
