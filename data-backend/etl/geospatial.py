"""
GEOSPATIAL PROCESSING stage.

Converts plain lat/lng columns into real geometry objects using
GeoPandas/Shapely, so the load stage can write proper PostGIS
geography columns instead of two separate float columns.
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
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
    geometry = [Point(lng, lat) for lng, lat in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def district_population_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """boundary_wkt column -> real polygon geometry."""
    df = df.copy()
    df["geometry"] = df["boundary_wkt"].apply(lambda w: wkt.loads(w) if isinstance(w, str) and w.strip() else None)
    df = df.dropna(subset=["geometry"])
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    gdf["population"] = pd.to_numeric(gdf["population"], errors="coerce")
    gdf["area_sq_km"] = pd.to_numeric(gdf["area_sq_km"], errors="coerce")
    return gdf


def network_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """geom_wkt column (LINESTRING) -> real line geometry."""
    df = df.copy()
    df["geometry"] = df["geom_wkt"].apply(lambda w: wkt.loads(w) if isinstance(w, str) and w.strip() else None)
    df = df.dropna(subset=["geometry"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
