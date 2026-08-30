"""
Shared pytest fixtures.

The data-backend tests exercise REAL PostGIS behaviour (spatial queries,
upserts, truncation), so they need a live database. A session-scoped
autouse fixture seeds schema + ETL data once. If no database is reachable
the DB-backed tests are skipped rather than failing — the DB-free unit
tests (validation, quality, transform) still run.
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _db_available() -> bool:
    try:
        eng = create_engine(settings.database_url)
        with eng.connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.database_url)


@pytest.fixture(scope="session", autouse=True)
def seed_database():
    """Initialize schema and load all ETL datasets once per test session."""
    if not _db_available():
        pytest.skip("No PostgreSQL/PostGIS database reachable; skipping DB-backed tests.")
    from scripts.init_db import main as init_db_main
    from etl.pipeline import run_full_pipeline

    init_db_main()
    run_full_pipeline(reset=True)
    yield


@pytest.fixture()
def db_conn(engine):
    with engine.connect() as conn:
        yield conn


@pytest.fixture()
def table_count(engine):
    def _count(table: str) -> int:
        with engine.connect() as conn:
            return conn.execute(text(f"select count(*) from {table}")).scalar()

    return _count
