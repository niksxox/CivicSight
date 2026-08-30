from __future__ import annotations

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.adapters import validate_point_rows

REQUIRED_SCHOOL_COLUMNS = ["school_id", "school_name", "state", "district", "latitude", "longitude"]
BOOL_COLUMNS = [
    "has_electricity", "has_drinking_water", "has_toilet", "has_girls_toilet",
    "has_ramp", "has_computer", "has_internet", "has_library", "has_playground",
]


def extract_schools_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def validate_schools(df: pd.DataFrame):
    valid, rejected = validate_point_rows(df, REQUIRED_SCHOOL_COLUMNS)
    duplicates = valid.duplicated(subset=["school_id"], keep="first")
    if duplicates.any():
        duplicate_rows = valid[duplicates].copy()
        duplicate_rows["rejection_reason"] = "duplicate school_id"
        valid = valid[~duplicates].reset_index(drop=True)
        rejected = pd.concat([rejected, duplicate_rows], ignore_index=True)
    return valid, rejected.reset_index(drop=True)


def clean_schools(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["school_id", "school_name", "state", "district", "block", "village", "school_category", "management"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"nan": None, "": None})
    for col in ["latitude", "longitude", "student_count", "teacher_count", "classroom_count"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in BOOL_COLUMNS:
        if col not in df.columns:
            df[col] = True
        df[col] = df[col].astype(str).str.strip().str.lower().map({
            "true": True, "1": True, "yes": True, "y": True,
            "false": False, "0": False, "no": False, "n": False,
        }).fillna(True)
    return df


def transform_schools(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.loc[~df["has_toilet"], "has_girls_toilet"] = False
    df.loc[(~df["has_computer"]) | (~df["has_electricity"]), "has_internet"] = False
    return df


def schools_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    geometry = [Point(lng, lat) for lng, lat in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def load_schools(gdf: gpd.GeoDataFrame, engine: Engine) -> int:
    upsert_sql = text("""
        INSERT INTO schools (
            school_id, school_name, state, district, block, village, location,
            school_category, management, student_count, teacher_count, classroom_count,
            has_electricity, has_drinking_water, has_toilet, has_girls_toilet,
            has_ramp, has_computer, has_internet, has_library, has_playground
        ) VALUES (
            :school_id, :school_name, :state, :district, :block, :village,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :school_category, :management, :student_count, :teacher_count, :classroom_count,
            :has_electricity, :has_drinking_water, :has_toilet, :has_girls_toilet,
            :has_ramp, :has_computer, :has_internet, :has_library, :has_playground
        )
        ON CONFLICT (school_id) DO UPDATE SET
            school_name = EXCLUDED.school_name,
            state = EXCLUDED.state,
            district = EXCLUDED.district,
            block = EXCLUDED.block,
            village = EXCLUDED.village,
            location = EXCLUDED.location,
            school_category = EXCLUDED.school_category,
            management = EXCLUDED.management,
            student_count = EXCLUDED.student_count,
            teacher_count = EXCLUDED.teacher_count,
            classroom_count = EXCLUDED.classroom_count,
            has_electricity = EXCLUDED.has_electricity,
            has_drinking_water = EXCLUDED.has_drinking_water,
            has_toilet = EXCLUDED.has_toilet,
            has_girls_toilet = EXCLUDED.has_girls_toilet,
            has_ramp = EXCLUDED.has_ramp,
            has_computer = EXCLUDED.has_computer,
            has_internet = EXCLUDED.has_internet,
            has_library = EXCLUDED.has_library,
            has_playground = EXCLUDED.has_playground
    """)
    facility_sql = text("""
        INSERT INTO facilities (name, type, location, district, source_ref, geo_precision)
        VALUES (:name, 'school', ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography, :district, :source_ref, 'source_coordinates')
        ON CONFLICT (type, source_ref) WHERE source_ref IS NOT NULL DO UPDATE SET
            name = EXCLUDED.name,
            location = EXCLUDED.location,
            district = EXCLUDED.district,
            geo_precision = EXCLUDED.geo_precision
    """)
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            values = {col: row.get(col) for col in [
                "school_id", "school_name", "state", "district", "block", "village",
                "school_category", "management", *BOOL_COLUMNS
            ]}
            values.update({
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "student_count": int(row["student_count"]),
                "teacher_count": int(row["teacher_count"]),
                "classroom_count": int(row["classroom_count"]),
            })
            conn.execute(upsert_sql, values)
            conn.execute(facility_sql, {
                "name": row["school_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "district": row["district"],
                "source_ref": row["school_id"],
            })
    return len(gdf)
