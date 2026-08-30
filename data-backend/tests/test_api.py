"""
Smoke tests. These hit a REAL database (via TestClient -> FastAPI ->
SQLAlchemy), so run `python scripts/init_db.py` and
`python scripts/generate_sample_data.py && python scripts/run_etl.py`
first. Not mocked on purpose — for a data pipeline, "does the query
actually run against PostGIS" is the thing worth testing.

Run: pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_projects():
    r = client.get("/projects?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_get_single_project_404():
    r = client.get("/projects/999999")
    assert r.status_code == 404


def test_district_analytics():
    r = client.get("/analytics/district")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_map_infrastructure():
    r = client.get("/map/infrastructure")
    assert r.status_code == 200
    assert "points" in r.json()


def test_project_flow_if_data_exists():
    """If sample data was loaded, walk one project through every endpoint."""
    listing = client.get("/projects?limit=1").json()
    if not listing["items"]:
        return  # no data loaded yet, nothing to assert further
    pid = listing["items"][0]["id"]

    assert client.get(f"/projects/{pid}").status_code == 200
    assert client.get(f"/projects/{pid}/nearby").status_code == 200
    assert client.get(f"/projects/{pid}/analytics").status_code == 200
    assert client.get(f"/projects/{pid}/history").status_code == 200
