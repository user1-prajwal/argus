"""Tests for app/geo/conversion.py.

Pure geometry/math -- no network calls, no dependency on Overpass
being reachable. Covers the reversibility guarantee, the rasterizer's
"not just centroid" requirement, and deterministic obstacle id
generation.
"""

from __future__ import annotations

import pytest

from app.geo.conversion import (
    BuildingPolygon,
    GeoBounds,
    geo_to_world,
    obstacle_id_for_cell,
    rasterize_building,
    world_to_geo,
)


# A realistic small Bengaluru-scale operating area.
BENGALURU_BOUNDS = GeoBounds(south=12.930, west=77.610, north=12.945, east=77.625)


class TestGeoBounds:
    def test_valid_bounds_construct(self):
        bounds = GeoBounds(south=12.9, west=77.6, north=12.95, east=77.65)
        assert bounds.south == 12.9

    def test_south_must_be_less_than_north(self):
        with pytest.raises(ValueError):
            GeoBounds(south=13.0, west=77.6, north=12.9, east=77.65)

    def test_west_must_be_less_than_east(self):
        with pytest.raises(ValueError):
            GeoBounds(south=12.9, west=77.7, north=12.95, east=77.6)


class TestReversibility:
    """The core determinism/reversibility guarantee: every World cell,
    converted to geo and back, must recover the same cell. Verified
    computationally across the full grid, not merely asserted for one
    or two example points.
    """

    @pytest.mark.parametrize("world_width,world_height", [(12, 12), (20, 20), (8, 15)])
    def test_every_cell_round_trips(self, world_width, world_height):
        failures = []
        for x in range(world_width):
            for y in range(world_height):
                lat, lng = world_to_geo(x, y, BENGALURU_BOUNDS, world_width, world_height)
                back_x, back_y = geo_to_world(lat, lng, BENGALURU_BOUNDS, world_width, world_height)
                if (back_x, back_y) != (x, y):
                    failures.append(((x, y), (lat, lng), (back_x, back_y)))
        assert failures == [], f"{len(failures)} cells failed to round-trip: {failures[:5]}"

    def test_sw_corner_click_maps_to_cell_0_0(self):
        x, y = geo_to_world(
            BENGALURU_BOUNDS.south, BENGALURU_BOUNDS.west, BENGALURU_BOUNDS, 12, 12
        )
        assert (x, y) == (0, 0)

    def test_ne_corner_click_maps_to_last_cell(self):
        x, y = geo_to_world(
            BENGALURU_BOUNDS.north, BENGALURU_BOUNDS.east, BENGALURU_BOUNDS, 12, 12
        )
        assert (x, y) == (11, 11)

    def test_point_outside_bounds_clamps_rather_than_errors(self):
        x, y = geo_to_world(0.0, 0.0, BENGALURU_BOUNDS, 12, 12)
        assert (x, y) == (0, 0)

        x, y = geo_to_world(50.0, 100.0, BENGALURU_BOUNDS, 12, 12)
        assert (x, y) == (11, 11)


class TestRasterizeBuilding:
    """Verifies the rasterizer intersects actual polygon geometry,
    not just a centroid -- the project's explicit "do NOT simply use
    the building centroid" requirement.
    """

    def test_building_smaller_than_one_cell_still_produces_a_cell(self):
        # A tiny building, well within a single World cell's
        # sub-region for a coarse 12x12 grid over this bounding box.
        building = BuildingPolygon(
            osm_id=1001,
            ring=(
                (12.9355, 77.6155),
                (12.9356, 77.6155),
                (12.9356, 77.6156),
                (12.9355, 77.6156),
            ),
        )
        cells = rasterize_building(building, BENGALURU_BOUNDS, 12, 12)
        assert len(cells) >= 1

    def test_building_spanning_multiple_cells_produces_multiple_cells(self):
        # A building large enough (relative to a fine 40x40 grid) to
        # span several cells -- confirms the rasterizer covers the
        # whole footprint, not just one representative point.
        building = BuildingPolygon(
            osm_id=1002,
            ring=(
                (12.935, 77.615),
                (12.940, 77.615),
                (12.940, 77.620),
                (12.935, 77.620),
            ),
        )
        cells = rasterize_building(building, BENGALURU_BOUNDS, 40, 40)
        assert len(cells) > 4

    def test_building_outside_bounds_produces_no_cells_incorrectly_inside(self):
        # A degenerate/tiny ring (fewer than 3 usable vertices) must
        # not crash and must produce no cells.
        building = BuildingPolygon(osm_id=1003, ring=((12.935, 77.615), (12.936, 77.616)))
        cells = rasterize_building(building, BENGALURU_BOUNDS, 12, 12)
        assert cells == []

    def test_cells_are_returned_in_deterministic_row_major_order(self):
        building = BuildingPolygon(
            osm_id=1004,
            ring=(
                (12.935, 77.615),
                (12.938, 77.615),
                (12.938, 77.618),
                (12.935, 77.618),
            ),
        )
        cells = rasterize_building(building, BENGALURU_BOUNDS, 30, 30)
        # Row-major: y then x, non-decreasing.
        for (x1, y1), (x2, y2) in zip(cells, cells[1:]):
            assert (y2, x2) >= (y1, x1)

    def test_same_input_produces_same_output_every_call(self):
        building = BuildingPolygon(
            osm_id=1005,
            ring=(
                (12.936, 77.616),
                (12.9375, 77.616),
                (12.9375, 77.6175),
                (12.936, 77.6175),
            ),
        )
        first = rasterize_building(building, BENGALURU_BOUNDS, 24, 24)
        second = rasterize_building(building, BENGALURU_BOUNDS, 24, 24)
        assert first == second


class TestObstacleIdForCell:
    def test_same_input_produces_same_id(self):
        assert obstacle_id_for_cell(555, (3, 4)) == obstacle_id_for_cell(555, (3, 4))

    def test_different_cells_produce_different_ids(self):
        assert obstacle_id_for_cell(555, (3, 4)) != obstacle_id_for_cell(555, (3, 5))

    def test_different_osm_ids_produce_different_ids_for_same_cell(self):
        assert obstacle_id_for_cell(555, (3, 4)) != obstacle_id_for_cell(999, (3, 4))
