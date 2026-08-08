"""Shared fixtures for Path Planner module tests."""

from __future__ import annotations

import pytest

from app.path_planner import PathPlanner
from app.world import World


@pytest.fixture
def world() -> World:
    """A fresh, empty 5x5 world for each test."""
    return World(width=5, height=5)


@pytest.fixture
def planner(world: World) -> PathPlanner:
    """A PathPlanner bound to the world fixture."""
    return PathPlanner(world)