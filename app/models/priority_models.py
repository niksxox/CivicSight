"""
CivSight AI Infrastructure Intelligence

Pydantic schemas for infrastructure/project priority scoring.

These models define the data contract between:
    API -> Priority Scoring Service -> API/Frontend

The schemas contain validation only.
Priority calculation and weighting belong in
services/priority_scorer.py.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PriorityAssessmentRequest(BaseModel):
    """
    Inputs used by the deterministic priority-scoring service.

    The scoring service is responsible for:
    - normalization
    - applying weights
    - calculating the final score
    - mapping the score to a priority level
    - generating a recommended action
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_delay: float = Field(
        ge=0.0,
        le=100.0,
        description="Project delay percentage.",
    )

    infrastructure_condition: str = Field(
        min_length=1,
        max_length=100,
        description="Current observed infrastructure condition.",
    )

    population_affected: int = Field(
        ge=0,
        description="Estimated number of people affected.",
    )

    project_importance: str = Field(
        min_length=1,
        max_length=100,
        description="Importance or criticality of the project.",
    )

    issue_severity: str = Field(
        min_length=1,
        max_length=100,
        description="Severity of the identified infrastructure issue.",
    )

    duration: float = Field(
        ge=0.0,
        description="Duration of the issue or delay, in the agreed project time unit.",
    )

    historical_data: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional historical information relevant to priority scoring. "
            "The scoring service determines which historical fields are used."
        ),
    )


class PriorityAssessmentResponse(BaseModel):
    """
    Result returned by the priority-scoring service.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    priority_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Final priority score from 0 to 100.",
    )

    priority: str = Field(
        min_length=1,
        max_length=50,
        description="Priority level derived from the final score.",
    )

    recommended_action: str | None = Field(
        default=None,
        max_length=500,
        description="Optional recommended action based on the priority result.",
    )

    factors: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Normalized factor scores used by the deterministic scorer. "
            "Each value is between 0 and 100."
        ),
    )

