"""Custom exceptions for the ARGUS Planning module.

Per docs/planning-api.md, the Planning Engine raises TypeError for
invalid constructor arguments and propagates MissionNotFoundError from
the Mission module when given an unknown mission id -- "no eligible
agent" is not an error condition. PlanningError exists for consistency
with the World, Agent, and Mission modules' error hierarchies, and as
an extension point for future planning-specific error conditions.
"""

from __future__ import annotations


class PlanningError(Exception):
    """Base class for all Planning Engine errors."""