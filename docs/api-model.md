# API Model Design

## Purpose

The API layer exposes ARGUS's existing backend (World, Agent, Mission, Planning Engine, Path Planner, Simulation Engine, Scenario Runner) over HTTP so a frontend can create scenarios, inspect state, and control simulation execution tick by tick.

The API layer contains no planning, routing, or simulation logic of its own. Every meaningful decision — which agent works which mission, what route an agent takes, how battery drains, when a mission completes or fails — is made by the existing modules, exactly as already implemented and tested. The API's job is narrower: hold a live scenario in memory across HTTP requests, call the existing modules' existing public methods, and translate their existing dataclasses and enums into JSON.

This is the first ARGUS layer that talks to the outside world. Every layer before it (World through Scenario Runner) is a plain Python library with no knowledge that HTTP exists.

---

# Design Goals

- Thin: every endpoint handler calls existing methods and serializes the result, nothing more
- No duplicated logic: capability matching, route computation, battery rules, and execution state transitions are never reimplemented here
- Session-based: a scenario's live objects persist in memory across requests, so tick-by-tick control is possible without re-running from scratch
- Simple over scalable: an in-memory session store is the right size for a prototype; the design says explicitly where it would need to change to grow, rather than building that growth in now
- REST first: WebSocket support is designed for, not built, until a real need for server-pushed updates exists
- Honest about state: the API never claims to know something the backend doesn't expose

---

# Dependencies

The API layer depends on:

- World
- Agent
- Mission
- Planning Engine
- Path Planner
- Simulation Engine
- Scenario Runner

It uses FastAPI and Pydantic for the HTTP and serialization layer, both already listed in requirements.txt.

It does **not** depend on SQLAlchemy, psycopg, Redis, or WebSockets in Version 1, despite these being present in requirements.txt for future phases. See "Future Extensions" in docs/api-spec.md for exactly when each would become necessary.

---

# Responsibilities

The API layer:

- Creates a new scenario: a World, AgentRegistry, and MissionRegistry, populated from a request.
- Starts a scenario: runs PlanningEngine.plan() exactly once against it.
- Advances a scenario: calls SimulationEngine.step(), once or repeatedly, up to a safety limit.
- Reports scenario state: the current World, agents, missions, and simulation summary, translated to JSON.
- Reports scenario metrics: the same aggregate counts AgentRegistry, MissionRegistry, and SimulationEngine already compute, not new ones.
- Keeps each scenario's live objects (World, AgentRegistry, MissionRegistry, PlanningEngine, PathPlanner, SimulationEngine) associated with one session id across requests.

The API layer does **not**:

- Decide which agent is assigned to which mission.
- Compute a route.
- Decide when a mission completes, fails, or an agent waits.
- Modify World, Agent, or Mission state directly. Every state change happens by calling an existing module's existing public method.
- Persist scenario state beyond the process's lifetime in Version 1.
- Push updates to a client without being asked, in Version 1.

---

# Session Lifecycle

A session wraps one scenario's live objects and tracks where it is in three phases:

1. **not_started** — World, AgentRegistry, and MissionRegistry exist and are populated. No planning has run. Every mission is PENDING.
2. **in_progress** — PlanningEngine.plan() has run once. SimulationEngine may have advanced zero or more ticks. At least one mission is not PENDING, or at least one agent is not IDLE.
3. **settled** — SimulationEngine has nothing left executing or returning, and no mission is still ASSIGNED waiting to be picked up. This mirrors Scenario Runner's own termination check exactly, not a new definition.

A session holds:

- A unique session id.
- The World, AgentRegistry, MissionRegistry, PlanningEngine, PathPlanner, and SimulationEngine for this scenario.
- The current phase.
- The planning results from the one PlanningEngine.plan() call, once it has run.
- Every tick result SimulationEngine.step() has returned so far, in order.

A session's PlanningEngine.plan() call happens at most once. Re-running planning on a session that has already started is out of scope for Version 1 — see "Future Extensions" in docs/api-spec.md.

There is no explicit "pause." Because stepping happens synchronously within a single HTTP request, there is no background execution to pause — a client simply stops calling step or run. See docs/api-spec.md, "Simulation Control".

---

# State Serialization

Every response is built from the existing dataclasses and enums, field for field:

- World → its width, height, and a summary (world_summary()'s own dict) rather than every cell, since the grid can be large and most cells are empty. Obstacles, spawn points, charging stations, and mission zones are listed explicitly.
- Agent → id, platform_type, x, y, battery_level, health_status, activity, capabilities, current_mission_id, registered_at. Enum fields serialize to their string value.
- Mission → id, name, description, priority, status, required_capabilities, target_cells, assigned_agent_ids, created_at.
- Route → cells and length, exactly as Path Planner defines them.
- Tick results, planning results, and every summary → the same dicts SimulationEngine.step(), PlanningEngine.plan(), AgentRegistry.agent_summary(), MissionRegistry.mission_summary(), and SimulationEngine.simulation_summary() already return, reshaped into a response model but not recomputed.

No field is invented that the backend does not already expose. If a future frontend needs something the backend does not currently report, that is a backend change to propose separately, not something to approximate in the API layer.

---

# Frontend/Backend Boundary

The frontend is responsible for:

- Displaying the world, agents, missions, routes, and metrics.
- Providing controls (create, start, step, run).
- Any animation, layout, or visual styling.

The frontend is never responsible for and never receives the tools to:

- Decide an assignment, a route, or a state transition.
- Read or write World/Agent/Mission state directly. Every change happens through an API endpoint, which calls an existing module's existing method.

If a future frontend need would require backend logic to move into the API layer or the frontend, that is a sign the backend is missing a capability, not a reason to duplicate one.

---

# Security Considerations

Version 1 is an engineering prototype, not a deployed multi-user system. Accordingly:

- No authentication or authorization. Every session is accessible to anyone who can reach the API.
- CORS is open to the frontend's local development origin only.
- Session ids are not treated as secrets; they are convenience identifiers, not access control.
- No rate limiting.

These are explicit, deliberate simplifications for a college project's demonstration scope, not oversights — production deployment would need all of the above before being exposed beyond a local demo.

---

# Future Extensions

Not part of Version 1.

- WebSocket support for server-pushed tick updates, once a client genuinely needs updates without polling.
- Persisting sessions in a database (SQLAlchemy/psycopg) once scenarios need to survive a process restart or be shared across multiple API workers.
- Redis-backed sessions once the API runs as more than one process.
- Re-running or replanning an in-progress session.
- Authentication, once this moves beyond a local demo.
- A route-history endpoint reflecting exactly what SimulationEngine has internally tracked per agent, if a read-only accessor is added to SimulationEngine for this purpose — see docs/api-spec.md, "Routes".

---

# Design Principles

1. The API layer never makes a planning, routing, or execution decision.

2. The API layer never duplicates a rule already implemented in World, Agent, Mission, Planning Engine, Path Planner, or Simulation Engine.

3. The API layer never reports a fact the backend does not already expose.

4. Every state change happens through an existing module's existing public method.

5. The session store is as simple as the current requirements allow, not as complex as future requirements might eventually need.

This keeps the API layer a thin, honest translation of an already-correct backend, and leaves growth (persistence, real-time push, multi-process scaling) as clearly-marked future work rather than premature architecture.