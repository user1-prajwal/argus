"""Tests for MissionRegistry construction and basic CRUD: add_mission,
remove_mission, get_mission."""

from __future__ import annotations

from typing import Callable

import pytest

from app.mission import DuplicateMissionError, Mission, MissionNotFoundError, MissionRegistry


def test_new_registry_is_empty(registry: MissionRegistry) -> None:
    assert registry.list_missions() == []
    assert registry.mission_summary()["total"] == 0


def test_add_mission_valid(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)

    assert registry.get_mission(mission.id) == mission
    assert registry.mission_summary()["total"] == 1


def test_add_mission_rejects_wrong_type(registry: MissionRegistry) -> None:
    with pytest.raises(TypeError):
        registry.add_mission({"id": "m1"})  # type: ignore[arg-type]


def test_add_mission_rejects_duplicate_id(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(make_mission(mission_id="m1"))

    with pytest.raises(DuplicateMissionError):
        registry.add_mission(make_mission(mission_id="m1"))


def test_remove_mission_valid(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)
    registry.remove_mission(mission.id)

    assert registry.list_missions() == []
    with pytest.raises(MissionNotFoundError):
        registry.get_mission(mission.id)


def test_remove_mission_raises_when_not_found(registry: MissionRegistry) -> None:
    with pytest.raises(MissionNotFoundError):
        registry.remove_mission("does-not-exist")


def test_remove_mission_rejects_wrong_type(registry: MissionRegistry) -> None:
    with pytest.raises(TypeError):
        registry.remove_mission(123)  # type: ignore[arg-type]


def test_remove_mission_allows_id_reuse_after_removal(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(make_mission(mission_id="m1", name="First"))
    registry.remove_mission("m1")

    registry.add_mission(make_mission(mission_id="m1", name="Second"))
    assert registry.get_mission("m1").name == "Second"


def test_get_mission_raises_when_not_found(registry: MissionRegistry) -> None:
    with pytest.raises(MissionNotFoundError):
        registry.get_mission("does-not-exist")


def test_get_mission_rejects_wrong_type(registry: MissionRegistry) -> None:
    with pytest.raises(TypeError):
        registry.get_mission(123)  # type: ignore[arg-type]