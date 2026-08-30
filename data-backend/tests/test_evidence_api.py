"""
Citizen-evidence AI handoff endpoint test.

Validates the documented integration point used by the AI/image-analysis
teammate: POST /evidence/{id}/ai-result persists ai_condition/ai_confidence
and flips needs_human_review based on the confidence threshold.
"""
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.main import app

client = TestClient(app)


def _insert_evidence(engine):
    with engine.begin() as conn:
        return conn.execute(text(
            "INSERT INTO citizen_evidence (location) "
            "VALUES (ST_SetSRID(ST_MakePoint(80.6, 16.5), 4326)) RETURNING id"
        )).scalar()


def test_ai_handoff_stores_result_and_review_flag(engine):
    eid = _insert_evidence(engine)
    r = client.post(f"/evidence/{eid}/ai-result", json={
        "ai_condition": "cracked surface",
        "ai_confidence": 0.9,
        "ai_issue": "construction stopped",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ai_condition"] == "cracked surface"
    # 0.9 >= 0.65 threshold -> no human review needed
    assert body["needs_human_review"] is False

    # low confidence -> flagged for human review
    r2 = client.post(f"/evidence/{eid}/ai-result", json={
        "ai_condition": "looks fine",
        "ai_confidence": 0.2,
    })
    assert r2.status_code == 200
    assert r2.json()["needs_human_review"] is True

    with engine.connect() as conn:
        stored = conn.execute(text(
            "select ai_condition, ai_confidence from citizen_evidence where id=:id"
        ), {"id": eid}).mappings().first()
    assert stored["ai_condition"] == "looks fine"
    assert round(float(stored["ai_confidence"]), 2) == 0.2


def test_ai_handoff_404_for_missing_evidence(engine):
    eid = _insert_evidence(engine)
    with engine.begin() as conn:
        conn.execute(text("delete from citizen_evidence where id=:id"), {"id": eid})
    r = client.post(f"/evidence/{eid}/ai-result", json={
        "ai_condition": "x", "ai_confidence": 0.8,
    })
    assert r.status_code == 404
