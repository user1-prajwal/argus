# Planning API Specification

## Purpose

The Planning API defines the public interface for running planning decisions over the current World, Agent, and Mission state.

Only the `PlanningEngine` class should be used by other modules.

The Planning Engine has no persistent internal state of its own to protect — every call reads the current state of the `World`, `AgentRegistry`, and `MissionRegistry` it was constructed with. It changes Agent and Mission state only through their existing public methods (`AgentRegistry.update_activity`, `AgentRegistry.assign_mission`, `AgentRegistry.clear_mission`, `MissionRegistry.update_status`, `MissionRegistry.assign_agents`, `MissionRegistry.clear_agents`), and never modifies World state or reaches into any module's internals.

The Planning Engine does not own application state. Future modules such as the Simulation Engine may invoke it through its public API.

---

# Create Engine

```
engine = PlanningEngine(world, agents, missions)
```

Creates a new Planning Engine bound to a specific World, AgentRegistry, and MissionRegistry.

Raises:

- `TypeError`

---

# Plan

```
results = engine.plan()
```

Considers every PENDING mission, highest priority first, and attempts to assign the most appropriate available agent to each — see docs/planning-model.md, "Assignment Selection". An agent successfully assigned during this call is no longer available for the remaining missions in the same call.

Returns a list with one entry per pending mission considered, in the order processed:

```
[
    {"mission_id": "m1", "assigned_agent_id": "a3"},
    {"mission_id": "m2", "assigned_agent_id": None}
]
```

`assigned_agent_id` is `None` when no eligible agent was found; the mission is left PENDING.

---

# Assign Mission

```
result = engine.assign_mission(mission_id)
```

Attempts to assign the most appropriate available agent to a mission.
Only missions in the PENDING state are eligible for assignment.
If the mission is in any other state, no assignment is performed.Does not release any agent the mission may already have.

Returns:

```
{"mission_id": "m1", "assigned_agent_id": "a3"}
```

`assigned_agent_id` is `None` when no eligible agent was found.

Raises:

- `MissionNotFoundError`

---

# Replan

```
result = engine.replan(mission_id)
```

Releases the mission's current assignment, if any — reverting any previously assigned agent to activity IDLE with no current mission, and the mission to status PENDING — then attempts a fresh assignment exactly like `assign_mission`.

Returns:

```
{"mission_id": "m1", "assigned_agent_id": "a7"}
```

`assigned_agent_id` is `None` when no eligible agent was found after release.

Raises:

- `MissionNotFoundError`

---

# Planning Summary

```
summary = engine.planning_summary()
```

Returns

```
{
    "pending_missions": 5,
    "available_agents": 3,
    "assignable_missions": 2,
    "unassignable_missions": 3
}
```

`assignable_missions` is the number of pending missions with at least one currently eligible agent; `unassignable_missions` is the rest.

---

# Validation Rules

Create Engine

- world must be a World instance
- agents must be an AgentRegistry instance
- missions must be a MissionRegistry instance

Assign Mission / Replan

- mission_id must refer to a mission that exists in the MissionRegistry

Eligibility (not a validation error — see docs/planning-model.md, "Availability and Eligibility")

- agent health_status must be ONLINE
- agent activity must be IDLE
- agent capabilities must be a superset of the mission's required_capabilities

No suitable agent is never an error. It is reported as `assigned_agent_id: None`.

---

# Public API

Only these methods are public.

```
PlanningEngine()

plan()

assign_mission()

replan()

planning_summary()
```

Everything else should be private.