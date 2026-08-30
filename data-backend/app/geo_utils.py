"""
Small helpers shared by multiple routers so the raw PostGIS SQL
(ST_DWithin, ST_Distance, ST_X/ST_Y) lives in exactly one place.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def project_lat_lng(session: Session, location_column_expr: str) -> str:
    """Not used directly — kept as documentation of the pattern below."""
    return f"ST_Y({location_column_expr}::geometry), ST_X({location_column_expr}::geometry)"


def nearby_facilities(db: Session, lat: float, lng: float, radius_m: int):
    """
    Facilities within radius_m meters of (lat, lng), nearest first.
    Uses geography type so distances are true meters, not degrees.
    """
    sql = text("""
        SELECT id, name, type,
               ST_Distance(location, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) AS distance_m
        FROM facilities
        WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius)
        ORDER BY distance_m ASC
    """)
    rows = db.execute(sql, {"lat": lat, "lng": lng, "radius": radius_m}).mappings().all()
    return rows


def estimate_nearby_population(db: Session, lat: float, lng: float, radius_m: int) -> int | None:
    """
    Population estimate for a radius around a point.

    We don't have a fine-grained population grid in the MVP, so we
    approximate: find the district whose boundary contains the point,
    then scale that district's population by the ratio of
    (circle area / district area). Good enough for a demo; swap in a
    real gridded population dataset (e.g. WorldPop) post-MVP.
    """
    sql = text("""
        SELECT population, area_sq_km
        FROM district_population
        WHERE ST_Contains(boundary::geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        LIMIT 1
    """)
    row = db.execute(sql, {"lat": lat, "lng": lng}).mappings().first()
    if not row or not row["population"] or not row["area_sq_km"]:
        return None

    import math
    circle_area_km2 = math.pi * (radius_m / 1000) ** 2
    ratio = min(circle_area_km2 / float(row["area_sq_km"]), 1.0)
    return int(row["population"] * ratio)


def nearby_road_segments(db: Session, lat: float, lng: float, radius_m: int):
    """Roads/rail/etc. passing within radius_m of the point — used for connectivity notes."""
    sql = text("""
        SELECT id, name, type
        FROM infrastructure_network
        WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius)
    """)
    return db.execute(sql, {"lat": lat, "lng": lng, "radius": radius_m}).mappings().all()
