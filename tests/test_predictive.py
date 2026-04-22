"""Tests para predictive/ml.py, registry.py y evaluation/backtesting.py"""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.predictive.ml import XGBoostModel, RandomForestModel
from estadistica_ambiental.predictive.registry import get_model, list_models, register
from estadistica_ambiental.predictive.classical import ARIMAModel
from estadistica_ambiental.evaluation.backtesting import walk_forward, compare_backtests


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


class TestRandomForest:
    def test_fit_predict(self, ts):
        model = RandomForestModel(lags=[1, 2, 3])
        model.fit(ts)
        preds = model.predict(4)
        assert len(preds) == 4


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
        from estadistica_ambiental.predictive.base import BaseModel
        import numpy as np

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
