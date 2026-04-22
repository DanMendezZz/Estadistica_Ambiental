"""Registro central de modelos predictivos del catálogo."""

from __future__ import annotations

from typing import Dict, List, Type

from estadistica_ambiental.predictive.base import BaseModel
from estadistica_ambiental.predictive.classical import ARIMAModel, ETSModel, SARIMAModel, SARIMAXModel
from estadistica_ambiental.predictive.ml import LightGBMModel, RandomForestModel, XGBoostModel

_REGISTRY: Dict[str, Type[BaseModel]] = {
    "arima":        ARIMAModel,
    "sarima":       SARIMAModel,
    "sarimax":      SARIMAXModel,
    "ets":          ETSModel,
    "xgboost":      XGBoostModel,
    "random_forest":RandomForestModel,
    "lightgbm":     LightGBMModel,
}

# Modelos deep learning — se registran solo si PyTorch está disponible
try:
    from estadistica_ambiental.predictive.deep import LSTMModel, GRUModel
    _REGISTRY["lstm"] = LSTMModel
    _REGISTRY["gru"]  = GRUModel
except ImportError:
    pass


def get_model(name: str, **kwargs) -> BaseModel:
    """Instancia un modelo por nombre. kwargs pasan al constructor."""
    key = name.lower().replace("-", "_").replace(" ", "_")
    if key not in _REGISTRY:
        raise ValueError(f"Modelo '{name}' no registrado. Disponibles: {list(_REGISTRY)}")
    return _REGISTRY[key](**kwargs)


def list_models() -> List[str]:
    """Devuelve la lista de modelos disponibles."""
    return list(_REGISTRY.keys())


def register(name: str, model_class: Type[BaseModel]) -> None:
    """Registra un modelo personalizado en el catálogo."""
    _REGISTRY[name.lower()] = model_class
