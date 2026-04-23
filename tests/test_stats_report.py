"""Tests para reporting/stats_report.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.reporting.stats_report import stats_report


@pytest.fixture
def env_df():
    np.random.seed(0)
    n = 60
    return pd.DataFrame({
        "fecha": pd.date_range("2020-01-01", periods=n, freq="ME"),
        "pm25": np.random.gamma(3, 5, n),
        "temperatura": np.random.normal(15, 3, n),
    })


class TestStatsReport:
    def test_creates_html_file(self, tmp_path, env_df):
        out = tmp_path / "stats.html"
        stats_report(env_df, output=str(out), date_col="fecha")
        assert out.exists()

    def test_returns_path(self, tmp_path, env_df):
        from pathlib import Path
        out = tmp_path / "stats.html"
        result = stats_report(env_df, output=str(out))
        assert isinstance(result, Path)

    def test_html_contains_title(self, tmp_path, env_df):
        out = tmp_path / "stats.html"
        stats_report(env_df, output=str(out), title="Reporte PM2.5")
        content = out.read_text(encoding="utf-8")
        assert "Reporte PM2.5" in content

    def test_with_date_col_adds_sections(self, tmp_path, env_df):
        out = tmp_path / "stats_full.html"
        stats_report(env_df, output=str(out), date_col="fecha")
        content = out.read_text(encoding="utf-8")
        assert "Estacionariedad" in content

    def test_without_date_col_still_creates(self, tmp_path, env_df):
        out = tmp_path / "stats_nodates.html"
        stats_report(env_df.drop(columns=["fecha"]), output=str(out))
        assert out.exists()

    def test_specific_value_cols(self, tmp_path, env_df):
        out = tmp_path / "stats_cols.html"
        stats_report(env_df, output=str(out), date_col="fecha", value_cols=["pm25"])
        content = out.read_text(encoding="utf-8")
        assert "pm25" in content

    def test_creates_parent_dirs(self, tmp_path, env_df):
        out = tmp_path / "sub" / "report.html"
        stats_report(env_df, output=str(out))
        assert out.exists()

    def test_short_series_stationarity_skipped(self, tmp_path):
        # Series < 20 puntos → _section_stationarity las salta sin error
        df = pd.DataFrame({
            "fecha": pd.date_range("2020-01-01", periods=10, freq="ME"),
            "pm25": np.random.default_rng(1).normal(20, 5, 10),
        })
        out = tmp_path / "short.html"
        stats_report(df, output=str(out), date_col="fecha")
        assert out.exists()
