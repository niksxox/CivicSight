"""
Repeated ETL execution must not create duplicate records. Keyed tables
(projects, schools, district_population, coverage, lgd) upsert; the demo
facilities/network tables rely on deterministic source_ref upserts plus the
opt-in --reset truncate.
"""
from app.config import settings
from etl.pipeline import run_full_pipeline


def test_repeated_full_run_is_idempotent(table_count):
    run_full_pipeline(reset=False)
    counts_first = {t: table_count(t) for t in (
        "projects", "facilities", "district_population",
        "infrastructure_network", "infrastructure_coverage", "schools", "lgd_villages",
    )}
    run_full_pipeline(reset=False)
    counts_second = {t: table_count(t) for t in (
        "projects", "facilities", "district_population",
        "infrastructure_network", "infrastructure_coverage", "schools", "lgd_villages",
    )}
    assert counts_first == counts_second


def test_reset_gives_clean_counts(table_count):
    run_full_pipeline(reset=True)
    assert table_count("projects") == 60
    assert table_count("schools") == 1000
    assert table_count("facilities") == 1040  # 40 demo + 1000 school mirror
    assert table_count("district_population") == 5
    assert table_count("infrastructure_network") == 15
    assert table_count("infrastructure_coverage") == 66
