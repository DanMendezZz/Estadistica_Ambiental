"""Tests para estadistica_ambiental.eda.viz."""

import matplotlib
matplotlib.use("Agg")  # sin ventana gráfica en CI/tests

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from estadistica_ambiental.eda.viz import (
    plot_series,
    plot_missing_heatmap,
    plot_histogram,
    plot_boxplot,
    plot_correlation_heatmap,
    plot_seasonal_means,
    plot_multi_series,
    plot_scatter,
)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def env_df():
    return pd.DataFrame({
        "fecha":      pd.date_range("2023-01-01", periods=60, freq="D"),
        "estacion":   (["Kennedy", "Usme"] * 30),
        "pm25":       [10 + i % 15 + (i % 3) * 0.5 for i in range(60)],
        "pm10":       [20 + i % 20 for i in range(60)],
        "temperatura": [14 + (i % 7) * 0.3 for i in range(60)],
    })


# ---------------------------------------------------------------------------
# plot_series
# ---------------------------------------------------------------------------

class TestPlotSeries:
    def test_returns_figure(self, env_df):
        fig = plot_series(env_df, "fecha", "pm25")
        assert isinstance(fig, plt.Figure)

    def test_with_group(self, env_df):
        fig = plot_series(env_df, "fecha", "pm25", group_col="estacion")
        assert isinstance(fig, plt.Figure)

    def test_custom_title(self, env_df):
        fig = plot_series(env_df, "fecha", "pm25", title="Mi título")
        assert fig.axes[0].get_title() == "Mi título"


# ---------------------------------------------------------------------------
# plot_missing_heatmap
# ---------------------------------------------------------------------------

class TestPlotMissingHeatmap:
    def test_returns_figure(self, env_df):
        fig = plot_missing_heatmap(env_df)
        assert isinstance(fig, plt.Figure)

    def test_with_missing_values(self, env_df):
        env_df.loc[[2, 5, 10], "pm25"] = None
        fig = plot_missing_heatmap(env_df, date_col="fecha")
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_histogram
# ---------------------------------------------------------------------------

class TestPlotHistogram:
    def test_returns_figure(self, env_df):
        fig = plot_histogram(env_df, "pm25")
        assert isinstance(fig, plt.Figure)

    def test_with_group(self, env_df):
        fig = plot_histogram(env_df, "pm25", group_col="estacion")
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_boxplot
# ---------------------------------------------------------------------------

class TestPlotBoxplot:
    def test_global(self, env_df):
        fig = plot_boxplot(env_df, "pm25")
        assert isinstance(fig, plt.Figure)

    def test_by_group(self, env_df):
        fig = plot_boxplot(env_df, "pm25", group_col="estacion")
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_correlation_heatmap
# ---------------------------------------------------------------------------

class TestPlotCorrelationHeatmap:
    def test_returns_figure(self, env_df):
        fig = plot_correlation_heatmap(env_df)
        assert isinstance(fig, plt.Figure)

    def test_spearman(self, env_df):
        fig = plot_correlation_heatmap(env_df, method="spearman")
        assert isinstance(fig, plt.Figure)

    def test_single_numeric_col_no_crash(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        fig = plot_correlation_heatmap(df)
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_seasonal_means
# ---------------------------------------------------------------------------

class TestPlotSeasonalMeans:
    def test_monthly(self, env_df):
        fig = plot_seasonal_means(env_df, "fecha", "pm25", period="month")
        assert isinstance(fig, plt.Figure)

    def test_weekday(self, env_df):
        fig = plot_seasonal_means(env_df, "fecha", "pm25", period="weekday")
        assert isinstance(fig, plt.Figure)

    def test_hour(self):
        df = pd.DataFrame({
            "fecha": pd.date_range("2023-01-01", periods=48, freq="h"),
            "pm25": range(48),
        })
        fig = plot_seasonal_means(df, "fecha", "pm25", period="hour")
        assert isinstance(fig, plt.Figure)

    def test_invalid_period_raises(self, env_df):
        with pytest.raises(ValueError):
            plot_seasonal_means(env_df, "fecha", "pm25", period="quincenal")


# ---------------------------------------------------------------------------
# plot_multi_series
# ---------------------------------------------------------------------------

class TestPlotMultiSeries:
    def test_returns_figure(self, env_df):
        fig = plot_multi_series(env_df, "fecha", ["pm25", "pm10", "temperatura"])
        assert isinstance(fig, plt.Figure)

    def test_single_col(self, env_df):
        fig = plot_multi_series(env_df, "fecha", ["pm25"])
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_scatter
# ---------------------------------------------------------------------------

class TestPlotScatter:
    def test_basic(self, env_df):
        fig = plot_scatter(env_df, "pm25", "pm10")
        assert isinstance(fig, plt.Figure)

    def test_with_color_col(self, env_df):
        fig = plot_scatter(env_df, "pm25", "pm10", color_col="estacion")
        assert isinstance(fig, plt.Figure)
