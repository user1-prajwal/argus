"""In-memory session store for the ARGUS API layer.

A Session wraps one scenario's live backend objects -- World,
AgentRegistry, MissionRegistry, PlanningEngine, PathPlanner, and
SimulationEngine -- and tracks the three-phase lifecycle described in
docs/api-model.md, "Session Lifecycle": not_started -> in_progress ->
settled.

This module holds no business logic. It only constructs the existing
backend objects via their existing constructors and calls their
existing public methods -- see docs/api-model.md, "Design Principles".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.agent import Agent, AgentActivity, AgentRegistry, HealthStatus
from app.geo import GeoBounds
from app.mission import Mission, MissionRegistry, MissionStatus
from app.path_planner import PathPlanner
from app.planning import PlanningEngine, PlanningResult
from app.simulation import SimulationEngine
from app.world import World

# Matches app.simulation.engine.StepResult -- see
# app/scenario/runner.py's own re-declaration of the same type for the
# same reason: only SimulationEngine itself should be imported past its
# public surface.
StepResult = dict[str, "int | list[str]"]

PHASE_NOT_STARTED = "not_started"
PHASE_IN_PROGRESS = "in_progress"
PHASE_SETTLED = "settled"


@dataclass
class Session:
    """One scenario's live objects, plus API-layer bookkeeping.

    The six backend objects are constructed once, at session creation,
    and never replaced -- every subsequent request advances the same
    live objects, which is what lets tick-by-tick control work across
    separate HTTP requests (docs/api-model.md, "Design Goals").
    """

    session_id: str
    world: World
    agents: AgentRegistry
    missions: MissionRegistry
    planning_engine: PlanningEngine
    path_planner: PathPlanner
    simulation_engine: SimulationEngine
    phase: str = PHASE_NOT_STARTED
    planning_results: list[PlanningResult] = field(default_factory=list)
    tick_results: list[StepResult] = field(default_factory=list)
    # Set only for a session created via POST /scenarios/geo (see
    # routes.py's create_geo_scenario). None for every session created
    # via the original POST /scenarios -- that path has no real
    # geographic area, so there is nothing honest to put here. The
    # world_width/world_height used at creation time are always
    # recoverable from world.width/world.height directly (no
    # duplicate storage needed for those).
    geo_bounds: GeoBounds | None = None

    def is_settled(self) -> bool:
        """The same termination check ScenarioRunner._is_settled() uses.

        Duplicated here rather than imported because ScenarioRunner's
        version is a private method, and the API layer needs this check
        both to update session.phase and to drive Run's stopping
        condition -- see docs/api-spec.md, "Run".
        """
        summary = self.simulation_engine.simulation_summary()
        if summary["agents_executing"] > 0 or summary["agents_returning"] > 0:
            return False
        return not any(
            mission.status is MissionStatus.ASSIGNED
            for mission in self.missions.list_missions()
        )

    def refresh_phase(self) -> None:
        """Recompute phase after planning or a tick, per docs/api-model.md,
        "Session Lifecycle".

        Only ever moves a started session between in_progress and
        settled -- never back to not_started, and never touches a
        session that has not been started yet (start() sets
        in_progress explicitly, once, on the transition into it).
        """
        if self.phase == PHASE_NOT_STARTED:
            return
        self.phase = PHASE_SETTLED if self.is_settled() else PHASE_IN_PROGRESS


class SessionStore:
    """A simple in-memory dictionary of sessions, keyed by session id.

    Per docs/api-model.md, "Design Goals": "an in-memory session store
    is the right size for a prototype." No persistence, no locking --
    single-process Version 1 only.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(
        self,
        world: World,
        agents: AgentRegistry,
        missions: MissionRegistry,
        planning_engine: PlanningEngine,
        path_planner: PathPlanner,
        simulation_engine: SimulationEngine,
        geo_bounds: GeoBounds | None = None,
    ) -> Session:
        """Construct and store a new Session with a fresh session id."""
        session_id = uuid.uuid4().hex
        session = Session(
            session_id=session_id,
            world=world,
            agents=agents,
            missions=missions,
            planning_engine=planning_engine,
            path_planner=path_planner,
            simulation_engine=simulation_engine,
            geo_bounds=geo_bounds,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Return the session for this id, or None if it does not exist."""
        return self._sessions.get(session_id)
