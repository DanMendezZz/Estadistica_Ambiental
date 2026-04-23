"""Clase base abstracta y protocolo ModelSpec para todos los modelos predictivos ambientales."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Penalización estándar cuando un trial de Optuna falla
# ---------------------------------------------------------------------------

OPTIMIZER_PENALTY: float = 1e6


# ---------------------------------------------------------------------------
# Protocolo ModelSpec — contrato estructural para modelos del pipeline
# ---------------------------------------------------------------------------

@runtime_checkable
class ModelSpec(Protocol):
    """Protocolo estructural que todo modelo optimizable debe satisfacer.

    Permite agregar nuevos modelos al pipeline de optimización sin modificar
    el optimizador. Basta con que la clase implemente los miembros requeridos;
    no es necesario heredar de esta clase (duck-typing estructural).

    Uso típico::

        class MiModelo:
            name = "MiModelo"

            @property
            def warm_starts(self) -> list[dict]:
                return [{"n_estimators": 100, "max_depth": 5}]

            def suggest_params(self, trial) -> dict:
                return {"n_estimators": trial.suggest_int("n_estimators", 50, 500)}

            def build_model(self, params: dict):
                return MiEstimador(**params)

        assert isinstance(MiModelo(), ModelSpec)  # True sin herencia
    """

    #: Nombre identificador del modelo (p. ej. "XGBoost", "SARIMA").
    name: str

    @property
    def warm_starts(self) -> List[Dict[str, Any]]:
        """Configuraciones iniciales conocidas para acelerar Optuna.

        Cada dict se encola como trial inicial antes de la búsqueda aleatoria,
        reduciendo el número de evaluaciones necesarias para converger.

        Returns:
            Lista de dicts con hiperparámetros (puede estar vacía).
        """
        ...

    def suggest_params(self, trial: Any) -> Dict[str, Any]:
        """Sugiere hiperparámetros a partir de un Trial de Optuna.

        Args:
            trial: ``optuna.Trial`` activo en la búsqueda.

        Returns:
            Dict con los hiperparámetros sugeridos para este trial.
        """
        ...

    def build_model(self, params: Dict[str, Any]) -> Any:
        """Construye e instancia el modelo con los parámetros dados.

        Args:
            params: Dict de hiperparámetros, típicamente obtenido de
                    :meth:`suggest_params` o de :attr:`warm_starts`.

        Returns:
            Instancia del modelo (sklearn, statsmodels, etc.) lista para
            ser ajustada con ``.fit()``.
        """
        ...

    @property
    def search_space(self) -> Dict[str, Any]:
        """Descripción del espacio de búsqueda (opcional, para documentación).

        Returns:
            Dict con metadatos del espacio: nombre → (tipo, min, max, ...).
        """
        ...


# ---------------------------------------------------------------------------
# OptimizationResult — resultado estándar de una corrida de optimización
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """Resultado estándar de una corrida de optimización bayesiana.

    Attributes:
        best_params: Mejores hiperparámetros encontrados por Optuna.
        best_score: Valor de la métrica objetivo para ``best_params``.
        n_trials: Número de trials ejecutados.
        model: Instancia del modelo construida con ``best_params``
               (None si no se construyó explícitamente).
        study: Objeto ``optuna.Study`` con el historial completo
               (None si no está disponible o hubo fallback).
        model_name: Nombre identificador del modelo optimizado.
        cv_scores: Puntuaciones individuales por trial (para análisis).
        fallback: True si Optuna falló y se usó el primer warm_start.
    """

    best_params: Dict[str, Any]
    best_score: float
    n_trials: int
    model: Any = field(default=None, repr=False)
    study: Any = field(default=None, repr=False)
    model_name: str = ""
    cv_scores: List[float] = field(default_factory=list)
    fallback: bool = False

    def __post_init__(self) -> None:
        if self.best_score == OPTIMIZER_PENALTY and not self.fallback:
            # Marcar automáticamente como fallback si el score es la penalización
            object.__setattr__(self, "fallback", True)


# ---------------------------------------------------------------------------
# BaseModel — clase base abstracta para todos los modelos del catálogo
# ---------------------------------------------------------------------------

class BaseModel(ABC):
    """Interfaz común para todos los modelos del catálogo.

    Subclases deben implementar :meth:`fit` y :meth:`predict`.
    Para participar en el pipeline de optimización bayesiana, las subclases
    también pueden implementar el protocolo :class:`ModelSpec` añadiendo
    :attr:`warm_starts`, :meth:`suggest_params` y :meth:`build_model`.
    """

    name: str = "BaseModel"

    def __init__(self, **hyperparams: Any) -> None:
        self.hyperparams = hyperparams
        self._fitted = False

    @abstractmethod
    def fit(self, y: pd.Series, X: Optional[pd.DataFrame] = None) -> "BaseModel":
        """Ajusta el modelo a la serie objetivo y exógenas opcionales."""

    @abstractmethod
    def predict(self, horizon: int, X_future: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Genera pronóstico para ``horizon`` pasos adelante."""

    def fit_predict(
        self,
        y: pd.Series,
        horizon: int,
        X: Optional[pd.DataFrame] = None,
        X_future: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        """Ajusta el modelo y genera el pronóstico en un solo paso."""
        self.fit(y, X)
        return self.predict(horizon, X_future)

    @property
    def is_fitted(self) -> bool:
        """True si el modelo ha sido ajustado con :meth:`fit`."""
        return self._fitted

    def get_params(self) -> Dict[str, Any]:
        """Devuelve copia de los hiperparámetros actuales."""
        return self.hyperparams.copy()

    def __repr__(self) -> str:
        return f"{self.name}({self.hyperparams})"
