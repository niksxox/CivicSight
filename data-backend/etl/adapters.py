from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import LineString, Point


INDIA_LAT_RANGE = (6.0, 37.5)
INDIA_LNG_RANGE = (68.0, 97.5)


def canonical_column(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return re.sub(r"_+", "_", text).strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [canonical_column(c) for c in df.columns]
    return df


def resolve_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    columns = {canonical_column(c): c for c in df.columns}
    for candidate in candidates:
        key = canonical_column(candidate)
        if key in columns:
            return columns[key]
    return None


def read_table(path: str | Path, chunksize: int | None = None):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Dataset file is empty: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, chunksize=chunksize)
    if suffix in {".xlsx", ".xls"}:
        if chunksize:
            raise ValueError("Excel chunked reads are not supported; export LGD-scale files as CSV.")
        return pd.read_excel(path, dtype=str)
    if suffix == ".xml":
        if chunksize:
            raise ValueError("XML chunked reads are not supported by this adapter.")
        return read_simple_xml(path)
    raise ValueError(f"Unsupported dataset format for {path.name}")


def read_simple_xml(path: str | Path) -> pd.DataFrame:
    root = ET.parse(path).getroot()
    rows = []
    for row in root:
        rows.append({child.tag: child.text for child in row})
    return pd.DataFrame(rows)


def to_number(value):
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if text.upper() in {"", "NA", "N/A", "NULL", "NONE", "-"}:
        return None
    match = re.search(r"-?\d+(\.\d+)?", text)
    return float(match.group(0)) if match else None


def valid_lat_lng(lat, lng) -> bool:
    lat = to_number(lat)
    lng = to_number(lng)
    return (
        lat is not None
        and lng is not None
        and INDIA_LAT_RANGE[0] <= lat <= INDIA_LAT_RANGE[1]
        and INDIA_LNG_RANGE[0] <= lng <= INDIA_LNG_RANGE[1]
    )


def validate_point_rows(df: pd.DataFrame, required: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df = df.copy()
    reasons = [[] for _ in range(len(df))]
    for col in required:
        for i, val in enumerate(df[col]):
            if pd.isna(val) or str(val).strip() == "":
                reasons[i].append(f"missing {col}")

    for i, row in df.iterrows():
        if "latitude" in df.columns and "longitude" in df.columns:
            if not valid_lat_lng(row["latitude"], row["longitude"]):
                reasons[i].append("invalid latitude/longitude")

    df["_rejection_reasons"] = reasons
    valid_mask = df["_rejection_reasons"].apply(len).eq(0)
    valid = df[valid_mask].drop(columns=["_rejection_reasons"]).reset_index(drop=True)
    rejected = df[~valid_mask].copy()
    rejected["rejection_reason"] = rejected["_rejection_reasons"].apply(lambda r: "; ".join(r))
    rejected = rejected.drop(columns=["_rejection_reasons"]).reset_index(drop=True)
    return valid, rejected


def roads_to_network(df: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    df = normalize_columns(df)
    name_col = resolve_column(df, ["road_name", "name", "package_name", "work_name"])
    district_col = resolve_column(df, ["district", "district_name"])
    geom_col = resolve_column(df, ["geom_wkt", "geometry_wkt", "wkt"])
    lat_col = resolve_column(df, ["latitude", "lat", "start_latitude"])
    lng_col = resolve_column(df, ["longitude", "lng", "lon", "start_longitude"])
    end_lat_col = resolve_column(df, ["end_latitude", "to_latitude"])
    end_lng_col = resolve_column(df, ["end_longitude", "to_longitude"])
    length_col = resolve_column(df, ["road_length_completed_in_km", "length_km", "road_length", "sanctioned_length"])
    status_col = resolve_column(df, ["status", "work_status", "completion_status"])

    rows = []
    rejected = []
    for idx, row in df.iterrows():
        geom = None
        precision = None
        reason = None
        if geom_col and isinstance(row.get(geom_col), str) and row.get(geom_col).strip():
            try:
                geom = wkt.loads(row[geom_col])
                precision = "source_geometry"
                if geom.geom_type != "LineString":
                    reason = f"geometry is {geom.geom_type}, expected LineString"
            except Exception as exc:
                reason = f"invalid geometry WKT: {exc}"
        elif all([lat_col, lng_col, end_lat_col, end_lng_col]) and valid_lat_lng(row[lat_col], row[lng_col]) and valid_lat_lng(row[end_lat_col], row[end_lng_col]):
            geom = LineString([(to_number(row[lng_col]), to_number(row[lat_col])), (to_number(row[end_lng_col]), to_number(row[end_lat_col]))])
            precision = "source_coordinates"
        else:
            reason = "no road geometry or start/end coordinates available"

        if reason:
            rejected.append({**row.to_dict(), "rejection_reason": reason})
            continue

        rows.append({
            "source_ref": str(row.get(resolve_column(df, ["road_id", "pmgsy_id", "id", "sl_no"]) or idx)).strip(),
            "name": str(row.get(name_col) if name_col else f"PMGSY road {idx + 1}").strip(),
            "type": "road",
            "district": row.get(district_col) if district_col else None,
            "length_km": to_number(row.get(length_col)) if length_col else None,
            "status": row.get(status_col) if status_col else None,
            "geo_precision": precision,
            "geometry": geom,
        })
    columns = ["source_ref", "name", "type", "district", "length_km", "status", "geo_precision", "geometry"]
    return gpd.GeoDataFrame(rows, columns=columns, geometry="geometry", crs="EPSG:4326"), pd.DataFrame(rejected)


def roads_to_state_coverage(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalize_columns(df)
    state_col = resolve_column(df, ["stateut", "state_ut", "state", "state_name"])
    roads_col = resolve_column(df, ["no_of_roads", "roads"])
    length_col = resolve_column(df, ["road_length_completed_in_km", "length_km"])
    if not state_col:
        raise ValueError("PMGSY aggregate file is missing a state column.")
    rows = []
    rejected = []
    for idx, row in df.iterrows():
        state = str(row.get(state_col, "")).strip()
        if not state:
            rejected.append({**row.to_dict(), "rejection_reason": "missing state"})
            continue
        rows.append({
            "source": "pmgsy",
            "area_level": "state",
            "state": state,
            "district": None,
            "metric_name": "completed_roads",
            "metric_value": to_number(row.get(roads_col)) if roads_col else None,
            "secondary_metric_name": "completed_road_length_km",
            "secondary_metric_value": to_number(row.get(length_col)) if length_col else None,
            "geo_precision": "non_spatial_state_aggregate",
        })
    return pd.DataFrame(rows), pd.DataFrame(rejected)


def water_to_coverage(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalize_columns(df)
    state_col = resolve_column(df, ["state_ut", "stateut", "state", "state_name"])
    total_col = resolve_column(df, ["total_rural_hhs_as_on_date", "total_households"])
    covered_col = resolve_column(df, ["total_rural_hhs_with_tap_water_supply_as_on_26_07_2023_no", "households_with_tap_water"])
    pct_col = resolve_column(df, ["total_rural_hhs_with_tap_water_supply_as_on_26_07_2023_inpercent", "coverage_percent"])
    if not state_col:
        raise ValueError("JJM file is missing a state column.")
    rows = []
    rejected = []
    for _, row in df.iterrows():
        state = str(row.get(state_col, "")).strip()
        if not state:
            rejected.append({**row.to_dict(), "rejection_reason": "missing state"})
            continue
        rows.append({
            "source": "jal_jeevan_mission",
            "area_level": "state",
            "state": state,
            "district": None,
            "metric_name": "tap_water_coverage_percent",
            "metric_value": to_number(row.get(pct_col)) if pct_col else None,
            "secondary_metric_name": "rural_households_lakh_with_tap_water",
            "secondary_metric_value": to_number(row.get(covered_col)) if covered_col else None,
            "total_households_lakh": to_number(row.get(total_col)) if total_col else None,
            "geo_precision": "non_spatial_state_aggregate",
        })
    return pd.DataFrame(rows), pd.DataFrame(rejected)


def normalize_lgd_chunk(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalize_columns(df)
    village_col = resolve_column(df, ["village_name", "village", "local_body_name"])
    village_code_col = resolve_column(df, ["village_code", "lgd_village_code", "local_body_code"])
    state_col = resolve_column(df, ["state_name", "state"])
    district_col = resolve_column(df, ["district_name", "district"])
    block_col = resolve_column(df, ["block_name", "block"])
    required = [c for c in [village_col, village_code_col, state_col, district_col] if c]
    if len(required) < 4:
        raise ValueError("LGD village file needs village code, village name, state, and district columns.")
    rows = []
    rejected = []
    seen = set()
    for _, row in df.iterrows():
        raw_code = row.get(village_code_col)
        raw_name = row.get(village_col)
        code = "" if raw_code is None or (isinstance(raw_code, float) and pd.isna(raw_code)) else str(raw_code).strip()
        name = "" if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)) else str(raw_name).strip()
        if not code or not name:
            rejected.append({**row.to_dict(), "rejection_reason": "missing village code/name"})
            continue
        if code in seen:
            rejected.append({**row.to_dict(), "rejection_reason": "duplicate village code in chunk"})
            continue
        seen.add(code)
        rows.append({
            "village_code": code,
            "village_name": name,
            "state": str(row.get(state_col, "")).strip() or None,
            "district": str(row.get(district_col, "")).strip() or None,
            "block": str(row.get(block_col, "")).strip() if block_col else None,
        })
    return pd.DataFrame(rows), pd.DataFrame(rejected)
