"""ARGUS Simulation module.

Per docs/simulation-api.md, only ``SimulationEngine`` forms the public
surface of this module. Internal helpers (anything prefixed with
``_``) must not be used or modified by other modules.
"""

from .engine import SimulationEngine
from .exceptions import SimulationError

__all__ = [
    "SimulationEngine",
    "SimulationError",
]