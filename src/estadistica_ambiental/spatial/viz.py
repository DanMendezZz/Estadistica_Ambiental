"""Visualización espacial: mapas de estaciones, interpolación y coropletas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import folium
    import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def map_stations(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    label_col: Optional[str] = None,
    value_col: Optional[str] = None,
    title: str = "Estaciones de monitoreo",
    zoom: int = 6,
) -> "folium.Map":
    """Mapa interactivo de estaciones con folium.

    Requiere: pip install folium (incluido en [spatial]).
    """
    try:
        import folium
    except ImportError:
        raise ImportError("pip install folium  (o [spatial])")

    center_lat = df[lat_col].mean()
    center_lon = df[lon_col].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom,
                   tiles="CartoDB positron")

    for _, row in df.iterrows():
        popup_text = f"{row.get(label_col, '')} — {row.get(value_col, '')}" if value_col else str(row.get(label_col, ""))
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=6,
            color="#1a5276",
            fill=True,
            fill_color="#2e86c1",
            fill_opacity=0.7,
            popup=popup_text,
        ).add_to(m)

    folium.map.Marker(
        [center_lat + 0.5, center_lon],
        icon=folium.DivIcon(html=f"<b style='font-size:14px;color:#1a5276'>{title}</b>"),
    ).add_to(m)

    return m


def choropleth_map(
    gdf,
    value_col: str,
    title: str = "Mapa",
    cmap: str = "YlOrRd",
    zoom: int = 6,
) -> "folium.Map":
    """Mapa coroplético de un GeoDataFrame con folium + branca.

    Requiere: pip install folium branca.
    """
    try:
        import branca.colormap as cm
        import folium
    except ImportError:
        raise ImportError("pip install folium branca")

    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    colormap = cm.linear.YlOrRd_09.scale(gdf[value_col].min(), gdf[value_col].max())
    colormap.caption = value_col

    folium.GeoJson(
        gdf,
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"].get(value_col, 0)),
            "color": "#333",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=folium.GeoJsonTooltip(fields=[value_col]),
    ).add_to(m)
    colormap.add_to(m)
    return m


def plot_kriging_map(
    grid_lat: np.ndarray,
    grid_lon: np.ndarray,
    z_values: np.ndarray,
    points_df: Optional[pd.DataFrame] = None,
    lat_col: str = "lat",
    lon_col: str = "lon",
    title: str = "Kriging",
    figsize: tuple = (8, 7),
) -> "plt.Figure":
    """Mapa estático (matplotlib) del resultado del Kriging."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    img = ax.pcolormesh(grid_lon, grid_lat, z_values,
                        cmap="YlOrRd", shading="auto")
    fig.colorbar(img, ax=ax, label=title)

    if points_df is not None:
        ax.scatter(points_df[lon_col], points_df[lat_col],
                   c="black", s=20, zorder=5, label="Estaciones")
        ax.legend(fontsize=8)

    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title(title, fontweight="bold")
    fig.tight_layout()
    return fig
