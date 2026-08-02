# Agent Model Design

## Purpose

The Agent Model represents the state of every autonomous agent operating inside the simulation.

A drone is only one example of an agent. The same model must support ground robots, autonomous vehicles, and future platform types without modification.

The Planning Engine, Route Planner, Dashboard, Event Engine, and Simulation Engine all read agent state from this module.

The Agent Model does **not** contain business logic or planning algorithms. Its responsibility is only to describe agent state.

---

# Design Goals

- Generic across platform types (drones, ground robots, autonomous vehicles, future platforms)
- Simple to understand
- Fast to query
- Easy to extend
- Independent from the World Model
- Independent from the Planning Engine
- Independent from the UI

---

# Coordinate System

Agent positions use the same coordinate system as the World Model: a two-dimensional Cartesian grid, origin (0,0), increasing X to the east, increasing Y to the north.

The Agent Model does not validate positions against any specific world's dimensions. See "Design Principles."

---

# Agent Identity

Every agent has a unique identity and a platform type.

Properties

- id
- platform_type

platform_type is represented by the PlatformType enum.

Values

- DRONE
- GROUND_ROBOT
- AUTONOMOUS_VEHICLE
- MARINE_VEHICLE

PlatformType is descriptive only in Version 1. It does not affect validation or behavior.

Future versions may use PlatformType to influence movement rules or default capabilities.

---

# Position

Every agent has a position expressed in the coordinate system above.

Properties

- x
- y

The Agent Model validates only that x and y are non-negative. It does not know any world's width or height, and does not check whether a position is walkable, obstacle-free, or already occupied by another agent. See "Design Principles."

---

# Battery

Properties

- battery_level

Range: 0-100.

The Agent Model stores the current battery level only. It never predicts remaining operating time, drain rate, or charging duration. See "Design Principles."

---

# Capabilities

Capabilities describe what an agent can sense or do, independent of platform type.

Properties

- capabilities

Examples

- thermal_camera
- standard_camera
- lidar
- gps

Capabilities are descriptive tags only. Version 1 does not validate them against a fixed list, and they do not affect movement or validation behavior.

Set once at registration. Version 1 has no operation to change an agent's capabilities afterward.

Future versions may support dynamic capability changes (e.g. equipment swaps) and capability-based validation.

---

# Health Status

Health Status describes whether an agent is operating normally.

Values

- ONLINE
- FAILED
- OFFLINE

Health Status is independent of Agent Activity — see "Agent Activity."

The Agent Model stores whatever health status it is told. It never infers health from battery level or any other field. See "Design Principles."

---

# Agent Activity

Agent Activity describes what an agent is currently doing.

Values

- IDLE
- ASSIGNED
- EXECUTING_MISSION
- RETURNING
- CHARGING

Agent Activity is independent of Health Status.

The Agent Model stores whatever activity it is told. It never decides when an agent should transition between activities — that is the Planning Engine's responsibility.

---

# Current Mission

Properties

- current_mission_id

Optional. Null when the agent is not currently associated with a mission.

The Agent Model stores this reference only. It does not validate that the referenced mission exists — the Mission module is not part of this version.

Version 1 does not enforce consistency between current_mission_id and Agent Activity (e.g. an agent may have activity=ASSIGNED with no current_mission_id set). Keeping them consistent is the caller's responsibility.

---

# Agent State

The Agent Model stores

- id
- platform_type
- x
- y
- battery_level
- health_status
- activity
- capabilities
- current_mission_id
- registered_at

It does not store

- Planning decisions
- Route calculations
- Mission assignment decisions
- Battery predictions
- World occupancy

---

# Public Interface

The Agent Model exposes the following operations.

## Register Agent

Input

Agent

---

## Remove Agent

Input

Agent ID

---

## Get Agent

Input

Agent ID

Output

Agent state

---

## Update Position

Input

Agent ID

New Position

---

## Update Battery

Input

Agent ID

New Battery Level

---

## Update Health Status

Input

Agent ID

New Health Status

---

## Update Activity

Input

Agent ID

New Activity

---

## Assign Mission

Input

Agent ID

Mission ID

---

## Clear Mission

Input

Agent ID

---

## List Agents

Output

All registered agents

---

## Agent Summary

Output

Aggregate counts by health status and activity

Used by

- Dashboard
- Planning Engine
- Simulation Engine

---

# Constraints

Agent id must be unique.

Position coordinates must be non-negative.

Battery level must be between 0 and 100.

Health Status must be one of the defined values.

Agent Activity must be one of the defined values.

The Agent Model does not depend on the World Model (Version 1).

---

# Future Extensions

Not part of MVP.

- Heading / orientation
- Speed / velocity
- Altitude (for aerial agents)
- Fuel-based (non-battery) energy models
- Dynamic capability changes
- Task-level granularity below Current Mission
- Agent groups / formations
- Agent-to-agent communication links
- Richer health telemetry (temperature, signal strength, diagnostics)
- Capability-based validation
- World/Agent synchronization, owned by a future Simulation/Orchestrator module
- Payload capacity / payload weight

---

# Design Principles

1. Agent Model never performs planning.

2. Agent Model never allocates tasks or assigns missions.

3. Agent Model never predicts battery life or computes routes.

4. Agent Model never depends on the World Model.

5. Agent Model only stores agent state.

This separation keeps the architecture clean, keeps Agent and World independently testable, and lets the same Agent Model represent any future platform type without modification.