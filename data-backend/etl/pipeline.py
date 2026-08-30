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

from sqlalchemy import create_engine

from app.config import settings
from etl import extract, validate, clean, transform, geospatial, load

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("civsight.etl")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def run_projects_pipeline(csv_path: str, engine) -> None:
    logger.info("EXTRACT: reading %s", csv_path)
    raw = extract.extract_projects_csv(csv_path)
    logger.info("Extracted %d raw rows", len(raw))

    logger.info("VALIDATE")
    valid, rejected = validate.validate_projects(raw)
    logger.info("Valid: %d | Rejected: %d", len(valid), len(rejected))
    if len(rejected):
        out_path = DATA_DIR / "processed" / "rejected_projects.csv"
        rejected.to_csv(out_path, index=False)
        logger.warning("Rejected rows written to %s — review these", out_path)

    logger.info("CLEAN")
    cleaned = clean.clean_projects(valid)

    logger.info("TRANSFORM")
    transformed = transform.transform_projects(cleaned)

    logger.info("GEOSPATIAL PROCESSING")
    geo = geospatial.projects_to_geodataframe(transformed)

    logger.info("LOAD")
    written = load.load_projects(geo, engine)
    logger.info("Loaded %d projects into the unified database", written)


def run_facilities_pipeline(csv_path: str, engine) -> None:
    logger.info("Facilities: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_facilities_csv(csv_path)
    geo = geospatial.facilities_to_geodataframe(raw)
    written = load.load_facilities(geo, engine)
    logger.info("Loaded %d facilities", written)


def run_population_pipeline(csv_path: str, engine) -> None:
    logger.info("District population: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_district_population_csv(csv_path)
    geo = geospatial.district_population_to_geodataframe(raw)
    written = load.load_district_population(geo, engine)
    logger.info("Loaded %d districts", written)


def run_network_pipeline(csv_path: str, engine) -> None:
    logger.info("Infrastructure network: extract -> geospatial -> load (%s)", csv_path)
    raw = extract.extract_network_csv(csv_path)
    geo = geospatial.network_to_geodataframe(raw)
    written = load.load_network(geo, engine)
    logger.info("Loaded %d network segments", written)


def run_full_pipeline():
    engine = create_engine(settings.database_url)

    run_facilities_pipeline(str(DATA_DIR / "raw" / "facilities.csv"), engine)
    run_population_pipeline(str(DATA_DIR / "raw" / "district_population.csv"), engine)
    run_network_pipeline(str(DATA_DIR / "raw" / "network.csv"), engine)
    run_projects_pipeline(str(DATA_DIR / "raw" / "projects.csv"), engine)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run_full_pipeline()
