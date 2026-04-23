"""
Motor de optimización bayesiana con Optuna TPE.
Adaptado de boa-sarima-forecaster/optimizer.py por Dan Méndez — 2026-04-22

Generalizado: soporta cualquier función objetivo y espacio de búsqueda,
no solo SARIMA. Usado por predictive/classical.py y demás modelos.

Mejoras incorporadas (v2):
- ``optimize_model``: acepta cualquier objeto que satisfaga el protocolo
  ``ModelSpec`` (warm_starts, suggest_params, build_model).
- Warm-start: encola configuraciones conocidas antes de la búsqueda TPE.
- Graceful fallback: si Optuna falla N veces seguidas usa warm_start[0].
- MedianPruner: descarta trials malos temprano para ahorrar tiempo.
- Devuelve ``OptimizationResult`` tipado en lugar del Study crudo.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)
logger = logging.getLogger(__name__)

# Número máximo de fallos consecutivos antes de activar el fallback
_MAX_FALLOS_CONSECUTIVOS: int = 5


def optimize(
    objective: Callable[[optuna.Trial], float],
    n_trials: int = 50,
    timeout: Optional[int] = None,
    direction: str = "minimize",
    study_name: Optional[str] = None,
    storage: Optional[str] = None,
    show_progress: bool = False,
    warm_starts: Optional[List[Dict[str, Any]]] = None,
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
        warm_starts: Lista de dicts de hiperparámetros que se encolan como
                     trials iniciales antes de la exploración aleatoria.
                     Si se provee, Optuna parte de configuraciones conocidas
                     en lugar de explorar ciegamente.

    Returns:
        optuna.Study con el historial completo de la búsqueda.
    """
    sampler = optuna.samplers.TPESampler(multivariate=True, seed=42)
    study = optuna.create_study(
        direction=direction,
        sampler=sampler,
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )

    # Inyectar warm-starts antes de la búsqueda aleatoria
    if warm_starts:
        for ws in warm_starts:
            study.enqueue_trial(ws)
        logger.debug("Warm-starts encolados: %d configuración(es)", len(warm_starts))

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


def optimize_model(
    model_spec: Any,
    objective: Callable[[optuna.Trial], float],
    n_trials: int = 50,
    timeout: Optional[int] = None,
    direction: str = "minimize",
    study_name: Optional[str] = None,
    storage: Optional[str] = None,
    show_progress: bool = False,
    max_fallos: int = _MAX_FALLOS_CONSECUTIVOS,
) -> "OptimizationResult":
    """Optimiza los hiperparámetros de un modelo que sigue el protocolo ModelSpec.

    Esta función extiende :func:`optimize` con soporte explícito para el
    protocolo ``ModelSpec``:

    - Si ``model_spec`` tiene ``warm_starts``, los inyecta como trials
      iniciales antes de la exploración aleatoria de Optuna.
    - Si Optuna acumula ``max_fallos`` excepciones consecutivas (o falla
      completamente), activa el fallback usando ``warm_starts[0]`` como
      parámetros por defecto en lugar de propagar la excepción.
    - Construye el modelo final con ``model_spec.build_model(best_params)``
      si el método está disponible.

    Args:
        model_spec: Objeto que implementa el protocolo ``ModelSpec``
                    (``warm_starts``, ``suggest_params``, ``build_model``).
                    También acepta objetos sin esos atributos (funciona como
                    :func:`optimize` en ese caso).
        objective: Función ``(optuna.Trial) → float`` a minimizar/maximizar.
        n_trials: Número total de evaluaciones de Optuna.
        timeout: Tiempo límite en segundos (None = sin límite).
        direction: 'minimize' | 'maximize'.
        study_name: Nombre del estudio Optuna (opcional).
        storage: URL de base de datos Optuna para persistencia (opcional).
        show_progress: Mostrar barra de progreso en consola.
        max_fallos: Fallos consecutivos tolerados antes de activar fallback.

    Returns:
        :class:`~estadistica_ambiental.predictive.base.OptimizationResult`
        con ``best_params``, ``best_score``, ``n_trials``, ``model``,
        ``study`` y el flag ``fallback``.
    """
    from estadistica_ambiental.predictive.base import OPTIMIZER_PENALTY, OptimizationResult

    model_name: str = getattr(model_spec, "name", "desconocido")
    warm_starts: List[Dict[str, Any]] = (
        list(model_spec.warm_starts)
        if hasattr(model_spec, "warm_starts")
        else []
    )

    # Envoltorio del objetivo con conteo de fallos consecutivos
    fallos_consecutivos = [0]

    penalty = OPTIMIZER_PENALTY if direction == "minimize" else -OPTIMIZER_PENALTY

    def objetivo_robusto(trial: optuna.Trial) -> float:
        try:
            valor = objective(trial)
            fallos_consecutivos[0] = 0  # reiniciar contador en éxito
            return valor
        except optuna.TrialPruned:
            raise
        except Exception as exc:
            fallos_consecutivos[0] += 1
            logger.warning(
                "Trial %d falló para '%s' (fallo %d/%d): %s",
                trial.number,
                model_name,
                fallos_consecutivos[0],
                max_fallos,
                exc,
            )
            if fallos_consecutivos[0] >= max_fallos:
                raise optuna.exceptions.OptunaError(
                    f"Demasiados fallos consecutivos ({max_fallos}) para '{model_name}'"
                ) from exc
            return penalty

    # Intentar la optimización completa
    fallback_activado = False
    study: Optional[optuna.Study] = None

    try:
        sampler = optuna.samplers.TPESampler(multivariate=True, seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1)
        study = optuna.create_study(
            direction=direction,
            sampler=sampler,
            pruner=pruner,
            study_name=study_name,
            storage=storage,
            load_if_exists=True,
        )

        # Inyectar warm-starts antes de la exploración aleatoria
        for ws in warm_starts:
            study.enqueue_trial(ws)
        if warm_starts:
            logger.debug(
                "Warm-starts encolados para '%s': %d configuración(es)",
                model_name,
                len(warm_starts),
            )

        study.optimize(
            objetivo_robusto,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=show_progress,
            gc_after_trial=True,
        )

        best_p = study.best_params
        best_s = study.best_value

    except Exception as exc:
        logger.warning(
            "Optuna falló para '%s': %s. Activando fallback con warm_start[0].",
            model_name,
            exc,
        )
        if study is not None and study.best_trial is not None:
            best_p = study.best_params
            best_s = study.best_value
        else:
            best_p = warm_starts[0] if warm_starts else {}
            best_s = penalty
        fallback_activado = True

    # Construir el modelo final si el spec lo soporta
    modelo_final = None
    if hasattr(model_spec, "build_model"):
        try:
            modelo_final = model_spec.build_model(best_p or {})
        except Exception as exc:
            logger.warning("build_model falló para '%s': %s", model_name, exc)

    resultado = OptimizationResult(
        best_params=best_p,
        best_score=best_s,
        n_trials=len(study.trials) if study is not None else 0,
        model=modelo_final,
        study=study,
        model_name=model_name,
        fallback=fallback_activado,
    )

    logger.info(
        "optimize_model '%s' finalizado. Score=%.4f | Fallback=%s | Params=%s",
        model_name,
        best_s,
        fallback_activado,
        best_p,
    )
    return resultado


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


def optimize_sarima(
    series: "pd.Series",
    n_trials: int = 50,
    max_p: int = 5,
    max_q: int = 5,
    seasonal_period: int = 12,
    n_splits: int = 3,
    horizon: int = 1,
    gap: int = 0,
    timeout: Optional[int] = None,
) -> "OptimizationResult":
    """Wrapper convenience para optimizar hiperparámetros SARIMA con Optuna.

    Uso::

        from estadistica_ambiental.optimization.bayes_opt import optimize_sarima
        result = optimize_sarima(serie_caudal, n_trials=50)
        mejor_modelo = result.model  # SARIMAModel listo para fit()

    Args:
        series: Serie temporal objetivo (pd.Series con DatetimeIndex).
        n_trials: Evaluaciones de Optuna.
        max_p: Máximo orden AR (p).
        max_q: Máximo orden MA (q).
        seasonal_period: Período estacional S (default 12 para datos mensuales).
        n_splits: Folds del walk-forward dentro del objetivo.
        horizon: Horizonte de pronóstico en el objetivo.
        gap: Purga entre train y test (ver walk_forward).
        timeout: Tiempo límite en segundos.

    Returns:
        OptimizationResult con best_params, best_score y model construido.
    """
    from estadistica_ambiental.evaluation.backtesting import walk_forward
    from estadistica_ambiental.predictive.classical import SARIMAModel

    spec = SARIMAModel(seasonal_order=(1, 1, 1, seasonal_period))

    def objective(trial: optuna.Trial) -> float:
        params = sarima_search_space(
            trial, max_p=max_p, max_d=2, max_q=max_q,
            max_P=2, max_D=1, max_Q=2,
            seasonal_period=seasonal_period,
        )
        model = SARIMAModel(
            order=(params["p"], params["d"], params["q"]),
            seasonal_order=(params["P"], params["D"], params["Q"], params["s"]),
        )
        result = walk_forward(
            model, series, horizon=horizon, n_splits=n_splits, gap=gap
        )
        return result["metrics"].get("nrmse", 1e6)

    return optimize_model(
        spec, objective,
        n_trials=n_trials,
        timeout=timeout,
        direction="minimize",
        study_name=f"sarima_s{seasonal_period}",
    )


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
