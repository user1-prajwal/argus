"""Tests for World.add_mission_zone."""

from __future__ import annotations

import pytest

from app.world import CellType, DuplicateMissionZoneError, MissionZone, Obstacle, World


def _zone(id: str = "mz-1", cells=None, mission_id: str = "mission-1") -> MissionZone:
    return MissionZone(
        id=id,
        name="Search Sector",
        priority=1,
        cells=cells if cells is not None else [(0, 0), (0, 1), (1, 0), (1, 1)],
        mission_id=mission_id,
    )


def test_add_mission_zone_valid(world: World) -> None:
    world.add_mission_zone(_zone())

    assert world.get_cell(0, 0).cell_type is CellType.MISSION_ZONE
    assert world.get_cell(1, 1).cell_type is CellType.MISSION_ZONE
    assert world.world_summary()["mission_zones"] == 1


def test_add_mission_zone_rejects_wrong_type(world: World) -> None:
    with pytest.raises(TypeError):
        world.add_mission_zone({"id": "mz-1"})  # type: ignore[arg-type]


def test_add_mission_zone_rejects_cell_out_of_bounds(world: World) -> None:
    with pytest.raises(ValueError):
        world.add_mission_zone(_zone(cells=[(0, 0), (999, 999)]))


def test_add_mission_zone_rejects_duplicate_id(world: World) -> None:
    world.add_mission_zone(_zone(id="mz-1", cells=[(0, 0)]))

    with pytest.raises(DuplicateMissionZoneError):
        world.add_mission_zone(_zone(id="mz-1", cells=[(1, 1)]))


def test_add_mission_zone_rejects_overlap_with_obstacle(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Building"))

    with pytest.raises(ValueError):
        world.add_mission_zone(_zone(cells=[(2, 2), (3, 3)]))


def test_add_mission_zone_does_not_partially_apply_on_overlap_failure(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Building"))

    with pytest.raises(ValueError):
        world.add_mission_zone(_zone(cells=[(0, 0), (2, 2)]))

    # (0, 0) must NOT have been registered as part of a mission zone,
    # since the whole add_mission_zone call failed.
    assert world.get_cell(0, 0).cell_type is CellType.EMPTY
    assert world.world_summary()["mission_zones"] == 0


def test_mission_id_can_own_multiple_mission_zones(world: World) -> None:
    world.add_mission_zone(_zone(id="mz-1", cells=[(0, 0)], mission_id="mission-1"))
    world.add_mission_zone(_zone(id="mz-2", cells=[(1, 1)], mission_id="mission-1"))

    assert world.world_summary()["mission_zones"] == 2


def test_mission_zones_may_spatially_overlap_each_other(world: World) -> None:
    # Not forbidden by docs/world-model.md; only overlap with obstacles is.
    world.add_mission_zone(_zone(id="mz-1", cells=[(5, 5)], mission_id="mission-1"))
    world.add_mission_zone(_zone(id="mz-2", cells=[(5, 5)], mission_id="mission-2"))

    assert world.get_cell(5, 5).cell_type is CellType.MISSION_ZONE
    assert world.world_summary()["mission_zones"] == 2