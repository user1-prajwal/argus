"""Tests for SimulationEngine keeping World's occupancy state in sync
with actively-executing agents -- see docs/simulation-model.md,
"Occupancy".
"""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry
from app.mission import Mission, MissionRegistry
from app.simulation import SimulationEngine
from app.world import World


def test_agents_launch_cell_is_occupied_once_picked_up(
    engine: SimulationEngine,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    assert world.is_walkable(0, 0) is True  # not yet picked up

    engine.step()  # pickup

    assert world.is_walkable(0, 0) is False


def test_old_cell_is_released_and_new_cell_occupied_on_move(
    engine: SimulationEngine,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(3, 0)}))
    assign(agent, mission)

    engine.step()  # pickup: (0, 0) occupied
    engine.step()  # move to (1, 0)

    assert world.is_walkable(0, 0) is True  # released
    assert world.is_walkable(1, 0) is False  # newly occupied


def test_a_second_agent_must_wait_for_an_occupied_cell_to_clear(
    engine: SimulationEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    # "mover" is assigned first, so it is processed first each tick --
    # meaning it checks (1, 0)'s occupancy before "blocker" (assigned
    # second, moving away from (1, 0) on this same tick) has a chance
    # to vacate it. This deterministically produces one wait, then a
    # successful move on the following tick.
    mover = make_agent(agent_id="mover", x=0, y=0, battery_level=100)
    mover_mission = make_mission(
        mission_id="move", target_cells=frozenset({(2, 0)}), name="Move", description="Move"
    )
    assign(mover, mover_mission)

    blocker = make_agent(agent_id="blocker", x=1, y=0, battery_level=100)
    blocker_mission = make_mission(
        mission_id="wander",
        target_cells=frozenset({(1, 4)}),
        name="Wander",
        description="Wander north",
    )
    assign(blocker, blocker_mission)

    engine.step()  # pickup both

    result = engine.step()  # mover checks (1, 0) before blocker vacates it

    assert "mover" in result["waiting"]
    assert "blocker" in result["moved"]
    assert (agents.get_agent("mover").x, agents.get_agent("mover").y) == (0, 0)

    result = engine.step()  # (1, 0) is now free

    assert "mover" in result["moved"]
    assert (agents.get_agent("mover").x, agents.get_agent("mover").y) == (1, 0)


def test_agent_going_idle_at_home_releases_its_cell(
    engine: SimulationEngine,
    world: World,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    assign: Callable[[Agent, Mission], None],
) -> None:
    agent = make_agent(agent_id="a1", x=0, y=0, battery_level=100)
    mission = make_mission(mission_id="m1", target_cells=frozenset({(1, 0)}))
    assign(agent, mission)

    for _ in range(10):
        result = engine.step()
        if "a1" in result["returned_home"]:
            break

    assert world.is_walkable(0, 0) is True