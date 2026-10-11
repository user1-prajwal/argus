/**
 * Types mirroring backend/app/api/schemas.py field-for-field.
 *
 * Nothing here is computed or inferred beyond what the backend already
 * returns — see docs/api-model.md, "State Serialization": "No field is
 * invented that the backend does not already expose." The frontend
 * consumes these shapes as-is.
 */

// ---------------------------------------------------------------------
// Enums — string literal unions matching the backend's str Enum values
// exactly (see app/agent/enums.py, app/mission/enums.py).
// ---------------------------------------------------------------------

export type PlatformType =
  | "DRONE"
  | "GROUND_ROBOT"
  | "AUTONOMOUS_VEHICLE"
  | "MARINE_VEHICLE";

export type Capability = "thermal_camera" | "standard_camera" | "lidar" | "gps";

export type HealthStatus = "ONLINE" | "FAILED" | "OFFLINE";

export type AgentActivity =
  | "IDLE"
  | "ASSIGNED"
  | "EXECUTING_MISSION"
  | "RETURNING"
  | "CHARGING";

export type MissionPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type MissionStatus =
  | "PENDING"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type ScenarioPhase = "not_started" | "in_progress" | "settled";

// ---------------------------------------------------------------------
// Scenario creation request (POST /scenarios)
// ---------------------------------------------------------------------

export interface WorldCreate {
  width: number;
  height: number;
}

export interface ObstacleCreate {
  id: string;
  x: number;
  y: number;
  type: string;
}

export interface AgentCreate {
  id: string;
  platform_type: PlatformType;
  x: number;
  y: number;
  battery_level: number;
  capabilities?: Capability[];
}

export interface MissionCreate {
  id: string;
  name: string;
  description: string;
  priority: MissionPriority;
  target_cells: [number, number][];
  required_capabilities?: Capability[];
}

export interface ScenarioCreateRequest {
  world: WorldCreate;
  obstacles?: ObstacleCreate[];
  agents?: AgentCreate[];
  missions?: MissionCreate[];
}

export interface ScenarioCreateResponse {
  session_id: string;
  phase: ScenarioPhase;
}

// ---------------------------------------------------------------------
// State (GET /scenarios/{session_id})
// ---------------------------------------------------------------------

export interface AgentOut {
  id: string;
  platform_type: PlatformType;
  x: number;
  y: number;
  battery_level: number;
  health_status: HealthStatus;
  activity: AgentActivity;
  capabilities: Capability[];
  current_mission_id: string | null;
  registered_at: string;
}

export interface MissionOut {
  id: string;
  name: string;
  description: string;
  priority: MissionPriority;
  status: MissionStatus;
  required_capabilities: Capability[];
  target_cells: [number, number][];
  assigned_agent_ids: string[];
  created_at: string;
  /** The ~4 Area Watch coverage waypoints, in visiting order (backend's
   * coverage_waypoints_for) — null for a point mission (a single
   * target cell). Not a raw Mission field; derived for display. */
  coverage_waypoints: [number, number][] | null;
}

export interface WorldSummaryOut {
  width: number;
  height: number;
  obstacles: number;
  spawn_points: number;
  charging_stations: number;
  mission_zones: number;
}

export interface SimulationSummary {
  tick: number;
  agents_executing: number;
  agents_returning: number;
  missions_in_progress: number;
  missions_completed: number;
  missions_failed: number;
}

export interface ScenarioStateResponse {
  session_id: string;
  phase: ScenarioPhase;
  tick: number;
  world: WorldSummaryOut;
  agents: AgentOut[];
  missions: MissionOut[];
  simulation_summary: SimulationSummary;
  geo_bounds: GeoBoundsOut | null;
}

// ---------------------------------------------------------------------
// Start (POST /scenarios/{session_id}/start)
// ---------------------------------------------------------------------

export interface PlanningResultOut {
  mission_id: string;
  assigned_agent_id: string | null;
}

export interface StartResponse {
  planning_results: PlanningResultOut[];
}

// ---------------------------------------------------------------------
// Step (POST /scenarios/{session_id}/step)
// ---------------------------------------------------------------------

export interface StepResponse {
  tick: number;
  moved: string[];
  waiting: string[];
  completed_missions: string[];
  failed_missions: string[];
  returned_home: string[];
}

// ---------------------------------------------------------------------
// Run (POST /scenarios/{session_id}/run)
// ---------------------------------------------------------------------

export interface RunRequest {
  max_ticks?: number;
}

export interface RunResponse {
  ticks_run: number;
  terminated_reason: string;
  tick_results: StepResponse[];
}

// ---------------------------------------------------------------------
// Metrics (GET /scenarios/{session_id}/metrics)
// ---------------------------------------------------------------------

export interface AgentSummary {
  total: number;
  health_status: Record<string, number>;
  activity: Record<string, number>;
}

export interface MissionSummary {
  total: number;
  status: Record<string, number>;
  priority: Record<string, number>;
}

export interface MetricsResponse {
  agent_summary: AgentSummary;
  mission_summary: MissionSummary;
  simulation_summary: SimulationSummary;
}

// ---------------------------------------------------------------------
// Route (GET /scenarios/{session_id}/agents/{agent_id}/route)
// ---------------------------------------------------------------------

export interface AgentRouteResponse {
  agent_id: string;
  cells: [number, number][];
  length: number;
  /** 1-indexed (current, total) Area Watch coverage progress — both
   * null for a point mission or a return-to-home leg. */
  current_waypoint: number | null;
  total_waypoints: number | null;
}

// ---------------------------------------------------------------------
// Geographic scenario creation (POST /scenarios/geo)
// ---------------------------------------------------------------------

export interface GeoBoundsOut {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface GeoScenarioCreateRequest {
  south: number;
  west: number;
  north: number;
  east: number;
  world_width?: number;
  world_height?: number;
  agents?: AgentCreate[];
  missions?: MissionCreate[];
}

export interface GeoScenarioCreateResponse {
  session_id: string;
  phase: ScenarioPhase;
  bounds: GeoBoundsOut;
  world_width: number;
  world_height: number;
  building_count: number;
  obstacle_cell_count: number;
}

// ---------------------------------------------------------------------
// Error shape (see docs/api-spec.md, "Error Behavior")
// ---------------------------------------------------------------------

export interface ApiErrorBody {
  detail: string;
}
