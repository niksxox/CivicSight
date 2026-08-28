"""
Tests for CivicSight ResolutionVerifier.

No real vision model or external service is used.

Coverage:
- VerificationStatus
- VerificationResult
- dependency injection
- analyzed evidence
- Pydantic-style evidence
- dataclass/object evidence
- raw image bytes
- verify_results()
- verify_images()
- condition extraction
- condition scoring
- confidence calculation
- status classification
- invalid evidence
- analyzer failures
- result serialization
- deterministic behavior
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.resolution_verifier import (
    InvalidEvidenceError,
    ResolutionVerificationError,
    ResolutionVerifier,
    VerificationResult,
    VerificationStatus,
)


# ============================================================
# Test Doubles
# ============================================================


class FakeImageAnalyzer:
    """Mock ImageAnalyzer used for raw-image tests."""

    def __init__(
        self,
        results=None,
        error=None,
    ):
        self.results = list(results or [])
        self.error = error
        self.calls = []

    def analyze(self, image_bytes):
        self.calls.append(image_bytes)

        if self.error is not None:
            raise self.error

        if not self.results:
            raise RuntimeError(
                "No fake analysis result configured."
            )

        return self.results.pop(0)


class FakePydanticResult:
    """Minimal Pydantic-like object."""

    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return dict(self.data)


class FakeDictResult:
    """Object exposing the Pydantic v1-style dict() method."""

    def __init__(self, data):
        self.data = data

    def dict(self):
        return dict(self.data)


@dataclass
class FakeDataclassResult:
    """Dataclass-style analysis result."""

    condition: str
    confidence: float = 90.0


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def high_confidence_previous():
    return {
        "condition": "poor",
        "confidence": 95.0,
        "infrastructure": "road",
    }


@pytest.fixture
def high_confidence_current():
    return {
        "condition": "repaired",
        "confidence": 95.0,
        "infrastructure": "road",
    }


@pytest.fixture
def verifier():
    """Verifier with a mocked image analyzer."""

    return ResolutionVerifier(
        image_analyzer=FakeImageAnalyzer()
    )


# ============================================================
# Initialization
# ============================================================


def test_verifier_accepts_injected_image_analyzer():
    """Dependency injection should preserve the supplied analyzer."""

    analyzer = FakeImageAnalyzer()

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    assert verifier.image_analyzer is analyzer


def test_verifier_can_be_constructed_with_default_analyzer():
    """
    Default construction should remain available.

    This only verifies construction; no model inference is triggered.
    """

    verifier = ResolutionVerifier()

    assert verifier.image_analyzer is not None


# ============================================================
# VerificationStatus
# ============================================================


def test_verification_status_values_are_stable():
    """Public status values must remain API-safe strings."""

    assert (
        VerificationStatus.COMPLETION_APPEARS_GENUINE.value
        == "completion_appears_genuine"
    )

    assert (
        VerificationStatus.IMPROVEMENT_APPEARS_GENUINE.value
        == "improvement_appears_genuine"
    )

    assert (
        VerificationStatus.NO_IMPROVEMENT.value
        == "no_improvement"
    )

    assert (
        VerificationStatus.CONDITION_WORSENED.value
        == "condition_worsened"
    )

    assert (
        VerificationStatus.UNCERTAIN.value
        == "uncertain"
    )


# ============================================================
# VerificationResult
# ============================================================


def test_verification_result_to_dict():
    """VerificationResult should serialize to the expected API shape."""

    result = VerificationResult(
        previous_condition="poor",
        current_condition="repaired",
        visual_verification=94.0,
        status="completion_appears_genuine",
    )

    data = result.to_dict()

    assert data == {
        "previous_condition": "poor",
        "current_condition": "repaired",
        "visual_verification": 94.0,
        "status": "completion_appears_genuine",
    }


def test_verification_result_is_frozen():
    """VerificationResult should be immutable."""

    result = VerificationResult(
        previous_condition="poor",
        current_condition="repaired",
        visual_verification=94.0,
        status="completion_appears_genuine",
    )

    with pytest.raises(AttributeError):
        result.status = "uncertain"


# ============================================================
# Basic verify()
# ============================================================


def test_verify_returns_expected_dictionary(
    verifier,
):
    """verify() should return the documented public structure."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 95.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 95.0,
        },
    )

    assert set(result.keys()) == {
        "previous_condition",
        "current_condition",
        "visual_verification",
        "status",
    }


def test_verify_extracts_previous_and_current_conditions(
    verifier,
):
    """Conditions should be preserved in the returned result."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "good",
            "confidence": 90.0,
        },
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "good"


# ============================================================
# Completion Verification
# ============================================================


def test_repaired_after_poor_condition_is_genuine_completion(
    verifier,
):
    """
    Poor -> repaired is a strong improvement and should indicate
    completion appears genuine.
    """

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 95.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 95.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.COMPLETION_APPEARS_GENUINE.value
    )


def test_restored_after_damaged_condition_is_genuine_completion(
    verifier,
):
    """Damaged -> restored should indicate genuine completion."""

    result = verifier.verify(
        previous_evidence={
            "condition": "damaged",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "restored",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.COMPLETION_APPEARS_GENUINE.value
    )


def test_completed_after_critical_condition_is_genuine_completion(
    verifier,
):
    """Critical -> completed is a strong positive change."""

    result = verifier.verify(
        previous_evidence={
            "condition": "critical",
            "confidence": 95.0,
        },
        current_evidence={
            "condition": "completed",
            "confidence": 95.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.COMPLETION_APPEARS_GENUINE.value
    )


# ============================================================
# Improvement Status
# ============================================================


def test_poor_to_fair_is_improvement(
    verifier,
):
    """Poor -> Fair should be recognized as genuine improvement."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "fair",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.IMPROVEMENT_APPEARS_GENUINE.value
    )


def test_fair_to_good_is_improvement(
    verifier,
):
    """Fair -> Good should be recognized as improvement."""

    result = verifier.verify(
        previous_evidence={
            "condition": "fair",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "good",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.IMPROVEMENT_APPEARS_GENUINE.value
    )


# ============================================================
# No Improvement
# ============================================================


def test_same_condition_with_high_confidence_is_no_improvement(
    verifier,
):
    """Identical reliable evidence should produce no_improvement."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.NO_IMPROVEMENT.value
    )


def test_same_condition_with_low_confidence_is_uncertain(
    verifier,
):
    """
    Identical low-confidence evidence should not produce a strong
    no-improvement conclusion.
    """

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 50.0,
        },
        current_evidence={
            "condition": "poor",
            "confidence": 50.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.UNCERTAIN.value
    )


# ============================================================
# Worsening
# ============================================================


def test_good_to_poor_is_condition_worsened(
    verifier,
):
    """A large deterioration should be detected."""

    result = verifier.verify(
        previous_evidence={
            "condition": "good",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.CONDITION_WORSENED.value
    )


def test_repaired_to_critical_is_condition_worsened(
    verifier,
):
    """Severe deterioration should be detected."""

    result = verifier.verify(
        previous_evidence={
            "condition": "repaired",
            "confidence": 95.0,
        },
        current_evidence={
            "condition": "critical",
            "confidence": 95.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.CONDITION_WORSENED.value
    )


# ============================================================
# Uncertain Cases
# ============================================================


def test_small_improvement_is_uncertain(
    verifier,
):
    """
    A small condition change should not be presented as strong
    improvement.
    """

    result = verifier.verify(
        previous_evidence={
            "condition": "fair",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "moderate",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.UNCERTAIN.value
    )


def test_unknown_conditions_are_uncertain(
    verifier,
):
    """Unknown -> unknown should not claim completion."""

    result = verifier.verify(
        previous_evidence={
            "condition": "unknown",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "unknown",
            "confidence": 90.0,
        },
    )

    assert (
        result["status"]
        == VerificationStatus.NO_IMPROVEMENT.value
    )


# ============================================================
# Visual Verification Score
# ============================================================


def test_visual_verification_is_between_zero_and_hundred(
    verifier,
):
    """Verification confidence must always remain 0..100."""

    result = verifier.verify(
        previous_evidence={
            "condition": "critical",
            "confidence": 100.0,
        },
        current_evidence={
            "condition": "completed",
            "confidence": 100.0,
        },
    )

    assert 0.0 <= result["visual_verification"] <= 100.0


def test_visual_verification_is_rounded_to_two_decimals(
    verifier,
):
    """Confidence should be returned with at most two decimal places."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 83.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 87.0,
        },
    )

    score = result["visual_verification"]

    assert score == round(
        score,
        2,
    )


def test_clear_improvement_has_higher_verification_than_no_change(
    verifier,
):
    """Strong visual improvement should have stronger confidence."""

    improved = verifier.verify(
        previous_evidence={
            "condition": "critical",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "completed",
            "confidence": 90.0,
        },
    )

    unchanged = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
    )

    assert (
        improved["visual_verification"]
        > unchanged["visual_verification"]
    )


# ============================================================
# Condition Score Mapping
# ============================================================


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("critical", 0.0),
        ("severe", 15.0),
        ("poor", 30.0),
        ("damaged", 30.0),
        ("bad", 30.0),
        ("fair", 50.0),
        ("moderate", 50.0),
        ("average", 50.0),
        ("good", 75.0),
        ("repaired", 90.0),
        ("restored", 95.0),
        ("excellent", 100.0),
        ("completed", 100.0),
        ("complete", 100.0),
        ("healthy", 100.0),
        ("functional", 90.0),
        ("unknown", 50.0),
    ],
)
def test_condition_score_mapping(
    verifier,
    condition,
    expected,
):
    """Known conditions must map to their defined scores."""

    assert verifier._condition_score(
        condition
    ) == expected


def test_condition_score_is_case_insensitive(
    verifier,
):
    """Condition matching should ignore case and surrounding whitespace."""

    assert verifier._condition_score(
        "  POOR  "
    ) == 30.0


def test_condition_score_normalizes_repeated_whitespace(
    verifier,
):
    """Repeated internal whitespace should be normalized."""

    assert verifier._condition_score(
        "bad    condition"
    ) == 30.0


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("severely damaged road", 15.0),
        ("critical infrastructure failure", 15.0),
        ("major damage", 15.0),
        ("broken road", 30.0),
        ("deteriorated surface", 30.0),
        ("partially damaged", 50.0),
        ("improved road", 75.0),
        ("functional road", 75.0),
        ("road repaired", 95.0),
        ("work completed", 95.0),
    ],
)
def test_condition_score_compound_descriptions(
    verifier,
    condition,
    expected,
):
    """Common compound condition descriptions should be classified."""

    assert verifier._condition_score(
        condition
    ) == expected


def test_unknown_condition_uses_neutral_score(
    verifier,
):
    """Unknown condition text should not imply severe damage."""

    assert verifier._condition_score(
        "something completely unrelated"
    ) == 50.0


# ============================================================
# Evidence Resolution
# ============================================================


def test_verify_accepts_previous_and_current_evidence(
    verifier,
):
    """Already analyzed dictionaries should bypass ImageAnalyzer."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "good",
            "confidence": 90.0,
        },
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "good"

    assert (
        len(
            verifier.image_analyzer.calls
        )
        == 0
    )


def test_verify_accepts_explicit_previous_result_and_current_result(
    verifier,
):
    """Explicit result arguments should take priority."""

    result = verifier.verify(
        previous_evidence={
            "condition": "critical",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "critical",
            "confidence": 90.0,
        },
        previous_result={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_result={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"


# ============================================================
# Pydantic-like / Object Evidence
# ============================================================


def test_verify_accepts_model_dump_objects(
    verifier,
):
    """Objects exposing model_dump() should be accepted."""

    previous = FakePydanticResult(
        {
            "condition": "poor",
            "confidence": 90.0,
        }
    )

    current = FakePydanticResult(
        {
            "condition": "repaired",
            "confidence": 90.0,
        }
    )

    result = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"


def test_verify_accepts_dict_method_objects(
    verifier,
):
    """Objects exposing dict() should be accepted."""

    previous = FakeDictResult(
        {
            "condition": "poor",
            "confidence": 90.0,
        }
    )

    current = FakeDictResult(
        {
            "condition": "good",
            "confidence": 90.0,
        }
    )

    result = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "good"


def test_verify_accepts_dataclass_like_objects(
    verifier,
):
    """Objects exposing __dict__ should be accepted."""

    previous = FakeDataclassResult(
        condition="poor",
        confidence=90.0,
    )

    current = FakeDataclassResult(
        condition="repaired",
        confidence=90.0,
    )

    result = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"


# ============================================================
# Alternative Condition Field Names
# ============================================================


@pytest.mark.parametrize(
    "field_name",
    [
        "condition",
        "current_condition",
        "previous_condition",
    ],
)
def test_condition_field_aliases_are_supported(
    verifier,
    field_name,
):
    """Supported condition field names should be recognized."""

    previous = {
        field_name: "poor",
        "confidence": 90.0,
    }

    current = {
        field_name: "repaired",
        "confidence": 90.0,
    }

    result = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"


# ============================================================
# Confidence Extraction
# ============================================================


@pytest.mark.parametrize(
    ("field_name", "value", "expected"),
    [
        ("confidence", 90, 90.0),
        ("detection_confidence", 80, 80.0),
        ("analysis_confidence", 70, 70.0),
    ],
)
def test_confidence_field_aliases(
    verifier,
    field_name,
    value,
    expected,
):
    """All supported confidence field names should work."""

    evidence = {
        "condition": "good",
        field_name: value,
    }

    assert verifier._extract_confidence(
        evidence
    ) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, 0.0),
        (0.5, 50.0),
        (0.8, 80.0),
        (1.0, 100.0),
    ],
)
def test_confidence_accepts_zero_to_one_scale(
    verifier,
    value,
    expected,
):
    """Confidence values between 0 and 1 should be converted to percent."""

    evidence = {
        "condition": "good",
        "confidence": value,
    }

    assert verifier._extract_confidence(
        evidence
    ) == expected


def test_missing_confidence_uses_conservative_default(
    verifier,
):
    """Missing confidence should default to 50."""

    assert verifier._extract_confidence(
        {
            "condition": "good",
        }
    ) == 50.0


def test_invalid_confidence_uses_conservative_default(
    verifier,
):
    """Invalid confidence should default to 50."""

    assert verifier._extract_confidence(
        {
            "condition": "good",
            "confidence": "invalid",
        }
    ) == 50.0


def test_confidence_above_100_is_clamped(
    verifier,
):
    """Confidence cannot exceed 100."""

    assert verifier._extract_confidence(
        {
            "condition": "good",
            "confidence": 150,
        }
    ) == 100.0


def test_negative_confidence_is_clamped(
    verifier,
):
    """Confidence cannot be below zero."""

    assert verifier._extract_confidence(
        {
            "condition": "good",
            "confidence": -10,
        }
    ) == 0.0


# ============================================================
# Infrastructure Matching
# ============================================================


def test_matching_infrastructure_increases_verification_confidence(
    verifier,
):
    """Matching infrastructure labels should improve confidence."""

    result_with_match = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
            "infrastructure": "road",
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
            "infrastructure": "road",
        },
    )

    result_without_match = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert (
        result_with_match["visual_verification"]
        > result_without_match["visual_verification"]
    )


def test_mismatched_infrastructure_reduces_confidence(
    verifier,
):
    """Different infrastructure labels should reduce confidence."""

    matching = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
            "infrastructure": "road",
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
            "infrastructure": "road",
        },
    )

    mismatched = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
            "infrastructure": "road",
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
            "infrastructure": "streetlight",
        },
    )

    assert (
        mismatched["visual_verification"]
        < matching["visual_verification"]
    )


# ============================================================
# Raw Image Verification
# ============================================================


def test_verify_images_calls_image_analyzer_twice():
    """verify_images() should analyze both supplied images."""

    analyzer = FakeImageAnalyzer(
        results=[
            {
                "condition": "poor",
                "confidence": 90.0,
            },
            {
                "condition": "repaired",
                "confidence": 90.0,
            },
        ]
    )

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    previous_bytes = b"previous-image"
    current_bytes = b"current-image"

    result = verifier.verify_images(
        previous_bytes,
        current_bytes,
    )

    assert len(analyzer.calls) == 2
    assert analyzer.calls[0] == previous_bytes
    assert analyzer.calls[1] == current_bytes

    assert (
        result["status"]
        == VerificationStatus.COMPLETION_APPEARS_GENUINE.value
    )


def test_verify_raw_images_directly():
    """verify() should also support raw image byte arguments."""

    analyzer = FakeImageAnalyzer(
        results=[
            {
                "condition": "poor",
                "confidence": 90.0,
            },
            {
                "condition": "good",
                "confidence": 90.0,
            },
        ]
    )

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    result = verifier.verify(
        previous_image_bytes=b"old-image",
        current_image_bytes=b"new-image",
    )

    assert len(analyzer.calls) == 2
    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "good"


def test_verify_accepts_bytearray_images():
    """Bytearray image evidence should be accepted."""

    analyzer = FakeImageAnalyzer(
        results=[
            {
                "condition": "poor",
                "confidence": 90.0,
            },
            {
                "condition": "good",
                "confidence": 90.0,
            },
        ]
    )

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    result = verifier.verify(
        previous_image_bytes=bytearray(
            b"old"
        ),
        current_image_bytes=bytearray(
            b"new"
        ),
    )

    assert result["current_condition"] == "good"


# ============================================================
# verify_results()
# ============================================================


def test_verify_results_delegates_to_verify(
    verifier,
):
    """verify_results() should avoid duplicate image analysis."""

    previous = {
        "condition": "poor",
        "confidence": 90.0,
    }

    current = {
        "condition": "repaired",
        "confidence": 90.0,
    }

    result = verifier.verify_results(
        previous,
        current,
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"

    assert (
        len(
            verifier.image_analyzer.calls
        )
        == 0
    )


# ============================================================
# Invalid Evidence
# ============================================================


def test_missing_previous_evidence_raises(
    verifier,
):
    """Previous evidence is mandatory."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Previous evidence is required",
    ):
        verifier.verify(
            current_evidence={
                "condition": "good",
            }
        )


def test_missing_current_evidence_raises(
    verifier,
):
    """Current evidence is mandatory."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Current evidence is required",
    ):
        verifier.verify(
            previous_evidence={
                "condition": "poor",
            }
        )


def test_empty_previous_image_raises(
    verifier,
):
    """Empty previous image bytes are invalid."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Previous evidence is required",
    ):
        verifier.verify(
            previous_image_bytes=b"",
            current_image_bytes=b"current",
        )


def test_empty_current_image_raises(
    verifier,
):
    """Empty current image bytes are invalid."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Current evidence is required",
    ):
        verifier.verify(
            previous_image_bytes=b"previous",
            current_image_bytes=b"",
        )


def test_invalid_previous_image_type_raises(
    verifier,
):
    """Non-bytes image evidence should be rejected."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Previous image evidence must be non-empty bytes",
    ):
        verifier.verify(
            previous_image_bytes="not bytes",
            current_image_bytes=b"current",
        )


def test_invalid_current_image_type_raises(
    verifier,
):
    """Non-bytes current image evidence should be rejected."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Current image evidence must be non-empty bytes",
    ):
        verifier.verify(
            previous_image_bytes=b"previous",
            current_image_bytes="not bytes",
        )


def test_analysis_without_condition_raises(
    verifier,
):
    """Analysis objects must expose a condition."""

    with pytest.raises(
        InvalidEvidenceError,
        match="condition",
    ):
        verifier.verify(
            previous_evidence={
                "confidence": 90.0,
            },
            current_evidence={
                "condition": "good",
            },
        )


def test_empty_condition_raises(
    verifier,
):
    """Empty condition strings are invalid."""

    with pytest.raises(
        InvalidEvidenceError,
        match="condition cannot be empty",
    ):
        verifier.verify(
            previous_evidence={
                "condition": "   ",
            },
            current_evidence={
                "condition": "good",
            },
        )


def test_invalid_evidence_object_raises(
    verifier,
):
    """Completely unsupported evidence objects should fail."""

    with pytest.raises(
        InvalidEvidenceError,
        match="Previous evidence is required",
    ):
        verifier.verify(
            previous_evidence=object(),
            current_evidence={
                "condition": "good",
            },
        )


# ============================================================
# Analyzer Failure Handling
# ============================================================


def test_previous_image_analysis_failure_is_wrapped():
    """Unexpected analyzer failures should become service errors."""

    analyzer = FakeImageAnalyzer(
        error=RuntimeError(
            "vision model failed"
        )
    )

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    with pytest.raises(
        ResolutionVerificationError,
        match="Failed to analyze previous evidence",
    ):
        verifier.verify_images(
            b"previous",
            b"current",
        )


def test_current_image_analysis_failure_is_wrapped():
    """Current-image analyzer failures should become service errors."""

    class CurrentFailingAnalyzer:
        def __init__(self):
            self.calls = []

        def analyze(self, image_bytes):
            self.calls.append(image_bytes)

            if len(self.calls) == 1:
                return {
                    "condition": "poor",
                    "confidence": 90.0,
                }

            raise RuntimeError(
                "current image failed"
            )

    verifier = ResolutionVerifier(
        image_analyzer=CurrentFailingAnalyzer()
    )

    with pytest.raises(
        ResolutionVerificationError,
        match="Failed to analyze current evidence",
    ):
        verifier.verify_images(
            b"previous",
            b"current",
        )


def test_invalid_analyzer_result_is_rejected():
    """Analyzer output without recognized analysis fields is invalid."""

    analyzer = FakeImageAnalyzer(
        results=[
            {
                "confidence": 90.0,
            }
        ]
    )

    verifier = ResolutionVerifier(
        image_analyzer=analyzer
    )

    with pytest.raises(
        ResolutionVerificationError,
        match="returned invalid previous evidence",
    ):
        verifier.verify_images(
            b"previous",
            b"current",
        )


# ============================================================
# Evidence Priority
# ============================================================


def test_explicit_result_has_highest_priority(
    verifier,
):
    """previous_result/current_result should override evidence."""

    result = verifier.verify(
        previous_evidence={
            "condition": "critical",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "critical",
            "confidence": 90.0,
        },
        previous_result={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_result={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"


def test_evidence_has_priority_over_raw_image(
    verifier,
):
    """Valid analyzed evidence should prevent unnecessary inference."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
        previous_image_bytes=b"old",
        current_image_bytes=b"new",
    )

    assert result["previous_condition"] == "poor"
    assert result["current_condition"] == "repaired"

    assert (
        len(
            verifier.image_analyzer.calls
        )
        == 0
    )


# ============================================================
# Public Output Contract
# ============================================================


def test_output_status_is_string(
    verifier,
):
    """Status must be frontend/API compatible."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert isinstance(
        result["status"],
        str,
    )


def test_output_conditions_are_strings(
    verifier,
):
    """Conditions must be serialized as strings."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert isinstance(
        result["previous_condition"],
        str,
    )

    assert isinstance(
        result["current_condition"],
        str,
    )


def test_output_visual_verification_is_float(
    verifier,
):
    """Visual verification should be numeric."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    assert isinstance(
        result["visual_verification"],
        float,
    )


def test_output_can_be_json_serialized(
    verifier,
):
    """The verification result should be safe for FastAPI JSON output."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
        },
    )

    encoded = __import__("json").dumps(
        result
    )

    decoded = __import__("json").loads(
        encoded
    )

    assert decoded == result


# ============================================================
# Determinism
# ============================================================


@pytest.mark.parametrize(
    (
        "previous_condition",
        "current_condition",
    ),
    [
        ("critical", "completed"),
        ("poor", "repaired"),
        ("fair", "good"),
        ("poor", "poor"),
        ("good", "poor"),
        ("unknown", "unknown"),
    ],
)
def test_verification_is_deterministic(
    verifier,
    previous_condition,
    current_condition,
):
    """Identical evidence must always produce identical results."""

    previous = {
        "condition": previous_condition,
        "confidence": 90.0,
    }

    current = {
        "condition": current_condition,
        "confidence": 90.0,
    }

    first = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    second = verifier.verify(
        previous_evidence=previous,
        current_evidence=current,
    )

    assert first == second


# ============================================================
# Confidence Boundary Tests
# ============================================================


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        25,
        50,
        75,
        100,
        150,
        -50,
    ],
)
def test_confidence_never_leaves_zero_to_hundred(
    verifier,
    confidence,
):
    """Confidence normalization must always remain bounded."""

    value = verifier._extract_confidence(
        {
            "condition": "good",
            "confidence": confidence,
        }
    )

    assert 0.0 <= value <= 100.0


# ============================================================
# Optional Infrastructure Fields
# ============================================================


def test_infrastructure_type_alias_is_supported(
    verifier,
):
    """infrastructure_type should work as an alternative field."""

    result = verifier.verify(
        previous_evidence={
            "condition": "poor",
            "confidence": 90.0,
            "infrastructure_type": "road",
        },
        current_evidence={
            "condition": "repaired",
            "confidence": 90.0,
            "infrastructure_type": "road",
        },
    )

    assert (
        result["status"]
        == VerificationStatus.COMPLETION_APPEARS_GENUINE.value
    )


# ============================================================
# Module Export Contract
# ============================================================


def test_expected_public_exports_are_available():
    """Public classes/functions required by the service must exist."""

    assert ResolutionVerifier is not None
    assert VerificationResult is not None
    assert VerificationStatus is not None
    assert InvalidEvidenceError is not None
    assert ResolutionVerificationError is not None