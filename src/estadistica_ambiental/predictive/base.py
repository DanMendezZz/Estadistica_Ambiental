"""Clase base abstracta para todos los modelos predictivos ambientales."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


class BaseModel(ABC):
    """Interfaz común para todos los modelos del catálogo."""

    name: str = "BaseModel"

    def __init__(self, **hyperparams):
        self.hyperparams = hyperparams
        self._fitted = False

    @abstractmethod
    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "BaseModel":
        """Ajusta el modelo a la serie objetivo y exógenas opcionales."""

    @abstractmethod
    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Genera pronóstico para `horizon` pasos adelante."""

    def fit_predict(
        self,
        y: pd.Series,
        horizon: int,
        X: Optional[pd.DataFrame] = None,
        X_future: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        self.fit(y, X)
        return self.predict(horizon, X_future)

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def get_params(self) -> Dict[str, Any]:
        return self.hyperparams.copy()

    def __repr__(self) -> str:
        return f"{self.name}({self.hyperparams})"
