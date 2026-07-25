"""
Módulo predictive — modelos de pronóstico y protocolo de optimización.

Exporta las clases base y el protocolo ModelSpec para que otros módulos
puedan importarlos directamente desde ``estadistica_ambiental.predictive``.
"""

from estadistica_ambiental.predictive.base import (
    OPTIMIZER_PENALTY,
    BaseModel,
    ModelSpec,
    OptimizationResult,
)

__all__ = [
    "BaseModel",
    "ModelSpec",
    "OptimizationResult",
    "OPTIMIZER_PENALTY",
]
