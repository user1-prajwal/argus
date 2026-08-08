# Path Planner Model Design

## Purpose

The Path Planner computes a route between two cells in the World Model. It is the second ARGUS module to contain algorithmic logic, after the Planning Engine — but its logic is pure pathfinding computation, not a business decision. Given a start and a goal, there is a single well-defined shortest route (subject to a deterministic tie-break); the Path Planner's job is to compute it, not to choose between competing priorities.

The Path Planner does not own or duplicate World state. It reads the World Model through its existing public API (`is_walkable`, `get_neighbors`) and produces a route. It never mutates World, Agent, or Mission state.

The Path Planner does not own application state. Future modules such as the Simulation Engine or Planning Engine may invoke it through its public API.

---

# Design Goals

- Deterministic: the same start, goal, and World state always produce the same route
- Correct: finds a shortest route when one exists, using only the moves the World Model allows
- Reads World state only; never duplicates it
- Never mutates World, Agent, or Mission state
- Independent from Agent, Mission, and the Planning Engine
- Simple enough to reason about and test exhaustively

---

# Dependencies

The Path Planner depends on:

- World

A `PathPlanner` instance is constructed with a reference to a single `World`. It holds no other state.

The Path Planner does not depend on Agent or Mission. It works entirely in terms of grid coordinates — a caller (such as a future Planning Engine) is responsible for translating an agent's position or a mission's target cells into the coordinates this module expects.

---

# Responsibilities

The Path Planner:

- Finds a route between a start cell and a goal cell.
- Uses only the movement the World Model allows: four-directional (Up, Down, Left, Right), no diagonals.
- Treats obstacles and currently-occupied cells as impassable, exactly as `World.is_walkable` reports them.
- Reports when no route exists.

The Path Planner does **not**:

- Simulate an agent moving along a route over time.
- Predict how long a route will take.
- Predict battery usage.
- Coordinate or avoid future collisions between multiple agents' routes.
- Modify World, Agent, or Mission state.
- Choose a destination — it is always given both a start and a goal.

Movement simulation and multi-agent route coordination belong to a future Simulation Engine.

---

# Algorithm

Version 1 uses A* search with Manhattan distance (`|dx| + |dy|`) as the heuristic. This heuristic never overestimates the true cost on a four-directional, unit-cost grid, so the route found is always a shortest route by cell count.

Each step (one move to an adjacent walkable cell) costs 1. There is no terrain cost in Version 1 — every walkable cell is equally expensive to enter.

When multiple shortest routes exist, the Path Planner resolves the tie deterministically rather than returning an arbitrary one — the same query against the same World state always returns the same route. See docs/path-planner-api.md for the exact tie-break.

---

# Route

Properties

- cells
- length

`cells` is an ordered sequence of (x, y) positions from the start cell to the goal cell, inclusive of both. `length` is the number of moves in the route (`len(cells) - 1`).

A route from a cell to itself is valid: `cells` contains just that one position, and `length` is 0.

Unlike Mission's target_cells, a route's cells are ordered — position in the sequence is the order the route is walked in.

---

# Path Planner State

Like the Planning Engine, the Path Planner stores no persistent state of its own. Every call reads the current state of the World Model at call time and computes a fresh result.

The Path Planner does not store

- Previously computed routes
- A cache of walkability results
- Any notion of which agent a route was computed for

---

# Public Interface

The Path Planner exposes the following operation.

## Find Path

Input

Start Position, Goal Position

Output

Route, or nothing if no route exists

---

# Constraints

The Path Planner never modifies World, Agent, or Mission state.

The Path Planner only reads World state through World's existing public methods (`is_walkable`, `get_neighbors`) — it never reaches into World's internals.

Start and goal positions must be within the World's bounds.

Start and goal need not be walkable — an unwalkable start or goal simply means no route exists, not an error.

The Path Planner does not persist any state of its own between calls.

---

# Future Extensions

Not part of MVP.

- Terrain costs (some cells more expensive to cross than others)
- Diagonal movement, if the World Model ever supports it
- Multi-agent route coordination (avoiding routes that would collide with each other over time)
- Route caching or incremental replanning when the World changes slightly
- Alternative or configurable heuristics
- Turning cost / minimum turning radius, for platforms that cannot pivot in place
- Dynamic replanning when newly discovered obstacles are reported by the World Model
---

# Design Principles

1. Path Planner never simulates movement over time.

2. Path Planner never predicts battery usage or travel time.

3. Path Planner never performs multi-agent collision avoidance.

4. Path Planner never modifies World, Agent, or Mission state.

5. Path Planner never duplicates World state — it always reads current state through World's existing public API.

6. Path Planner is deterministic: the same inputs against the same World state always produce the same route.

7. Path Planner stores no persistent state of its own.

This keeps the Path Planner a thin, stateless computation on top of the World Model, and leaves execution, timing, and multi-agent coordination to modules built specifically for them.