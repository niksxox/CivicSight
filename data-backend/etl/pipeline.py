"""
Pipeline orchestrator — wires every stage together in the exact order
from the spec:

    Government/Open Data -> Extract -> Validate -> Clean -> Transform
        -> Geospatial Processing -> Load -> Unified Database

Run directly: python -m etl.pipeline
Or via the convenience wrapper: python scripts/run_etl.py
"""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from app.config import settings
from etl import extract, validate, clean, transform, geospatial, load, school_etl
from etl.adapters import (
    normalize_lgd_chunk,
    read_table,
    roads_to_network,
    roads_to_state_coverage,
    water_to_coverage,
)
from etl.reporting import EtlReport, write_rejections
from etl.quality import audit_points, audit_geometries, has_geometry_issues

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("civsight.etl")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def _log_report(report: EtlReport) -> EtlReport:
    report.finish()
    for line in report.as_lines():
        logger.info(line)
    return report


def _skip_report(dataset: str, path: Path, reason: str) -> EtlReport:
    report = EtlReport(dataset=dataset, source_file=str(path), warnings=[reason])
    return _log_report(report)


def _log_geometry_quality(gdf, dataset: str) -> None:
    report = audit_geometries(gdf)
    if has_geometry_issues(report):
        logger.warning("GEOMETRY QUALITY [%s]: %s", dataset, report)
    else:
        logger.info("GEOMETRY QUALITY [%s]: %s", dataset, report)


def _log_point_quality(df, dataset: str) -> None:
    report = audit_points(df)
    if report["missing"] or report["out_of_india_bbox"] or report["duplicate_coords"]:
        logger.warning("POINT QUALITY [%s]: %s", dataset, report)
    else:
        logger.info("POINT QUALITY [%s]: %s", dataset, report)


def run_projects_pipeline(csv_path: str, engine) -> EtlReport:
    report = EtlReport("projects", csv_path)
    logger.info("EXTRACT: reading %s", csv_path)
    raw = extract.extract_projects_csv(csv_path)
    report.input_rows = len(raw)
    _log_point_quality(raw, "projects")

    logger.info("VALIDATE")
    valid, rejected = validate.validate_projects(raw)
    report.valid_rows = len(valid)
    report.rejected_rows = len(rejected)
    report.rejected_path = write_rejections(rejected, PROCESSED_DIR, "projects")

    logger.info("CLEAN")
    cleaned = clean.clean_projects(valid)

    logger.info("TRANSFORM")
    transformed = transform.transform_projects(cleaned)

    logger.info("GEOSPATIAL PROCESSING")
    geo = geospatial.projects_to_geodataframe(transformed)

    logger.info("LOAD")
    report.loaded_rows = load.load_projects(geo, engine)
    return _log_report(report)


def run_facilities_pipeline(csv_path: str, engine) -> EtlReport:
    report = EtlReport("facilities", csv_path)
    logger.info("Facilities: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_facilities_csv(csv_path)
    report.input_rows = len(raw)
    _log_point_quality(raw, "facilities")
    geo = geospatial.facilities_to_geodataframe(raw)
    report.valid_rows = len(geo)
    report.rejected_rows = len(raw) - len(geo)
    report.loaded_rows = load.load_facilities(geo, engine)
    return _log_report(report)


def run_population_pipeline(csv_path: str, engine) -> EtlReport:
    report = EtlReport("district_population", csv_path)
    logger.info("District population: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_district_population_csv(csv_path)
    report.input_rows = len(raw)
    geo = geospatial.district_population_to_geodataframe(raw)
    _log_geometry_quality(geo, "district_population")
    report.valid_rows = len(geo)
    report.rejected_rows = len(raw) - len(geo)
    if report.rejected_rows:
        rejected = raw.loc[~raw.index.isin(geo.index)].copy()
        rejected["rejection_reason"] = "missing or invalid boundary_wkt"
        report.rejected_path = write_rejections(rejected, PROCESSED_DIR, "district_population")
    report.loaded_rows = load.load_district_population(geo, engine)
    return _log_report(report)


def run_network_pipeline(csv_path: str, engine) -> EtlReport:
    report = EtlReport("network", csv_path)
    logger.info("Infrastructure network: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_network_csv(csv_path)
    report.input_rows = len(raw)
    geo = geospatial.network_to_geodataframe(raw)
    _log_geometry_quality(geo, "network")
    report.valid_rows = len(geo)
    report.rejected_rows = len(raw) - len(geo)
    report.loaded_rows = load.load_network(geo, engine)
    return _log_report(report)


def run_schools_pipeline(csv_path: str, engine) -> EtlReport:
    report = EtlReport("schools", csv_path)
    raw = school_etl.extract_schools_csv(csv_path)
    report.input_rows = len(raw)
    _log_point_quality(raw, "schools")
    valid, rejected = school_etl.validate_schools(raw)
    report.valid_rows = len(valid)
    report.rejected_rows = len(rejected)
    report.rejected_path = write_rejections(rejected, PROCESSED_DIR, "schools")
    geo = school_etl.schools_to_geodataframe(school_etl.transform_schools(school_etl.clean_schools(valid)))
    report.loaded_rows = school_etl.load_schools(geo, engine)
    return _log_report(report)


def run_roads_pipeline(path: str, engine) -> EtlReport:
    report = EtlReport("roads", path)
    raw = read_table(path)
    report.input_rows = len(raw)
    network_gdf, rejected = roads_to_network(raw)
    if not network_gdf.empty:
        report.valid_rows = len(network_gdf)
        report.rejected_rows = len(rejected)
        report.rejected_path = write_rejections(rejected, PROCESSED_DIR, "roads")
        report.loaded_rows = load.load_network(network_gdf, engine)
    else:
        coverage, coverage_rejected = roads_to_state_coverage(raw)
        report.valid_rows = len(coverage)
        report.rejected_rows = len(coverage_rejected)
        report.rejected_path = write_rejections(coverage_rejected, PROCESSED_DIR, "roads")
        report.loaded_rows = load.load_infrastructure_coverage(coverage, engine)
        report.warnings.append("PMGSY source is non-spatial aggregate data; loaded as infrastructure_coverage, not road geometry.")
    return _log_report(report)


def run_water_pipeline(path: str, engine) -> EtlReport:
    report = EtlReport("water", path)
    raw = read_table(path)
    report.input_rows = len(raw)
    coverage, rejected = water_to_coverage(raw)
    report.valid_rows = len(coverage)
    report.rejected_rows = len(rejected)
    report.rejected_path = write_rejections(rejected, PROCESSED_DIR, "water")
    report.loaded_rows = load.load_infrastructure_coverage(coverage, engine)
    report.warnings.append("JJM source is non-spatial aggregate data; no coordinates were invented.")
    return _log_report(report)


def run_lgd_villages_pipeline(path: str, engine, chunk_size: int = 50000) -> EtlReport:
    report = EtlReport("villages", path)
    reader = read_table(path, chunksize=chunk_size)
    rejected_parts = []
    if isinstance(reader, pd.DataFrame):
        reader = [reader]
    for chunk_no, chunk in enumerate(reader, start=1):
        logger.info("LGD villages: processing chunk %d (%d rows)", chunk_no, len(chunk))
        report.input_rows += len(chunk)
        valid, rejected = normalize_lgd_chunk(chunk)
        report.valid_rows += len(valid)
        report.rejected_rows += len(rejected)
        if not rejected.empty:
            rejected_parts.append(rejected)
        report.loaded_rows += load.load_lgd_villages(valid, engine)
    if rejected_parts:
        report.rejected_path = write_rejections(pd.concat(rejected_parts, ignore_index=True), PROCESSED_DIR, "villages")
    return _log_report(report)


def _candidate(name: str, filenames: list[str]) -> Path | None:
    for filename in filenames:
        path = RAW_DIR / filename
        if path.exists() and path.stat().st_size > 0:
            return path
    logger.warning("%s skipped: none of these files exists with content: %s", name, ", ".join(filenames))
    return None


def reset_datasets(selected: set[str], engine) -> None:
    """
    Demo-refresh helper: truncate the target tables for the chosen datasets
    so a re-run starts from a clean slate instead of stacking on top of
    stale rows. Keyed tables (coverage, lgd) are upsert-idempotent and are
    intentionally NOT truncated here.

    This is opt-in via ``--reset``; the default run is incremental/upsert so
    it never destroys data a teammate loaded by hand.
    """
    targets: set[str] = set()
    if "facilities" in selected:
        targets.add("facilities")
    if "population" in selected or "district_population" in selected:
        targets.add("district_population")
    if "network" in selected:
        targets.add("infrastructure_network")
    if "projects" in selected:
        targets.update({"projects", "project_history"})
    if "schools" in selected:
        targets.add("schools")
    if "villages" in selected or "lgd" in selected:
        targets.add("lgd_villages")

    if not targets:
        return

    with engine.begin() as conn:
        for table in targets:
            if table == "facilities":
                # keep the school mirror; the schools pipeline owns that
                conn.execute(text("DELETE FROM facilities WHERE type <> 'school'"))
            else:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        if "schools" in selected:
            conn.execute(text("DELETE FROM facilities WHERE type = 'school'"))
    logger.info("Reset cleared tables: %s", ", ".join(sorted(targets)) or "none")


def run_full_pipeline(datasets: list[str] | None = None, chunk_size: int = 50000, reset: bool = False):
    engine = create_engine(settings.database_url)
    selected = set(datasets or ["facilities", "population", "network", "projects", "schools", "roads", "water", "villages"])
    if reset:
        reset_datasets(selected, engine)
    reports = []

    if "facilities" in selected:
        reports.append(run_facilities_pipeline(str(RAW_DIR / "facilities.csv"), engine))
    if "population" in selected or "district_population" in selected:
        reports.append(run_population_pipeline(str(RAW_DIR / "district_population.csv"), engine))
    if "network" in selected:
        reports.append(run_network_pipeline(str(RAW_DIR / "network.csv"), engine))
    if "projects" in selected:
        reports.append(run_projects_pipeline(str(RAW_DIR / "projects.csv"), engine))
    if "schools" in selected:
        school_path = _candidate("schools", ["schools.csv"])
        reports.append(run_schools_pipeline(str(school_path), engine) if school_path else _skip_report("schools", RAW_DIR / "schools.csv", "Synthetic school CSV not present; run scripts/generate_synthetic_schools.py."))
    if "roads" in selected:
        road_path = _candidate("roads", ["pmgsy_roads.csv", "pmgsy_roads.xml", "road.xml", "road (1).xml"])
        reports.append(run_roads_pipeline(str(road_path), engine) if road_path else _skip_report("roads", RAW_DIR / "pmgsy_roads.csv", "PMGSY file not available in data/raw."))
    if "water" in selected or "jjm" in selected:
        water_path = _candidate("water", ["jjm_water.csv", "water_connections.csv", "water_connections.xml", "water_connections (1).xml"])
        reports.append(run_water_pipeline(str(water_path), engine) if water_path else _skip_report("water", RAW_DIR / "jjm_water.csv", "JJM file not available in data/raw."))
    if "villages" in selected or "lgd" in selected:
        village_path = _candidate("villages", ["lgd_villages.csv", "villages.csv"])
        reports.append(run_lgd_villages_pipeline(str(village_path), engine, chunk_size) if village_path else _skip_report("villages", RAW_DIR / "lgd_villages.csv", "LGD village file not available in data/raw."))

    logger.info("Pipeline complete.")
    return reports


if __name__ == "__main__":
    run_full_pipeline()
