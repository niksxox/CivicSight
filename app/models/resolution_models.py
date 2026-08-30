"""
CivSight AI Infrastructure Intelligence

Pydantic schemas for resolution and progress verification.

These models define the data contract between:
    API -> Resolution Verification Service -> API/Frontend

The schemas contain validation only.
Evidence comparison and verification logic belong in
services/resolution_verifier.py.
"""

from pydantic import BaseModel, ConfigDict, Field


class ResolutionVerificationRequest(BaseModel):
    """
    Request payload for verifying whether an infrastructure issue
    appears to have been resolved based on previous and new evidence.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    previous_evidence: str = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Reference to or description of the previous evidence "
            "showing the earlier infrastructure condition."
        ),
    )

    previous_condition: str = Field(
        min_length=1,
        max_length=100,
        description="Condition observed in the previous evidence.",
    )

    previous_result: str | None = Field(
        default=None,
        max_length=1_000,
        description=(
            "Previous analysis result or reported project state, "
            "when available."
        ),
    )

    new_evidence: str = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Reference to or description of the new evidence "
            "showing the current infrastructure condition."
        ),
    )


class ResolutionVerificationResponse(BaseModel):
    """
    Result returned by the resolution verification service.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    previous_condition: str = Field(
        min_length=1,
        max_length=100,
        description="Condition identified from the previous evidence.",
    )

    current_condition: str = Field(
        min_length=1,
        max_length=100,
        description="Condition identified from the new evidence.",
    )

    visual_verification: float = Field(
        ge=0.0,
        le=100.0,
        description=(
            "Evidence-based visual verification confidence as a "
            "percentage from 0 to 100. It is not proof of repair."
        ),
    )

    status: str = Field(
        min_length=1,
        max_length=100,
        description="Evidence-based resolution verification status.",
    )