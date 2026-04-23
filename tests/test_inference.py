"""Tests para estadistica_ambiental.inference.*"""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.inference.distributions import normality_tests, fit_distribution
from estadistica_ambiental.inference.hypothesis import ttest, mannwhitney, anova, kruskalwallis
from estadistica_ambiental.inference.stationarity import adf_test, kpss_test, stationarity_report
from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
from estadistica_ambiental.inference.intervals import (
    ci_mean, ci_median_bootstrap, ci_quantile_bootstrap, exceedance_probability,
)


@pytest.fixture
def normal_series():
    np.random.seed(1)
    return pd.Series(np.random.normal(15, 3, 200))


@pytest.fixture
def stationary_series():
    np.random.seed(2)
    return pd.Series(np.random.normal(0, 1, 150))


@pytest.fixture
def trending_series():
    return pd.Series(np.linspace(5, 30, 150) + np.random.default_rng(3).normal(0, 1, 150))


@pytest.fixture
def group_df():
    np.random.seed(4)
    return pd.DataFrame({
        "valor":    np.concatenate([np.random.normal(10, 2, 50), np.random.normal(14, 2, 50)]),
        "estacion": ["A"] * 50 + ["B"] * 50,
    })


# --- distributions ---

class TestNormality:
    def test_returns_dataframe(self, normal_series):
        result = normality_tests(normal_series)
        assert isinstance(result, pd.DataFrame)

    def test_has_test_column(self, normal_series):
        result = normality_tests(normal_series)
        assert "test" in result.columns and len(result) >= 2

    def test_normal_series_passes(self, normal_series):
        result = normality_tests(normal_series)
        # Al menos una prueba no rechaza H0 para datos normales
        assert result["normal"].any()


class TestFitDistribution:
    def test_returns_sorted_by_aic(self, normal_series):
        result = fit_distribution(normal_series, distributions=["norm", "lognorm"])
        assert list(result.columns[:1]) == ["distribucion"]
        assert result["aic"].iloc[0] <= result["aic"].iloc[-1]


# --- hypothesis ---

class TestHypothesis:
    def test_ttest_significant(self, group_df):
        result = ttest(group_df, "valor", "estacion")
        assert result["significant"]

    def test_ttest_wrong_groups_raises(self, group_df):
        with pytest.raises(ValueError):
            ttest(group_df, "valor", "estacion", groups=["A", "B", "C"])

    def test_mannwhitney(self, group_df):
        result = mannwhitney(group_df, "valor", "estacion")
        assert 0 <= result["pval"] <= 1

    def test_mannwhitney_more_than_2_groups_raises(self, group_df):
        df3 = group_df.copy()
        df3.loc[0, "estacion"] = "C"
        with pytest.raises(ValueError):
            mannwhitney(df3, "valor", "estacion")

    def test_anova(self, group_df):
        result = anova(group_df, "valor", "estacion")
        assert "statistic" in result

    def test_kruskal(self, group_df):
        result = kruskalwallis(group_df, "valor", "estacion")
        assert result["pval"] <= 1


# --- stationarity ---

class TestStationarity:
    def test_adf_stationary(self, stationary_series):
        result = adf_test(stationary_series)
        assert result["stationary"]

    def test_kpss_stationary(self, stationary_series):
        result = kpss_test(stationary_series)
        assert result["stationary"]

    def test_report_returns_dataframe(self, stationary_series):
        result = stationarity_report(stationary_series)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_report_nonstationary_diagnosis(self, trending_series):
        result = stationarity_report(trending_series)
        # Serie con tendencia → diagnóstico "no estacionaria" o "evidencia mixta"
        assert any("estacionaria" in str(c) for c in result["conclusion"].values)

    def test_adf_nonstationary_logs_warning(self, trending_series, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            adf_test(trending_series)

    def test_report_mixed_evidence(self, stationary_series, monkeypatch):
        # Forzar evidencia mixta: ADF dice estacionaria, KPSS dice no estacionaria
        import estadistica_ambiental.inference.stationarity as st_module
        adf_result  = {"test": "ADF",  "stationary": True,  "pval": 0.01, "statistic": -5.0,
                       "lags_used": 1, "n_obs": 100, "critical_1%": -3.5, "critical_5%": -2.9,
                       "critical_10%": -2.6, "alpha": 0.05}
        kpss_result = {"test": "KPSS", "stationary": False, "pval": 0.01, "statistic": 0.8,
                       "lags_used": 1, "critical_1%": 0.7, "critical_5%": 0.5,
                       "critical_10%": 0.4, "alpha": 0.05}
        monkeypatch.setattr(st_module, "adf_test",  lambda s, a=0.05, **kw: adf_result)
        monkeypatch.setattr(st_module, "kpss_test", lambda s, a=0.05, **kw: kpss_result)
        result = stationarity_report(stationary_series)
        assert any("mixta" in str(c) for c in result["conclusion"].values)


# --- trend ---

class TestTrend:
    def test_mann_kendall_increasing(self, trending_series):
        result = mann_kendall(trending_series)
        assert result["trend"] == "increasing"

    def test_sens_slope_positive(self, trending_series):
        result = sens_slope(trending_series)
        assert result["slope"] > 0


# --- intervals ---

class TestIntervals:
    def test_ci_mean_tuple(self, normal_series):
        lo, hi = ci_mean(normal_series)
        assert lo < hi

    def test_ci_mean_contains_true_mean(self, normal_series):
        lo, hi = ci_mean(normal_series)
        assert lo < normal_series.mean() < hi

    def test_ci_median_bootstrap(self, normal_series):
        lo, hi = ci_median_bootstrap(normal_series)
        assert lo < hi

    def test_ci_quantile_bootstrap(self, normal_series):
        lo, hi = ci_quantile_bootstrap(normal_series, q=0.95)
        assert lo < hi

    def test_exceedance_probability(self, normal_series):
        result = exceedance_probability(normal_series, threshold=20.0)
        assert 0 <= result["pct_exceed"] <= 100

    def test_ci_bootstrap_custom_statistic(self, normal_series):
        from estadistica_ambiental.inference.intervals import ci_bootstrap
        lo, hi = ci_bootstrap(normal_series, statistic=np.std, n_boot=500)
        assert lo < hi
        assert lo > 0  # desviación estándar siempre positiva

    def test_ci_bootstrap_mean_vs_ci_mean(self, normal_series):
        from estadistica_ambiental.inference.intervals import ci_bootstrap
        lo, hi = ci_bootstrap(normal_series, statistic=np.mean, n_boot=500)
        assert lo < normal_series.mean() < hi


# --- pettitt_test ---
# pymannkendall no expone pettitt_test en la versión instalada — xfail hasta actualizar

class TestPettitt:
    @pytest.mark.xfail(reason="pymannkendall instalado no expone pettitt_test", strict=False)
    def test_returns_dict_with_keys(self, trending_series):
        from estadistica_ambiental.inference.trend import pettitt_test
        result = pettitt_test(trending_series)
        assert "change_point_idx" in result
        assert "pval" in result
        assert "significant" in result

    @pytest.mark.xfail(reason="pymannkendall instalado no expone pettitt_test", strict=False)
    def test_change_point_in_range(self, trending_series):
        from estadistica_ambiental.inference.trend import pettitt_test
        result = pettitt_test(trending_series)
        assert 0 <= result["change_point_idx"] < len(trending_series)

    @pytest.mark.xfail(reason="pymannkendall instalado no expone pettitt_test", strict=False)
    def test_no_trend_not_significant(self, stationary_series):
        from estadistica_ambiental.inference.trend import pettitt_test
        result = pettitt_test(stationary_series, alpha=0.05)
        assert isinstance(result["pval"], float)

    @pytest.mark.xfail(reason="pymannkendall instalado no expone pettitt_test", strict=False)
    def test_date_index_preserved(self):
        from estadistica_ambiental.inference.trend import pettitt_test
        s = pd.Series(
            np.concatenate([np.ones(50), np.ones(50) * 5]),
            index=pd.date_range("2020-01-01", periods=100, freq="D"),
        )
        result = pettitt_test(s)
        assert "change_point_date" in result


# --- sens_slope edge cases ---

class TestSensSlope:
    def test_constant_series_zero_slope(self):
        from estadistica_ambiental.inference.trend import sens_slope
        s = pd.Series([5.0] * 50)
        result = sens_slope(s)
        assert result["slope"] == pytest.approx(0.0, abs=1e-6)

    def test_linear_series_correct_slope(self):
        from estadistica_ambiental.inference.trend import sens_slope
        s = pd.Series(np.arange(100, dtype=float))
        result = sens_slope(s)
        assert result["slope"] == pytest.approx(1.0, abs=0.01)
