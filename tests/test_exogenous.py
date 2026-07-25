"""Tests para features/exogenous.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.features.exogenous import (
    align_exogenous,
    create_exog_matrix,
    meteorological_features,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def target_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=30, freq="D"),
            "pm25": np.random.default_rng(0).normal(20, 5, 30),
        }
    )


@pytest.fixture
def exog_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=30, freq="D"),
            "temperatura": np.random.default_rng(1).normal(15, 3, 30),
            "humedad": np.random.default_rng(2).normal(75, 10, 30),
        }
    )


@pytest.fixture
def meteo_df():
    np.random.seed(42)
    n = 50
    return pd.DataFrame(
        {
            "temp": np.random.normal(20, 5, n),
            "viento": np.abs(np.random.normal(3, 1, n)),
            "humedad": np.random.normal(70, 10, n),
            "lluvia": np.abs(np.random.normal(2, 3, n)),
        }
    )


# ---------------------------------------------------------------------------
# align_exogenous
# ---------------------------------------------------------------------------


class TestAlignExogenous:
    def test_returns_dataframe(self, target_df, exog_df):
        result = align_exogenous(
            target_df,
            exog_df,
            date_col_target="fecha",
            date_col_exog="fecha",
            exog_cols=["temperatura", "humedad"],
        )
        assert isinstance(result, pd.DataFrame)

    def test_exog_cols_added(self, target_df, exog_df):
        result = align_exogenous(
            target_df,
            exog_df,
            date_col_target="fecha",
            date_col_exog="fecha",
            exog_cols=["temperatura"],
        )
        assert "temperatura" in result.columns

    def test_same_row_count(self, target_df, exog_df):
        result = align_exogenous(
            target_df,
            exog_df,
            date_col_target="fecha",
            date_col_exog="fecha",
        )
        assert len(result) == len(target_df)


# ---------------------------------------------------------------------------
# create_exog_matrix
# ---------------------------------------------------------------------------


class TestCreateExogMatrix:
    def test_returns_train_and_future_keys(self, target_df):
        df = target_df.copy()
        df["temp"] = 15.0
        result = create_exog_matrix(df, cols=["temp"], date_col="fecha", train_end_idx=20)
        assert "train" in result and "future" in result

    def test_train_size(self, target_df):
        df = target_df.copy()
        df["temp"] = 15.0
        result = create_exog_matrix(df, cols=["temp"], date_col="fecha", train_end_idx=20)
        assert len(result["train"]) == 20

    def test_future_size(self, target_df):
        df = target_df.copy()
        df["temp"] = 15.0
        result = create_exog_matrix(df, cols=["temp"], date_col="fecha", train_end_idx=20)
        assert len(result["future"]) == len(target_df) - 20

    def test_works_without_date_col_in_columns(self, target_df):
        df = target_df.set_index("fecha")
        df["temp"] = 15.0
        result = create_exog_matrix(df, cols=["temp"], date_col="fecha", train_end_idx=10)
        assert len(result["train"]) == 10


# ---------------------------------------------------------------------------
# meteorological_features
# ---------------------------------------------------------------------------


class TestMeteorologicalFeatures:
    def test_heat_index_created(self, meteo_df):
        result = meteorological_features(meteo_df, temp_col="temp", humidity_col="humedad")
        assert "heat_index" in result.columns

    def test_wind_sq_created(self, meteo_df):
        result = meteorological_features(meteo_df, wind_col="viento")
        assert "viento_sq" in result.columns
        assert (result["viento_sq"] >= 0).all()

    def test_lluvia_bin_created(self, meteo_df):
        result = meteorological_features(meteo_df, rain_col="lluvia")
        assert "lluvia_bin" in result.columns
        assert result["lluvia_bin"].isin([0, 1]).all()

    def test_no_cols_specified_returns_copy(self, meteo_df):
        result = meteorological_features(meteo_df)
        assert result.shape == meteo_df.shape

    def test_missing_col_skipped(self, meteo_df):
        result = meteorological_features(meteo_df, temp_col="no_existe", humidity_col="humedad")
        assert "heat_index" not in result.columns
