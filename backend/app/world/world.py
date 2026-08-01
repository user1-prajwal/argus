"""The World class: the single source of truth for the ARGUS simulation
environment.

The World stores grid state, obstacles, mission zones, charging stations,
and spawn points. It performs no planning, mission, or path-finding logic
-- see docs/world-model.md and docs/world-api.md for the full
specification this module implements.
"""

from __future__ import annotations

from .cell import Cell
from .entities import ChargingStation, MissionZone, Obstacle, SpawnPoint
from .enums import CellType
from .exceptions import (
    DuplicateChargingStationError,
    DuplicateMissionZoneError,
    DuplicateObstacleError,
    DuplicateSpawnPointError,
    ObstacleNotFoundError,
)

Position = tuple[int, int]

# Four-directional movement offsets, in the order specified by
# docs/world-model.md: Up, Down, Left, Right. "Up" is +y (north), per
# the documented coordinate system where increasing Y moves north.
_NEIGHBOR_OFFSETS: tuple[Position, ...] = ((0, 1), (0, -1), (-1, 0), (1, 0))


class World:
    """The simulation world: a fixed-size 2D grid of obstacles, mission
    zones, charging stations, and spawn points.

    Only the methods documented in docs/world-api.md are public. Every
    other attribute and method is an internal implementation detail --
    including a private occupancy mechanism reserved for a future Agent
    module, which is intentionally excluded from this class's public
    surface so that module can be added later without changing this API.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create a new, empty world.

        Args:
            width: Number of cells along the X axis. Must be a positive
                integer.
            height: Number of cells along the Y axis. Must be a positive
                integer.

        Raises:
            TypeError: If width or height is not an int.
            ValueError: If width or height is not positive.
        """
        if not isinstance(width, int) or isinstance(width, bool):
            raise TypeError(f"width must be an int, got {type(width).__name__}")
        if not isinstance(height, int) or isinstance(height, bool):
            raise TypeError(f"height must be an int, got {type(height).__name__}")
        if width <= 0:
            raise ValueError("width must be a positive integer")
        if height <= 0:
            raise ValueError("height must be a positive integer")

        self._width = width
        self._height = height

        self._obstacles: dict[str, Obstacle] = {}
        self._obstacle_positions: dict[Position, str] = {}

        self._spawn_points: dict[str, SpawnPoint] = {}
        self._spawn_point_positions: dict[Position, str] = {}

        self._charging_stations: dict[str, ChargingStation] = {}
        self._charging_station_positions: dict[Position, str] = {}

        self._mission_zones: dict[str, MissionZone] = {}
        self._mission_zone_cells: dict[Position, set[str]] = {}

        # Internal occupancy tracking, reserved for a future Agent module.
        # Deliberately has no public getter/setter in this module.
        self._occupied_cells: set[Position] = set()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """int: Number of cells along the X axis."""
        return self._width

    @property
    def height(self) -> int:
        """int: Number of cells along the Y axis."""
        return self._height

    # ------------------------------------------------------------------
    # Public API (docs/world-api.md, "Public API")
    # ------------------------------------------------------------------

    def get_cell(self, x: int, y: int) -> Cell:
        """Return the Cell at (x, y).

        Args:
            x: East-west coordinate.
            y: North-south coordinate.

        Returns:
            The Cell describing that position.

        Raises:
            TypeError: If x or y is not an int.
            ValueError: If (x, y) is outside the world.
        """
        self._validate_coordinates(x, y)
        return Cell(x=x, y=y, cell_type=self._cell_type_at(x, y))

    def is_walkable(self, x: int, y: int) -> bool:
        """Check whether an agent could stand at (x, y).

        Per docs/world-api.md this method always returns a bool and never
        raises: any invalid input (wrong type or out of bounds) is simply
        treated as not walkable.

        Args:
            x: East-west coordinate.
            y: North-south coordinate.

        Returns:
            False if the position is outside the world, is not made of
            integer coordinates, is an obstacle, or is currently marked
            occupied. True otherwise.
        """
        if not self._is_valid_position(x, y):
            return False
        if (x, y) in self._obstacle_positions:
            return False
        if (x, y) in self._occupied_cells:
            return False
        return True

    def get_neighbors(self, x: int, y: int) -> list[Cell]:
        """Return the walkable cells adjacent to (x, y).

        Only four-directional movement is supported (Up, Down, Left,
        Right); diagonal neighbors are never returned. Like
        ``is_walkable``, this method never raises: an invalid source
        position simply yields no neighbors.

        Args:
            x: East-west coordinate of the reference cell.
            y: North-south coordinate of the reference cell.

        Returns:
            The walkable neighboring cells, in Up, Down, Left, Right
            order. Neighbors that fall outside the world or are not
            walkable are omitted. Returns an empty list if (x, y) itself
            is not a valid in-bounds position.
        """
        if not self._is_valid_position(x, y):
            return []
        neighbors: list[Cell] = []
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append(self.get_cell(nx, ny))
        return neighbors

    def add_obstacle(self, obstacle: Obstacle) -> None:
        """Register a new obstacle in the world.

        Args:
            obstacle: The obstacle to add.

        Raises:
            TypeError: If obstacle is not an Obstacle instance.
            ValueError: If the obstacle's position is outside the world,
                or another obstacle already occupies that position.
            DuplicateObstacleError: If an obstacle with this id already
                exists.
        """
        if not isinstance(obstacle, Obstacle):
            raise TypeError("obstacle must be an Obstacle instance")
        self._validate_coordinates(obstacle.x, obstacle.y)
        if obstacle.id in self._obstacles:
            raise DuplicateObstacleError(f"Obstacle id '{obstacle.id}' already exists")

        position = (obstacle.x, obstacle.y)
        if position in self._obstacle_positions:
            raise ValueError(f"Position {position} already contains an obstacle")

        self._obstacles[obstacle.id] = obstacle
        self._obstacle_positions[position] = obstacle.id

    def remove_obstacle(self, obstacle_id: str) -> None:
        """Remove an obstacle by id.

        Args:
            obstacle_id: Id of the obstacle to remove.

        Raises:
            TypeError: If obstacle_id is not a string.
            ObstacleNotFoundError: If no obstacle with this id exists.
        """
        if not isinstance(obstacle_id, str):
            raise TypeError("obstacle_id must be a string")
        if obstacle_id not in self._obstacles:
            raise ObstacleNotFoundError(f"Obstacle id '{obstacle_id}' does not exist")

        obstacle = self._obstacles.pop(obstacle_id)
        del self._obstacle_positions[(obstacle.x, obstacle.y)]

    def add_spawn_point(self, spawn: SpawnPoint) -> None:
        """Register a new spawn point in the world.

        Args:
            spawn: The spawn point to add.

        Raises:
            TypeError: If spawn is not a SpawnPoint instance.
            ValueError: If the spawn point's position is outside the
                world or falls inside an existing obstacle.
            DuplicateSpawnPointError: If a spawn point with this id
                already exists.
        """
        if not isinstance(spawn, SpawnPoint):
            raise TypeError("spawn must be a SpawnPoint instance")
        self._validate_coordinates(spawn.x, spawn.y)
        if spawn.id in self._spawn_points:
            raise DuplicateSpawnPointError(f"SpawnPoint id '{spawn.id}' already exists")

        position = (spawn.x, spawn.y)
        if position in self._obstacle_positions:
            raise ValueError(f"Spawn point cannot be placed inside obstacle at {position}")

        self._spawn_points[spawn.id] = spawn
        self._spawn_point_positions[position] = spawn.id

    def add_charging_station(self, station: ChargingStation) -> None:
        """Register a new charging station in the world.

        Args:
            station: The charging station to add.

        Raises:
            TypeError: If station is not a ChargingStation instance.
            ValueError: If the station's position is outside the world or
                falls inside an existing obstacle.
            DuplicateChargingStationError: If a charging station with
                this id already exists.
        """
        if not isinstance(station, ChargingStation):
            raise TypeError("station must be a ChargingStation instance")
        self._validate_coordinates(station.x, station.y)
        if station.id in self._charging_stations:
            raise DuplicateChargingStationError(
                f"ChargingStation id '{station.id}' already exists"
            )

        position = (station.x, station.y)
        if position in self._obstacle_positions:
            raise ValueError(
                f"Charging station cannot be placed inside obstacle at {position}"
            )

        self._charging_stations[station.id] = station
        self._charging_station_positions[position] = station.id

    def add_mission_zone(self, zone: MissionZone) -> None:
        """Register a new mission zone in the world.

        Args:
            zone: The mission zone to add.

        Raises:
            TypeError: If zone is not a MissionZone instance.
            ValueError: If any of the zone's cells is outside the world,
                or the zone overlaps an existing obstacle.
            DuplicateMissionZoneError: If a mission zone with this id
                already exists.
        """
        if not isinstance(zone, MissionZone):
            raise TypeError("zone must be a MissionZone instance")
        for x, y in zone.cells:
            self._validate_coordinates(x, y)
        if zone.id in self._mission_zones:
            raise DuplicateMissionZoneError(f"MissionZone id '{zone.id}' already exists")

        overlapping = zone.cells & self._obstacle_positions.keys()
        if overlapping:
            raise ValueError(f"Mission zone overlaps obstacle(s) at {sorted(overlapping)}")

        self._mission_zones[zone.id] = zone
        for cell in zone.cells:
            self._mission_zone_cells.setdefault(cell, set()).add(zone.id)

    def world_summary(self) -> dict[str, int]:
        """Return summary counts describing the current world state.

        Returns:
            A dict with keys "width", "height", "obstacles",
            "spawn_points", "charging_stations", and "mission_zones".
        """
        return {
            "width": self._width,
            "height": self._height,
            "obstacles": len(self._obstacles),
            "spawn_points": len(self._spawn_points),
            "charging_stations": len(self._charging_stations),
            "mission_zones": len(self._mission_zones),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, x: int, y: int) -> bool:
        """Range check only. Assumes x, y are already known to be ints."""
        return 0 <= x < self._width and 0 <= y < self._height

    def _is_valid_position(self, x: object, y: object) -> bool:
        """Non-raising validity check used by is_walkable/get_neighbors."""
        if not isinstance(x, int) or isinstance(x, bool):
            return False
        if not isinstance(y, int) or isinstance(y, bool):
            return False
        return self._in_bounds(x, y)

    def _validate_coordinates(self, x: int, y: int) -> None:
        """Raising validity check used by get_cell/add_*/remove_obstacle."""
        if not isinstance(x, int) or isinstance(x, bool):
            raise TypeError(f"x must be an int, got {type(x).__name__}")
        if not isinstance(y, int) or isinstance(y, bool):
            raise TypeError(f"y must be an int, got {type(y).__name__}")
        if not self._in_bounds(x, y):
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside the world bounds "
                f"({self._width}x{self._height})"
            )

    def _cell_type_at(self, x: int, y: int) -> CellType:
        """Resolve a position's CellType by precedence.

        A position can only ever be an Obstacle if it is one (obstacles
        are validated as mutually exclusive with every other entity type
        at add-time). Spawn points, charging stations, and mission zones
        are not mutually exclusive with each other in the specification,
        so ties are broken by this fixed precedence order:
        Obstacle > SpawnPoint > ChargingStation > MissionZone > Empty.
        """
        position = (x, y)
        if position in self._obstacle_positions:
            return CellType.OBSTACLE
        if position in self._spawn_point_positions:
            return CellType.SPAWN_POINT
        if position in self._charging_station_positions:
            return CellType.CHARGING_STATION
        if position in self._mission_zone_cells:
            return CellType.MISSION_ZONE
        return CellType.EMPTY

    # ------------------------------------------------------------------
    # Internal occupancy hooks -- reserved for a future Agent module.
    # Intentionally NOT part of the public API defined in
    # docs/world-api.md. The Agent module will call these directly once
    # it exists; today they exist only so is_walkable's documented
    # "occupied" condition is real, testable behavior rather than dead
    # code.
    # ------------------------------------------------------------------

    def _occupy_cell(self, x: int, y: int) -> None:
        """Mark (x, y) as occupied.

        Raises:
            TypeError: If x or y is not an int.
            ValueError: If (x, y) is outside the world, is an obstacle,
                or is already occupied.
        """
        self._validate_coordinates(x, y)
        if (x, y) in self._obstacle_positions:
            raise ValueError(f"Cannot occupy obstacle cell at ({x}, {y})")
        if (x, y) in self._occupied_cells:
            raise ValueError(f"Cell ({x}, {y}) is already occupied")
        self._occupied_cells.add((x, y))

    def _release_cell(self, x: int, y: int) -> None:
        """Clear the occupied flag at (x, y).

        Releasing a cell that is not currently occupied is a no-op, not
        an error.

        Raises:
            TypeError: If x or y is not an int.
            ValueError: If (x, y) is outside the world.
        """
        self._validate_coordinates(x, y)
        self._occupied_cells.discard((x, y))

    def _is_occupied(self, x: int, y: int) -> bool:
        """Return whether (x, y) is currently marked occupied."""
        return (x, y) in self._occupied_cells