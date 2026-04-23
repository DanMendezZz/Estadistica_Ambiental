"""Tests para predictive/ml.py, registry.py y evaluation/backtesting.py"""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.evaluation.backtesting import compare_backtests, walk_forward
from estadistica_ambiental.predictive.classical import ARIMAModel
from estadistica_ambiental.predictive.ml import RandomForestModel, XGBoostModel
from estadistica_ambiental.predictive.registry import get_model, list_models, register


@pytest.fixture
def ts():
    np.random.seed(42)
    return pd.Series(
        10 + np.cumsum(np.random.normal(0, 0.5, 80)),
        index=pd.date_range("2017-01-01", periods=80, freq="ME"),
    )


# --- ML models ---

class TestXGBoost:
    def test_fit_predict(self, ts):
        model = XGBoostModel(lags=[1, 2, 3])
        model.fit(ts)
        preds = model.predict(6)
        assert len(preds) == 6
        assert not np.any(np.isnan(preds))

    def test_is_fitted(self, ts):
        model = XGBoostModel(lags=[1, 2, 3])
        assert not model.is_fitted
        model.fit(ts)
        assert model.is_fitted


class TestXGBoostWithExog:
    def test_fit_with_exogenous(self, ts):
        X = pd.DataFrame({"temp": np.random.default_rng(1).normal(15, 3, len(ts))},
                         index=ts.index)
        model = XGBoostModel(lags=[1, 2, 3])
        model.fit(ts, X=X)
        assert model.is_fitted

    def test_predict_before_fit_raises(self):
        model = XGBoostModel(lags=[1, 2])
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(3)

    def test_predict_with_x_future(self, ts):
        X = pd.DataFrame({"temp": np.random.default_rng(2).normal(15, 3, len(ts))},
                         index=ts.index)
        X_future = pd.DataFrame({"temp": np.random.default_rng(3).normal(15, 3, 4)})
        model = XGBoostModel(lags=[1, 2, 3])
        model.fit(ts, X=X)
        preds = model.predict(4, X_future=X_future)
        assert len(preds) == 4


class TestRandomForest:
    def test_fit_predict(self, ts):
        model = RandomForestModel(lags=[1, 2, 3])
        model.fit(ts)
        preds = model.predict(4)
        assert len(preds) == 4

    def test_fit_with_exogenous(self, ts):
        X = pd.DataFrame({"feat": np.random.default_rng(5).normal(0, 1, len(ts))},
                         index=ts.index)
        X_future = pd.DataFrame({"feat": np.random.default_rng(6).normal(0, 1, 3)})
        model = RandomForestModel(lags=[1, 2, 3])
        model.fit(ts, X=X)
        preds = model.predict(3, X_future=X_future)
        assert len(preds) == 3


# --- registry ---

class TestRegistry:
    def test_list_models(self):
        models = list_models()
        assert "arima" in models
        assert "xgboost" in models
        assert "random_forest" in models

    def test_get_model_arima(self):
        model = get_model("arima")
        assert model.name == "ARIMA"

    def test_get_model_unknown_raises(self):
        with pytest.raises(ValueError, match="no registrado"):
            get_model("modelo_fantasma")

    def test_register_custom(self):
        import numpy as np

        from estadistica_ambiental.predictive.base import BaseModel

        class NaiveModel(BaseModel):
            name = "Naive"
            def fit(self, y, X=None):
                self._last = float(y.iloc[-1])
                self._fitted = True
                return self
            def predict(self, horizon, X_future=None):
                return np.full(horizon, self._last)

        register("naive", NaiveModel)
        model = get_model("naive")
        assert model.name == "Naive"


# --- BaseModel helpers ---

class TestBaseModelHelpers:
    def _make_naive(self, ts):
        from estadistica_ambiental.predictive.base import BaseModel

        class NaiveModel(BaseModel):
            name = "NaiveHelper"
            def fit(self, y, X=None):
                self._last = float(y.iloc[-1])
                self._fitted = True
                return self
            def predict(self, horizon, X_future=None):
                return np.full(horizon, self._last)

        return NaiveModel()

    def test_fit_predict_combined(self, ts):
        model = self._make_naive(ts)
        preds = model.fit_predict(ts, horizon=5)
        assert len(preds) == 5

    def test_get_params_returns_dict(self, ts):
        model = self._make_naive(ts)
        params = model.get_params()
        assert isinstance(params, dict)

    def test_repr_contains_name(self, ts):
        model = self._make_naive(ts)
        assert "NaiveHelper" in repr(model)

    def test_optimization_result_penalty_sets_fallback(self):
        from estadistica_ambiental.predictive.base import OPTIMIZER_PENALTY, OptimizationResult
        r = OptimizationResult(best_params={}, best_score=OPTIMIZER_PENALTY, n_trials=0)
        assert r.fallback is True


# --- backtesting ---

class TestBacktesting:
    def test_walk_forward_returns_dict(self, ts):
        model = ARIMAModel(order=(1, 1, 0))
        result = walk_forward(model, ts, horizon=3, n_splits=3)
        assert "metrics" in result and "folds" in result

    def test_metrics_populated(self, ts):
        model = ARIMAModel(order=(1, 1, 0))
        result = walk_forward(model, ts, horizon=3, n_splits=3)
        assert "mae" in result["metrics"]
        assert "rmse" in result["metrics"]

    def test_compare_backtests(self, ts):
        results = {
            "arima": walk_forward(ARIMAModel(order=(1, 1, 0)), ts, horizon=3, n_splits=3),
            "rf":    walk_forward(RandomForestModel(lags=[1, 2, 3]), ts, horizon=3, n_splits=3),
        }
        df = compare_backtests(results)
        assert "rmse" in df.columns
        assert len(df) == 2

    def test_sliding_window_strategy(self, ts):
        model = RandomForestModel(lags=[1, 2, 3])
        result = walk_forward(model, ts, horizon=3, n_splits=3, strategy="sliding")
        assert "metrics" in result

    def test_no_folds_returns_empty(self, ts):
        # n_splits muy alto para serie corta → algunos folds fallarán
        model = RandomForestModel(lags=[1, 2, 3])
        # Serie muy corta para forzar empty folds
        tiny_ts = ts.iloc[:10]
        result = walk_forward(model, tiny_ts, horizon=50, n_splits=1)
        # Puede que no haya folds válidos o que devuelva resultado vacío
        assert isinstance(result, dict)

    def test_fold_exception_handled(self, ts):
        # Un modelo que siempre falla → walk_forward captura excepción y continúa
        from estadistica_ambiental.predictive.base import BaseModel

        class AlwaysFailModel(BaseModel):
            name = "Failing"
            def fit(self, y, X=None):
                raise RuntimeError("fallo intencional")
            def predict(self, horizon, X_future=None):
                return np.zeros(horizon)

        model = AlwaysFailModel()
        result = walk_forward(model, ts, horizon=3, n_splits=2)
        # Todos los folds fallan → resultado vacío sin crash
        assert isinstance(result, dict)
