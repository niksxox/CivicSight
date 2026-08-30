"""
Citizen-evidence AI handoff endpoint.

This is the documented integration point between the data backend and the
AI/image-analysis teammate (Avinash). The backend stores citizen evidence
and AI output but does NOT run any model. Another service calls this endpoint
with the analysis result and the backend persists it.

INPUT : existing citizen_evidence row + image-analysis result
OUTPUT: ai_condition, ai_issue, ai_confidence, needs_human_review
DEST  : citizen_evidence
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.services.evidence_handoff import AiEvidenceResult, apply_ai_evidence_result

router = APIRouter(prefix="/evidence", tags=["evidence"])


class AiEvidenceIn(BaseModel):
    ai_condition: str
    ai_confidence: float
    ai_issue: Optional[str] = None


class AiEvidenceOut(BaseModel):
    id: int
    ai_condition: Optional[str]
    ai_issue: Optional[str]
    ai_confidence: Optional[float]
    needs_human_review: Optional[bool]


@router.post("/{evidence_id}/ai-result", response_model=AiEvidenceOut)
def post_ai_result(evidence_id: int, payload: AiEvidenceIn, db: Session = Depends(get_db)):
    """
    Handoff point for the AI teammate. Apply an image-analysis result to an
    existing citizen_evidence row. Raises 404 if the evidence row is missing.
    """
    try:
        result = AiEvidenceResult(
            ai_condition=payload.ai_condition,
            ai_confidence=payload.ai_confidence,
            ai_issue=payload.ai_issue,
        )
        evidence = apply_ai_evidence_result(db, evidence_id, result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AiEvidenceOut(
        id=evidence.id,
        ai_condition=evidence.ai_condition,
        ai_issue=evidence.ai_issue,
        ai_confidence=float(evidence.ai_confidence) if evidence.ai_confidence is not None else None,
        needs_human_review=evidence.needs_human_review,
    )
