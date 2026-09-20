"""Tests for app/geo/overpass.py.

Response-parsing tests use realistic, hand-built Overpass [out:json]
response bodies -- no real network call. fetch_buildings' HTTP
plumbing is tested via httpx's own mock transport (httpx.MockTransport),
which intercepts the request at the transport layer without touching
the network, keeping this test suite fast and independent of Overpass
actually being reachable.
"""

from __future__ import annotations

import httpx
import pytest

from app.geo.conversion import GeoBounds
from app.geo.overpass import OverpassError, fetch_buildings, parse_overpass_buildings


BENGALURU_BOUNDS = GeoBounds(south=12.930, west=77.610, north=12.945, east=77.625)


def _sample_response() -> dict:
    return {
        "version": 0.6,
        "elements": [
            {
                "type": "way",
                "id": 123456789,
                "tags": {"building": "yes"},
                "geometry": [
                    {"lat": 12.9351, "lon": 77.6151},
                    {"lat": 12.9352, "lon": 77.6151},
                    {"lat": 12.9352, "lon": 77.6152},
                    {"lat": 12.9351, "lon": 77.6152},
                ],
            },
            {
                "type": "way",
                "id": 987654321,
                "tags": {"building": "commercial"},
                "geometry": [
                    {"lat": 12.936, "lon": 77.616},
                    {"lat": 12.937, "lon": 77.616},
                    {"lat": 12.937, "lon": 77.617},
                ],
            },
            {
                "type": "relation",
                "id": 555000,
                "tags": {"building": "apartments", "type": "multipolygon"},
                "members": [
                    {
                        "type": "way",
                        "role": "outer",
                        "geometry": [
                            {"lat": 12.938, "lon": 77.618},
                            {"lat": 12.939, "lon": 77.618},
                            {"lat": 12.939, "lon": 77.619},
                            {"lat": 12.938, "lon": 77.619},
                        ],
                    },
                ],
            },
        ],
    }


class TestParseOverpassBuildings:
    def test_parses_ways_and_relations(self):
        buildings = parse_overpass_buildings(_sample_response())
        assert len(buildings) == 3

    def test_skips_degenerate_geometry(self):
        response = {
            "elements": [
                {"type": "way", "id": 1, "geometry": [{"lat": 12.9, "lon": 77.6}]},
            ]
        }
        assert parse_overpass_buildings(response) == []

    def test_skips_non_way_non_relation_elements(self):
        response = {
            "elements": [
                {"type": "node", "id": 1, "tags": {"building": "yes"}},
            ]
        }
        assert parse_overpass_buildings(response) == []

    def test_skips_relation_with_no_usable_outer_ring(self):
        response = {
            "elements": [
                {
                    "type": "relation",
                    "id": 2,
                    "members": [{"type": "way", "role": "inner", "geometry": []}],
                }
            ]
        }
        assert parse_overpass_buildings(response) == []

    def test_sorted_by_osm_id_ascending(self):
        buildings = parse_overpass_buildings(_sample_response())
        ids = [b.osm_id for b in buildings]
        assert ids == sorted(ids)

    def test_relation_outer_ring_extracted_not_inner(self):
        buildings = parse_overpass_buildings(_sample_response())
        relation_building = next(b for b in buildings if b.osm_id == 555000)
        assert len(relation_building.ring) == 4

    def test_empty_elements_returns_empty_list(self):
        assert parse_overpass_buildings({"elements": []}) == []

    def test_missing_elements_key_returns_empty_list(self):
        assert parse_overpass_buildings({}) == []

    def test_deterministic_across_repeated_calls(self):
        response = _sample_response()
        assert parse_overpass_buildings(response) == parse_overpass_buildings(response)


class TestFetchBuildings:
    def test_successful_response_returns_parsed_buildings(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_sample_response())

        client = httpx.Client(transport=httpx.MockTransport(handler))
        buildings = fetch_buildings(BENGALURU_BOUNDS, client=client)
        assert len(buildings) == 3

    def test_non_200_status_raises_overpass_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, text="rate limited")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(OverpassError):
            fetch_buildings(BENGALURU_BOUNDS, client=client)

    def test_non_json_response_raises_overpass_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json at all {{{")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(OverpassError):
            fetch_buildings(BENGALURU_BOUNDS, client=client)

    def test_empty_area_is_a_valid_non_error_result(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"elements": []})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        buildings = fetch_buildings(BENGALURU_BOUNDS, client=client)
        assert buildings == []

    def test_query_includes_bounding_box(self):
        captured_request = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_request["body"] = request.read().decode()
            return httpx.Response(200, json={"elements": []})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        fetch_buildings(BENGALURU_BOUNDS, client=client)
        body = captured_request["body"]
        assert "12.93" in body
        assert "77.61" in body
        assert "building" in body

    def test_request_sends_identifying_user_agent_and_accept_header(self):
        # Overpass's public instance (overpass-api.de) has been
        # observed rejecting requests with no explicit Accept header
        # and httpx's default User-Agent with an HTTP 406 -- see
        # fetch_buildings' own comment. This locks in the fix so a
        # future change to this function can't silently drop these
        # headers again.
        captured_request = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_request["headers"] = dict(request.headers)
            return httpx.Response(200, json={"elements": []})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        fetch_buildings(BENGALURU_BOUNDS, client=client)
        headers = captured_request["headers"]
        assert "argus" in headers.get("user-agent", "").lower()
        assert headers.get("accept") == "application/json"
