"""Tests for PlanningEngine.assign_mission."""

from __future__ import annotations

from typing import Callable

import pytest

from app.agent import Agent, AgentActivity, AgentRegistry
from app.mission import Mission, MissionNotFoundError, MissionRegistry, MissionStatus
from app.planning import PlanningEngine


def test_assign_mission_valid(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1"))

    result = engine.assign_mission("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": "a1"}
    assert missions.get_mission("m1").status is MissionStatus.ASSIGNED
    assert agents.get_agent("a1").activity is AgentActivity.ASSIGNED


def test_assign_mission_raises_when_mission_not_found(engine: PlanningEngine) -> None:
    with pytest.raises(MissionNotFoundError):
        engine.assign_mission("does-not-exist")


def test_assign_mission_returns_none_when_no_agent_is_eligible(
    engine: PlanningEngine,
    missions: MissionRegistry,
    make_mission: Callable[..., Mission],
) -> None:
    missions.add_mission(make_mission(mission_id="m1"))

    result = engine.assign_mission("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": None}
    assert missions.get_mission("m1").status is MissionStatus.PENDING


@pytest.mark.parametrize(
    "status",
    [
        MissionStatus.ASSIGNED,
        MissionStatus.IN_PROGRESS,
        MissionStatus.COMPLETED,
        MissionStatus.FAILED,
        MissionStatus.CANCELLED,
    ],
)
def test_assign_mission_is_a_no_op_for_non_pending_missions(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
    status: MissionStatus,
) -> None:
    # A completed (or otherwise non-pending) mission must never receive
    # a new agent assignment just because an eligible agent exists.
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", status=status))

    result = engine.assign_mission("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": None}
    assert missions.get_mission("m1").status is status
    assert agents.get_agent("a1").activity is AgentActivity.IDLE


def test_assign_mission_does_not_release_an_existing_assignment(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # docs/planning-api.md: assign_mission does not release any agent the
    # mission may already have. Combined with the PENDING-only rule above,
    # an already-ASSIGNED mission is simply left untouched.
    agents.add_agent(make_agent(agent_id="original-agent", activity=AgentActivity.ASSIGNED))
    agents.add_agent(make_agent(agent_id="new-agent"))
    missions.add_mission(
        make_mission(
            mission_id="m1",
            status=MissionStatus.ASSIGNED,
            assigned_agent_ids=frozenset({"original-agent"}),
        )
    )

    result = engine.assign_mission("m1")

    assert result == {"mission_id": "m1", "assigned_agent_id": None}
    assert missions.get_mission("m1").assigned_agent_ids == frozenset({"original-agent"})
    assert agents.get_agent("new-agent").activity is AgentActivity.IDLE