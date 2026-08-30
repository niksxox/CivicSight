

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from app.services.image_analyzer import ImageAnalyzer


# Exceptions


class ResolutionVerificationError(Exception):
    """Base exception for resolution verification failures."""


class InvalidEvidenceError(ResolutionVerificationError):
    """Raised when supplied evidence is invalid or missing."""


# Status


class VerificationStatus(str, Enum):
    """Stable verification statuses exposed by the service."""

    COMPLETION_APPEARS_GENUINE = (
        "completion_appears_genuine"
    )

    IMPROVEMENT_APPEARS_GENUINE = (
        "improvement_appears_genuine"
    )

    NO_IMPROVEMENT = "no_improvement"

    CONDITION_WORSENED = "condition_worsened"

    UNCERTAIN = "uncertain"


# Result


@dataclass(frozen=True)
class VerificationResult:
    """
    Verification result.

    All fields are JSON-compatible and can be converted directly
    into a dictionary for FastAPI/Pydantic integration.
    """

    previous_condition: str
    current_condition: str
    visual_verification: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return {
            "previous_condition": self.previous_condition,
            "current_condition": self.current_condition,
            "visual_verification": self.visual_verification,
            "status": self.status,
        }


# Resolution Verifier


class ResolutionVerifier:
    """
    Verify whether infrastructure repair/progress appears genuine.

    Supported evidence:

    1. Already analyzed evidence:

        verifier.verify(
            previous_evidence=previous_analysis,
            current_evidence=current_analysis,
        )

    2. Raw image bytes:

        verifier.verify(
            previous_image_bytes=old_bytes,
            current_image_bytes=new_bytes,
        )

    The service deliberately keeps image analysis separate from
    resolution comparison so the backend can reuse existing
    ImageAnalyzer results without running inference twice.
    """

    # Condition scoring
    
    # Lower score = worse condition.
    # Higher score = better condition.
    #
    # These are deterministic heuristic scores, not probabilities.

    _CONDITION_SCORES: dict[str, float] = {
        "critical": 0.0,
        "severe": 15.0,
        "severely damaged": 15.0,
        "critical infrastructure failure": 15.0,
        "major damage": 15.0,

        "poor": 30.0,
        "damaged": 30.0,
        "broken": 30.0,
        "bad": 30.0,
        "bad condition": 30.0,
        "deteriorated": 30.0,
        "deteriorated surface": 30.0,

        "partially damaged": 50.0,
        "fair": 50.0,
        "moderate": 50.0,
        "average": 50.0,
        "unknown": 50.0,

        "good": 75.0,
        "improved": 75.0,
        "functional": 75.0,

        "repaired": 95.0,
        "road repaired": 95.0,
        "restored": 95.0,
        "completed": 95.0,
        "work completed": 95.0,
        "complete": 95.0,

        "excellent": 100.0,
        "healthy": 100.0,
    }

    def __init__(
        self,
        image_analyzer: Optional[ImageAnalyzer] = None,
    ) -> None:
        """
        Initialize the verifier.

        Dependency injection is supported so tests and backend
        integrations can provide an existing ImageAnalyzer.
        """

        self.image_analyzer = (
            image_analyzer
            if image_analyzer is not None
            else ImageAnalyzer()
        )

    # Public API

    def verify(
        self,
        previous_evidence: Any = None,
        current_evidence: Any = None,
        *,
        previous_image_bytes: Optional[bytes] = None,
        current_image_bytes: Optional[bytes] = None,
        previous_result: Any = None,
        current_result: Any = None,
    ) -> dict[str, Any]:
        """
        Compare previous and current infrastructure evidence.

        Returns:

            {
                "previous_condition": "...",
                "current_condition": "...",
                "visual_verification": 82.5,
                "status": "improvement_appears_genuine"
            }

        Raw image inputs are validated BEFORE either image is
        analyzed. This prevents an invalid current image from
        accidentally causing analysis of the previous image first.
        """

        # Validate explicitly supplied raw images FIRST.

        self._validate_raw_image_argument(
            previous_image_bytes,
            label="Previous",
        )

        self._validate_raw_image_argument(
            current_image_bytes,
            label="Current",
        )

        # Resolve evidence.

        previous = self._resolve_evidence(
            evidence=previous_evidence,
            image_bytes=previous_image_bytes,
            result=previous_result,
            label="previous",
        )

        current = self._resolve_evidence(
            evidence=current_evidence,
            image_bytes=current_image_bytes,
            result=current_result,
            label="current",
        )

        # Extract conditions.

        previous_condition = self._extract_condition(
            previous
        )

        current_condition = self._extract_condition(
            current
        )

        # Calculate condition scores.

        previous_score = self._condition_score(
            previous_condition
        )

        current_score = self._condition_score(
            current_condition
        )

        # Calculate verification confidence.

        confidence = (
            self._calculate_verification_confidence(
                previous=previous,
                current=current,
                previous_score=previous_score,
                current_score=current_score,
            )
        )

        # Determine verification status.

        status = self._determine_status(
            previous=previous,
            current=current,
            previous_condition=previous_condition,
            current_condition=current_condition,
            previous_score=previous_score,
            current_score=current_score,
        )

        return VerificationResult(
            previous_condition=previous_condition,
            current_condition=current_condition,
            visual_verification=confidence,
            status=status,
        ).to_dict()

    # Convenience APIs

    def verify_results(
        self,
        previous_result: Any,
        current_result: Any,
    ) -> dict[str, Any]:
        """
        Verify two already-analyzed image results.

        ImageAnalyzer is not called again.
        """

        return self.verify(
            previous_evidence=previous_result,
            current_evidence=current_result,
        )

    def verify_images(
        self,
        previous_image_bytes: bytes,
        current_image_bytes: bytes,
    ) -> dict[str, Any]:
        """Verify two raw image byte payloads."""

        return self.verify(
            previous_image_bytes=previous_image_bytes,
            current_image_bytes=current_image_bytes,
        )

    # Raw Image Validation

    @staticmethod
    def _validate_raw_image_argument(
        image_bytes: Optional[bytes],
        *,
        label: str,
    ) -> None:
        """
        Validate an explicitly supplied raw image.

        This happens before either image is analyzed.

        Important:
        None means the caller did not provide raw image bytes.
        That is allowed because analyzed evidence may be supplied
        through previous_evidence/current_evidence.

        An explicitly supplied empty image is invalid.
        """

        if image_bytes is None:
            return

        if not isinstance(
            image_bytes,
            (bytes, bytearray, memoryview),
        ):
            raise InvalidEvidenceError(
                f"{label} image evidence must be non-empty bytes."
            )

        if len(image_bytes) == 0:
            raise InvalidEvidenceError(
                f"{label} evidence is required."
            )

    # Evidence Resolution

    def _resolve_evidence(
        self,
        *,
        evidence: Any,
        image_bytes: Optional[bytes],
        result: Any,
        label: str,
    ) -> Any:
        """
        Resolve one evidence source.

        Priority:

            1. Explicit analyzed result
            2. Evidence argument
            3. Raw image bytes

        Already analyzed evidence is preferred because it avoids
        duplicate image inference.
        """

        candidate = (
            result
            if result is not None
            else evidence
        )

        # Explicit result/evidence.

        if candidate is not None:

            if self._is_valid_analysis(
                candidate
            ):
                return candidate

            if self._looks_like_image_bytes(
                candidate
            ):
                image_bytes = candidate

            elif isinstance(
                candidate,
                Mapping,
            ):
                # Keep malformed mappings so _extract_condition()
                # can produce a useful InvalidEvidenceError.
                return candidate

            else:
                raise InvalidEvidenceError(
                    f"{label.capitalize()} evidence is invalid."
                )

        # No evidence supplied.

        if image_bytes is None:
            raise InvalidEvidenceError(
                f"{label.capitalize()} evidence is required."
            )

        # Validate image bytes again for internally resolved
        # byte-like evidence.
        

        if not self._looks_like_image_bytes(
            image_bytes
        ):
            raise InvalidEvidenceError(
                f"{label.capitalize()} image evidence must be "
                "non-empty bytes."
            )

        # Analyze image.

        try:
            analyzed = self.image_analyzer.analyze(
                image_bytes
            )

        except Exception as exc:
            raise ResolutionVerificationError(
                f"Failed to analyze {label} evidence."
            ) from exc

        if not self._is_valid_analysis(
            analyzed
        ):
            raise ResolutionVerificationError(
                f"Image analyzer returned invalid "
                f"{label} evidence."
            )

        return analyzed

    # Evidence Type Helpers

    @staticmethod
    def _looks_like_image_bytes(
        value: Any,
    ) -> bool:
        """
        Return True for non-empty bytes-like image evidence.
        """

        return (
            isinstance(
                value,
                (
                    bytes,
                    bytearray,
                    memoryview,
                ),
            )
            and len(value) > 0
        )

    @staticmethod
    def _is_valid_analysis(
        value: Any,
    ) -> bool:
        """
        Determine whether a value looks like an image-analysis
        result.

        Supported:

        - dictionaries
        - Pydantic models
        - dataclasses
        - normal Python objects exposing attributes
        """

        data = (
            ResolutionVerifier._to_mapping(
                value
            )
        )

        if data is None:
            return False

        return any(
            key in data
            for key in (
                "condition",
                "current_condition",
                "detected_issue",
                "issue",
                "severity",
                "infrastructure",
            )
        )

    @staticmethod
    def _to_mapping(
        value: Any,
    ) -> Optional[Mapping[str, Any]]:
        """Convert supported result objects into mappings."""

        if isinstance(
            value,
            Mapping,
        ):
            return value

        model_dump = getattr(
            value,
            "model_dump",
            None,
        )

        if callable(model_dump):
            try:
                dumped = model_dump()
            except Exception:
                dumped = None

            if isinstance(
                dumped,
                Mapping,
            ):
                return dumped

        dict_method = getattr(
            value,
            "dict",
            None,
        )

        if callable(dict_method):
            try:
                dumped = dict_method()
            except Exception:
                dumped = None

            if isinstance(
                dumped,
                Mapping,
            ):
                return dumped

        if hasattr(
            value,
            "__dict__",
        ):
            data = vars(value)

            if isinstance(
                data,
                Mapping,
            ):
                return data

        return None

    # Condition Extraction

    def _extract_condition(
        self,
        evidence: Any,
    ) -> str:
        """
        Extract condition text from analyzed evidence.
        """

        data = self._to_mapping(
            evidence
        )

        if data is None:
            raise InvalidEvidenceError(
                "Evidence must be a mapping or supported model."
            )

        raw_condition = self._first_value(
            data,
            (
                "condition",
                "current_condition",
                "previous_condition",
            ),
        )

        if raw_condition is None:
            raise InvalidEvidenceError(
                "Evidence must contain a condition."
            )

        condition = str(
            raw_condition
        ).strip()

        if not condition:
            raise InvalidEvidenceError(
                "Evidence condition cannot be empty."
            )

        return condition

    @staticmethod
    def _first_value(
        data: Mapping[str, Any],
        keys: Sequence[str],
    ) -> Any:
        """Return the first non-null value for the supplied keys."""

        for key in keys:

            if key not in data:
                continue

            value = data[key]

            if value is not None:
                return value

        return None

    # Condition Scoring

    def _condition_score(
        self,
        condition: str,
    ) -> float:
        """
        Convert condition text into a deterministic health score.

        Score interpretation:

            0-20    critical/severe
            21-40   poor/damaged
            41-60   moderate/fair
            61-80   good/improved
            81-100  repaired/completed/healthy

        Unknown descriptions receive 50.0.

        Specific compound phrases are checked BEFORE generic
        substrings so that:

            "partially damaged"
                -> 50

        does not incorrectly become:

            "damaged"
                -> 30
        """

        normalized = self._normalize(
            condition
        )

        if not normalized:
            return 50.0

        # Exact/specific compound matches FIRST.

        specific_scores = (
            (
                (
                    "severely damaged",
                    "critical infrastructure failure",
                    "major damage",
                ),
                15.0,
            ),
            (
                (
                    "partially damaged",
                ),
                50.0,
            ),
            (
                (
                    "bad condition",
                    "deteriorated surface",
                ),
                30.0,
            ),
            (
                (
                    "road repaired",
                    "work completed",
                ),
                95.0,
            ),
        )

        for phrases, score in specific_scores:

            if any(
                phrase in normalized
                for phrase in phrases
            ):
                return score

        # Exact known values.

        exact_score = (
            self._CONDITION_SCORES.get(
                normalized
            )
        )

        if exact_score is not None:
            return exact_score

        # Generic semantic phrases.

        if any(
            phrase in normalized
            for phrase in (
                "severe",
                "critical",
                "major damage",
            )
        ):
            return 15.0

        if any(
            phrase in normalized
            for phrase in (
                "poor",
                "damaged",
                "broken",
                "deteriorated",
            )
        ):
            return 30.0

        if any(
            phrase in normalized
            for phrase in (
                "moderate",
                "fair",
            )
        ):
            return 50.0

        if any(
            phrase in normalized
            for phrase in (
                "good",
                "improved",
                "functional",
            )
        ):
            return 75.0



        if any(
            phrase in normalized
            for phrase in (
                "repaired",
                "restored",
                "completed",
                "work completed",
                "road repaired",
                "fully repaired",
                "fully restored",
                "fully functional",
            )
        ):
            return 95.0

        if normalized in {
            "complete",
            "completion",
            "healthy",
            "excellent",
        }:
            return 95.0

        # Unknown = neutral.
        return 50.0

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        """
        Normalize condition text.

        Repeated whitespace is collapsed so:

            "bad    condition"

        becomes:

            "bad condition"
        """

        return " ".join(
            str(value)
            .lower()
            .strip()
            .split()
        )

    # Verification Confidence

    def _calculate_verification_confidence(
        self,
        *,
        previous: Any,
        current: Any,
        previous_score: float,
        current_score: float,
    ) -> float:
        """
        Calculate a 0-100 verification confidence.

        This represents confidence in the evidence comparison,
        not mathematical proof that a repair occurred.
        """

        improvement = (
            current_score
            - previous_score
        )

        previous_confidence = (
            self._extract_confidence(
                previous
            )
        )

        current_confidence = (
            self._extract_confidence(
                current
            )
        )

        evidence_confidence = (
            previous_confidence
            + current_confidence
        ) / 2.0

        # Strength of observed change.

        if improvement >= 50:
            change_strength = 95.0

        elif improvement >= 35:
            change_strength = 90.0

        elif improvement >= 20:
            change_strength = 80.0

        elif improvement >= 10:
            change_strength = 65.0

        elif improvement > 0:
            change_strength = 55.0

        elif improvement == 0:
            change_strength = 45.0

        elif improvement >= -10:
            change_strength = 40.0

        else:
            change_strength = 30.0

        result = (
            (change_strength * 0.65)
            + (evidence_confidence * 0.35)
        )

        # Same infrastructure type increases confidence.
        # Different infrastructure types reduce confidence.

        previous_infrastructure = (
            self._extract_optional_text(
                previous,
                (
                    "infrastructure",
                    "infrastructure_type",
                ),
            )
        )

        current_infrastructure = (
            self._extract_optional_text(
                current,
                (
                    "infrastructure",
                    "infrastructure_type",
                ),
            )
        )

        if (
            previous_infrastructure
            and current_infrastructure
        ):

            if (
                self._normalize(
                    previous_infrastructure
                )
                ==
                self._normalize(
                    current_infrastructure
                )
            ):
                result += 5.0

            else:
                result -= 20.0

        return self._clamp(
            result,
            0.0,
            100.0,
        )

    # Status Determination

    def _determine_status(
        self,
        *,
        previous: Any,
        current: Any,
        previous_condition: str,
        current_condition: str,
        previous_score: float,
        current_score: float,
    ) -> str:
        """
        Determine verification status.

        Rules:

            improvement < -10
                -> CONDITION_WORSENED

            improvement >= 20 and repaired/completed-like state
                -> COMPLETION_APPEARS_GENUINE

            improvement >= 20
                -> IMPROVEMENT_APPEARS_GENUINE

            small/no negative change with high-confidence evidence
                -> NO_IMPROVEMENT

            otherwise
                -> UNCERTAIN
        """

        improvement = (
            current_score
            - previous_score
        )

        current_normalized = (
            self._normalize(
                current_condition
            )
        )

        # Clearly worse.

        if improvement < -10:
            return (
                VerificationStatus
                .CONDITION_WORSENED
                .value
            )

        # Strong completion signal.

        if (
            improvement >= 20
            and self._is_completion_condition(
                current_normalized
            )
        ):
            return (
                VerificationStatus
                .COMPLETION_APPEARS_GENUINE
                .value
            )

        # Strong general improvement.

        if improvement >= 20:
            return (
                VerificationStatus
                .IMPROVEMENT_APPEARS_GENUINE
                .value
            )

        if improvement <= 0:

            previous_confidence = (
                self._extract_confidence(
                    previous
                )
            )

            current_confidence = (
                self._extract_confidence(
                    current
                )
            )

            if (
                previous_confidence >= 70
                and current_confidence >= 70
            ):
                return (
                    VerificationStatus
                    .NO_IMPROVEMENT
                    .value
                )

        # Small positive/ambiguous change.

        return (
            VerificationStatus
            .UNCERTAIN
            .value
        )

    @staticmethod
    def _is_completion_condition(
        condition: str,
    ) -> bool:
        """Check for a genuine completion/recovery phrase."""

        exact_completion_values = {
            "repaired",
            "restored",
            "completed",
            "complete",
            "excellent",
            "healthy",
            "functional",
        }

        if condition in exact_completion_values:
            return True

        completion_phrases = (
            "fully repaired",
            "fully restored",
            "fully functional",
            "work completed",
            "road repaired",
        )

        return any(
            phrase in condition
            for phrase in completion_phrases
        )

    # Confidence Extraction

    def _extract_confidence(
        self,
        evidence: Any,
    ) -> float:
        """
        Extract confidence from analyzed evidence.

        Accepts either:

            0.0 - 1.0

        or:

            0 - 100
        """

        data = self._to_mapping(
            evidence
        )

        if data is None:
            return 50.0

        raw = self._first_value(
            data,
            (
                "confidence",
                "detection_confidence",
                "analysis_confidence",
            ),
        )

        if raw is None:
            return 50.0

        try:
            value = float(raw)

        except (
            TypeError,
            ValueError,
        ):
            return 50.0

        if 0.0 <= value <= 1.0:
            value *= 100.0

        return self._clamp(
            value,
            0.0,
            100.0,
        )

    # Optional Text Extraction

    def _extract_optional_text(
        self,
        evidence: Any,
        keys: Sequence[str],
    ) -> Optional[str]:
        """Extract an optional text value."""

        data = self._to_mapping(
            evidence
        )

        if data is None:
            return None

        value = self._first_value(
            data,
            keys,
        )

        if value is None:
            return None

        text = str(
            value
        ).strip()

        return text or None

    # Numeric Helpers

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        """Clamp a numeric value to the supplied range."""

        return round(
            max(
                minimum,
                min(
                    value,
                    maximum,
                ),
            ),
            2,
        )


__all__ = [
    "InvalidEvidenceError",
    "ResolutionVerificationError",
    "ResolutionVerifier",
    "VerificationResult",
    "VerificationStatus",
]
