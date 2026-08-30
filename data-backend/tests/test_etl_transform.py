from datetime import date, timedelta

import pandas as pd

from etl.clean import clean_projects
from etl.transform import compute_planned_progress, transform_projects


def test_clean_projects_normalizes_status_and_dates():
    today = date.today()
    start = today - timedelta(days=60)
    end = today + timedelta(days=300)
    df = pd.DataFrame([{
        "name": "Road X",
        "category": "ROAD",
        "latitude": "16.5",
        "longitude": "80.6",
        "budget_allocated": "1000000",
        "reported_progress": "40",
        "status": "In Progress",
        "planned_start": start.isoformat(),
        "planned_end": end.isoformat(),
    }])
    cleaned = clean_projects(df)
    assert cleaned["category"].iloc[0] == "road"
    assert cleaned["status"].iloc[0] == "IN_PROGRESS"
    assert cleaned["budget_allocated"].iloc[0] == 1000000.0


def test_compute_planned_progress_clamps_and_models_linear():
    start = date(2024, 1, 1)
    end = date(2024, 1, 11)  # 10 day duration
    # at day 5 (midpoint) => 50%
    assert compute_planned_progress(start, end, date(2024, 1, 6)) == 50.0
    # before start => 0; well past end => 100
    assert compute_planned_progress(start, end, date(2023, 1, 1)) == 0.0
    assert compute_planned_progress(start, end, date(2025, 1, 1)) == 100.0


def test_transform_projects_sets_status_and_priority():
    today = date.today()
    start = today - timedelta(days=200)
    end = today + timedelta(days=100)
    df = pd.DataFrame([{
        "name": "Road Y",
        "category": "road",
        "latitude": "16.5",
        "longitude": "80.6",
        "reported_progress": "10",
        "status": "IN_PROGRESS",
        "planned_start": start.isoformat(),
        "planned_end": end.isoformat(),
        "budget_allocated": "5000000",
    }])
    # clean (as the pipeline does) before transform so dates are real date objects
    out = transform_projects(clean_projects(df))
    assert "planned_progress" in out.columns
    assert "actual_progress" in out.columns
    assert "priority_score" in out.columns
    # far behind schedule => escalated
    assert out["current_status"].iloc[0] in ("DELAYED", "STALLED")
