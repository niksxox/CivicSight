"""
CivicSight AI Infrastructure Intelligence

FastAPI route definitions for the AI service.

Responsibilities:
- Receive HTTP requests.
- Validate uploaded files.
- Validate request data.
- Call service-layer functions/classes.
- Validate service responses.
- Convert expected failures into safe HTTP responses.

Business/AI logic remains inside service modules.

Endpoints:
    POST /ai/analyze-image
    POST /ai/extract-issue
    POST /ai/assess-progress
    POST /ai/calculate-priority
    POST /ai/verify-resolution
"""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from app.models.image_models import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
)

from app.models.progress_models import (
    ProgressAssessmentRequest,
    ProgressAssessmentResponse,
)


# Router


router = APIRouter(
    prefix="/ai",
    tags=[
        "AI Infrastructure Intelligence"
    ],
)


# API request models


class IssueExtractionRequest(BaseModel):
    """
    Request body for natural-language issue extraction.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description=(
            "Citizen or field-officer infrastructure description."
        ),
    )


class PriorityCalculationRequest(BaseModel):
    """
    Request body for deterministic priority calculation.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_delay: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Project delay percentage."
        ),
    )

    infrastructure_condition: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "Current infrastructure condition."
        ),
    )

    population_affected: float = Field(
        ...,
        ge=0.0,
        description=(
            "Estimated number of affected people."
        ),
    )

    project_importance: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Project importance score."
        ),
    )

    issue_severity: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description=(
            "Issue severity."
        ),
    )

    duration: float = Field(
        ...,
        ge=0.0,
        description=(
            "Issue/project duration in days."
        ),
    )

    historical_data: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Historical risk/incident score."
        ),
    )


class ResolutionVerificationRequest(BaseModel):
    """
    Metadata accompanying resolution evidence.

    Evidence files themselves are uploaded through multipart
    form-data.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    previous_condition: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "Condition observed in previous evidence."
        ),
    )

    previous_result: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "Previous analysis result or claimed status."
        ),
    )


# File configuration


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


MAX_IMAGE_UPLOAD_BYTES = (
    15 * 1024 * 1024
)


# Error handling


def _raise_service_error(
    operation: str,
    exc: Exception,
) -> None:
    """
    Convert internal service failures into safe HTTP errors.

    Internal implementation details are intentionally hidden.
    """

    if isinstance(
        exc,
        HTTPException,
    ):
        raise exc

    if isinstance(
        exc,
        ValidationError,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"Invalid data for {operation}."
            ),
        ) from exc

    # Service-specific validation errors.
    if exc.__class__.__name__.startswith(
        "Invalid"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"Invalid data for {operation}."
            ),
        ) from exc

    # Invalid image input should be a client error.
    if exc.__class__.__name__ == (
        "InvalidImageError"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Invalid image data."
            ),
        ) from exc

    # Model loading/inference failures are server-side.
    raise HTTPException(
        status_code=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        detail=f"{operation} failed.",
    ) from exc


# Uploaded file validation


async def _read_uploaded_file(
    uploaded_file: UploadFile,
    *,
    allowed_content_types: set[str],
    max_bytes: int,
) -> bytes:
    """
    Safely read an uploaded file.

    FastAPI-specific UploadFile objects are converted to bytes
    before entering the service layer.
    """

    if not uploaded_file.filename:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Uploaded file must have a filename."
            ),
        )

    content_type = (
        uploaded_file.content_type
    )

    if content_type not in allowed_content_types:

        raise HTTPException(
            status_code=(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                "Unsupported file type."
            ),
        )

    data = await uploaded_file.read()

    if not data:

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Uploaded file is empty."
            ),
        )

    if len(data) > max_bytes:

        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "Uploaded file is too large."
            ),
        )

    return data


# Image metadata validation


def _validate_image_metadata(
    filename: str | None,
    content_type: str | None,
) -> ImageAnalysisRequest:
    """
    Validate image metadata using the shared Pydantic contract.
    """

    try:

        return ImageAnalysisRequest(
            filename=filename,
            content_type=content_type,
        )

    except ValidationError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Invalid image metadata."
            ),
        ) from exc


# POST /ai/analyze-image


@router.post(
    "/analyze-image",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze infrastructure image",
    description=(
        "Analyze uploaded infrastructure evidence and return "
        "the identified infrastructure, issue, condition, "
        "confidence, severity, and visual classifications."
    ),
)
async def analyze_image(
    image: UploadFile = File(
        ...,
        description=(
            "Infrastructure image."
        ),
    ),
) -> ImageAnalysisResponse:
    """
    Analyze an uploaded infrastructure image.

    Flow:

        HTTP upload
            ↓
        validation
            ↓
        image bytes
            ↓
        ImageAnalyzer
            ↓
        ImageAnalysisResponse
    """

    image_bytes = await _read_uploaded_file(
        image,
        allowed_content_types=(
            ALLOWED_IMAGE_CONTENT_TYPES
        ),
        max_bytes=MAX_IMAGE_UPLOAD_BYTES,
    )

    metadata = _validate_image_metadata(
        filename=image.filename,
        content_type=image.content_type,
    )

    try:

        from app.services.image_analyzer import (
            ImageAnalyzer,
        )

        analyzer = ImageAnalyzer()

        result = analyzer.analyze(
            image_bytes,
            filename=metadata.filename,
            content_type=metadata.content_type,
        )

        return ImageAnalysisResponse.model_validate(
            result
        )

    except Exception as exc:

        _raise_service_error(
            "image analysis",
            exc,
        )

    raise AssertionError(
        "Unreachable"
    )


# POST /ai/extract-issue


@router.post(
    "/extract-issue",
    status_code=status.HTTP_200_OK,
    summary="Extract structured issue information",
    description=(
        "Convert a natural-language infrastructure "
        "description into structured issue information."
    ),
)
async def extract_issue(
    request: IssueExtractionRequest,
) -> Any:
    """
    Extract structured information from natural language.

    The LLM service remains responsible for:
    - prompting
    - model invocation
    - parsing
    - validation
    - hallucination prevention
    """

    try:

        from app.services.llm_extractor import (
            LLMExtractor,
        )

        extractor = LLMExtractor()

        result = extractor.extract(
            request.text
        )

        return result

    except Exception as exc:

        _raise_service_error(
            "issue extraction",
            exc,
        )

    raise AssertionError(
        "Unreachable"
    )


# POST /ai/assess-progress


@router.post(
    "/assess-progress",
    response_model=ProgressAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess project progress",
    description=(
        "Compare planned progress with estimated actual "
        "progress and return deviation and project status."
    ),
)
async def assess_progress(
    request: ProgressAssessmentRequest,
) -> ProgressAssessmentResponse:
    """
    Assess project progress.
    """

    try:

        from app.services.progress_assessor import (
            ProgressAssessor,
        )

        assessor = ProgressAssessor()

        result = assessor.assess(
            planned_progress=(
                request.planned_progress
            ),
            estimated_actual_progress=(
                request.estimated_actual_progress
            ),
        )

        return ProgressAssessmentResponse.model_validate(
            result
        )

    except Exception as exc:

        _raise_service_error(
            "progress assessment",
            exc,
        )

    raise AssertionError(
        "Unreachable"
    )


# POST /ai/calculate-priority


@router.post(
    "/calculate-priority",
    status_code=status.HTTP_200_OK,
    summary="Calculate infrastructure priority",
    description=(
        "Calculate deterministic infrastructure/project "
        "priority from delay, condition, population, "
        "importance, severity, duration, and historical data."
    ),
)
async def calculate_priority(
    request: PriorityCalculationRequest,
) -> dict[str, Any]:
    """
    Calculate infrastructure/project priority.

    The scoring algorithm remains inside priority_scorer.py.
    """

    try:

        from app.services.priority_scorer import (
            PriorityScorer,
        )

        scorer = PriorityScorer()

        result = scorer.calculate(
            project_delay=(
                request.project_delay
            ),
            infrastructure_condition=(
                request.infrastructure_condition
            ),
            population_affected=(
                request.population_affected
            ),
            project_importance=(
                request.project_importance
            ),
            issue_severity=(
                request.issue_severity
            ),
            duration=(
                request.duration
            ),
            historical_data=(
                request.historical_data
            ),
        )

        return result

    except Exception as exc:

        _raise_service_error(
            "priority calculation",
            exc,
        )

    raise AssertionError(
        "Unreachable"
    )


# POST /ai/verify-resolution



@router.post(
    "/verify-resolution",
    status_code=status.HTTP_200_OK,
    summary="Verify claimed infrastructure resolution",
    description=(
        "Compare previous and current infrastructure "
        "evidence to determine whether a claimed repair "
        "or completion appears genuine."
    ),
)
async def verify_resolution(
    previous_evidence: UploadFile = File(
        ...,
        description=(
            "Previous infrastructure evidence."
        ),
    ),
    new_evidence: UploadFile = File(
        ...,
        description=(
            "Current infrastructure evidence."
        ),
    ),
    previous_condition: str = Form(
        ...,
        description=(
            "Previously observed infrastructure condition."
        ),
    ),
    previous_result: str = Form(
        ...,
        description=(
            "Previous analysis result or claimed status."
        ),
    ),
) -> Any:
    """
    Verify a claimed infrastructure repair/completion.
    """

    
    # Validate metadata

    try:

        metadata = ResolutionVerificationRequest(
            previous_condition=(
                previous_condition
            ),
            previous_result=(
                previous_result
            ),
        )

    except ValidationError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Invalid resolution metadata."
            ),
        ) from exc

    # Read previous evidence

    previous_bytes = await _read_uploaded_file(
        previous_evidence,
        allowed_content_types=(
            ALLOWED_IMAGE_CONTENT_TYPES
        ),
        max_bytes=MAX_IMAGE_UPLOAD_BYTES,
    )

    # Read new evidence
    

    new_bytes = await _read_uploaded_file(
        new_evidence,
        allowed_content_types=(
            ALLOWED_IMAGE_CONTENT_TYPES
        ),
        max_bytes=MAX_IMAGE_UPLOAD_BYTES,
    )

    # Call service

    try:

        from app.services.resolution_verifier import (
            ResolutionVerifier,
        )

        verifier = ResolutionVerifier()

        result = verifier.verify(
            previous_evidence=previous_bytes,
            previous_condition=(
                metadata.previous_condition
            ),
            previous_result=(
                metadata.previous_result
            ),
            new_evidence=new_bytes,
        )

        return result

    except Exception as exc:

        _raise_service_error(
            "resolution verification",
            exc,
        )

    raise AssertionError(
        "Unreachable"
    )


# Abandonment & Recommendation Models and Endpoints


class AbandonmentDetectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    months_since_inspection: float = Field(0.0, ge=0.0)
    citizen_report_count: int = Field(1, ge=0)
    visual_tags: list[str] | None = None


class ActionRecommendationRequest(BaseModel):
    facility_type: str = Field(..., min_length=1)
    facility_name: str = Field(..., min_length=1)
    district: str = Field(..., min_length=1)
    abandonment_score: float = Field(..., ge=0.0, le=100.0)
    population_catchment: int = Field(..., ge=0)
    distance_to_alternative_km: float = Field(2.0, ge=0.0)
    has_structural_integrity: bool = True


@router.post(
    "/detect-abandonment",
    summary="Detect infrastructure abandonment or underutilization",
)
async def detect_abandonment_endpoint(request: AbandonmentDetectionRequest) -> dict[str, Any]:
    from app.services.abandonment_detector import detect_abandonment

    try:
        return detect_abandonment(
            text=request.text,
            months_since_inspection=request.months_since_inspection,
            citizen_report_count=request.citizen_report_count,
            visual_tags=request.visual_tags,
        )
    except Exception as exc:
        _raise_service_error("abandonment detection", exc)


@router.post(
    "/recommend-action",
    summary="Generate strategic civic recommendation (Repair, Repurpose, or Develop)",
)
async def recommend_action_endpoint(request: ActionRecommendationRequest) -> dict[str, Any]:
    from app.services.recommendation_engine import generate_recommendation

    try:
        return generate_recommendation(
            facility_type=request.facility_type,
            facility_name=request.facility_name,
            district=request.district,
            abandonment_score=request.abandonment_score,
            population_catchment=request.population_catchment,
            distance_to_alternative_km=request.distance_to_alternative_km,
            has_structural_integrity=request.has_structural_integrity,
        )
    except Exception as exc:
        _raise_service_error("action recommendation", exc)


# Public exports


__all__ = [
    "router",
]