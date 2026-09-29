"""ARGUS Simulation module.

Per docs/simulation-api.md, only ``SimulationEngine`` (plus the small
``coverage_waypoints_for`` display helper below) forms the public
surface of this module. Internal helpers (anything prefixed with
``_``) must not be used or modified by other modules.
"""

from .engine import SimulationEngine, coverage_waypoints_for
from .exceptions import SimulationError

__all__ = [
    "SimulationEngine",
    "SimulationError",
    "coverage_waypoints_for",
]