"""Tests para estadistica_ambiental.descriptive.*"""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.descriptive.bivariate import (
    chi2_test, contingency_table, correlation_matrix, correlation_table,
)
from estadistica_ambiental.descriptive.temporal import (
    acf_values, pacf_values, rolling_stats, seasonal_summary,
)
from estadistica_ambiental.descriptive.univariate import frequency_table, summarize


@pytest.fixture
def env_df():
    np.random.seed(0)
    return pd.DataFrame({
        "fecha":       pd.date_range("2020-01-01", periods=120, freq="ME"),
        "estacion":    ["Kennedy", "Usme"] * 60,
        "pm25":        np.random.gamma(3, 5, 120),
        "pm10":        np.random.gamma(4, 6, 120),
        "temperatura": np.random.normal(15, 3, 120),
        "calidad":     np.random.choice(["buena", "moderada", "mala"], 120),
    })


# --- univariate ---

class TestSummarize:
    def test_returns_dataframe(self, env_df):
        assert isinstance(summarize(env_df), pd.DataFrame)

    def test_contains_expected_stats(self, env_df):
        result = summarize(env_df)
        for col in ["mean", "median", "std", "skewness", "kurtosis"]:
            assert col in result.columns

    def test_grouped(self, env_df):
        result = summarize(env_df, group_col="estacion")
        assert "grupo" in result.columns
        assert result["grupo"].nunique() == 2

    def test_missing_counted(self):
        df = pd.DataFrame({"a": [1.0, 2.0, None, 4.0]})
        assert summarize(df).loc[0, "n_missing"] == 1


class TestFrequencyTable:
    def test_has_columns(self, env_df):
        result = frequency_table(env_df["calidad"])
        assert {"n", "pct"}.issubset(result.columns)

    def test_pct_sums_to_100(self, env_df):
        result = frequency_table(env_df["calidad"])
        assert abs(result["pct"].sum() - 100.0) < 0.1


# --- bivariate ---

class TestCorrelation:
    def test_matrix_is_square(self, env_df):
        mat = correlation_matrix(env_df)
        assert mat.shape[0] == mat.shape[1]

    def test_table_has_pairs(self, env_df):
        tbl = correlation_table(env_df)
        assert "correlation" in tbl.columns and len(tbl) > 0

    def test_contingency_rows(self, env_df):
        ct = contingency_table(env_df, "estacion", "calidad")
        assert ct.shape[0] == 2

    def test_chi2_pval_range(self, env_df):
        result = chi2_test(env_df, "estacion", "calidad")
        assert 0 <= result["pval"] <= 1


# --- temporal ---

class TestTemporal:
    def test_acf_includes_lag0(self, env_df):
        vals = acf_values(env_df["pm25"], nlags=20)
        assert len(vals) == 21

    def test_pacf_length(self, env_df):
        assert len(pacf_values(env_df["pm25"], nlags=20)) == 21

    def test_rolling_stats_columns(self, env_df):
        result = rolling_stats(env_df["pm25"], window=12)
        assert {"mean", "std"}.issubset(result.columns)

    def test_seasonal_summary(self, env_df):
        result = seasonal_summary(env_df, "fecha", "pm25", freq="YE")
        assert "mean" in result.columns and len(result) > 0
