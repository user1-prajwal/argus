"""Tests for AgentRegistry.list_agents and AgentRegistry.agent_summary."""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry, HealthStatus


def test_list_agents_empty(registry: AgentRegistry) -> None:
    assert registry.list_agents() == []


def test_list_agents_returns_all_registered_agents(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(make_agent(agent_id="a1"))
    registry.add_agent(make_agent(agent_id="a2"))

    ids = {a.id for a in registry.list_agents()}
    assert ids == {"a1", "a2"}


def test_agent_summary_on_empty_registry(registry: AgentRegistry) -> None:
    summary = registry.agent_summary()

    assert summary["total"] == 0
    assert summary["health_status"] == {"online": 0, "failed": 0, "offline": 0}
    assert summary["activity"] == {
        "idle": 0,
        "assigned": 0,
        "executing_mission": 0,
        "returning": 0,
        "charging": 0,
    }


def test_agent_summary_reflects_registered_agents(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(
        make_agent(agent_id="a1", health_status=HealthStatus.ONLINE, activity=AgentActivity.IDLE)
    )
    registry.add_agent(
        make_agent(
            agent_id="a2",
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.EXECUTING_MISSION,
        )
    )
    registry.add_agent(
        make_agent(agent_id="a3", health_status=HealthStatus.FAILED, activity=AgentActivity.IDLE)
    )

    summary = registry.agent_summary()

    assert summary["total"] == 3
    assert summary["health_status"]["online"] == 2
    assert summary["health_status"]["failed"] == 1
    assert summary["health_status"]["offline"] == 0
    assert summary["activity"]["idle"] == 2
    assert summary["activity"]["executing_mission"] == 1


def test_agent_summary_updates_after_removal(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(make_agent(agent_id="a1"))
    registry.remove_agent("a1")

    assert registry.agent_summary()["total"] == 0


def test_agent_summary_reflects_status_updates(
    registry: AgentRegistry, make_agent: Callable[..., Agent]
) -> None:
    registry.add_agent(make_agent(agent_id="a1", health_status=HealthStatus.ONLINE))
    registry.update_health_status("a1", HealthStatus.FAILED)

    summary = registry.agent_summary()
    assert summary["health_status"]["online"] == 0
    assert summary["health_status"]["failed"] == 1