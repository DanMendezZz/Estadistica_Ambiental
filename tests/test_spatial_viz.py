"""Tests para spatial/viz.py — mapas de estaciones, coropletas y kriging.

folium/branca/matplotlib sí se asumen instalados (parte del stack base);
choropleth_map requiere geopandas → se salta con `importorskip`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.spatial.viz import (
    choropleth_map,
    map_stations,
    plot_kriging_map,
)


class TestMapStations:
    @pytest.fixture
    def stations_df(self):
        return pd.DataFrame(
            {
                "lat": [4.60, 4.65, 4.55],
                "lon": [-74.10, -74.15, -74.05],
                "nombre": ["Kennedy", "Usme", "Suba"],
                "pm25": [25.0, 30.0, 18.0],
            }
        )

    def test_returns_folium_map(self, stations_df):
        folium = pytest.importorskip("folium")
        m = map_stations(stations_df, label_col="nombre")
        assert isinstance(m, folium.Map)

    def test_contains_one_marker_per_station(self, stations_df):
        """El HTML debe tener tantos CircleMarker como estaciones."""
        m = map_stations(stations_df, label_col="nombre", value_col="pm25")
        html = m._repr_html_()
        assert html.count("circle_marker") >= len(stations_df)

    def test_title_appears_in_html(self, stations_df):
        m = map_stations(stations_df, label_col="nombre", title="Mi Red")
        html = m._repr_html_()
        assert "Mi Red" in html

    def test_import_error_when_folium_missing(self, monkeypatch, stations_df):
        import sys

        monkeypatch.setitem(sys.modules, "folium", None)
        with pytest.raises(ImportError, match="folium"):
            map_stations(stations_df)


class TestChoroplethMap:
    """choropleth_map requiere geopandas — se salta limpiamente si no está."""

    def test_returns_folium_map(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        gdf = gpd.GeoDataFrame(
            {"valor": [1.0, 2.0, 3.0], "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)]},
            crs="EPSG:4326",
        )
        import folium

        m = choropleth_map(gdf, value_col="valor", title="Test")
        assert isinstance(m, folium.Map)


class TestPlotKrigingMap:
    @pytest.fixture
    def kriging_grid(self):
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 5), np.linspace(-74.5, -73.5, 5), indexing="ij"
        )
        z = np.random.default_rng(0).normal(15, 3, grid_lat.shape)
        return grid_lat, grid_lon, z

    def test_returns_matplotlib_figure(self, kriging_grid):
        plt = pytest.importorskip("matplotlib.pyplot")
        grid_lat, grid_lon, z = kriging_grid
        fig = plot_kriging_map(grid_lat, grid_lon, z, title="PM2.5 Kriging")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_with_overlay_points(self, kriging_grid):
        """Pasar points_df agrega scatter de estaciones (cubre rama if points_df)."""
        plt = pytest.importorskip("matplotlib.pyplot")
        grid_lat, grid_lon, z = kriging_grid
        points = pd.DataFrame({"lat": [4.2, 4.7], "lon": [-74.3, -73.8]})
        fig = plot_kriging_map(grid_lat, grid_lon, z, points_df=points)
        # Verifica que el ax tiene un PathCollection (scatter)
        ax = fig.axes[0]
        scatters = [c for c in ax.collections if hasattr(c, "get_offsets") and len(c.get_offsets()) > 0]
        assert any(len(s.get_offsets()) == len(points) for s in scatters)
        plt.close(fig)

    def test_axes_labels_set(self, kriging_grid):
        plt = pytest.importorskip("matplotlib.pyplot")
        grid_lat, grid_lon, z = kriging_grid
        fig = plot_kriging_map(grid_lat, grid_lon, z)
        ax = fig.axes[0]
        assert ax.get_xlabel() == "Longitud"
        assert ax.get_ylabel() == "Latitud"
        plt.close(fig)
