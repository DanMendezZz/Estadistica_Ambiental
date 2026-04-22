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
