# API Specification

## Purpose

This specification defines the HTTP endpoints ARGUS exposes, their request and response shapes, and their error behavior. It implements exactly the responsibilities described in docs/api-model.md.

Every endpoint calls an existing backend method and serializes the result. No endpoint contains a planning, routing, or execution decision.

---

# Create Scenario

```
POST /scenarios
```

Creates a new session: a World, AgentRegistry, and MissionRegistry, populated from the request body. Does not run PlanningEngine.plan() -- the session starts in phase not_started, and every mission is PENDING.

Request body:

```json
{
    "world": {"width": 12, "height": 12},
    "obstacles": [
        {"id": "wall-0", "x": 6, "y": 0, "type": "Wall"}
    ],
    "agents": [
        {
            "id": "drone-thermal",
            "platform_type": "DRONE",
            "x": 0,
            "y": 0,
            "battery_level": 90,
            "capabilities": ["thermal_camera"]
        }
    ],
    "missions": [
        {
            "id": "thermal-survey",
            "name": "Thermal Survey",
            "description": "Requires a thermal camera.",
            "priority": "HIGH",
            "target_cells": [[9, 3]],
            "required_capabilities": ["thermal_camera"]
        }
    ]
}
```

Every field not shown a sensible default for (health_status, activity, mission status, and so on) is set to the same default the underlying dataclass already uses -- this endpoint does not invent new defaults.

Returns:

```json
{"session_id": "b3f1...", "phase": "not_started"}
```

Raises:

- `422 Unprocessable Entity` if the request body fails Pydantic validation (matches the underlying dataclass's own validation -- e.g. an empty world, a duplicate agent id, an empty mission name)

---

# Get State

```
GET /scenarios/{session_id}
```

Returns the session's current phase, world summary, every agent, every mission, and the current simulation summary.

Returns:

```json
{
    "session_id": "b3f1...",
    "phase": "in_progress",
    "tick": 4,
    "world": {"width": 12, "height": 12, "obstacles": 9, "spawn_points": 0, "charging_stations": 0, "mission_zones": 0},
    "agents": [ { "...Agent fields as in docs/api-model.md, \"State Serialization\"..." } ],
    "missions": [ { "...Mission fields..." } ],
    "simulation_summary": { "...SimulationEngine.simulation_summary()..." }
}
```

Raises:

- `404 Not Found` if session_id does not exist

---

# Start Scenario

```
POST /scenarios/{session_id}/start
```

Runs PlanningEngine.plan() exactly once against this session's agents and missions. Moves the session to phase in_progress.

Returns:

```json
{"planning_results": [{"mission_id": "thermal-survey", "assigned_agent_id": "drone-thermal"}]}
```

`planning_results` is exactly what PlanningEngine.plan() returned.

Raises:

- `404 Not Found` if session_id does not exist
- `409 Conflict` if the session has already been started

---

# Step

```
POST /scenarios/{session_id}/step
```

Calls SimulationEngine.step() exactly once and returns its result.

Returns:

```json
{"tick": 4, "moved": ["drone-thermal"], "waiting": [], "completed_missions": [], "failed_missions": [], "returned_home": []}
```

This is exactly the dict SimulationEngine.step() returned.

Raises:

- `404 Not Found` if session_id does not exist
- `409 Conflict` if the session has not been started yet, or has already settled

---

# Run

```
POST /scenarios/{session_id}/run
```

Calls SimulationEngine.step() repeatedly until the session settles or max_ticks is reached -- the same termination check Scenario Runner already uses.

Request body:

```json
{"max_ticks": 200}
```

`max_ticks` defaults to Scenario Runner's own default if omitted.

Returns:

```json
{
    "ticks_run": 49,
    "terminated_reason": "no_active_agents",
    "tick_results": [ { "...one entry per tick, each shaped like Step's response..." } ]
}
```

Raises:

- `404 Not Found` if session_id does not exist
- `409 Conflict` if the session has not been started yet, or has already settled
- `422 Unprocessable Entity` if max_ticks is not a positive integer

---

# Get Metrics

```
GET /scenarios/{session_id}/metrics
```

Returns the same aggregate counts AgentRegistry.agent_summary(), MissionRegistry.mission_summary(), and SimulationEngine.simulation_summary() already compute, reshaped into one response.

Returns:

```json
{
    "agent_summary": { "...AgentRegistry.agent_summary()..." },
    "mission_summary": { "...MissionRegistry.mission_summary()..." },
    "simulation_summary": { "...SimulationEngine.simulation_summary()..." }
}
```

Raises:

- `404 Not Found` if session_id does not exist

---

# Routes

Not part of Version 1's public API.

Path Planner computes routes on request and Simulation Engine tracks each active agent's current route internally, but nothing currently exposes "what route is agent X on right now" as a read-only fact. Adding this endpoint requires a decision this document does not make on its own: either recompute a route live via PathPlanner.find_path() from the agent's current position (available today, no backend change, but a fresh computation rather than a read of Simulation Engine's actual internal state), or add a minimal read-only accessor to SimulationEngine exposing what it already tracks (a small, genuine addition to an existing module). See docs/api-model.md, "Future Extensions".

---

# Error Behavior

Every error response has the shape:

```json
{"detail": "human-readable message"}
```

This is FastAPI's default error shape, not a custom one.

| Status | Meaning |
|---|---|
| 404 | session_id does not refer to an existing session |
| 409 | The requested action does not fit the session's current phase (e.g. stepping before starting, starting twice) |
| 422 | The request body failed validation |

No endpoint returns a 500 for a condition already handled by the backend as normal, non-error behavior (an unreachable mission, insufficient battery, a blocked cell) -- those are reported in the response body exactly as the backend already reports them, not converted into HTTP errors.

---

# Simulation Control

There is no pause endpoint. Step and Run execute synchronously within one HTTP request; there is no background execution for a client to pause. A frontend animates tick by tick by calling Step repeatedly (or Run once, for "play to completion"), not by starting a background process and later stopping it.

---

# WebSocket Integration (Future)

Not implemented in Version 1. When added, a WebSocket endpoint would call the same session-stepping logic the REST Step endpoint already calls, and push each tick's result to connected clients as it happens, rather than requiring the client to poll. This is additive to the REST design, not a replacement for it -- see docs/api-model.md, "Future Extensions".

---

# What Is Intentionally Not Implemented Yet

- Authentication and authorization.
- Persisting sessions across a process restart.
- Running more than one session concurrently against shared, persistent state (each session's objects are independent in memory, so concurrent sessions already work -- what is not implemented is surviving a restart).
- Replanning or restarting an in-progress session.
- WebSocket push updates.
- A dedicated routes endpoint (see "Routes" above).
- Rate limiting.

---

# Public API

Only these endpoints are part of Version 1.

```
POST   /scenarios
GET    /scenarios/{session_id}
POST   /scenarios/{session_id}/start
POST   /scenarios/{session_id}/step
POST   /scenarios/{session_id}/run
GET    /scenarios/{session_id}/metrics
```