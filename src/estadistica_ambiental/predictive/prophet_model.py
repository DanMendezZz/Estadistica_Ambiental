"""Modelo Prophet (Meta) con interfaz BaseModel."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


class ProphetModel(BaseModel):
    """Envuelve Prophet con la interfaz BaseModel.

    Requiere: pip install prophet
    """

    name = "Prophet"

    def __init__(
        self,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = False,
        daily_seasonality: bool = False,
        interval_width: float = 0.80,
    ):
        super().__init__(
            changepoint_prior_scale=changepoint_prior_scale,
            seasonality_prior_scale=seasonality_prior_scale,
        )
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.interval_width = interval_width
        self._model = None
        self._last_date = None
        self._freq = None

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "ProphetModel":
        try:
            from prophet import Prophet
        except ImportError:
            raise ImportError("Instalar Prophet: pip install prophet")

        self._model = Prophet(
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            interval_width=self.interval_width,
        )

        df = pd.DataFrame({"ds": y.index, "y": y.values})
        if X is not None:
            for col in X.columns:
                df[col] = X[col].values
                self._model.add_regressor(col)

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model.fit(df)

        self._last_date = y.index[-1]
        self._freq = pd.infer_freq(y.index) or "D"
        self._fitted = True
        logger.info("Prophet ajustado hasta %s", self._last_date)
        return self

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Llama fit() primero.")
        future = self._model.make_future_dataframe(periods=horizon, freq=self._freq)

        if X_future is not None:
            for col in X_future.columns:
                future.loc[future.index[-horizon:], col] = X_future[col].values

        forecast = self._model.predict(future)
        return forecast["yhat"].values[-horizon:]

    @property
    def warm_starts(self):
        return [
            {"changepoint_prior_scale": 0.05, "seasonality_prior_scale": 10.0},
            {"changepoint_prior_scale": 0.10, "seasonality_prior_scale": 5.0},
            {"changepoint_prior_scale": 0.01, "seasonality_prior_scale": 20.0},
        ]

    def suggest_params(self, trial) -> dict:
        return {
            "changepoint_prior_scale": trial.suggest_float(
                "changepoint_prior_scale", 0.001, 0.5, log=True
            ),
            "seasonality_prior_scale": trial.suggest_float(
                "seasonality_prior_scale", 0.01, 20.0, log=True
            ),
        }

    def build_model(self, params: dict) -> "ProphetModel":
        return ProphetModel(
            changepoint_prior_scale=params.get("changepoint_prior_scale", 0.05),
            seasonality_prior_scale=params.get("seasonality_prior_scale", 10.0),
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            interval_width=self.interval_width,
        )
