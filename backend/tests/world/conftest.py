"""Shared fixtures for World module tests."""

from __future__ import annotations

import pytest

from app.world import World


@pytest.fixture
def world() -> World:
    """A fresh 10x10 world for each test."""
    return World(width=10, height=10)


@pytest.fixture
def tiny_world() -> World:
    """A 1x1 world, useful for boundary/edge-case tests."""
    return World(width=1, height=1)