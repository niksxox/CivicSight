"""
Tests for CivicSight deterministic severity scoring service.

No external APIs are used.

The tests cover:
- normalization
- score clamping
- condition scoring
- issue scoring
- delay scoring
- impact scoring
- severity classification
- weighted calculation
- missing factors
- boundary conditions
- result immutability
- JSON-friendly convenience wrapper
"""

from __future__ import annotations

import pytest

from app.services.severity_scorer import (
    CONDITION_WEIGHT,
    DELAY_WEIGHT,
    IMPACT_WEIGHT,
    ISSUE_WEIGHT,
    SeverityResult,
    _clamp_score,
    _condition_score,
    _delay_score,
    _impact_score,
    _issue_score,
    _normalize_text,
    _round_score,
    calculate_severity,
    classify_severity,
    score_severity,
)
from app.utils.constants import (
    ConditionLevel,
    IssueType,
    SeverityLevel,
)


# ============================================================
# Normalization
# ============================================================


def test_normalize_text_with_string():
    """Normal strings should be stripped and lowercased."""

    assert _normalize_text("  Poor  ") == "poor"


def test_normalize_text_with_enum():
    """Enum values should be normalized using their value."""

    assert _normalize_text(
        ConditionLevel.POOR
    ) == "poor"


def test_normalize_text_with_none():
    """None should normalize to an empty string."""

    assert _normalize_text(None) == ""


def test_normalize_text_with_numeric_value():
    """Numeric values should be converted to strings."""

    assert _normalize_text(25) == "25"


# ============================================================
# Score Clamping
# ============================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-100.0, 0.0),
        (-1.0, 0.0),
        (0.0, 0.0),
        (25.0, 25.0),
        (100.0, 100.0),
        (101.0, 100.0),
        (500.0, 100.0),
    ],
)
def test_clamp_score(value, expected):
    """Scores must remain inside the global 0-100 range."""

    assert _clamp_score(value) == expected


def test_round_score_rounds_to_two_decimals():
    """Final score rounding must use two decimal places."""

    assert _round_score(33.333333) == 33.33
    assert _round_score(66.666666) == 66.67


def test_round_score_also_clamps():
    """Rounding helper must never produce values outside 0-100."""

    assert _round_score(-5.123) == 0.0
    assert _round_score(105.123) == 100.0


# ============================================================
# Condition Scoring
# ============================================================


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        (ConditionLevel.GOOD, 10.0),
        (ConditionLevel.FAIR, 35.0),
        (ConditionLevel.POOR, 70.0),
        (ConditionLevel.CRITICAL, 100.0),
        (ConditionLevel.UNKNOWN, 40.0),
        ("Good", 10.0),
        (" Fair ", 35.0),
        ("POOR", 70.0),
        ("critical", 100.0),
    ],
)
def test_condition_score(condition, expected):
    """Known condition levels must map to their defined scores."""

    assert _condition_score(condition) == expected


def test_unknown_condition_uses_neutral_score():
    """Unknown condition text should use the neutral fallback."""

    assert _condition_score(
        "something completely unknown"
    ) == 40.0


def test_none_condition_uses_neutral_score():
    """Direct condition helper should treat None as unknown."""

    assert _condition_score(None) == 40.0


# ============================================================
# Issue Scoring
# ============================================================


@pytest.mark.parametrize(
    ("issue", "expected"),
    [
        (IssueType.POTHOLE, 55.0),
        (IssueType.CRACK, 45.0),
        (IssueType.ROAD_DAMAGE, 70.0),
        (IssueType.BROKEN_STREETLIGHT, 55.0),
        (IssueType.DAMAGED_DRAINAGE, 75.0),
        (IssueType.GARBAGE_ACCUMULATION, 40.0),
        (IssueType.DAMAGED_STRUCTURE, 85.0),
        (IssueType.INCOMPLETE_WORK, 65.0),
        (IssueType.ABANDONED_INFRASTRUCTURE, 80.0),
        (IssueType.CONSTRUCTION_PROGRESS, 30.0),
        (IssueType.VISIBLE_DETERIORATION, 65.0),
        (IssueType.OTHER, 40.0),
    ],
)
def test_issue_score(issue, expected):
    """Every supported issue type must map deterministically."""

    assert _issue_score(issue) == expected


def test_issue_score_is_case_insensitive():
    """Issue strings should be matched case-insensitively."""

    assert _issue_score("POTHOLE") == 55.0
    assert _issue_score("  Road Damage  ") == 70.0


def test_unknown_issue_uses_neutral_score():
    """Unknown issues should use the conservative fallback."""

    assert _issue_score(
        "unknown infrastructure problem"
    ) == 40.0


def test_none_issue_uses_neutral_score():
    """Direct issue helper should safely handle None."""

    assert _issue_score(None) == 40.0


# ============================================================
# Delay Scoring
# ============================================================


@pytest.mark.parametrize(
    ("delay", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (0.0, 0.0),
        (10, 20.0),
        (10.0, 20.0),
        (25, 50.0),
        (50, 100.0),
        (100, 100.0),
    ],
)
def test_delay_score(delay, expected):
    """Delay percentage should be converted using the defined formula."""

    assert _delay_score(delay) == expected


def test_delay_score_accepts_numeric_string():
    """Numeric strings should be accepted."""

    assert _delay_score("25") == 50.0


def test_delay_score_rejects_invalid_string_safely():
    """Invalid delay text should return zero."""

    assert _delay_score("not-a-number") == 0.0


@pytest.mark.parametrize(
    "delay",
    [
        -1,
        -10,
        -100,
    ],
)
def test_negative_delay_is_zero(delay):
    """Negative delay represents being ahead and cannot increase severity."""

    assert _delay_score(delay) == 0.0


def test_delay_score_clamps_large_values():
    """Very large delay values must be capped at 100."""

    assert _delay_score(1000) == 100.0


# ============================================================
# Impact Scoring
# ============================================================


@pytest.mark.parametrize(
    ("impact", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (25, 25.0),
        (50, 50.0),
        (75, 75.0),
        (100, 100.0),
    ],
)
def test_numeric_impact_score(impact, expected):
    """Numeric impact should be interpreted directly as 0-100."""

    assert _impact_score(impact) == expected


@pytest.mark.parametrize(
    ("impact", "expected"),
    [
        ("low", 25.0),
        ("medium", 50.0),
        ("high", 75.0),
        ("critical", 100.0),
        ("LOW", 25.0),
        (" High ", 75.0),
    ],
)
def test_text_impact_score(impact, expected):
    """Text impact levels must map deterministically."""

    assert _impact_score(impact) == expected


def test_numeric_string_impact_is_supported():
    """Numeric strings should be accepted."""

    assert _impact_score("80") == 80.0


def test_unknown_impact_uses_neutral_score():
    """Unknown impact text should use the neutral score."""

    assert _impact_score(
        "unknown impact"
    ) == 40.0


def test_impact_clamps_values_above_100():
    """Impact values above 100 must be capped."""

    assert _impact_score(150) == 100.0


def test_impact_clamps_negative_values():
    """Negative numeric impact must be clamped to zero."""

    assert _impact_score(-50) == 0.0


# ============================================================
# Severity Classification
# ============================================================


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, SeverityLevel.LOW),
        (10.0, SeverityLevel.LOW),
        (33.33, SeverityLevel.LOW),
        (33.34, SeverityLevel.MEDIUM),
        (50.0, SeverityLevel.MEDIUM),
        (66.66, SeverityLevel.MEDIUM),
        (66.67, SeverityLevel.HIGH),
        (75.0, SeverityLevel.HIGH),
        (100.0, SeverityLevel.HIGH),
    ],
)
def test_classify_severity_boundaries(
    score,
    expected,
):
    """Severity classification must exactly follow project boundaries."""

    assert classify_severity(score) == expected


def test_classify_severity_clamps_negative_score():
    """Negative scores should classify as Low after clamping."""

    assert classify_severity(-100) == SeverityLevel.LOW


def test_classify_severity_clamps_score_above_100():
    """Scores above 100 should classify as High after clamping."""

    assert classify_severity(500) == SeverityLevel.HIGH


# ============================================================
# Main Calculation
# ============================================================


def test_calculate_severity_with_all_factors():
    """All supplied factors should participate in the weighted score."""

    result = calculate_severity(
        condition=ConditionLevel.POOR,
        issue=IssueType.ROAD_DAMAGE,
        delay=20,
        impact="high",
    )

    assert isinstance(
        result,
        SeverityResult,
    )

    # Condition = 70
    # Issue     = 70
    # Delay     = 40
    # Impact    = 75
    #
    # Weighted:
    # (70*.50 + 70*.20 + 40*.15 + 75*.15)
    # = 35 + 14 + 6 + 11.25
    # = 66.25

    assert result.score == 66.25
    assert result.severity == SeverityLevel.MEDIUM


def test_calculate_severity_condition_only():
    """When only condition is supplied, its score should be preserved."""

    result = calculate_severity(
        condition=ConditionLevel.POOR,
    )

    assert result.score == 70.0
    assert result.severity == SeverityLevel.HIGH


def test_calculate_severity_issue_only():
    """When only issue is supplied, its score should be preserved."""

    result = calculate_severity(
        issue=IssueType.DAMAGED_STRUCTURE,
    )

    assert result.score == 85.0
    assert result.severity == SeverityLevel.HIGH


def test_calculate_severity_delay_only():
    """When only delay is supplied, delay score should be preserved."""

    result = calculate_severity(
        delay=25,
    )

    assert result.score == 50.0
    assert result.severity == SeverityLevel.MEDIUM


def test_calculate_severity_impact_only():
    """When only impact is supplied, impact score should be preserved."""

    result = calculate_severity(
        impact="high",
    )

    assert result.score == 75.0
    assert result.severity == SeverityLevel.HIGH


def test_calculate_severity_missing_optional_factors_are_not_zero_weighted():
    """
    Supplied factors are renormalized when optional factors are omitted.

    With condition=Poor only, the result must remain 70 rather than
    being artificially reduced because issue/delay/impact are absent.
    """

    result = calculate_severity(
        condition="Poor",
    )

    assert result.score == 70.0


def test_calculate_severity_no_factors():
    """No supplied factors should produce the documented neutral result."""

    result = calculate_severity()

    assert result.score == 0.0
    assert result.severity == SeverityLevel.LOW

    assert result.factors == {
        "condition": 0.0,
        "issue": 0.0,
        "delay": 0.0,
        "impact": 0.0,
    }

    assert "No severity factors were supplied" in (
        result.explanation
    )


# ============================================================
# Weighting Tests
# ============================================================


def test_scoring_weights_sum_to_one():
    """The four internal weights must form a complete distribution."""

    total = (
        CONDITION_WEIGHT
        + ISSUE_WEIGHT
        + DELAY_WEIGHT
        + IMPACT_WEIGHT
    )

    assert total == pytest.approx(1.0)


def test_condition_has_highest_weight():
    """Condition should remain the strongest severity signal."""

    assert CONDITION_WEIGHT > ISSUE_WEIGHT
    assert CONDITION_WEIGHT > DELAY_WEIGHT
    assert CONDITION_WEIGHT > IMPACT_WEIGHT


def test_issue_weight_is_greater_than_delay_and_impact():
    """Issue context should have more weight than each secondary factor."""

    assert ISSUE_WEIGHT > DELAY_WEIGHT
    assert ISSUE_WEIGHT > IMPACT_WEIGHT


# ============================================================
# Factor Output Tests
# ============================================================


def test_result_contains_all_factor_scores():
    """Result should expose all normalized factor scores."""

    result = calculate_severity(
        condition="Poor",
        issue="Pothole",
        delay=20,
        impact="High",
    )

    assert set(result.factors.keys()) == {
        "condition",
        "issue",
        "delay",
        "impact",
    }

    assert result.factors["condition"] == 70.0
    assert result.factors["issue"] == 55.0
    assert result.factors["delay"] == 40.0
    assert result.factors["impact"] == 75.0


def test_all_factor_scores_are_within_range():
    """Every exposed factor score must stay inside 0-100."""

    result = calculate_severity(
        condition="Critical",
        issue="Damaged Structure",
        delay=1000,
        impact=1000,
    )

    for value in result.factors.values():
        assert 0.0 <= value <= 100.0


# ============================================================
# Explanation Tests
# ============================================================


def test_explanation_contains_severity_and_score():
    """Explanation should contain useful human-readable information."""

    result = calculate_severity(
        condition="Poor",
    )

    assert "High" in result.explanation
    assert "70.00/100" in result.explanation


def test_explanation_lists_supplied_factors():
    """Explanation should identify the supplied scoring factors."""

    result = calculate_severity(
        condition="Poor",
        issue="Pothole",
    )

    assert "condition" in result.explanation
    assert "issue" in result.explanation


def test_explanation_does_not_claim_missing_factors():
    """Only supplied factors should appear in the explanation."""

    result = calculate_severity(
        condition="Poor",
    )

    assert "condition" in result.explanation
    assert "issue" not in result.explanation
    assert "delay" not in result.explanation
    assert "impact" not in result.explanation


# ============================================================
# Result Immutability
# ============================================================


def test_severity_result_is_immutable():
    """SeverityResult is a frozen dataclass and should not be mutable."""

    result = calculate_severity(
        condition="Poor",
    )

    with pytest.raises(
        AttributeError,
    ):
        result.score = 50.0


# ============================================================
# Convenience Wrapper
# ============================================================


def test_score_severity_returns_dictionary():
    """score_severity should return a JSON-friendly dictionary."""

    result = score_severity(
        condition="Poor",
        issue="Pothole",
        delay=20,
        impact="High",
    )

    assert isinstance(
        result,
        dict,
    )


def test_score_severity_contains_expected_keys():
    """Wrapper output must contain the public API fields."""

    result = score_severity(
        condition="Poor",
        issue="Pothole",
    )

    assert set(result.keys()) == {
        "score",
        "severity",
        "explanation",
        "factors",
    }


def test_score_severity_returns_string_severity():
    """JSON-friendly output should expose severity as a string."""

    result = score_severity(
        condition="Critical",
    )

    assert result["severity"] == "High"


def test_score_severity_returns_serializable_factor_dict():
    """Factors should be a normal dictionary."""

    result = score_severity(
        condition="Poor",
        issue="Pothole",
        delay=20,
        impact="High",
    )

    assert isinstance(
        result["factors"],
        dict,
    )

    for value in result["factors"].values():
        assert isinstance(
            value,
            float,
        )


# ============================================================
# Regression Tests
# ============================================================


@pytest.mark.parametrize(
    (
        "condition",
        "issue",
        "delay",
        "impact",
    ),
    [
        ("Good", "Crack", 0, "low"),
        ("Fair", "Pothole", 10, "medium"),
        ("Poor", "Road Damage", 20, "high"),
        ("Critical", "Damaged Structure", 50, "critical"),
        ("Unknown", "Other", None, None),
    ],
)
def test_calculation_is_deterministic(
    condition,
    issue,
    delay,
    impact,
):
    """Repeated calculations with identical input must match."""

    first = calculate_severity(
        condition=condition,
        issue=issue,
        delay=delay,
        impact=impact,
    )

    second = calculate_severity(
        condition=condition,
        issue=issue,
        delay=delay,
        impact=impact,
    )

    assert first == second


@pytest.mark.parametrize(
    "condition",
    [
        ConditionLevel.GOOD,
        ConditionLevel.FAIR,
        ConditionLevel.POOR,
        ConditionLevel.CRITICAL,
        ConditionLevel.UNKNOWN,
    ],
)
def test_every_condition_produces_valid_result(
    condition,
):
    """Every supported condition must produce a valid result."""

    result = calculate_severity(
        condition=condition,
    )

    assert 0.0 <= result.score <= 100.0
    assert result.severity in {
        SeverityLevel.LOW,
        SeverityLevel.MEDIUM,
        SeverityLevel.HIGH,
    }


@pytest.mark.parametrize(
    "issue",
    list(IssueType),
)
def test_every_issue_type_produces_valid_result(
    issue,
):
    """Every supported issue type must produce a valid result."""

    result = calculate_severity(
        issue=issue,
    )

    assert 0.0 <= result.score <= 100.0
    assert result.severity in {
        SeverityLevel.LOW,
        SeverityLevel.MEDIUM,
        SeverityLevel.HIGH,
    }