"""ARGUS Planning module.

Per docs/planning-api.md, only ``PlanningEngine`` forms the public
surface of this module. Internal helpers (anything prefixed with
``_``) must not be used or modified by other modules.
"""

from .exceptions import PlanningError
from .planner import PlanningEngine, PlanningResult

__all__ = [
    "PlanningEngine",
    "PlanningResult",
    "PlanningError",
]