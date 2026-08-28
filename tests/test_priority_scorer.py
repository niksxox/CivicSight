"""
Tests for CivicSight deterministic priority scoring service.

No external APIs, LLMs, databases, or FastAPI components are used.

Coverage:
- normalization helpers
- all seven priority factors
- fixed weights
- priority boundaries
- recommended actions
- complete weighted scoring
- missing factors
- invalid inputs
- score clamping
- PriorityResult
- JSON-friendly score_priority()
- deterministic/repeatable behavior
"""

from __future__ import annotations

import json

import pytest

from app.services.priority_scorer import (
    CONDITION_WEIGHT,
    DELAY_WEIGHT,
    DURATION_WEIGHT,
    HISTORICAL_WEIGHT,
    IMPORTANCE_WEIGHT,
    POPULATION_WEIGHT,
    SEVERITY_WEIGHT,
    TOTAL_WEIGHT,
    PriorityResult,
    _clamp_score,
    _normalize_condition,
    _normalize_delay,
    _normalize_duration,
    _normalize_historical_data,
    _normalize_importance,
    _normalize_population,
    _normalize_severity,
    _normalize_text,
    _round_score,
    calculate_priority,
    classify_priority,
    recommend_action,
    score_priority,
)
from app.utils.constants import (
    ConditionLevel,
    PriorityLevel,
    SeverityLevel,
)


# ============================================================
# Normalization Helpers
# ============================================================


def test_normalize_text_with_string():
    """Strings should be stripped and lowercased."""

    assert _normalize_text("  HIGH  ") == "high"


def test_normalize_text_with_enum():
    """Enums should be normalized using their value."""

    assert _normalize_text(
        PriorityLevel.CRITICAL
    ) == "critical"


def test_normalize_text_with_none():
    """None should normalize to an empty string."""

    assert _normalize_text(None) == ""


def test_normalize_text_with_number():
    """Numbers should become normalized strings."""

    assert _normalize_text(25) == "25"


# ============================================================
# Generic Score Helpers
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
    """Priority scores must remain inside 0..100."""

    assert _clamp_score(value) == expected


def test_round_score_rounds_to_two_decimals():
    """Final scores should be rounded to two decimal places."""

    assert _round_score(25.1234) == 25.12
    assert _round_score(66.6666) == 66.67


def test_round_score_clamps_before_returning():
    """Rounded values must still remain inside 0..100."""

    assert _round_score(-5.5) == 0.0
    assert _round_score(105.5) == 100.0


# ============================================================
# Weight Tests
# ============================================================


def test_total_weight_is_exactly_one():
    """All seven weights must sum to exactly 1.0."""

    assert TOTAL_WEIGHT == pytest.approx(1.0)


def test_individual_weights_match_design():
    """Verify the fixed scoring model weights."""

    assert DELAY_WEIGHT == 0.20
    assert CONDITION_WEIGHT == 0.20
    assert POPULATION_WEIGHT == 0.15
    assert IMPORTANCE_WEIGHT == 0.15
    assert SEVERITY_WEIGHT == 0.15
    assert DURATION_WEIGHT == 0.10
    assert HISTORICAL_WEIGHT == 0.05


# ============================================================
# Delay Normalization
# ============================================================


@pytest.mark.parametrize(
    ("delay", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (0.0, 0.0),
        (10, 20.0),
        (25, 50.0),
        (50, 100.0),
        (100, 100.0),
    ],
)
def test_normalize_delay(delay, expected):
    """Delay percentages should map to bounded severity scores."""

    assert _normalize_delay(delay) == expected


def test_normalize_delay_accepts_numeric_string():
    """Numeric strings should be accepted."""

    assert _normalize_delay("25") == 50.0


def test_normalize_delay_clamps_large_delay():
    """Delay above 50% should remain capped at 100."""

    assert _normalize_delay(500) == 100.0


@pytest.mark.parametrize(
    "delay",
    [
        -1,
        -10,
        -100,
    ],
)
def test_normalize_delay_rejects_negative_values(delay):
    """Negative delay is invalid."""

    with pytest.raises(ValueError):
        _normalize_delay(delay)


@pytest.mark.parametrize(
    "delay",
    [
        "invalid",
        "abc",
        [],
        {},
        True,
        False,
    ],
)
def test_normalize_delay_rejects_invalid_values(delay):
    """Invalid delay values should not silently become zero."""

    with pytest.raises(ValueError):
        _normalize_delay(delay)


# ============================================================
# Condition Normalization
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
        (" FAIR ", 35.0),
        ("POOR", 70.0),
        ("critical", 100.0),
    ],
)
def test_normalize_condition(condition, expected):
    """Known condition values should map correctly."""

    assert _normalize_condition(condition) == expected


def test_normalize_condition_none_returns_zero():
    """Missing condition should contribute zero to priority."""

    assert _normalize_condition(None) == 0.0


def test_normalize_unknown_condition_returns_neutral():
    """Unknown textual condition should receive the neutral score."""

    assert _normalize_condition(
        "something unknown"
    ) == 40.0


# ============================================================
# Population Normalization
# ============================================================


@pytest.mark.parametrize(
    ("population", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (1, 20.0),
        (100, 20.0),
        (101, 40.0),
        (500, 40.0),
        (501, 60.0),
        (1000, 60.0),
        (1001, 80.0),
        (5000, 80.0),
        (5001, 100.0),
        (100000, 100.0),
    ],
)
def test_normalize_population(population, expected):
    """Population thresholds must follow the fixed mapping."""

    assert _normalize_population(population) == expected


def test_normalize_population_accepts_numeric_string():
    """Numeric population strings should be accepted."""

    assert _normalize_population("500") == 40.0


@pytest.mark.parametrize(
    "population",
    [
        -1,
        -100,
    ],
)
def test_normalize_population_rejects_negative_values(
    population,
):
    """Negative population values are invalid."""

    with pytest.raises(ValueError):
        _normalize_population(population)


@pytest.mark.parametrize(
    "population",
    [
        "invalid",
        True,
        False,
        [],
        {},
    ],
)
def test_normalize_population_rejects_invalid_values(
    population,
):
    """Invalid population values should raise ValueError."""

    with pytest.raises(ValueError):
        _normalize_population(population)


# ============================================================
# Importance Normalization
# ============================================================


@pytest.mark.parametrize(
    ("importance", "expected"),
    [
        (None, 0.0),
        ("low", 25.0),
        ("medium", 50.0),
        ("high", 75.0),
        ("critical", 100.0),
        ("LOW", 25.0),
        (" High ", 75.0),
        (0, 0.0),
        (50, 50.0),
        (100, 100.0),
    ],
)
def test_normalize_importance(importance, expected):
    """Project importance should follow its documented mapping."""

    assert _normalize_importance(
        importance
    ) == expected


def test_normalize_importance_accepts_numeric_string():
    """Numeric importance strings should be accepted."""

    assert _normalize_importance("80") == 80.0


def test_normalize_importance_clamps_numeric_values():
    """Numeric importance should be bounded to 0..100."""

    assert _normalize_importance(150) == 100.0
    assert _normalize_importance(-10) == 0.0


def test_normalize_importance_rejects_boolean():
    """Boolean values are not valid numeric importance."""

    with pytest.raises(ValueError):
        _normalize_importance(True)


def test_normalize_importance_unknown_text_is_neutral():
    """Unknown importance text should use 50."""

    assert _normalize_importance(
        "something unknown"
    ) == 50.0


# ============================================================
# Severity Normalization
# ============================================================


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (None, 0.0),
        (SeverityLevel.LOW, 20.0),
        (SeverityLevel.MEDIUM, 55.0),
        (SeverityLevel.HIGH, 100.0),
        ("low", 20.0),
        ("medium", 55.0),
        ("high", 100.0),
        ("LOW", 20.0),
    ],
)
def test_normalize_severity(severity, expected):
    """Severity levels should map to the defined scores."""

    assert _normalize_severity(
        severity
    ) == expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (0, 0.0),
        (50, 50.0),
        (100, 100.0),
        ("75", 75.0),
    ],
)
def test_normalize_numeric_severity(severity, expected):
    """Numeric severity is accepted as an integration convenience."""

    assert _normalize_severity(
        severity
    ) == expected


def test_normalize_severity_unknown_text_is_neutral():
    """Unknown severity text should default to 55."""

    assert _normalize_severity(
        "unknown severity"
    ) == 55.0


# ============================================================
# Duration Normalization
# ============================================================


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (30, 30.0),
        (90, 60.0),
        (180, 80.0),
        (365, 100.0),
        (500, 100.0),
    ],
)
def test_normalize_duration_numeric(duration, expected):
    """Numeric durations are interpreted as days."""

    assert _normalize_duration(
        duration
    ) == expected


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        ("0 days", 0.0),
        ("30 days", 30.0),
        ("90 days", 60.0),
        ("180 days", 80.0),
        ("365 days", 100.0),
        ("1 week", 7.0),
        ("2 weeks", 14.0),
        ("1 month", 30.0),
        ("2 months", 60.0),
        ("1 year", 100.0),
    ],
)
def test_normalize_duration_text(duration, expected):
    """Supported duration strings should be converted deterministically."""

    assert _normalize_duration(
        duration
    ) == expected


def test_normalize_duration_accepts_numeric_string():
    """A plain numeric string is interpreted as days."""

    assert _normalize_duration("30") == 30.0


@pytest.mark.parametrize(
    "duration",
    [
        -1,
        -10,
    ],
)
def test_normalize_duration_rejects_negative_numeric(duration):
    """Negative duration is invalid."""

    with pytest.raises(ValueError):
        _normalize_duration(duration)


def test_normalize_duration_rejects_negative_numeric_string():
    """Negative numeric strings are invalid."""

    with pytest.raises(ValueError):
        _normalize_duration("-30")


@pytest.mark.parametrize(
    "duration",
    [
        "unknown duration",
        "abc",
        "30 hours",
    ],
)
def test_normalize_duration_unknown_text_returns_neutral(
    duration,
):
    """Unsupported duration text should use the neutral score."""

    assert _normalize_duration(
        duration
    ) == 50.0


# ============================================================
# Historical Data Normalization
# ============================================================


@pytest.mark.parametrize(
    ("historical", "expected"),
    [
        (None, 0.0),
        (0, 0.0),
        (25, 25.0),
        (50, 50.0),
        (100, 100.0),
        ("none", 0.0),
        ("no history", 0.0),
        ("low", 25.0),
        ("medium", 50.0),
        ("high", 75.0),
        ("critical", 100.0),
        ("recurring", 75.0),
        ("repeated", 100.0),
    ],
)
def test_normalize_historical_data(
    historical,
    expected,
):
    """Supported historical-data forms should map correctly."""

    assert _normalize_historical_data(
        historical
    ) == expected


def test_normalize_historical_boolean_true():
    """True represents recurring historical issues."""

    assert _normalize_historical_data(True) == 75.0


def test_normalize_historical_boolean_false():
    """False represents no recurring historical issue."""

    assert _normalize_historical_data(False) == 0.0


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"previous_incidents": 0}, 0.0),
        ({"previous_incidents": 1}, 25.0),
        ({"previous_incidents": 2}, 50.0),
        ({"previous_incidents": 3}, 75.0),
        ({"previous_incidents": 4}, 100.0),
        ({"repeat_count": 1}, 25.0),
        ({"repeat_count": 4}, 100.0),
        ({"recurring": True}, 75.0),
    ],
)
def test_normalize_historical_mapping(
    data,
    expected,
):
    """Mapping-based historical information should be supported."""

    assert _normalize_historical_data(
        data
    ) == expected


def test_unknown_historical_mapping_is_neutral():
    """A mapping without recognized history fields should be neutral."""

    assert _normalize_historical_data(
        {"unknown": "value"}
    ) == 50.0


def test_unknown_historical_text_is_neutral():
    """Unknown historical text should use a neutral score."""

    assert _normalize_historical_data(
        "unknown history"
    ) == 50.0


# ============================================================
# Priority Classification
# ============================================================


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, PriorityLevel.LOW),
        (10.0, PriorityLevel.LOW),
        (24.99, PriorityLevel.LOW),
        (25.0, PriorityLevel.MEDIUM),
        (49.99, PriorityLevel.MEDIUM),
        (50.0, PriorityLevel.HIGH),
        (74.99, PriorityLevel.HIGH),
        (75.0, PriorityLevel.CRITICAL),
        (100.0, PriorityLevel.CRITICAL),
    ],
)
def test_classify_priority_boundaries(
    score,
    expected,
):
    """Priority classification must follow shared project boundaries."""

    assert classify_priority(
        score
    ) == expected


def test_classify_priority_clamps_negative_score():
    """Negative scores should classify as Low."""

    assert classify_priority(
        -100
    ) == PriorityLevel.LOW


def test_classify_priority_clamps_score_above_100():
    """Scores above 100 should classify as Critical."""

    assert classify_priority(
        500
    ) == PriorityLevel.CRITICAL


# ============================================================
# Recommended Actions
# ============================================================


@pytest.mark.parametrize(
    ("priority", "expected"),
    [
        (
            PriorityLevel.LOW,
            "Routine monitoring and maintenance.",
        ),
        (
            PriorityLevel.MEDIUM,
            "Schedule inspection and maintenance.",
        ),
        (
            PriorityLevel.HIGH,
            "Prioritize inspection and corrective action.",
        ),
        (
            PriorityLevel.CRITICAL,
            "Immediate inspection and urgent corrective action.",
        ),
    ],
)
def test_recommend_action(
    priority,
    expected,
):
    """Every priority level should have its defined action."""

    assert recommend_action(
        priority
    ) == expected


def test_recommend_action_accepts_string():
    """String priority values should also be accepted."""

    assert recommend_action(
        "critical"
    ) == "Immediate inspection and urgent corrective action."


def test_recommend_action_is_case_insensitive():
    """Priority action lookup should normalize text."""

    assert recommend_action(
        " HIGH "
    ) == "Prioritize inspection and corrective action."


def test_recommend_action_unknown_value_uses_fallback():
    """Unknown priority values should use the safe fallback action."""

    result = recommend_action(
        "unknown"
    )

    assert result == (
        "Review the issue and determine appropriate action."
    )


# ============================================================
# Main Priority Calculation
# ============================================================


def test_calculate_priority_returns_priority_result():
    """calculate_priority should return the declared dataclass."""

    result = calculate_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert isinstance(
        result,
        PriorityResult,
    )


def test_calculate_priority_with_all_factors():
    """
    Verify the complete seven-factor weighted calculation.

    Factor scores:
        delay       = 40
        condition   = 70
        population  = 40
        importance  = 75
        severity    = 100
        duration    = 60
        historical  = 50

    Weighted:
        40*.20
      + 70*.20
      + 40*.15
      + 75*.15
      + 100*.15
      + 60*.10
      + 50*.05

      = 8 + 14 + 6 + 11.25 + 15 + 6 + 2.5
      = 62.75
    """

    result = calculate_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert result.score == 62.75
    assert result.priority == PriorityLevel.HIGH


def test_calculate_priority_all_maximum_factors():
    """All maximum inputs should produce exactly 100."""

    result = calculate_priority(
        project_delay=100,
        infrastructure_condition="Critical",
        population_affected=100000,
        project_importance="Critical",
        issue_severity="High",
        duration="10 years",
        historical_data=100,
    )

    assert result.score == 100.0
    assert result.priority == PriorityLevel.CRITICAL


def test_calculate_priority_no_factors():
    """Missing factors should contribute zero."""

    result = calculate_priority()

    assert result.score == 0.0
    assert result.priority == PriorityLevel.LOW

    assert result.recommended_action == (
        "Routine monitoring and maintenance."
    )


def test_calculate_priority_single_condition():
    """A single supplied factor should retain its fixed weight."""

    result = calculate_priority(
        infrastructure_condition="Critical",
    )

    # 100 * 0.20 = 20
    assert result.score == 20.0
    assert result.priority == PriorityLevel.LOW


def test_calculate_priority_single_issue_severity():
    """A single severity factor should use its fixed weight."""

    result = calculate_priority(
        issue_severity="High",
    )

    # 100 * 0.15 = 15
    assert result.score == 15.0
    assert result.priority == PriorityLevel.LOW


def test_calculate_priority_single_population():
    """Population factor should use its fixed weight."""

    result = calculate_priority(
        population_affected=5001,
    )

    # 100 * 0.15 = 15
    assert result.score == 15.0
    assert result.priority == PriorityLevel.LOW


def test_calculate_priority_single_importance():
    """Importance factor should use its fixed weight."""

    result = calculate_priority(
        project_importance="Critical",
    )

    # 100 * 0.15 = 15
    assert result.score == 15.0
    assert result.priority == PriorityLevel.LOW


def test_calculate_priority_single_duration():
    """Duration factor should use its fixed weight."""

    result = calculate_priority(
        duration="1 year",
    )

    # 100 * 0.10 = 10
    assert result.score == 10.0
    assert result.priority == PriorityLevel.LOW


def test_calculate_priority_single_historical_factor():
    """Historical factor should use its fixed weight."""

    result = calculate_priority(
        historical_data=100,
    )

    # 100 * 0.05 = 5
    assert result.score == 5.0
    assert result.priority == PriorityLevel.LOW


# ============================================================
# Factor Dictionary
# ============================================================


def test_result_contains_all_seven_factors():
    """PriorityResult must expose all seven normalized factors."""

    result = calculate_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert set(result.factors.keys()) == {
        "project_delay",
        "infrastructure_condition",
        "population_affected",
        "project_importance",
        "issue_severity",
        "duration",
        "historical_data",
    }


def test_result_factor_values_are_normalized():
    """Factors should expose normalized 0-100 values."""

    result = calculate_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert result.factors["project_delay"] == 40.0
    assert result.factors["infrastructure_condition"] == 70.0
    assert result.factors["population_affected"] == 40.0
    assert result.factors["project_importance"] == 75.0
    assert result.factors["issue_severity"] == 100.0
    assert result.factors["duration"] == 60.0
    assert result.factors["historical_data"] == 50.0


def test_all_factor_values_are_within_range():
    """No factor exposed by the result may exceed 0..100."""

    result = calculate_priority(
        project_delay=1000,
        infrastructure_condition="Critical",
        population_affected=1000000,
        project_importance=1000,
        issue_severity=1000,
        duration="100 years",
        historical_data=1000,
    )

    for value in result.factors.values():
        assert 0.0 <= value <= 100.0


# ============================================================
# Priority Result Contract
# ============================================================


def test_priority_result_is_frozen():
    """PriorityResult should be immutable."""

    result = calculate_priority(
        project_delay=20,
    )

    with pytest.raises(
        AttributeError,
    ):
        result.score = 99.0


def test_priority_result_has_expected_fields():
    """Result structure must remain stable for backend integration."""

    result = calculate_priority(
        project_delay=20,
    )

    assert hasattr(result, "score")
    assert hasattr(result, "priority")
    assert hasattr(result, "recommended_action")
    assert hasattr(result, "factors")


# ============================================================
# JSON-Friendly Wrapper
# ============================================================


def test_score_priority_returns_dict():
    """score_priority should return a normal dictionary."""

    result = score_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert isinstance(
        result,
        dict,
    )


def test_score_priority_has_frontend_safe_keys():
    """Wrapper should expose the documented API-friendly fields."""

    result = score_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    assert set(result.keys()) == {
        "priority_score",
        "priority",
        "recommended_action",
        "factors",
    }


def test_score_priority_returns_string_priority():
    """Priority enum should be converted to its string value."""

    result = score_priority(
        infrastructure_condition="Critical",
    )

    assert isinstance(
        result["priority"],
        str,
    )

    assert result["priority"] == "Low"


def test_score_priority_returns_numeric_score():
    """Priority score should be JSON-compatible numeric data."""

    result = score_priority(
        project_importance="Critical",
        issue_severity="High",
    )

    assert isinstance(
        result["priority_score"],
        float,
    )


def test_score_priority_can_be_json_serialized():
    """Wrapper output should be directly JSON serializable."""

    result = score_priority(
        project_delay=20,
        infrastructure_condition="Poor",
        population_affected=500,
        project_importance="High",
        issue_severity="High",
        duration="3 months",
        historical_data="medium",
    )

    encoded = json.dumps(result)
    decoded = json.loads(encoded)

    assert decoded == result


# ============================================================
# Error Handling / Integration Safety
# ============================================================


def test_calculate_priority_rejects_negative_delay():
    """Invalid negative delay must not silently produce a result."""

    with pytest.raises(ValueError):
        calculate_priority(
            project_delay=-10,
        )


def test_calculate_priority_rejects_negative_population():
    """Negative population cannot be a valid factor."""

    with pytest.raises(ValueError):
        calculate_priority(
            population_affected=-100,
        )


def test_calculate_priority_rejects_negative_duration():
    """Negative duration cannot be valid."""

    with pytest.raises(ValueError):
        calculate_priority(
            duration=-30,
        )


def test_calculate_priority_rejects_boolean_delay():
    """Boolean delay must not be treated as numeric data."""

    with pytest.raises(ValueError):
        calculate_priority(
            project_delay=True,
        )


def test_calculate_priority_rejects_boolean_importance():
    """Boolean importance must not be accepted as numeric data."""

    with pytest.raises(ValueError):
        calculate_priority(
            project_importance=True,
        )


def test_calculate_priority_rejects_boolean_duration():
    """Boolean duration must not be accepted."""

    with pytest.raises(ValueError):
        calculate_priority(
            duration=True,
        )


# ============================================================
# Boundary Regression Tests
# ============================================================


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (24.99, PriorityLevel.LOW),
        (25.00, PriorityLevel.MEDIUM),
        (49.99, PriorityLevel.MEDIUM),
        (50.00, PriorityLevel.HIGH),
        (74.99, PriorityLevel.HIGH),
        (75.00, PriorityLevel.CRITICAL),
    ],
)
def test_exact_priority_boundaries(
    score,
    expected,
):
    """Exact priority thresholds must never shift."""

    assert classify_priority(
        score
    ) == expected


@pytest.mark.parametrize(
    "inputs",
    [
        {
            "project_delay": 20,
            "infrastructure_condition": "Poor",
            "population_affected": 500,
            "project_importance": "High",
            "issue_severity": "High",
            "duration": "3 months",
            "historical_data": "medium",
        },
        {
            "project_delay": 50,
            "infrastructure_condition": "Critical",
            "population_affected": 5001,
            "project_importance": "Critical",
            "issue_severity": "High",
            "duration": "1 year",
            "historical_data": "repeated",
        },
        {
            "project_delay": 0,
            "infrastructure_condition": "Good",
            "population_affected": 0,
            "project_importance": "low",
            "issue_severity": "low",
            "duration": 0,
            "historical_data": "none",
        },
    ],
)
def test_priority_calculation_is_deterministic(inputs):
    """Identical inputs must always produce identical results."""

    first = calculate_priority(**inputs)
    second = calculate_priority(**inputs)

    assert first == second


# ============================================================
# Public API Consistency
# ============================================================


def test_score_priority_matches_calculate_priority():
    """The convenience wrapper must not alter the calculation."""

    kwargs = {
        "project_delay": 20,
        "infrastructure_condition": "Poor",
        "population_affected": 500,
        "project_importance": "High",
        "issue_severity": "High",
        "duration": "3 months",
        "historical_data": "medium",
    }

    result = calculate_priority(**kwargs)
    wrapped = score_priority(**kwargs)

    assert wrapped["priority_score"] == result.score
    assert wrapped["priority"] == result.priority.value
    assert wrapped["recommended_action"] == (
        result.recommended_action
    )
    assert wrapped["factors"] == result.factors