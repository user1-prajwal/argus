# World API Specification

## Purpose

The World API defines the public interface for interacting with the simulation world.

Only the `World` class should be used by other modules.

Other modules must not directly modify `Grid`, `Cell`, or other internal classes.

---

# Create World

```python
world = World(width=100, height=100)
```

Creates a new empty world.

---

# Properties

```python
world.width
world.height
```

Returns the dimensions of the world.

---

# Get Cell

```python
cell = world.get_cell(x, y)
```

Returns the `Cell` at `(x, y)`.

Raises:

- `ValueError` if coordinates are outside the world.

---

# Check Walkability

```python
world.is_walkable(x, y)
```

Returns:

```python
True
False
```

Returns `False` if:

- obstacle
- outside world
- occupied

---

# Add Obstacle

```python
world.add_obstacle(obstacle)
```

Raises:

- `ValueError`
- `DuplicateObstacleError`

---

# Remove Obstacle

```python
world.remove_obstacle(obstacle_id)
```

Raises:

- `ObstacleNotFoundError`

---

# Add Spawn Point

```python
world.add_spawn_point(spawn)
```

---

# Add Charging Station

```python
world.add_charging_station(station)
```

---

# Add Mission Zone

```python
world.add_mission_zone(zone)
```

---

# Neighbor Query

```python
world.get_neighbors(x, y)
```

Returns only walkable neighbors.

Movement:

- Up
- Down
- Left
- Right

No diagonal movement.

---

# World Summary

```python
summary = world.world_summary()
```

Returns

```python
{
    "width":100,
    "height":100,
    "obstacles":14,
    "spawn_points":2,
    "charging_stations":3,
    "mission_zones":5
}
```

---

# Validation Rules

Coordinates

- x >= 0
- y >= 0
- x < width
- y < height

Duplicate IDs are not allowed.

Mission zones cannot overlap obstacles.

Spawn points cannot be placed inside obstacles.

Charging stations cannot be placed inside obstacles.

---

# Public API

Only these methods are public.

```python
World()

get_cell()

is_walkable()

get_neighbors()

add_obstacle()

remove_obstacle()

add_spawn_point()

add_charging_station()

add_mission_zone()

world_summary()
```

Everything else should be private.