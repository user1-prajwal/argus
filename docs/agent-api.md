# Agent API Specification

## Purpose

The Agent API defines the public interface for interacting with agent state.

Only the `AgentRegistry` class should be used by other modules.

Other modules must not directly modify `Agent` or other internal classes.

The Agent module has no dependency on the World module. Keeping an agent's position in sync with the World's occupancy state is the responsibility of a future Simulation/Orchestrator module.

---

# Create Registry

```python
agents = AgentRegistry()
```

Creates a new, empty agent registry.

`AgentRegistry` is the only public entry point into the Agent module.

Other modules must never modify `Agent` objects directly. All changes to agent state (position, battery, health status, activity, missions, etc.) must be performed through the `AgentRegistry` public methods.

---

# Register Agent

```python
agents.add_agent(agent)
```

Raises:

- `DuplicateAgentError`

---

# Remove Agent

```python
agents.remove_agent(agent_id)
```

Raises:

- `AgentNotFoundError`

---

# Get Agent

```python
agent = agents.get_agent(agent_id)
```

Returns the `Agent` with the given id.

Raises:

- `AgentNotFoundError`

---

# Update Position

```python
agents.update_position(agent_id, x, y)
```

Raises:

- `ValueError`
- `AgentNotFoundError`

---

# Update Battery

```python
agents.update_battery(agent_id, battery_level)
```

Raises:

- `ValueError`
- `AgentNotFoundError`

---

# Update Health Status

```python
agents.update_health_status(agent_id, health_status)
```

Raises:

- `ValueError`
- `AgentNotFoundError`

---

# Update Activity

```python
agents.update_activity(agent_id, activity)
```

Raises:

- `ValueError`
- `AgentNotFoundError`

---

# Assign Mission

```python
agents.assign_mission(agent_id, mission_id)
```

Raises:

- `ValueError`
- `AgentNotFoundError`

---

# Clear Mission

```python
agents.clear_mission(agent_id)
```

Raises:

- `AgentNotFoundError`

---

# List Agents

```python
agents.list_agents()
```

Returns all registered agents.

---

# Agent Summary

```python
summary = agents.agent_summary()
```

Returns

```python
{
    "total": 12,
    "health_status": {
        "online": 10,
        "failed": 1,
        "offline": 1
    },
    "activity": {
        "idle": 4,
        "assigned": 3,
        "executing_mission": 3,
        "returning": 1,
        "charging": 1
    }
}
```

---

# Validation Rules

Identity

- id must not be empty
- id must be unique

Position

- x >= 0
- y >= 0

Position is not validated against any world's width or height. The Agent Model has no dependency on the World Model.

Battery

- 0 <= battery_level <= 100

Health Status

- must be one of: ONLINE, FAILED, OFFLINE

Activity

- must be one of: IDLE, ASSIGNED, EXECUTING_MISSION, RETURNING, CHARGING

Platform Type

- must not be empty

Capabilities

- descriptive only; not validated against a fixed list

Current Mission

- current_mission_id is optional
- not validated against any Mission module

---

# Public API

Only these methods are public.

```python
AgentRegistry()

add_agent()

remove_agent()

get_agent()

update_position()

update_battery()

update_health_status()

update_activity()

assign_mission()

clear_mission()

list_agents()

agent_summary()
```

Everything else should be private.