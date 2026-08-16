"""Tests for SimulationEngine.step() handling an agent's health status
dropping mid-execution.
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentRegistry, HealthStatus
from app.mission import Mission, MissionRegistry, MissionStatus
from app.simulation import SimulationEngine
from app.world import World


def test_mission_fails_when_agent_health_fails_mid_execution(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)
    engine.step()  # pickup
    engine.step()  # one move, now at (1, 0)

    agents.update_health_status("a1", HealthStatus.FAILED)
    result = engine.step()

    assert missions.get_mission("m1").status is MissionStatus.FAILED
    assert "m1" in result["failed_missions"]


def test_agent_stops_moving_once_health_fails(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)
    engine.step()
    engine.step()  # now at (1, 0)

    agents.update_health_status("a1", HealthStatus.FAILED)
    engine.step()
    position_after_failure = (agents.get_agent("a1").x, agents.get_agent("a1").y)

    engine.step()  # further ticks must not move it either
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == position_after_failure


def test_offline_agent_also_stops_execution(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)
    engine.step()
    engine.step()

    agents.update_health_status("a1", HealthStatus.OFFLINE)
    engine.step()

    assert missions.get_mission("m1").status is MissionStatus.FAILED


def test_health_failure_releases_the_agents_occupied_cell(
    engine: SimulationEngine,
    agents: AgentRegistry,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(5, 0)}))
    assign(agent, mission)
    engine.step()
    engine.step()  # now at (1, 0); (1, 0) is occupied

    agents.update_health_status("a1", HealthStatus.FAILED)
    engine.step()

    assert world.is_walkable(1, 0) is True


def test_health_failure_during_return_does_not_touch_the_completed_mission(
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
    engine.step()  # move to (2, 0), arrival, mission COMPLETED, begin return

    assert missions.get_mission("m1").status is MissionStatus.COMPLETED

    agents.update_health_status("a1", HealthStatus.FAILED)
    engine.step()  # health failure while returning

    # The mission already succeeded; a health failure afterward must not
    # retroactively change that.
    assert missions.get_mission("m1").status is MissionStatus.COMPLETED