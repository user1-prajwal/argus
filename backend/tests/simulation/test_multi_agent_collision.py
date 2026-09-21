"""Tests for multi-agent collision behavior in SimulationEngine.step().

These tests verify a property of the EXISTING implementation (see
app/simulation/engine.py, _advance_one): agents are advanced one at a
time within a single step() call, and each agent's move updates
World's shared _occupied_cells immediately (via _occupy_cell/
_release_cell) before the next agent in the same tick is evaluated.
Because World.is_walkable consults _occupied_cells live, this already
guarantees:

  1. Two agents can never end a tick standing on the same cell.
  2. An agent whose next cell is already occupied (by an obstacle OR
     another agent) waits that tick rather than moving into it.
  3. This resolves deterministically, since agents are always
     processed in the same order (insertion order of
     SimulationEngine._executions, itself driven by MissionRegistry's
     own insertion-ordered iteration).

No change was made to SimulationEngine to satisfy this -- these tests
exist to prove the existing mechanism already satisfies the project's
multi-drone collision requirements, per this phase's instruction to
verify before changing anything.
"""

from __future__ import annotations

from app.agent import (
    Agent,
    AgentActivity,
    AgentRegistry,
    HealthStatus,
    PlatformType,
)
from app.mission import Mission, MissionPriority, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner
from app.simulation import SimulationEngine
from app.world import World


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
        status=MissionStatus.PENDING,
        target_cells=frozenset({target}),
    )


class TestNoTwoAgentsShareACell:
    def test_two_agents_converging_on_adjacent_paths_never_share_a_cell(self):
        # Two agents start side by side and are both routed to targets
        # that would put them on a collision course through the same
        # corridor if not for sequential per-tick resolution.
        world = World(width=6, height=3)
        agents = AgentRegistry()
        agents.add_agent(_agent("a1", 0, 1))
        agents.add_agent(_agent("a2", 5, 1))
        missions = MissionRegistry()
        missions.add_mission(_mission("m1", (5, 1)))
        missions.add_mission(_mission("m2", (0, 1)))
        missions.assign_agents("m1", {"a1"})
        missions.update_status("m1", MissionStatus.ASSIGNED)
        missions.assign_agents("m2", {"a2"})
        missions.update_status("m2", MissionStatus.ASSIGNED)
        agents.assign_mission("a1", "m1")
        agents.update_activity("a1", AgentActivity.ASSIGNED)
        agents.assign_mission("a2", "m2")
        agents.update_activity("a2", AgentActivity.ASSIGNED)

        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        seen_positions_ok: list[bool] = []
        for _ in range(20):
            engine.step()
            pos1 = (agents.get_agent("a1").x, agents.get_agent("a1").y)
            pos2 = (agents.get_agent("a2").x, agents.get_agent("a2").y)
            seen_positions_ok.append(pos1 != pos2)
            if (
                agents.get_agent("a1").activity == AgentActivity.IDLE
                and agents.get_agent("a2").activity == AgentActivity.IDLE
            ):
                break

        assert all(seen_positions_ok), "two agents occupied the same cell in some tick"

    def test_agent_waits_when_next_cell_is_occupied_by_another_agent(self):
        # "blocker" sits directly in "mover"'s path and never moves
        # (no mission of its own). "mover" must wait rather than move
        # into the blocker's cell.
        world = World(width=5, height=1)
        agents = AgentRegistry()
        agents.add_agent(_agent("blocker", 2, 0))
        agents.add_agent(_agent("mover", 0, 0))
        missions = MissionRegistry()
        missions.add_mission(_mission("m-mover", (4, 0)))
        missions.assign_agents("m-mover", {"mover"})
        missions.update_status("m-mover", MissionStatus.ASSIGNED)
        agents.assign_mission("mover", "m-mover")
        agents.update_activity("mover", AgentActivity.ASSIGNED)
        # Manually occupy the blocker's cell the same way SimulationEngine
        # does for an executing agent, since "blocker" has no mission of
        # its own to trigger _begin_execution's own _occupy_cell call.
        world._occupy_cell(2, 0)

        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        engine.step()  # pickup phase: mover's route computed, no move yet
        assert agents.get_agent("mover").x == 0

        for _ in range(10):
            if agents.get_agent("mover").activity == AgentActivity.IDLE:
                break
            engine.step()
            mover = agents.get_agent("mover")
            assert (mover.x, mover.y) != (2, 0), "mover moved onto the occupied blocker cell"


class TestDeterministicResolution:
    def test_same_scenario_run_twice_produces_identical_tick_by_tick_results(self):
        def build_and_run():
            world = World(width=6, height=6)
            agents = AgentRegistry()
            agents.add_agent(_agent("a1", 0, 0))
            agents.add_agent(_agent("a2", 5, 5))
            agents.add_agent(_agent("a3", 0, 5))
            missions = MissionRegistry()
            for mid, target, aid in [
                ("m1", (5, 5), "a1"),
                ("m2", (0, 0), "a2"),
                ("m3", (5, 0), "a3"),
            ]:
                missions.add_mission(_mission(mid, target))
                missions.assign_agents(mid, {aid})
                missions.update_status(mid, MissionStatus.ASSIGNED)
                agents.assign_mission(aid, mid)
                agents.update_activity(aid, AgentActivity.ASSIGNED)

            path_planner = PathPlanner(world)
            engine = SimulationEngine(world, agents, missions, path_planner)
            all_results = []
            for _ in range(30):
                all_results.append(engine.step())
                if all(
                    agents.get_agent(a).activity == AgentActivity.IDLE
                    for a in ("a1", "a2", "a3")
                ):
                    break
            return all_results

        run1 = build_and_run()
        run2 = build_and_run()
        assert run1 == run2


class TestExistingBehaviorIntact:
    def test_single_agent_mission_still_completes_and_returns_home(self):
        world = World(width=6, height=6)
        agents = AgentRegistry()
        agents.add_agent(_agent("solo", 0, 0))
        missions = MissionRegistry()
        missions.add_mission(_mission("m1", (3, 0)))
        missions.assign_agents("m1", {"solo"})
        missions.update_status("m1", MissionStatus.ASSIGNED)
        agents.assign_mission("solo", "m1")
        agents.update_activity("solo", AgentActivity.ASSIGNED)

        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        completed = False
        returned = False
        for _ in range(20):
            result = engine.step()
            if "m1" in result["completed_missions"]:
                completed = True
            if "solo" in result["returned_home"]:
                returned = True
            if returned:
                break

        assert completed
        assert returned
        assert agents.get_agent("solo").activity == AgentActivity.IDLE
        assert (agents.get_agent("solo").x, agents.get_agent("solo").y) == (0, 0)

    def test_battery_drains_by_exactly_one_per_move(self):
        world = World(width=6, height=1)
        agents = AgentRegistry()
        agents.add_agent(_agent("solo", 0, 0, battery=100))
        missions = MissionRegistry()
        missions.add_mission(_mission("m1", (3, 0)))
        missions.assign_agents("m1", {"solo"})
        missions.update_status("m1", MissionStatus.ASSIGNED)
        agents.assign_mission("solo", "m1")
        agents.update_activity("solo", AgentActivity.ASSIGNED)

        path_planner = PathPlanner(world)
        engine = SimulationEngine(world, agents, missions, path_planner)

        engine.step()  # pickup, no move
        battery_before = agents.get_agent("solo").battery_level
        engine.step()  # one move
        battery_after = agents.get_agent("solo").battery_level
        assert battery_before - battery_after == 1
