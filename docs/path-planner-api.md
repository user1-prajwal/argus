# Path Planner API Specification

## Purpose

The Path Planner API defines the public interface for computing routes across World state.

Only the `PathPlanner` class should be used by other modules.

Other modules must not directly modify `Route` or other internal classes.

The Path Planner has no persistent internal state of its own to protect — every call reads the current state of the `World` it was constructed with. It never modifies World, Agent, or Mission state, and never reaches into any module's internals.

The Path Planner does not own application state. Future modules such as the Simulation Engine or Planning Engine may invoke it through its public API.

---

# Create Planner

```
planner = PathPlanner(world)
```

Creates a new Path Planner bound to a specific World.

Raises:

- `TypeError`

---

# Find Path

```
route = planner.find_path(start_x, start_y, goal_x, goal_y)
```

Computes a shortest route from (start_x, start_y) to (goal_x, goal_y) using four-directional movement, treating obstacles and currently-occupied cells as impassable exactly as `World.is_walkable` reports them.

Ties between equally short routes are broken deterministically by considering neighboring cells in a fixed order (Up, Down, Left, Right). This guarantees that identical inputs always produce identical routes.

A start equal to the goal returns a route containing just that one cell, with length 0.

Returns a `Route`:

```
Route(
    cells=((0, 0), (0, 1), (1, 1)),
    length=2,
)
```

Returns `None` if no route exists — this is not an error. It happens when the goal is unreachable from the start given the World's current obstacles and occupied cells, or when the start or goal cell itself is not walkable.

Raises:

- `TypeError` if a coordinate is not an int
- `ValueError` if start or goal is outside the World's bounds

---

# Validation Rules

Create Planner

- world must be a World instance

Find Path

- start_x, start_y, goal_x, goal_y must be ints
- start and goal must each be within the World's bounds (0 <= x < width, 0 <= y < height)

Reachability (not a validation error — see docs/path-planner-model.md, "Constraints")

- start and goal do not need to be walkable
- an unreachable goal, or a start/goal that is not walkable, results in find_path returning None, not an exception

---

# Public API

Only these methods are public.

```
PathPlanner()

find_path()
```

Everything else should be private.