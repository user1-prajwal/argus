"""Tests for World.add_obstacle / World.remove_obstacle and their effects
on get_cell / is_walkable / get_neighbors."""

from __future__ import annotations

import pytest

from app.world import CellType, DuplicateObstacleError, Obstacle, ObstacleNotFoundError, World


def test_add_obstacle_valid(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Building"))

    assert world.get_cell(2, 2).cell_type is CellType.OBSTACLE
    assert world.world_summary()["obstacles"] == 1


def test_add_obstacle_blocks_walkability(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Tree"))
    assert world.is_walkable(2, 2) is False


def test_add_obstacle_rejects_wrong_type(world: World) -> None:
    with pytest.raises(TypeError):
        world.add_obstacle({"id": "obs-1", "x": 0, "y": 0})  # type: ignore[arg-type]


def test_add_obstacle_rejects_out_of_bounds(world: World) -> None:
    with pytest.raises(ValueError):
        world.add_obstacle(Obstacle(id="obs-1", x=100, y=0, type="Wall"))


def test_add_obstacle_rejects_duplicate_id(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=1, y=1, type="Tree"))

    with pytest.raises(DuplicateObstacleError):
        world.add_obstacle(Obstacle(id="obs-1", x=2, y=2, type="Water"))


def test_add_obstacle_rejects_duplicate_position() -> None:
    w = World(width=10, height=10)
    w.add_obstacle(Obstacle(id="obs-1", x=3, y=3, type="Tree"))

    with pytest.raises(ValueError):
        w.add_obstacle(Obstacle(id="obs-2", x=3, y=3, type="Mountain"))


def test_remove_obstacle_valid(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=4, y=4, type="Tree"))
    world.remove_obstacle("obs-1")

    assert world.get_cell(4, 4).cell_type is CellType.EMPTY
    assert world.is_walkable(4, 4) is True
    assert world.world_summary()["obstacles"] == 0


def test_remove_obstacle_raises_when_not_found(world: World) -> None:
    with pytest.raises(ObstacleNotFoundError):
        world.remove_obstacle("does-not-exist")


def test_remove_obstacle_rejects_wrong_type(world: World) -> None:
    with pytest.raises(TypeError):
        world.remove_obstacle(123)  # type: ignore[arg-type]


def test_remove_obstacle_allows_id_reuse_after_removal(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=1, y=1, type="Tree"))
    world.remove_obstacle("obs-1")

    # Re-adding the same id at a new position should now succeed.
    world.add_obstacle(Obstacle(id="obs-1", x=5, y=5, type="Building"))
    assert world.get_cell(5, 5).cell_type is CellType.OBSTACLE


def test_get_neighbors_excludes_obstacle_cells(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-north", x=5, y=6, type="Tree"))

    neighbors = world.get_neighbors(5, 5)

    assert all(n.cell_type is not CellType.OBSTACLE for n in neighbors)
    assert (5, 6) not in {(n.x, n.y) for n in neighbors}