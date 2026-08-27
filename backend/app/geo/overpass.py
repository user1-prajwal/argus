"""Queries the Overpass API for real OpenStreetMap building footprints
within a bounding box.

This module performs the ONE network call this feature depends on --
everything downstream (conversion.py, scenario_builder.py) is pure,
offline, deterministic geometry once this module has returned its
BuildingPolygon list. Overpass itself is not deterministic in the
strict sense (OSM data changes over time, and Overpass mirrors can
return elements in different orders) -- the determinism guarantee this
project makes ("same bounding box + same World dimensions + same OSM
data should produce the same World") is scoped to "same OSM data": for
a fixed snapshot of OSM data, the conversion is deterministic. This
module does not attempt to pin an OSM data version; that is a known
Version 1 limitation (see the module docstring in
scenario_builder.py's "Known limitations" section).

Uses the "building" tag exactly as instructed -- queries for any
element tagged building=* (not just building=yes), matching how OSM
actually tags real building footprints (building=yes, building=house,
building=apartments, building=commercial, etc. all count as
buildings).
"""

from __future__ import annotations

import httpx

from .conversion import BuildingPolygon, GeoBounds

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Generous but bounded -- Overpass can be slow under load; this is a
# demo/prototype timeout, not a production SLA.
_REQUEST_TIMEOUT_SECONDS = 25.0


class OverpassError(RuntimeError):
    """Raised when the Overpass API request fails or returns a
    response this module cannot parse. Distinct from a query that
    succeeds but finds zero buildings (that is not an error -- an
    empty list is a valid, normal result for a bounding box with no
    mapped buildings).
    """


def _build_query(bounds: GeoBounds) -> str:
    """Build an Overpass QL query for every building=* way and
    relation within bounds, requesting full geometry (out geom) so
    each returned element already carries its own vertex coordinates
    -- no separate node-resolution pass is needed.
    """
    bbox = f"{bounds.south},{bounds.west},{bounds.north},{bounds.east}"
    return f"""
    [out:json][timeout:25];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
    );
    out geom;
    """


def _extract_ring_from_way(element: dict) -> tuple[tuple[float, float], ...] | None:
    """A way's "geometry" field (present because the query uses
    "out geom") is an ordered list of {"lat":, "lon":} points. Returns
    None if the element has fewer than 3 usable vertices -- not a
    valid polygon, so not a building footprint this module can
    rasterize.
    """
    geometry = element.get("geometry")
    if not geometry:
        return None
    ring = tuple((pt["lat"], pt["lon"]) for pt in geometry if "lat" in pt and "lon" in pt)
    if len(ring) < 3:
        return None
    return ring


def _extract_ring_from_relation(element: dict) -> tuple[tuple[float, float], ...] | None:
    """A multipolygon relation's outer ring, taken from the first
    member tagged role "outer" that carries its own geometry. Version
    1 scope: only the first outer ring is used (inner rings / holes
    and multiple disjoint outer rings on one relation are not
    modeled) -- see scenario_builder.py's "Known limitations". This is
    a real, disclosed simplification, not a silent drop: a relation
    with no usable outer ring returns None and is skipped by
    parse_overpass_buildings, which the caller can count and report.
    """
    for member in element.get("members", []):
        if member.get("role") == "outer" and member.get("geometry"):
            ring = tuple(
                (pt["lat"], pt["lon"])
                for pt in member["geometry"]
                if "lat" in pt and "lon" in pt
            )
            if len(ring) >= 3:
                return ring
    return None


def parse_overpass_buildings(response_json: dict) -> list[BuildingPolygon]:
    """Parse an Overpass [out:json] response (from a query built by
    _build_query) into a list of BuildingPolygon.

    Elements with unusable geometry (too few vertices, or a relation
    with no outer ring carrying geometry) are skipped, not raised on
    -- OSM data is user-contributed and not every element is
    well-formed. Sorted by osm_id ascending before returning, so
    downstream rasterization always processes buildings in the same
    order regardless of the order Overpass happened to return them in
    -- required for this feature's determinism guarantee.
    """
    buildings: list[BuildingPolygon] = []
    for element in response_json.get("elements", []):
        element_type = element.get("type")
        osm_id = element.get("id")
        if osm_id is None:
            continue

        if element_type == "way":
            ring = _extract_ring_from_way(element)
        elif element_type == "relation":
            ring = _extract_ring_from_relation(element)
        else:
            continue

        if ring is not None:
            buildings.append(BuildingPolygon(osm_id=osm_id, ring=ring))

    buildings.sort(key=lambda b: b.osm_id)
    return buildings


def fetch_buildings(bounds: GeoBounds, client: httpx.Client | None = None) -> list[BuildingPolygon]:
    """Query Overpass for every building footprint within bounds and
    return them as BuildingPolygon instances, sorted deterministically
    by osm_id.

    Args:
        bounds: The geographic area to query. Callers are responsible
            for keeping this to a genuinely small operating area (see
            scenario_builder.py's area-size guard) -- Overpass is a
            shared public resource, not a service for bulk-downloading
            an entire city.
        client: Optional httpx.Client to use (for testing / connection
            reuse). A new one-off client is created and closed if not
            provided.

    Returns:
        Every parsed building footprint in the query result, possibly
        empty if the area has no mapped buildings.

    Raises:
        OverpassError: If the request fails (network error, non-200
            response, or a response body that is not valid JSON in
            the expected shape).
    """
    query = _build_query(bounds)
    owns_client = client is None
    http_client = client or httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS)

    # Overpass's public instance (overpass-api.de) rejects requests
    # that arrive with no Accept header and httpx's default User-Agent
    # -- observed in practice as an HTTP 406 from its Apache front end,
    # not a query-syntax problem. Sending an explicit, identifying
    # User-Agent (naming this project, per Overpass's own courtesy
    # expectation for automated clients) and an explicit Accept header
    # resolves this. This changes only how the request identifies
    # itself; the query body and everything downstream of the response
    # is unchanged.
    request_headers = {
        "User-Agent": "ARGUS-Geo-Scenario-Builder/1.0 (prototype; contact: none)",
        "Accept": "application/json",
    }

    try:
        try:
            response = http_client.post(
                OVERPASS_API_URL, data={"data": query}, headers=request_headers
            )
        except httpx.HTTPError as exc:
            raise OverpassError(f"Overpass API request failed: {exc}") from exc

        if response.status_code != 200:
            raise OverpassError(
                f"Overpass API returned status {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:
            response_json = response.json()
        except ValueError as exc:
            raise OverpassError("Overpass API returned a non-JSON response") from exc

        return parse_overpass_buildings(response_json)
    finally:
        if owns_client:
            http_client.close()
