"""Tests para preprocessing/resampling.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.preprocessing.resampling import (
    resample,
    align_frequencies,
    fill_missing_timestamps,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def hourly_df():
    n = 72  # 3 días horarios
    return pd.DataFrame({
        "fecha": pd.date_range("2023-01-01", periods=n, freq="h"),
        "pm25": np.random.default_rng(0).normal(20, 5, n),
        "lluvia": np.abs(np.random.default_rng(1).normal(1, 2, n)),
    })


# ---------------------------------------------------------------------------
# resample
# ---------------------------------------------------------------------------

class TestResample:
    def test_mean_reduces_rows(self, hourly_df):
        result = resample(hourly_df, "fecha", freq="D", agg="mean")
        assert len(result) == 3

    def test_sum_agg(self, hourly_df):
        result = resample(hourly_df, "fecha", freq="D", agg="sum")
        assert len(result) == 3
        # La suma diaria debe ser mayor que la media individual
        assert result["pm25"].sum() > hourly_df["pm25"].mean()

    def test_dict_agg(self, hourly_df):
        result = resample(hourly_df, "fecha", freq="D",
                          agg={"pm25": "mean", "lluvia": "sum"})
        assert "pm25" in result.columns
        assert "lluvia" in result.columns

    def test_custom_value_cols(self, hourly_df):
        result = resample(hourly_df, "fecha", value_cols=["pm25"], freq="D")
        assert "pm25" in result.columns
        assert "lluvia" not in result.columns

    def test_date_col_in_output(self, hourly_df):
        result = resample(hourly_df, "fecha", freq="D")
        assert "fecha" in result.columns

    def test_weekly_agg(self, hourly_df):
        result = resample(hourly_df, "fecha", freq="W")
        assert len(result) <= 3


# ---------------------------------------------------------------------------
# align_frequencies
# ---------------------------------------------------------------------------

class TestAlignFrequencies:
    def test_returns_list(self, hourly_df):
        result = align_frequencies([hourly_df, hourly_df], ["fecha", "fecha"], target_freq="D")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_all_resampled_to_daily(self, hourly_df):
        result = align_frequencies([hourly_df, hourly_df], ["fecha", "fecha"], target_freq="D")
        for df in result:
            assert len(df) == 3


# ---------------------------------------------------------------------------
# fill_missing_timestamps
# ---------------------------------------------------------------------------

class TestFillMissingTimestamps:
    def test_fills_gaps(self):
        df = pd.DataFrame({
            "fecha": pd.to_datetime(["2023-01-01", "2023-01-03", "2023-01-05"]),
            "val": [1.0, 3.0, 5.0],
        })
        result = fill_missing_timestamps(df, "fecha", freq="D")
        assert len(result) == 5

    def test_inserted_vals_are_nan(self):
        df = pd.DataFrame({
            "fecha": pd.to_datetime(["2023-01-01", "2023-01-03"]),
            "val": [1.0, 3.0],
        })
        result = fill_missing_timestamps(df, "fecha", freq="D")
        assert result["val"].isna().sum() == 1
