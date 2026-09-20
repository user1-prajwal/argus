"""HTTP integration tests for the ARGUS API layer.

Tests every endpoint in docs/api-spec.md and every documented error
case (404, 409, 422). Uses FastAPI's TestClient, which wraps httpx.
"""

from __future__ import annotations


# ----------------------------------------------------------------------
# POST /scenarios
# ----------------------------------------------------------------------


class TestCreateScenario:
    def test_creates_session_not_started(self, client, minimal_scenario_payload):
        response = client.post("/scenarios", json=minimal_scenario_payload)
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body and body["session_id"]
        assert body["phase"] == "not_started"

    def test_creates_session_with_agents_and_missions(self, client, scenario_payload):
        response = client.post("/scenarios", json=scenario_payload)
        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "not_started"

        state = client.get(f"/scenarios/{body['session_id']}").json()
        assert len(state["agents"]) == 1
        assert len(state["missions"]) == 1
        assert state["missions"][0]["status"] == "PENDING"
        assert state["world"]["obstacles"] == 1

    def test_each_create_call_gets_a_distinct_session(
        self, client, minimal_scenario_payload
    ):
        first = client.post("/scenarios", json=minimal_scenario_payload).json()
        second = client.post("/scenarios", json=minimal_scenario_payload).json()
        assert first["session_id"] != second["session_id"]

    def test_invalid_world_returns_422(self, client):
        payload = {"world": {"width": 0, "height": 12}, "agents": [], "missions": []}
        response = client.post("/scenarios", json=payload)
        assert response.status_code == 422

    def test_missing_world_returns_422(self, client):
        response = client.post("/scenarios", json={"agents": [], "missions": []})
        assert response.status_code == 422

    def test_duplicate_agent_id_returns_422(self, client):
        payload = {
            "world": {"width": 5, "height": 5},
            "agents": [
                {
                    "id": "dup",
                    "platform_type": "DRONE",
                    "x": 0,
                    "y": 0,
                    "battery_level": 50,
                },
                {
                    "id": "dup",
                    "platform_type": "DRONE",
                    "x": 1,
                    "y": 1,
                    "battery_level": 50,
                },
            ],
            "missions": [],
        }
        response = client.post("/scenarios", json=payload)
        assert response.status_code == 422

    def test_empty_mission_name_returns_422(self, client):
        payload = {
            "world": {"width": 5, "height": 5},
            "agents": [],
            "missions": [
                {
                    "id": "m1",
                    "name": "",
                    "description": "desc",
                    "priority": "LOW",
                    "target_cells": [[1, 1]],
                }
            ],
        }
        response = client.post("/scenarios", json=payload)
        assert response.status_code == 422

    def test_invalid_world_422_has_detail_message(self, client):
        payload = {"world": {"width": 0, "height": 12}, "agents": [], "missions": []}
        response = client.post("/scenarios", json=payload)
        assert response.status_code == 422
        assert "detail" in response.json()
        assert response.json()["detail"]

    def test_invalid_platform_type_returns_422(self, client):
        payload = {
            "world": {"width": 5, "height": 5},
            "agents": [
                {
                    "id": "a1",
                    "platform_type": "NOT_A_REAL_TYPE",
                    "x": 0,
                    "y": 0,
                    "battery_level": 50,
                }
            ],
            "missions": [],
        }
        response = client.post("/scenarios", json=payload)
        assert response.status_code == 422


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}
# ----------------------------------------------------------------------


class TestGetScenario:
    def test_returns_full_state(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        response = client.get(f"/scenarios/{created['session_id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == created["session_id"]
        assert body["phase"] == "not_started"
        assert body["tick"] == 0
        assert body["world"]["width"] == 12
        assert body["world"]["height"] == 12
        assert "simulation_summary" in body

    def test_unknown_session_returns_404(self, client):
        response = client.get("/scenarios/does-not-exist")
        assert response.status_code == 404
        assert "detail" in response.json()


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/start
# ----------------------------------------------------------------------


class TestStartScenario:
    def test_runs_planning_once_and_moves_to_in_progress(
        self, client, scenario_payload
    ):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]

        response = client.post(f"/scenarios/{session_id}/start")
        assert response.status_code == 200
        body = response.json()
        assert body["planning_results"] == [
            {"mission_id": "thermal-survey", "assigned_agent_id": "drone-thermal"}
        ]

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["phase"] == "in_progress"
        assert state["missions"][0]["status"] == "ASSIGNED"
        assert state["missions"][0]["assigned_agent_ids"] == ["drone-thermal"]

    def test_unknown_session_returns_404(self, client):
        response = client.post("/scenarios/does-not-exist/start")
        assert response.status_code == 404

    def test_starting_twice_returns_409(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/start")
        assert response.status_code == 409
        assert "detail" in response.json()


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/step
# ----------------------------------------------------------------------


class TestStepScenario:
    def test_advances_one_tick(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/step")
        assert response.status_code == 200
        body = response.json()
        assert body["tick"] == 0
        assert set(body.keys()) == {
            "tick",
            "moved",
            "waiting",
            "completed_missions",
            "failed_missions",
            "returned_home",
        }

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["tick"] == 1

    def test_unknown_session_returns_404(self, client):
        response = client.post("/scenarios/does-not-exist/step")
        assert response.status_code == 404

    def test_stepping_before_start_returns_409(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        response = client.post(f"/scenarios/{created['session_id']}/step")
        assert response.status_code == 409

    def test_stepping_after_settled_returns_409(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        # Step until the session settles (thermal-survey target is
        # close; a small safety cap avoids an infinite loop if the
        # scenario's own behavior ever changes).
        for _ in range(100):
            state = client.get(f"/scenarios/{session_id}").json()
            if state["phase"] == "settled":
                break
            client.post(f"/scenarios/{session_id}/step")

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["phase"] == "settled"

        response = client.post(f"/scenarios/{session_id}/step")
        assert response.status_code == 409


# ----------------------------------------------------------------------
# POST /scenarios/{session_id}/run
# ----------------------------------------------------------------------


class TestRunScenario:
    def test_runs_to_settlement(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/run", json={"max_ticks": 200})
        assert response.status_code == 200
        body = response.json()
        assert body["terminated_reason"] in {"no_active_agents", "max_ticks_reached"}
        assert body["ticks_run"] == len(body["tick_results"])

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["phase"] == "settled"
        assert state["missions"][0]["status"] == "COMPLETED"

    def test_max_ticks_defaults_when_omitted(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/run", json={})
        assert response.status_code == 200

    def test_unknown_session_returns_404(self, client):
        response = client.post("/scenarios/does-not-exist/run", json={})
        assert response.status_code == 404

    def test_running_before_start_returns_409(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        response = client.post(
            f"/scenarios/{created['session_id']}/run", json={}
        )
        assert response.status_code == 409

    def test_running_after_settled_returns_409(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")
        client.post(f"/scenarios/{session_id}/run", json={"max_ticks": 200})

        response = client.post(f"/scenarios/{session_id}/run", json={"max_ticks": 200})
        assert response.status_code == 409

    def test_non_positive_max_ticks_returns_422(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/run", json={"max_ticks": 0})
        assert response.status_code == 422

    def test_negative_max_ticks_returns_422(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        response = client.post(f"/scenarios/{session_id}/run", json={"max_ticks": -5})
        assert response.status_code == 422


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/metrics
# ----------------------------------------------------------------------


class TestGetMetrics:
    def test_returns_three_summaries(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]

        response = client.get(f"/scenarios/{session_id}/metrics")
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "agent_summary",
            "mission_summary",
            "simulation_summary",
        }
        assert body["agent_summary"]["total"] == 1
        assert body["mission_summary"]["total"] == 1

    def test_reflects_state_after_start(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")

        body = client.get(f"/scenarios/{session_id}/metrics").json()
        assert body["mission_summary"]["status"]["assigned"] == 1

    def test_unknown_session_returns_404(self, client):
        response = client.get("/scenarios/does-not-exist/metrics")
        assert response.status_code == 404


# ----------------------------------------------------------------------
# GET /scenarios/{session_id}/agents/{agent_id}/route
# ----------------------------------------------------------------------


class TestGetAgentRoute:
    def test_returns_route_for_executing_agent(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")
        client.post(f"/scenarios/{session_id}/step")  # pickup phase computes the route

        response = client.get(
            f"/scenarios/{session_id}/agents/drone-thermal/route"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["agent_id"] == "drone-thermal"
        assert body["cells"][0] == [0, 0]
        assert body["cells"][-1] == [2, 0]
        assert body["length"] == len(body["cells"]) - 1
        assert body["length"] == 2

    def test_route_reflects_live_backend_state_not_a_recomputation(
        self, client, scenario_payload
    ):
        # This mirrors the backend's own
        # test_get_active_route_does_not_mutate_execution_state: calling
        # the endpoint twice in a row must not itself advance anything.
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")
        client.post(f"/scenarios/{session_id}/step")

        first = client.get(
            f"/scenarios/{session_id}/agents/drone-thermal/route"
        ).json()
        second = client.get(
            f"/scenarios/{session_id}/agents/drone-thermal/route"
        ).json()
        assert first == second

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["tick"] == 1

    def test_idle_agent_with_no_active_route_returns_404(
        self, client, scenario_payload
    ):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        # Not started yet -- agent is still IDLE, no execution tracked.

        response = client.get(
            f"/scenarios/{session_id}/agents/drone-thermal/route"
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_unknown_agent_returns_404(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]

        response = client.get(
            f"/scenarios/{session_id}/agents/does-not-exist/route"
        )
        assert response.status_code == 404

    def test_unknown_session_returns_404(self, client):
        response = client.get(
            "/scenarios/does-not-exist/agents/drone-thermal/route"
        )
        assert response.status_code == 404

    def test_route_disappears_once_agent_returns_home(
        self, client, scenario_payload
    ):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        client.post(f"/scenarios/{session_id}/start")
        client.post(f"/scenarios/{session_id}/run", json={"max_ticks": 200})

        state = client.get(f"/scenarios/{session_id}").json()
        assert state["phase"] == "settled"

        response = client.get(
            f"/scenarios/{session_id}/agents/drone-thermal/route"
        )
        assert response.status_code == 404


# ----------------------------------------------------------------------
# Full lifecycle
# ----------------------------------------------------------------------


class TestFullLifecycle:
    def test_create_start_step_run_metrics(self, client, scenario_payload):
        created = client.post("/scenarios", json=scenario_payload).json()
        session_id = created["session_id"]
        assert created["phase"] == "not_started"

        start_body = client.post(f"/scenarios/{session_id}/start").json()
        assert start_body["planning_results"][0]["assigned_agent_id"] == "drone-thermal"

        step_body = client.post(f"/scenarios/{session_id}/step").json()
        assert step_body["tick"] == 0

        run_body = client.post(
            f"/scenarios/{session_id}/run", json={"max_ticks": 200}
        ).json()
        assert run_body["terminated_reason"] in {
            "no_active_agents",
            "max_ticks_reached",
        }

        metrics = client.get(f"/scenarios/{session_id}/metrics").json()
        assert metrics["mission_summary"]["total"] == 1

        final_state = client.get(f"/scenarios/{session_id}").json()
        assert final_state["phase"] == "settled"
