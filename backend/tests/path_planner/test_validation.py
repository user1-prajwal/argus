"""Tests for PathPlanner.find_path input validation."""

from __future__ import annotations

import pytest

from app.path_planner import PathPlanner


def test_find_path_rejects_non_int_start_x(planner: PathPlanner) -> None:
    with pytest.raises(TypeError):
        planner.find_path(1.5, 0, 1, 1)  # type: ignore[arg-type]


def test_find_path_rejects_non_int_start_y(planner: PathPlanner) -> None:
    with pytest.raises(TypeError):
        planner.find_path(0, "0", 1, 1)  # type: ignore[arg-type]


def test_find_path_rejects_non_int_goal_x(planner: PathPlanner) -> None:
    with pytest.raises(TypeError):
        planner.find_path(0, 0, None, 1)  # type: ignore[arg-type]


def test_find_path_rejects_non_int_goal_y(planner: PathPlanner) -> None:
    with pytest.raises(TypeError):
        planner.find_path(0, 0, 1, 1.5)  # type: ignore[arg-type]


def test_find_path_rejects_bool_coordinates(planner: PathPlanner) -> None:
    # bool is a subclass of int in Python; must not be silently accepted.
    with pytest.raises(TypeError):
        planner.find_path(True, 0, 1, 1)
    with pytest.raises(TypeError):
        planner.find_path(0, False, 1, 1)


def test_find_path_rejects_start_outside_world(planner: PathPlanner) -> None:
    with pytest.raises(ValueError):
        planner.find_path(-1, 0, 1, 1)
    with pytest.raises(ValueError):
        planner.find_path(0, -1, 1, 1)
    with pytest.raises(ValueError):
        planner.find_path(5, 0, 1, 1)  # world width is 5: x=5 is out of range
    with pytest.raises(ValueError):
        planner.find_path(0, 5, 1, 1)  # world height is 5: y=5 is out of range


def test_find_path_rejects_goal_outside_world(planner: PathPlanner) -> None:
    with pytest.raises(ValueError):
        planner.find_path(0, 0, -1, 0)
    with pytest.raises(ValueError):
        planner.find_path(0, 0, 0, -1)
    with pytest.raises(ValueError):
        planner.find_path(0, 0, 5, 0)
    with pytest.raises(ValueError):
        planner.find_path(0, 0, 0, 5)


def test_find_path_accepts_corner_coordinates(planner: PathPlanner) -> None:
    # Must not raise: (0, 0) and (4, 4) are valid corners of a 5x5 world.
    route = planner.find_path(0, 0, 4, 4)

    assert route is not None


def test_find_path_validates_before_computing_anything(planner: PathPlanner) -> None:
    # An invalid start/goal pair must raise, not silently return None.
    with pytest.raises((TypeError, ValueError)):
        planner.find_path(-1, -1, -1, -1)