"""Tests for app.mission.mission.Mission."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest

from app.agent import Capability
from app.mission import Mission, MissionPriority, MissionStatus


def test_mission_valid_construction(make_mission: Callable[..., Mission]) -> None:
    mission = make_mission(
        mission_id="m1",
        name="Search A",
        description="Find survivors",
        target_cells=frozenset({(1, 1), (2, 2)}),
    )

    assert mission.id == "m1"
    assert mission.name == "Search A"
    assert mission.description == "Find survivors"
    assert mission.target_cells == frozenset({(1, 1), (2, 2)})
    assert mission.priority is MissionPriority.MEDIUM
    assert mission.status is MissionStatus.PENDING
    assert mission.required_capabilities == frozenset()
    assert mission.assigned_agent_ids == frozenset()


def test_mission_rejects_empty_id(make_mission: Callable[..., Mission]) -> None:
    with pytest.raises(ValueError):
        make_mission(mission_id="")


def test_mission_rejects_empty_name(make_mission: Callable[..., Mission]) -> None:
    with pytest.raises(ValueError):
        make_mission(name="")


def test_mission_rejects_empty_description(make_mission: Callable[..., Mission]) -> None:
    with pytest.raises(ValueError):
        make_mission(description="")


def test_mission_rejects_empty_target_cells(make_mission: Callable[..., Mission]) -> None:
    with pytest.raises(ValueError):
        make_mission(target_cells=frozenset())


@pytest.mark.parametrize(
    "cells", [frozenset({(-1, 0)}), frozenset({(0, -1)}), frozenset({(0, 0), (-5, -5)})]
)
def test_mission_rejects_negative_target_cell_coordinates(
    make_mission: Callable[..., Mission], cells: frozenset
) -> None:
    with pytest.raises(ValueError):
        make_mission(target_cells=cells)


def test_mission_normalizes_target_cells_to_frozenset(
    make_mission: Callable[..., Mission]
) -> None:
    mission = make_mission(target_cells=[(1, 1), (1, 1), (2, 2)])

    assert isinstance(mission.target_cells, frozenset)
    assert mission.target_cells == frozenset({(1, 1), (2, 2)})


def test_mission_normalizes_required_capabilities_to_frozenset(
    make_mission: Callable[..., Mission]
) -> None:
    mission = make_mission(
        required_capabilities=[Capability.LIDAR, Capability.LIDAR, Capability.GPS]
    )

    assert isinstance(mission.required_capabilities, frozenset)
    assert mission.required_capabilities == frozenset({Capability.LIDAR, Capability.GPS})


def test_mission_required_capabilities_defaults_to_empty(
    make_mission: Callable[..., Mission]
) -> None:
    mission = make_mission()

    assert mission.required_capabilities == frozenset()


def test_mission_normalizes_assigned_agent_ids_to_frozenset(
    make_mission: Callable[..., Mission]
) -> None:
    mission = make_mission(assigned_agent_ids=["a1", "a1", "a2"])

    assert isinstance(mission.assigned_agent_ids, frozenset)
    assert mission.assigned_agent_ids == frozenset({"a1", "a2"})


def test_mission_assigned_agent_ids_defaults_to_empty(
    make_mission: Callable[..., Mission]
) -> None:
    mission = make_mission()

    assert mission.assigned_agent_ids == frozenset()


def test_mission_is_immutable(make_mission: Callable[..., Mission]) -> None:
    mission = make_mission()

    with pytest.raises(dataclasses.FrozenInstanceError):
        mission.status = MissionStatus.COMPLETED  # type: ignore[misc]


def test_mission_created_at_is_set_automatically(
    make_mission: Callable[..., Mission]
) -> None:
    before = datetime.now(timezone.utc)
    mission = make_mission()
    after = datetime.now(timezone.utc)

    assert isinstance(mission.created_at, datetime)
    assert before <= mission.created_at <= after


def test_mission_created_at_cannot_be_supplied_by_caller() -> None:
    # created_at has init=False, so passing it must raise TypeError
    # rather than silently being accepted.
    with pytest.raises(TypeError):
        Mission(
            id="m1",
            name="Search A",
            description="Find survivors",
            priority=MissionPriority.MEDIUM,
            status=MissionStatus.PENDING,
            target_cells=frozenset({(0, 0)}),
            created_at=datetime.now(timezone.utc),  # type: ignore[call-arg]
        )


def test_mission_equality_is_value_based(make_mission: Callable[..., Mission]) -> None:
    a = make_mission(mission_id="same-id")
    b = dataclasses.replace(a, id="same-id")
    # dataclasses.replace() regenerates created_at (it has init=False),
    # so force it back to a's value to isolate equality to the fields
    # that matter for this test.
    object.__setattr__(b, "created_at", a.created_at)

    assert a == b


def test_missions_with_different_created_at_are_not_equal(
    make_mission: Callable[..., Mission]
) -> None:
    a = make_mission(mission_id="same-id")
    b = dataclasses.replace(a, id="same-id")
    object.__setattr__(b, "created_at", a.created_at + timedelta(seconds=1))

    assert a != b