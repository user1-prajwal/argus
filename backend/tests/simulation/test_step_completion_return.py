"""Tests for SimulationEngine.step() completing a mission and the
subsequent return trip back to the agent's launch position.
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry
from app.mission import Mission, MissionRegistry, MissionStatus
from app.simulation import SimulationEngine


def _run_until_idle(
    engine: SimulationEngine, agents: AgentRegistry, agent_id: str, max_ticks: int = 50
) -> None:
    for _ in range(max_ticks):
        engine.step()
        if agents.get_agent(agent_id).activity is AgentActivity.IDLE:
            return
    raise AssertionError(f"{agent_id} never returned to IDLE within {max_ticks} ticks")


def test_reaching_target_completes_mission_and_starts_returning(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(2, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()  # move to (1, 0)
    result = engine.step()  # move to (2, 0) -- arrival

    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (2, 0)
    assert missions.get_mission("m1").status is MissionStatus.COMPLETED
    assert "m1" in result["completed_missions"]
    assert agents.get_agent("a1").activity is AgentActivity.RETURNING


def test_agent_returns_to_launch_position_and_becomes_idle(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(2, 0)}))
    assign(agent, mission)

    _run_until_idle(engine, agents, "a1")

    final = agents.get_agent("a1")
    assert (final.x, final.y) == (0, 0)
    assert final.activity is AgentActivity.IDLE


def test_current_mission_id_is_cleared_on_completion(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(2, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()
    engine.step()  # arrival, mission completed

    assert agents.get_agent("a1").current_mission_id is None


def test_current_mission_id_is_cleared_the_instant_return_begins(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # Cleared at the moment the agent starts returning, not only once
    # it arrives home.
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(1, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()  # arrival at (1, 0), mission completed, return begins

    assert agents.get_agent("a1").current_mission_id is None
    assert agents.get_agent("a1").activity is AgentActivity.RETURNING


def test_battery_continues_draining_during_return_trip(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(2, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()  # move -> battery 99
    engine.step()  # move, arrival -> battery 98
    battery_at_arrival = agents.get_agent("a1").battery_level
    assert battery_at_arrival == 98

    engine.step()  # first return move
    assert agents.get_agent("a1").battery_level == battery_at_arrival - 1


def test_returned_home_appears_in_step_result(
    engine: SimulationEngine,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(1, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()  # move to (1, 0), arrival, mission completed, begin return
    result = engine.step()  # return move to (0, 0), arrival home

    assert "a1" in result["returned_home"]


def test_zero_length_mission_at_launch_position_completes_immediately(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # The agent's launch position is itself one of the mission's target
    # cells -- it "arrives" without ever moving. Both completion and the
    # (trivial) return home resolve within this single pickup tick,
    # rather than getting tracked for a move that would never come.
    agent = make_agent(agent_id="a1", x=4, y=4, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(4, 4)}))
    assign(agent, mission)

    engine.step()

    assert missions.get_mission("m1").status is MissionStatus.COMPLETED
    final = agents.get_agent("a1")
    assert final.activity is AgentActivity.IDLE
    assert (final.x, final.y) == (4, 4)