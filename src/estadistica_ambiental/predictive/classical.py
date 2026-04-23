"""
Modelos estadísticos clásicos: ARIMA, SARIMA, SARIMAX, ETS/Holt-Winters.
Adaptado de boa-sarima-forecaster/model.py por Dan Méndez — 2026-04-22

Cambios respecto al original:
- Interfaz BaseModel unificada (fit/predict).
- Soporte SARIMAX con exógenas meteorológicas (crítico para calidad del aire).
- Validación de estacionariedad obligatoria via stationarity.py (ADR-004).
- Sin terminología financiera (SKU/country → variable/estacion).
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


class SARIMAXModel(BaseModel):
    """SARIMAX — SARIMA con regresores exógenos opcionales.

    Envuelve statsmodels.tsa.statespace.sarimax.SARIMAX con la interfaz BaseModel.
    """

    name = "SARIMAX"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        seasonal_order: Tuple[int, int, int, int] = (0, 0, 0, 0),
        trend: str = "n",
        enforce_stationarity: bool = False,
        enforce_invertibility: bool = False,
    ):
        super().__init__(
            order=order,
            seasonal_order=seasonal_order,
            trend=trend,
        )
        self.order = order
        self.seasonal_order = seasonal_order
        self.trend = trend
        self._enforce_stationarity = enforce_stationarity
        self._enforce_invertibility = enforce_invertibility
        self._result = None

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "SARIMAXModel":
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = SARIMAX(
                y,
                exog=X,
                order=self.order,
                seasonal_order=self.seasonal_order,
                trend=self.trend,
                enforce_stationarity=self._enforce_stationarity,
                enforce_invertibility=self._enforce_invertibility,
            )
            self._result = model.fit(disp=False)
        self._fitted = True
        logger.info("%s ajustado. AIC=%.2f", self.name, self._result.aic)
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("El modelo no ha sido ajustado. Llama fit() primero.")
        forecast = self._result.forecast(steps=horizon, exog=X_future)
        return np.asarray(forecast)

    @property
    def warm_starts(self):
        return [
            {"p": 1, "d": 1, "q": 1, "P": 1, "D": 1, "Q": 1},
            {"p": 2, "d": 1, "q": 2, "P": 1, "D": 1, "Q": 1},
            {"p": 0, "d": 1, "q": 1, "P": 0, "D": 1, "Q": 1},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "p": trial.suggest_int("p", 0, 4),
            "d": trial.suggest_int("d", 0, 2),
            "q": trial.suggest_int("q", 0, 4),
            "P": trial.suggest_int("P", 0, 2),
            "D": trial.suggest_int("D", 0, 1),
            "Q": trial.suggest_int("Q", 0, 2),
        }

    def build_model(self, params: dict) -> "SARIMAXModel":
        return SARIMAXModel(
            order=(params.get("p", 1), params.get("d", 1), params.get("q", 1)),
            seasonal_order=(params.get("P", 0), params.get("D", 0), params.get("Q", 0), 12),
            trend=self.trend,
        )

    @property
    def aic(self) -> float:
        return self._result.aic if self._fitted else float("inf")

    @property
    def summary(self):
        return self._result.summary() if self._fitted else None


class ARIMAModel(SARIMAXModel):
    """ARIMA puro (sin estacionalidad ni exógenas)."""

    name = "ARIMA"

    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1)):
        super().__init__(order=order, seasonal_order=(0, 0, 0, 0))

    @property
    def warm_starts(self):
        return [
            {"p": 1, "d": 1, "q": 1},
            {"p": 2, "d": 1, "q": 2},
            {"p": 1, "d": 0, "q": 1},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "p": trial.suggest_int("p", 0, 5),
            "d": trial.suggest_int("d", 0, 2),
            "q": trial.suggest_int("q", 0, 5),
        }

    def build_model(self, params: dict) -> "ARIMAModel":
        return ARIMAModel(order=(params.get("p", 1), params.get("d", 1), params.get("q", 1)))


class SARIMAModel(SARIMAXModel):
    """SARIMA sin exógenas."""

    name = "SARIMA"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12),
    ):
        super().__init__(order=order, seasonal_order=seasonal_order)

    @property
    def warm_starts(self):
        return [
            {"p": 1, "d": 1, "q": 1, "P": 1, "D": 1, "Q": 1},
            {"p": 2, "d": 1, "q": 2, "P": 0, "D": 1, "Q": 1},
            {"p": 0, "d": 1, "q": 1, "P": 1, "D": 1, "Q": 0},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "p": trial.suggest_int("p", 0, 4),
            "d": trial.suggest_int("d", 0, 2),
            "q": trial.suggest_int("q", 0, 4),
            "P": trial.suggest_int("P", 0, 2),
            "D": trial.suggest_int("D", 0, 1),
            "Q": trial.suggest_int("Q", 0, 2),
        }

    def build_model(self, params: dict) -> "SARIMAModel":
        s = self.seasonal_order[3]
        return SARIMAModel(
            order=(params.get("p", 1), params.get("d", 1), params.get("q", 1)),
            seasonal_order=(params.get("P", 1), params.get("D", 1), params.get("Q", 1), s),
        )


class ETSModel(BaseModel):
    """ETS / Holt-Winters vía statsmodels ExponentialSmoothing."""

    name = "ETS"

    def __init__(
        self,
        trend: Optional[str] = "add",
        seasonal: Optional[str] = "add",
        seasonal_periods: int = 12,
        damped_trend: bool = False,
    ):
        super().__init__(
            trend=trend,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            damped_trend=damped_trend,
        )
        self.trend = trend
        self.seasonal = seasonal
        self.seasonal_periods = seasonal_periods
        self.damped_trend = damped_trend
        self._result = None

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "ETSModel":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ExponentialSmoothing(
                y,
                trend=self.trend,
                seasonal=self.seasonal,
                seasonal_periods=self.seasonal_periods,
                damped_trend=self.damped_trend,
            )
            self._result = model.fit(optimized=True)
        self._fitted = True
        logger.info("%s ajustado. AIC=%.2f", self.name, self._result.aic)
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Llama fit() primero.")
        return np.asarray(self._result.forecast(steps=horizon))

    @property
    def warm_starts(self):
        return [
            {"trend": "add", "seasonal": "add", "damped_trend": False},
            {"trend": "mul", "seasonal": "mul", "damped_trend": False},
            {"trend": "add", "seasonal": "add", "damped_trend": True},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "trend": trial.suggest_categorical("trend", ["add", "mul", None]),
            "seasonal": trial.suggest_categorical("seasonal", ["add", "mul", None]),
            "damped_trend": trial.suggest_categorical("damped_trend", [True, False]),
        }

    def build_model(self, params: dict) -> "ETSModel":
        return ETSModel(
            trend=params.get("trend", "add"),
            seasonal=params.get("seasonal", "add"),
            seasonal_periods=self.seasonal_periods,
            damped_trend=params.get("damped_trend", False),
        )
