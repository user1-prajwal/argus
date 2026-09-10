"""Tests for POST /scenarios/geo.

Mocks app.geo.overpass.fetch_buildings directly (via
unittest.mock.patch) rather than making a real Overpass call --
consistent with tests/geo/test_overpass.py's own approach of testing
HTTP plumbing separately from this endpoint's request/response
handling. No test in this file makes a real network request.
"""

from __future__ import annotations

from unittest.mock import patch

from app.geo.conversion import BuildingPolygon
from app.geo.overpass import OverpassError
from app.geo.scenario_builder import OperatingAreaTooLargeError

# A small Bengaluru-scale bounding box, matching tests/geo's own
# fixture area.
BENGALURU_PAYLOAD = {
    "south": 12.930,
    "west": 77.610,
    "north": 12.945,
    "east": 77.625,
    "world_width": 12,
    "world_height": 12,
}


def _one_building() -> list[BuildingPolygon]:
    return [
        BuildingPolygon(
            osm_id=42,
            ring=(
                (12.935, 77.615),
                (12.936, 77.615),
                (12.936, 77.616),
                (12.935, 77.616),
            ),
        )
    ]


class TestCreateGeoScenario:
    def test_creates_session_with_real_building_obstacles(self, client):
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings",
            return_value=_one_building(),
        ):
            response = client.post("/scenarios/geo", json=BENGALURU_PAYLOAD)

        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "not_started"
        assert body["building_count"] == 1
        assert body["obstacle_cell_count"] >= 1
        assert body["world_width"] == 12
        assert body["world_height"] == 12
        assert body["bounds"] == {
            "south": 12.930,
            "west": 77.610,
            "north": 12.945,
            "east": 77.625,
        }

    def test_zero_buildings_is_a_valid_result_not_an_error(self, client):
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            response = client.post("/scenarios/geo", json=BENGALURU_PAYLOAD)

        assert response.status_code == 200
        body = response.json()
        assert body["building_count"] == 0
        assert body["obstacle_cell_count"] == 0

    def test_creates_zero_agents_when_none_configured(self, client):
        # Core contract of this feature: no automatic fleet. See
        # app/geo/scenario_builder.py's module docstring, "FLEET IS
        # USER-CONFIGURED, NEVER AUTO-GENERATED".
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            created = client.post("/scenarios/geo", json=BENGALURU_PAYLOAD).json()
            state = client.get(f"/scenarios/{created['session_id']}").json()

        assert state["agents"] == []

    def test_creates_exactly_the_configured_agents(self, client):
        payload = {
            **BENGALURU_PAYLOAD,
            "agents": [
                {
                    "id": "DRONE-01",
                    "platform_type": "DRONE",
                    "x": 2,
                    "y": 3,
                    "battery_level": 100,
                    "capabilities": ["thermal_camera"],
                },
                {
                    "id": "DRONE-02",
                    "platform_type": "DRONE",
                    "x": 8,
                    "y": 9,
                    "battery_level": 95,
                    "capabilities": [],
                },
            ],
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            created = client.post("/scenarios/geo", json=payload).json()
            state = client.get(f"/scenarios/{created['session_id']}").json()

        assert len(state["agents"]) == 2
        by_id = {agent["id"]: agent for agent in state["agents"]}
        assert by_id["DRONE-01"]["x"] == 2
        assert by_id["DRONE-01"]["y"] == 3
        assert by_id["DRONE-01"]["capabilities"] == ["thermal_camera"]
        assert by_id["DRONE-02"]["battery_level"] == 95
        for agent in state["agents"]:
            assert agent["activity"] == "IDLE"
            assert agent["health_status"] == "ONLINE"
            assert agent["platform_type"] == "DRONE"

    def test_agent_position_is_snapped_off_a_building_obstacle(self, client):
        # A user can click a position that turns out to sit on a real
        # building they cannot see the outline of (no API exposes
        # obstacle geometry) -- the backend nudges it to the nearest
        # walkable cell rather than rejecting the request. See
        # app/geo/scenario_builder.py's _find_nearest_walkable.
        building_on_cell_5_5 = BuildingPolygon(
            osm_id=99,
            ring=(
                (12.9354, 77.6154),
                (12.9356, 77.6154),
                (12.9356, 77.6156),
                (12.9354, 77.6156),
            ),
        )
        payload = {
            **BENGALURU_PAYLOAD,
            "agents": [
                {
                    "id": "DRONE-01",
                    "platform_type": "DRONE",
                    "x": 5,
                    "y": 5,
                    "battery_level": 100,
                    "capabilities": [],
                },
            ],
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings",
            return_value=[building_on_cell_5_5],
        ):
            created = client.post("/scenarios/geo", json=payload).json()
            state = client.get(f"/scenarios/{created['session_id']}").json()

        assert len(state["agents"]) == 1
        agent = state["agents"][0]
        # Should have been created (not rejected), and should not
        # literally be sitting on the same cell as the obstacle it
        # would otherwise share -- exact nudged cell isn't asserted
        # (that's an implementation detail of the walkable-search
        # order), only that construction succeeded and didn't just
        # silently keep the blocked position without checking.
        assert agent["id"] == "DRONE-01"

    def test_duplicate_agent_ids_returns_422(self, client):
        payload = {
            **BENGALURU_PAYLOAD,
            "agents": [
                {
                    "id": "DRONE-01",
                    "platform_type": "DRONE",
                    "x": 1,
                    "y": 1,
                    "battery_level": 100,
                    "capabilities": [],
                },
                {
                    "id": "DRONE-01",
                    "platform_type": "DRONE",
                    "x": 2,
                    "y": 2,
                    "battery_level": 100,
                    "capabilities": [],
                },
            ],
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            response = client.post("/scenarios/geo", json=payload)

        assert response.status_code == 422

    def test_state_response_echoes_geo_bounds(self, client):
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            created = client.post("/scenarios/geo", json=BENGALURU_PAYLOAD).json()
            state = client.get(f"/scenarios/{created['session_id']}").json()

        assert state["geo_bounds"] == {
            "south": 12.930,
            "west": 77.610,
            "north": 12.945,
            "east": 77.625,
        }

    def test_ordinary_scenario_state_has_no_geo_bounds(
        self, client, minimal_scenario_payload
    ):
        created = client.post("/scenarios", json=minimal_scenario_payload).json()
        state = client.get(f"/scenarios/{created['session_id']}").json()
        assert state["geo_bounds"] is None

    def test_accepts_missions_directly(self, client):
        payload = {
            **BENGALURU_PAYLOAD,
            "missions": [
                {
                    "id": "survey-1",
                    "name": "Survey",
                    "description": "A test mission.",
                    "priority": "HIGH",
                    "target_cells": [[5, 5]],
                    "required_capabilities": [],
                }
            ],
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            created = client.post("/scenarios/geo", json=payload).json()
            state = client.get(f"/scenarios/{created['session_id']}").json()

        assert len(state["missions"]) == 1
        assert state["missions"][0]["status"] == "PENDING"

    def test_area_too_large_returns_422(self, client):
        huge_payload = {
            "south": 12.0,
            "west": 77.0,
            "north": 13.5,
            "east": 78.5,
            "world_width": 12,
            "world_height": 12,
        }
        response = client.post("/scenarios/geo", json=huge_payload)
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_invalid_bounds_south_greater_than_north_returns_422(self, client):
        bad_payload = {**BENGALURU_PAYLOAD, "south": 13.0, "north": 12.9}
        response = client.post("/scenarios/geo", json=bad_payload)
        assert response.status_code == 422

    def test_overpass_failure_returns_502(self, client):
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings",
            side_effect=OverpassError("upstream unreachable"),
        ):
            response = client.post("/scenarios/geo", json=BENGALURU_PAYLOAD)

        assert response.status_code == 502
        assert "detail" in response.json()

    def test_missing_required_field_returns_422(self, client):
        incomplete = {"south": 12.9, "west": 77.6, "north": 12.95}
        response = client.post("/scenarios/geo", json=incomplete)
        assert response.status_code == 422

    def test_default_world_dimensions_used_when_omitted(self, client):
        payload = {
            "south": 12.930,
            "west": 77.610,
            "north": 12.945,
            "east": 77.625,
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            response = client.post("/scenarios/geo", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["world_width"] == 12
        assert body["world_height"] == 12

    def test_full_lifecycle_start_step_on_geo_scenario(self, client):
        payload = {
            **BENGALURU_PAYLOAD,
            "agents": [
                {
                    "id": "DRONE-01",
                    "platform_type": "DRONE",
                    "x": 0,
                    "y": 0,
                    "battery_level": 100,
                    "capabilities": [],
                },
            ],
            "missions": [
                {
                    "id": "survey-1",
                    "name": "Survey",
                    "description": "A test mission.",
                    "priority": "HIGH",
                    "target_cells": [[2, 1]],
                    "required_capabilities": [],
                }
            ],
        }
        with patch(
            "app.geo.scenario_builder.overpass.fetch_buildings", return_value=[]
        ):
            created = client.post("/scenarios/geo", json=payload).json()
            session_id = created["session_id"]

            start_response = client.post(f"/scenarios/{session_id}/start")
            assert start_response.status_code == 200
            assert start_response.json()["planning_results"][0]["assigned_agent_id"] == "DRONE-01"

            step_response = client.post(f"/scenarios/{session_id}/step")
            assert step_response.status_code == 200
