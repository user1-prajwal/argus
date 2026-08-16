"""Shared fixtures for Simulation module tests."""

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
from app.path_planner import PathPlanner
from app.simulation import SimulationEngine
from app.world import World


@pytest.fixture
def world() -> World:
    """A fresh, empty 10x10 world for each test."""
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
def path_planner(world: World) -> PathPlanner:
    """A PathPlanner bound to the world fixture."""
    return PathPlanner(world)


@pytest.fixture
def engine(
    world: World, agents: AgentRegistry, missions: MissionRegistry, path_planner: PathPlanner
) -> SimulationEngine:
    """A SimulationEngine bound to the other fixtures."""
    return SimulationEngine(world, agents, missions, path_planner)


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
        name: str = "Test Mission",
        description: str = "A mission used for Simulation Engine tests.",
        priority: MissionPriority = MissionPriority.MEDIUM,
        status: MissionStatus = MissionStatus.PENDING,
        target_cells: frozenset = frozenset({(5, 5)}),
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


@pytest.fixture
def assign(
    agents: AgentRegistry, missions: MissionRegistry
) -> Callable[[Agent, Mission], None]:
    """Factory fixture: register an agent and a mission, then put them
    into the ASSIGNED state a real PlanningEngine.plan() would leave
    them in, so SimulationEngine.step() will pick the mission up.
    """

    def _assign(agent: Agent, mission: Mission) -> None:
        agents.add_agent(agent)
        missions.add_mission(mission)
        missions.assign_agents(mission.id, {agent.id})
        missions.update_status(mission.id, MissionStatus.ASSIGNED)
        agents.assign_mission(agent.id, mission.id)
        agents.update_activity(agent.id, AgentActivity.ASSIGNED)

    return _assign