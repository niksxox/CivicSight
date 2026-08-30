"""
Spatial / analytics query checks against the live PostGIS database.

Covers: nearest-facility distance, point/geometry containment, distance
calculation, and a spatial join between projects and facilities, plus the
analytics/coverage API feeds that the dashboard depends on.
"""
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app

client = TestClient(app)


def test_nearest_facility_distance(engine):
    with engine.connect() as conn:
        # a known point inside Andhra Pradesh
        lng, lat = 80.6, 16.5
        dist = conn.execute(text(
            "SELECT ST_Distance(location, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography) "
            "FROM facilities ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lng,:lat),4326) LIMIT 1"
        ), {"lng": lng, "lat": lat}).scalar()
    assert dist is not None
    assert dist >= 0


def test_district_boundary_contains_its_centroid(engine):
    with engine.connect() as conn:
        inside = conn.execute(text(
            "SELECT ST_Contains(boundary::geometry, ST_Centroid(boundary::geometry)) "
            "FROM district_population LIMIT 1"
        )).scalar()
    assert inside is True


def test_spatial_join_projects_near_facilities(engine):
    with engine.connect() as conn:
        pid = conn.execute(text("select id from projects limit 1")).scalar()
        near = conn.execute(text(
            "SELECT count(*) FROM facilities f, projects p "
            "WHERE p.id = :pid AND ST_DWithin(f.location, p.location, 50000)"
        ), {"pid": pid}).scalar()
    assert near >= 1


def test_infrastructure_endpoint_returns_geojson():
    r = client.get("/infrastructure")
    assert r.status_code == 200
    body = r.json()
    assert "network" in body and "facilities" in body
    if body["network"]:
        assert "geojson" in body["network"][0]


def test_coverage_endpoint_returns_state_aggregates():
    r = client.get("/analytics/coverage")
    assert r.status_code == 200
    sources = {row["source"] for row in r.json()}
    assert "pmgsy" in sources
    assert "jal_jeevan_mission" in sources
    # non-spatial aggregates must never claim a fake geometry
    for row in r.json():
        assert row["geo_precision"] == "non_spatial_state_aggregate"
