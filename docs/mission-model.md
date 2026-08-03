# Mission Model Design

## Purpose

The Mission Model represents work that must be completed inside the simulation: a search area, an inspection task, a delivery, or any other objective assigned to one or more agents.

The Planning Engine, Dashboard, and Event Engine all read mission state from this module.

The Mission Model does **not** contain business logic, planning, routing, scheduling, optimization, or battery prediction. Its responsibility is only to describe mission state.

---

# Design Goals

- Simple to understand
- Fast to query
- Easy to extend
- Independent from the World Model
- Independent from the Agent Model
- Independent from the Planning Engine
- Independent from the UI

---

# Coordinate System

Target cells use the same coordinate system as the World Model: a two-dimensional Cartesian grid, origin (0,0), increasing X to the east, increasing Y to the north.

The Mission Model does not validate target cells against any specific world's dimensions, and does not reference the World Model's Cell, MissionZone, or any other class. See "Design Principles."

---

# Mission Identity

Every mission has a unique identity, a name, and a description.

Properties

- id
- name
- description

---

# Priority

Priority describes how urgent a mission is.

Values

- LOW
- MEDIUM
- HIGH
- CRITICAL

Set once at creation. Version 1 has no operation to change a mission's priority afterward.

Priority does not affect how missions are stored or queried; ordering or scheduling by priority is the Planning Engine's responsibility.

---

# Status

Status describes where a mission is in its lifecycle.

Values

- PENDING
- ASSIGNED
- IN_PROGRESS
- COMPLETED
- FAILED
- CANCELLED

The Mission Model stores whatever status it is told. It never decides when a mission should transition between statuses, and does not enforce any particular transition order — that is the Planning Engine's responsibility.

---

# Required Capabilities

Required Capabilities describe what an agent needs in order to work this mission.

Properties

- required_capabilities

Reuses the `Capability` enum from the Agent Model (`backend/app/agent`) rather than defining a second one. This is the one point of contact between the Mission Model and the Agent Model — a shared vocabulary type only. The Mission Model does not import or reference `Agent` or `AgentRegistry`, and does not validate required_capabilities against any agent's actual capabilities. See "Design Principles."

Defaults to an empty frozenset.

---

# Target Cells

Target Cells describe the grid cells this mission covers.

Properties

- target_cells

Stored as an explicit, non-empty set of (x, y) cells — the same representation style as the World Model's Mission Zones, but an independent type. The Mission Model does not reference `MissionZone` or any other World Model class, and does not validate target cells against obstacles, world bounds, or any other World state.

Set once at creation. Version 1 has no operation to change a mission's target cells afterward.

---

# Assigned Agents

Assigned Agents describes which agents are currently working this mission.

Properties

- assigned_agent_ids

Stored as a set of agent id strings, not `Agent` objects. The Mission Model does not import `Agent` or `AgentRegistry`, and does not validate that an id refers to a real, registered agent. Multiple agents may be assigned to the same mission.

Defaults to an empty frozenset.

---

# Created At

Properties

- created_at

The UTC timestamp of when the mission was created. Set automatically; cannot be supplied or changed by the caller.

This is a record of creation time only. Version 1 has no scheduling, no deadlines, and no ETA calculations — see "Design Principles."

---

# Mission State

The Mission Model stores

- id
- name
- description
- priority
- status
- required_capabilities
- target_cells
- assigned_agent_ids
- created_at

It does not store

- Planning decisions
- Route calculations
- Task allocation results
- Scheduling or deadline data
- Agent objects
- World cells or obstacles

---

# Public Interface

The Mission Model exposes the following operations.

## Register Mission

Input

Mission

---

## Remove Mission

Input

Mission ID

---

## Get Mission

Input

Mission ID

Output

Mission state

---

## Update Status

Input

Mission ID

New Status

---

## Assign Agents

Input

Mission ID

Agent IDs

---

## Clear Agents

Input

Mission ID

---

## List Missions

Output

All registered missions

---

## Mission Summary

Output

Aggregate counts by status and priority

Used by

- Dashboard
- Planning Engine

---

# Constraints

Mission id must be unique.

Name and description must not be empty.

Target cells must not be empty.

Target cell coordinates must be non-negative.

Status must be one of the defined values.

Priority must be one of the defined values.

The Mission Model does not depend on the World Model.

The Mission Model does not depend on the Agent Model, except for reusing the `Capability` enum as a shared vocabulary type.

---

# Future Extensions

Not part of MVP.

- Deadlines / scheduling windows
- ETA calculations
- Sub-mission / task-level granularity
- Mission dependencies (mission B blocked by mission A)
- Mission templates
- Priority changes after creation
- Target cell changes after creation
- Validation of required_capabilities against assigned agents' actual capabilities
- Validation of assigned_agent_ids against a live Agent registry

---

# Design Principles

1. Mission Model never performs planning.

2. Mission Model never allocates tasks or selects agents.

3. Mission Model never computes routes, schedules, or ETAs.

4. Mission Model never predicts battery usage.

5. Mission Model never depends on the World Model.

6. Mission Model never depends on the Agent Model beyond reusing the `Capability` enum type.

7. Mission Model only stores mission state.

This separation keeps the architecture clean, keeps Mission, Agent, and World independently testable, and leaves all coordination — matching agents to missions, planning routes, tracking progress — to a future Planning Engine.