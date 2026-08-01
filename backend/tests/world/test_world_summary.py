"""Tests for World.world_summary."""

from __future__ import annotations

from app.world import ChargingStation, MissionZone, Obstacle, SpawnPoint, World


def test_summary_on_empty_world(world: World) -> None:
    assert world.world_summary() == {
        "width": 10,
        "height": 10,
        "obstacles": 0,
        "spawn_points": 0,
        "charging_stations": 0,
        "mission_zones": 0,
    }


def test_summary_reflects_all_entity_counts(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=0, y=0, type="Tree"))
    world.add_obstacle(Obstacle(id="obs-2", x=1, y=0, type="Building"))
    world.add_spawn_point(SpawnPoint(id="sp-1", x=2, y=0))
    world.add_charging_station(ChargingStation(id="cs-1", x=3, y=0, capacity=2))
    world.add_mission_zone(
        MissionZone(
            id="mz-1",
            name="Zone A",
            priority=1,
            cells=[(4, 0), (4, 1)],
            mission_id="mission-1",
        )
    )

    assert world.world_summary() == {
        "width": 10,
        "height": 10,
        "obstacles": 2,
        "spawn_points": 1,
        "charging_stations": 1,
        "mission_zones": 1,
    }


def test_summary_decrements_after_obstacle_removal(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=0, y=0, type="Tree"))
    world.remove_obstacle("obs-1")

    assert world.world_summary()["obstacles"] == 0