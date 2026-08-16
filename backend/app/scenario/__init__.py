"""ARGUS Scenario module.

An integration/demo layer above the existing World, Agent, Mission,
Planning, Path Planner, and Simulation modules -- it assembles and runs
a scenario using their public APIs only, and implements no planning,
routing, or execution logic of its own.

Only ``ScenarioRunner``, ``ScenarioResult``, and ``build_demo_scenario``
form the public surface of this module. Internal helpers (anything
prefixed with ``_``) must not be used or modified by other modules.
"""

from .runner import DEFAULT_MAX_TICKS, ScenarioResult, ScenarioRunner, build_demo_scenario

__all__ = [
    "ScenarioRunner",
    "ScenarioResult",
    "build_demo_scenario",
    "DEFAULT_MAX_TICKS",
]