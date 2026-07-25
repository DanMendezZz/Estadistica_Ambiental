"""Smoke tests para predictive/deep.py — protocolo BaseModel + ModelSpec.

Todos los tests requieren PyTorch (``importorskip``). Se enfocan en verificar
la firma del contrato y la integración con :func:`walk_forward`, sin
entrenamientos reales largos (epochs=1, series cortas).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from estadistica_ambiental.evaluation.backtesting import walk_forward  # noqa: E402
from estadistica_ambiental.predictive.base import BaseModel, ModelSpec  # noqa: E402
from estadistica_ambiental.predictive.deep import BiLSTMModel, GRUModel, LSTMModel  # noqa: E402
from estadistica_ambiental.predictive.registry import get_model, list_models  # noqa: E402


@pytest.fixture
def ts():
    rng = np.random.default_rng(42)
    return pd.Series(
        10 + np.cumsum(rng.normal(0, 0.5, 80)),
        index=pd.date_range("2017-01-01", periods=80, freq="ME"),
    )


@pytest.mark.parametrize("cls", [LSTMModel, BiLSTMModel, GRUModel])
class TestDeepProtocol:
    def test_is_basemodel_subclass(self, cls):
        assert issubclass(cls, BaseModel)

    def test_satisfies_model_spec(self, cls):
        # Protocol estructural: solo necesita los miembros, no la herencia.
        instance = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        assert isinstance(instance, ModelSpec)

    def test_warm_starts_returns_list(self, cls):
        instance = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        ws = instance.warm_starts
        assert isinstance(ws, list) and len(ws) >= 1
        assert all(isinstance(d, dict) for d in ws)

    def test_search_space_has_keys(self, cls):
        instance = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        ss = instance.search_space
        assert "lookback" in ss and "hidden_size" in ss

    def test_build_model_returns_same_class(self, cls):
        instance = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        built = instance.build_model({"lookback": 8, "hidden_size": 16, "n_layers": 1})
        assert isinstance(built, cls)
        assert built.lookback == 8
        assert built.hidden_size == 16


@pytest.mark.parametrize("cls", [LSTMModel, BiLSTMModel, GRUModel])
class TestDeepFitPredict:
    def test_fit_predict_smoke(self, cls, ts):
        model = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        assert not model.is_fitted
        model.fit(ts)
        assert model.is_fitted
        preds = model.predict(4)
        assert preds.shape == (4,)
        assert not np.any(np.isnan(preds))

    def test_predict_before_fit_raises(self, cls):
        model = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(3)

    def test_summary_returns_dict(self, cls, ts):
        model = cls(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        s = model.summary()
        assert isinstance(s, dict)
        assert s["fitted"] is False
        assert s["name"] == cls.name
        model.fit(ts)
        assert model.summary()["fitted"] is True


class TestDeepRegistry:
    def test_registered_keys(self):
        models = list_models()
        assert "lstm" in models
        assert "gru" in models
        assert "bilstm" in models

    def test_get_model_lstm(self):
        m = get_model("lstm", lookback=6, hidden_size=8, n_layers=1, epochs=1)
        assert isinstance(m, LSTMModel)


class TestDeepWalkForward:
    def test_walk_forward_lstm(self, ts):
        # Smoke: pocos folds, lookback corto, epochs=1
        model = LSTMModel(lookback=6, hidden_size=8, n_layers=1, epochs=1)
        result = walk_forward(model, ts, horizon=3, n_splits=2)
        assert "metrics" in result
        assert "folds" in result
        # Al menos un fold válido o estructura bien formada
        assert isinstance(result["folds"], (list, pd.DataFrame))
