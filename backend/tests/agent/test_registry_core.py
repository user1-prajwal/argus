"""Tests for AgentRegistry construction and basic CRUD: add_agent,
remove_agent, get_agent."""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import Agent, AgentNotFoundError, AgentRegistry, DuplicateAgentError


def test_new_registry_is_empty(registry: AgentRegistry) -> None:
    assert registry.list_agents() == []
    assert registry.agent_summary()["total"] == 0


def test_add_agent_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)

    assert registry.get_agent(agent.id) == agent
    assert registry.agent_summary()["total"] == 1


def test_add_agent_rejects_wrong_type(registry: AgentRegistry) -> None:
    with pytest.raises(TypeError):
        registry.add_agent({"id": "a1"})  # type: ignore[arg-type]


def test_add_agent_rejects_duplicate_id(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(make_agent(agent_id="a1"))

    with pytest.raises(DuplicateAgentError):
        registry.add_agent(make_agent(agent_id="a1"))


def test_remove_agent_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.remove_agent(agent.id)

    assert registry.list_agents() == []
    with pytest.raises(AgentNotFoundError):
        registry.get_agent(agent.id)


def test_remove_agent_raises_when_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.remove_agent("does-not-exist")


def test_remove_agent_rejects_wrong_type(registry: AgentRegistry) -> None:
    with pytest.raises(TypeError):
        registry.remove_agent(123)  # type: ignore[arg-type]


def test_remove_agent_allows_id_reuse_after_removal(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(make_agent(agent_id="a1", x=0, y=0))
    registry.remove_agent("a1")

    registry.add_agent(make_agent(agent_id="a1", x=5, y=5))
    assert registry.get_agent("a1").x == 5


def test_get_agent_raises_when_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.get_agent("does-not-exist")


def test_get_agent_rejects_wrong_type(registry: AgentRegistry) -> None:
    with pytest.raises(TypeError):
        registry.get_agent(123)  # type: ignore[arg-type]