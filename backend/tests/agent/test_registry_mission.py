"""Tests for AgentRegistry.assign_mission and AgentRegistry.clear_mission."""

from __future__ import annotations

import pytest

from app.agent import Agent, AgentNotFoundError, AgentRegistry


def test_assign_mission_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.assign_mission(agent.id, "mission-1")

    assert registry.get_agent(agent.id).current_mission_id == "mission-1"


def test_assign_mission_rejects_empty_string(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)

    with pytest.raises(ValueError):
        registry.assign_mission(agent.id, "")


def test_assign_mission_rejects_wrong_type(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)

    with pytest.raises(TypeError):
        registry.assign_mission(agent.id, 123)  # type: ignore[arg-type]


def test_assign_mission_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.assign_mission("does-not-exist", "mission-1")


def test_assign_mission_not_validated_against_any_mission_module(
    registry: AgentRegistry, agent: Agent
) -> None:
    # docs/agent-model.md: the Agent Model does not validate that the
    # referenced mission exists.
    registry.add_agent(agent)
    registry.assign_mission(agent.id, "mission-does-not-exist-anywhere")

    assert registry.get_agent(agent.id).current_mission_id == "mission-does-not-exist-anywhere"


def test_reassigning_mission_overwrites_previous_value(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)
    registry.assign_mission(agent.id, "mission-1")
    registry.assign_mission(agent.id, "mission-2")

    assert registry.get_agent(agent.id).current_mission_id == "mission-2"


def test_clear_mission_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.assign_mission(agent.id, "mission-1")
    registry.clear_mission(agent.id)

    assert registry.get_agent(agent.id).current_mission_id is None


def test_clear_mission_on_already_unassigned_agent_is_a_no_op(
    registry: AgentRegistry, agent: Agent
) -> None:
    registry.add_agent(agent)
    registry.clear_mission(agent.id)  # must not raise

    assert registry.get_agent(agent.id).current_mission_id is None


def test_clear_mission_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.clear_mission("does-not-exist")