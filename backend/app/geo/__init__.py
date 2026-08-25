"""The ARGUS geographic scenario layer.

Converts a real geographic bounding box (via OpenStreetMap building
data, fetched through Overpass) into a live World populated with
obstacles matching real building footprints, plus a small set of
agents at deterministic starting positions.

This is an additive layer: it depends on World, Agent, and their
existing public constructors/methods, and does not modify any of
them. See scenario_builder.py's module docstring for the full design,
the important modeling decision this feature rests on, and known
Version 1 limitations.
"""

from __future__ import annotations

from .conversion import BuildingPolygon, GeoBounds, geo_to_world, world_to_geo
from .overpass import OverpassError, fetch_buildings
from .scenario_builder import (
    GeneratedGeoScenario,
    OperatingAreaTooLargeError,
    build_geo_scenario,
)

__all__ = [
    "GeoBounds",
    "BuildingPolygon",
    "geo_to_world",
    "world_to_geo",
    "fetch_buildings",
    "OverpassError",
    "build_geo_scenario",
    "GeneratedGeoScenario",
    "OperatingAreaTooLargeError",
]
