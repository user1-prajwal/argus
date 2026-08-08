"""Tests for PlanningEngine.planning_summary."""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry, Capability, HealthStatus
from app.mission import Mission, MissionRegistry, MissionStatus
from app.planning import PlanningEngine


def test_planning_summary_on_empty_registries(engine: PlanningEngine) -> None:
    summary = engine.planning_summary()

    assert summary == {
        "pending_missions": 0,
        "available_agents": 0,
        "assignable_missions": 0,
        "unassignable_missions": 0,
    }


def test_planning_summary_counts_pending_missions_and_available_agents(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    agents.add_agent(make_agent(agent_id="a2", activity=AgentActivity.CHARGING))
    missions.add_mission(make_mission(mission_id="m1"))
    missions.add_mission(make_mission(mission_id="m2", status=MissionStatus.COMPLETED))

    summary = engine.planning_summary()

    assert summary["pending_missions"] == 1
    assert summary["available_agents"] == 1


def test_planning_summary_distinguishes_assignable_from_unassignable(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", capabilities=frozenset({Capability.LIDAR})))
    missions.add_mission(
        make_mission(mission_id="assignable", required_capabilities=frozenset({Capability.LIDAR}))
    )
    missions.add_mission(
        make_mission(
            mission_id="unassignable",
            required_capabilities=frozenset({Capability.THERMAL_CAMERA}),
        )
    )

    summary = engine.planning_summary()

    assert summary["pending_missions"] == 2
    assert summary["assignable_missions"] == 1
    assert summary["unassignable_missions"] == 1


def test_planning_summary_does_not_mutate_any_state(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1"))

    engine.planning_summary()

    assert missions.get_mission("m1").status is MissionStatus.PENDING
    assert agents.get_agent("a1").activity is AgentActivity.IDLE


def test_planning_summary_available_agents_requires_both_online_and_idle(
    engine: PlanningEngine,
    agents: AgentRegistry,
    make_agent: Callable[..., Agent],
) -> None:
    agents.add_agent(make_agent(agent_id="failed-but-idle", health_status=HealthStatus.FAILED))
    agents.add_agent(make_agent(agent_id="online-but-busy", activity=AgentActivity.EXECUTING_MISSION))
    agents.add_agent(make_agent(agent_id="available"))

    summary = engine.planning_summary()

    assert summary["available_agents"] == 1