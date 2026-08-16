"""Tests for SimulationEngine.step() waiting when the next cell along a
route is occupied.
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentRegistry
from app.mission import Mission, MissionRegistry, MissionStatus
from app.simulation import SimulationEngine
from app.world import World


def test_agent_waits_when_next_cell_is_occupied(
    engine: SimulationEngine,
    agents: AgentRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)
    engine.step()  # pickup

    world._occupy_cell(1, 0)  # block the agent's very next cell

    result = engine.step()

    assert "a1" in result["waiting"]
    assert "a1" not in result["moved"]
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (0, 0)
    assert agents.get_agent("a1").battery_level == 100  # no cost for waiting


def test_agent_resumes_moving_once_the_cell_is_freed(
    engine: SimulationEngine,
    agents: AgentRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)
    engine.step()  # pickup

    world._occupy_cell(1, 0)
    engine.step()  # waits

    world._release_cell(1, 0)
    result = engine.step()  # now moves

    assert "a1" in result["moved"]
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (1, 0)


def test_mission_stays_in_progress_while_waiting(
    engine: SimulationEngine,
    missions: MissionRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)
    engine.step()  # pickup

    world._occupy_cell(1, 0)
    engine.step()

    assert missions.get_mission("m1").status is MissionStatus.IN_PROGRESS


def test_waiting_agent_can_be_blocked_for_multiple_ticks_in_a_row(
    engine: SimulationEngine,
    agents: AgentRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)
    engine.step()  # pickup

    world._occupy_cell(1, 0)
    engine.step()
    engine.step()
    result = engine.step()

    assert "a1" in result["waiting"]
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (0, 0)
    assert agents.get_agent("a1").battery_level == 100