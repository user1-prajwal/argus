"""Tests for SimulationEngine.simulation_summary()."""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentRegistry
from app.mission import Mission, MissionRegistry
from app.simulation import SimulationEngine
from app.world import Obstacle, World


def test_summary_on_empty_simulation(engine: SimulationEngine) -> None:
    summary = engine.simulation_summary()

    assert summary == {
        "tick": 0,
        "agents_executing": 0,
        "agents_returning": 0,
        "missions_in_progress": 0,
        "missions_completed": 0,
        "missions_failed": 0,
    }


def test_summary_reflects_tick_count(engine: SimulationEngine) -> None:
    engine.step()
    engine.step()
    engine.step()

    assert engine.simulation_summary()["tick"] == 3


def test_summary_counts_executing_agent(
    engine: SimulationEngine,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup

    summary = engine.simulation_summary()
    assert summary["agents_executing"] == 1
    assert summary["missions_in_progress"] == 1


def test_summary_counts_returning_agent(
    engine: SimulationEngine,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(1, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()  # arrival, mission completed, return begins

    summary = engine.simulation_summary()
    assert summary["agents_returning"] == 1
    assert summary["agents_executing"] == 0
    assert summary["missions_completed"] == 1


def test_summary_counts_failed_mission(
    engine: SimulationEngine,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=1)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(9, 9)}))
    assign(agent, mission)

    engine.step()

    assert engine.simulation_summary()["missions_failed"] == 1


def test_summary_reflects_multiple_agents_and_missions_together(
    engine: SimulationEngine,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # One executing, one unreachable (fails immediately).
    for y in range(10):
        world.add_obstacle(Obstacle(id=f"wall-{y}", x=5, y=y, type="Wall"))

    ok_agent = make_agent(agent_id="ok", x=0, y=0, battery_level=100)
    ok_mission = make_mission(
        mission_id="ok-mission", target_cells=frozenset({(3, 0)}), name="OK", description="OK"
    )
    assign(ok_agent, ok_mission)

    blocked_agent = make_agent(agent_id="blocked", x=0, y=1, battery_level=100)
    blocked_mission = make_mission(
        mission_id="blocked-mission",
        target_cells=frozenset({(9, 9)}),
        name="Blocked",
        description="Blocked",
    )
    assign(blocked_agent, blocked_mission)

    engine.step()

    summary = engine.simulation_summary()
    assert summary["agents_executing"] == 1
    assert summary["missions_in_progress"] == 1
    assert summary["missions_failed"] == 1


def test_summary_is_computed_live_not_cached(
    engine: SimulationEngine,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(1, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    assert engine.simulation_summary()["missions_in_progress"] == 1

    engine.step()  # arrival, completed
    assert engine.simulation_summary()["missions_in_progress"] == 0
    assert engine.simulation_summary()["missions_completed"] == 1