"""
CivicSight AI Infrastructure Intelligence

Pydantic schemas for infrastructure image analysis.

These models define the data contract between:

    API
      ↓
    Image Analysis Service
      ↓
    API / Frontend

Responsibilities:
- Validate image-analysis request metadata.
- Validate individual classification detections.
- Validate the final image-analysis response.

Business logic remains inside the service layer.
These models do not perform AI inference or scoring.
"""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# Image Analysis Request


class ImageAnalysisRequest(BaseModel):
    """
    Metadata accompanying an uploaded infrastructure image.

    The actual image bytes are handled by FastAPI's UploadFile
    in the API layer.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Original image filename, when available."
        ),
    )

    content_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "MIME type of the uploaded image."
        ),
    )

    @field_validator(
        "filename",
        "content_type",
    )
    @classmethod
    def validate_metadata_text(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Reject metadata containing null characters.

        Null characters are not useful in filenames or MIME types
        and can create problems when values are passed to other
        systems.
        """

        if value is None:
            return None

        if "\x00" in value:
            raise ValueError(
                "Metadata cannot contain null characters."
            )

        return value


# Detection


class Detection(BaseModel):
    """
    Individual visual classification result.

    The current CivicSight image analyzer uses image-level
    classification rather than object detection.

    Therefore coordinates are normally null.

    If a future object-detection model is introduced, normalized
    coordinates can be supplied in the range 0.0-1.0.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    label: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Detected infrastructure issue or visual category."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Classification confidence between 0 and 1."
        ),
    )

    x_min: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized left coordinate. "
            "Null for classification-only results."
        ),
    )

    y_min: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized top coordinate. "
            "Null for classification-only results."
        ),
    )

    x_max: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized right coordinate. "
            "Null for classification-only results."
        ),
    )

    y_max: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized bottom coordinate. "
            "Null for classification-only results."
        ),
    )

    @model_validator(mode="after")
    def validate_bounding_box(
        self,
    ) -> "Detection":
        """
        Validate bounding-box consistency.

        Rules:

        1. All coordinates must be supplied together.
        2. If coordinates are absent, this is a classification
           result and is valid.
        3. If supplied:
             x_min <= x_max
             y_min <= y_max
        """

        coordinates = (
            self.x_min,
            self.y_min,
            self.x_max,
            self.y_max,
        )

        supplied_count = sum(
            coordinate is not None
            for coordinate in coordinates
        )

        # No coordinates = classification-only detection.
        if supplied_count == 0:
            return self

        # Partial coordinates are invalid.
        if supplied_count != 4:
            raise ValueError(
                "Bounding-box coordinates must either all be "
                "provided or all be null."
            )

        if self.x_min > self.x_max:
            raise ValueError(
                "x_min cannot be greater than x_max."
            )

        if self.y_min > self.y_max:
            raise ValueError(
                "y_min cannot be greater than y_max."
            )

        return self


# Image Analysis Response


class ImageAnalysisResponse(BaseModel):
    """
    Structured result returned after infrastructure image analysis.

    Contract:

        infrastructure
        detected_issue
        condition
        confidence
        severity
        detections
        metadata
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    infrastructure: str = Field(
        min_length=1,
        max_length=100,
        description=(
            "Identified infrastructure category."
        ),
    )

    detected_issue: str = Field(
        min_length=1,
        max_length=500,
        description=(
            "Primary visible infrastructure issue."
        ),
    )

    condition: str = Field(
        min_length=1,
        max_length=50,
        description=(
            "Observed infrastructure condition."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Overall analysis confidence between 0 and 1."
        ),
    )

    severity: str = Field(
        min_length=1,
        max_length=50,
        description=(
            "Initial visual severity estimate. Final workflow severity is calculated by the dedicated severity scorer."
        ),
    )

    detections: list[Detection] = Field(
        default_factory=list,
        description=(
            "Top visual classification results."
        ),
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Non-sensitive analysis metadata."
        ),
    )

    @field_validator(
        "infrastructure",
        "detected_issue",
        "condition",
        "severity",
    )
    @classmethod
    def validate_text_fields(
        cls,
        value: str,
    ) -> str:
        """
        Reject null characters from response text.
        """

        if "\x00" in value:
            raise ValueError(
                "Text fields cannot contain null characters."
            )

        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Ensure metadata remains a dictionary.

        Pydantic already validates the type; this method mainly
        protects against null-character keys.
        """

        for key in value:
            if "\x00" in str(key):
                raise ValueError(
                    "Metadata keys cannot contain null characters."
                )

        return value