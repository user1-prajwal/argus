"""Tests for AgentRegistry.update_health_status."""

from __future__ import annotations

import pytest

from app.agent import Agent, AgentActivity, AgentNotFoundError, AgentRegistry, HealthStatus


def test_update_health_status_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.update_health_status(agent.id, HealthStatus.FAILED)

    assert registry.get_agent(agent.id).health_status is HealthStatus.FAILED


def test_update_health_status_is_independent_of_activity(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)
    registry.update_activity(agent.id, AgentActivity.EXECUTING_MISSION)
    registry.update_health_status(agent.id, HealthStatus.FAILED)

    updated = registry.get_agent(agent.id)
    assert updated.health_status is HealthStatus.FAILED
    assert updated.activity is AgentActivity.EXECUTING_MISSION


def test_update_health_status_rejects_wrong_type(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)

    with pytest.raises(TypeError):
        registry.update_health_status(agent.id, "ONLINE")  # type: ignore[arg-type]


def test_update_health_status_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.update_health_status("does-not-exist", HealthStatus.OFFLINE)