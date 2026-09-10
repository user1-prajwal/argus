"""Shared fixtures for ARGUS API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes import _store


@pytest.fixture(autouse=True)
def _clear_session_store():
    """Reset the in-memory session store between tests.

    The store is a module-level singleton (see docs/api-model.md,
    "Design Goals": in-memory is the right size for Version 1), so
    without this, sessions created by one test would leak into the
    next.
    """
    _store._sessions.clear()
    yield
    _store._sessions.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def minimal_scenario_payload() -> dict:
    """A small, valid POST /scenarios body with no agents or missions."""
    return {
        "world": {"width": 12, "height": 12},
        "obstacles": [],
        "agents": [],
        "missions": [],
    }


@pytest.fixture
def scenario_payload() -> dict:
    """A valid POST /scenarios body with one agent and one mission that
    PlanningEngine can assign and SimulationEngine can execute in a few
    ticks -- mirrors docs/api-spec.md's own "Create Scenario" example.
    """
    return {
        "world": {"width": 12, "height": 12},
        "obstacles": [{"id": "wall-0", "x": 6, "y": 0, "type": "Wall"}],
        "agents": [
            {
                "id": "drone-thermal",
                "platform_type": "DRONE",
                "x": 0,
                "y": 0,
                "battery_level": 90,
                "capabilities": ["thermal_camera"],
            }
        ],
        "missions": [
            {
                "id": "thermal-survey",
                "name": "Thermal Survey",
                "description": "Requires a thermal camera.",
                "priority": "HIGH",
                "target_cells": [[2, 0]],
                "required_capabilities": ["thermal_camera"],
            }
        ],
    }
