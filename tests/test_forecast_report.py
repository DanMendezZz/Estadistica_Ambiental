"""Tests para reporting/forecast_report.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.reporting.forecast_report import (
    _build_body,
    _section_metrics_table,
    _section_series,
    _section_summary,
    forecast_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_data():
    y_true = pd.Series(
        np.random.default_rng(0).normal(20, 5, 30),
        index=pd.date_range("2023-01-01", periods=30, freq="D"),
    )
    predictions = {
        "SARIMAX": np.random.default_rng(1).normal(20, 5, 30),
        "XGBoost": np.random.default_rng(2).normal(20, 5, 30),
    }
    metrics = {
        "SARIMAX": {"rmse": 4.5, "mae": 3.2, "r2": 0.81},
        "XGBoost": {"rmse": 3.9, "mae": 2.8, "r2": 0.87},
    }
    return y_true, predictions, metrics


# ---------------------------------------------------------------------------
# forecast_report — función principal
# ---------------------------------------------------------------------------


class TestForecastReport:
    def test_creates_html_file(self, tmp_path, sample_data):
        y_true, preds, mets = sample_data
        out = tmp_path / "report.html"
        result = forecast_report(y_true, preds, mets, output=str(out))
        assert out.exists()
        assert result == out

    def test_html_contains_title(self, tmp_path, sample_data):
        y_true, preds, mets = sample_data
        out = tmp_path / "report.html"
        forecast_report(y_true, preds, mets, output=str(out), title="Reporte PM2.5")
        content = out.read_text(encoding="utf-8")
        assert "Reporte PM2.5" in content

    def test_creates_parent_dir(self, tmp_path, sample_data):
        y_true, preds, mets = sample_data
        out = tmp_path / "sub" / "deep" / "report.html"
        forecast_report(y_true, preds, mets, output=str(out))
        assert out.exists()

    def test_html_contains_model_names(self, tmp_path, sample_data):
        y_true, preds, mets = sample_data
        out = tmp_path / "report.html"
        forecast_report(y_true, preds, mets, output=str(out))
        content = out.read_text(encoding="utf-8")
        assert "SARIMAX" in content
        assert "XGBoost" in content

    def test_returns_path_object(self, tmp_path, sample_data):
        from pathlib import Path

        y_true, preds, mets = sample_data
        out = tmp_path / "report.html"
        result = forecast_report(y_true, preds, mets, output=str(out))
        assert isinstance(result, Path)

    def test_unit_in_output(self, tmp_path, sample_data):
        y_true, preds, mets = sample_data
        out = tmp_path / "report.html"
        forecast_report(y_true, preds, mets, output=str(out), variable_name="PM2.5", unit="µg/m³")
        content = out.read_text(encoding="utf-8")
        assert "µg/m³" in content


# ---------------------------------------------------------------------------
# _section_summary
# ---------------------------------------------------------------------------


class TestSectionSummary:
    def test_empty_metrics_returns_empty_string(self):
        assert _section_summary({}) == ""

    def test_identifies_best_model_by_rmse(self):
        metrics = {
            "A": {"rmse": 5.0},
            "B": {"rmse": 2.0},
        }
        result = _section_summary(metrics)
        assert "B" in result

    def test_shows_model_count(self):
        metrics = {"A": {"rmse": 1.0}, "B": {"rmse": 2.0}, "C": {"rmse": 3.0}}
        result = _section_summary(metrics)
        assert "3" in result


# ---------------------------------------------------------------------------
# _section_metrics_table
# ---------------------------------------------------------------------------


class TestSectionMetricsTable:
    def test_empty_metrics_returns_empty_string(self):
        assert _section_metrics_table({}) == ""

    def test_contains_metric_keys(self):
        metrics = {"ModelA": {"rmse": 1.5, "mae": 1.0}}
        result = _section_metrics_table(metrics)
        assert "rmse" in result
        assert "mae" in result

    def test_best_model_marked(self):
        metrics = {
            "Good": {"rmse": 1.0},
            "Bad": {"rmse": 5.0},
        }
        result = _section_metrics_table(metrics)
        assert "best" in result

    def test_contains_table_html(self):
        metrics = {"M": {"rmse": 2.0}}
        result = _section_metrics_table(metrics)
        assert "<table>" in result
        assert "<th>" in result


# ---------------------------------------------------------------------------
# _section_series
# ---------------------------------------------------------------------------


class TestSectionSeries:
    def test_contains_canvas(self):
        y_true = pd.Series([1.0, 2.0, 3.0])
        preds = {"ModelA": np.array([1.1, 2.1, 3.1])}
        result = _section_series(y_true, preds, "PM2.5", "µg/m³")
        assert "canvas" in result

    def test_contains_model_name(self):
        y_true = pd.Series([10.0, 12.0, 11.0])
        preds = {"SARIMAX": np.array([10.5, 11.5, 11.0])}
        result = _section_series(y_true, preds, "PM2.5", "")
        assert "SARIMAX" in result

    def test_multiple_models_all_present(self):
        y_true = pd.Series([10.0, 12.0])
        preds = {"A": np.array([10.0, 12.0]), "B": np.array([11.0, 11.0])}
        result = _section_series(y_true, preds, "PM2.5", "µg/m³")
        assert "A" in result and "B" in result

    def test_no_unit_still_works(self):
        y_true = pd.Series([5.0, 6.0])
        preds = {"M": np.array([5.1, 6.1])}
        result = _section_series(y_true, preds, "caudal", "")
        assert "caudal" in result


# ---------------------------------------------------------------------------
# _build_body
# ---------------------------------------------------------------------------


class TestBuildBody:
    def test_returns_string(self):
        y_true = pd.Series([1.0, 2.0, 3.0])
        preds = {"M": np.array([1.0, 2.0, 3.0])}
        mets = {"M": {"rmse": 0.0}}
        result = _build_body(y_true, preds, mets, "v", "u")
        assert isinstance(result, str)
        assert len(result) > 0
