"""Modelos espaciales: Kriging y Gaussian Process con interfaz BaseModel."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


class KrigingInterpolator:
    """Wrapper de pykrige.OrdinaryKriging para uso en pipelines del repo.

    No hereda BaseModel porque opera en espacio 2D, no en tiempo.
    Interfaz: fit(points_df) → predict(grid_lat, grid_lon).
    """

    def __init__(
        self,
        variogram_model: str = "spherical",
        lat_col: str = "lat",
        lon_col: str = "lon",
        value_col: str = "valor",
    ):
        self.variogram_model = variogram_model
        self.lat_col   = lat_col
        self.lon_col   = lon_col
        self.value_col = value_col
        self._ok = None

    def fit(self, points: pd.DataFrame) -> "KrigingInterpolator":
        try:
            from pykrige.ok import OrdinaryKriging
        except ImportError:
            raise ImportError("pip install pykrige  (o [spatial])")

        self._ok = OrdinaryKriging(
            x=points[self.lon_col].values,
            y=points[self.lat_col].values,
            z=points[self.value_col].values,
            variogram_model=self.variogram_model,
            verbose=False,
            enable_plotting=False,
        )
        logger.info("Kriging ajustado con %d puntos", len(points))
        return self

    def predict(
        self,
        grid_lat: np.ndarray,
        grid_lon: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Interpola sobre la grilla. Returns (z_values, z_variance)."""
        if self._ok is None:
            raise RuntimeError("Llama fit() primero.")
        z, ss = self._ok.execute("grid", grid_lon[0, :], grid_lat[:, 0])
        return np.array(z), np.array(ss)

    def predict_points(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        """Interpola en puntos arbitrarios (no en grilla)."""
        if self._ok is None:
            raise RuntimeError("Llama fit() primero.")
        z, _ = self._ok.execute("points", lons, lats)
        return np.array(z)


class SpatioTemporalKriging:
    """Kriging espacio-temporal simplificado: ajusta un Kriging por período.

    Para cada timestamp, interpola espacialmente las estaciones disponibles.
    Útil para mapas de PM2.5 o temperatura por fecha.
    """

    def __init__(self, variogram_model: str = "spherical"):
        self.variogram_model = variogram_model
        self._models: dict = {}

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        lat_col: str,
        lon_col: str,
        value_col: str,
    ) -> "SpatioTemporalKriging":
        for date, group in df.groupby(date_col):
            if group[value_col].notna().sum() >= 3:
                ki = KrigingInterpolator(self.variogram_model, lat_col, lon_col, value_col)
                ki.fit(group.dropna(subset=[value_col]))
                self._models[date] = ki
        logger.info("Kriging espacio-temporal: %d períodos ajustados", len(self._models))
        return self

    def predict(
        self,
        date,
        grid_lat: np.ndarray,
        grid_lon: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        if date not in self._models:
            raise KeyError(f"Sin modelo para la fecha {date}")
        return self._models[date].predict(grid_lat, grid_lon)
