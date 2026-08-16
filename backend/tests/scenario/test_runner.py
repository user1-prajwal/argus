"""Tests for ScenarioRunner: construction, validation, and real
integration behavior across PlanningEngine, PathPlanner, and
SimulationEngine.
"""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import Agent, AgentActivity, AgentRegistry, Capability
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner
from app.planning import PlanningEngine
from app.scenario import ScenarioResult, ScenarioRunner, build_demo_scenario
from app.simulation import SimulationEngine
from app.world import Obstacle, World


def test_construct_valid(
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    planning_engine: PlanningEngine,
    path_planner: PathPlanner,
    simulation_engine: SimulationEngine,
) -> None:
    runner = ScenarioRunner(world, agents, missions, planning_engine, path_planner, simulation_engine)

    assert isinstance(runner, ScenarioRunner)


def test_construct_rejects_wrong_world_type(
    agents: AgentRegistry,
    missions: MissionRegistry,
    planning_engine: PlanningEngine,
    path_planner: PathPlanner,
    simulation_engine: SimulationEngine,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            "not-a-world", agents, missions, planning_engine, path_planner, simulation_engine
        )  # type: ignore[arg-type]


def test_construct_rejects_wrong_agents_type(
    world: World,
    missions: MissionRegistry,
    planning_engine: PlanningEngine,
    path_planner: PathPlanner,
    simulation_engine: SimulationEngine,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            world, "not-a-registry", missions, planning_engine, path_planner, simulation_engine
        )  # type: ignore[arg-type]


def test_construct_rejects_wrong_missions_type(
    world: World,
    agents: AgentRegistry,
    planning_engine: PlanningEngine,
    path_planner: PathPlanner,
    simulation_engine: SimulationEngine,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            world, agents, "not-a-registry", planning_engine, path_planner, simulation_engine
        )  # type: ignore[arg-type]


def test_construct_rejects_wrong_planning_engine_type(
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    path_planner: PathPlanner,
    simulation_engine: SimulationEngine,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            world, agents, missions, "not-a-planning-engine", path_planner, simulation_engine
        )  # type: ignore[arg-type]


def test_construct_rejects_wrong_path_planner_type(
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    planning_engine: PlanningEngine,
    simulation_engine: SimulationEngine,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            world, agents, missions, planning_engine, "not-a-path-planner", simulation_engine
        )  # type: ignore[arg-type]


def test_construct_rejects_wrong_simulation_engine_type(
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    planning_engine: PlanningEngine,
    path_planner: PathPlanner,
) -> None:
    with pytest.raises(TypeError):
        ScenarioRunner(
            world, agents, missions, planning_engine, path_planner, "not-a-simulation-engine"
        )  # type: ignore[arg-type]


def test_run_rejects_non_positive_max_ticks(runner: ScenarioRunner) -> None:
    with pytest.raises(ValueError):
        runner.run(max_ticks=0)
    with pytest.raises(ValueError):
        runner.run(max_ticks=-5)


def test_run_rejects_non_int_max_ticks(runner: ScenarioRunner) -> None:
    with pytest.raises(TypeError):
        runner.run(max_ticks=1.5)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# Real integration behavior: does ScenarioRunner actually connect
# PlanningEngine, PathPlanner, and SimulationEngine correctly?
# ----------------------------------------------------------------------


def test_run_calls_planning_engine_and_reports_its_results(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(3, 0)})))

    result = runner.run()

    assert result.planning_results == [{"mission_id": "m1", "assigned_agent_id": "a1"}]
    assert missions.get_mission("m1").status is not MissionStatus.PENDING


def test_run_executes_the_assignment_planning_produced(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(3, 0)})))

    result = runner.run()

    assert "m1" in result.completed_mission_ids
    final_agent = next(a for a in result.final_agents if a.id == "a1")
    assert (final_agent.x, final_agent.y) == (0, 0)  # returned home
    assert final_agent.activity is AgentActivity.IDLE
    assert result.ticks_run > 0


def test_run_respects_obstacles_via_real_path_planner(
    runner: ScenarioRunner,
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # Wall across y=3 for x in [0, 8], leaving x=9 as the only gap in a
    # 10-wide world -- forces a real detour, not a straight line.
    for x in range(9):
        world.add_obstacle(Obstacle(id=f"wall-{x}", x=x, y=3, type="Wall"))

    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(0, 6)})))

    result = runner.run()

    assert "m1" in result.completed_mission_ids
    # A straight line would be 6 moves; detouring around the wall to
    # the gap at x=9 and back is necessarily longer.
    move_ticks = [t for t in result.tick_results if "a1" in t["moved"]]
    assert len(move_ticks) > 6


def test_run_respects_capability_requirements(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(
        make_agent(agent_id="no-lidar", x=0, y=0, capabilities=frozenset())
    )
    agents.add_agent(
        make_agent(agent_id="has-lidar", x=9, y=9, capabilities=frozenset({Capability.LIDAR}))
    )
    missions.add_mission(
        make_mission(
            mission_id="m1",
            target_cells=frozenset({(5, 5)}),
            required_capabilities=frozenset({Capability.LIDAR}),
        )
    )

    result = runner.run()

    assert result.planning_results == [{"mission_id": "m1", "assigned_agent_id": "has-lidar"}]


def test_run_fails_mission_when_no_agent_has_enough_battery(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=2))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(9, 9)})))

    result = runner.run()

    assert "m1" in result.failed_mission_ids
    final_agent = next(a for a in result.final_agents if a.id == "a1")
    assert (final_agent.x, final_agent.y) == (0, 0)  # never moved
    assert final_agent.battery_level == 2  # untouched


def test_run_handles_multiple_missions_with_different_priorities(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # Only one agent exists, so only the higher-priority mission can
    # claim it -- this exercises PlanningEngine's real priority
    # ordering, not something ScenarioRunner reimplements.
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(
        make_mission(mission_id="low", priority=MissionPriority.LOW, target_cells=frozenset({(2, 0)}))
    )
    missions.add_mission(
        make_mission(
            mission_id="critical",
            priority=MissionPriority.CRITICAL,
            target_cells=frozenset({(3, 0)}),
        )
    )

    result = runner.run()

    result_by_mission = {r["mission_id"]: r["assigned_agent_id"] for r in result.planning_results}
    assert result_by_mission["critical"] == "a1"
    assert result_by_mission["low"] is None
    assert missions.get_mission("low").status is MissionStatus.PENDING


def test_run_terminates_when_nothing_is_active_rather_than_hitting_max_ticks(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(2, 0)})))

    result = runner.run(max_ticks=200)

    assert result.terminated_reason == "no_active_agents"
    assert result.ticks_run < 200


def test_run_stops_at_max_ticks_if_a_scenario_never_settles(
    runner: ScenarioRunner,
    world: World,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # Two agents approaching each other head-on in a 1-wide corridor,
    # each needing to pass the other's position -- a known, documented
    # V1 limitation (see docs/simulation-model.md, "Multi-Agent
    # Execution": anticipating conflicts before they happen is left to
    # a future coordination layer). Targets are chosen past each
    # other's launch cell, not on it, so both missions clear the
    # round-trip pre-flight check and actually begin executing before
    # deadlocking. ScenarioRunner must still terminate safely via
    # max_ticks rather than looping forever.
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    agents.add_agent(make_agent(agent_id="a2", x=9, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(8, 0)})))
    missions.add_mission(make_mission(mission_id="m2", target_cells=frozenset({(1, 0)})))

    result = runner.run(max_ticks=30)

    assert result.terminated_reason == "max_ticks_reached"
    assert result.ticks_run == 30
    assert result.completed_mission_ids == []
    assert result.failed_mission_ids == []


def test_run_returns_live_summaries_matching_the_registries(
    runner: ScenarioRunner,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", x=0, y=0, battery_level=100))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(2, 0)})))

    result = runner.run()

    assert result.agent_summary == agents.agent_summary()
    assert result.mission_summary == missions.mission_summary()


def test_run_is_deterministic_across_independent_runs() -> None:
    result_a = build_demo_scenario().run()
    result_b = build_demo_scenario().run()

    assert result_a.ticks_run == result_b.ticks_run
    assert result_a.completed_mission_ids == result_b.completed_mission_ids
    assert result_a.failed_mission_ids == result_b.failed_mission_ids
    positions_a = [(a.id, a.x, a.y, a.battery_level) for a in result_a.final_agents]
    positions_b = [(a.id, a.x, a.y, a.battery_level) for a in result_b.final_agents]
    assert positions_a == positions_b


def test_build_demo_scenario_produces_a_working_scenario() -> None:
    result = build_demo_scenario().run()

    assert isinstance(result, ScenarioResult)
    assert len(result.completed_mission_ids) > 0
    assert result.ticks_run > 0