"""Tests for PlanningEngine.plan."""

from __future__ import annotations

from typing import Callable

from app.agent import Agent, AgentActivity, AgentRegistry, Capability, HealthStatus
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.planning import PlanningEngine


def test_plan_on_empty_registries_returns_empty_list(engine: PlanningEngine) -> None:
    assert engine.plan() == []


def test_plan_assigns_single_eligible_agent_to_single_pending_mission(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1"))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": "a1"}]
    assert missions.get_mission("m1").status is MissionStatus.ASSIGNED
    assert missions.get_mission("m1").assigned_agent_ids == frozenset({"a1"})
    assert agents.get_agent("a1").activity is AgentActivity.ASSIGNED
    assert agents.get_agent("a1").current_mission_id == "m1"


def test_plan_leaves_mission_pending_when_no_agent_matches_capabilities(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", capabilities=frozenset({Capability.GPS})))
    missions.add_mission(
        make_mission(mission_id="m1", required_capabilities=frozenset({Capability.LIDAR}))
    )

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": None}]
    assert missions.get_mission("m1").status is MissionStatus.PENDING


def test_plan_ignores_agents_that_are_not_online(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", health_status=HealthStatus.FAILED))
    missions.add_mission(make_mission(mission_id="m1"))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": None}]


def test_plan_ignores_agents_that_are_not_idle(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", activity=AgentActivity.CHARGING))
    missions.add_mission(make_mission(mission_id="m1"))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": None}]


def test_plan_ignores_missions_that_are_not_pending(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", status=MissionStatus.IN_PROGRESS))

    results = engine.plan()

    assert results == []
    assert agents.get_agent("a1").activity is AgentActivity.IDLE


def test_plan_prefers_higher_battery_level(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="low-battery", battery_level=20))
    agents.add_agent(make_agent(agent_id="high-battery", battery_level=90))
    missions.add_mission(make_mission(mission_id="m1"))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": "high-battery"}]


def test_plan_breaks_battery_ties_with_lower_agent_id(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="zzz", battery_level=50))
    agents.add_agent(make_agent(agent_id="aaa", battery_level=50))
    missions.add_mission(make_mission(mission_id="m1"))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": "aaa"}]


def test_plan_processes_higher_priority_missions_first(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # Only one agent exists, so only the higher-priority mission can win it.
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="low", priority=MissionPriority.LOW))
    missions.add_mission(make_mission(mission_id="critical", priority=MissionPriority.CRITICAL))

    results = engine.plan()

    result_by_mission = {r["mission_id"]: r["assigned_agent_id"] for r in results}
    assert result_by_mission["critical"] == "a1"
    assert result_by_mission["low"] is None


def test_plan_does_not_reuse_an_agent_already_assigned_earlier_in_the_same_call(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", priority=MissionPriority.CRITICAL))
    missions.add_mission(make_mission(mission_id="m2", priority=MissionPriority.HIGH))

    results = engine.plan()

    result_by_mission = {r["mission_id"]: r["assigned_agent_id"] for r in results}
    assert result_by_mission["m1"] == "a1"
    assert result_by_mission["m2"] is None


def test_plan_requires_all_capabilities_not_just_overlap(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(make_agent(agent_id="a1", capabilities=frozenset({Capability.LIDAR})))
    missions.add_mission(
        make_mission(
            mission_id="m1",
            required_capabilities=frozenset({Capability.LIDAR, Capability.THERMAL_CAMERA}),
        )
    )

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": None}]


def test_plan_allows_agent_with_extra_capabilities_beyond_what_is_required(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    agents.add_agent(
        make_agent(
            agent_id="a1",
            capabilities=frozenset({Capability.LIDAR, Capability.GPS, Capability.STANDARD_CAMERA}),
        )
    )
    missions.add_mission(
        make_mission(mission_id="m1", required_capabilities=frozenset({Capability.LIDAR}))
    )

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": "a1"}]


def test_plan_does_not_touch_world(
    engine: PlanningEngine,
    agents: AgentRegistry,
    missions: MissionRegistry,
    make_agent: Callable[..., Agent],
    make_mission: Callable[..., Mission],
) -> None:
    # No World read is exercised by Version 1 -- a completely empty world
    # (no obstacles, spawn points, etc.) must not affect planning at all.
    agents.add_agent(make_agent(agent_id="a1"))
    missions.add_mission(make_mission(mission_id="m1", target_cells=frozenset({(999, 999)})))

    results = engine.plan()

    assert results == [{"mission_id": "m1", "assigned_agent_id": "a1"}]