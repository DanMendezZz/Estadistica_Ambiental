"""Tests para BayesianARIMA y HierarchicalModel.

Si pymc/arviz no están instalados, los tests se SALTAN con importorskip.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # sin ventana gráfica en CI/tests

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

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

# Para los tests "spec" (recuperación de phi, intervalos predictivos) damos un
# poco más de muestreo manteniendo el coste bajo control.
SAMPLES_SPEC = 200
TUNE_SPEC = 200


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


@pytest.fixture(autouse=True)
def _close_matplotlib_figures():
    """Cierra figuras de matplotlib también si el test falla a mitad de camino."""
    yield
    plt.close("all")


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
        assert "mu_group" in names
        assert "mu_global" in names

    def test_fit_without_groups_raises(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        with pytest.raises(ValueError, match="groups"):
            model.fit(panel_data["y"])

    def test_predict_before_fit_raises(self):
        model = HierarchicalModel()
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(3)


# ---------------------------------------------------------------------------
# Tests adicionales para la API "spec" (positional p,d,q + return_samples,
# group_estimates, posterior_predictive_interval, etc.)
# ---------------------------------------------------------------------------


@pytest.fixture
def ar1_strong():
    """Serie AR(1) con phi=0.7 grande para recuperar el coeficiente."""
    rng = np.random.default_rng(123)
    n = 200
    phi_true = 0.7
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = phi_true * y[t - 1] + rng.normal(0.0, 0.5)
    return pd.Series(y, index=pd.date_range("2020-01-01", periods=n, freq="ME"))


@pytest.fixture
def panel_long():
    """DataFrame largo con grupos y valor para HierarchicalModel(group_col=...).

    Pocas observaciones por grupo y noise relativamente grande para que el
    partial pooling jale las medias hacia el global de forma visible.
    """
    rng = np.random.default_rng(7)
    rows = []
    for est, offset in [("A", -1.5), ("B", 0.0), ("C", 1.5)]:
        for _ in range(8):
            rows.append({"estacion": est, "y": offset + rng.normal(0.0, 1.5)})
    return pd.DataFrame(rows)


@pytest.fixture
def panel_unbalanced():
    """Panel con tamaños de grupo desbalanceados."""
    rng = np.random.default_rng(9)
    rows = []
    for est, n in [("A", 5), ("B", 25), ("C", 60)]:
        offset = {"A": 1.0, "B": 0.0, "C": -1.0}[est]
        for _ in range(n):
            rows.append({"estacion": est, "y": offset + rng.normal(0.0, 0.4)})
    return pd.DataFrame(rows)


class TestBayesianARIMASpec:
    """Tests de la API 'spec': positional p,d,q + Series-by-default + intervalos."""

    def test_fits_and_predicts_synthetic_ar1(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES_SPEC, tune=TUNE_SPEC, chains=CHAINS)
        model.fit(ar1_strong)
        df = model.summary()
        # Buscar la fila de phi[0]
        phi_rows = [r for r in df.index if "phi" in str(r)]
        assert phi_rows, "No se encontró parámetro phi en summary"
        phi_mean = df.loc[phi_rows[0], "mean"]
        assert 0.5 <= phi_mean <= 0.9, f"phi posterior fuera de [0.5, 0.9]: {phi_mean}"

    def test_predict_returns_series_of_correct_length(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar1_strong)
        out = model.predict(horizon=8)
        assert isinstance(out, pd.Series)
        assert len(out) == 8

    def test_predict_with_return_samples_returns_ndarray(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar1_strong)
        arr = model.predict(horizon=4, return_samples=True)
        assert isinstance(arr, np.ndarray)
        assert arr.ndim == 2
        assert arr.shape[1] == 4
        assert arr.shape[0] > 0

    def test_summary_returns_dataframe_with_rhat(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar1_strong)
        df = model.summary()
        assert isinstance(df, pd.DataFrame)
        assert "r_hat" in df.columns
        assert "ess_bulk" in df.columns or "ess_mean" in df.columns

    def test_posterior_predictive_interval_columns(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar1_strong)
        ci = model.posterior_predictive_interval(horizon=5, hdi_prob=0.9)
        assert list(ci.columns) == ["mean", "lower", "upper"]
        assert len(ci) == 5
        assert (ci["lower"] <= ci["mean"]).all()
        assert (ci["mean"] <= ci["upper"]).all()

    def test_trace_attribute_is_set(self, ar1_strong):
        model = BayesianARIMA(1, 0, 0, samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar1_strong)
        assert hasattr(model, "trace_")
        assert model.trace_ is not None


class TestHierarchicalModelSpec:
    """Tests de la API 'spec': fit(df, value_col=...) + group_estimates + unbalanced."""

    def test_partial_pooling_pulls_extreme_groups_to_global_mean(self, panel_long):
        model = HierarchicalModel(
            group_col="estacion", samples=SAMPLES_SPEC, tune=TUNE_SPEC, chains=CHAINS
        )
        model.fit(panel_long, value_col="y")
        ge = model.group_estimates()
        sample_means = panel_long.groupby("estacion")["y"].mean().to_dict()
        global_mean = float(panel_long["y"].mean())

        # Para al menos uno de los grupos extremos el posterior debe quedar
        # estrictamente más cerca del global que la media muestral (shrinkage
        # observable). Con MCMC + pocas muestras no exigimos shrinkage en TODOS.
        shrinkages = []
        for est in ["A", "C"]:
            row = ge[ge["estacion"] == est].iloc[0]
            posterior_mean = float(row["mean"])
            sm = float(sample_means[est])
            dist_post = abs(posterior_mean - global_mean)
            dist_sample = abs(sm - global_mean)
            shrinkages.append(dist_sample - dist_post)
        assert max(shrinkages) > 0.0, (
            "Ningún grupo extremo fue jalado al global por el partial pooling: "
            f"shrinkages={shrinkages}"
        )

    def test_group_estimates_one_row_per_group(self, panel_long):
        model = HierarchicalModel(group_col="estacion", samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_long, value_col="y")
        ge = model.group_estimates()
        assert len(ge) == panel_long["estacion"].nunique()
        assert set(ge.columns) == {"estacion", "mean", "hdi_lower", "hdi_upper"}
        assert (ge["hdi_lower"] <= ge["mean"]).all()
        assert (ge["mean"] <= ge["hdi_upper"]).all()

    def test_handles_unbalanced_groups(self, panel_unbalanced):
        model = HierarchicalModel(group_col="estacion", samples=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_unbalanced, value_col="y")
        assert model.is_fitted
        ge = model.group_estimates()
        assert len(ge) == 3
        # No NaNs en estimaciones por grupo
        assert ge["mean"].notna().all()
        assert ge["hdi_lower"].notna().all()
        assert ge["hdi_upper"].notna().all()

    def test_fit_dataframe_value_col_inferred(self, panel_long):
        model = HierarchicalModel(group_col="estacion", samples=SAMPLES, tune=TUNE, chains=CHAINS)
        # Sin value_col explícito: debe inferir 'y' como única columna numérica.
        model.fit(panel_long)
        assert model.is_fitted
        assert set(model._stations) == {"A", "B", "C"}


class TestBayesianARIMAMoreBranches:
    """Ramas de fit()/_simulate_paths() no cubiertas por los tests de arriba."""

    def test_ma_component_q_gt_0(self, ar_series):
        model = BayesianARIMA(p=1, d=0, q=1, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        sims = model.predict(horizon=4, n_samples=20)
        assert sims.shape == (20, 4)
        assert np.isfinite(sims).all()

    def test_ar_order_zero(self, ar_series):
        # p=0: la rama `phi = None` en fit() y `phis = zeros` en _simulate_paths.
        model = BayesianARIMA(p=0, d=0, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        sims = model.predict(horizon=4, n_samples=20)
        assert sims.shape == (20, 4)
        assert np.isfinite(sims).all()

    def test_d_greater_than_one_undifferences_correctly(self, ar_series):
        y = ar_series.cumsum().cumsum()  # doblemente integrada, nivel final ~90-100
        model = BayesianARIMA(p=1, d=2, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(y)
        sims = model.predict(horizon=3, n_samples=20)
        assert sims.shape == (20, 3)
        assert np.isfinite(sims).all()
        # Si _simulate_paths se saltara el des-diferenciado (self.d>0), los sims
        # quedarían en la escala de la 2da diferencia (<1 en este fixture) en vez
        # de la escala del nivel de la serie (~90-100) -- shape/isfinite no lo detectan.
        assert np.abs(sims).mean() > 20.0

    def test_fit_samples_override(self, ar_series):
        model = BayesianARIMA(p=1, d=0, q=0, draws=1, tune=TUNE, chains=CHAINS)
        model.fit(ar_series, samples=SAMPLES)
        assert model.samples == SAMPLES
        assert model.draws == SAMPLES
        assert model._trace.posterior.sizes["draw"] == SAMPLES

    def test_series_too_short_raises_valueerror(self):
        y = pd.Series([1.0, 2.0, 3.0])
        model = BayesianARIMA(p=5, d=0, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        with pytest.raises(ValueError, match="demasiado corta"):
            model.fit(y)

    def test_non_datetime_index_skips_future_index(self):
        # La rama nueva es el `isinstance(..., DatetimeIndex)` de fit() (no
        # asigna _last_index/_freq); ese caso ya lo cubre test_bayesian_helpers.py
        # instanciando sin fit(), así que aquí solo se verifica el efecto tras
        # un fit() real: predict_interval cae al índice entero por defecto.
        rng = np.random.default_rng(0)
        y = pd.Series(rng.normal(size=50))  # RangeIndex, no datetime
        model = BayesianARIMA(p=1, d=0, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(y)
        ci = model.predict_interval(horizon=3)
        assert list(ci.index) == [0, 1, 2]  # índice entero por defecto, no fechas

    def test_plot_trace_smoke(self, ar_series):
        model = BayesianARIMA(p=1, d=0, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        axes = model.plot_trace()
        assert axes is not None

    def test_n_samples_greater_than_posterior_oversamples_with_replacement(self, ar_series):
        # Issue #38: antes, n_draw = min(n_samples, n_total) capaba el
        # resultado a n_total filas en silencio (con replace=False) cuando se
        # pedían más muestras que draws tiene el posterior, contradiciendo el
        # docstring de predict() (forma (n_samples, horizon) garantizada).
        # Con SAMPLES*CHAINS = 200 draws en el posterior, pedir 300 debe dar
        # 300 filas -- solo posible re-muestreando con reemplazo.
        model = BayesianARIMA(p=1, d=0, q=0, draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(ar_series)
        n_total = model._trace.posterior.sizes["chain"] * model._trace.posterior.sizes["draw"]
        assert n_total == SAMPLES * CHAINS
        sims = model.predict(horizon=3, n_samples=n_total + 100)
        assert sims.shape == (n_total + 100, 3)
        assert np.isfinite(sims).all()


class TestHierarchicalModelMoreBranches:
    """Ramas de fit()/group_estimates() no cubiertas por los tests de arriba."""

    def test_multiindex_group_level(self):
        rng = np.random.default_rng(2)
        values, idx_tuples = [], []
        for est, offset in [("A", 0.0), ("B", 1.0)]:
            for i in range(15):
                values.append(offset + rng.normal(0, 0.3))
                idx_tuples.append((est, i))
        idx = pd.MultiIndex.from_tuples(idx_tuples, names=["estacion", "obs"])
        y = pd.Series(values, index=idx)
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(y)
        assert model.is_fitted
        assert set(model._stations) == {"A", "B"}

    def test_dataframe_missing_group_col_raises(self, panel_data):
        model = HierarchicalModel(group_col="estacion", draws=SAMPLES, tune=TUNE, chains=CHAINS)
        df = panel_data.rename(columns={"estacion": "otra_columna"})
        with pytest.raises(ValueError, match="columna de grupo"):
            model.fit(df, value_col="y")

    def test_dataframe_no_numeric_value_col_raises(self, panel_data):
        model = HierarchicalModel(group_col="estacion", draws=SAMPLES, tune=TUNE, chains=CHAINS)
        df = panel_data.copy()
        df["y"] = df["y"].astype(str)  # ya no es numérica: vc no se puede inferir
        with pytest.raises(ValueError, match="value_col"):
            model.fit(df)

    def test_group_estimates_hdi_fallback(self, panel_data, monkeypatch):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)

        def _boom(*args, **kwargs):
            raise RuntimeError("az.hdi roto a propósito")

        monkeypatch.setattr(az, "hdi", _boom)
        ge = model.group_estimates()
        assert len(ge) == 3
        # Comparar contra el cálculo exacto del fallback (no solo "no-NaN" ni
        # "lower<=upper", que sobreviven igual si el fallback usa cuantiles
        # invertidos o si el monkeypatch no llegó a interceptar az.hdi).
        flat = model._trace.posterior["mu_group"].values.reshape(-1, len(model._stations))
        np.testing.assert_allclose(ge["hdi_lower"].values, np.quantile(flat, 0.025, axis=0))
        np.testing.assert_allclose(ge["hdi_upper"].values, np.quantile(flat, 0.975, axis=0))

    def test_plot_forest_smoke(self, panel_data):
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)
        ax = model.plot_forest()
        assert ax is not None

    def test_n_samples_greater_than_posterior_oversamples_with_replacement(self, panel_data):
        # Mismo bug/fix que en BayesianARIMA (issue #38), pero en el
        # `predict()` de HierarchicalModel: forma documentada
        # (n_samples, horizon, n_groups).
        model = HierarchicalModel(draws=SAMPLES, tune=TUNE, chains=CHAINS)
        model.fit(panel_data["y"], groups=panel_data["estacion"].values)
        n_total = model._trace.posterior.sizes["chain"] * model._trace.posterior.sizes["draw"]
        sims = model.predict(horizon=2, n_samples=n_total + 50)
        assert sims.shape == (n_total + 50, 2, 3)
        assert np.isfinite(sims).all()


class TestBayesianRegistry:
    def test_bayesian_arima_in_registry(self):
        from estadistica_ambiental.predictive.registry import list_models

        assert "bayesian_arima" in list_models()
        assert "hierarchical" in list_models()

    def test_get_bayesian_arima_via_registry(self):
        from estadistica_ambiental.predictive.registry import get_model

        m = get_model("bayesian_arima", p=1, d=0, q=0, samples=50, tune=50, chains=2)
        assert m.name == "BayesianARIMA"
        assert m.order == (1, 0, 0)


class TestImportErrorWhenPymcMissing:
    """Verifica que el módulo se importa aunque pymc no esté (ImportError diferido)."""

    def test_check_pymc_returns_modules_when_available(self):
        from estadistica_ambiental.predictive.bayesian import _check_pymc

        pm_mod, az_mod = _check_pymc()
        assert pm_mod is not None
        assert az_mod is not None
