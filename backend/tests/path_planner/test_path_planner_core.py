"""Tests for PathPlanner construction."""

from __future__ import annotations

import pytest

from app.path_planner import PathPlanner
from app.world import World


def test_construct_valid(world: World) -> None:
    planner = PathPlanner(world)

    assert isinstance(planner, PathPlanner)


def test_construct_rejects_wrong_world_type() -> None:
    with pytest.raises(TypeError):
        PathPlanner("not-a-world")  # type: ignore[arg-type]


def test_construct_rejects_none() -> None:
    with pytest.raises(TypeError):
        PathPlanner(None)  # type: ignore[arg-type]


def test_construct_rejects_agent_registry_style_object(world: World) -> None:
    # A plausible mistake: passing something else with a similar shape.
    with pytest.raises(TypeError):
        PathPlanner(object())  # type: ignore[arg-type]


def test_two_planners_on_the_same_world_are_independent_instances(world: World) -> None:
    planner_a = PathPlanner(world)
    planner_b = PathPlanner(world)

    assert planner_a is not planner_b