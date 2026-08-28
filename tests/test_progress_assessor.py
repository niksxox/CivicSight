"""
Tests for CivicSight project progress assessment service.

These tests verify the deterministic progress-assessment contract:

    deviation = estimated_actual_progress - planned_progress

Status boundaries are defined by app.utils.constants.

The tests do not call any external service.
"""

from __future__ import annotations

import pytest

from app.models.progress_models import (
    ProgressAssessmentRequest,
    ProgressAssessmentResponse,
)
from app.services.progress_assessor import ProgressAssessor


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def assessor() -> ProgressAssessor:
    """Create a fresh progress assessor for each test."""
    return ProgressAssessor()


# ============================================================
# Request Model Validation
# ============================================================


def test_progress_request_accepts_valid_values():
    """Valid planned and actual percentages should be accepted."""

    request = ProgressAssessmentRequest(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    assert request.planned_progress == 80.0
    assert request.estimated_actual_progress == 58.0


@pytest.mark.parametrize(
    "planned_progress",
    [
        -1.0,
        -100.0,
        100.01,
        101.0,
    ],
)
def test_progress_request_rejects_invalid_planned_progress(
    planned_progress,
):
    """Planned progress must remain within 0..100."""

    with pytest.raises(Exception):
        ProgressAssessmentRequest(
            planned_progress=planned_progress,
            estimated_actual_progress=50.0,
        )


@pytest.mark.parametrize(
    "actual_progress",
    [
        -1.0,
        -100.0,
        100.01,
        101.0,
    ],
)
def test_progress_request_rejects_invalid_actual_progress(
    actual_progress,
):
    """Actual progress must remain within 0..100."""

    with pytest.raises(Exception):
        ProgressAssessmentRequest(
            planned_progress=50.0,
            estimated_actual_progress=actual_progress,
        )


@pytest.mark.parametrize(
    "value",
    [
        0.0,
        100.0,
    ],
)
def test_progress_request_accepts_percentage_boundaries(value):
    """0% and 100% are valid progress values."""

    request = ProgressAssessmentRequest(
        planned_progress=value,
        estimated_actual_progress=value,
    )

    assert request.planned_progress == value
    assert request.estimated_actual_progress == value


def test_progress_request_rejects_extra_fields():
    """The API data contract forbids unexpected fields."""

    with pytest.raises(Exception):
        ProgressAssessmentRequest(
            planned_progress=80.0,
            estimated_actual_progress=58.0,
            unexpected_field="invalid",
        )


# ============================================================
# Core Progress Assessment
# ============================================================


def test_standard_delayed_project(assessor):
    """
    SIH demo case:

        Planned = 80%
        Actual  = 58%
        Deviation = -22%
        Status = delayed
    """

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    assert isinstance(
        result,
        ProgressAssessmentResponse,
    )

    assert result.planned_progress == 80.0
    assert result.estimated_actual_progress == 58.0
    assert result.deviation == -22.0
    assert result.status == "delayed"


def test_positive_deviation_means_ahead(assessor):
    """Actual progress above planned progress should be ahead."""

    result = assessor.assess(
        planned_progress=50.0,
        estimated_actual_progress=60.0,
    )

    assert result.deviation == 10.0
    assert result.status == "ahead"


def test_zero_deviation_means_on_track(assessor):
    """Equal planned and actual progress should be on track."""

    result = assessor.assess(
        planned_progress=50.0,
        estimated_actual_progress=50.0,
    )

    assert result.deviation == 0.0
    assert result.status == "on_track"


def test_small_negative_deviation_is_on_track(assessor):
    """Deviation within the configured on-track tolerance is on track."""

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=75.0,
    )

    assert result.deviation == -5.0
    assert result.status == "on_track"


def test_small_positive_deviation_is_on_track(assessor):
    """Deviation within the positive tolerance is on track."""

    result = assessor.assess(
        planned_progress=50.0,
        estimated_actual_progress=55.0,
    )

    assert result.deviation == 5.0
    assert result.status == "on_track"


def test_deviation_below_negative_threshold_is_delayed(
    assessor,
):
    """Deviation below -5% should be delayed."""

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=74.9,
    )

    assert result.deviation == pytest.approx(-5.1)
    assert result.status == "delayed"


def test_deviation_above_positive_threshold_is_ahead(
    assessor,
):
    """Deviation above +5% should be ahead."""

    result = assessor.assess(
        planned_progress=50.0,
        estimated_actual_progress=55.1,
    )

    assert result.deviation == pytest.approx(5.1)
    assert result.status == "ahead"


# ============================================================
# Boundary Progress Values
# ============================================================


def test_zero_planned_zero_actual(assessor):
    """A project at 0% planned and 0% actual is on track."""

    result = assessor.assess(
        planned_progress=0.0,
        estimated_actual_progress=0.0,
    )

    assert result.deviation == 0.0
    assert result.status == "on_track"


def test_zero_planned_positive_actual_is_ahead(assessor):
    """Actual progress above zero with zero planned progress is ahead."""

    result = assessor.assess(
        planned_progress=0.0,
        estimated_actual_progress=10.0,
    )

    assert result.deviation == 10.0
    assert result.status == "ahead"


def test_full_planned_full_actual_is_on_track(assessor):
    """100% planned and 100% actual should be on track."""

    result = assessor.assess(
        planned_progress=100.0,
        estimated_actual_progress=100.0,
    )

    assert result.deviation == 0.0
    assert result.status == "on_track"


def test_full_planned_low_actual_is_delayed(assessor):
    """Large negative deviation should be delayed."""

    result = assessor.assess(
        planned_progress=100.0,
        estimated_actual_progress=0.0,
    )

    assert result.deviation == -100.0
    assert result.status == "delayed"


def test_zero_planned_full_actual_is_ahead(assessor):
    """Maximum positive deviation should be ahead."""

    result = assessor.assess(
        planned_progress=0.0,
        estimated_actual_progress=100.0,
    )

    assert result.deviation == 100.0
    assert result.status == "ahead"


# ============================================================
# Deviation Calculation
# ============================================================


@pytest.mark.parametrize(
    (
        "planned",
        "actual",
        "expected_deviation",
    ),
    [
        (80.0, 58.0, -22.0),
        (50.0, 60.0, 10.0),
        (50.0, 50.0, 0.0),
        (90.0, 80.0, -10.0),
        (20.0, 40.0, 20.0),
        (0.0, 100.0, 100.0),
        (100.0, 0.0, -100.0),
    ],
)
def test_deviation_is_actual_minus_planned(
    assessor,
    planned,
    actual,
    expected_deviation,
):
    """Deviation must always equal actual - planned."""

    result = assessor.assess(
        planned_progress=planned,
        estimated_actual_progress=actual,
    )

    assert result.deviation == pytest.approx(
        expected_deviation
    )


# ============================================================
# Status Mapping
# ============================================================


@pytest.mark.parametrize(
    (
        "planned",
        "actual",
        "expected_status",
    ),
    [
        (50.0, 50.0, "on_track"),
        (80.0, 75.0, "on_track"),
        (50.0, 55.0, "on_track"),
        (80.0, 74.99, "delayed"),
        (50.0, 55.01, "ahead"),
        (80.0, 58.0, "delayed"),
        (50.0, 70.0, "ahead"),
    ],
)
def test_status_mapping(
    assessor,
    planned,
    actual,
    expected_status,
):
    """Status must follow the documented deviation thresholds."""

    result = assessor.assess(
        planned_progress=planned,
        estimated_actual_progress=actual,
    )

    assert result.status == expected_status


# ============================================================
# Invalid Input Tests
# ============================================================


@pytest.mark.parametrize(
    (
        "planned",
        "actual",
    ),
    [
        (-1.0, 50.0),
        (50.0, -1.0),
        (-100.0, 50.0),
        (50.0, -100.0),
        (101.0, 50.0),
        (50.0, 101.0),
    ],
)
def test_assessor_rejects_out_of_range_values(
    assessor,
    planned,
    actual,
):
    """Service should reject impossible percentage values."""

    with pytest.raises(Exception):
        assessor.assess(
            planned_progress=planned,
            estimated_actual_progress=actual,
        )


@pytest.mark.parametrize(
    "planned",
    [
        None,
        "",
        "invalid",
        [],
        {},
    ],
)
def test_assessor_rejects_invalid_planned_values(
    assessor,
    planned,
):
    """Planned progress must be numeric."""

    with pytest.raises(Exception):
        assessor.assess(
            planned_progress=planned,
            estimated_actual_progress=50.0,
        )


@pytest.mark.parametrize(
    "actual",
    [
        None,
        "",
        "invalid",
        [],
        {},
    ],
)
def test_assessor_rejects_invalid_actual_values(
    assessor,
    actual,
):
    """Actual progress must be numeric."""

    with pytest.raises(Exception):
        assessor.assess(
            planned_progress=50.0,
            estimated_actual_progress=actual,
        )


# ============================================================
# Response Contract
# ============================================================


def test_response_contains_only_expected_fields(
    assessor,
):
    """Response must remain compatible with the frontend/API contract."""

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    data = (
        result.model_dump()
        if hasattr(result, "model_dump")
        else result.dict()
    )

    assert set(data.keys()) == {
        "planned_progress",
        "estimated_actual_progress",
        "deviation",
        "status",
    }


def test_response_values_are_api_serializable(
    assessor,
):
    """Result should be safely serializable for FastAPI."""

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    data = (
        result.model_dump()
        if hasattr(result, "model_dump")
        else result.dict()
    )

    assert isinstance(data, dict)
    assert isinstance(
        data["planned_progress"],
        float,
    )
    assert isinstance(
        data["estimated_actual_progress"],
        float,
    )
    assert isinstance(
        data["deviation"],
        float,
    )
    assert isinstance(
        data["status"],
        str,
    )


def test_response_percentage_values_remain_in_valid_range(
    assessor,
):
    """Response percentages must remain between 0 and 100."""

    result = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    assert 0.0 <= result.planned_progress <= 100.0
    assert 0.0 <= result.estimated_actual_progress <= 100.0


def test_response_deviation_remains_in_valid_range(
    assessor,
):
    """Deviation must remain between -100 and +100."""

    result = assessor.assess(
        planned_progress=0.0,
        estimated_actual_progress=100.0,
    )

    assert -100.0 <= result.deviation <= 100.0


# ============================================================
# Determinism / Regression Tests
# ============================================================


def test_same_input_produces_same_output(
    assessor,
):
    """Progress assessment must be deterministic."""

    first = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    second = assessor.assess(
        planned_progress=80.0,
        estimated_actual_progress=58.0,
    )

    assert first == second


@pytest.mark.parametrize(
    (
        "planned",
        "actual",
    ),
    [
        (0.0, 0.0),
        (0.0, 100.0),
        (100.0, 0.0),
        (100.0, 100.0),
        (80.0, 58.0),
        (50.0, 50.0),
        (50.0, 60.0),
    ],
)
def test_result_is_always_validated_response(
    assessor,
    planned,
    actual,
):
    """Every valid input should produce the declared response model."""

    result = assessor.assess(
        planned_progress=planned,
        estimated_actual_progress=actual,
    )

    assert isinstance(
        result,
        ProgressAssessmentResponse,
    )

    assert result.planned_progress == planned
    assert result.estimated_actual_progress == actual