"""Tests for PlanningEngine.replan."""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import Agent, AgentActivity, AgentRegistry, HealthStatus
from app.mission import Mission, MissionNotFoundError, MissionRegistry, MissionStatus
from app.planning import PlanningEngine


def test_replan_releases_previous_agent_and_reassigns(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(
        make_agent(agent_id="old-agent", activity=AgentActivity.ASSIGNED, current_mission_id="m1")
    )
    agents.add_agent(make_agent(agent_id="new-agent"))
    missions.add_mission(
        make_mission(
            mission_id="m1",
            status=MissionStatus.ASSIGNED,
            assigned_agent_ids=frozenset({"old-agent"}),
        )
    )

    result = engine.replan("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": "new-agent"}
    assert agents.get_agent("old-agent").activity is AgentActivity.IDLE
    assert agents.get_agent("old-agent").current_mission_id is None
    assert agents.get_agent("new-agent").activity is AgentActivity.ASSIGNED
    assert missions.get_mission("m1").assigned_agent_ids == frozenset({"new-agent"})
    assert missions.get_mission("m1").status is MissionStatus.ASSIGNED


def test_replan_on_never_assigned_mission_behaves_like_assign(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", status=MissionStatus.PENDING))

    result = engine.replan("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": "a1"}


def test_replan_raises_when_mission_not_found(engine: PlanningEngine) -> None:
    with pytest.raises(MissionNotFoundError):
        engine.replan("does-not-exist")


def test_replan_returns_none_and_leaves_mission_pending_when_no_agent_is_eligible(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(
        make_agent(
            agent_id="old-agent",
            health_status=HealthStatus.FAILED,
            activity=AgentActivity.ASSIGNED,
            current_mission_id="m1",
        )
    )
    missions.add_mission(
        make_mission(
            mission_id="m1",
            status=MissionStatus.ASSIGNED,
            assigned_agent_ids=frozenset({"old-agent"}),
        )
    )

    result = engine.replan("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": None}
    assert missions.get_mission("m1").status is MissionStatus.PENDING
    assert missions.get_mission("m1").assigned_agent_ids == frozenset()
    # The old agent was still released even though no replacement was found.
    assert agents.get_agent("old-agent").activity is AgentActivity.IDLE


def test_replan_skips_a_previously_assigned_agent_that_no_longer_exists(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # The agent referenced by assigned_agent_ids was removed from the
    # AgentRegistry after the mission was assigned -- replan must not
    # raise because of this.
    agents.add_agent(make_agent(agent_id="new-agent"))
    missions.add_mission(
        make_mission(
            mission_id="m1",
            status=MissionStatus.ASSIGNED,
            assigned_agent_ids=frozenset({"agent-that-no-longer-exists"}),
        )
    )

    result = engine.replan("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": "new-agent"}


def test_replan_does_not_reassign_the_same_agent_if_it_is_no_longer_eligible(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # Simulates the motivating scenario: the previously assigned agent
    # has since failed.
    agents.add_agent(
        make_agent(
            agent_id="failed-agent",
            health_status=HealthStatus.FAILED,
            activity=AgentActivity.ASSIGNED,
            current_mission_id="m1",
        )
    )
    agents.add_agent(make_agent(agent_id="healthy-agent"))
    missions.add_mission(
        make_mission(
            mission_id="m1",
            status=MissionStatus.ASSIGNED,
            assigned_agent_ids=frozenset({"failed-agent"}),
        )
    )

    result = engine.replan("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": "healthy-agent"}