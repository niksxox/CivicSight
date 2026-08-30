"""
National-scale LGD village loader: exercises the chunked CSV path safely
with a small synthetic file (no real 650k+ file is required to validate the
logic). Verifies chunked reading, duplicate detection, validation, and
idempotent upsert by village_code.
"""
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.config import settings
from etl.pipeline import run_lgd_villages_pipeline

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
TEMP_FILE = RAW_DIR / "lgd_villages.csv"


@pytest.fixture()
def lgd_temp_file():
    rows = [
        "village_code,village_name,state_name,district_name,block_name",
        "1001,Village A,Andhra Pradesh,Guntur,Vijayawada Rural",
        "1002,Village B,Andhra Pradesh,Guntur,Vijayawada Rural",
        "1001,Village A dup,Andhra Pradesh,Guntur,Vijayawada Rural",  # duplicate code
        ",Village NoCode,Andhra Pradesh,Guntur,Vijayawada Rural",       # missing code
        "1003,Village C,Andhra Pradesh,Kurnool,Kurnool Rural",
    ]
    TEMP_FILE.write_text("\n".join(rows))
    yield TEMP_FILE
    if TEMP_FILE.exists():
        TEMP_FILE.unlink()
    with create_engine(settings.database_url).begin() as conn:
        conn.execute(text("TRUNCATE TABLE lgd_villages"))


def test_lgd_chunked_load_validates_and_dedups(lgd_temp_file):
    engine = create_engine(settings.database_url)
    report = run_lgd_villages_pipeline(str(lgd_temp_file), engine, chunk_size=2)
    # 1 missing code rejected (NaN -> treated as missing). The duplicate
    # code 1001 spans chunks, so it is not rejected inline; it is collapsed
    # at load time by the village_code upsert instead.
    assert report.rejected_rows == 1
    assert report.valid_rows == 4
    assert report.loaded_rows == 4
    with engine.connect() as conn:
        count = conn.execute(text("select count(*) from lgd_villages")).scalar()
        assert count == 3
        # upsert keyed on village_code -> no duplicate for 1001
        dup = conn.execute(
            text("select count(*) from lgd_villages where village_code='1001'")
        ).scalar()
        assert dup == 1


def test_lgd_chunked_rerun_is_idempotent(lgd_temp_file):
    engine = create_engine(settings.database_url)
    run_lgd_villages_pipeline(str(lgd_temp_file), engine, chunk_size=2)
    run_lgd_villages_pipeline(str(lgd_temp_file), engine, chunk_size=2)
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from lgd_villages")).scalar() == 3
