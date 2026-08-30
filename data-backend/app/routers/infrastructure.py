"""
GET /infrastructure — the raw "what physical infrastructure exists"
feed: road/rail network + critical facilities. Separate from
/projects, which is about tracked *work* (planned/actual progress).
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


@router.get("")
def list_infrastructure(
    db: Session = Depends(get_db),
    district: Optional[str] = Query(None),
    type: Optional[str] = Query(None, description="road | rail | water_line | power_line"),
):
    """
    Returns road/rail/utility network segments as GeoJSON-ish features
    plus a facilities list, filterable by district and network type.
    """
    network_sql = "SELECT id, name, type, district, ST_AsGeoJSON(geom::geometry) AS geojson FROM infrastructure_network WHERE 1=1"
    params = {}
    if district:
        network_sql += " AND district = :district"
        params["district"] = district
    if type:
        network_sql += " AND type = :type"
        params["type"] = type

    network_rows = db.execute(text(network_sql), params).mappings().all()

    facilities_sql = "SELECT id, name, type, district, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng FROM facilities WHERE 1=1"
    fparams = {}
    if district:
        facilities_sql += " AND district = :district"
        fparams["district"] = district

    facility_rows = db.execute(text(facilities_sql), fparams).mappings().all()

    return {
        "network": [dict(r) for r in network_rows],
        "facilities": [dict(r) for r in facility_rows],
    }
