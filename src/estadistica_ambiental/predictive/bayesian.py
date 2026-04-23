"""Modelos bayesianos jerárquicos para series ambientales.

Requiere: pip install estadistica-ambiental[bayes]  (pymc + arviz)

Estado: stub — implementación completa en Fase 10.
Referencia de diseño en docs/modelos.md sección Familia 5.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


def _check_pymc():
    try:
        import pymc as pm
        return pm
    except ImportError:
        raise ImportError(
            "PyMC es necesario para modelos bayesianos.\n"
            "Instalar: pip install estadistica-ambiental[bayes]"
        )


class BayesianARIMA(BaseModel):
    """SARIMA bayesiano con PyMC — cuantifica incertidumbre en los parámetros.

    Ventaja sobre SARIMA clásico: devuelve distribuciones posteriores en lugar
    de estimaciones puntuales; muy útil para intervalos de confianza de pronóstico.

    Requiere: pymc >= 5.9, arviz >= 0.18.
    """

    name = "BayesianARIMA"

    def __init__(
        self,
        order: tuple = (1, 1, 1),
        seasonal_order: tuple = (0, 0, 0, 0),
        draws: int = 1000,
        tune: int = 500,
        chains: int = 2,
        random_seed: int = 42,
    ):
        super().__init__(order=order, seasonal_order=seasonal_order, draws=draws)
        self.order = order
        self.seasonal_order = seasonal_order
        self.draws = draws
        self.tune = tune
        self.chains = chains
        self.random_seed = random_seed
        self._trace = None
        self._model = None

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "BayesianARIMA":
        _check_pymc()
        raise NotImplementedError(
            "BayesianARIMA está en desarrollo (Fase 10). "
            "Usar SARIMAXModel para pronóstico clásico."
        )

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        raise NotImplementedError("Llama fit() primero.")

    def predict_interval(
        self,
        horizon: int,
        credible_interval: float = 0.94,
    ) -> pd.DataFrame:
        """Pronóstico con intervalo de credibilidad bayesiano.

        Returns DataFrame con columnas: mean, lower, upper.
        """
        raise NotImplementedError("BayesianARIMA está en desarrollo (Fase 10).")


class HierarchicalModel(BaseModel):
    """Modelo jerárquico multi-estación con PyMC.

    Permite modelar simultáneamente múltiples estaciones compartiendo
    información sobre la estructura temporal (partial pooling).

    Útil cuando: pocas observaciones por estación, se quiere
    regularización automática entre estaciones similares.
    """

    name = "HierarchicalModel"

    def __init__(self, draws: int = 1000, tune: int = 500):
        super().__init__(draws=draws, tune=tune)
        self.draws = draws
        self.tune = tune

    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "HierarchicalModel":
        _check_pymc()
        raise NotImplementedError("HierarchicalModel está en desarrollo (Fase 10).")

    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        raise NotImplementedError("Llama fit() primero.")
