"""
CivicSight AI Infrastructure Intelligence
------------------------------------------

Deterministic severity calculation service.

Responsibilities:
- Convert infrastructure condition into a normalized score.
- Convert issue type into a normalized score.
- Convert project delay into a normalized score.
- Convert public impact into a normalized score.
- Calculate a deterministic 0-100 severity score.
- Classify the score as Low, Medium, or High.
- Provide a deterministic explanation.

Design:
- No FastAPI dependency.
- No database dependency.
- No LLM dependency.
- Deterministic and repeatable.
- Missing factors are excluded and remaining weights are
  renormalized.
- Final score is always between 0 and 100.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any


# ============================================================
# Weights
# ============================================================

CONDITION_WEIGHT = 0.50
ISSUE_WEIGHT = 0.20
DELAY_WEIGHT = 0.15
IMPACT_WEIGHT = 0.15

TOTAL_WEIGHT = (
    CONDITION_WEIGHT
    + ISSUE_WEIGHT
    + DELAY_WEIGHT
    + IMPACT_WEIGHT
)

if abs(TOTAL_WEIGHT - 1.0) > 1e-9:
    raise RuntimeError(
        "Severity scoring weights must sum to exactly 1.0."
    )


# ============================================================
# Severity enum
# ============================================================


class SeverityLevel(str, Enum):
    """Public severity levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ============================================================
# Result model
# ============================================================


@dataclass(frozen=True)
class SeverityResult:
    """
    Immutable severity calculation result.

    Attributes:
        score:
            Final normalized severity score from 0 to 100.

        severity:
            Low, Medium, or High.

        factors:
            Individual normalized factor scores.

        explanation:
            Deterministic human-readable explanation.
    """

    score: float
    severity: SeverityLevel
    factors: dict[str, float]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return {
            "score": self.score,
            "severity": self.severity.value,
            "factors": dict(self.factors),
            "explanation": self.explanation,
        }


# ============================================================
# Exceptions
# ============================================================


class SeverityScoringError(Exception):
    """Base severity-scoring exception."""


class InvalidSeverityInputError(
    SeverityScoringError
):
    """Raised when severity input is invalid."""


# ============================================================
# Text normalization
# ============================================================


def _normalize_text(value: Any) -> str:
    """
    Normalize strings and Enum values.

    Examples:
        "  POOR  " -> "poor"
        "damaged_structure" -> "damaged structure"
        SeverityLevel.HIGH -> "high"
        None -> ""
    """

    if value is None:
        return ""

    if isinstance(value, Enum):
        value = value.value

    text = str(value)

    text = text.replace(
        "_",
        " ",
    )

    text = text.strip().lower()

    return " ".join(
        text.split()
    )


# ============================================================
# Numeric helpers
# ============================================================


def _clamp_score(score: Any) -> float:
    """
    Clamp a numeric score to 0-100.

    Invalid or non-finite values return 0.
    """

    try:
        value = float(score)

    except (TypeError, ValueError):
        return 0.0

    if not isfinite(value):
        return 0.0

    return max(
        0.0,
        min(
            100.0,
            value,
        ),
    )


def _round_score(score: Any) -> float:
    """Clamp and round a score to two decimal places."""

    return round(
        _clamp_score(score),
        2,
    )


def _is_supplied(value: Any) -> bool:
    """Return True when a factor was explicitly supplied."""

    return value is not None


# ============================================================
# Condition scoring
# ============================================================


def _condition_score(
    condition: Any,
) -> float:
    """
    Convert infrastructure condition to 0-100.

    Mapping:

        Good      -> 10
        Fair      -> 35
        Poor      -> 70
        Critical  -> 100
        Unknown   -> 40

    Unknown textual values are treated as neutral.
    """

    normalized = _normalize_text(
        condition
    )

    scores = {
        "good": 10.0,
        "fair": 35.0,
        "poor": 70.0,
        "critical": 100.0,
        "unknown": 40.0,
    }

    return scores.get(
        normalized,
        40.0,
    )


# ============================================================
# Issue scoring
# ============================================================


def _issue_score(
    issue: Any,
) -> float:
    """
    Convert infrastructure issue type to 0-100.

    Mapping:

        Pothole                   -> 55
        Crack                     -> 45
        Road Damage               -> 70
        Broken Streetlight        -> 55
        Damaged Drainage          -> 75
        Garbage Accumulation      -> 40
        Damaged Structure         -> 85
        Incomplete Work           -> 65
        Abandoned Infrastructure  -> 80
        Construction Progress     -> 30
        Visible Deterioration     -> 65
        Other                     -> 40
        Unknown                   -> 40
    """

    normalized = _normalize_text(
        issue
    )

    scores = {
        "pothole": 55.0,
        "crack": 45.0,
        "road damage": 70.0,
        "broken streetlight": 55.0,
        "damaged drainage": 75.0,
        "garbage accumulation": 40.0,
        "damaged structure": 85.0,
        "incomplete work": 65.0,
        "abandoned infrastructure": 80.0,
        "construction progress": 30.0,
        "visible deterioration": 65.0,
        "other": 40.0,
        "unknown": 40.0,
    }

    return scores.get(
        normalized,
        40.0,
    )


# ============================================================
# Delay scoring
# ============================================================


def _delay_score(
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

    if isinstance(
        delay,
        bool,
    ):
        return 0.0

    if isinstance(
        delay,
        str,
    ):

        normalized = _normalize_text(
            delay
        )

        if not normalized:
            return 0.0

        try:
            delay = float(
                normalized
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    try:
        value = float(
            delay
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    if not isfinite(value):
        return 0.0

    if value <= 0:
        return 0.0

    if value <= 10:
        return value * 2.0

    if value <= 25:
        return (
            20.0
            + (
                value - 10.0
            )
            * (
                30.0 / 15.0
            )
        )

    if value <= 50:
        return (
            50.0
            + (
                value - 25.0
            )
            * (
                50.0 / 25.0
            )
        )

    return 100.0


# ============================================================
# Impact scoring
# ============================================================


def _impact_score(
    impact: Any,
) -> float:
    """
    Convert public impact into 0-100.

    Text mapping:

        low       -> 25
        medium    -> 50
        moderate  -> 50
        high      -> 75
        critical  -> 100
        unknown   -> 40

    Numeric values are clamped to 0-100.

    None means the factor was not supplied.
    """

    if impact is None:
        return 0.0

    if isinstance(
        impact,
        Enum,
    ):
        impact = impact.value

    if isinstance(
        impact,
        str,
    ):

        normalized = _normalize_text(
            impact
        )

        text_scores = {
            "low": 25.0,
            "medium": 50.0,
            "moderate": 50.0,
            "high": 75.0,
            "critical": 100.0,
            "unknown": 40.0,
        }

        if normalized in text_scores:
            return text_scores[
                normalized
            ]

        try:
            impact = float(
                normalized
            )

        except (
            TypeError,
            ValueError,
        ):
            return 40.0

    try:
        return _clamp_score(
            float(impact)
        )

    except (
        TypeError,
        ValueError,
    ):
        return 40.0


# ============================================================
# Severity classification
# ============================================================


def classify_severity(
    score: Any,
) -> SeverityLevel:
    """
    Convert a 0-100 score into a severity level.

    Boundaries:

        0.00 - 33.33 -> Low
        33.34 - 66.66 -> Medium
        66.67 - 100 -> High
    """

    numeric = _clamp_score(
        score
    )

    if numeric <= 33.33:
        return SeverityLevel.LOW

    if numeric <= 66.66:
        return SeverityLevel.MEDIUM

    return SeverityLevel.HIGH


# ============================================================
# Explanation
# ============================================================


def _build_explanation(
    *,
    score: float,
    severity: SeverityLevel,
    factors: dict[str, float],
) -> str:
    """
    Build a deterministic explanation.

    This function intentionally does NOT call itself.

    The previous implementation contained a recursive call here,
    which could cause RecursionError.
    """

    if not factors:
        return (
            "No severity factors were supplied. "
            "Severity defaults to Low with a score of 0."
        )

    factor_names = {
        "condition": "infrastructure condition",
        "issue": "issue type",
        "delay": "project delay",
        "impact": "public impact",
    }

    # Find the strongest contributing factor.
    strongest_factor = max(
        factors,
        key=factors.get,
    )

    strongest_value = factors[
        strongest_factor
    ]

    strongest_name = factor_names.get(
        strongest_factor,
        strongest_factor,
    )

    supplied_names = [
        factor_names.get(
            name,
            name,
        )
        for name in factors
    ]

    supplied_text = ", ".join(
        supplied_names
    )

    return (
        f"Severity is {severity.value} "
        f"with a score of {score:.2f}. "
        f"Evaluated factors: {supplied_text}. "
        f"The strongest factor was "
        f"{strongest_name} "
        f"with a normalized score of "
        f"{strongest_value:.2f}."
    )


# ============================================================
# Main calculation
# ============================================================


def calculate_severity(
    *,
    condition: Any = None,
    issue: Any = None,
    delay: Any = None,
    impact: Any = None,
) -> SeverityResult:
    """
    Calculate deterministic infrastructure severity.

    Supplied factors only are included.

    Missing factors are excluded and the weights of supplied
    factors are renormalized.

    If no factors are supplied:

        score = 0
        severity = Low
        factors = {}
    """

    factors: dict[str, float] = {}
    weights: dict[str, float] = {}

    # --------------------------------------------------------
    # Condition
    # --------------------------------------------------------

    if _is_supplied(condition):

        factors["condition"] = (
            _condition_score(
                condition
            )
        )

        weights["condition"] = (
            CONDITION_WEIGHT
        )

    # --------------------------------------------------------
    # Issue
    # --------------------------------------------------------

    if _is_supplied(issue):

        factors["issue"] = (
            _issue_score(
                issue
            )
        )

        weights["issue"] = (
            ISSUE_WEIGHT
        )

    # --------------------------------------------------------
    # Delay
    # --------------------------------------------------------

    if _is_supplied(delay):

        factors["delay"] = (
            _delay_score(
                delay
            )
        )

        weights["delay"] = (
            DELAY_WEIGHT
        )

    # --------------------------------------------------------
    # Impact
    # --------------------------------------------------------

    if _is_supplied(impact):

        factors["impact"] = (
            _impact_score(
                impact
            )
        )

        weights["impact"] = (
            IMPACT_WEIGHT
        )

    # --------------------------------------------------------
    # No factors
    # --------------------------------------------------------

    if not factors:

        score = 0.0

        severity = classify_severity(
            score
        )

        explanation = _build_explanation(
            score=score,
            severity=severity,
            factors=factors,
        )

        return SeverityResult(
            score=score,
            severity=severity,
            factors={},
            explanation=explanation,
        )

    # --------------------------------------------------------
    # Renormalize supplied weights
    # --------------------------------------------------------

    total_weight = sum(
        weights.values()
    )

    if total_weight <= 0:
        raise InvalidSeverityInputError(
            "Total severity weight must be greater than zero."
        )

    weighted_score = sum(
        factors[name]
        * weights[name]
        for name in factors
    )

    score = _round_score(
        weighted_score
        / total_weight
    )

    severity = classify_severity(
        score
    )

    # Round factor values for stable API output.
    normalized_factors = {
        name: round(
            value,
            2,
        )
        for name, value
        in factors.items()
    }

    explanation = _build_explanation(
        score=score,
        severity=severity,
        factors=normalized_factors,
    )

    return SeverityResult(
        score=score,
        severity=severity,
        factors=normalized_factors,
        explanation=explanation,
    )


# ============================================================
# JSON-friendly API
# ============================================================


def score_severity(
    *,
    condition: Any = None,
    issue: Any = None,
    delay: Any = None,
    impact: Any = None,
) -> dict[str, Any]:
    """
    JSON-friendly wrapper around calculate_severity().
    """

    result = calculate_severity(
        condition=condition,
        issue=issue,
        delay=delay,
        impact=impact,
    )

    return result.to_dict()


# ============================================================
# Compatibility alias
# ============================================================


def calculate_severity_dict(
    *,
    condition: Any = None,
    issue: Any = None,
    delay: Any = None,
    impact: Any = None,
) -> dict[str, Any]:
    """
    Backward-compatible dictionary API.
    """

    return score_severity(
        condition=condition,
        issue=issue,
        delay=delay,
        impact=impact,
    )


# ============================================================
# Public exports
# ============================================================


__all__ = [
    "CONDITION_WEIGHT",
    "ISSUE_WEIGHT",
    "DELAY_WEIGHT",
    "IMPACT_WEIGHT",
    "SeverityLevel",
    "SeverityResult",
    "SeverityScoringError",
    "InvalidSeverityInputError",
    "_normalize_text",
    "_clamp_score",
    "_round_score",
    "_condition_score",
    "_issue_score",
    "_delay_score",
    "_impact_score",
    "classify_severity",
    "calculate_severity",
    "score_severity",
    "calculate_severity_dict",
]