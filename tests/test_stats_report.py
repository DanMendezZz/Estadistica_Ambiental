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
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2020-01-01", periods=n, freq="ME"),
            "pm25": np.random.gamma(3, 5, n),
            "temperatura": np.random.normal(15, 3, n),
        }
    )


class TestStatsReport:
    def test_creates_html_file(self, tmp_path, env_df):
        out = tmp_path / "stats.html"
        stats_report(env_df, output=str(out), date_col="fecha")
        assert out.exists()
        assert out.stat().st_size > 500
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()

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
        assert out.stat().st_size > 500
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()

    def test_specific_value_cols(self, tmp_path, env_df):
        out = tmp_path / "stats_cols.html"
        stats_report(env_df, output=str(out), date_col="fecha", value_cols=["pm25"])
        content = out.read_text(encoding="utf-8")
        assert "pm25" in content

    def test_creates_parent_dirs(self, tmp_path, env_df):
        out = tmp_path / "sub" / "report.html"
        stats_report(env_df, output=str(out))
        assert out.exists()
        assert out.parent.is_dir()
        assert out.stat().st_size > 500

    def test_short_series_stationarity_skipped(self, tmp_path):
        # Series < 20 puntos → _section_stationarity las salta sin error
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2020-01-01", periods=10, freq="ME"),
                "pm25": np.random.default_rng(1).normal(20, 5, 10),
            }
        )
        out = tmp_path / "short.html"
        stats_report(df, output=str(out), date_col="fecha")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()

    def test_very_short_series_trend_skipped(self, tmp_path):
        """_section_trend: len(s) < 10 → continue; si todos, retorna '' (lines 78, 94)."""
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2020-01-01", periods=5, freq="ME"),
                "pm25": [10.0, 12.0, 11.0, 13.0, 12.5],
            }
        )
        out = tmp_path / "short_trend.html"
        stats_report(df, output=str(out), date_col="fecha")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()

    def test_stationarity_exception_handled(self, tmp_path, monkeypatch):
        """_section_stationarity: excepción capturada con continue (lines 65-66)."""
        import estadistica_ambiental.reporting.stats_report as sr

        def bad_stationarity(s):
            raise RuntimeError("forced stationarity error")

        monkeypatch.setattr(sr, "stationarity_report", bad_stationarity)

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2020-01-01", periods=30, freq="ME"),
                "pm25": np.arange(30, dtype=float),
            }
        )
        out = tmp_path / "exc_stat.html"
        stats_report(df, output=str(out), date_col="fecha")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "forced stationarity error" not in content

    def test_trend_exception_handled(self, tmp_path, monkeypatch):
        """_section_trend: excepción en mann_kendall capturada (lines 91-92)."""
        import estadistica_ambiental.reporting.stats_report as sr

        def bad_mk(s):
            raise RuntimeError("forced trend error")

        monkeypatch.setattr(sr, "mann_kendall", bad_mk)

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2020-01-01", periods=15, freq="ME"),
                "pm25": np.arange(15, dtype=float),
            }
        )
        out = tmp_path / "exc_trend.html"
        stats_report(df, output=str(out), date_col="fecha")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "forced trend error" not in content
