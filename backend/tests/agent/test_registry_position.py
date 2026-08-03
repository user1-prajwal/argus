"""Tests for AgentRegistry.update_position."""

from __future__ import annotations

import pytest

from app.agent import Agent, AgentNotFoundError, AgentRegistry


def test_update_position_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.update_position(agent.id, 7, 8)

    updated = registry.get_agent(agent.id)
    assert (updated.x, updated.y) == (7, 8)


def test_update_position_preserves_other_fields(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.update_position(agent.id, 7, 8)

    updated = registry.get_agent(agent.id)
    assert updated.battery_level == agent.battery_level
    assert updated.health_status == agent.health_status
    assert updated.activity == agent.activity
    assert updated.registered_at == agent.registered_at


def test_update_position_rejects_negative_coordinates(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)

    with pytest.raises(ValueError):
        registry.update_position(agent.id, -1, 0)

    with pytest.raises(ValueError):
        registry.update_position(agent.id, 0, -1)


def test_update_position_rejects_non_int_coordinates(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)

    with pytest.raises(TypeError):
        registry.update_position(agent.id, 1.5, 0)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        registry.update_position(agent.id, 0, "0")  # type: ignore[arg-type]


def test_update_position_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.update_position("does-not-exist", 0, 0)


def test_update_position_does_not_apply_on_invalid_input(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)

    with pytest.raises(ValueError):
        registry.update_position(agent.id, -1, -1)

    # Position must be unchanged after a failed update.
    unchanged = registry.get_agent(agent.id)
    assert (unchanged.x, unchanged.y) == (agent.x, agent.y)