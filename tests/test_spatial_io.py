"""Tests para spatial/io.py — lectura/escritura de formatos espaciales.

En el entorno típico de CI **no** hay geopandas/rasterio/fiona/xarray instalados,
así que estos tests se enfocan en los paths de ImportError (cobertura del except)
y usan `pytest.importorskip` cuando el camino de éxito requiere la dependencia.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from estadistica_ambiental.spatial.io import (
    list_gpkg_layers,
    load_netcdf_spatial,
    load_raster,
    load_vector,
    vector_to_parquet,
)


class TestLoadVector:
    def test_import_error_when_geopandas_missing(self, monkeypatch, tmp_path):
        """ImportError elevada con mensaje de instalación cuando geopandas falta."""
        import sys

        monkeypatch.setitem(sys.modules, "geopandas", None)
        with pytest.raises(ImportError, match="geopandas"):
            load_vector(tmp_path / "fake.shp")

    def test_file_not_found_when_path_missing(self, tmp_path):
        """Si geopandas está, FileNotFoundError debe lanzarse antes de leer."""
        pytest.importorskip("geopandas")
        with pytest.raises(FileNotFoundError, match="no encontrado"):
            load_vector(tmp_path / "no_existe.shp")


class TestLoadRaster:
    def test_import_error_when_rasterio_missing(self, monkeypatch, tmp_path):
        import sys

        monkeypatch.setitem(sys.modules, "rasterio", None)
        with pytest.raises(ImportError, match="rasterio"):
            load_raster(tmp_path / "fake.tif")


class TestLoadNetcdfSpatial:
    def test_import_error_when_xarray_missing(self, monkeypatch, tmp_path):
        import sys

        monkeypatch.setitem(sys.modules, "xarray", None)
        with pytest.raises(ImportError, match="xarray"):
            load_netcdf_spatial(tmp_path / "fake.nc")


class TestListGpkgLayers:
    def test_import_error_when_fiona_missing(self, monkeypatch, tmp_path):
        import sys

        monkeypatch.setitem(sys.modules, "fiona", None)
        with pytest.raises(ImportError, match="fiona"):
            list_gpkg_layers(tmp_path / "fake.gpkg")

    def test_calls_fiona_listlayers(self, monkeypatch, tmp_path):
        """Path de éxito: fiona.listlayers se invoca con la ruta correcta."""
        import sys

        fake_fiona = SimpleNamespace(listlayers=MagicMock(return_value=["capa1", "capa2"]))
        monkeypatch.setitem(sys.modules, "fiona", fake_fiona)

        result = list_gpkg_layers(tmp_path / "datos.gpkg")
        assert result == ["capa1", "capa2"]
        fake_fiona.listlayers.assert_called_once_with(str(tmp_path / "datos.gpkg"))


class TestVectorToParquet:
    def test_creates_parent_dir_and_calls_to_parquet(self, tmp_path):
        """Verifica que crea el directorio padre y delega en gdf.to_parquet()."""
        out = tmp_path / "subdir" / "vector.parquet"
        mock_gdf = MagicMock()

        result = vector_to_parquet(mock_gdf, out)

        assert isinstance(result, Path)
        assert result == out
        assert out.parent.is_dir()
        mock_gdf.to_parquet.assert_called_once_with(out)

    def test_accepts_string_path(self, tmp_path):
        out_str = str(tmp_path / "vec.parquet")
        mock_gdf = MagicMock()

        result = vector_to_parquet(mock_gdf, out_str)

        assert isinstance(result, Path)
        mock_gdf.to_parquet.assert_called_once()
