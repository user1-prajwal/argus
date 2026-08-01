"""Tests for app.world.entities."""

from __future__ import annotations

import dataclasses

import pytest

from app.world import ChargingStation, MissionZone, Obstacle, SpawnPoint


# ----------------------------------------------------------------------
# Obstacle
# ----------------------------------------------------------------------


def test_obstacle_valid_construction() -> None:
    obstacle = Obstacle(id="obs-1", x=2, y=3, type="Building")

    assert obstacle.id == "obs-1"
    assert (obstacle.x, obstacle.y) == (2, 3)
    assert obstacle.type == "Building"


def test_obstacle_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        Obstacle(id="", x=0, y=0, type="Tree")


def test_obstacle_rejects_empty_type() -> None:
    with pytest.raises(ValueError):
        Obstacle(id="obs-1", x=0, y=0, type="")


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1), (-5, -5)])
def test_obstacle_rejects_negative_coordinates(x: int, y: int) -> None:
    with pytest.raises(ValueError):
        Obstacle(id="obs-1", x=x, y=y, type="Wall")


def test_obstacle_is_immutable() -> None:
    obstacle = Obstacle(id="obs-1", x=0, y=0, type="Tree")

    with pytest.raises(dataclasses.FrozenInstanceError):
        obstacle.type = "Water"  # type: ignore[misc]


# ----------------------------------------------------------------------
# SpawnPoint
# ----------------------------------------------------------------------


def test_spawn_point_valid_construction() -> None:
    spawn = SpawnPoint(id="sp-1", x=1, y=1)

    assert spawn.id == "sp-1"
    assert (spawn.x, spawn.y) == (1, 1)


def test_spawn_point_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        SpawnPoint(id="", x=0, y=0)


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1)])
def test_spawn_point_rejects_negative_coordinates(x: int, y: int) -> None:
    with pytest.raises(ValueError):
        SpawnPoint(id="sp-1", x=x, y=y)


# ----------------------------------------------------------------------
# ChargingStation
# ----------------------------------------------------------------------


def test_charging_station_valid_construction() -> None:
    station = ChargingStation(id="cs-1", x=5, y=5, capacity=4)

    assert station.capacity == 4
    assert station.occupied_slots == 0


def test_charging_station_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        ChargingStation(id="", x=0, y=0, capacity=1)


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1)])
def test_charging_station_rejects_negative_coordinates(x: int, y: int) -> None:
    with pytest.raises(ValueError):
        ChargingStation(id="cs-1", x=x, y=y, capacity=1)


@pytest.mark.parametrize("capacity", [0, -1, -10])
def test_charging_station_rejects_non_positive_capacity(capacity: int) -> None:
    with pytest.raises(ValueError):
        ChargingStation(id="cs-1", x=0, y=0, capacity=capacity)


def test_charging_station_rejects_occupied_slots_above_capacity() -> None:
    with pytest.raises(ValueError):
        ChargingStation(id="cs-1", x=0, y=0, capacity=2, occupied_slots=3)


def test_charging_station_rejects_negative_occupied_slots() -> None:
    with pytest.raises(ValueError):
        ChargingStation(id="cs-1", x=0, y=0, capacity=2, occupied_slots=-1)


def test_charging_station_allows_occupied_slots_equal_to_capacity() -> None:
    station = ChargingStation(id="cs-1", x=0, y=0, capacity=2, occupied_slots=2)

    assert station.occupied_slots == 2


# ----------------------------------------------------------------------
# MissionZone
# ----------------------------------------------------------------------


def test_mission_zone_valid_construction() -> None:
    zone = MissionZone(
        id="mz-1",
        name="Search Sector A",
        priority=1,
        cells=[(0, 0), (0, 1), (1, 0)],
        mission_id="mission-1",
    )

    assert zone.cells == frozenset({(0, 0), (0, 1), (1, 0)})


def test_mission_zone_normalizes_cells_to_frozenset() -> None:
    zone = MissionZone(
        id="mz-1",
        name="Zone",
        priority=1,
        cells=[(0, 0), (0, 0), (1, 1)],
        mission_id="mission-1",
    )

    assert isinstance(zone.cells, frozenset)
    assert zone.cells == frozenset({(0, 0), (1, 1)})


def test_mission_zone_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        MissionZone(id="", name="Zone", priority=1, cells=[(0, 0)], mission_id="m-1")


def test_mission_zone_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        MissionZone(id="mz-1", name="", priority=1, cells=[(0, 0)], mission_id="m-1")


def test_mission_zone_rejects_empty_mission_id() -> None:
    with pytest.raises(ValueError):
        MissionZone(id="mz-1", name="Zone", priority=1, cells=[(0, 0)], mission_id="")


def test_mission_zone_rejects_empty_cells() -> None:
    with pytest.raises(ValueError):
        MissionZone(id="mz-1", name="Zone", priority=1, cells=[], mission_id="m-1")


def test_mission_zone_rejects_negative_cell_coordinates() -> None:
    with pytest.raises(ValueError):
        MissionZone(
            id="mz-1", name="Zone", priority=1, cells=[(-1, 0)], mission_id="m-1"
        )