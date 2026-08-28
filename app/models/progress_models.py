"""
CivSight AI Infrastructure Intelligence

Pydantic schemas for project progress assessment.

These models define the data contract between:
    API -> Progress Assessment Service -> API/Frontend

The schemas contain validation only.
Progress estimation and status calculation belong in
services/progress_assessor.py.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProgressAssessmentRequest(BaseModel):
    """
    Request payload for assessing project progress.

    planned_progress:
        Expected project completion percentage.

    estimated_actual_progress:
        AI-estimated current completion percentage based on
        available evidence.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    planned_progress: float = Field(
        ge=0.0,
        le=100.0,
        description="Planned project completion percentage.",
    )

    estimated_actual_progress: float = Field(
        ge=0.0,
        le=100.0,
        description="AI-estimated actual project completion percentage.",
    )


class ProgressAssessmentResponse(BaseModel):
    """
    Validated project progress assessment result.

    deviation is calculated as:

        estimated_actual_progress - planned_progress

    A negative value indicates that the estimated actual progress
    is behind the planned progress.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    planned_progress: float = Field(
        ge=0.0,
        le=100.0,
        description="Planned project completion percentage.",
    )

    estimated_actual_progress: float = Field(
        ge=0.0,
        le=100.0,
        description="AI-estimated actual project completion percentage.",
    )

    deviation: float = Field(
        ge=-100.0,
        le=100.0,
        description=(
            "Difference between estimated actual progress and "
            "planned progress."
        ),
    )

    status: Literal["ahead", "on_track", "delayed"] = Field(
        description="Deterministic project progress status.",
    )