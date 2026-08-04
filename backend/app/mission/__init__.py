"""ARGUS Mission module.

Per docs/mission-api.md, only ``MissionRegistry`` and the value/enum
types below form the public surface of this module. Internal classes
and methods (anything prefixed with ``_``) must not be used or modified
by other modules.

The ``Capability`` enum used by ``required_capabilities`` is reused
from the Agent module (``app.agent``) rather than redefined here --
import it from there, not from this package.
"""

from .enums import MissionPriority, MissionStatus
from .exceptions import DuplicateMissionError, MissionError, MissionNotFoundError
from .mission import Mission
from .registry import MissionRegistry

__all__ = [
    "MissionRegistry",
    "Mission",
    "MissionPriority",
    "MissionStatus",
    "MissionError",
    "DuplicateMissionError",
    "MissionNotFoundError",
]