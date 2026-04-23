"""Modelos de Machine Learning: XGBoost, Random Forest, LightGBM, SVR.

Todos usan features de lags internamente (feature engineering mínimo).
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


def _make_lag_features(series: np.ndarray, lags: List[int]) -> pd.DataFrame:
    s = pd.Series(series)
    features = {f"lag_{l}": s.shift(l) for l in lags}
    return pd.DataFrame(features).dropna()


class _SklearnModel(BaseModel):
    """Mixin para modelos sklearn con lag features."""

    name = "_SklearnBase"
    _lags: List[int] = [1, 2, 3, 6, 12]

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "_SklearnModel":
        feats = _make_lag_features(y.values, self._lags)
        target = pd.Series(y.values[max(self._lags):], name="y")
        if X is not None:
            exog = X.iloc[max(self._lags):].reset_index(drop=True)
            feats = pd.concat([feats.reset_index(drop=True), exog], axis=1)

        self._model.fit(feats, target)
        self._last_values = y.values[-max(self._lags):]
        self._fitted = True
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Llama fit() primero.")
        history = list(self._last_values)
        preds = []
        for i in range(horizon):
            lag_vals = {f"lag_{l}": history[-l] for l in self._lags}
            row = pd.DataFrame([lag_vals])
            if X_future is not None and i < len(X_future):
                exog_row = X_future.iloc[[i]].reset_index(drop=True)
                row = pd.concat([row, exog_row], axis=1)
            p = float(self._model.predict(row)[0])
            preds.append(p)
            history.append(p)
        return np.array(preds)


class XGBoostModel(_SklearnModel):
    """XGBoost para pronóstico ambiental."""

    name = "XGBoost"

    def __init__(self, lags: List[int] = None, **xgb_params):
        super().__init__(**xgb_params)
        try:
            from xgboost import XGBRegressor
        except ImportError:
            raise ImportError("Instalar xgboost: pip install xgboost")
        self._lags = lags or [1, 2, 3, 6, 12]
        defaults = {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
                    "subsample": 0.8, "colsample_bytree": 0.8,
                    "verbosity": 0, "random_state": 42}
        defaults.update(xgb_params)
        self._model = XGBRegressor(**defaults)

    @property
    def warm_starts(self):
        return [
            {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
             "subsample": 0.8, "colsample_bytree": 0.8},
            {"n_estimators": 500, "max_depth": 6, "learning_rate": 0.01,
             "subsample": 0.7, "colsample_bytree": 0.7},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "n_estimators":     trial.suggest_int("n_estimators", 50, 500),
            "max_depth":        trial.suggest_int("max_depth", 2, 8),
            "learning_rate":    trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        }

    def build_model(self, params: dict) -> "XGBoostModel":
        return XGBoostModel(lags=self._lags, **params)


class RandomForestModel(_SklearnModel):
    """Random Forest para pronóstico ambiental."""

    name = "RandomForest"

    def __init__(self, lags: List[int] = None, **rf_params):
        super().__init__(**rf_params)
        from sklearn.ensemble import RandomForestRegressor
        self._lags = lags or [1, 2, 3, 6, 12]
        defaults = {"n_estimators": 200, "max_depth": None,
                    "min_samples_leaf": 2, "random_state": 42, "n_jobs": -1}
        defaults.update(rf_params)
        self._model = RandomForestRegressor(**defaults)

    @property
    def warm_starts(self):
        return [
            {"n_estimators": 200, "max_depth": None,  "min_samples_leaf": 2},
            {"n_estimators": 500, "max_depth": 10,    "min_samples_leaf": 1},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "n_estimators":    trial.suggest_int("n_estimators", 50, 500),
            "max_depth":       trial.suggest_categorical("max_depth", [None, 5, 10, 20]),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }

    def build_model(self, params: dict) -> "RandomForestModel":
        return RandomForestModel(lags=self._lags, **params)


class LightGBMModel(_SklearnModel):
    """LightGBM para pronóstico ambiental."""

    name = "LightGBM"

    def __init__(self, lags: List[int] = None, **lgb_params):
        super().__init__(**lgb_params)
        try:
            from lightgbm import LGBMRegressor
        except ImportError:
            raise ImportError("Instalar lightgbm: pip install lightgbm")
        self._lags = lags or [1, 2, 3, 6, 12]
        defaults = {"n_estimators": 200, "max_depth": -1,
                    "learning_rate": 0.05, "random_state": 42,
                    "verbosity": -1, "n_jobs": -1}
        defaults.update(lgb_params)
        self._model = LGBMRegressor(**defaults)

    @property
    def warm_starts(self):
        return [
            {"n_estimators": 200, "max_depth": -1, "learning_rate": 0.05, "num_leaves": 31},
            {"n_estimators": 500, "max_depth":  7, "learning_rate": 0.01, "num_leaves": 63},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "n_estimators":  trial.suggest_int("n_estimators", 50, 500),
            "max_depth":     trial.suggest_int("max_depth", -1, 10),
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            "num_leaves":    trial.suggest_int("num_leaves", 20, 150),
        }

    def build_model(self, params: dict) -> "LightGBMModel":
        return LightGBMModel(lags=self._lags, **params)
