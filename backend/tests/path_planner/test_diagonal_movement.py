"""Tests for diagonal movement in app/path_planner/planner.py.

Covers what changed in this phase: eight-directional movement, octile
distance as the route-selection heuristic, corner-cutting prevention,
and the preserved guarantee that Route.length is a plain move count
(not a sum of geometric costs) so SimulationEngine's existing
battery/round-trip check keeps working unmodified.
"""

from __future__ import annotations

import math

from app.path_planner import PathPlanner
from app.world import Obstacle, World


class TestDiagonalMovement:
    def test_diagonal_route_is_shorter_than_orthogonal_l_shape(self):
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 3, 3)

        assert route is not None
        # A pure four-directional L-shaped route from (0,0) to (3,3)
        # needs 6 moves (3 horizontal + 3 vertical). A route that can
        # use diagonals needs only 3.
        assert route.length == 3
        assert route.cells == ((0, 0), (1, 1), (2, 2), (3, 3))

    def test_mixed_diagonal_and_orthogonal_route(self):
        # A target that is not on a perfect diagonal should still use
        # diagonal moves for the shared portion and orthogonal moves
        # for the remainder, rather than a pure L-shape.
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 5, 2)

        assert route is not None
        # Optimal: 2 diagonal moves + 3 orthogonal moves = 5 moves,
        # strictly fewer than the 7-move pure L-shape.
        assert route.length == 5


class TestShortestRoute:
    def test_open_grid_prefers_direct_diagonal_over_detour(self):
        world = World(width=20, height=20)
        planner = PathPlanner(world)
        route = planner.find_path(2, 2, 10, 10)
        assert route is not None
        assert route.length == 8  # pure diagonal, no obstruction

    def test_straight_line_orthogonal_route_unaffected(self):
        # A straight horizontal/vertical target should not somehow
        # become "cheaper" via a detour through diagonals -- straight
        # remains straight and minimal.
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 6, 0)
        assert route is not None
        assert route.length == 6
        assert all(y == 0 for _, y in route.cells)


class TestObstacleAvoidance:
    def test_route_never_crosses_an_obstacle_cell(self):
        world = World(width=8, height=8)
        for y in range(7):
            world.add_obstacle(Obstacle(id=f"wall-{y}", x=4, y=y, type="Wall"))
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 7, 0)

        assert route is not None
        obstacle_cells = {(4, y) for y in range(7)}
        assert all(cell not in obstacle_cells for cell in route.cells)

    def test_no_route_exists_when_fully_enclosed(self):
        world = World(width=6, height=6)
        # Wall off (3,3) completely, including diagonals, so it is a
        # genuinely unreachable island under the corner-cutting rule.
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
            world.add_obstacle(Obstacle(id=f"o-{dx}-{dy}", x=3 + dx, y=3 + dy, type="Wall"))
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 3, 3)
        assert route is None


class TestCornerCuttingPrevention:
    def test_diagonal_move_blocked_when_both_corners_are_obstacles(self):
        world = World(width=8, height=8)
        world.add_obstacle(Obstacle(id="o1", x=4, y=3, type="Wall"))
        world.add_obstacle(Obstacle(id="o2", x=3, y=4, type="Wall"))
        planner = PathPlanner(world)

        route = planner.find_path(3, 3, 4, 4)
        assert route is not None
        # Must NOT be the direct two-cell diagonal cut.
        assert route.cells != ((3, 3), (4, 4))
        # Every cell in the route must still be walkable (no obstacle
        # crossed, confirming the detour is genuine, not a fluke).
        assert (4, 3) not in route.cells
        assert (3, 4) not in route.cells

    def test_diagonal_move_allowed_when_corners_are_clear(self):
        world = World(width=8, height=8)
        planner = PathPlanner(world)
        route = planner.find_path(3, 3, 4, 4)
        assert route is not None
        assert route.cells == ((3, 3), (4, 4))

    def test_diagonal_move_blocked_when_only_one_corner_is_an_obstacle(self):
        # Even a single blocked corner must prevent the diagonal cut
        # -- not just both corners together.
        world = World(width=8, height=8)
        world.add_obstacle(Obstacle(id="o1", x=4, y=3, type="Wall"))
        planner = PathPlanner(world)
        route = planner.find_path(3, 3, 4, 4)
        assert route is not None
        assert route.cells != ((3, 3), (4, 4))


class TestDeterminism:
    def test_same_start_goal_and_world_always_produces_same_route(self):
        world = World(width=15, height=15)
        for y in range(10):
            world.add_obstacle(Obstacle(id=f"wall-{y}", x=7, y=y, type="Wall"))
        planner = PathPlanner(world)

        first = planner.find_path(0, 0, 14, 5)
        second = planner.find_path(0, 0, 14, 5)
        third = planner.find_path(0, 0, 14, 5)

        assert first == second == third

    def test_determinism_holds_across_separate_planner_instances(self):
        def build_and_route():
            world = World(width=15, height=15)
            for y in range(10):
                world.add_obstacle(Obstacle(id=f"wall-{y}", x=7, y=y, type="Wall"))
            planner = PathPlanner(world)
            return planner.find_path(0, 0, 14, 5)

        assert build_and_route() == build_and_route()


class TestRouteLengthIsAMoveCount:
    def test_length_equals_cell_count_minus_one(self):
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(1, 1, 6, 4)
        assert route is not None
        assert route.length == len(route.cells) - 1

    def test_length_is_an_int_not_a_float(self):
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 5, 5)  # pure diagonal, would sum to a float internally
        assert route is not None
        assert isinstance(route.length, int)

    def test_diagonal_and_orthogonal_moves_each_count_as_one_move(self):
        # A 3-move pure-diagonal route and a 3-move pure-orthogonal
        # route must report the same length (3) even though their
        # internal A* selection costs differ (3*sqrt(2) vs 3).
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        diagonal_route = planner.find_path(0, 0, 3, 3)
        orthogonal_route = planner.find_path(0, 0, 3, 0)
        assert diagonal_route.length == 3
        assert orthogonal_route.length == 3

    def test_start_equals_goal_has_length_zero(self):
        world = World(width=12, height=12)
        planner = PathPlanner(world)
        route = planner.find_path(5, 5, 5, 5)
        assert route is not None
        assert route.length == 0
        assert route.cells == ((5, 5),)


class TestMovementCostConsistency:
    def test_octile_distance_matches_route_geometry(self):
        # Sanity check that the actual selected route's geometric cost
        # (independently recomputed here) matches what octile distance
        # predicts for an open, unobstructed diagonal case -- confirms
        # the heuristic and the real search agree, not just that the
        # route "looks" diagonal.
        world = World(width=20, height=20)
        planner = PathPlanner(world)
        route = planner.find_path(0, 0, 7, 4)
        assert route is not None

        total_cost = 0.0
        for (x1, y1), (x2, y2) in zip(route.cells, route.cells[1:]):
            dx, dy = abs(x2 - x1), abs(y2 - y1)
            assert dx <= 1 and dy <= 1  # every step is a single-cell move
            total_cost += math.sqrt(2) if (dx == 1 and dy == 1) else 1.0

        dx, dy = 7, 4
        diag = min(dx, dy)
        straight = max(dx, dy) - diag
        expected_cost = diag * math.sqrt(2) + straight
        assert abs(total_cost - expected_cost) < 1e-9
