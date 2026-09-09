"""Tests para spatial/io.py — lectura/escritura de formatos espaciales.

En el entorno típico de CI del JOB principal **no** hay geopandas/rasterio/
fiona/xarray instalados, así que los paths de ImportError (cobertura del
except) están cubiertos sin depender de nada. Los paths de éxito usan
`pytest.importorskip` y solo corren (y cuentan para cobertura) en el job
`test-spatial`, que sí instala esas dependencias.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
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

    def test_repairs_invalid_geometry_with_buffer_zero(self, tmp_path, caplog):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Polygon

        # Polígono "bowtie" autointersectante: geometría inválida real, no
        # simulada -- confirmado con .is_valid antes de escribir el archivo.
        bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
        assert not bowtie.is_valid
        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[bowtie], crs="EPSG:4326")
        path = tmp_path / "invalida.geojson"
        gdf.to_file(path, driver="GeoJSON")

        result = load_vector(path)

        assert result.geometry.is_valid.all()
        assert "geometría(s) inválida(s)" in caplog.text

    def test_reprojects_when_to_epsg_given(self, tmp_path):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-74.1, 4.6)], crs="EPSG:4326")
        path = tmp_path / "punto.geojson"
        gdf.to_file(path, driver="GeoJSON")

        result = load_vector(path, to_epsg=3857)

        assert result.crs.to_epsg() == 3857

    def test_skips_reprojection_when_already_target_epsg(self, tmp_path, monkeypatch):
        # to_epsg == CRS actual: no debe llamar a to_crs (rama `!= to_epsg`).
        # to_crs(4326) sobre datos ya en 4326 es identidad, así que sin
        # espiar la llamada el test pasaría igual con o sin la rama.
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-74.1, 4.6)], crs="EPSG:4326")
        path = tmp_path / "punto.geojson"
        gdf.to_file(path, driver="GeoJSON")

        original_to_crs = gpd.GeoDataFrame.to_crs
        spy = MagicMock(side_effect=original_to_crs)
        monkeypatch.setattr(gpd.GeoDataFrame, "to_crs", spy)

        result = load_vector(path, to_epsg=4326)

        spy.assert_not_called()
        assert result.crs.to_epsg() == 4326


class TestLoadRaster:
    def test_import_error_when_rasterio_missing(self, monkeypatch, tmp_path):
        import sys

        monkeypatch.setitem(sys.modules, "rasterio", None)
        with pytest.raises(ImportError, match="rasterio"):
            load_raster(tmp_path / "fake.tif")

    def test_reads_real_geotiff_metadata_and_data(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from rasterio.transform import from_origin

        path = tmp_path / "test.tif"
        data = np.arange(9, dtype="float32").reshape(3, 3)
        transform = from_origin(-75, 5, 0.1, 0.1)
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=3,
            width=3,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999,
        ) as dst:
            dst.write(data, 1)

        result = load_raster(path)

        assert set(result) == {"data", "transform", "crs", "shape", "nodata", "bounds", "res"}
        np.testing.assert_array_equal(result["data"], data)
        assert result["shape"] == (3, 3)
        assert result["nodata"] == -9999
        assert result["crs"].to_epsg() == 4326


class TestLoadNetcdfSpatial:
    def test_import_error_when_xarray_missing(self, monkeypatch, tmp_path):
        import sys

        monkeypatch.setitem(sys.modules, "xarray", None)
        with pytest.raises(ImportError, match="xarray"):
            load_netcdf_spatial(tmp_path / "fake.nc")

    @pytest.fixture
    def sample_netcdf(self, tmp_path):
        xr = pytest.importorskip("xarray")
        pytest.importorskip("h5netcdf")
        ds = xr.Dataset(
            {
                "temp": (("time", "lat", "lon"), np.arange(8.0).reshape(2, 2, 2)),
                "precip": (("time", "lat", "lon"), np.arange(8.0).reshape(2, 2, 2) * 10),
            },
            coords={
                "time": ["2024-01-01", "2024-01-02"],
                "lat": [4.0, 5.0],
                "lon": [-75.0, -74.0],
            },
        )
        path = tmp_path / "datos.nc"
        # h5netcdf en vez del engine por defecto (netcdf4, no instalado en este entorno).
        ds.to_netcdf(path, engine="h5netcdf")
        return path

    def test_subsets_single_variable(self, sample_netcdf):
        result = load_netcdf_spatial(sample_netcdf, variable="temp")
        assert list(result.data_vars) == ["temp"]

    def test_slices_time_dimension(self, sample_netcdf):
        result = load_netcdf_spatial(sample_netcdf, time_slice=slice("2024-01-01", "2024-01-01"))
        assert result.sizes["time"] == 1


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
