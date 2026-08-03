"""Tests for AgentRegistry.update_battery."""

from __future__ import annotations

import pytest

from app.agent import Agent, AgentNotFoundError, AgentRegistry


def test_update_battery_valid(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)
    registry.update_battery(agent.id, 42)

    assert registry.get_agent(agent.id).battery_level == 42


@pytest.mark.parametrize("battery_level", [0, 100])
def test_update_battery_allows_boundary_values(
    registry: AgentRegistry, agent: Agent, battery_level: int
) -> None:
    registry.add_agent(agent)
    registry.update_battery(agent.id, battery_level)

    assert registry.get_agent(agent.id).battery_level == battery_level


@pytest.mark.parametrize("battery_level", [-1, 101])
def test_update_battery_rejects_out_of_range(
    registry: AgentRegistry, agent: Agent, battery_level: int
) -> None:
    registry.add_agent(agent)

    with pytest.raises(ValueError):
        registry.update_battery(agent.id, battery_level)


def test_update_battery_rejects_non_int(registry: AgentRegistry, agent: Agent) -> None:
    registry.add_agent(agent)

    with pytest.raises(TypeError):
        registry.update_battery(agent.id, 50.0)  # type: ignore[arg-type]


def test_update_battery_raises_when_agent_not_found(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.update_battery("does-not-exist", 50)