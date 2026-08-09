# Simulation Model Design

## Purpose

The Simulation Engine connects World, Agent, Mission, and Path Planner into a running multi-agent simulation. It is the module that actually moves agents, drains battery, and advances missions from ASSIGNED to COMPLETED or FAILED, tick by tick.

The Simulation Engine does not decide *which* agent should work *which* mission — that is the Planning Engine's job, performed before the Simulation Engine ever sees a mission. It does not compute *how* to get from one cell to another — that is the Path Planner's job. The Simulation Engine's job is narrower and more mechanical: given an assignment that already exists and a route that Path Planner can compute, advance it, tick by tick, and keep World, Agent, and Mission state honest as it does.

A drone is only one example of an agent, exactly as established in the Agent Model. The Simulation Engine's execution logic is written entirely in terms of generic Agent fields (position, battery_level, health_status, activity, capabilities) and is not redesigned around any specific platform.

This Version 1 is a **software coordination layer over a simulated world**. It does not control real hardware. Real drone or robot integration would require a real autopilot interface (e.g. MAVLink or an equivalent flight-controller API), live telemetry, networked safety systems, and hardware-in-the-loop testing — none of which exist here. Every position, battery level, and movement in this module is simulated state inside `World` and `AgentRegistry`, not a real-world signal.

---

# Design Goals

- Deterministic: the same sequence of `step()` calls against the same starting state always produces the same outcome
- Owns execution/time state only; never duplicates World, Agent, or Mission state
- Reuses Path Planner for all route computation; never computes a path itself
- Never decides which agent is assigned to which mission; only acts on assignments that already exist
- Supports multiple agents executing at the same time, independently
- Simple, explainable battery and safety model — no physics, no prediction beyond straightforward arithmetic
- Leaves room for future multi-agent collision avoidance without needing to solve it now

---

# Dependencies

The Simulation Engine depends on:

- World
- Agent
- Mission
- Path Planner

A `SimulationEngine` instance is constructed with references to a `World`, an `AgentRegistry`, a `MissionRegistry`, and a `PathPlanner`. It holds no other external state.

The Simulation Engine does **not** depend on the Planning Engine. A caller — today, whoever is driving the simulation; eventually, a Dashboard or scheduler — is responsible for calling `PlanningEngine.plan()` (or `assign_mission` / `replan`) to produce ASSIGNED missions. The Simulation Engine only ever reads missions that are already ASSIGNED; it never matches agents to missions itself.

---

# Responsibilities

The Simulation Engine:

- Finds missions with status ASSIGNED and begins executing them.
- Before committing to a mission, checks that the assigned agent has enough battery for the full round trip (see "Battery Model"). If not, the mission fails immediately, before the agent moves at all.
- Computes an outbound route (via Path Planner) from the agent's current position to the nearest cell of the mission's target_cells.
- Advances each active agent by one cell per tick along its current route, respecting obstacles and occupied cells exactly as `World.is_walkable` reports them.
- Decreases agent battery_level by a fixed cost for each move.
- Marks a mission COMPLETED when its agent reaches the target, and sends the agent on a return trip to where it started.
- Marks a mission FAILED when it cannot be safely started, or when the assigned agent's health stops being ONLINE mid-execution.
- Updates Mission status and Agent activity as execution progresses (see "Execution Lifecycle").
- Keeps World's occupancy state in sync with agent positions while agents are under active execution (see "Occupancy").

The Simulation Engine does **not**:

- Decide which agent is assigned to which mission (Planning Engine's responsibility).
- Compute routes itself — every route comes from Path Planner.
- Perform predictive multi-agent collision avoidance (see "Future Extensions").
- Model realistic battery physics, weather, or terrain cost.
- Control real drone or robot hardware.

---

# Execution Lifecycle

A mission and its assigned agent move through the following phases once the Simulation Engine picks the mission up.

1. **ASSIGNED → round-trip check.** The Simulation Engine computes an outbound route to the nearest target cell and a return route back to the agent's current position. If either route does not exist, or the agent's battery is insufficient for both combined, the mission is marked FAILED and the agent is returned to IDLE without moving.

2. **IN_PROGRESS / EXECUTING_MISSION.** If the round-trip check passes, Mission status becomes IN_PROGRESS and Agent activity becomes EXECUTING_MISSION. Each subsequent tick, the agent advances one cell along the outbound route.

3. **COMPLETED / RETURNING.** When the agent reaches the target cell, Mission status becomes COMPLETED. The mission's work is done — the Simulation Engine no longer tracks it — but the agent is not yet idle: Agent activity becomes RETURNING, and the Simulation Engine begins advancing it back toward its original position, one cell per tick, using the same movement and occupancy rules as the outbound trip.

4. **IDLE.** When the agent reaches its original position, Agent activity becomes IDLE and current_mission_id is cleared. The Simulation Engine stops tracking it until it picks up a new ASSIGNED mission.

If an obstacle-free but currently occupied cell blocks the next step (another agent is standing there), the agent waits — it does not move, and it does not lose battery for a tick spent waiting. If an agent's health_status stops being ONLINE while it is EXECUTING_MISSION or RETURNING, it stops moving immediately; if it was still outbound, its mission is marked FAILED.

---

# Battery Model

Version 1's battery model is intentionally simple and deterministic:

- Each move (one cell-to-cell step along a route) costs a fixed amount of battery.
- Waiting for an occupied cell costs nothing.
- Before a mission begins, the Simulation Engine checks that battery_level is enough to cover the entire outbound route plus the entire return route, computed once via Path Planner. This is the round-trip safety check described in "Execution Lifecycle".
- There is no in-flight recharging and no battery regeneration in Version 1 — an agent's battery only ever goes down during execution.

This guarantees an agent never starts a mission it cannot also return from, and battery is never allowed to reach zero while an agent is still under active execution — the round-trip check makes that condition unreachable by construction, not by monitoring for it after the fact. Version 1 does not simulate charging, so once an agent is idle with a low battery, subsequent missions may fail the round-trip check until its battery is manually adjusted (e.g. by whatever process manages recharging in a future version).

---

# Occupancy

Unlike the Path Planner, which only reads World through its public API, the Simulation Engine also calls World's internal occupancy hooks (documented as private in docs/world-api.md and reserved for exactly this purpose in docs/agent-api.md and docs/path-planner-api.md). As it moves an agent, the Simulation Engine releases the agent's old cell and occupies its new one, so that `World.is_walkable` — and therefore every other active agent's Path Planner queries — correctly treats it as an obstacle in place.

Version 1 only tracks occupancy for agents currently under active execution (EXECUTING_MISSION or RETURNING). An agent's cell is occupied when the Simulation Engine begins tracking it and released when the agent reaches IDLE. Idle agents that have never been picked up for a mission are not occupied by the Simulation Engine — their positions are set by whatever process registered them, outside the Simulation Engine's control. See "Future Extensions".

---

# Multi-Agent Execution

Each tick, the Simulation Engine advances every currently-tracked agent independently — one move each, in some consistent order. Because occupancy is checked immediately before each individual move, two agents can never move into the same cell in the same tick: whichever is processed first occupies the cell, and the other sees it as occupied and waits.

This is deliberately simple reactive behavior, not planning: an agent does not know in advance that its path will cross another agent's, it only discovers a blocked cell when it tries to move into it. Anticipating and avoiding such conflicts before they happen is left to a future coordination layer — see "Future Extensions".

---

# Simulation State

The Simulation Engine owns execution state that does not exist anywhere else in the system:

- The current tick count.
- For each actively-tracked agent: which route it is following, how far along that route it is, and (while still outbound) which mission and launch position it will return to.

The Simulation Engine does not store

- Agent position, battery, health, or activity (owned by Agent)
- Mission status or assigned agents (owned by Mission)
- Grid, obstacles, or occupancy data itself (owned by World; the Simulation Engine only calls World's hooks to keep it updated)
- Routes beyond what is needed for the agents currently executing (Path Planner recomputes on demand; nothing is cached long-term)

---

# Public Interface

The Simulation Engine exposes the following operations.

## Step

Output

A summary of what happened during this tick: agents that moved, agents that waited, agents that arrived (mission completed or returned home), and missions that failed

---

## Simulation Summary

Output

Aggregate counts describing the current simulation state

---

# Constraints

The Simulation Engine never assigns an agent to a mission.

The Simulation Engine never computes a route itself; every route comes from Path Planner.

The Simulation Engine never lets a mission begin without enough battery for the full round trip.

The Simulation Engine only reaches into World's internal occupancy hooks — never into Agent's, Mission's, Planning Engine's, or Path Planner's internals.

The Simulation Engine does not control real hardware.

---

# Future Extensions

Not part of MVP.

- Predictive multi-agent collision avoidance (reserving cells in advance, not just reacting to them)
- Occupancy tracking for all registered agents, not just those under active execution
- Recharging at charging stations, and returning to the nearest one instead of the launch position
- A configurable battery safety margin beyond the exact round-trip cost
- Dynamic replanning when the World changes mid-execution (ties to the same extension already noted in docs/path-planner-model.md)
- Variable move cost (terrain, speed, platform differences)
- Real drone/robot hardware integration via a flight-controller API (e.g. MAVLink), telemetry, and networked safety systems
- Event logging of every tick, for the future Event Engine and Replay

---

# Design Principles

1. Simulation Engine never decides which agent works which mission.

2. Simulation Engine never computes a route itself.

3. Simulation Engine never lets an agent begin a mission it cannot also return from.

4. Simulation Engine never duplicates World, Agent, or Mission state — it reads and writes them only through their existing public APIs, with occupancy as the one documented, anticipated exception.

5. Simulation Engine is deterministic: the same starting state and sequence of ticks always produce the same outcome.

6. Simulation Engine does not control real hardware — it is a software coordination layer over a simulated world.

This keeps the Simulation Engine a thin execution loop over four independently-built modules, and gives ARGUS a complete, explainable story: agents exist, missions exist, Planning Engine matches them, Path Planner routes them, and the Simulation Engine is what actually makes them move.