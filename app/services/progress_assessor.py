

from __future__ import annotations

from enum import Enum
from numbers import Real
from typing import Any, Mapping, Optional

from app.models.progress_models import (
    ProgressAssessmentResponse,
)


# Exceptions


class ProgressAssessmentError(ValueError):
    """Base exception for progress-assessment failures."""


class InvalidProgressError(ProgressAssessmentError):
    """Raised when a progress percentage is invalid."""


class InsufficientProgressEvidenceError(
    ProgressAssessmentError
):
    """Raised when actual progress cannot be determined."""


# Progress Status


class ProgressStatus(str, Enum):
    """
    Stable progress-status values.

    IMPORTANT:
    The current CivicSight API/test contract uses lowercase
    values:

        ahead
        on_track
        delayed
    """

    AHEAD = "ahead"

    ON_TRACK = "on_track"

    DELAYED = "delayed"


# Progress Assessor


class ProgressAssessor:
    """
    Deterministic project-progress assessor.

    Core flow:

        validate planned
              +
        validate actual
              |
              v
        actual - planned
              |
              v
           deviation
              |
              v
            status

    Example:

        planned = 80
        actual = 58

        deviation = -22
        status = delayed
    """

    # Percentage boundaries

    MIN_PROGRESS = 0.0

    MAX_PROGRESS = 100.0

    # Status tolerance

    DEFAULT_TOLERANCE = 5.0

    # Accepted evidence field names

    ACTUAL_PROGRESS_FIELDS = (
        "estimated_actual_progress",
        "actual_progress",
        "estimated_progress",
        "progress",
    )

    # Initialization

    def __init__(
        self,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> None:
        """
        Initialize the progress assessor.

        Args:
            tolerance:
                Difference in percentage points considered
                ON_TRACK.

        Example:

            planned = 80
            actual = 75

            deviation = -5

            With tolerance = 5:
                status = on_track
        """

        if (
            isinstance(tolerance, bool)
            or not isinstance(tolerance, Real)
        ):
            raise TypeError(
                "tolerance must be a number."
            )

        tolerance_value = float(
            tolerance
        )

        self._validate_finite_number(
            tolerance_value,
            field_name="tolerance",
        )

        if tolerance_value < 0:
            raise ValueError(
                "tolerance cannot be negative."
            )

        self.tolerance = tolerance_value

    # Public assessment API

    def assess(
        self,
        planned_progress: Real,
        evidence: Any = None,
        *,
        estimated_actual_progress: Optional[
            Real
        ] = None,
    ) -> ProgressAssessmentResponse:
        """
        Assess project progress.

        Args:
            planned_progress:
                Planned project completion percentage.

            evidence:
                Optional processed evidence containing actual
                progress.

                Supported forms:

                    58

                or:

                    {
                        "estimated_actual_progress": 58
                    }

                or:

                    {
                        "actual_progress": 58
                    }

                or an object with one of the supported fields.

            estimated_actual_progress:
                Explicit actual progress.

                When supplied, this takes precedence over evidence.

        Returns:
            ProgressAssessmentResponse

        Raises:
            InvalidProgressError:
                Invalid planned or actual percentage.

            InsufficientProgressEvidenceError:
                Actual progress is unavailable.
        """

        # Validate planned progress

        planned = self._validate_progress(
            planned_progress,
            field_name="planned_progress",
        )

        # Resolve actual progress

        if (
            estimated_actual_progress
            is not None
        ):
            actual = self._validate_progress(
                estimated_actual_progress,
                field_name=(
                    "estimated_actual_progress"
                ),
            )

        else:
            actual = (
                self._extract_actual_progress(
                    evidence
                )
            )

        # Calculate deviation

        deviation = self.calculate_deviation(
            actual_progress=actual,
            planned_progress=planned,
        )

        # Determine status

        status = self.determine_status(
            deviation
        )

        # Return API-compatible Pydantic model

        return ProgressAssessmentResponse(
            planned_progress=planned,
            estimated_actual_progress=actual,
            deviation=deviation,
            status=status.value,
        )

    # Deviation

    def calculate_deviation(
        self,
        actual_progress: Real,
        planned_progress: Real,
    ) -> float:
        """
        Calculate progress deviation.

        Formula:

            actual - planned

        Example:

            actual = 58
            planned = 80

            deviation = -22
        """

        actual = self._validate_progress(
            actual_progress,
            field_name="actual_progress",
        )

        planned = self._validate_progress(
            planned_progress,
            field_name="planned_progress",
        )

        return round(
            actual - planned,
            2,
        )

    # Status

    def determine_status(
        self,
        deviation: Real,
    ) -> ProgressStatus:
        """
        Determine project status from deviation.

        Rules:

            deviation < -tolerance
                -> delayed

            deviation > +tolerance
                -> ahead

            otherwise
                -> on_track

        With the default tolerance:

            -5 <= deviation <= +5
                -> on_track
        """

        if (
            isinstance(deviation, bool)
            or not isinstance(deviation, Real)
        ):
            raise TypeError(
                "deviation must be a number."
            )

        deviation_value = float(
            deviation
        )

        self._validate_finite_number(
            deviation_value,
            field_name="deviation",
        )

        if (
            deviation_value
            < -self.tolerance
        ):
            return ProgressStatus.DELAYED

        if (
            deviation_value
            > self.tolerance
        ):
            return ProgressStatus.AHEAD

        return ProgressStatus.ON_TRACK

    # Evidence extraction

    def _extract_actual_progress(
        self,
        evidence: Any,
    ) -> float:
        """
        Extract actual progress from processed evidence.

        This method intentionally does NOT interpret arbitrary
        natural language.

        Natural-language interpretation belongs to the LLM
        extraction layer.

        Visual estimation belongs to image/video processing.

        Supported examples:

            58

        or:

            {
                "estimated_actual_progress": 58
            }

        or:

            {
                "actual_progress": 58
            }

        or an object exposing one of the supported attributes.
        """

        if evidence is None:
            raise InsufficientProgressEvidenceError(
                "Actual project progress is required. "
                "Provide estimated_actual_progress or "
                "processed progress evidence."
            )

        # Direct numeric evidence

        if (
            isinstance(evidence, Real)
            and not isinstance(evidence, bool)
        ):
            return self._validate_progress(
                evidence,
                field_name=(
                    "estimated_actual_progress"
                ),
            )

        # Mapping / dictionary evidence

        if isinstance(
            evidence,
            Mapping,
        ):
            value = (
                self._find_mapping_value(
                    evidence
                )
            )

            if value is None:
                raise InsufficientProgressEvidenceError(
                    "Evidence does not contain an "
                    "actual-progress estimate."
                )

            return self._validate_progress(
                value,
                field_name=(
                    "estimated_actual_progress"
                ),
            )

        # Pydantic model / normal object

        for field_name in (
            self.ACTUAL_PROGRESS_FIELDS
        ):
            if not hasattr(
                evidence,
                field_name,
            ):
                continue

            value = getattr(
                evidence,
                field_name,
            )

            if value is None:
                continue

            return self._validate_progress(
                value,
                field_name=(
                    "estimated_actual_progress"
                ),
            )

        raise InsufficientProgressEvidenceError(
            "Unable to extract actual progress from supplied "
            "evidence. Expected a numeric value or an object "
            "containing 'estimated_actual_progress' or "
            "'actual_progress'."
        )

    # Mapping evidence

    @classmethod
    def _find_mapping_value(
        cls,
        evidence: Mapping[str, Any],
    ) -> Any:
        """
        Find an actual-progress value from a mapping.

        Supported aliases are intentionally limited to the
        established service contract.
        """

        for field_name in (
            cls.ACTUAL_PROGRESS_FIELDS
        ):
            if field_name not in evidence:
                continue

            value = evidence[
                field_name
            ]

            if value is not None:
                return value

        return None

    # Progress validation

    @classmethod
    def _validate_progress(
        cls,
        value: Real,
        *,
        field_name: str,
    ) -> float:
        """
        Validate a progress percentage.

        Valid:

            0 <= value <= 100

        Invalid:

            negative
            greater than 100
            boolean
            string
            list
            dictionary
            NaN
            infinity
        """

        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
        ):
            raise InvalidProgressError(
                f"{field_name} must be a number "
                "between 0 and 100."
            )

        numeric_value = float(
            value
        )

        cls._validate_finite_number(
            numeric_value,
            field_name=field_name,
        )

        if not (
            cls.MIN_PROGRESS
            <= numeric_value
            <= cls.MAX_PROGRESS
        ):
            raise InvalidProgressError(
                f"{field_name} must be between "
                f"{cls.MIN_PROGRESS:g} and "
                f"{cls.MAX_PROGRESS:g}."
            )

        return round(
            numeric_value,
            2,
        )

    # Finite-number validation

    @staticmethod
    def _validate_finite_number(
        value: float,
        *,
        field_name: str,
    ) -> None:
        """
        Reject NaN and infinite numeric values.
        """

        if value != value:
            raise InvalidProgressError(
                f"{field_name} cannot be NaN."
            )

        if value in (
            float("inf"),
            float("-inf"),
        ):
            raise InvalidProgressError(
                f"{field_name} must be finite."
            )

    # Compatibility aliases


ProjectProgressAssessor = ProgressAssessor


# Convenience API


def assess_progress(
    planned_progress: Real,
    evidence: Any = None,
    *,
    estimated_actual_progress: Optional[
        Real
    ] = None,
    tolerance: float = (
        ProgressAssessor.DEFAULT_TOLERANCE
    ),
) -> dict[str, Any]:
    """
    Convenience function for backend integration.

    Example:

        assess_progress(
            planned_progress=80,
            estimated_actual_progress=58,
        )

    Returns:

        {
            "planned_progress": 80.0,
            "estimated_actual_progress": 58.0,
            "deviation": -22.0,
            "status": "delayed"
        }
    """

    assessor = ProgressAssessor(
        tolerance=tolerance
    )

    result = assessor.assess(
        planned_progress=planned_progress,
        evidence=evidence,
        estimated_actual_progress=(
            estimated_actual_progress
        ),
    )

    if hasattr(
        result,
        "model_dump",
    ):
        return result.model_dump()

    return result.dict()


# Public exports


__all__ = [
    "ProgressAssessmentError",
    "InvalidProgressError",
    "InsufficientProgressEvidenceError",
    "ProgressStatus",
    "ProgressAssessmentResponse",
    "ProgressAssessor",
    "ProjectProgressAssessor",
    "assess_progress",
]
