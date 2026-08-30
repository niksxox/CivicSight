"""
Data/analytics APIs owned by Nikita.

Reminder of the split (Section F of the spec):
  Nikita  -> these routers: data + analytics endpoints, read-heavy.
  Chetan  -> separate app/business API service that WRITES
             (assign officer, update status, verify completion etc).
This service is intentionally read-only past ingestion, so there's
no endpoint here that mutates a project's status.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app import models, schemas
from app.geo_utils import nearby_facilities, estimate_nearby_population, nearby_road_segments

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_out(p: models.Project, lat: float, lng: float) -> schemas.ProjectOut:
    return schemas.ProjectOut(
        id=p.id,
        external_ref=p.external_ref,
        name=p.name,
        category=p.category,
        department=p.department,
        district=p.district,
        state=p.state,
        latitude=lat,
        longitude=lng,
        budget_allocated=float(p.budget_allocated) if p.budget_allocated is not None else None,
        budget_spent=float(p.budget_spent) if p.budget_spent is not None else None,
        planned_start=p.planned_start,
        planned_end=p.planned_end,
        planned_progress=float(p.planned_progress) if p.planned_progress is not None else None,
        actual_progress=float(p.actual_progress) if p.actual_progress is not None else None,
        progress_deviation=p.progress_deviation,
        current_status=p.current_status.value if hasattr(p.current_status, "value") else p.current_status,
        priority_score=float(p.priority_score) if p.priority_score is not None else None,
        updated_at=p.updated_at,
    )


def _get_lat_lng(db: Session, project_id: int):
    """
    PostGIS stores location as a geography(POINT). We pull lat/lng back
    out as plain floats here so the API never leaks raw WKB to clients.
    """
    from sqlalchemy import text
    r = db.execute(
        text("SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng FROM projects WHERE id = :id"),
        {"id": project_id},
    ).mappings().first()
    return (r["lat"], r["lng"]) if r else (None, None)


@router.get("", response_model=schemas.ProjectListOut)
def list_projects(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by current_status, e.g. DELAYED"),
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_deviation: Optional[float] = Query(None, description="Only projects with deviation <= this (e.g. -20)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List projects with optional filters. This is the main feed for
    the government dashboard's project table / map.
    """
    q = db.query(models.Project)
    if status:
        q = q.filter(models.Project.current_status == status)
    if district:
        q = q.filter(models.Project.district == district)
    if category:
        q = q.filter(models.Project.category == category)

    total = q.count()
    rows = q.order_by(models.Project.updated_at.desc()).offset(offset).limit(limit).all()

    items = []
    for p in rows:
        lat, lng = _get_lat_lng(db, p.id)
        out = _to_project_out(p, lat, lng)
        if min_deviation is not None and (out.progress_deviation is None or out.progress_deviation > min_deviation):
            continue
        items.append(out)

    return schemas.ProjectListOut(total=total, items=items)


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    lat, lng = _get_lat_lng(db, project_id)
    return _to_project_out(p, lat, lng)


@router.get("/{project_id}/nearby", response_model=schemas.NearbyOut)
def get_project_nearby(project_id: int, db: Session = Depends(get_db), radius: int = Query(None)):
    """
    Nearby population + critical facilities + a plain-English
    connectivity note (e.g. "this road delay affects hospital access").
    This is the "much more meaningful than just saying delayed"
    feature from Section D of the spec.
    """
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    radius_m = radius or settings.nearby_radius_meters
    lat, lng = _get_lat_lng(db, project_id)

    facilities_rows = nearby_facilities(db, lat, lng, radius_m)
    population = estimate_nearby_population(db, lat, lng, radius_m)
    roads = nearby_road_segments(db, lat, lng, radius_m)

    facilities_out = [
        schemas.NearbyFacilityOut(id=f["id"], name=f["name"], type=f["type"], distance_meters=round(f["distance_m"], 1))
        for f in facilities_rows
    ]

    notes = []
    is_behind = p.progress_deviation is not None and p.progress_deviation < -10
    if is_behind and p.category.lower() == "road" and roads:
        hospitals = [f for f in facilities_out if f.type == "hospital"]
        schools = [f for f in facilities_out if f.type == "school"]
        if hospitals:
            notes.append(
                f"This road project is {abs(p.progress_deviation):.0f}% behind schedule and sits within "
                f"{radius_m}m of {len(hospitals)} hospital(s) — delays may be affecting emergency access."
            )
        if schools:
            notes.append(
                f"{len(schools)} school(s) are within {radius_m}m; a stalled road here can affect daily commute for students."
            )
    if population:
        notes.append(f"An estimated {population:,} people live within {radius_m}m of this project.")
    if not notes:
        notes.append("No significant connectivity impact detected for the current radius.")

    return schemas.NearbyOut(
        project_id=project_id,
        radius_meters=radius_m,
        estimated_nearby_population=population,
        facilities=facilities_out,
        connectivity_notes=notes,
    )


@router.get("/{project_id}/analytics", response_model=schemas.AnalyticsOut)
def get_project_analytics(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    today = date.today()
    days_elapsed = (today - p.planned_start).days if p.planned_start else None
    days_remaining = (p.planned_end - today).days if p.planned_end else None

    deviation = p.progress_deviation
    if deviation is None:
        health = "unknown"
    elif deviation >= 0:
        health = "ahead" if deviation > 2 else "on_track"
    elif deviation >= -10:
        health = "on_track"
    else:
        health = "behind"

    reports_count = db.query(func.count(models.CitizenEvidence.id)).filter(
        models.CitizenEvidence.project_id == project_id
    ).scalar()
    flags_count = db.query(func.count(models.CitizenEvidence.id)).filter(
        models.CitizenEvidence.project_id == project_id,
        models.CitizenEvidence.needs_human_review.is_(True),
    ).scalar()

    return schemas.AnalyticsOut(
        project_id=project_id,
        planned_progress=float(p.planned_progress) if p.planned_progress is not None else None,
        actual_progress=float(p.actual_progress) if p.actual_progress is not None else None,
        progress_deviation=deviation,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        schedule_health=health,
        citizen_reports_count=reports_count or 0,
        open_flags_needing_review=flags_count or 0,
    )


@router.get("/{project_id}/history", response_model=list[schemas.HistoryEntryOut])
def get_project_history(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    rows = (
        db.query(models.ProjectHistory)
        .filter(models.ProjectHistory.project_id == project_id)
        .order_by(models.ProjectHistory.recorded_at.desc())
        .all()
    )
    return [
        schemas.HistoryEntryOut(
            status=r.status.value if r.status else None,
            progress=float(r.progress) if r.progress is not None else None,
            note=r.note,
            source=r.source.value,
            recorded_at=r.recorded_at,
        )
        for r in rows
    ]
