"""
CivicSight AI Infrastructure Intelligence

Pydantic schemas for structured issue extraction.

These models define the data contract between:
    API -> LLM Extraction Service -> API/Frontend
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProjectStatus = Literal[
    "planned",
    "ongoing",
    "delayed",
    "completed",
    "halted",
    "abandoned",
    "unknown",
]


class IssueExtractionRequest(BaseModel):
    """Request payload for structured issue extraction."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(
        min_length=1,
        max_length=10_000,
        description=(
            "Citizen or field-officer description "
            "to analyze."
        ),
    )


class IssueExtractionResponse(BaseModel):
    """
    Structured information extracted from project text.

    All fields may legitimately be None because the source
    description may not contain every piece of information.

    The LLM service itself requires the JSON object to contain
    all four keys. A key may have a null value.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_status: ProjectStatus | None = Field(
        default=None,
        description=(
            "Project status explicitly supported by "
            "the source text."
        ),
    )

    duration: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Duration explicitly mentioned in "
            "the source text."
        ),
    )

    estimated_completion: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Completion estimate explicitly supported "
            "by the source text."
        ),
    )

    issue: str | None = Field(
        default=None,
        max_length=1_000,
        description=(
            "Infrastructure or project issue described "
            "in the source text."
        ),
    )

    @field_validator("duration", "estimated_completion", "issue")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Text fields cannot contain null characters.")
        value = value.strip()
        return value or None


__all__ = [
    "ProjectStatus",
    "IssueExtractionRequest",
    "IssueExtractionResponse",
]