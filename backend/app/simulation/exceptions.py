"""Custom exceptions for the ARGUS Simulation module.

Per docs/simulation-api.md, SimulationEngine raises TypeError for
invalid constructor arguments. Every in-simulation failure condition
(insufficient round-trip battery, an unreachable target, an agent's
health dropping mid-execution, a blocked next cell) is reported in
step()'s return value, not as an exception. SimulationError exists for
consistency with the World, Agent, Mission, Planning, and Path Planner
modules' error hierarchies, and as an extension point for future
simulation-specific error conditions.
"""

from __future__ import annotations


class SimulationError(Exception):
    """Base class for all Simulation Engine errors."""