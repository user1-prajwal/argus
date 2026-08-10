# Simulation API Specification

## Purpose

The Simulation API defines the public interface for advancing a running multi-agent simulation, tick by tick.

Only the `SimulationEngine` class should be used by other modules.

The Simulation Engine's only persistent state is its own execution bookkeeping (current tick, and which route each active agent is following) — it never stores World, Agent, or Mission data itself. Every call reads their current state directly and writes back through their existing public methods (`AgentRegistry.update_position`, `AgentRegistry.update_battery`, `AgentRegistry.update_activity`, `AgentRegistry.clear_mission`, `MissionRegistry.update_status`), plus World's private occupancy hooks, which the Simulation Engine is the intended caller of — see docs/simulation-model.md, "Occupancy".

The Simulation Engine does not call the Planning Engine. A caller is responsible for producing ASSIGNED missions (via `PlanningEngine.plan()`, `assign_mission`, or `replan`) before the Simulation Engine will act on them.

This is a simulated software coordination layer, not a real drone/robot control system. See docs/simulation-model.md, "Purpose".

---

# Create Engine

```
sim = SimulationEngine(world, agents, missions, path_planner)
```

Creates a new Simulation Engine bound to a specific World, AgentRegistry, MissionRegistry, and PathPlanner, starting at tick 0.

Raises:

- `TypeError`

---

# Step

```
result = sim.step()
```

Advances the simulation by one tick:

1. Finds every mission with status ASSIGNED and not yet tracked, and attempts to begin executing it — computing an outbound and return route via PathPlanner and checking the round-trip battery cost. A mission that fails this check becomes FAILED immediately, before its agent moves; otherwise the mission becomes IN_PROGRESS and its agent's activity becomes EXECUTING_MISSION.
2. Advances every actively-tracked agent (EXECUTING_MISSION or RETURNING) by one cell along its current route, if the next cell is walkable; otherwise the agent waits this tick.
3. Handles arrivals: an agent reaching its mission target completes the mission and begins a return trip; an agent reaching its launch position becomes IDLE.

Returns a summary of what happened this tick:

```
{
    "tick": 4,
    "moved": ["a1", "a3"],
    "waiting": ["a2"],
    "completed_missions": ["m1"],
    "failed_missions": ["m2"],
    "returned_home": ["a4"],
}
```

`tick` is the tick number that was just completed. All other keys are lists of ids and may be empty. `step()` does not raise under normal operation — every failure condition (insufficient battery, unreachable target, agent health failure) is reported in this result, not as an exception.

---

# Simulation Summary

```
summary = sim.simulation_summary()
```

Returns

```
{
    "tick": 12,
    "agents_executing": 2,
    "agents_returning": 1,
    "missions_in_progress": 2,
    "missions_completed": 5,
    "missions_failed": 1,
}
```

Computed live from the current World, Agent, and Mission state at call time — not a stored or cached total.

---

# Validation Rules

Create Engine

- world must be a World instance
- agents must be an AgentRegistry instance
- missions must be a MissionRegistry instance
- path_planner must be a PathPlanner instance

Round-trip battery check (not a validation error — see docs/simulation-model.md, "Battery Model")

- a mission that cannot be safely completed and returned from becomes FAILED, not an exception

Occupied or blocked next cell (not a validation error — see docs/simulation-model.md, "Execution Lifecycle")

- the agent waits for one tick; this is normal, expected behavior, not a failure

---

# Public API

Only these methods are public.

```
SimulationEngine()

step()

simulation_summary()
```

Everything else should be private.