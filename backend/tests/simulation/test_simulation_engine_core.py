"""Tests for SimulationEngine construction."""

from __future__ import annotations

import pytest

from app.agent import AgentRegistry
from app.mission import MissionRegistry
from app.path_planner import PathPlanner
from app.simulation import SimulationEngine
from app.world import World


def test_construct_valid(
    world: World, agents: AgentRegistry, missions: MissionRegistry, path_planner: PathPlanner
) -> None:
    engine = SimulationEngine(world, agents, missions, path_planner)

    assert isinstance(engine, SimulationEngine)


def test_construct_starts_at_tick_zero(engine: SimulationEngine) -> None:
    assert engine.simulation_summary()["tick"] == 0


def test_construct_rejects_wrong_world_type(
    agents: AgentRegistry, missions: MissionRegistry, path_planner: PathPlanner
) -> None:
    with pytest.raises(TypeError):
        SimulationEngine("not-a-world", agents, missions, path_planner)  # type: ignore[arg-type]


def test_construct_rejects_wrong_agents_type(
    world: World, missions: MissionRegistry, path_planner: PathPlanner
) -> None:
    with pytest.raises(TypeError):
        SimulationEngine(world, "not-a-registry", missions, path_planner)  # type: ignore[arg-type]


def test_construct_rejects_wrong_missions_type(
    world: World, agents: AgentRegistry, path_planner: PathPlanner
) -> None:
    with pytest.raises(TypeError):
        SimulationEngine(world, agents, "not-a-registry", path_planner)  # type: ignore[arg-type]


def test_construct_rejects_wrong_path_planner_type(
    world: World, agents: AgentRegistry, missions: MissionRegistry
) -> None:
    with pytest.raises(TypeError):
        SimulationEngine(world, agents, missions, "not-a-planner")  # type: ignore[arg-type]


def test_construct_rejects_none_arguments(
    world: World, agents: AgentRegistry, missions: MissionRegistry, path_planner: PathPlanner
) -> None:
    with pytest.raises(TypeError):
        SimulationEngine(None, agents, missions, path_planner)  # type: ignore[arg-type]