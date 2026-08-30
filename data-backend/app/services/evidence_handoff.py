from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import models
from app.config import settings


@dataclass(frozen=True)
class AiEvidenceResult:
    ai_condition: str
    ai_confidence: float
    ai_issue: str | None = None


def apply_ai_evidence_result(db: Session, evidence_id: int, result: AiEvidenceResult) -> models.CitizenEvidence:
    """
    Handoff point for the AI/image-analysis teammate.

    Input: existing citizen_evidence row plus ai_condition/ai_confidence.
    Destination: citizen_evidence.ai_condition, ai_issue, ai_confidence,
    needs_human_review.
    """
    evidence = db.get(models.CitizenEvidence, evidence_id)
    if evidence is None:
        raise ValueError(f"citizen_evidence id {evidence_id} was not found")
    evidence.ai_condition = result.ai_condition
    evidence.ai_issue = result.ai_issue
    evidence.ai_confidence = result.ai_confidence
    evidence.needs_human_review = result.ai_confidence < settings.ai_confidence_threshold
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence
