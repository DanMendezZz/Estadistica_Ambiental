"""Tests para estadistica_ambiental.io.validators."""

import pandas as pd
import pytest

from estadistica_ambiental.io.validators import (
    ValidationReport,
    validate,
    _check_missing,
    _check_duplicates,
    _check_ranges,
    _check_temporal,
    PHYSICAL_RANGES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "fecha": pd.date_range("2023-01-01", periods=5, freq="D"),
        "estacion": ["Kennedy"] * 5,
        "pm25": [12.0, 15.0, 18.0, 10.0, 14.0],
        "temperatura": [14.5, 15.0, 13.0, 16.0, 14.0],
    })


@pytest.fixture
def dirty_df():
    return pd.DataFrame({
        "fecha": ["2023-01-01", "2023-01-02", "2023-01-02", "2030-01-01", "2023-01-04"],
        "estacion": ["Kennedy"] * 5,
        "pm25": [12.0, None, 18.0, 9999.0, 14.0],  # None y valor imposible
        "temperatura": [14.5, 15.0, 13.0, 16.0, 14.0],
        "ph": [7.0, 7.5, 8.0, 20.0, 6.5],           # pH=20 imposible
    })


# ---------------------------------------------------------------------------
# _check_missing
# ---------------------------------------------------------------------------

class TestCheckMissing:
    def test_no_missing(self, clean_df):
        result = _check_missing(clean_df)
        assert result == {}

    def test_detects_missing(self, dirty_df):
        result = _check_missing(dirty_df)
        assert "pm25" in result
        assert result["pm25"] == pytest.approx(20.0)

    def test_returns_percentage(self):
        df = pd.DataFrame({"a": [1, None, None, None, None]})
        result = _check_missing(df)
        assert result["a"] == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# _check_duplicates
# ---------------------------------------------------------------------------

class TestCheckDuplicates:
    def test_no_duplicates(self, clean_df):
        exact, key = _check_duplicates(clean_df, key_cols=["estacion", "fecha"])
        assert exact == 0
        assert key == 0

    def test_detects_exact_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        exact, _ = _check_duplicates(df, key_cols=None)
        assert exact == 1

    def test_detects_key_duplicates(self, dirty_df):
        dirty_df["fecha"] = pd.to_datetime(dirty_df["fecha"], errors="coerce")
        _, key = _check_duplicates(dirty_df, key_cols=["estacion", "fecha"])
        assert key >= 1

    def test_ignores_missing_key_col(self, clean_df):
        exact, key = _check_duplicates(clean_df, key_cols=["col_inexistente"])
        assert key == 0


# ---------------------------------------------------------------------------
# _check_ranges
# ---------------------------------------------------------------------------

class TestCheckRanges:
    def test_clean_df_no_violations(self, clean_df):
        result = _check_ranges(clean_df, PHYSICAL_RANGES)
        assert "pm25" not in result
        assert "temperatura" not in result

    def test_detects_pm25_violation(self):
        # Rango plausible actualizado a 999 µg/m³ (episodios extremos Colombia).
        # Un sensor mal calibrado o error de digitación puede reportar 1500+.
        df = pd.DataFrame({"pm25": [10.0, 1500.0, 15.0]})  # 1500 > 999
        result = _check_ranges(df, PHYSICAL_RANGES)
        assert "pm25" in result
        assert result["pm25"]["n"] == 1
        assert result["pm25"]["pct"] == pytest.approx(100 / 3, rel=1e-2)

    def test_detects_ph_violation(self, dirty_df):
        result = _check_ranges(dirty_df, PHYSICAL_RANGES)
        assert "ph" in result
        assert result["ph"]["n"] == 1

    def test_custom_range_overrides(self):
        df = pd.DataFrame({"pm25": [10.0, 50.0, 100.0]})
        result = _check_ranges(df, {"pm25": (0.0, 40.0)})
        assert result["pm25"]["n"] == 2  # 50 y 100 fuera de rango


# ---------------------------------------------------------------------------
# _check_temporal
# ---------------------------------------------------------------------------

class TestCheckTemporal:
    def test_clean_dates(self, clean_df):
        result = _check_temporal(clean_df, "fecha")
        assert "fechas_invalidas" not in result
        assert "fechas_futuras" not in result

    def test_detects_future_dates(self, dirty_df):
        dirty_df["fecha"] = pd.to_datetime(dirty_df["fecha"], errors="coerce")
        result = _check_temporal(dirty_df, "fecha")
        assert result.get("fechas_futuras", 0) >= 1

    def test_reports_range(self, clean_df):
        result = _check_temporal(clean_df, "fecha")
        assert "fecha_inicio" in result
        assert "fecha_fin" in result
        assert result["n_periodos"] == 5


# ---------------------------------------------------------------------------
# validate (integración)
# ---------------------------------------------------------------------------

class TestValidate:
    def test_returns_report(self, clean_df):
        report = validate(clean_df, date_col="fecha")
        assert isinstance(report, ValidationReport)

    def test_clean_df_no_issues(self, clean_df):
        report = validate(clean_df, date_col="fecha", key_cols=["estacion", "fecha"])
        assert not report.has_issues()

    def test_dirty_df_has_issues(self, dirty_df):
        report = validate(dirty_df, date_col="fecha")
        assert report.has_issues()

    def test_summary_is_string(self, clean_df):
        report = validate(clean_df)
        assert isinstance(report.summary(), str)

    def test_high_missing_generates_warning(self):
        df = pd.DataFrame({"pm25": [1.0] + [None] * 9})
        report = validate(df)
        assert any("pm25" in w for w in report.warnings)
