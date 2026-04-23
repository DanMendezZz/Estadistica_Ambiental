"""Manejo de proyecciones geográficas para datos ambientales colombianos.

Sistemas de referencia más usados en Colombia:
  MAGNA-SIRGAS geográfico  EPSG:4686
  MAGNA-SIRGAS / CTM12     EPSG:9377  (proyección oficial desde 2020)
  WGS84                    EPSG:4326  (GPS, OpenStreetMap)
  Web Mercator             EPSG:3857  (visualización web)
"""

from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)

EPSG_MAGNA_SIRGAS   = 4686
EPSG_CTM12          = 9377
EPSG_WGS84          = 4326
EPSG_WEB_MERCATOR   = 3857


def reproject(gdf, from_epsg: int, to_epsg: int):
    """Reprojecta un GeoDataFrame entre sistemas de referencia."""
    try:
        import geopandas  # noqa: F401
    except ImportError:
        raise ImportError("pip install geopandas")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=from_epsg)
    return gdf.to_crs(epsg=to_epsg)


def points_to_geodataframe(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    epsg: int = EPSG_WGS84,
):
    """Convierte un DataFrame con lat/lon a GeoDataFrame de puntos."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        raise ImportError("pip install geopandas shapely")

    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs=f"EPSG:{epsg}")


def bounding_box_colombia(buffer_deg: float = 0.0) -> Tuple[float, float, float, float]:
    """Bounding box de Colombia en WGS84 (lon_min, lat_min, lon_max, lat_max)."""
    return (
        -82.0 - buffer_deg,
        -4.5  - buffer_deg,
        -66.0 + buffer_deg,
        13.0  + buffer_deg,
    )


def clip_to_colombia(gdf, buffer_deg: float = 0.5):
    """Recorta un GeoDataFrame al territorio colombiano."""
    try:
        import geopandas as gpd
        from shapely.geometry import box
    except ImportError:
        raise ImportError("pip install geopandas shapely")

    bbox = bounding_box_colombia(buffer_deg)
    colombia_box = gpd.GeoDataFrame(geometry=[box(*bbox)], crs="EPSG:4326")
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gpd.clip(gdf, colombia_box)
