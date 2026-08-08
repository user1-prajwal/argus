"""Custom exceptions for the ARGUS Path Planner module.

Per docs/path-planner-api.md, the Path Planner raises TypeError for
non-int coordinates and ValueError for coordinates outside the World's
bounds. "No route exists" is not an error -- find_path() returns None.
PathPlannerError exists for consistency with the World, Agent, Mission,
and Planning modules' error hierarchies, and as an extension point for
future path-planner-specific error conditions.
"""

from __future__ import annotations


class PathPlannerError(Exception):
    """Base class for all Path Planner errors."""