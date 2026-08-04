"""Shared fixtures for Mission module tests."""

from __future__ import annotations

from typing import Callable

import pytest

from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus


@pytest.fixture
def make_mission() -> Callable[..., Mission]:
    """Factory fixture: build a valid Mission with sensible defaults,
    overriding only what a test cares about.

    Usage:
        def test_x(make_mission):
            mission = make_mission(priority=MissionPriority.HIGH)
    """

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


@pytest.fixture
def registry() -> MissionRegistry:
    """A fresh, empty mission registry for each test."""
    return MissionRegistry()


@pytest.fixture
def mission(make_mission: Callable[..., Mission]) -> Mission:
    """A single valid Mission, not yet registered."""
    return make_mission()