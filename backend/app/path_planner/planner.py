"""The PathPlanner class: computes routes across World state.

PathPlanner is the second ARGUS module to contain algorithmic logic,
after the Planning Engine -- but its logic is pure pathfinding
computation, not a business decision. It reads World state through its
existing public API and computes a route, never mutating World, Agent,
or Mission state, and owning no persistent state of its own -- see
docs/path-planner-model.md and docs/path-planner-api.md for the full
specification this module implements.

Version 1 uses the A* search algorithm with Manhattan distance
(|dx| + |dy|) as the heuristic. Ties between equally short routes are
broken deterministically by considering neighboring cells in a fixed
order (Up, Down, Left, Right), defined locally by this module rather
than sourced from World.get_neighbors -- this keeps the Path Planner's
determinism guarantee independent of another module's internal
implementation.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from app.world import World

# Four-directional movement offsets, in a fixed Up, Down, Left, Right
# order. Defined locally rather than sourced from World.get_neighbors
# so the Path Planner's tie-break guarantee does not depend on another
# module's internal implementation -- see docs/path-planner-api.md,
# "Find Path".
_NEIGHBOR_OFFSETS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (-1, 0), (1, 0))

Position = tuple[int, int]


@dataclass(frozen=True)
class Route:
    """An immutable, ordered route between two cells.

    Attributes:
        cells: The ordered sequence of (x, y) positions from the start
            cell to the goal cell, inclusive of both. Position in the
            sequence is the order the route is walked in.
        length: The number of moves in the route (len(cells) - 1). A
            route from a cell to itself has length 0.
    """

    cells: tuple[Position, ...]
    length: int


def _manhattan_distance(a: Position, b: Position) -> int:
    """The Manhattan distance heuristic used by A*.

    Never overestimates the true cost on a four-directional, unit-cost
    grid, so the route found by find_path is always a shortest route
    by cell count.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Computes routes across a World's grid.

    A PathPlanner is bound to one World at construction. It holds no
    other state -- every call reads the World's current state and
    computes a fresh result.

    The Path Planner does not own application state. Future modules
    such as a Simulation Engine or Planning Engine may invoke it
    through this public API.
    """

    def __init__(self, world: World) -> None:
        """Create a Path Planner bound to a specific World.

        Args:
            world: The World to compute routes against.

        Raises:
            TypeError: If world is not a World instance.
        """
        if not isinstance(world, World):
            raise TypeError(f"world must be a World instance, got {type(world).__name__}")
        self._world = world

    # ------------------------------------------------------------------
    # Public API (docs/path-planner-api.md, "Public API")
    # ------------------------------------------------------------------

    def find_path(self, start_x: int, start_y: int, goal_x: int, goal_y: int) -> Route | None:
        """Compute a shortest route from (start_x, start_y) to (goal_x, goal_y).

        Uses four-directional movement, treating obstacles and
        currently-occupied cells as impassable exactly as
        World.is_walkable reports them. Ties between equally short
        routes are broken deterministically, so the same start, goal,
        and World state always produce the same route.

        A start equal to the goal returns a route containing just that
        one cell, with length 0 -- unless that cell is not walkable, in
        which case this returns None like any other unwalkable start or
        goal.

        Args:
            start_x: East-west coordinate of the start cell.
            start_y: North-south coordinate of the start cell.
            goal_x: East-west coordinate of the goal cell.
            goal_y: North-south coordinate of the goal cell.

        Returns:
            A Route, or None if no route exists -- including when the
            start or goal cell itself is not walkable. This is not an
            error.

        Raises:
            TypeError: If a coordinate is not an int.
            ValueError: If start or goal is outside the World's bounds.
        """
        self._validate_coordinates(start_x, start_y)
        self._validate_coordinates(goal_x, goal_y)

        start: Position = (start_x, start_y)
        goal: Position = (goal_x, goal_y)

        if not self._world.is_walkable(*start) or not self._world.is_walkable(*goal):
            return None

        if start == goal:
            return Route(cells=(start,), length=0)

        return self._a_star(start, goal)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_coordinates(self, x: int, y: int) -> None:
        """Raising validity check: x, y must be ints within world bounds."""
        if not isinstance(x, int) or isinstance(x, bool):
            raise TypeError(f"x must be an int, got {type(x).__name__}")
        if not isinstance(y, int) or isinstance(y, bool):
            raise TypeError(f"y must be an int, got {type(y).__name__}")
        if not (0 <= x < self._world.width and 0 <= y < self._world.height):
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside the world bounds "
                f"({self._world.width}x{self._world.height})"
            )

    def _neighbors(self, position: Position) -> list[Position]:
        """Walkable neighbors of position, in a fixed Up, Down, Left,
        Right order, using only World.is_walkable.
        """
        x, y = position
        candidates = ((x + dx, y + dy) for dx, dy in _NEIGHBOR_OFFSETS)
        return [candidate for candidate in candidates if self._world.is_walkable(*candidate)]

    def _a_star(self, start: Position, goal: Position) -> Route | None:
        """A* search from start to goal, both already confirmed walkable.

        Ties in total estimated cost are broken by a monotonically
        increasing counter assigned in the same fixed Up, Down, Left,
        Right order _neighbors always yields for a given position, so
        the search order -- and therefore the resulting route -- is
        fully deterministic.
        """
        counter = 0
        open_heap: list[tuple[int, int, Position]] = [
            (_manhattan_distance(start, goal), counter, start)
        ]
        came_from: dict[Position, Position] = {}
        g_score: dict[Position, int] = {start: 0}
        closed: set[Position] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal:
                return self._reconstruct_route(came_from, current)
            closed.add(current)

            for neighbor in self._neighbors(current):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, tentative_g + 1):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    counter += 1
                    f_score = tentative_g + _manhattan_distance(neighbor, goal)
                    heapq.heappush(open_heap, (f_score, counter, neighbor))

        return None

    @staticmethod
    def _reconstruct_route(came_from: dict[Position, Position], goal: Position) -> Route:
        """Walk came_from backward from goal to build the final Route."""
        cells = [goal]
        while cells[-1] in came_from:
            cells.append(came_from[cells[-1]])
        cells.reverse()
        return Route(cells=tuple(cells), length=len(cells) - 1)