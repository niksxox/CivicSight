

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping
import re

from app.models.priority_models import PriorityAssessmentResponse
from app.utils.constants import (
    ConditionLevel,
    MAX_SCORE,
    MIN_SCORE,
    PriorityLevel,
    PRIORITY_CRITICAL_MIN,
    PRIORITY_HIGH_MAX,
    PRIORITY_LOW_MAX,
    PRIORITY_MEDIUM_MAX,
    SeverityLevel,
)



# Scoring weights

DELAY_WEIGHT = 0.20
CONDITION_WEIGHT = 0.20
POPULATION_WEIGHT = 0.15
IMPORTANCE_WEIGHT = 0.15
SEVERITY_WEIGHT = 0.15
DURATION_WEIGHT = 0.10
HISTORICAL_WEIGHT = 0.05

TOTAL_WEIGHT = (
    DELAY_WEIGHT
    + CONDITION_WEIGHT
    + POPULATION_WEIGHT
    + IMPORTANCE_WEIGHT
    + SEVERITY_WEIGHT
    + DURATION_WEIGHT
    + HISTORICAL_WEIGHT
)

if abs(TOTAL_WEIGHT - 1.0) > 1e-9:
    raise RuntimeError(
        "Priority scoring weights must sum to exactly 1.0."
    )


# Exceptions


class PriorityScoringError(Exception):
    """Base priority-scoring exception."""


class InvalidPriorityInputError(
    PriorityScoringError,
    ValueError,
):
    """Raised when priority input is invalid."""


# General helpers


def _normalize_text(value: Any) -> str:
    """
    Normalize strings and Enum values.

    Examples:
        " HIGH " -> "high"
        PriorityLevel.HIGH -> "high"
        "damaged_structure" -> "damaged structure"
        None -> ""
    """

    if value is None:
        return ""

    if hasattr(value, "value"):
        value = value.value

    text = str(value)

    text = text.replace(
        "_",
        " ",
    )

    return " ".join(
        text.strip().lower().split()
    )


def _clamp_score(
    value: Any,
) -> float:
    """
    Clamp a score to the global 0-100 range.
    """

    try:
        numeric = float(value)

    except (TypeError, ValueError) as exc:
        raise InvalidPriorityInputError(
            f"Invalid numeric score: {value!r}."
        ) from exc

    if not isfinite(numeric):
        raise InvalidPriorityInputError(
            f"Score must be finite: {value!r}."
        )

    return max(
        MIN_SCORE,
        min(
            MAX_SCORE,
            numeric,
        ),
    )


def _round_score(
    value: Any,
) -> float:
    """Clamp and round a score to two decimal places."""

    return round(
        _clamp_score(value),
        2,
    )


def _to_non_negative_float(
    value: Any,
    *,
    field_name: str,
) -> float:
    """
    Convert a value to a finite non-negative float.
    """

    if isinstance(
        value,
        bool,
    ):
        raise InvalidPriorityInputError(
            f"{field_name} cannot be a boolean."
        )

    try:
        numeric = float(value)

    except (TypeError, ValueError) as exc:
        raise InvalidPriorityInputError(
            f"{field_name} must be numeric."
        ) from exc

    if not isfinite(numeric):
        raise InvalidPriorityInputError(
            f"{field_name} must be finite."
        )

    if numeric < 0:
        raise InvalidPriorityInputError(
            f"{field_name} cannot be negative."
        )

    return numeric


# Delay normalization



def _normalize_delay(
    delay: Any,
) -> float:
    """
    Convert project delay percentage into 0-100.

    Mapping:

        0%   -> 0
        10%  -> 20
        25%  -> 50
        50%  -> 100
        >50% -> 100
    """

    if delay is None:
        return 0.0

    numeric_delay = _to_non_negative_float(
        delay,
        field_name="project_delay",
    )

    return _clamp_score(
        numeric_delay * 2.0
    )


# Condition normalization


def _normalize_condition(
    condition: Any,
) -> float:
    """
    Convert infrastructure condition into 0-100.

    Mapping:

        Good      -> 10
        Fair      -> 35
        Poor      -> 70
        Critical  -> 100
        Unknown   -> 40

    Missing condition contributes 0.
    """

    if condition is None:
        return 0.0

    normalized = _normalize_text(
        condition
    )

    mapping = {
        _normalize_text(
            ConditionLevel.GOOD
        ): 10.0,

        _normalize_text(
            ConditionLevel.FAIR
        ): 35.0,

        _normalize_text(
            ConditionLevel.POOR
        ): 70.0,

        _normalize_text(
            ConditionLevel.CRITICAL
        ): 100.0,

        _normalize_text(
            ConditionLevel.UNKNOWN
        ): 40.0,
    }

    if normalized in mapping:
        return mapping[normalized]

    return 40.0


# Population normalization


def _normalize_population(
    population_affected: Any,
) -> float:
    """
    Convert affected population into 0-100.

    Mapping:

        0           -> 0
        1-100       -> 20
        101-500     -> 40
        501-1000    -> 60
        1001-5000   -> 80
        >5000       -> 100
    """

    if population_affected is None:
        return 0.0

    population = _to_non_negative_float(
        population_affected,
        field_name="population_affected",
    )

    if population == 0:
        return 0.0

    if population <= 100:
        return 20.0

    if population <= 500:
        return 40.0

    if population <= 1000:
        return 60.0

    if population <= 5000:
        return 80.0

    return 100.0


# Importance normalization


def _normalize_importance(
    project_importance: Any,
) -> float:
    """
    Convert project importance into 0-100.

    Supported text:

        low       -> 25
        medium    -> 50
        high      -> 75
        critical  -> 100

    Numeric values:

        0-100
    """

    if project_importance is None:
        return 0.0

    if isinstance(
        project_importance,
        bool,
    ):
        raise InvalidPriorityInputError(
            "project_importance cannot be a boolean."
        )

    if isinstance(
        project_importance,
        (int, float),
    ):
        return _clamp_score(
            project_importance
        )

    normalized = _normalize_text(
        project_importance
    )

    mapping = {
        "low": 25.0,
        "medium": 50.0,
        "high": 75.0,
        "critical": 100.0,
    }

    if normalized in mapping:
        return mapping[normalized]

    try:
        return _clamp_score(
            float(normalized)
        )

    except (
        TypeError,
        ValueError,
    ):
        return 50.0


# Severity normalization


def _normalize_severity(
    issue_severity: Any,
) -> float:
    """
    Convert issue severity into 0-100.

    Mapping:

        Low     -> 20
        Medium  -> 55
        High    -> 100

    Numeric values between 0 and 100
    are also accepted.
    """

    if issue_severity is None:
        return 0.0

    if isinstance(
        issue_severity,
        bool,
    ):
        raise InvalidPriorityInputError(
            "issue_severity cannot be a boolean."
        )

    if isinstance(
        issue_severity,
        (int, float),
    ):
        return _clamp_score(
            issue_severity
        )

    normalized = _normalize_text(
        issue_severity
    )

    mapping = {
        _normalize_text(
            SeverityLevel.LOW
        ): 20.0,

        _normalize_text(
            SeverityLevel.MEDIUM
        ): 55.0,

        _normalize_text(
            SeverityLevel.HIGH
        ): 100.0,
    }

    if normalized in mapping:
        return mapping[normalized]

    try:
        return _clamp_score(
            float(normalized)
        )

    except (
        TypeError,
        ValueError,
    ):
        return 55.0


# Duration normalization


def _duration_days_to_score(
    days: float,
) -> float:
    """
    Convert duration in days into 0-100.

    Mapping:

        0 days      -> 0
        30 days     -> 30
        90 days     -> 60
        180 days    -> 80
        365+ days   -> 100
    """

    if days <= 0:
        return 0.0

    if days <= 30:
        return round(
            (days / 30.0) * 30.0,
            2,
        )

    if days <= 90:
        return round(
            30.0
            + (
                (days - 30.0)
                / 60.0
            )
            * 30.0,
            2,
        )

    if days <= 180:
        return round(
            60.0
            + (
                (days - 90.0)
                / 90.0
            )
            * 20.0,
            2,
        )

    if days <= 365:
        return round(
            80.0
            + (
                (days - 180.0)
                / 185.0
            )
            * 20.0,
            2,
        )

    return 100.0


def _normalize_duration(
    duration: Any,
) -> float:
    """
    Convert duration into a 0-100 score.

    Supported:

        numeric
            interpreted as days

        "30 days"
        "2 weeks"
        "4 months"
        "1 year"

    Important contract:

        1 month = 30 days
        1 year  = 365 days

    Negative numeric values and negative numeric strings
    raise InvalidPriorityInputError, which is also a ValueError.
    """

    if duration is None:
        return 0.0

    if isinstance(
        duration,
        bool,
    ):
        raise InvalidPriorityInputError(
            "duration cannot be a boolean."
        )

    # Numeric duration

    if isinstance(
        duration,
        (int, float),
    ):
        days = _to_non_negative_float(
            duration,
            field_name="duration",
        )

        return _duration_days_to_score(
            days
        )

    # Normalize string

    normalized = _normalize_text(
        duration
    )

    if not normalized:
        return 0.0

    # Numeric string
    #
    # Must be handled BEFORE unit parsing so:
    #
    #     "-10"
    #
    # raises instead of becoming neutral 50.

    numeric_match = re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)",
        normalized,
    )

    if numeric_match is not None:

        try:
            days = float(
                normalized
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise InvalidPriorityInputError(
                "duration must be numeric."
            ) from exc

        if not isfinite(days):
            raise InvalidPriorityInputError(
                "duration must be finite."
            )

        if days < 0:
            raise InvalidPriorityInputError(
                "duration cannot be negative."
            )

        return _duration_days_to_score(
            days
        )

    # Unit-based duration

    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*"
        r"(day|days|week|weeks|month|months|year|years)",
        normalized,
    )

    if match is None:
        return 50.0

    amount = float(
        match.group(1)
    )

    if not isfinite(amount):
        raise InvalidPriorityInputError(
            "duration must be finite."
        )

    if amount < 0:
        raise InvalidPriorityInputError(
            "duration cannot be negative."
        )

    unit = match.group(2)

    # Convert to days

    if unit in {
        "day",
        "days",
    }:

        days = amount

    elif unit in {
        "week",
        "weeks",
    }:

        days = amount * 7.0

    elif unit in {
        "month",
        "months",
    }:

        # Fixed CivicSight conversion.
        # 1 month = 30 days.
        days = amount * 30.0

    elif unit in {
        "year",
        "years",
    }:

        # Fixed CivicSight conversion.
        # 1 year = 365 days.
        days = amount * 365.0

    else:
        raise InvalidPriorityInputError(
            f"Unsupported duration unit: {unit!r}."
        )

    return _duration_days_to_score(
        days
    )


# Historical normalization


def _normalize_historical_data(
    historical_data: Any,
) -> float:
    """
    Convert historical issue information into 0-100.
    """

    if historical_data is None:
        return 0.0

    if isinstance(
        historical_data,
        bool,
    ):
        return (
            75.0
            if historical_data
            else 0.0
        )

    if isinstance(
        historical_data,
        (int, float),
    ):
        return _clamp_score(
            historical_data
        )

    if isinstance(
        historical_data,
        Mapping,
    ):

        recurring = historical_data.get(
            "recurring"
        )

        if (
            isinstance(
                recurring,
                bool,
            )
            and recurring
        ):
            return 75.0

        repeat_count = historical_data.get(
            "repeat_count",
            historical_data.get(
                "previous_incidents"
            ),
        )

        if repeat_count is not None:

            count = _to_non_negative_float(
                repeat_count,
                field_name="repeat_count",
            )

            if count == 0:
                return 0.0

            if count == 1:
                return 25.0

            if count == 2:
                return 50.0

            if count == 3:
                return 75.0

            return 100.0

        return 50.0

    normalized = _normalize_text(
        historical_data
    )

    mapping = {
        "none": 0.0,
        "no history": 0.0,
        "low": 25.0,
        "medium": 50.0,
        "high": 75.0,
        "critical": 100.0,
        "recurring": 75.0,
        "repeated": 100.0,
    }

    if normalized in mapping:
        return mapping[normalized]

    try:
        return _clamp_score(
            float(normalized)
        )

    except (
        TypeError,
        ValueError,
    ):
        return 50.0


# Priority classification


def classify_priority(
    score: Any,
) -> PriorityLevel:
    """
    Convert a 0-100 score into a priority level.

    Mapping:

        0-24.99   -> Low
        25-49.99  -> Medium
        50-74.99  -> High
        75-100    -> Critical
    """

    numeric = _clamp_score(
        score
    )

    if numeric <= PRIORITY_LOW_MAX:
        return PriorityLevel.LOW

    if numeric <= PRIORITY_MEDIUM_MAX:
        return PriorityLevel.MEDIUM

    if numeric <= PRIORITY_HIGH_MAX:
        return PriorityLevel.HIGH

    return PriorityLevel.CRITICAL


# Recommended action


def recommend_action(
    priority: PriorityLevel | str,
) -> str:
    """
    Return deterministic operational guidance.
    """

    normalized = _normalize_text(
        priority
    )

    mapping = {
        _normalize_text(
            PriorityLevel.LOW
        ):
            "Routine monitoring and maintenance.",

        _normalize_text(
            PriorityLevel.MEDIUM
        ):
            "Schedule inspection and maintenance.",

        _normalize_text(
            PriorityLevel.HIGH
        ):
            "Prioritize inspection and corrective action.",

        _normalize_text(
            PriorityLevel.CRITICAL
        ):
            "Immediate inspection and urgent corrective action.",
    }

    return mapping.get(
        normalized,
        "Review the issue and determine appropriate action.",
    )


# ============================================================
# Result model
# ============================================================


@dataclass(frozen=True)
class PriorityResult:
    """
    Immutable priority result.
    """

    score: float
    priority: PriorityLevel
    recommended_action: str
    factors: dict[str, float]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Return output validated against the public API contract."""

        response = PriorityAssessmentResponse(
            priority_score=self.score,
            priority=self.priority.value,
            recommended_action=self.recommended_action,
            factors={
                key: round(float(value), 2)
                for key, value in self.factors.items()
            },
        )

        if hasattr(response, "model_dump"):
            return response.model_dump()

        return response.dict()


# Core calculation


def calculate_priority(
    *,
    project_delay: Any = None,
    infrastructure_condition: Any = None,
    population_affected: Any = None,
    project_importance: Any = None,
    issue_severity: Any = None,
    duration: Any = None,
    historical_data: Any = None,
) -> PriorityResult:
    """
    Calculate deterministic infrastructure priority.

    Missing factors contribute zero.

    Score formula:

        delay
        + condition
        + population
        + importance
        + severity
        + duration
        + historical
    """

    factors = {
        "project_delay": _normalize_delay(
            project_delay
        ),

        "infrastructure_condition":
            _normalize_condition(
                infrastructure_condition
            ),

        "population_affected":
            _normalize_population(
                population_affected
            ),

        "project_importance":
            _normalize_importance(
                project_importance
            ),

        "issue_severity":
            _normalize_severity(
                issue_severity
            ),

        "duration":
            _normalize_duration(
                duration
            ),

        "historical_data":
            _normalize_historical_data(
                historical_data
            ),
    }

    weighted_score = (
        factors["project_delay"]
        * DELAY_WEIGHT

        + factors["infrastructure_condition"]
        * CONDITION_WEIGHT

        + factors["population_affected"]
        * POPULATION_WEIGHT

        + factors["project_importance"]
        * IMPORTANCE_WEIGHT

        + factors["issue_severity"]
        * SEVERITY_WEIGHT

        + factors["duration"]
        * DURATION_WEIGHT

        + factors["historical_data"]
        * HISTORICAL_WEIGHT
    )

    score = _round_score(
        weighted_score
    )

    priority = classify_priority(
        score
    )

    action = recommend_action(
        priority
    )

    normalized_factors = {
        key: round(
            value,
            2,
        )
        for key, value in factors.items()
    }

    return PriorityResult(
        score=score,
        priority=priority,
        recommended_action=action,
        factors=normalized_factors,
    )


# JSON-friendly API


def score_priority(
    *,
    project_delay: Any = None,
    infrastructure_condition: Any = None,
    population_affected: Any = None,
    project_importance: Any = None,
    issue_severity: Any = None,
    duration: Any = None,
    historical_data: Any = None,
) -> dict[str, Any]:
    """
    JSON-friendly priority scoring API.
    """

    result = calculate_priority(
        project_delay=project_delay,
        infrastructure_condition=(
            infrastructure_condition
        ),
        population_affected=(
            population_affected
        ),
        project_importance=(
            project_importance
        ),
        issue_severity=(
            issue_severity
        ),
        duration=duration,
        historical_data=(
            historical_data
        ),
    )

    return result.to_dict()


# FastAPI-compatible service class


class PriorityScorer:
    """
    Stateless compatibility service used by the FastAPI route.
    """

    def calculate(
        self,
        *,
        project_delay: Any = None,
        infrastructure_condition: Any = None,
        population_affected: Any = None,
        project_importance: Any = None,
        issue_severity: Any = None,
        duration: Any = None,
        historical_data: Any = None,
    ) -> dict[str, Any]:
        """
        Calculate priority and return JSON-safe output.
        """

        return score_priority(
            project_delay=project_delay,
            infrastructure_condition=(
                infrastructure_condition
            ),
            population_affected=(
                population_affected
            ),
            project_importance=(
                project_importance
            ),
            issue_severity=(
                issue_severity
            ),
            duration=duration,
            historical_data=(
                historical_data
            ),
        )


# Public exports


__all__ = [
    "DELAY_WEIGHT",
    "CONDITION_WEIGHT",
    "POPULATION_WEIGHT",
    "IMPORTANCE_WEIGHT",
    "SEVERITY_WEIGHT",
    "DURATION_WEIGHT",
    "HISTORICAL_WEIGHT",
    "TOTAL_WEIGHT",
    "PriorityScoringError",
    "InvalidPriorityInputError",
    "PriorityResult",
    "PriorityScorer",
    "classify_priority",
    "recommend_action",
    "calculate_priority",
    "score_priority",
]
