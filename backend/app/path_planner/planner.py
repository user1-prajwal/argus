"""The PathPlanner class: computes routes across World state.

PathPlanner is the second ARGUS module to contain algorithmic logic,
after the Planning Engine -- but its logic is pure pathfinding
computation, not a business decision. It reads World state through its
existing public API and computes a route, never mutating World, Agent,
or Mission state, and owning no persistent state of its own -- see
docs/path-planner-model.md and docs/path-planner-api.md for the full
specification this module implements.

Version 1 used four-directional movement with Manhattan distance as
the A* heuristic. This version adds the four diagonal directions and
switches the heuristic to octile distance, so a genuinely shorter
diagonal route is preferred over a longer L-shaped detour when no
obstacle forces the detour.

MOVEMENT COST: orthogonal moves cost 1; diagonal moves cost sqrt(2),
matching a diagonal step's actual geometric distance relative to an
orthogonal step on a unit grid. This cost is used ONLY to rank
candidate routes inside this module's own A* search -- it is NOT the
same number SimulationEngine charges to an agent's battery.
SimulationEngine's battery model is, and remains, a flat cost per
move regardless of direction (see app/simulation/engine.py's
_MOVE_COST) -- a deliberate, pre-existing, per-action convention, not
a distance-based one. Route.length is therefore still a plain count
of moves (len(cells) - 1), exactly as before; it is not the sum of
this module's internal pathfinding costs. Diagonal support changes
which route is chosen, not how much battery following it costs.

Ties between equally-costed routes are broken deterministically by
considering neighboring cells in a fixed order (Up, Down, Left, Right,
then the four diagonals), defined locally by this module rather than
sourced from World.get_neighbors -- this keeps the Path Planner's
determinism guarantee independent of another module's internal
implementation. World.get_neighbors itself remains four-directional
only (see docs/world-model.md) -- this module has never sourced its
neighbor list from World.get_neighbors, so that module needs no
change for diagonal support to exist here.

CORNER-CUTTING: a diagonal move is only offered when BOTH cells
orthogonally adjacent to that diagonal step are also walkable.
Obstacles in this project occupy a single cell each; without this
check, a diagonal step between two obstacle cells that touch only at
a shared corner would let an agent visually clip through that corner
-- still "flying through an obstacle" even though neither the
diagonal's start nor destination cell is itself blocked. This
restriction only ever removes a candidate edge from the search graph;
it cannot make the octile-distance heuristic overestimate the true
remaining cost (which can only increase, never decrease, as edges are
removed), so A* is still guaranteed to find a true shortest-cost
route under this rule.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from app.world import World

# Eight-directional movement offsets: the original four (Up, Down,
# Left, Right), followed by the four diagonals in a fixed order
# (Up-Right, Up-Left, Down-Right, Down-Left). The first four are
# unchanged from Version 1's ordering, preserving that half of the
# existing tie-break behavior for any route that never needs a
# diagonal step; the diagonals are appended, not interleaved, so
# orthogonal candidates are still always considered first at each
# node.
_NEIGHBOR_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (0, -1),
    (-1, 0),
    (1, 0),
    (1, 1),
    (-1, 1),
    (1, -1),
    (-1, -1),
)

# Per-offset movement cost, indexed the same order as
# _NEIGHBOR_OFFSETS: 1.0 for the four orthogonal moves, sqrt(2) for
# the four diagonals -- a diagonal step's actual geometric distance
# relative to an orthogonal step on a unit grid. Used only to rank
# candidate routes inside this module's A* search; see this module's
# docstring, "MOVEMENT COST".
_SQRT2 = math.sqrt(2)
_NEIGHBOR_COSTS: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0, _SQRT2, _SQRT2, _SQRT2, _SQRT2)

Position = tuple[int, int]


@dataclass(frozen=True)
class Route:
    """An immutable, ordered route between two cells.

    Attributes:
        cells: The ordered sequence of (x, y) positions from the start
            cell to the goal cell, inclusive of both. Position in the
            sequence is the order the route is walked in. Consecutive
            cells may now be diagonal neighbors of each other, not
            only orthogonal ones.
        length: The number of moves in the route (len(cells) - 1). A
            route from a cell to itself has length 0. This remains a
            plain move COUNT, not a sum of geometric distances -- an
            orthogonal step and a diagonal step each count as exactly
            one move here, even though they cost differently inside
            this module's own route-selection search. See this
            module's docstring, "MOVEMENT COST", for why: this is what
            keeps SimulationEngine's existing battery/round-trip-check
            arithmetic (which reads only this field) correct and
            unchanged.
    """

    cells: tuple[Position, ...]
    length: int


def _octile_distance(a: Position, b: Position) -> float:
    """The octile distance heuristic used by A* once diagonal movement
    is allowed.

    On an open (obstacle-free) eight-directional unit grid, this is
    not merely a lower bound but the EXACT shortest-path cost between
    a and b: min(dx, dy) diagonal moves (cost sqrt(2) each) plus
    |dx - dy| orthogonal moves (cost 1 each) for the remainder. Since
    obstacles (and the corner-cutting rule) can only increase the true
    cost above this open-grid value, never decrease it, this heuristic
    never overestimates the true remaining cost on any World -- the
    same admissibility guarantee Manhattan distance gave Version 1's
    four-directional search, extended to eight directions.
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    diagonal_steps = min(dx, dy)
    straight_steps = max(dx, dy) - diagonal_steps
    return diagonal_steps * _SQRT2 + straight_steps


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
        """Compute a shortest (lowest-cost) route from (start_x, start_y)
        to (goal_x, goal_y).

        Uses eight-directional movement (orthogonal and diagonal),
        treating obstacles and currently-occupied cells as impassable
        exactly as World.is_walkable reports them. A diagonal move is
        never taken through a blocked corner -- see this module's
        docstring, "CORNER-CUTTING".

        Ties between equally-costed routes are broken deterministically,
        so the same start, goal, and World state always produce the
        same route.

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

    def _neighbors(self, position: Position) -> list[tuple[Position, float]]:
        """Walkable neighbors of position, in the fixed order
        _NEIGHBOR_OFFSETS defines (the four orthogonal directions
        first, then the four diagonals), paired with each neighbor's
        movement cost, using only World.is_walkable.

        A diagonal candidate is included only if its destination cell
        AND both cells orthogonally adjacent to that diagonal step
        (the "corners" the step would otherwise cut across) are all
        walkable -- see find_path's docstring and this module's
        docstring, "CORNER-CUTTING". Orthogonal candidates are
        unaffected; they only ever needed the single destination-cell
        check Version 1 already used.
        """
        x, y = position
        result: list[tuple[Position, float]] = []
        for (dx, dy), cost in zip(_NEIGHBOR_OFFSETS, _NEIGHBOR_COSTS):
            candidate = (x + dx, y + dy)
            if not self._world.is_walkable(*candidate):
                continue
            is_diagonal = dx != 0 and dy != 0
            if is_diagonal:
                corner_a = (x + dx, y)
                corner_b = (x, y + dy)
                if not self._world.is_walkable(*corner_a) or not self._world.is_walkable(
                    *corner_b
                ):
                    continue
            result.append((candidate, cost))
        return result

    def _a_star(self, start: Position, goal: Position) -> Route | None:
        """A* search from start to goal, both already confirmed walkable.

        Ties in total estimated cost are broken by a monotonically
        increasing counter assigned in the same fixed neighbor order
        _neighbors always yields for a given position, so the search
        order -- and therefore the resulting route -- is fully
        deterministic. Floating-point costs (from diagonal moves) do
        not weaken this: identical inputs always produce identical
        floating-point arithmetic on the same platform, so the same
        start, goal, and World state still always produce the same
        route.
        """
        counter = 0
        open_heap: list[tuple[float, int, Position]] = [
            (_octile_distance(start, goal), counter, start)
        ]
        came_from: dict[Position, Position] = {}
        g_score: dict[Position, float] = {start: 0.0}
        closed: set[Position] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal:
                return self._reconstruct_route(came_from, current)
            closed.add(current)

            for neighbor, move_cost in self._neighbors(current):
                tentative_g = g_score[current] + move_cost
                if tentative_g < g_score.get(neighbor, tentative_g + 1):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    counter += 1
                    f_score = tentative_g + _octile_distance(neighbor, goal)
                    heapq.heappush(open_heap, (f_score, counter, neighbor))

        return None

    @staticmethod
    def _reconstruct_route(came_from: dict[Position, Position], goal: Position) -> Route:
        """Walk came_from backward from goal to build the final Route.

        length is the number of MOVES (cells - 1), a plain count --
        not a sum of the float costs used to select this route. See
        this module's docstring, "MOVEMENT COST".
        """
        cells = [goal]
        while cells[-1] in came_from:
            cells.append(came_from[cells[-1]])
        cells.reverse()
        return Route(cells=tuple(cells), length=len(cells) - 1)
