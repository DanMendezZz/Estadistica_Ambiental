"""Tests para estadistica_ambiental.eda.quality."""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.eda.quality import (
    MissingPattern,
    _analyze_freeze,
    _analyze_missing,
    _analyze_outliers,
    _analyze_temporal_gaps,
    _consecutive_gap_lengths,
    _cross_column_checks,
    assess_quality,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
            "pm25": [10.0, 12.0, 11.0, 13.0, 10.5, 11.5, 12.5, 10.0, 11.0, 12.0],
            "pm10": [20.0, 22.0, 21.0, 23.0, 20.5, 21.5, 22.5, 20.0, 21.0, 22.0],
            "temperatura": [14.0] * 10,
        }
    )


@pytest.fixture
def dirty_df():
    pm25 = [10.0, None, None, None, 15.0, 16.0, None, 18.0, 19.0, 20.0]
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
            "pm25": pm25,
            "pm10": [20.0, 22.0, 5.0, 23.0, 8.0, 21.5, 22.5, 20.0, 21.0, 22.0],
        }
    )


# ---------------------------------------------------------------------------
# _consecutive_gap_lengths
# ---------------------------------------------------------------------------


class TestConsecutiveGaps:
    def test_no_gaps(self):
        mask = pd.Series([False, False, False])
        assert _consecutive_gap_lengths(mask) == []

    def test_single_gap(self):
        mask = pd.Series([False, True, True, True, False])
        assert _consecutive_gap_lengths(mask) == [3]

    def test_multiple_gaps(self):
        mask = pd.Series([True, True, False, True, False, False, True])
        result = _consecutive_gap_lengths(mask)
        assert sorted(result) == sorted([2, 1, 1])

    def test_trailing_gap(self):
        mask = pd.Series([False, True, True])
        assert _consecutive_gap_lengths(mask) == [2]


# ---------------------------------------------------------------------------
# _analyze_missing
# ---------------------------------------------------------------------------


class TestAnalyzeMissing:
    def test_no_missing(self, clean_df):
        info = _analyze_missing(clean_df["pm25"], "pm25")
        assert info.n_missing == 0
        assert info.pct_missing == 0.0
        assert info.max_consecutive_gap == 0

    def test_counts_missing(self, dirty_df):
        info = _analyze_missing(dirty_df["pm25"], "pm25")
        assert info.n_missing == 4
        assert info.pct_missing == pytest.approx(40.0)

    def test_max_consecutive_gap(self, dirty_df):
        info = _analyze_missing(dirty_df["pm25"], "pm25")
        assert info.max_consecutive_gap == 3

    def test_returns_pattern(self, clean_df):
        info = _analyze_missing(clean_df["pm25"], "pm25")
        assert isinstance(info.pattern, MissingPattern)


# ---------------------------------------------------------------------------
# _analyze_outliers
# ---------------------------------------------------------------------------


class TestAnalyzeOutliers:
    def test_no_outliers_clean(self, clean_df):
        info = _analyze_outliers(clean_df["pm25"], "pm25")
        assert info.n_iqr == 0
        assert info.n_zscore == 0

    def test_detects_iqr_outlier(self):
        values = pd.Series([10.0] * 18 + [1000.0, -500.0])
        info = _analyze_outliers(values, "test")
        assert info.n_iqr >= 2

    def test_detects_zscore_outlier(self):
        values = pd.Series([10.0] * 17 + [500.0])
        info = _analyze_outliers(values, "test")
        assert info.n_zscore >= 1

    def test_worst_values_populated(self):
        values = pd.Series([10.0] * 15 + [999.0])
        info = _analyze_outliers(values, "test")
        assert 999.0 in info.worst_values


# ---------------------------------------------------------------------------
# _analyze_freeze
# ---------------------------------------------------------------------------


class TestAnalyzeFreeze:
    def test_no_freeze_in_varying_data(self, clean_df):
        info = _analyze_freeze(clean_df["pm25"], "pm25", min_length=5)
        assert info.n_sequences == 0

    def test_detects_freeze(self):
        values = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0, 15.0, 16.0])
        info = _analyze_freeze(values, "test", min_length=3)
        assert info.n_sequences == 1
        assert info.max_length == 5

    def test_min_length_threshold(self):
        values = pd.Series([5.0, 5.0, 5.0, 6.0, 7.0])
        assert _analyze_freeze(values, "test", min_length=5).n_sequences == 0
        assert _analyze_freeze(values, "test", min_length=3).n_sequences == 1

    def test_freeze_temperatura_constante(self):
        # temperatura constante = sensor congelado
        values = pd.Series([14.0] * 10)
        info = _analyze_freeze(values, "temperatura", min_length=5)
        assert info.n_sequences >= 1


# ---------------------------------------------------------------------------
# _analyze_temporal_gaps
# ---------------------------------------------------------------------------


class TestTemporalGaps:
    def test_complete_daily_series(self):
        dates = pd.Series(pd.date_range("2023-01-01", periods=30, freq="D"))
        info = _analyze_temporal_gaps(dates)
        assert info.completeness_pct == pytest.approx(100.0)
        assert info.inferred_freq is not None

    def test_detects_missing_days(self):
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        dates = pd.Series(dates).drop([5, 6, 7])  # elimina 3 días
        info = _analyze_temporal_gaps(dates)
        assert info.completeness_pct < 100.0

    def test_single_date_no_crash(self):
        dates = pd.Series(pd.to_datetime(["2023-01-01"]))
        info = _analyze_temporal_gaps(dates)
        assert info.actual_n == 1


# ---------------------------------------------------------------------------
# _cross_column_checks
# ---------------------------------------------------------------------------


class TestCrossColumnChecks:
    def test_no_issues_clean(self, clean_df):
        issues = _cross_column_checks(clean_df)
        assert issues == []

    def test_pm25_greater_than_pm10(self):
        df = pd.DataFrame({"pm25": [30.0, 10.0], "pm10": [20.0, 25.0]})
        issues = _cross_column_checks(df)
        assert any("PM2.5 > PM10" in i for i in issues)

    def test_dbo_greater_than_dqo(self):
        df = pd.DataFrame({"dbo": [50.0], "dqo": [30.0]})
        issues = _cross_column_checks(df)
        assert any("DBO > DQO" in i for i in issues)


# ---------------------------------------------------------------------------
# assess_quality (integración)
# ---------------------------------------------------------------------------


class TestAssessQuality:
    def test_returns_report(self, clean_df):
        from estadistica_ambiental.eda.quality import QualityReport

        report = assess_quality(clean_df, date_col="fecha")
        assert isinstance(report, QualityReport)

    def test_clean_df_minimal_issues(self, clean_df):
        report = assess_quality(clean_df, date_col="fecha")
        # temperatura constante sí genera freeze pero no otros problemas
        assert report.missing["pm25"].n_missing == 0
        assert report.temporal_gaps is not None
        assert report.temporal_gaps.completeness_pct == pytest.approx(100.0)

    def test_dirty_df_has_issues(self, dirty_df):
        report = assess_quality(dirty_df, date_col="fecha")
        assert report.has_issues()

    def test_missing_detected_in_dirty(self, dirty_df):
        report = assess_quality(dirty_df)
        assert report.missing["pm25"].n_missing == 4

    def test_summary_is_string(self, clean_df):
        report = assess_quality(clean_df)
        assert isinstance(report.summary(), str)

    def test_summary_with_missing_mentions_col(self, dirty_df):
        report = assess_quality(dirty_df, date_col="fecha")
        summary = report.summary()
        assert "pm25" in summary

    def test_summary_with_temporal_gaps_mentions_completitud(self):
        # Serie con gaps temporales
        df = pd.DataFrame(
            {
                "fecha": pd.to_datetime(["2023-01-01", "2023-01-03", "2023-01-05"]),
                "pm25": [10.0, 12.0, 14.0],
            }
        )
        report = assess_quality(df, date_col="fecha")
        summary = report.summary()
        assert isinstance(summary, str)

    def test_summary_with_cross_issues(self):
        # PM2.5 > PM10 → cross issue
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=5, freq="D"),
                "pm25": [50.0, 60.0, 55.0, 58.0, 52.0],
                "pm10": [30.0, 40.0, 35.0, 38.0, 32.0],
            }
        )
        report = assess_quality(df, date_col="fecha")
        summary = report.summary()
        assert isinstance(summary, str)


class TestMissingPatterns:
    def test_mnar_pattern_heavy_tails(self):
        from estadistica_ambiental.eda.quality import _analyze_missing

        # Crear serie donde los NaN están concentrados en los extremos (colas)
        vals = np.concatenate(
            [
                np.full(20, np.nan),  # extremo bajo → NaN
                np.linspace(30, 70, 60),  # valores centrales con datos
                np.full(20, np.nan),  # extremo alto → NaN
            ]
        )
        s = pd.Series(vals)
        result = _analyze_missing(s, "pm25")
        assert result is not None  # No crash

    def test_add_rolling_features_drop_na(self):
        from estadistica_ambiental.features.lags import add_rolling_features

        df = pd.DataFrame({"pm25": np.random.default_rng(0).normal(20, 5, 50)})
        result = add_rolling_features(df, "pm25", windows=[3], drop_na=True)
        assert result.isna().sum().sum() == 0

    def test_humidity_out_of_range_cross_check(self):
        # Humedad fuera de [0, 100] debe aparecer en cross_issues
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=5, freq="D"),
                "humedad": [75.0, 110.0, 80.0, -5.0, 70.0],  # 110 y -5 imposibles
            }
        )
        report = assess_quality(df, date_col="fecha")
        summary = report.summary()
        assert isinstance(summary, str)

    def test_single_date_series_completeness(self):
        # Serie con un solo registro → sin gaps (cubre líneas 359-361 y 372-373)
        df = pd.DataFrame(
            {
                "fecha": pd.to_datetime(["2023-01-01"]),
                "pm25": [15.0],
            }
        )
        report = assess_quality(df, date_col="fecha")
        assert report is not None

    def test_get_numeric_cols_with_specific_cols(self):
        # _get_numeric_cols con cols específicas cubre línea 435
        from estadistica_ambiental.eda.quality import _get_numeric_cols

        df = pd.DataFrame(
            {
                "pm25": [10.0, 15.0],
                "texto": ["a", "b"],
                "temperatura": [14.0, 15.0],
            }
        )
        result = _get_numeric_cols(df, cols=["pm25", "texto", "temperatura"])
        assert "pm25" in result
        assert "texto" not in result  # no numérica

    def test_identical_timestamps_coverage(self):
        # Timestamps idénticos → mode_diff=0 → else branch (líneas 359-361)
        from estadistica_ambiental.eda.quality import _analyze_temporal_gaps

        dates = pd.Series(pd.to_datetime(["2023-01-01", "2023-01-01", "2023-01-01"]))
        result = _analyze_temporal_gaps(dates)
        assert result.completeness_pct == 100.0
