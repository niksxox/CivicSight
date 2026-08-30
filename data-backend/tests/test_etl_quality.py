import pandas as pd

from etl.quality import audit_points, audit_geometries


def test_audit_points_flags_out_of_bounds_and_missing():
    df = pd.DataFrame([
        {"latitude": "16.5", "longitude": "80.6"},   # ok
        {"latitude": "", "longitude": "80.6"},        # missing
        {"latitude": "99.0", "longitude": "80.6"},     # out of India bbox
        {"latitude": "16.5", "longitude": "80.6"},     # duplicate coord
    ])
    rep = audit_points(df)
    assert rep["total"] == 4
    assert rep["missing"] == 1
    assert rep["out_of_india_bbox"] == 1
    assert rep["duplicate_coords"] == 1


def test_audit_points_empty_frame():
    assert audit_points(pd.DataFrame())["total"] == 0


def test_audit_geometries_flags_invalid_and_null():
    from shapely.geometry import Point, Polygon
    import geopandas as gpd

    # A self-intersecting "bowtie" polygon is invalid.
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame(
        {"name": ["a", "b", "c"]},
        geometry=[Point(80, 16), bowtie, None],
        crs="EPSG:4326",
    )
    rep = audit_geometries(gdf)
    assert rep["total"] == 3
    assert rep["invalid_geometry"] == 1
    assert rep["null_geometry"] == 1
