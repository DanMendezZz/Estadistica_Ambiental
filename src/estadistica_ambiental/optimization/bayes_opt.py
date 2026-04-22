"""
Motor de optimización bayesiana con Optuna TPE.
Adaptado de boa-sarima-forecaster/optimizer.py por Dan Méndez — 2026-04-22

Generalizado: soporta cualquier función objetivo y espacio de búsqueda,
no solo SARIMA. Usado por predictive/classical.py y demás modelos.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)
logger = logging.getLogger(__name__)


def optimize(
    objective: Callable[[optuna.Trial], float],
    n_trials: int = 50,
    timeout: Optional[int] = None,
    direction: str = "minimize",
    study_name: Optional[str] = None,
    storage: Optional[str] = None,
    show_progress: bool = False,
) -> optuna.Study:
    """Ejecuta optimización bayesiana TPE sobre la función objetivo.

    Args:
        objective: Función que recibe un Trial de Optuna y devuelve el valor
                   a minimizar (o maximizar si direction='maximize').
        n_trials: Número de evaluaciones.
        timeout: Tiempo límite en segundos (None = sin límite).
        direction: 'minimize' | 'maximize'.
        study_name: Nombre del estudio (opcional).
        storage: URL de base de datos Optuna para persistencia (opcional).
        show_progress: Mostrar barra de progreso en consola.

    Returns:
        optuna.Study con el historial completo de la búsqueda.
    """
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(
        direction=direction,
        sampler=sampler,
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=show_progress,
        gc_after_trial=True,
    )
    logger.info(
        "Optimización finalizada. Mejor valor: %.4f | Params: %s",
        study.best_value,
        study.best_params,
    )
    return study


def best_params(study: optuna.Study) -> Dict[str, Any]:
    """Devuelve los mejores hiperparámetros del estudio."""
    return study.best_params


def optimization_history(study: optuna.Study) -> "pd.DataFrame":
    """Historial de trials como DataFrame (requiere optuna visualización)."""
    import pandas as pd
    rows = [
        {"trial": t.number, "value": t.value, **t.params}
        for t in study.trials
        if t.value is not None
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Espacios de búsqueda predefinidos
# ---------------------------------------------------------------------------

def sarima_search_space(
    trial: optuna.Trial,
    max_p: int = 5,
    max_d: int = 2,
    max_q: int = 5,
    max_P: int = 2,
    max_D: int = 1,
    max_Q: int = 2,
    seasonal_period: int = 12,
) -> Dict[str, int]:
    """Espacio de búsqueda estándar para SARIMA (p,d,q)(P,D,Q,s)."""
    return {
        "p": trial.suggest_int("p", 0, max_p),
        "d": trial.suggest_int("d", 0, max_d),
        "q": trial.suggest_int("q", 0, max_q),
        "P": trial.suggest_int("P", 0, max_P),
        "D": trial.suggest_int("D", 0, max_D),
        "Q": trial.suggest_int("Q", 0, max_Q),
        "s": seasonal_period,
    }


def xgboost_search_space(trial: optuna.Trial) -> Dict[str, Any]:
    """Espacio de búsqueda estándar para XGBoost."""
    return {
        "n_estimators":    trial.suggest_int("n_estimators", 50, 500),
        "max_depth":       trial.suggest_int("max_depth", 3, 10),
        "learning_rate":   trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "subsample":       trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree":trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha":       trial.suggest_float("reg_alpha", 1e-5, 10.0, log=True),
        "reg_lambda":      trial.suggest_float("reg_lambda", 1e-5, 10.0, log=True),
    }
