# Planning Model Design

## Purpose

The Planning Engine is the first module in ARGUS that contains decision-making logic. Earlier modules (World, Agent, Mission) only store state; the Planning Engine reads that state and decides which agent should work which mission.

The Planning Engine does not own or duplicate World, Agent, or Mission state. It reads the World Model, the Agent Model, and the Mission Model through their existing public APIs, and it changes Agent and Mission state only by calling their existing public methods — never by reaching into their internals.

The Planning Engine does not own application state. Future modules such as the Simulation Engine may invoke it through its public API.

---

# Design Goals

- Simple, deterministic matching for Version 1
- Reads World, Agent, and Mission state; never duplicates it
- Mutates Agent and Mission state only through `AgentRegistry` and `MissionRegistry`'s existing public methods
- Never mutates World state
- Independent from the Dashboard, Event Engine, and Replay
- Easy to extend with a more sophisticated matching strategy later

---

# Dependencies

The Planning Engine depends on:

- World
- Agent
- Mission

A `PlanningEngine` instance is constructed with references to a `World`, an `AgentRegistry`, and a `MissionRegistry`. It holds no other state.

Version 1's matching logic (see "Assignment Selection") only reads from the Agent and Mission Models — capabilities, battery level, activity, health status, mission status, and required capabilities. It does not read from the World Model. The dependency on World is accepted at construction for forward compatibility (see "Future Extensions"), not exercised by any Version 1 responsibility.

---

# Responsibilities

The Planning Engine:

- Finds available agents.
- Finds pending missions.
- Matches agent capabilities to mission requirements.
- Assigns the most appropriate agent to a mission.
- Updates mission status.
- Updates agent activity.

The Planning Engine does **not**:

- Calculate paths.
- Perform collision avoidance.
- Simulate movement.
- Predict battery usage.
- Modify World state, directly or indirectly.

Path planning, collision avoidance, and movement simulation belong to a future Path Planner / Simulation Engine.

---

# Availability and Eligibility

An agent is **available** when:

- health_status is ONLINE, and
- activity is IDLE.

A mission is **pending** when:

- status is PENDING.

An agent is **eligible** for a mission when the agent is available and the agent's capabilities are a superset of the mission's required_capabilities. A mission with no required_capabilities can be worked by any available agent.

---

# Assignment Selection

Version 1 assigns at most one agent per mission. Among all eligible agents for a mission:

1. Prefer the agent with the higher battery_level.
2. If still tied, prefer the agent with the lower id (deterministic; not meaningful otherwise).

This is a simple, explicit tie-break — not a prediction of battery usage, and not a distance or path calculation. See "Design Principles."

If no agent is eligible, the mission is left PENDING and no state changes.

---

# State Changes

On a successful assignment, the Planning Engine calls:

- `MissionRegistry.assign_agents(mission_id, {agent_id})`
- `MissionRegistry.update_status(mission_id, MissionStatus.ASSIGNED)`
- `AgentRegistry.assign_mission(agent_id, mission_id)`
- `AgentRegistry.update_activity(agent_id, AgentActivity.ASSIGNED)`

IN_PROGRESS and EXECUTING_MISSION are not set by the Planning Engine — they belong to whichever future module actually tracks execution (e.g. a Simulation Engine).

On a release (see "Replan" in docs/planning-api.md), the Planning Engine calls:

- `AgentRegistry.update_activity(agent_id, AgentActivity.IDLE)`
- `AgentRegistry.clear_mission(agent_id)`
- `MissionRegistry.clear_agents(mission_id)`
- `MissionRegistry.update_status(mission_id, MissionStatus.PENDING)`

These are all pre-existing public methods on `AgentRegistry` and `MissionRegistry`. The Planning Engine adds no new methods to either module.

---

# Planning State

Unlike the World, Agent, and Mission Models, the Planning Engine stores no persistent state of its own. Every method reads the current state of the World, Agent, and Mission Models at call time and acts on it immediately.

The Planning Engine does not store

- A history of past decisions
- A queue of pending work
- Cached agent or mission state
- Explanations for its decisions

See "Future Extensions."

---

# Public Interface

The Planning Engine exposes the following operations.

## Plan

Output

One result per pending mission considered, each showing the mission and the agent assigned to it, if any

---

## Assign Mission

Input

Mission ID

Output

The mission and the agent assigned to it, if any

---

## Replan

Input

Mission ID

Output

The mission and the agent assigned to it, if any

---

## Planning Summary

Output

Aggregate counts describing the current planning picture

---

# Constraints

The Planning Engine assigns exactly one agent per mission in Version 1.

The Planning Engine never modifies World state.

The Planning Engine never adds methods to `AgentRegistry` or `MissionRegistry` — it only calls their existing public methods.

The Planning Engine does not persist any state of its own between calls.

---

# Future Extensions

Not part of MVP.

- Multi-agent assignment sizing (assigning more than one agent to a single large mission)
- Priority-aware preemption (reassigning a lower-priority mission's agent to a newly created CRITICAL mission)
- Automatic, event-triggered replanning (Version 1's replan is caller-invoked only)
- Proximity- or path-aware agent selection, once a Path Planner module exists
- Globally optimal assignment across the whole mission set, rather than a greedy per-mission match
- Explainable decisions (recording why a specific agent was chosen)
- Configurable or pluggable matching strategies
- Reading World state to validate that a mission's target cells are still reachable

---

# Design Principles

1. Planning Engine never calculates paths.

2. Planning Engine never performs collision avoidance or simulates movement.

3. Planning Engine never predicts battery usage.

4. Planning Engine never modifies World state.

5. Planning Engine never duplicates World, Agent, or Mission state — it always reads current state through their existing public APIs.

6. Planning Engine only mutates Agent and Mission state through `AgentRegistry` and `MissionRegistry`'s existing public methods.

7. The Planning Engine does not own application state. Future modules such as the Simulation Engine may invoke it through its public API.

This keeps the Planning Engine a thin decision-making layer on top of three independently-testable state stores, and leaves path calculation, collision avoidance, and movement simulation to modules built specifically for them.