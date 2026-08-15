"""Tests for SimulationEngine.step() picking up newly ASSIGNED missions:
the round-trip battery check and the ASSIGNED -> IN_PROGRESS transition.
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry
from app.mission import Mission, MissionRegistry, MissionStatus
from app.simulation import SimulationEngine
from app.world import Obstacle, World


def test_assigned_mission_becomes_in_progress(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()

    assert missions.get_mission("m1").status is MissionStatus.IN_PROGRESS
    assert agents.get_agent("a1").activity is AgentActivity.EXECUTING_MISSION


def test_agent_does_not_move_on_the_pickup_tick(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # docs/simulation-model.md: "Each subsequent tick, the agent
    # advances" -- movement starts the tick after pickup, not the same
    # tick.
    agent = make_agent(agent_id="a1", x=0, y=0)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    result = engine.step()

    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (0, 0)
    assert "a1" not in result["moved"]


def test_agent_moves_starting_the_tick_after_pickup(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup tick
    result = engine.step()  # first movement tick

    assert "a1" in result["moved"]
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (1, 0)


def test_pending_mission_status_unchanged_by_step(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", status=MissionStatus.PENDING))

    result = engine.step()

    assert missions.get_mission("m1").status is MissionStatus.PENDING
    assert result["moved"] == []
    assert result["failed_missions"] == []


def test_unreachable_target_fails_mission_without_moving_agent(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # Wall the whole world into two halves with no gap.
    for y in range(10):
        world.add_obstacle(Obstacle(id=f"wall-{y}", x=5, y=y, type="Wall"))

    agent = make_agent(agent_id="a1", x=0, y=0)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(9, 9)}))
    assign(agent, mission)

    result = engine.step()

    assert missions.get_mission("m1").status is MissionStatus.FAILED
    assert "m1" in result["failed_missions"]
    assert agents.get_agent("a1").activity is AgentActivity.IDLE
    assert agents.get_agent("a1").current_mission_id is None
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (0, 0)


def test_insufficient_round_trip_battery_fails_mission(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # Round trip to (5, 0) and back is 10 moves; battery of 5 is not enough.
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=5)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)

    result = engine.step()

    assert missions.get_mission("m1").status is MissionStatus.FAILED
    assert "m1" in result["failed_missions"]
    assert agents.get_agent("a1").battery_level == 5
    assert agents.get_agent("a1").activity is AgentActivity.IDLE


def test_exactly_enough_round_trip_battery_succeeds(
    engine: SimulationEngine,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # Round trip to (5, 0) and back is exactly 10 moves.
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=10)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)

    engine.step()

    assert missions.get_mission("m1").status is MissionStatus.IN_PROGRESS


def test_current_mission_id_cleared_when_mission_fails(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=1)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(9, 9)}))
    assign(agent, mission)

    engine.step()

    assert agents.get_agent("a1").current_mission_id is None