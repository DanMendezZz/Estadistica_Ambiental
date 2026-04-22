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


class SARIMAModel(SARIMAXModel):
    """SARIMA sin exógenas."""
    name = "SARIMA"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12),
    ):
        super().__init__(order=order, seasonal_order=seasonal_order)


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
        super().__init__(trend=trend, seasonal=seasonal,
                         seasonal_periods=seasonal_periods, damped_trend=damped_trend)
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
