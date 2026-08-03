# Mission API Specification

## Purpose

The Mission API defines the public interface for interacting with mission state.

Only the `MissionRegistry` class should be used by other modules.

Other modules must not directly modify `Mission` or other internal classes.

The Mission module has no dependency on the World module, and no dependency on the Agent module beyond reusing the `Capability` enum as a shared vocabulary type. Matching agents to missions, and keeping assigned_agent_ids consistent with a live Agent registry, is the responsibility of a future Planning Engine.

---

# Create Registry

```
missions = MissionRegistry()
```

Creates a new, empty mission registry.

`MissionRegistry` is the only public entry point into the Mission module.

Other modules must never modify `Mission` objects directly. All changes to mission state (status, assigned agents) must be performed through the `MissionRegistry` public methods.

---

# Register Mission

```
missions.add_mission(mission)
```

Raises:

- `DuplicateMissionError`

---

# Remove Mission

```
missions.remove_mission(mission_id)
```

Raises:

- `MissionNotFoundError`

---

# Get Mission

```
mission = missions.get_mission(mission_id)
```

Returns the `Mission` with the given id.

Raises:

- `MissionNotFoundError`

---

# Update Status

```
missions.update_status(mission_id, status)
```

Raises:

- `ValueError`
- `MissionNotFoundError`

---

# Assign Agents

```
missions.assign_agents(mission_id, agent_ids)
```

Replaces the mission's entire `assigned_agent_ids` with the given set. To add or remove specific agents, pass the full desired set of ids.

Raises:

- `ValueError`
- `MissionNotFoundError`

---

# Clear Agents

```
missions.clear_agents(mission_id)
```

Equivalent to `assign_agents(mission_id, frozenset())`.

Raises:

- `MissionNotFoundError`

---

# List Missions

```
missions.list_missions()
```

Returns all registered missions.

---

# Mission Summary

```
summary = missions.mission_summary()
```

Returns

```
{
    "total": 8,
    "status": {
        "pending": 3,
        "assigned": 2,
        "in_progress": 1,
        "completed": 1,
        "failed": 1,
        "cancelled": 0
    },
    "priority": {
        "low": 1,
        "medium": 3,
        "high": 3,
        "critical": 1
    }
}
```

---

# Validation Rules

Identity

- id must not be empty
- id must be unique
- name must not be empty
- description must not be empty

Target Cells

- must not be empty
- x >= 0
- y >= 0

Target cells are not validated against any world's width or height. The Mission Model has no dependency on the World Model.

Status

- must be one of: PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED

Priority

- must be one of: LOW, MEDIUM, HIGH, CRITICAL

Required Capabilities

- defaults to an empty frozenset
- values must be members of the `Capability` enum (reused from the Agent Model)

Assigned Agent IDs

- defaults to an empty frozenset
- stored as plain strings; not validated against any Agent registry

---

# Public API

Only these methods are public.

```
MissionRegistry()

add_mission()

remove_mission()

get_mission()

update_status()

assign_agents()

clear_agents()

list_missions()

mission_summary()
```

Everything else should be private.