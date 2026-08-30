"""
Geospatial data-quality audit.

Pure, DB-free helpers that summarize the geographic soundness of a frame
before it is loaded into PostGIS:

  * point rows: lat/lng within India's bounding box, non-null, no dupes
  * geometries: valid (ST_IsValid / shapely), non-null, correct SRID

These power the "explainable rejections" requirement: instead of silently
loading a self-intersecting polygon or an out-of-country coordinate, the
pipeline logs exactly how many rows were suspicious and why.
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry

INDIA_LAT_RANGE = (6.0, 37.5)
INDIA_LNG_RANGE = (68.0, 97.5)

EXPECTED_SRID = 4326


def _as_float(value):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def audit_points(df: pd.DataFrame, lat_col: str = "latitude", lng_col: str = "longitude") -> dict:
    """Count point-coordinate problems. Does not mutate the frame."""
    report = {
        "total": len(df),
        "missing": 0,
        "out_of_india_bbox": 0,
        "duplicate_coords": 0,
    }
    if df.empty:
        return report

    seen = set()
    for _, row in df.iterrows():
        lat = _as_float(row.get(lat_col))
        lng = _as_float(row.get(lng_col))
        if lat is None or lng is None:
            report["missing"] += 1
            continue
        if not (INDIA_LAT_RANGE[0] <= lat <= INDIA_LAT_RANGE[1] and INDIA_LNG_RANGE[0] <= lng <= INDIA_LNG_RANGE[1]):
            report["out_of_india_bbox"] += 1
        key = (round(lat, 6), round(lng, 6))
        if key in seen:
            report["duplicate_coords"] += 1
        else:
            seen.add(key)
    return report


def audit_geometries(gdf: gpd.GeoDataFrame) -> dict:
    """Count geometry problems: nulls, invalid shapes, wrong SRID, dupes."""
    report = {
        "total": len(gdf),
        "null_geometry": 0,
        "invalid_geometry": 0,
        "wrong_srid": 0,
        "duplicate_geometry": 0,
    }
    if gdf.empty:
        return report

    seen_wkt = set()
    for geom in gdf.geometry:
        if geom is None or (isinstance(geom, float) and pd.isna(geom)):
            report["null_geometry"] += 1
            continue
        if not isinstance(geom, BaseGeometry) or geom.is_empty:
            report["null_geometry"] += 1
            continue
        if not geom.is_valid:
            report["invalid_geometry"] += 1
        if getattr(geom, "srid", None) not in (None, EXPECTED_SRID):
            report["wrong_srid"] += 1
        wkt = geom.wkt
        if wkt in seen_wkt:
            report["duplicate_geometry"] += 1
        else:
            seen_wkt.add(wkt)
    return report


def has_geometry_issues(report: dict) -> bool:
    return any(report[k] for k in ("null_geometry", "invalid_geometry", "wrong_srid"))
