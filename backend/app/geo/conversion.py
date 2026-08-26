"""Deterministic geographic <-> ARGUS World coordinate conversion, and
building-polygon-to-World-cell rasterization.

This module owns the ONE mapping between a real geographic bounding
box and the discrete World grid. The frontend's src/geo/coordinates.ts
implements the same linear-interpolation math independently (it has
to: the frontend converts backend World responses back to lat/lng for
rendering, without a round-trip API call per marker) -- the two must
agree, so both are documented here and there with the same reasoning,
and the same worked example.

This module does NOT depend on World, Agent, Mission, or any other
ARGUS backend module -- it is pure coordinate/geometry math, with no
side effects and no I/O. app/geo/scenario_builder.py is the layer that
takes this module's output and calls World's own existing public
constructor/add_obstacle methods.

DETERMINISM: every function here is a pure function of its inputs.
Given the same bounding box, world dimensions, and building polygons
(themselves already deterministic once Overpass has responded -- see
overpass.py's own ordering guarantee), the same set of obstacle cells
is produced every time, in the same order.
"""

from __future__ import annotations

from dataclasses import dataclass

Position = tuple[int, int]


@dataclass(frozen=True)
class GeoBounds:
    """A rectangular geographic bounding box.

    Attributes:
        south: Southern (minimum) latitude.
        west: Western (minimum) longitude.
        north: Northern (maximum) latitude.
        east: Eastern (maximum) longitude.
    """

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        if self.west >= self.east:
            raise ValueError("west must be less than east")


@dataclass(frozen=True)
class BuildingPolygon:
    """A single building footprint, as returned by Overpass and parsed
    by overpass.py.

    Attributes:
        osm_id: The OSM way (or relation) id this polygon came from --
            used to build deterministic, stable obstacle ids. Not
            re-derived or guessed; comes directly from the OSM element.
        ring: The polygon's outer ring as an ordered list of (lat, lng)
            vertices. Closed or not (first == last vertex or not) does
            not matter to the rasterizer below, which treats the ring
            as closed regardless.
    """

    osm_id: int
    ring: tuple[tuple[float, float], ...]


def world_cell_size(bounds: GeoBounds, world_width: int, world_height: int) -> tuple[float, float]:
    """Return (cell_width_deg_lng, cell_height_deg_lat) for this
    bounds/world-size combination -- the size, in degrees, of one
    World cell's geographic sub-rectangle.
    """
    cell_width = (bounds.east - bounds.west) / world_width
    cell_height = (bounds.north - bounds.south) / world_height
    return cell_width, cell_height


def geo_to_world(
    lat: float, lng: float, bounds: GeoBounds, world_width: int, world_height: int
) -> Position:
    """Convert a geographic coordinate to the World cell whose
    sub-region contains it.

    Points outside bounds clamp to the nearest edge cell rather than
    raising or returning an out-of-range cell -- mirrors the
    frontend's geoToWorld exactly (src/geo/coordinates.ts) so a
    building that pokes slightly outside the chosen operating area
    still contributes a boundary obstacle instead of being silently
    dropped.
    """
    cell_width, cell_height = world_cell_size(bounds, world_width, world_height)

    raw_x = int((lng - bounds.west) // cell_width) if cell_width else 0
    raw_y = int((lat - bounds.south) // cell_height) if cell_height else 0

    x = min(max(raw_x, 0), world_width - 1)
    y = min(max(raw_y, 0), world_height - 1)
    return x, y


def world_to_geo(
    x: int, y: int, bounds: GeoBounds, world_width: int, world_height: int
) -> tuple[float, float]:
    """Convert a World cell to the geographic coordinate at the CENTER
    of that cell's sub-region. Center-anchoring (not a corner) is what
    makes this the inverse of geo_to_world for every in-range cell --
    same reasoning as the frontend's worldToGeo.

    Returns (lat, lng).
    """
    cell_width, cell_height = world_cell_size(bounds, world_width, world_height)
    lng = bounds.west + (x + 0.5) * cell_width
    lat = bounds.south + (y + 0.5) * cell_height
    return lat, lng


def _cell_bounds(
    cell_x: int, cell_y: int, bounds: GeoBounds, world_width: int, world_height: int
) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) geographic bounds of one
    World cell's sub-rectangle."""
    cell_width, cell_height = world_cell_size(bounds, world_width, world_height)
    west = bounds.west + cell_x * cell_width
    east = west + cell_width
    south = bounds.south + cell_y * cell_height
    north = south + cell_height
    return south, west, north, east


def _point_in_ring(lat: float, lng: float, ring: tuple[tuple[float, float], ...]) -> bool:
    """Standard ray-casting point-in-polygon test. ring is a sequence
    of (lat, lng) vertices, treated as closed regardless of whether
    the first and last vertices repeat.
    """
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        lat_i, lng_i = ring[i]
        lat_j, lng_j = ring[j]
        intersects = ((lat_i > lat) != (lat_j > lat)) and (
            lng < (lng_j - lng_i) * (lat - lat_i) / (lat_j - lat_i + 1e-15) + lng_i
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """True if line segment p1-p2 intersects segment p3-p4 (standard
    orientation-based segment intersection test, general position;
    collinear/touching edge cases resolve to False, which only affects
    cells exactly grazing a building edge -- acceptable for a
    rasterization test whose job is "does this cell overlap the
    building," not exact computational geometry).
    """

    def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> int:
        val = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if val > 0:
            return 1
        if val < 0:
            return 2
        return 0

    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)
    return o1 != o2 and o3 != o4


def _cell_intersects_ring(
    cell_south: float,
    cell_west: float,
    cell_north: float,
    cell_east: float,
    ring: tuple[tuple[float, float], ...],
) -> bool:
    """True if the axis-aligned cell rectangle overlaps the polygon
    ring in any way: the cell center is inside the ring, any ring
    vertex falls inside the cell, or any ring edge crosses any cell
    edge. This is a conservative "do these overlap at all" test
    (rectangle-polygon intersection), not a centroid check -- a
    building smaller than one World cell, or a cell that only clips a
    building's corner, both correctly register as intersecting.
    """
    cell_center_lat = (cell_south + cell_north) / 2
    cell_center_lng = (cell_west + cell_east) / 2
    if _point_in_ring(cell_center_lat, cell_center_lng, ring):
        return True

    for lat, lng in ring:
        if cell_south <= lat <= cell_north and cell_west <= lng <= cell_east:
            return True

    cell_corners = [
        (cell_south, cell_west),
        (cell_south, cell_east),
        (cell_north, cell_east),
        (cell_north, cell_west),
    ]
    n = len(ring)
    for i in range(n):
        edge_a = ring[i]
        edge_b = ring[(i + 1) % n]
        for j in range(4):
            corner_a = cell_corners[j]
            corner_b = cell_corners[(j + 1) % 4]
            if _segments_intersect(edge_a, edge_b, corner_a, corner_b):
                return True

    return False


def rasterize_building(
    building: BuildingPolygon, bounds: GeoBounds, world_width: int, world_height: int
) -> list[Position]:
    """Return every World cell this building's footprint intersects,
    sorted in a fixed, deterministic order (row-major: y then x) so
    obstacle id generation never depends on set/dict iteration order.

    Restricts the search to the building's own geographic bounding box
    (clamped to the World's cell range) rather than scanning the whole
    grid, since a building's footprint is normally a small fraction of
    the operating area.
    """
    if len(building.ring) < 3:
        return []

    lats = [pt[0] for pt in building.ring]
    lngs = [pt[1] for pt in building.ring]

    min_x, min_y = geo_to_world(min(lats), min(lngs), bounds, world_width, world_height)
    max_x, max_y = geo_to_world(max(lats), max(lngs), bounds, world_width, world_height)
    # geo_to_world takes (lat, lng) -- min(lats) with min(lngs) is not
    # necessarily the true SW corner in cell terms once clamped, so
    # widen defensively to the full min/max of both computed corners.
    min_x, max_x = min(min_x, max_x), max(min_x, max_x)
    min_y, max_y = min(min_y, max_y), max(min_y, max_y)

    cells: list[Position] = []
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            cell_south, cell_west, cell_north, cell_east = _cell_bounds(
                x, y, bounds, world_width, world_height
            )
            if _cell_intersects_ring(cell_south, cell_west, cell_north, cell_east, building.ring):
                cells.append((x, y))
    return cells


def obstacle_id_for_cell(osm_id: int, cell: Position) -> str:
    """A deterministic, stable obstacle id for one (building, cell)
    pair. Same osm_id + same cell always produces the same id, run to
    run -- required for the "same input produces the same World"
    determinism guarantee, and for two different buildings that
    happen to intersect the same cell to still get distinct ids (see
    scenario_builder.py's de-duplication, which needs distinct ids to
    detect and skip the collision).
    """
    x, y = cell
    return f"osm-{osm_id}-{x}-{y}"
