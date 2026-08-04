"""Tests for MissionRegistry.assign_agents and MissionRegistry.clear_agents."""

from __future__ import annotations

import pytest

from app.mission import Mission, MissionNotFoundError, MissionRegistry


def test_assign_agents_valid(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)
    registry.assign_agents(mission.id, ["a1", "a2"])

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset({"a1", "a2"})


def test_assign_agents_replaces_entire_set(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)
    registry.assign_agents(mission.id, ["a1", "a2"])
    registry.assign_agents(mission.id, ["a3"])

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset({"a3"})


def test_assign_agents_accepts_empty_iterable(
    registry: MissionRegistry, mission: Mission
) -> None:
    registry.add_mission(mission)
    registry.assign_agents(mission.id, [])

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset()


def test_assign_agents_rejects_single_string(registry: MissionRegistry, mission: Mission) -> None:
    # A bare string is iterable char-by-char -- must be rejected, not
    # silently split into individual characters.
    registry.add_mission(mission)

    with pytest.raises(TypeError):
        registry.assign_agents(mission.id, "a1")  # type: ignore[arg-type]


def test_assign_agents_rejects_non_iterable(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)

    with pytest.raises(TypeError):
        registry.assign_agents(mission.id, 123)  # type: ignore[arg-type]


def test_assign_agents_rejects_non_string_elements(
    registry: MissionRegistry, mission: Mission
) -> None:
    registry.add_mission(mission)

    with pytest.raises(TypeError):
        registry.assign_agents(mission.id, [123])  # type: ignore[arg-type]


def test_assign_agents_rejects_empty_string_element(
    registry: MissionRegistry, mission: Mission
) -> None:
    registry.add_mission(mission)

    with pytest.raises(ValueError):
        registry.assign_agents(mission.id, ["a1", ""])


def test_assign_agents_raises_when_mission_not_found(registry: MissionRegistry) -> None:
    with pytest.raises(MissionNotFoundError):
        registry.assign_agents("does-not-exist", ["a1"])


def test_assign_agents_not_validated_against_any_agent_registry(
    registry: MissionRegistry, mission: Mission
) -> None:
    # docs/mission-model.md: does not validate that an id refers to a
    # real, registered agent.
    registry.add_mission(mission)
    registry.assign_agents(mission.id, ["agent-does-not-exist-anywhere"])

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset(
        {"agent-does-not-exist-anywhere"}
    )


def test_clear_agents_valid(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)
    registry.assign_agents(mission.id, ["a1", "a2"])
    registry.clear_agents(mission.id)

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset()


def test_clear_agents_on_already_unassigned_mission_is_a_no_op(
    registry: MissionRegistry, mission: Mission
) -> None:
    registry.add_mission(mission)
    registry.clear_agents(mission.id)  # must not raise

    assert registry.get_mission(mission.id).assigned_agent_ids == frozenset()


def test_clear_agents_raises_when_mission_not_found(registry: MissionRegistry) -> None:
    with pytest.raises(MissionNotFoundError):
        registry.clear_agents("does-not-exist")