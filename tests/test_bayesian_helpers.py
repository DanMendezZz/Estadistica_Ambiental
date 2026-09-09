"""Tests para bayesian.py que NO requieren pymc instalado (issue #11).

``test_bayesian.py`` salta todo el archivo con ``pytest.importorskip("pymc")``
si no está instalado — el job de CI que sube a Codecov (``ci.yml`` JOB 2)
instala solo ``[dev]``, sin pymc, así que ninguno de esos tests cuenta para
la cobertura reportada. Este archivo cubre lo que SÍ es ejercitable sin pymc
en tiempo de ejecución: los helpers puros de diferenciación, la rama de
import fallido, y los alias de constructor.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

from estadistica_ambiental.predictive.bayesian import (
    BayesianARIMA,
    HierarchicalModel,
    _check_pymc,
    _difference,
    _try_import_pymc,
    _undifference,
)

# ---------------------------------------------------------------------------
# _difference
# ---------------------------------------------------------------------------


class TestDifference:
    def test_d0_returns_copy_not_view(self):
        y = np.array([1.0, 2.0, 3.0])
        out = _difference(y, 0)
        assert np.array_equal(out, y)
        out[0] = 99.0
        assert y[0] == 1.0  # no debe mutar el array original

    def test_d1_matches_np_diff(self):
        y = np.array([1.0, 3.0, 6.0, 10.0])
        assert np.array_equal(_difference(y, 1), np.diff(y))

    def test_d2_applies_twice(self):
        y = np.array([1.0, 3.0, 6.0, 10.0, 15.0])
        assert np.array_equal(_difference(y, 2), np.diff(np.diff(y)))


# ---------------------------------------------------------------------------
# _undifference
# ---------------------------------------------------------------------------


class TestUndifference:
    def test_d0_returns_input_unchanged(self):
        forecast = np.array([5.0, 6.0])
        out = _undifference(forecast, np.array([1.0, 2.0, 3.0]), 0)
        assert np.array_equal(out, forecast)

    def test_d1_roundtrip_recovers_tail(self):
        # "Pronosticar" exactamente los deltas ya observados debe reconstruir
        # la cola real de la serie original.
        y = np.array([1.0, 3.0, 6.0, 10.0, 15.0])
        horizon = 2
        forecast_diff = _difference(y, 1)[-horizon:]
        recovered = _undifference(forecast_diff, y[:-horizon], 1)
        assert np.allclose(recovered, y[-horizon:])

    def test_d2_roundtrip_recovers_tail(self):
        # Cúbicos, no números triangulares: la 2da diferencia de una cuadrática
        # es constante y un mutante que invierte el orden del pronóstico pasaría
        # igual de todas formas. Con cúbicos la 2da diferencia varía de verdad.
        y = np.array([1.0, 2.0, 8.0, 27.0, 64.0, 125.0, 216.0])
        horizon = 2
        forecast_diff = _difference(y, 2)[-horizon:]
        recovered = _undifference(forecast_diff, y[:-horizon], 2)
        assert np.allclose(recovered, y[-horizon:])


# ---------------------------------------------------------------------------
# _try_import_pymc / _check_pymc
# ---------------------------------------------------------------------------


class TestPymcImportMissing:
    def test_try_import_returns_none_none_when_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pymc", None)
        monkeypatch.setitem(sys.modules, "arviz", None)
        pm, az = _try_import_pymc()
        assert pm is None
        assert az is None

    def test_check_pymc_raises_importerror_when_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pymc", None)
        monkeypatch.setitem(sys.modules, "arviz", None)
        with pytest.raises(ImportError, match="PyMC y ArviZ"):
            _check_pymc()


# ---------------------------------------------------------------------------
# Alias de constructor (order=/draws=/random_seed=) — no requieren pymc,
# la instanciación no llama _check_pymc().
# ---------------------------------------------------------------------------


class TestBayesianARIMAConstructorAliases:
    def test_order_alias_overrides_positional_pdq(self):
        model = BayesianARIMA(p=9, d=9, q=9, order=(1, 2, 3))
        assert model.order == (1, 2, 3)
        assert (model.p, model.d, model.q) == (1, 2, 3)

    def test_draws_alias_overrides_samples(self):
        model = BayesianARIMA(samples=1, draws=77)
        assert model.samples == 77
        assert model.draws == 77

    def test_random_seed_alias_overrides_seed(self):
        model = BayesianARIMA(seed=1, random_seed=99)
        assert model.seed == 99
        assert model.random_seed == 99


class TestHierarchicalModelConstructorAliases:
    def test_draws_alias_overrides_samples(self):
        model = HierarchicalModel(samples=1, draws=77)
        assert model.samples == 77
        assert model.draws == 77

    def test_random_seed_alias_overrides_seed(self):
        model = HierarchicalModel(seed=1, random_seed=99)
        assert model.seed == 99
        assert model.random_seed == 99


# ---------------------------------------------------------------------------
# Guardas "llamar antes de fit()" — no requieren pymc: el RuntimeError se
# lanza antes de tocar self._trace/_check_pymc(). test_bayesian.py ya prueba
# 3 de estas pero quedan detrás de su importorskip de módulo, así que no
# cuentan para la cobertura del job sin pymc.
# ---------------------------------------------------------------------------


class TestBayesianARIMAGuardsSinFit:
    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            BayesianARIMA().predict(3)

    def test_summary_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            BayesianARIMA().summary()

    def test_plot_trace_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            BayesianARIMA().plot_trace()

    def test_future_index_without_fit_returns_none(self):
        # self._last_index es None hasta que fit() lo asigna.
        assert BayesianARIMA()._future_index(5) is None


class TestHierarchicalModelGuardsSinFit:
    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            HierarchicalModel().predict(3)

    def test_summary_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            HierarchicalModel().summary()

    def test_group_estimates_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            HierarchicalModel().group_estimates()

    def test_plot_forest_before_fit_raises(self):
        with pytest.raises(RuntimeError, match="fit"):
            HierarchicalModel().plot_forest()
