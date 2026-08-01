"""Tests for World.add_charging_station."""

from __future__ import annotations

import pytest

from app.world import (
    CellType,
    ChargingStation,
    DuplicateChargingStationError,
    Obstacle,
    World,
)


def test_add_charging_station_valid(world: World) -> None:
    world.add_charging_station(ChargingStation(id="cs-1", x=6, y=6, capacity=2))

    assert world.get_cell(6, 6).cell_type is CellType.CHARGING_STATION
    assert world.world_summary()["charging_stations"] == 1


def test_add_charging_station_rejects_wrong_type(world: World) -> None:
    with pytest.raises(TypeError):
        world.add_charging_station({"id": "cs-1"})  # type: ignore[arg-type]


def test_add_charging_station_rejects_out_of_bounds(world: World) -> None:
    with pytest.raises(ValueError):
        world.add_charging_station(ChargingStation(id="cs-1", x=-1, y=0, capacity=1))


def test_add_charging_station_rejects_duplicate_id(world: World) -> None:
    world.add_charging_station(ChargingStation(id="cs-1", x=1, y=1, capacity=1))

    with pytest.raises(DuplicateChargingStationError):
        world.add_charging_station(ChargingStation(id="cs-1", x=2, y=2, capacity=1))


def test_add_charging_station_rejects_position_inside_obstacle(world: World) -> None:
    world.add_obstacle(Obstacle(id="obs-1", x=7, y=7, type="Mountain"))

    with pytest.raises(ValueError):
        world.add_charging_station(ChargingStation(id="cs-1", x=7, y=7, capacity=1))