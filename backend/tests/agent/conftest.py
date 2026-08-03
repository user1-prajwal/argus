"""Shared fixtures for Agent module tests."""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import Agent, AgentActivity, AgentRegistry, HealthStatus, PlatformType


@pytest.fixture
def make_agent() -> Callable[..., Agent]:
    """Factory fixture: build a valid Agent with sensible defaults,
    overriding only what a test cares about.

    Usage:
        def test_x(make_agent):
            agent = make_agent(x=5, battery_level=10)
    """

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
def registry() -> AgentRegistry:
    """A fresh, empty agent registry for each test."""
    return AgentRegistry()


@pytest.fixture
def agent(make_agent: Callable[..., Agent]) -> Agent:
    """A single valid Agent, not yet registered."""
    return make_agent()