"""Tests para BayesianARIMA y HierarchicalModel.

Si pymc/arviz no están instalados, los tests se SALTAN con importorskip.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pm = pytest.importorskip("pymc")
az = pytest.importorskip("arviz")

from estadistica_ambiental.predictive.bayesian import (  # noqa: E402
    BayesianARIMA,
    HierarchicalModel,
)

# Sample sizes muy pequeños para que la suite sea rápida
SAMPLES = 100
TUNE = 100
CHAINS = 2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ar_series() -> pd.Series:
    rng = np.random.default_rng(0)
    n = 80
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = 0.6 * y[t - 1] + rng.normal(0, 0.5)
    return pd.Series(y, index=pd.date_range("2020-01-01", periods=n, freq="ME"))


@pytest.fixture
def panel_data() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    rows = []
    for est in ["A", "B", "C"]:
        offset = {"A": 0.0, "B": 1.5, "C": -1.0}[est]
        for _ in range(40):
            rows.append({"estacion": est, "y": offset + rng.normal(0, 0.3)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# BayesianARIMA
# ---------------------------------------------------------------------------


class TestBayesianARIMA:
    def test_fit_returns_self(self, ar_series):
        model = BayesianARIMA(order=(1, 0, 0), draws=SAMPLES, tune=TUNE, chains=CHAINS)
        out = model.fit(ar_series)
        assert out is model
        assert model.is_fitted

    def test_predict_shape(self, ar_series):
        model = BayesianARIMA(order=(1, 0, 0), draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        sims = model.predict(horizon=6, n_samples=50)
        assert sims.shape == (50, 6)
        assert np.isfinite(sims).all()

    def test_summary_dataframe(self, ar_series):
        model = BayesianARIMA(order=(1, 0, 0), draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        df = model.summary()
        assert isinstance(df, pd.DataFrame)
        for col in ("mean", "hdi_3%", "hdi_97%"):
            assert col in df.columns
        # Debe contener al menos los parámetros del modelo
        names = " ".join(df.index.astype(str).tolist())
        assert "phi" in names
        assert "sigma" in names

    def test_predict_interval_columns(self, ar_series):
        model = BayesianARIMA(order=(1, 0, 0), draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        ci = model.predict_interval(horizon=4, credible_interval=0.9)
        assert list(ci.columns) == ["mean", "lower", "upper"]
        assert len(ci) == 4
        assert (ci["lower"] <= ci["upper"]).all()

    def test_predict_before_fit_raises(self):
        model = BayesianARIMA(order=(1, 0, 0))
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(3)

    def test_summary_before_fit_raises(self):
        model = BayesianARIMA(order=(1, 0, 0))
        with pytest.raises(RuntimeError, match="fit"):
            model.summary()

    def test_with_differencing(self, ar_series):
        # serie integrada
        y = ar_series.cumsum()
        model = BayesianARIMA(order=(1, 1, 0), draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(y)
        sims = model.predict(horizon=3, n_samples=20)
        assert sims.shape == (20, 3)
        assert np.isfinite(sims).all()


# ---------------------------------------------------------------------------
# HierarchicalModel
# ---------------------------------------------------------------------------


class TestHierarchicalModel:
    def test_fit_with_groups(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)
        assert model.is_fitted

    def test_fit_with_X_estacion(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], X=panel_data[["estacion"]])
        assert model.is_fitted
        assert set(model._stations) == {"A", "B", "C"}

    def test_predict_shape(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)
        sims = model.predict(horizon=5, n_samples=40)
        # (n_samples, horizon, n_groups)
        assert sims.shape == (40, 5, 3)
        assert np.isfinite(sims).all()

    def test_summary_dataframe(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)
        df = model.summary()
        assert isinstance(df, pd.DataFrame)
        for col in ("mean", "hdi_3%", "hdi_97%"):
            assert col in df.columns
        names = " ".join(df.index.astype(str).tolist())
        assert "alpha" in names
        assert "mu" in names

    def test_fit_without_groups_raises(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        with pytest.raises(ValueError, match="groups"):
            model.fit(panel_data["y"])

    def test_predict_before_fit_raises(self):
        model = HierarchicalModel()
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(3)
