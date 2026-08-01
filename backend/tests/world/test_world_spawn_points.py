"""Tests for World.add_spawn_point."""

from __future__ import annotations

import pytest

from app.world import CellType, DuplicateSpawnPointError, Obstacle, SpawnPoint, World


def test_add_spawn_point_valid(world: World) -> None:
    world.add_spawn_point(SpawnPoint(id="sp-1", x=3, y=3))

    assert world.get_cell(3, 3).cell_type is CellType.SPAWN_POINT
    assert world.world_summary()["spawn_points"] == 1


def test_add_spawn_point_rejects_wrong_type(world: World) -> None:
    with pytest.raises(TypeError):
        world.add_spawn_point(("sp-1", 0, 0))  # type: ignore[arg-type]


def test_add_spawn_point_rejects_out_of_bounds(world: World) -> None:
    with pytest.raises(ValueError):
        world.add_spawn_point(SpawnPoint(id="sp-1", x=999, y=0))


def test_add_spawn_point_rejects_duplicate_id(world: World) -> None:
    world.add_spawn_point(SpawnPoint(id="sp-1", x=1, y=1))

    with pytest.raises(DuplicateSpawnPointError):
        world.add_spawn_point(SpawnPoint(id="sp-1", x=2, y=2))


def test_add_spawn_point_rejects_position_inside_obstacle(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=4, y=4, type="Building"))

    with pytest.raises(ValueError):
        world.add_spawn_point(SpawnPoint(id="sp-1", x=4, y=4))


def test_two_spawn_points_can_have_different_positions(world: World) -> None:
    world.add_spawn_point(SpawnPoint(id="sp-1", x=1, y=1))
    world.add_spawn_point(SpawnPoint(id="sp-2", x=2, y=2))

    assert world.world_summary()["spawn_points"] == 2