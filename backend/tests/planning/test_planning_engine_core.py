"""Tests for PlanningEngine construction."""

from __future__ import annotations

import pytest

from app.agent import AgentRegistry
from app.mission import MissionRegistry
from app.planning import PlanningEngine
from app.world import World


def test_construct_valid(world: World, agents: AgentRegistry, missions: MissionRegistry) -> None:
    engine = PlanningEngine(world, agents, missions)

    assert isinstance(engine, PlanningEngine)


def test_construct_rejects_wrong_world_type(
    agents: AgentRegistry, missions: MissionRegistry
) -> None:
    with pytest.raises(TypeError):
        PlanningEngine("not-a-world", agents, missions)  # type: ignore[arg-type]


def test_construct_rejects_wrong_agents_type(world: World, missions: MissionRegistry) -> None:
    with pytest.raises(TypeError):
        PlanningEngine(world, "not-a-registry", missions)  # type: ignore[arg-type]


def test_construct_rejects_wrong_missions_type(world: World, agents: AgentRegistry) -> None:
    with pytest.raises(TypeError):
        PlanningEngine(world, agents, "not-a-registry")  # type: ignore[arg-type]