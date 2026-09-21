"""Tests for SimulationEngine.get_active_route().

Constructed directly against the existing World, Agent, Mission,
PlanningEngine, PathPlanner, and SimulationEngine constructors and
methods pasted into this project's source -- no new backend behavior
is exercised here beyond the one new read-only method.
"""

from __future__ import annotations

from app.agent import (
    Agent,
    AgentActivity,
    AgentRegistry,
    Capability,
    HealthStatus,
    PlatformType,
)
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner
from app.simulation import SimulationEngine
from app.world import World


def _build_world() -> World:
    return World(width=6, height=6)


def _agent(agent_id: str, x: int, y: int, battery: int = 100) -> Agent:
    return Agent(
        id=agent_id,
        platform_type=PlatformType.DRONE,
        x=x,
        y=y,
        battery_level=battery,
        health_status=HealthStatus.ONLINE,
        activity=AgentActivity.IDLE,
        capabilities=frozenset(),
    )


def _mission(mission_id: str, target: tuple[int, int]) -> Mission:
    return Mission(
        id=mission_id,
        name=mission_id,
        description="test mission",
        priority=MissionPriority.HIGH,
        status=MissionStatus.ASSIGNED,
        target_cells=frozenset({target}),
    )


class TestGetActiveRouteNoExecution:
    def test_unknown_agent_id_returns_none(self):
        world = _build_world()
        agents = AgentRegistry()
        missions = MissionRegistry()
        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        assert engine.get_active_route("does-not-exist") is None

    def test_idle_agent_with_no_mission_returns_none(self):
        world = _build_world()
        agents = AgentRegistry()
        agents.add_agent(_agent("a1", 0, 0))
        missions = MissionRegistry()
        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        assert engine.get_active_route("a1") is None

    def test_before_any_step_freshly_assigned_agent_has_no_route_yet(self):
        # A mission in ASSIGNED status is only picked up by step()'s
        # own pickup phase -- before the first step() call,
        # SimulationEngine has not begun tracking any execution yet.
        world = _build_world()
        agents = AgentRegistry()
        agents.add_agent(_agent("a1", 0, 0))
        agents.assign_mission("a1", "m1")
        agents.update_activity("a1", AgentActivity.ASSIGNED)
        missions = MissionRegistry()
        missions.add_mission(_mission("m1", (3, 0)))
        missions.assign_agents("m1", {"a1"})
        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        assert engine.get_active_route("a1") is None


class TestGetActiveRouteDuringExecution:
    def _engine_with_assigned_mission(
        self, start: tuple[int, int] = (0, 0), target: tuple[int, int] = (3, 0)
    ):
        world = _build_world()
        agents = AgentRegistry()
        agents.add_agent(_agent("a1", *start))
        agents.assign_mission("a1", "m1")
        agents.update_activity("a1", AgentActivity.ASSIGNED)
        missions = MissionRegistry()
        missions.add_mission(_mission("m1", target))
        missions.assign_agents("m1", {"a1"})
        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)
        return engine

    def test_route_appears_after_pickup_step(self):
        engine = self._engine_with_assigned_mission()

        engine.step()  # pickup phase begins execution and computes the outbound route

        route = engine.get_active_route("a1")
        assert route is not None
        assert route.cells[0] == (0, 0)
        assert route.cells[-1] == (3, 0)
        assert route.length == 3

    def test_route_is_the_same_object_the_engine_is_actually_following(self):
        engine = self._engine_with_assigned_mission()
        engine.step()

        route_before = engine.get_active_route("a1")
        engine.step()
        route_after = engine.get_active_route("a1")

        # Same outbound route object/cells throughout the outbound
        # leg -- get_active_route reflects live internal state, not a
        # recomputation, so it does not change just from calling it.
        assert route_before is not None
        assert route_after is not None
        assert route_before.cells == route_after.cells

    def test_returns_none_after_agent_returns_home_and_stops_being_tracked(self):
        # start == target: outbound route has length 0, so
        # _begin_execution resolves arrival immediately and, since
        # start == launch_position, the agent is released straight to
        # IDLE within the same step() call -- never tracked at all.
        engine = self._engine_with_assigned_mission(start=(2, 2), target=(2, 2))

        engine.step()

        assert engine.get_active_route("a1") is None

    def test_returning_agent_has_a_return_route(self):
        engine = self._engine_with_assigned_mission(start=(0, 0), target=(2, 0))

        engine.step()  # begin outbound execution, route length 2
        engine.step()  # move 1 cell
        engine.step()  # arrive at target, mission completes, begin return route

        route = engine.get_active_route("a1")
        assert route is not None
        assert route.cells[0] == (2, 0)
        assert route.cells[-1] == (0, 0)

    def test_get_active_route_does_not_mutate_execution_state(self):
        engine = self._engine_with_assigned_mission()
        engine.step()

        route_first_call = engine.get_active_route("a1")
        route_second_call = engine.get_active_route("a1")

        assert route_first_call == route_second_call
        # Calling the getter twice in a row must not itself advance
        # anything -- simulation_summary should reflect no extra ticks
        # beyond the one step() call already made.
        assert engine.simulation_summary()["tick"] == 1
