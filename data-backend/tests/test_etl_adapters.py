import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import school_etl
from etl.adapters import normalize_lgd_chunk, roads_to_network, roads_to_state_coverage, water_to_coverage
from etl.geospatial import district_population_to_geodataframe, network_to_geodataframe


def test_school_validation_rejects_duplicate_and_bad_coordinates():
    df = pd.DataFrame([
        {"school_id": "1", "school_name": "A", "state": "AP", "district": "Guntur", "latitude": "16.1", "longitude": "80.1"},
        {"school_id": "1", "school_name": "B", "state": "AP", "district": "Guntur", "latitude": "16.2", "longitude": "80.2"},
        {"school_id": "2", "school_name": "C", "state": "AP", "district": "Guntur", "latitude": "999", "longitude": "80.2"},
    ])
    valid, rejected = school_etl.validate_schools(df)
    assert len(valid) == 1
    assert len(rejected) == 2
    assert "duplicate school_id" in rejected["rejection_reason"].to_string()
    assert "invalid latitude/longitude" in rejected["rejection_reason"].to_string()


def test_missing_required_school_column_is_explainable():
    with pytest.raises(ValueError, match="missing required columns"):
        school_etl.validate_schools(pd.DataFrame([{"school_id": "1"}]))


def test_road_aggregate_loads_as_non_spatial_coverage():
    df = pd.DataFrame([{
        "STATEUT": "Andhra Pradesh",
        "NO._OF_ROADS": "4813",
        "ROAD_LENGTH_COMPLETED_IN_KM": "16561.53",
    }])
    coverage, rejected = roads_to_state_coverage(df)
    assert rejected.empty
    assert coverage.iloc[0]["source"] == "pmgsy"
    assert coverage.iloc[0]["geo_precision"] == "non_spatial_state_aggregate"


def test_road_network_rejects_rows_without_geometry():
    gdf, rejected = roads_to_network(pd.DataFrame([{"STATEUT": "Andhra Pradesh", "NO._OF_ROADS": "4813"}]))
    assert gdf.empty
    assert rejected.iloc[0]["rejection_reason"] == "no road geometry or start/end coordinates available"


def test_water_coverage_handles_jjm_state_aggregate_columns():
    df = pd.DataFrame([{
        "STATE_UT": "Andhra Pradesh",
        "TOTAL_RURAL_HHS_AS_ON_DATE": "95.55",
        "TOTAL_RURAL_HHS_WITH_TAP_WATER_SUPPLY_AS_ON_26-07-2023_-_NO.": "66.95",
        "TOTAL_RURAL_HHS_WITH_TAP_WATER_SUPPLY_AS_ON_26-07-2023_-_INpercent": "70.08",
    }])
    coverage, rejected = water_to_coverage(df)
    assert rejected.empty
    assert coverage.iloc[0]["metric_value"] == 70.08
    assert coverage.iloc[0]["total_households_lakh"] == 95.55


def test_lgd_chunk_validation_rejects_duplicates():
    df = pd.DataFrame([
        {"Village Code": "100", "Village Name": "A", "State Name": "AP", "District Name": "Guntur"},
        {"Village Code": "100", "Village Name": "A again", "State Name": "AP", "District Name": "Guntur"},
    ])
    valid, rejected = normalize_lgd_chunk(df)
    assert len(valid) == 1
    assert len(rejected) == 1
    assert rejected.iloc[0]["rejection_reason"] == "duplicate village code in chunk"


def test_geospatial_converts_polygon_boundary_to_multipolygon():
    gdf = district_population_to_geodataframe(pd.DataFrame([{
        "district": "Guntur",
        "state": "AP",
        "population": "1000",
        "area_sq_km": "10",
        "boundary_wkt": "POLYGON((80 16, 81 16, 81 17, 80 17, 80 16))",
    }]))
    assert len(gdf) == 1
    assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"


def test_network_invalid_geometry_is_rejected():
    gdf = network_to_geodataframe(pd.DataFrame([{"name": "x", "type": "road", "district": "Guntur", "geom_wkt": "POINT(80 16)"}]))
    assert gdf.empty
