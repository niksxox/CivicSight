"""
EXTRACT stage.

Pulls raw records into pandas DataFrames, as-is, with zero
interpretation. If a source is broken or a column is missing, that's
a job for validate.py, not here — extract should be "dumb" so it's
easy to swap CSV for an API call or a govt open-data portal later
without touching downstream stages.
"""
import pandas as pd


def extract_projects_csv(path: str) -> pd.DataFrame:
    """
    Raw government project records.
    Expected (but NOT enforced here) columns:
    external_ref, name, category, department, district, state,
    latitude, longitude, budget_allocated, budget_spent,
    planned_start, planned_end, reported_progress, status
    """
    return pd.read_csv(path, dtype=str)  # read everything as str; typing happens in clean.py


def extract_facilities_csv(path: str) -> pd.DataFrame:
    """Raw critical-facility records: name, type, latitude, longitude, district."""
    return pd.read_csv(path, dtype=str)


def extract_district_population_csv(path: str) -> pd.DataFrame:
    """
    district, state, population, area_sq_km, boundary_wkt
    boundary_wkt: a WKT MULTIPOLYGON string (from GIS boundary files).
    """
    return pd.read_csv(path, dtype=str)


def extract_network_csv(path: str) -> pd.DataFrame:
    """name, type, district, geom_wkt (WKT LINESTRING)."""
    return pd.read_csv(path, dtype=str)
