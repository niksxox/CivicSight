"""
GET /map/infrastructure — lightweight, map-ready feed of every project
as a colored pin. Deliberately a slimmer payload than /projects
(no budgets, no history) since this can return hundreds of points
that just need to render fast on the government dashboard's map.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/map", tags=["map"])

# Status -> dashboard pin color. Frontend can also hardcode this, but
# keeping the mapping here means Nikita's API is the single source of
# truth if the status list ever changes.
STATUS_COLOR = {
    "PLANNED": "#94a3b8",     # slate
    "IN_PROGRESS": "#3b82f6", # blue
    "DELAYED": "#f97316",     # orange
    "STALLED": "#ef4444",     # red
    "COMPLETED": "#22c55e",   # green
    "VERIFIED": "#059669",    # dark green
}


@router.get("/infrastructure")
def map_infrastructure(
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    q = db.query(models.Project)
    if district:
        q = q.filter(models.Project.district == district)
    if status:
        q = q.filter(models.Project.current_status == status)

    from sqlalchemy import text
    rows = q.all()
    points = []
    for p in rows:
        r = db.execute(
            text("SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng FROM projects WHERE id = :id"),
            {"id": p.id},
        ).mappings().first()
        status_val = p.current_status.value if hasattr(p.current_status, "value") else p.current_status
        points.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "latitude": r["lat"],
            "longitude": r["lng"],
            "current_status": status_val,
            "color": STATUS_COLOR.get(status_val, "#94a3b8"),
            "progress_deviation": p.progress_deviation,
        })

    return {"total": len(points), "points": points}
