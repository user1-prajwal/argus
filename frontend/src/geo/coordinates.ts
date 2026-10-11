/**
 * Geographic <-> ARGUS World coordinate translation.
 *
 * The ARGUS backend (World, PathPlanner, SimulationEngine) has no
 * concept of geography — it operates entirely on a discrete integer
 * grid, (x, y) with 0 <= x < width, 0 <= y < height. That does not
 * change here and must not change: see docs/world-model.md and this
 * project's standing rule that PathPlanner/SimulationEngine's
 * coordinate model is backend-owned.
 *
 * This module mirrors backend/app/geo/conversion.py's math exactly —
 * same field names (south/west/north/east), same center-anchored
 * reversibility reasoning, same clamping behavior at the boundary.
 * The two must agree: the backend rasterizes real building footprints
 * against this exact mapping, and the frontend converts the backend's
 * World-cell responses back to lat/lng for rendering using the same
 * bounds the backend used to build that World in the first place (see
 * GeoScenarioCreateResponse.bounds / ScenarioStateResponse.geo_bounds
 * — the backend echoes back the bounds it actually used, so the
 * frontend never has to guess or re-derive them).
 *
 * ----------------------------------------------------------------
 * NO FIXED DEMO AREA
 * ----------------------------------------------------------------
 * Earlier versions of this module exported a hardcoded MAP_BOUNDS
 * constant (a fixed San Francisco-area box) for a fixed 12x12 demo
 * grid. That constant is gone. A real ARGUS scenario's bounds are now
 * chosen by the user (see components/OperatingAreaSelector.tsx) and
 * returned by the backend — every function here takes bounds and
 * world dimensions as explicit parameters rather than reading a
 * module-level default, so there is no "fake" area this module could
 * silently fall back to.
 *
 * ----------------------------------------------------------------
 * THE MAPPING
 * ----------------------------------------------------------------
 * Each World cell (x, y) is treated as occupying an equal-sized
 * rectangular sub-region of the given bounds. worldToGeo returns the
 * geographic coordinate at the CENTER of that sub-region (not a
 * corner) — this is what makes the mapping reversible: converting a
 * cell to geo and back with geoToWorld recovers the same cell,
 * because the center of a cell's sub-region always rounds back into
 * that same sub-region. A corner-anchored mapping does not have this
 * property (a corner point is ambiguous between up to four adjacent
 * cells at exact boundaries).
 *
 * World's y axis increases north (see app/world/world.py's neighbor
 * offsets: "'Up' is +y (north)"). Latitude also increases north, so y
 * maps directly to latitude with no flip needed here — unlike the SVG
 * grid (WorldMap.tsx), which had to flip y because SVG's y axis
 * increases downward on screen.
 */

export interface GeoBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface LatLng {
  lat: number;
  lng: number;
}

/**
 * A real, fixed point in central Bengaluru, used ONLY to center the
 * map's initial view before any scenario/operating-area exists yet —
 * never used as a scenario's bounds, never sent to the backend. Once
 * an operating area is selected and a scenario is created, the map
 * re-centers on that scenario's actual bounds instead (echoed back by
 * the backend). MG Road area — chosen only as a recognizable central
 * reference point, the same way earlier phases used an arbitrary real
 * urban area; ARGUS's own logic has no awareness of what this place
 * is.
 */
export const BENGALURU_CENTER: LatLng = { lat: 12.9716, lng: 77.5946 };
export const BENGALURU_DEFAULT_ZOOM = 13;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Convert a World cell to the geographic coordinate at the center of
 * that cell's sub-region within `bounds`.
 *
 * Deterministic and pure — same (x, y, bounds, dimensions) always
 * produces the same LatLng, and the reverse (geoToWorld) of this
 * exact point, with the same bounds and dimensions, always recovers
 * (x, y).
 */
export function worldToGeo(
  x: number,
  y: number,
  bounds: GeoBounds,
  worldWidth: number,
  worldHeight: number,
): LatLng {
  const cellWidth = (bounds.east - bounds.west) / worldWidth;
  const cellHeight = (bounds.north - bounds.south) / worldHeight;

  const lng = bounds.west + (x + 0.5) * cellWidth;
  const lat = bounds.south + (y + 0.5) * cellHeight;

  return { lat, lng };
}

/**
 * Convert a geographic coordinate to the World cell whose sub-region
 * contains it, for the given bounds and world dimensions. Points
 * outside bounds clamp to the nearest edge cell rather than returning
 * an out-of-range or undefined cell — a map click just outside the
 * operating area is still a meaningful "closest cell" intent, not an
 * error, matching the backend's own geo_to_world clamping exactly.
 *
 * This is the inverse of worldToGeo: for any (x, y) in range,
 * geoToWorld(worldToGeo(x, y, ...).lat, worldToGeo(x, y, ...).lng, ...)
 * === {x, y}.
 */
export function geoToWorld(
  lat: number,
  lng: number,
  bounds: GeoBounds,
  worldWidth: number,
  worldHeight: number,
): { x: number; y: number } {
  const cellWidth = (bounds.east - bounds.west) / worldWidth;
  const cellHeight = (bounds.north - bounds.south) / worldHeight;

  const rawX = Math.floor((lng - bounds.west) / cellWidth);
  const rawY = Math.floor((lat - bounds.south) / cellHeight);

  return {
    x: clamp(rawX, 0, worldWidth - 1),
    y: clamp(rawY, 0, worldHeight - 1),
  };
}

/** The two corners of `bounds`, in the order Leaflet's
 * L.latLngBounds / fitBounds expects (southwest, northeast). */
export function boundsToLeafletCorners(
  bounds: GeoBounds,
): [[number, number], [number, number]] {
  return [
    [bounds.south, bounds.west],
    [bounds.north, bounds.east],
  ];
}
