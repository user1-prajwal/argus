"""Tests for SimulationEngine.step() running multiple agents at once."""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentRegistry
from app.mission import Mission, MissionRegistry, MissionStatus
from app.simulation import SimulationEngine


def test_two_agents_execute_independently_in_the_same_tick(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent_a = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    agent_b = make_agent(agent_id="a2", x=0, y=9, battery_level=100)
    mission_a = make_mission(
        mission_id="m1", target_cells=frozenset({(3, 0)}), name="A", description="Mission A"
    )
    mission_b = make_mission(
        mission_id="m2", target_cells=frozenset({(3, 9)}), name="B", description="Mission B"
    )
    assign(agent_a, mission_a)
    assign(agent_b, mission_b)

    engine.step()  # pickup both
    result = engine.step()  # both move

    assert set(result["moved"]) == {"a1", "a2"}
    assert (agents.get_agent("a1").x, agents.get_agent("a1").y) == (1, 0)
    assert (agents.get_agent("a2").x, agents.get_agent("a2").y) == (1, 9)


def test_one_agent_completing_does_not_affect_another_still_executing(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    short_agent = make_agent(agent_id="short", x=0, y=0, battery_level=100)
    long_agent = make_agent(agent_id="long", x=0, y=9, battery_level=100)
    short_mission = make_mission(
        mission_id="short-mission",
        target_cells=frozenset({(1, 0)}),
        name="Short",
        description="Short mission",
    )
    long_mission = make_mission(
        mission_id="long-mission",
        target_cells=frozenset({(5, 9)}),
        name="Long",
        description="Long mission",
    )
    assign(short_agent, short_mission)
    assign(long_agent, long_mission)

    engine.step()  # pickup
    engine.step()  # short agent arrives and completes; long agent takes its first step

    assert missions.get_mission("short-mission").status is MissionStatus.COMPLETED
    assert missions.get_mission("long-mission").status is MissionStatus.IN_PROGRESS
    assert (agents.get_agent("long").x, agents.get_agent("long").y) == (1, 9)


def test_agents_never_share_a_cell_even_with_crossing_paths(
    engine: SimulationEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # Two agents whose routes cross paths through the middle of the
    # grid. Regardless of exactly how contention resolves tick to
    # tick, the two agents must never occupy the same cell at once --
    # World's occupancy hooks are what make this an invariant rather
    # than a race.
    agent_a = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    agent_b = make_agent(agent_id="a2", x=2, y=3, battery_level=100)
    mission_a = make_mission(
        mission_id="m1", target_cells=frozenset({(4, 0)}), name="A", description="Mission A"
    )
    mission_b = make_mission(
        mission_id="m2", target_cells=frozenset({(2, 0)}), name="B", description="Mission B"
    )
    assign(agent_a, mission_a)
    assign(agent_b, mission_b)

    for _ in range(30):
        engine.step()
        positions = [
            (agents.get_agent("a1").x, agents.get_agent("a1").y),
            (agents.get_agent("a2").x, agents.get_agent("a2").y),
        ]
        assert len(set(positions)) == len(positions), f"agents collided at {positions}"


def test_three_agents_can_run_to_completion_independently(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    for i, y in enumerate([0, 3, 6]):
        agent = make_agent(agent_id=f"a{i}", x=0, y=y, battery_level=100)
        mission = make_mission(
            mission_id=f"m{i}",
            target_cells=frozenset({(2, y)}),
            name=f"Mission {i}",
            description=f"Mission {i}",
        )
        assign(agent, mission)

    for _ in range(20):
        engine.step()

    for i in [0, 1, 2]:
        assert missions.get_mission(f"m{i}").status is MissionStatus.COMPLETED