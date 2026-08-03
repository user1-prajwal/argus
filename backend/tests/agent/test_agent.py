"""Tests for app.agent.agent.Agent."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest

from app.agent import Agent, AgentActivity, Capability, HealthStatus, PlatformType


def test_agent_valid_construction(make_agent: Callable[..., Agent]) -> None:
    agent = make_agent(agent_id="a1", x=3, y=4, battery_level=80)

    assert agent.id == "a1"
    assert (agent.x, agent.y) == (3, 4)
    assert agent.battery_level == 80
    assert agent.platform_type is PlatformType.DRONE
    assert agent.health_status is HealthStatus.ONLINE
    assert agent.activity is AgentActivity.IDLE
    assert agent.current_mission_id is None


def test_agent_rejects_empty_id(make_agent: Callable[..., Agent]) -> None:
    with pytest.raises(ValueError):
        make_agent(agent_id="")


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1), (-5, -5)])
def test_agent_rejects_negative_coordinates(
    make_agent: Callable[..., Agent], x: int, y: int
) -> None:
    with pytest.raises(ValueError):
        make_agent(x=x, y=y)


@pytest.mark.parametrize("battery_level", [-1, 101, 1000, -100])
def test_agent_rejects_out_of_range_battery(
    make_agent: Callable[..., Agent], battery_level: int
) -> None:
    with pytest.raises(ValueError):
        make_agent(battery_level=battery_level)


@pytest.mark.parametrize("battery_level", [0, 100, 50])
def test_agent_allows_boundary_and_mid_range_battery(
    make_agent: Callable[..., Agent], battery_level: int
) -> None:
    agent = make_agent(battery_level=battery_level)

    assert agent.battery_level == battery_level


def test_agent_rejects_empty_string_current_mission_id(
    make_agent: Callable[..., Agent]
) -> None:
    with pytest.raises(ValueError):
        make_agent(current_mission_id="")


def test_agent_allows_none_current_mission_id(make_agent: Callable[..., Agent]) -> None:
    agent = make_agent(current_mission_id=None)

    assert agent.current_mission_id is None


def test_agent_allows_valid_current_mission_id(make_agent: Callable[..., Agent]) -> None:
    agent = make_agent(current_mission_id="mission-1")

    assert agent.current_mission_id == "mission-1"


def test_agent_normalizes_capabilities_to_frozenset(
    make_agent: Callable[..., Agent]
) -> None:
    agent = make_agent(
        capabilities=[Capability.LIDAR, Capability.LIDAR, Capability.GPS]
    )

    assert isinstance(agent.capabilities, frozenset)
    assert agent.capabilities == frozenset({Capability.LIDAR, Capability.GPS})


def test_agent_allows_empty_capabilities(make_agent: Callable[..., Agent]) -> None:
    agent = make_agent(capabilities=frozenset())

    assert agent.capabilities == frozenset()


def test_agent_is_immutable(make_agent: Callable[..., Agent]) -> None:
    agent = make_agent()

    with pytest.raises(dataclasses.FrozenInstanceError):
        agent.battery_level = 50  # type: ignore[misc]


def test_agent_registered_at_is_set_automatically(
    make_agent: Callable[..., Agent]
) -> None:
    before = datetime.now(timezone.utc)
    agent = make_agent()
    after = datetime.now(timezone.utc)

    assert isinstance(agent.registered_at, datetime)
    assert before <= agent.registered_at <= after


def test_agent_registered_at_cannot_be_supplied_by_caller() -> None:
    # registered_at has init=False, so passing it must raise TypeError
    # rather than silently being accepted.
    with pytest.raises(TypeError):
        Agent(
            id="a1",
            platform_type=PlatformType.DRONE,
            x=0,
            y=0,
            battery_level=100,
            health_status=HealthStatus.ONLINE,
            activity=AgentActivity.IDLE,
            capabilities=frozenset(),
            registered_at=datetime.now(timezone.utc),  # type: ignore[call-arg]
        )


def test_agent_equality_is_value_based(make_agent: Callable[..., Agent]) -> None:
    a = make_agent(agent_id="same-id", x=1, y=1)
    b = dataclasses.replace(a, id="same-id")
    # dataclasses.replace() regenerates registered_at (it has
    # init=False), so force it back to a's value to isolate equality
    # to the fields that matter for this test.
    object.__setattr__(b, "registered_at", a.registered_at)

    assert a == b


def test_agents_with_different_registered_at_are_not_equal(
    make_agent: Callable[..., Agent]
) -> None:
    a = make_agent(agent_id="same-id")
    b = dataclasses.replace(a, id="same-id")
    # Force a deterministic, different registered_at so this assertion
    # never depends on clock resolution/timing.
    object.__setattr__(
        b, "registered_at", a.registered_at + timedelta(seconds=1)
    )

    assert a != b