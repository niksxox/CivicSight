"""
LOAD stage.

Writes cleaned/transformed/geo-processed data into the unified
PostGIS database. Uses upserts keyed on external_ref so re-running
the pipeline on a refreshed government extract updates existing
projects instead of duplicating them, and logs every progress change
into project_history so nothing is lost.
"""
import geopandas as gpd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def load_projects(gdf: gpd.GeoDataFrame, engine: Engine) -> int:
    """
    Upsert projects keyed on external_ref. Returns number of rows
    written. Every insert/update also appends a project_history row
    so 'planned vs actual' has a timeline, not just a snapshot.
    """
    upsert_sql = text("""
        INSERT INTO projects (
            external_ref, name, description, category, department, district, state,
            location, budget_allocated, budget_spent,
            planned_start, planned_end, planned_progress, actual_progress,
            current_status, priority_score
        ) VALUES (
            :external_ref, :name, :description, :category, :department, :district, :state,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :budget_allocated, :budget_spent,
            :planned_start, :planned_end, :planned_progress, :actual_progress,
            :current_status, :priority_score
        )
        ON CONFLICT (external_ref) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            department = EXCLUDED.department,
            district = EXCLUDED.district,
            state = EXCLUDED.state,
            location = EXCLUDED.location,
            budget_allocated = EXCLUDED.budget_allocated,
            budget_spent = EXCLUDED.budget_spent,
            planned_start = EXCLUDED.planned_start,
            planned_end = EXCLUDED.planned_end,
            planned_progress = EXCLUDED.planned_progress,
            actual_progress = EXCLUDED.actual_progress,
            current_status = EXCLUDED.current_status,
            priority_score = EXCLUDED.priority_score
        RETURNING id;
    """)

    history_sql = text("""
        INSERT INTO project_history (project_id, status, progress, note, source)
        VALUES (:project_id, :status, :progress, :note, 'GOVERNMENT')
    """)

    written = 0
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            result = conn.execute(upsert_sql, {
                "external_ref": row.get("external_ref"),
                "name": row["name"],
                "description": row.get("description"),
                "category": row["category"],
                "department": row.get("department"),
                "district": row.get("district"),
                "state": row.get("state"),
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "budget_allocated": row.get("budget_allocated"),
                "budget_spent": row.get("budget_spent"),
                "planned_start": row["planned_start"],
                "planned_end": row["planned_end"],
                "planned_progress": row["planned_progress"],
                "actual_progress": row["actual_progress"],
                "current_status": row["current_status"],
                "priority_score": row["priority_score"],
            })
            project_id = result.scalar()
            conn.execute(history_sql, {
                "project_id": project_id,
                "status": row["current_status"],
                "progress": row["actual_progress"],
                "note": "ETL sync from government source",
            })
            written += 1

    return written


def load_facilities(gdf: gpd.GeoDataFrame, engine: Engine) -> int:
    sql = text("""
        INSERT INTO facilities (name, type, location, district)
        VALUES (:name, :type, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography, :district)
    """)
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            conn.execute(sql, {
                "name": row["name"],
                "type": row["type"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "district": row.get("district"),
            })
    return len(gdf)


def load_district_population(gdf: gpd.GeoDataFrame, engine: Engine) -> int:
    sql = text("""
        INSERT INTO district_population (district, state, population, boundary, area_sq_km)
        VALUES (:district, :state, :population, ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography, :area_sq_km)
        ON CONFLICT (district) DO UPDATE SET
            population = EXCLUDED.population,
            boundary = EXCLUDED.boundary,
            area_sq_km = EXCLUDED.area_sq_km
    """)
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            conn.execute(sql, {
                "district": row["district"],
                "state": row.get("state"),
                "population": row["population"],
                "wkt": row.geometry.wkt,
                "area_sq_km": row["area_sq_km"],
            })
    return len(gdf)


def load_network(gdf: gpd.GeoDataFrame, engine: Engine) -> int:
    sql = text("""
        INSERT INTO infrastructure_network (name, type, geom, district)
        VALUES (:name, :type, ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography, :district)
    """)
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            conn.execute(sql, {
                "name": row.get("name"),
                "type": row.get("type"),
                "wkt": row.geometry.wkt,
                "district": row.get("district"),
            })
    return len(gdf)
