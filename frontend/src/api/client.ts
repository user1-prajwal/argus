/**
 * Thin HTTP client over the ARGUS API (docs/api-spec.md).
 *
 * Every function here does exactly one thing: call one endpoint and
 * return its parsed JSON body. No function here computes anything —
 * assignment, routing, battery, or state transitions are entirely the
 * backend's responsibility (see docs/api-model.md, "Responsibilities":
 * "The API layer does not decide which agent is assigned to which
 * mission... compute a route... decide when a mission completes").
 * This file mirrors that boundary on the client: it is a translation
 * layer, not a second implementation.
 */

import type {
  AgentRouteResponse,
  GeoScenarioCreateRequest,
  GeoScenarioCreateResponse,
  MetricsResponse,
  RunRequest,
  RunResponse,
  ScenarioCreateRequest,
  ScenarioCreateResponse,
  ScenarioStateResponse,
  StartResponse,
  StepResponse,
} from "../types/argus";

/**
 * Vite's dev server proxies /api -> http://localhost:8000 (see
 * vite.config.ts). In a production build, set VITE_API_BASE_URL to the
 * deployed API's origin; it defaults to the same-origin /api prefix.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`ARGUS API error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    // Per docs/api-spec.md, "Error Behavior": every error response is
    // {"detail": "..."}. Fall back gracefully if a proxy or network
    // failure returns something else shaped.
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Response body wasn't JSON — keep statusText.
    }
    throw new ApiError(response.status, detail);
  }

  // 204/empty-body responses never occur in this API's Version 1
  // surface, but guard defensively rather than assume.
  const text = await response.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

/** POST /scenarios */
export function createScenario(
  payload: ScenarioCreateRequest,
): Promise<ScenarioCreateResponse> {
  return request<ScenarioCreateResponse>("/scenarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * POST /scenarios/geo
 *
 * Creates a scenario whose World is generated from real OpenStreetMap
 * building footprints inside the given geographic bounding box (see
 * backend/app/geo/scenario_builder.py). This is the only scenario
 * creation path this console uses — there is no fixed/fake grid demo.
 */
export function createGeoScenario(
  payload: GeoScenarioCreateRequest,
): Promise<GeoScenarioCreateResponse> {
  return request<GeoScenarioCreateResponse>("/scenarios/geo", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** GET /scenarios/{session_id} */
export function getScenario(sessionId: string): Promise<ScenarioStateResponse> {
  return request<ScenarioStateResponse>(
    `/scenarios/${encodeURIComponent(sessionId)}`,
  );
}

/** POST /scenarios/{session_id}/start */
export function startScenario(sessionId: string): Promise<StartResponse> {
  return request<StartResponse>(
    `/scenarios/${encodeURIComponent(sessionId)}/start`,
    { method: "POST" },
  );
}

/** POST /scenarios/{session_id}/step */
export function stepScenario(sessionId: string): Promise<StepResponse> {
  return request<StepResponse>(
    `/scenarios/${encodeURIComponent(sessionId)}/step`,
    { method: "POST" },
  );
}

/** POST /scenarios/{session_id}/run */
export function runScenario(
  sessionId: string,
  payload: RunRequest = {},
): Promise<RunResponse> {
  return request<RunResponse>(
    `/scenarios/${encodeURIComponent(sessionId)}/run`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

/** GET /scenarios/{session_id}/metrics */
export function getMetrics(sessionId: string): Promise<MetricsResponse> {
  return request<MetricsResponse>(
    `/scenarios/${encodeURIComponent(sessionId)}/metrics`,
  );
}

/**
 * GET /scenarios/{session_id}/agents/{agent_id}/route
 *
 * Returns null when the agent has no active route (idle, unassigned,
 * or already returned home) rather than throwing — per this endpoint's
 * own spec, a 404 here means "nothing to show," not a failure. Any
 * other error status still throws normally via ApiError.
 */
export async function getAgentRoute(
  sessionId: string,
  agentId: string,
): Promise<AgentRouteResponse | null> {
  try {
    return await request<AgentRouteResponse>(
      `/scenarios/${encodeURIComponent(sessionId)}/agents/${encodeURIComponent(agentId)}/route`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}
