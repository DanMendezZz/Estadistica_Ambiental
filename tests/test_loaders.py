"""Tests para estadistica_ambiental.io.loaders."""

import textwrap

import pandas as pd
import pytest

from estadistica_ambiental.io.loaders import load, load_csv, load_excel, load_parquet

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CSV_CONTENT = textwrap.dedent("""\
    fecha,estacion,pm25,temperatura
    2023-01-01,Kennedy,15.2,14.5
    2023-01-02,Kennedy,18.7,13.1
    2023-01-03,Kennedy,,12.9
    2023-01-04,Kennedy,22.1,15.0
""")


@pytest.fixture
def csv_file(tmp_path):
    f = tmp_path / "pm25.csv"
    f.write_text(CSV_CONTENT, encoding="utf-8")
    return f


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=4, freq="D"),
            "estacion": ["Kennedy"] * 4,
            "pm25": [15.2, 18.7, None, 22.1],
            "temperatura": [14.5, 13.1, 12.9, 15.0],
        }
    )


# ---------------------------------------------------------------------------
# load_csv
# ---------------------------------------------------------------------------


class TestLoadCsv:
    def test_returns_dataframe(self, csv_file):
        df = load_csv(csv_file)
        assert isinstance(df, pd.DataFrame)

    def test_shape(self, csv_file):
        df = load_csv(csv_file)
        assert df.shape == (4, 4)

    def test_date_col_parsed(self, csv_file):
        df = load_csv(csv_file, date_col="fecha")
        assert pd.api.types.is_datetime64_any_dtype(df["fecha"])

    def test_sorted_by_date(self, csv_file):
        df = load_csv(csv_file, date_col="fecha")
        assert df["fecha"].is_monotonic_increasing

    def test_missing_values_preserved(self, csv_file):
        df = load_csv(csv_file)
        assert df["pm25"].isna().sum() == 1

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_csv(tmp_path / "no_existe.csv")

    def test_nonexistent_date_col_warns(self, csv_file, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            load_csv(csv_file, date_col="no_existe")
        assert "no_existe" in caplog.text


# ---------------------------------------------------------------------------
# load (dispatcher)
# ---------------------------------------------------------------------------


class TestLoad:
    def test_dispatches_csv(self, csv_file):
        df = load(csv_file, date_col="fecha")
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 4

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "datos.xyz"
        f.write_text("a,b\n1,2")
        with pytest.raises(ValueError, match="Formato no soportado"):
            load(f)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load(tmp_path / "no_existe.csv")


# ---------------------------------------------------------------------------
# load_parquet
# ---------------------------------------------------------------------------


class TestLoadParquet:
    def test_roundtrip(self, tmp_path, sample_df):
        p = tmp_path / "datos.parquet"
        sample_df.to_parquet(p, index=False)
        df = load_parquet(p, date_col="fecha")
        assert df.shape == sample_df.shape
        assert pd.api.types.is_datetime64_any_dtype(df["fecha"])


# ---------------------------------------------------------------------------
# load_excel
# ---------------------------------------------------------------------------


class TestLoadExcel:
    def test_roundtrip(self, tmp_path, sample_df):
        p = tmp_path / "datos.xlsx"
        sample_df.to_excel(p, index=False)
        df = load_excel(p, date_col="fecha")
        assert df.shape == sample_df.shape


# ---------------------------------------------------------------------------
# load TSV
# ---------------------------------------------------------------------------


class TestLoadTsv:
    def test_tsv_dispatched(self, tmp_path):
        from estadistica_ambiental.io.loaders import load

        content = "fecha\tpm25\n2023-01-01\t15.2\n2023-01-02\t18.7\n"
        f = tmp_path / "datos.tsv"
        f.write_text(content, encoding="utf-8")
        df = load(f)
        assert df.shape == (2, 2)


# ---------------------------------------------------------------------------
# _detect_encoding / _parse_dates helpers
# ---------------------------------------------------------------------------


class TestLoadNetcdf:
    def test_no_xarray_raises_import_error(self, tmp_path):
        """load_netcdf: ImportError cuando xarray no está instalado."""
        from estadistica_ambiental.io.loaders import load_netcdf

        with pytest.raises(ImportError, match="xarray"):
            load_netcdf(tmp_path / "fake.nc")

    def test_no_xarray_dispatch_raises(self, tmp_path):
        """load (dispatcher) con .nc levanta ImportError por falta de xarray."""
        from estadistica_ambiental.io.loaders import load

        f = tmp_path / "datos.nc"
        f.write_bytes(b"")
        with pytest.raises(ImportError):
            load(f)


class TestLoadShapefile:
    def test_no_geopandas_raises_import_error(self, tmp_path, monkeypatch):
        """load_shapefile: ImportError cuando geopandas no está instalado."""
        import sys

        monkeypatch.setitem(sys.modules, "geopandas", None)
        from estadistica_ambiental.io.loaders import load_shapefile

        with pytest.raises(ImportError, match="geopandas"):
            load_shapefile(tmp_path / "fake.shp")

    def test_no_geopandas_dispatch_raises(self, tmp_path, monkeypatch):
        """load (dispatcher) con .geojson levanta ImportError por falta de geopandas."""
        import sys

        monkeypatch.setitem(sys.modules, "geopandas", None)
        from estadistica_ambiental.io.loaders import load

        f = tmp_path / "datos.geojson"
        f.write_bytes(b"{}")
        with pytest.raises(ImportError):
            load(f)


class TestLoadNetcdfMock:
    def test_load_netcdf_body_with_xarray_mock(self, tmp_path, monkeypatch):
        """Cubre el cuerpo de load_netcdf (lines 116-125) mediante mock de xarray."""
        import sys
        import types
        from unittest.mock import MagicMock

        fake_df = pd.DataFrame(
            {
                "time": pd.date_range("2023-01-01", periods=3, freq="D"),
                "lat": [4.5, 4.6, 4.7],
                "lon": [-74.0, -74.1, -74.2],
                "pm25": [15.0, 18.0, 12.0],
            }
        )
        mock_ds = MagicMock()
        mock_ds.__getitem__.return_value = mock_ds
        mock_ds.to_dataframe.return_value.reset_index.return_value = fake_df

        mock_xr = types.ModuleType("xarray")
        mock_xr.open_dataset = MagicMock(return_value=mock_ds)
        monkeypatch.setitem(sys.modules, "xarray", mock_xr)

        from estadistica_ambiental.io.loaders import load_netcdf

        f = tmp_path / "fake.nc"
        f.write_bytes(b"CDF")  # fake NetCDF header
        df = load_netcdf(f, variable="pm25", date_col="time")
        assert isinstance(df, pd.DataFrame)

    def test_load_netcdf_no_variable_filter(self, tmp_path, monkeypatch):
        """load_netcdf sin variable=None evita el filtro ds[[variable]] (line 120)."""
        import sys
        import types
        from unittest.mock import MagicMock

        fake_df = pd.DataFrame({"time": pd.date_range("2023-01-01", periods=2), "val": [1.0, 2.0]})
        mock_ds = MagicMock()
        mock_ds.to_dataframe.return_value.reset_index.return_value = fake_df

        mock_xr = types.ModuleType("xarray")
        mock_xr.open_dataset = MagicMock(return_value=mock_ds)
        monkeypatch.setitem(sys.modules, "xarray", mock_xr)

        from estadistica_ambiental.io.loaders import load_netcdf

        f = tmp_path / "fake.nc"
        f.write_bytes(b"CDF")
        df = load_netcdf(f)  # variable=None → no filter
        assert isinstance(df, pd.DataFrame)


class TestDetectEncodingChardet:
    def test_chardet_used_when_available(self, tmp_path, monkeypatch):
        """_detect_encoding: usa chardet cuando está disponible (mock)."""
        import sys
        import types

        fake_chardet = types.ModuleType("chardet")
        fake_chardet.detect = lambda data: {"encoding": "latin-1", "confidence": 0.95}
        monkeypatch.setitem(sys.modules, "chardet", fake_chardet)

        f = tmp_path / "test.csv"
        f.write_bytes(b"fecha,pm25\n2023-01-01,15.2\n")

        from estadistica_ambiental.io import loaders

        result = loaders._detect_encoding(f)
        assert result == "latin-1"

    def test_chardet_none_encoding_falls_back_to_utf8(self, tmp_path, monkeypatch):
        """_detect_encoding: si chardet retorna None encoding, usa utf-8."""
        import sys
        import types

        fake_chardet = types.ModuleType("chardet")
        fake_chardet.detect = lambda data: {"encoding": None, "confidence": 0.0}
        monkeypatch.setitem(sys.modules, "chardet", fake_chardet)

        f = tmp_path / "test.csv"
        f.write_bytes(b"fecha,pm25\n2023-01-01,15.2\n")

        from estadistica_ambiental.io import loaders

        result = loaders._detect_encoding(f)
        assert result == "utf-8"


class TestHelpers:
    def test_invalid_date_col_logs_warning(self, csv_file, caplog):
        import logging

        from estadistica_ambiental.io.loaders import load_csv

        with caplog.at_level(logging.WARNING):
            load_csv(csv_file, date_col="columna_inexistente")
        assert "columna_inexistente" in caplog.text

    def test_load_csv_invalid_dates_warns(self, tmp_path, caplog):
        import logging

        content = "fecha,pm25\nnot_a_date,15.2\n2023-01-02,18.7\n"
        f = tmp_path / "bad_dates.csv"
        f.write_text(content, encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            df = load_csv(f, date_col="fecha")
        assert df.shape[0] == 2  # ambas filas cargadas aunque fecha sea NaT
