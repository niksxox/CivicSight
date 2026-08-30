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
        INSERT INTO facilities (name, type, location, district, source_ref, geo_precision)
        VALUES (
            :name, :type, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :district, :source_ref, 'source_coordinates'
        )
        ON CONFLICT (type, source_ref) WHERE source_ref IS NOT NULL DO UPDATE SET
            name = EXCLUDED.name,
            location = EXCLUDED.location,
            district = EXCLUDED.district,
            geo_precision = EXCLUDED.geo_precision
    """)
    with engine.begin() as conn:
        for idx, row in gdf.iterrows():
            conn.execute(sql, {
                "name": row["name"],
                "type": row["type"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "district": row.get("district"),
                "source_ref": row.get("source_ref") or f"{row['type']}:{row['name']}:{idx}",
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
        INSERT INTO infrastructure_network (
            source_ref, name, type, geom, district, length_km, status, geo_precision
        )
        VALUES (
            :source_ref, :name, :type, ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography,
            :district, :length_km, :status, :geo_precision
        )
        ON CONFLICT (type, source_ref) WHERE source_ref IS NOT NULL DO UPDATE SET
            name = EXCLUDED.name,
            geom = EXCLUDED.geom,
            district = EXCLUDED.district,
            length_km = EXCLUDED.length_km,
            status = EXCLUDED.status,
            geo_precision = EXCLUDED.geo_precision
    """)
    with engine.begin() as conn:
        for idx, row in gdf.iterrows():
            conn.execute(sql, {
                "source_ref": row.get("source_ref") or f"{row.get('type', 'network')}:{row.get('name', idx)}",
                "name": row.get("name"),
                "type": row.get("type"),
                "wkt": row.geometry.wkt,
                "district": row.get("district"),
                "length_km": row.get("length_km"),
                "status": row.get("status"),
                "geo_precision": row.get("geo_precision") or "source_geometry",
            })
    return len(gdf)


def load_infrastructure_coverage(df, engine: Engine) -> int:
    sql = text("""
        INSERT INTO infrastructure_coverage (
            source, area_level, state, district, district_key, metric_name, metric_value,
            secondary_metric_name, secondary_metric_value, total_households_lakh, geo_precision
        )
        VALUES (
            :source, :area_level, :state, :district, :district_key, :metric_name, :metric_value,
            :secondary_metric_name, :secondary_metric_value, :total_households_lakh, :geo_precision
        )
        ON CONFLICT (source, area_level, state, district_key, metric_name) DO UPDATE SET
            metric_value = EXCLUDED.metric_value,
            secondary_metric_name = EXCLUDED.secondary_metric_name,
            secondary_metric_value = EXCLUDED.secondary_metric_value,
            total_households_lakh = EXCLUDED.total_households_lakh,
            geo_precision = EXCLUDED.geo_precision,
            updated_at = now()
    """)
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(sql, {
                "source": row["source"],
                "area_level": row["area_level"],
                "state": row["state"],
                "district": row.get("district"),
                "district_key": row.get("district") or "",
                "metric_name": row["metric_name"],
                "metric_value": row.get("metric_value"),
                "secondary_metric_name": row.get("secondary_metric_name"),
                "secondary_metric_value": row.get("secondary_metric_value"),
                "total_households_lakh": row.get("total_households_lakh"),
                "geo_precision": row["geo_precision"],
            })
    return len(df)


def load_lgd_villages(df, engine: Engine) -> int:
    sql = text("""
        INSERT INTO lgd_villages (village_code, village_name, state, district, block)
        VALUES (:village_code, :village_name, :state, :district, :block)
        ON CONFLICT (village_code) DO UPDATE SET
            village_name = EXCLUDED.village_name,
            state = EXCLUDED.state,
            district = EXCLUDED.district,
            block = EXCLUDED.block,
            updated_at = now()
    """)
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(sql, {
                "village_code": row["village_code"],
                "village_name": row["village_name"],
                "state": row.get("state"),
                "district": row.get("district"),
                "block": row.get("block"),
            })
    return len(df)
