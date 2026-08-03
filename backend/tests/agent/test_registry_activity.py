"""Tests for AgentRegistry.update_activity."""

from __future__ import annotations

import pytest

from app.agent import Agent, AgentActivity, AgentNotFoundError, AgentRegistry, HealthStatus


def test_update_activity_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.update_activity(agent.id, AgentActivity.CHARGING)

    assert registry.get_agent(agent.id).activity is AgentActivity.CHARGING


def test_update_activity_is_independent_of_health_status(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)
    registry.update_health_status(agent.id, HealthStatus.OFFLINE)
    registry.update_activity(agent.id, AgentActivity.RETURNING)

    updated = registry.get_agent(agent.id)
    assert updated.activity is AgentActivity.RETURNING
    assert updated.health_status is HealthStatus.OFFLINE


def test_update_activity_rejects_wrong_type(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)

    with pytest.raises(TypeError):
        registry.update_activity(agent.id, "IDLE")  # type: ignore[arg-type]


def test_update_activity_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.update_activity("does-not-exist", AgentActivity.IDLE)


def test_update_activity_does_not_require_current_mission_id(
    registry: AgentRegistry, agent: Agent
) -> None:
    # docs/agent-model.md: Version 1 does not enforce consistency between
    # current_mission_id and Agent Activity.
    registry.add_agent(agent)
    registry.update_activity(agent.id, AgentActivity.ASSIGNED)

    updated = registry.get_agent(agent.id)
    assert updated.activity is AgentActivity.ASSIGNED
    assert updated.current_mission_id is None