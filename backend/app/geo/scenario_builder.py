"""The geographic scenario-building layer.

Turns a real geographic bounding box into a live ARGUS World populated
with obstacles derived from actual OpenStreetMap building footprints
inside it, plus a small set of agents at deterministic starting
positions. Missions are NOT created here -- per the project's mission
flow, mission targets come from a user's map click and are supplied by
the API caller as ordinary mission payloads, exactly like every other
scenario creation path (see app/api/routes.py's _build_missions).

This module is the one and only place that:
  1. Calls Overpass (via overpass.py) for real building data.
  2. Converts building polygons into World cells (via conversion.py).
  3. Constructs a World and adds those cells as obstacles, using
     World's own existing, unmodified add_obstacle() method.
  4. Places agents at their requested starting cells within the
     generated World, using AgentRegistry's own existing, unmodified
     add_agent() method.

It does NOT implement any planning, routing, or simulation logic --
those remain entirely PlanningEngine's, PathPlanner's, and
SimulationEngine's, unmodified, exactly as every other layer in this
project already respects.

----------------------------------------------------------------
FLEET IS USER-CONFIGURED, NEVER AUTO-GENERATED
----------------------------------------------------------------
build_geo_scenario() creates exactly the agents described in its
`agents` argument -- zero, one, or many -- and creates NO agents when
that argument is empty or omitted. There is no hardcoded fleet size or
fallback default; an earlier version of this module always spawned
four fixed drones at fixed relative positions, which this replaces
entirely (see AgentSpec and the loop in build_geo_scenario below).
Choosing how many agents exist, their ids, capabilities, and starting
positions is the caller's decision -- in practice, the user's, via the
frontend's fleet-configuration UI -- not something this layer invents.

----------------------------------------------------------------
IMPORTANT MODELING DECISION (documented per the project requirement)
----------------------------------------------------------------
For this prototype, every World cell a real building's mapped
footprint intersects is treated as a blocked/restricted cell for
simulated agents -- the same way any other Obstacle already works in
the existing World module. This is a simulation assumption for a
routing demonstration, not a claim that a real building is
necessarily a physical obstacle at every real drone flight altitude,
nor a claim that OSM's building outlines are survey-accurate. A future
version could vary this by agent altitude or platform type; Version 1
does not.

----------------------------------------------------------------
KNOWN LIMITATIONS (Version 1)
----------------------------------------------------------------
- Multipolygon relations: only the first "outer" ring with geometry is
  used (see overpass.py's _extract_ring_from_relation). Inner rings
  (holes/courtyards) and buildings mapped as relations with multiple
  disjoint outer rings are not fully modeled. This does not silently
  drop such buildings -- their first outer ring still becomes
  obstacles -- but it is not a complete multipolygon implementation.
- OSM data is not version-pinned: Overpass returns whatever the
  current OSM database holds at query time, so the SAME bounding box
  queried on two different days could return different (updated)
  building data if the map has been edited between queries. The
  determinism guarantee is scoped to "same OSM data produces the same
  World" -- see overpass.py's module docstring.
- A World cell that a building's footprint only barely clips (per the
  rasterizer's rectangle-polygon intersection test) is marked fully
  blocked, the same coarse-graining any grid-based obstacle
  representation has. This is inherent to modeling a continuous
  footprint on a discrete grid, not a bug in the rasterizer itself.
- Building footprints are the only OSM feature type modeled as
  obstacles in Version 1. Other real-world obstructions (trees, water,
  power lines, no-fly zones) are out of scope, matching the project's
  explicit "IMPORTANT MODELING DECISION" instruction to scope this to
  buildings only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import httpx

from app.agent import Agent, AgentActivity, AgentRegistry, Capability, HealthStatus, PlatformType
from app.world import Obstacle, World

from . import overpass
from .conversion import GeoBounds, obstacle_id_for_cell, rasterize_building

Position = tuple[int, int]

# A hard ceiling on the geographic area a single request may cover, in
# square kilometers (approximate, via a simple degrees-to-km
# conversion). Overpass is a shared public resource -- this guard is
# what makes "a small operating area inside Bengaluru" (the project
# requirement) an enforced constraint, not just a suggestion in a
# docstring.
_MAX_AREA_SQ_KM = 9.0
_KM_PER_DEGREE_LAT = 111.0


def _approximate_area_sq_km(bounds: GeoBounds) -> float:
    """A simple equirectangular approximation of the bounding box's
    area -- sufficient for an operating-area size guard (this is not
    used for anything geometrically precise), using the box's own
    center latitude for the longitude-degree-to-km conversion.
    """
    center_lat_rad = math.radians((bounds.south + bounds.north) / 2)
    km_per_degree_lng = _KM_PER_DEGREE_LAT * abs(math.cos(center_lat_rad))
    height_km = (bounds.north - bounds.south) * _KM_PER_DEGREE_LAT
    width_km = (bounds.east - bounds.west) * km_per_degree_lng
    return height_km * width_km


class OperatingAreaTooLargeError(ValueError):
    """Raised when the requested bounding box exceeds the Version 1
    area guard. Not a backend/World error -- this is a request
    validation concern, translated to 422 at the API layer exactly
    like every other request-validation error in this project (see
    app/api/routes.py's _SCENARIO_VALIDATION_ERRORS pattern).
    """


@dataclass(frozen=True)
class GeneratedGeoScenario:
    """The result of building a scenario from a real geographic area.

    Attributes:
        world: The constructed World, with one Obstacle per generated
            obstacle cell.
        agents: The constructed AgentRegistry, with agents placed at
            their requested (or nearest-walkable-fallback) starting
            cells -- see AgentSpec.
        bounds: The GeoBounds this scenario was generated from --
            returned so the API layer can echo it back to the caller,
            and so the frontend can convert World cells back to
            geographic coordinates using the exact same bounds it
            requested.
        world_width: The World's width, echoed for the same reason.
        world_height: The World's height, echoed for the same reason.
        building_count: Number of building footprints Overpass
            returned for this area (before rasterization) -- reported
            so a caller can distinguish "zero buildings because this
            area genuinely has none mapped" from a silent failure.
        obstacle_cell_count: Number of distinct World cells marked as
            obstacles (after rasterization and de-duplication across
            overlapping buildings).
    """

    world: World
    agents: AgentRegistry
    bounds: GeoBounds
    world_width: int
    world_height: int
    building_count: int
    obstacle_cell_count: int


@dataclass(frozen=True)
class AgentSpec:
    """One user-configured drone/agent to create in the generated
    scenario -- the caller-supplied replacement for the old fixed
    four-drone fleet.

    x/y are already World cell coordinates, not geographic ones -- the
    caller (app/api/routes.py's create_geo_scenario) is responsible
    for any geo-to-World conversion before constructing this, exactly
    like every other agent-creation path in this project (see
    app/api/routes.py's _build_agents for the plain, non-geo
    equivalent). This module has no geographic awareness of its own
    beyond what conversion.py already provides for buildings.

    Attributes:
        id: Unique identifier for this agent within the scenario.
            Uniqueness is enforced by AgentRegistry.add_agent() itself
            (DuplicateAgentError) -- not re-validated here.
        platform_type: The kind of physical platform, reusing the
            existing PlatformType enum unmodified.
        x: East-west World cell coordinate, the agent's requested
            starting position.
        y: North-south World cell coordinate, the agent's requested
            starting position.
        capabilities: The agent's sensing/functional capabilities,
            reusing the existing Capability enum unmodified.
        battery_level: Starting battery, 0-100. Defaults to 100 (a
            freshly registered/connected drone) -- not user-configured
            in this phase, per the task's scope.
    """

    id: str
    platform_type: PlatformType
    x: int
    y: int
    capabilities: frozenset[Capability] = frozenset()
    battery_level: int = 100


def _find_nearest_walkable(
    world: World, preferred: Position, occupied: set[Position]
) -> Position:
    """Return the closest walkable, not-yet-occupied-by-another-agent
    cell to `preferred`, expanding outward ring by ring. Falls back to
    `preferred` itself if the entire World somehow has no walkable
    cell left (should not happen in practice at Version 1 scale, but
    this avoids ever raising out of scenario generation for a
    pathological, extremely obstacle-dense area).

    Uses only World's existing public is_walkable() -- does not read
    or duplicate any private World state.
    """
    px, py = preferred
    if world.is_walkable(px, py) and preferred not in occupied:
        return preferred

    for radius in range(1, max(world.width, world.height) + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                candidate = (px + dx, py + dy)
                cx, cy = candidate
                if 0 <= cx < world.width and 0 <= cy < world.height:
                    if world.is_walkable(cx, cy) and candidate not in occupied:
                        return candidate

    return preferred


def build_geo_scenario(
    bounds: GeoBounds,
    world_width: int,
    world_height: int,
    agent_specs: list[AgentSpec] | None = None,
    overpass_client: httpx.Client | None = None,
) -> GeneratedGeoScenario:
    """Build a complete World + AgentRegistry from a real geographic
    operating area.

    Args:
        bounds: The geographic bounding box to generate the scenario
            from.
        world_width: Width of the World grid to generate.
        world_height: Height of the World grid to generate.
        agent_specs: The agents to create, in the order given -- zero,
            one, or many. Empty (the default) creates NO agents; there
            is no fallback fleet. Each spec's x/y is nudged to the
            nearest walkable cell if its requested position is a
            generated obstacle or already claimed by an earlier spec
            in the same list (see _find_nearest_walkable) -- callers
            cannot see obstacle geometry ahead of time (no API exposes
            it), so a user-clicked position landing inside a building
            is an expected, non-error case, not a validation failure.
        overpass_client: Optional httpx.Client, forwarded to
            overpass.fetch_buildings (primarily for tests that need to
            inject a mock transport rather than make a real network
            call).

    Returns:
        A GeneratedGeoScenario with the constructed World, agents, and
        the metadata needed to convert World cells back to geography.

    Raises:
        OperatingAreaTooLargeError: If bounds exceeds the Version 1
            area guard (_MAX_AREA_SQ_KM) -- this is a request
            validation failure, not a World construction failure.
        TypeError, ValueError: Propagated unmodified from World's own
            constructor/add_obstacle validation, or from
            GeoBounds/Agent's own validation -- this module invents no
            new validation rules beyond the area guard above.
        DuplicateAgentError: Propagated unmodified from
            AgentRegistry.add_agent() if two specs share an id.
        overpass.OverpassError: If the Overpass request fails.
    """
    area = _approximate_area_sq_km(bounds)
    if area > _MAX_AREA_SQ_KM:
        raise OperatingAreaTooLargeError(
            f"Requested operating area is approximately {area:.1f} sq km, "
            f"which exceeds the Version 1 limit of {_MAX_AREA_SQ_KM} sq km. "
            "Choose a smaller operating area."
        )

    resolved_agent_specs = agent_specs if agent_specs is not None else []

    buildings = overpass.fetch_buildings(bounds, client=overpass_client)

    world = World(width=world_width, height=world_height)
    # De-duplicate cells across overlapping/adjacent buildings: two
    # different buildings' footprints can rasterize to the same cell
    # (common at city-block scale where WORLD_WIDTH/HEIGHT is coarse
    # relative to real building density). World.add_obstacle refuses a
    # second obstacle at an already-occupied position, so the first
    # building to claim a cell (in the deterministic, osm_id-sorted
    # order buildings already arrive in) wins; later buildings sharing
    # that cell are not re-added, not silently lost -- their OTHER,
    # non-colliding cells are still added normally.
    claimed_cells: set[Position] = set()
    for building in buildings:
        cells = rasterize_building(building, bounds, world_width, world_height)
        for cell in cells:
            if cell in claimed_cells:
                continue
            claimed_cells.add(cell)
            obstacle_id = obstacle_id_for_cell(building.osm_id, cell)
            world.add_obstacle(Obstacle(id=obstacle_id, x=cell[0], y=cell[1], type="Building"))

    agents = AgentRegistry()
    occupied_start_cells: set[Position] = set()
    for spec in resolved_agent_specs:
        preferred = (
            min(max(spec.x, 0), world_width - 1),
            min(max(spec.y, 0), world_height - 1),
        )
        start = _find_nearest_walkable(world, preferred, occupied_start_cells)
        occupied_start_cells.add(start)
        agents.add_agent(
            Agent(
                id=spec.id,
                platform_type=spec.platform_type,
                x=start[0],
                y=start[1],
                battery_level=spec.battery_level,
                health_status=HealthStatus.ONLINE,
                activity=AgentActivity.IDLE,
                capabilities=spec.capabilities,
            )
        )

    return GeneratedGeoScenario(
        world=world,
        agents=agents,
        bounds=bounds,
        world_width=world_width,
        world_height=world_height,
        building_count=len(buildings),
        obstacle_cell_count=len(claimed_cells),
    )
