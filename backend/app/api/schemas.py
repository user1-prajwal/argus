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


class GeoBoundsOut(BaseModel):
    """Echoes the geographic bounding box a session was created from
    (app/geo/scenario_builder.py), when it was created via
    POST /scenarios/geo. Lets the frontend convert every subsequent
    World-cell response back to lat/lng using the exact bounds the
    backend actually used -- not a value the frontend has to remember
    or re-derive itself.
    """

    south: float
    west: float
    north: float
    east: float


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
    # None for a session created via the original POST /scenarios (no
    # real geographic area exists for it). Present for a session
    # created via POST /scenarios/geo -- see GeoBoundsOut's doc comment.
    geo_bounds: GeoBoundsOut | None = None


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


# ----------------------------------------------------------------------
# POST /scenarios/geo -- request body
# ----------------------------------------------------------------------


class GeoScenarioCreate(BaseModel):
    """Request body for creating a scenario from a real geographic
    operating area (app/geo/scenario_builder.py). Field names match
    the project requirement's exact shape: south/west/north/east.

    world_width/world_height are optional -- default to the same
    12x12 the rest of this project has used throughout, so an existing
    frontend or script that omits them still gets a working World.

    agents is the user-configured fleet -- zero, one, or many. Empty
    (the default) creates NO agents; there is no automatic fallback
    fleet. Reuses AgentCreate exactly as ScenarioCreate.agents already
    does (see _build_agents), so x/y here are World cell coordinates,
    not geographic ones -- the frontend converts a user's map click to
    a World cell before sending it, the same conversion it already
    performs for mission target_cells (see docs/api-model.md,
    "Frontend/Backend Boundary": all coordinate translation happens at
    the frontend/API boundary, never inside the simulation).

    missions is optional and defaults to none, exactly like
    ScenarioCreate.missions -- planning still never runs here (see
    create_geo_scenario's own doc comment); every mission still starts
    PENDING. Included directly on this request (rather than requiring
    a separate call) because there is no endpoint to add a mission to
    an already-created session -- see create_geo_scenario's doc
    comment for the full reasoning: a client wanting to add a mission
    re-POSTs here with the same bounding box plus the new mission,
    which regenerates an equivalent World deterministically from the
    same real building data (app/geo/conversion.py) rather than
    requiring a second, different endpoint.
    """

    south: float
    west: float
    north: float
    east: float
    world_width: int = 12
    world_height: int = 12
    agents: list[AgentCreate] = Field(default_factory=list)
    missions: list[MissionCreate] = Field(default_factory=list)


# ----------------------------------------------------------------------
# POST /scenarios/geo -- response body
# ----------------------------------------------------------------------


class GeoScenarioCreateResponse(BaseModel):
    """Kept response-compatible with ScenarioCreateResponse
    (session_id, phase) per the project requirement -- extended with
    the geographic metadata the frontend needs to convert every
    subsequent GET /scenarios/{id} World-cell response back to
    lat/lng, since a geo-created session's bounding box is chosen at
    request time rather than fixed like the original demo scenario.
    """

    session_id: str
    phase: str
    bounds: GeoBoundsOut
    world_width: int
    world_height: int
    building_count: int
    obstacle_cell_count: int
