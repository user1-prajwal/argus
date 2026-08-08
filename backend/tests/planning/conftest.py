"""Shared fixtures for Planning module tests."""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import (
    Agent,
    AgentActivity,
    AgentRegistry,
    Capability,
    HealthStatus,
    PlatformType,
)
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.planning import PlanningEngine
from app.world import World


@pytest.fixture
def world() -> World:
    """A small, empty world. Not read by any Version 1 planning logic."""
    return World(width=10, height=10)


@pytest.fixture
def agents() -> AgentRegistry:
    """A fresh, empty agent registry for each test."""
    return AgentRegistry()


@pytest.fixture
def missions() -> MissionRegistry:
    """A fresh, empty mission registry for each test."""
    return MissionRegistry()


@pytest.fixture
def engine(world: World, agents: AgentRegistry, missions: MissionRegistry) -> PlanningEngine:
    """A PlanningEngine bound to the world/agents/missions fixtures."""
    return PlanningEngine(world, agents, missions)


@pytest.fixture
def make_agent() -> Callable[..., Agent]:
    """Factory fixture: build a valid, available Agent by default,
    overriding only what a test cares about."""

    def _make_agent(
        agent_id: str = "agent-1",
        platform_type: PlatformType = PlatformType.DRONE,
        x: int = 0,
        y: int = 0,
        battery_level: int = 100,
        health_status: HealthStatus = HealthStatus.ONLINE,
        activity: AgentActivity = AgentActivity.IDLE,
        capabilities: frozenset = frozenset(),
        current_mission_id: str | None = None,
    ) -> Agent:
        return Agent(
            id=agent_id,
            platform_type=platform_type,
            x=x,
            y=y,
            battery_level=battery_level,
            health_status=health_status,
            activity=activity,
            capabilities=capabilities,
            current_mission_id=current_mission_id,
        )

    return _make_agent


@pytest.fixture
def make_mission() -> Callable[..., Mission]:
    """Factory fixture: build a valid, PENDING Mission by default,
    overriding only what a test cares about."""

    def _make_mission(
        mission_id: str = "mission-1",
        name: str = "Search Sector A",
        description: str = "Search the northern quadrant for survivors.",
        priority: MissionPriority = MissionPriority.MEDIUM,
        status: MissionStatus = MissionStatus.PENDING,
        target_cells: frozenset = frozenset({(0, 0)}),
        required_capabilities: frozenset = frozenset(),
        assigned_agent_ids: frozenset = frozenset(),
    ) -> Mission:
        return Mission(
            id=mission_id,
            name=name,
            description=description,
            priority=priority,
            status=status,
            target_cells=target_cells,
            required_capabilities=required_capabilities,
            assigned_agent_ids=assigned_agent_ids,
        )

    return _make_mission