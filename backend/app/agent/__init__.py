"""ARGUS Agent module.

Per docs/agent-api.md, only ``AgentRegistry`` and the value/enum types
below form the public surface of this module. Internal classes and
methods (anything prefixed with ``_``) must not be used or modified by
other modules.
"""

from .agent import Agent
from .enums import AgentActivity, Capability, HealthStatus, PlatformType
from .exceptions import AgentError, AgentNotFoundError, DuplicateAgentError
from .registry import AgentRegistry

__all__ = [
    "AgentRegistry",
    "Agent",
    "PlatformType",
    "Capability",
    "HealthStatus",
    "AgentActivity",
    "AgentError",
    "DuplicateAgentError",
    "AgentNotFoundError",
]