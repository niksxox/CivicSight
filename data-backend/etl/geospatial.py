"""
GEOSPATIAL PROCESSING stage.

Converts plain lat/lng columns into real geometry objects using
GeoPandas/Shapely, so the load stage can write proper PostGIS
geography columns instead of two separate float columns.
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import MultiPolygon, Polygon
from shapely import wkt


def projects_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Attach a Point(longitude, latitude) geometry, WGS84 (EPSG:4326)."""
    geometry = [Point(lng, lat) for lng, lat in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def facilities_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    df = df.copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    geometry = [Point(lng, lat) for lng, lat in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def district_population_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """boundary_wkt column -> real polygon geometry."""
    df = df.copy()
    def parse_boundary(value):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            geom = wkt.loads(value)
        except Exception:
            return None
        if isinstance(geom, Polygon):
            geom = MultiPolygon([geom])
        if not isinstance(geom, MultiPolygon) or not geom.is_valid:
            return None
        return geom
    df["geometry"] = df["boundary_wkt"].apply(parse_boundary)
    df = df.dropna(subset=["geometry"])
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    gdf["population"] = pd.to_numeric(gdf["population"], errors="coerce")
    gdf["area_sq_km"] = pd.to_numeric(gdf["area_sq_km"], errors="coerce")
    return gdf


def network_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """geom_wkt column (LINESTRING) -> real line geometry."""
    df = df.copy()
    def parse_line(value):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            geom = wkt.loads(value)
        except Exception:
            return None
        if geom.geom_type != "LineString" or not geom.is_valid:
            return None
        return geom
    df["geometry"] = df["geom_wkt"].apply(parse_line)
    df = df.dropna(subset=["geometry"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
