"""Tests para features/climate.py — load_oni, enso_dummy, enso_lagged."""

from __future__ import annotations

import textwrap

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.features.climate import (
    enso_dummy,
    enso_lagged,
    load_oni,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ONI_CONTENT = textwrap.dedent("""\
    Year  Season  Anom  Total
    2020  DJF     0.5   27.2
    2020  JFM     0.4   27.0
    2020  FMA     0.3   26.8
    2020  MAM    -0.2   26.5
    2020  AMJ    -0.6   26.2
    2020  MJJ    -0.8   26.0
    2020  JJA    -0.9   25.9
    2020  JAS    -1.2   25.7
    2020  ASO    -1.4   25.5
    2020  SON    -1.5   25.3
    2020  OND    -1.6   25.1
    2020  NDJ    -1.2   25.3
    2021  DJF    -1.0   25.5
    2021  JFM    -0.6   25.8
    2021  FMA    -0.2   26.1
    2021  MAM     0.1   26.4
""")


@pytest.fixture
def oni_file(tmp_path):
    f = tmp_path / "oni.txt"
    f.write_text(ONI_CONTENT, encoding="utf-8")
    return str(f)


@pytest.fixture
def oni_df(oni_file):
    return load_oni(path=oni_file, start_year=2020)


@pytest.fixture
def env_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2020-01-01", periods=24, freq="ME"),
            "caudal": np.random.default_rng(0).normal(50, 10, 24),
        }
    )


# ---------------------------------------------------------------------------
# load_oni con archivo local
# ---------------------------------------------------------------------------


class TestLoadOni:
    def test_returns_dataframe(self, oni_file):
        df = load_oni(path=oni_file, start_year=2020)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, oni_df):
        assert set(["fecha", "oni", "fase", "intensidad"]).issubset(oni_df.columns)

    def test_start_year_filter(self, oni_file):
        df2021 = load_oni(path=oni_file, start_year=2021)
        assert df2021["fecha"].dt.year.min() == 2021

    def test_fase_values_valid(self, oni_df):
        valid_fases = {"niño", "niña", "neutro"}
        assert set(oni_df["fase"].unique()).issubset(valid_fases)

    def test_intensidad_values_valid(self, oni_df):
        valid_int = {"fuerte", "moderado", "neutro"}
        assert set(oni_df["intensidad"].unique()).issubset(valid_int)

    def test_no_path_mocked_failure_returns_empty(self, monkeypatch):
        # Simular fallo de red → debe devolver DataFrame vacío
        def mock_read_csv(*args, **kwargs):
            raise OSError("sin red")

        monkeypatch.setattr("estadistica_ambiental.features.climate.pd.read_csv", mock_read_csv)
        df = load_oni(start_year=2020)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_oni_column_is_float(self, oni_df):
        assert oni_df["oni"].dtype == float


# ---------------------------------------------------------------------------
# enso_dummy
# ---------------------------------------------------------------------------


class TestEnsoDummy:
    def test_returns_dataframe(self, env_df, oni_df):
        result = enso_dummy(env_df, oni_df, date_col="fecha")
        assert isinstance(result, pd.DataFrame)

    def test_adds_oni_column(self, env_df, oni_df):
        result = enso_dummy(env_df, oni_df, date_col="fecha")
        assert "oni" in result.columns

    def test_adds_dummies(self, env_df, oni_df):
        result = enso_dummy(env_df, oni_df, date_col="fecha")
        dummy_cols = [c for c in result.columns if c.startswith("enso_")]
        assert len(dummy_cols) >= 1

    def test_preserves_row_count(self, env_df, oni_df):
        result = enso_dummy(env_df, oni_df, date_col="fecha")
        assert len(result) == len(env_df)


# ---------------------------------------------------------------------------
# enso_lagged
# ---------------------------------------------------------------------------


class TestEnsoLagged:
    def test_adds_oni_lagged(self, env_df, oni_df):
        result = enso_lagged(env_df, oni_df, date_col="fecha", linea_tematica="oferta_hidrica")
        assert any("oni" in c for c in result.columns)

    def test_preserves_row_count(self, env_df, oni_df):
        result = enso_lagged(env_df, oni_df, date_col="fecha", linea_tematica="calidad_aire")
        assert len(result) == len(env_df)
