"""Tests for MissionRegistry.update_status."""

from __future__ import annotations

import pytest

from app.mission import Mission, MissionNotFoundError, MissionRegistry, MissionStatus


def test_update_status_valid(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)
    registry.update_status(mission.id, MissionStatus.IN_PROGRESS)

    assert registry.get_mission(mission.id).status is MissionStatus.IN_PROGRESS


def test_update_status_preserves_other_fields_and_created_at(
    registry: MissionRegistry, mission: Mission
) -> None:
    registry.add_mission(mission)
    registry.update_status(mission.id, MissionStatus.COMPLETED)

    updated = registry.get_mission(mission.id)
    assert updated.name == mission.name
    assert updated.priority == mission.priority
    assert updated.target_cells == mission.target_cells
    assert updated.created_at == mission.created_at


def test_update_status_rejects_wrong_type(registry: MissionRegistry, mission: Mission) -> None:
    registry.add_mission(mission)

    with pytest.raises(TypeError):
        registry.update_status(mission.id, "COMPLETED")  # type: ignore[arg-type]


def test_update_status_raises_when_mission_not_found(registry: MissionRegistry) -> None:
    with pytest.raises(MissionNotFoundError):
        registry.update_status("does-not-exist", MissionStatus.CANCELLED)


def test_update_status_allows_any_transition(
    registry: MissionRegistry, mission: Mission
) -> None:
    # docs/mission-model.md: no particular transition order is enforced.
    registry.add_mission(mission)
    registry.update_status(mission.id, MissionStatus.COMPLETED)
    registry.update_status(mission.id, MissionStatus.PENDING)

    assert registry.get_mission(mission.id).status is MissionStatus.PENDING