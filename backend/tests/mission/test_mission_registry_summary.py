"""Tests for MissionRegistry.list_missions and MissionRegistry.mission_summary."""

from __future__ import annotations

from typing import Callable

from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus


def test_list_missions_empty(registry: MissionRegistry) -> None:
    assert registry.list_missions() == []


def test_list_missions_returns_all_registered_missions(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(make_mission(mission_id="m1"))
    registry.add_mission(make_mission(mission_id="m2"))

    ids = {m.id for m in registry.list_missions()}
    assert ids == {"m1", "m2"}


def test_mission_summary_on_empty_registry(registry: MissionRegistry) -> None:
    summary = registry.mission_summary()

    assert summary["total"] == 0
    assert summary["status"] == {
        "pending": 0,
        "assigned": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
    }
    assert summary["priority"] == {"low": 0, "medium": 0, "high": 0, "critical": 0}


def test_mission_summary_reflects_registered_missions(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(
        make_mission(mission_id="m1", status=MissionStatus.PENDING, priority=MissionPriority.LOW)
    )
    registry.add_mission(
        make_mission(
            mission_id="m2", status=MissionStatus.IN_PROGRESS, priority=MissionPriority.HIGH
        )
    )
    registry.add_mission(
        make_mission(mission_id="m3", status=MissionStatus.PENDING, priority=MissionPriority.HIGH)
    )

    summary = registry.mission_summary()

    assert summary["total"] == 3
    assert summary["status"]["pending"] == 2
    assert summary["status"]["in_progress"] == 1
    assert summary["priority"]["high"] == 2
    assert summary["priority"]["low"] == 1


def test_mission_summary_updates_after_removal(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(make_mission(mission_id="m1"))
    registry.remove_mission("m1")

    assert registry.mission_summary()["total"] == 0


def test_mission_summary_reflects_status_updates(
    registry: MissionRegistry, make_mission: Callable[..., Mission]
) -> None:
    registry.add_mission(make_mission(mission_id="m1", status=MissionStatus.PENDING))
    registry.update_status("m1", MissionStatus.COMPLETED)

    summary = registry.mission_summary()
    assert summary["status"]["pending"] == 0
    assert summary["status"]["completed"] == 1