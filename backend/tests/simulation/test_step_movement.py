"""Tests for SimulationEngine.step() -- tick advancement, movement, and
battery consumption while an agent is EXECUTING_MISSION.
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentRegistry
from app.mission import Mission
from app.simulation import SimulationEngine


def test_tick_number_advances_each_step(engine: SimulationEngine) -> None:
    assert engine.simulation_summary()["tick"] == 0
    engine.step()
    assert engine.simulation_summary()["tick"] == 1
    engine.step()
    assert engine.simulation_summary()["tick"] == 2


def test_step_result_reports_the_tick_it_just_completed(engine: SimulationEngine) -> None:
    result = engine.step()
    assert result["tick"] == 0

    result = engine.step()
    assert result["tick"] == 1


def test_agent_advances_one_cell_per_tick_toward_target(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    engine.step()
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (1, 0)

    engine.step()
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (2, 0)

    engine.step()  # arrival
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (3, 0)


def test_battery_decreases_by_one_per_move(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup, no battery cost
    assert agents.get_agent("a1").battery_level == 100

    engine.step()
    assert agents.get_agent("a1").battery_level == 99

    engine.step()
    assert agents.get_agent("a1").battery_level == 98


def test_step_result_lists_moved_agent_ids(
    engine: SimulationEngine,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup
    result = engine.step()

    assert result["moved"] == ["a1"]


def test_step_is_a_no_op_on_a_completely_empty_simulation(engine: SimulationEngine) -> None:
    result = engine.step()

    assert result["moved"] == []
    assert result["waiting"] == []
    assert result["completed_missions"] == []
    assert result["failed_missions"] == []
    assert result["returned_home"] == []