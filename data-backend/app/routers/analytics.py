"""
GET /analytics/district — the numbers behind the dashboard's summary
cards and charts (Section: "Government dashboard shows summary cards
... and analytics charts" in the MVP checklist).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/district", response_model=list[schemas.DistrictAnalyticsOut])
def district_analytics(db: Session = Depends(get_db)):
    districts = db.query(models.Project.district).distinct().all()
    results = []

    for (district,) in districts:
        if not district:
            continue
        q = db.query(models.Project).filter(models.Project.district == district)
        projects = q.all()
        total = len(projects)
        if total == 0:
            continue

        deviations = [p.progress_deviation for p in projects if p.progress_deviation is not None]
        avg_dev = sum(deviations) / len(deviations) if deviations else None

        delayed = sum(1 for p in projects if p.current_status.value in ("DELAYED", "STALLED"))
        completed = sum(1 for p in projects if p.current_status.value == "COMPLETED")
        verified = sum(1 for p in projects if p.current_status.value == "VERIFIED")
        total_budget = sum(float(p.budget_allocated) for p in projects if p.budget_allocated is not None) or None

        results.append(schemas.DistrictAnalyticsOut(
            district=district,
            total_projects=total,
            avg_deviation=round(avg_dev, 2) if avg_dev is not None else None,
            delayed_count=delayed,
            completed_count=completed,
            verified_count=verified,
            total_budget_allocated=total_budget,
        ))

    return results
