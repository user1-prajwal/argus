"""Custom exceptions for the ARGUS Agent module."""

from __future__ import annotations


class AgentError(Exception):
    """Base class for all Agent module errors."""


class DuplicateAgentError(AgentError):
    """Raised when adding an agent whose id is already registered."""


class AgentNotFoundError(AgentError):
    """Raised when looking up, updating, or removing an agent id that is
    not registered.
    """