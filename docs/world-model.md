# World Model Design

## Purpose

The World Model represents the virtual environment where all autonomous agents operate.

It is the single source of truth for the simulation.

The Planning Engine, Route Planner, Dashboard, and Simulation Engine all read the world state from this module.

The World Model does **not** contain business logic or planning algorithms. Its responsibility is only to describe the environment.

---

# Design Goals

- Simple to understand
- Fast to query
- Easy to extend
- Independent from the UI
- Independent from the Planning Engine

---

# Coordinate System

The simulation uses a two-dimensional Cartesian coordinate system.

Origin:

(0,0)

Increasing X moves east.

Increasing Y moves north.

Example:

```
(0,4) ---------------------- (9,4)

(0,3)

(0,2)

(0,1)

(0,0) ---------------------- (9,0)
```

---

# World Size

Version 1

100 x 100 cells

Future versions may support dynamic map sizes.

---

# Cell Types

Every position belongs to one of the following types.

| Type | Description |
|------|-------------|
| Empty | Free space |
| Obstacle | Cannot be crossed |
| MissionZone | Area to search |
| ChargingStation | Recharge point |
| SpawnPoint | Initial agent location |
| NoFlyZone | Forbidden area |

---

# Obstacles

Obstacles block movement.

Examples

- Building
- Tree
- Water
- Mountain

The Route Planner must avoid obstacle cells.

---

# Mission Zones

Mission Zones define areas assigned to missions.

Properties

- id
- name
- priority
- polygon/grid cells
- mission_id

A mission may contain multiple mission zones.

---

# Charging Stations

Charging stations allow agents to recharge.

Properties

- id
- position
- capacity
- occupied_slots

Version 1 assumes instant charging.

Future versions may simulate charging time.

---

# Spawn Points

Agents enter the world through spawn points.

Properties

- id
- position

---

# Agent Position

Every agent always occupies exactly one cell.

Properties

- x
- y

Agents cannot occupy obstacle cells.

---

# Movement

Version 1 supports four-direction movement.

Allowed

- Up
- Down
- Left
- Right

Diagonal movement is disabled.

Reason:

Simplifies A* implementation.

Future versions may enable diagonal movement.

---

# World State

The World Model stores

- Grid
- Obstacles
- Mission Zones
- Charging Stations
- Spawn Points
- Active Agents

It does not store

- Planning decisions
- Route calculations
- Mission assignments

---

# Public Interface

The World Model exposes the following operations.

## Query Cell

Input

(x,y)

Output

Cell information

---

## Is Walkable

Input

(x,y)

Output

True / False

---

## Get Neighbor Cells

Input

(x,y)

Output

Adjacent walkable cells

---

## Add Obstacle

Input

position

---

## Remove Obstacle

Input

position

---

## Add Agent

Input

Agent

---

## Remove Agent

Input

Agent ID

---

## Move Agent

Input

Agent ID

New Position

---

## Get World State

Returns complete world information.

Used by

- Dashboard
- Simulation Engine
- Planning Engine

---

# Constraints

Agents cannot

- move outside the world
- enter obstacle cells
- occupy the same cell (Version 1)

---

# Future Extensions

Not part of MVP.

- Dynamic obstacles
- Weather
- Terrain cost
- Elevation
- Real map integration
- Satellite imagery
- Multiple floors

---

# Design Principles

1. World Model never performs planning.

2. World Model never decides missions.

3. World Model never computes paths.

4. World Model only stores the environment.

This separation keeps the architecture clean and allows independent testing.