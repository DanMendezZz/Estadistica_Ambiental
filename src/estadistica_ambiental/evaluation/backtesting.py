"""Backtesting walk-forward para modelos predictivos ambientales."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.evaluation.metrics import evaluate
from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


def walk_forward(
    model: BaseModel,
    y: pd.Series,
    horizon: int = 1,
    n_splits: int = 5,
    min_train_size: Optional[int] = None,
    X: Optional[pd.DataFrame] = None,
    domain: str = "general",
    strategy: str = "expanding",
    pollutant: str = "pm25",
    gap: int = 0,
) -> Dict:
    """Walk-forward backtesting con ventana expansiva o deslizante.

    Args:
        model: Instancia de BaseModel (se re-entrena en cada fold).
        y: Serie temporal objetivo.
        horizon: Pasos a predecir en cada fold.
        n_splits: Número de folds.
        min_train_size: Tamaño mínimo del conjunto de entrenamiento.
        X: Exógenas (si el modelo las soporta).
        domain: 'general' | 'hydrology' | 'air_quality' para métricas.
        strategy: 'expanding' (crece) | 'sliding' (tamaño fijo).
        pollutant: Contaminante para breakpoints ICA ('pm25', 'pm10', 'o3',
            'no2', 'so2', 'co'). Solo aplica con domain='air_quality'.
        gap: Observaciones de purga entre fin de train y comienzo de test.
            Evita leakage por autocorrelación alta (PM2.5 horario, caudal diario).
            Default 0 (sin purga) para compatibilidad retroactiva.

    Returns:
        Dict con 'metrics' (promedio), 'folds' (lista por fold) y 'predictions'.
    """
    n = len(y)
    min_train = min_train_size or max(int(n * 0.5), horizon * 2)
    step = max(1, (n - min_train) // n_splits)

    folds = []
    all_actual, all_pred = [], []

    for fold_idx in range(n_splits):
        if strategy == "expanding":
            train_end = min_train + fold_idx * step
        else:
            train_start = fold_idx * step
            train_end = min_train + fold_idx * step

        test_start = train_end + gap
        test_end   = min(test_start + horizon, n)

        if test_end > n or test_start >= n:
            break

        if strategy == "expanding":
            y_train = y.iloc[:train_end]
            X_train = X.iloc[:train_end] if X is not None else None
        else:
            y_train = y.iloc[train_start:train_end]
            X_train = X.iloc[train_start:train_end] if X is not None else None

        y_test = y.iloc[test_start:test_end]
        X_test = X.iloc[test_start:test_end] if X is not None else None

        try:
            model.fit(y_train, X_train)
            preds = model.predict(len(y_test), X_test)
            actual = y_test.values
            metrics = evaluate(actual, preds, domain=domain, pollutant=pollutant)
        except Exception as e:
            logger.warning("Fold %d falló: %s", fold_idx, e)
            continue

        folds.append({"fold": fold_idx, "train_size": len(y_train),
                      "test_size": len(y_test), **metrics})
        all_actual.extend(actual)
        all_pred.extend(preds)

    if not folds:
        return {"metrics": {}, "folds": [], "predictions": pd.DataFrame()}

    folds_df   = pd.DataFrame(folds)
    avg_metrics = folds_df.drop(columns=["fold", "train_size", "test_size"]).mean().to_dict()
    avg_metrics = {k: round(v, 4) for k, v in avg_metrics.items()}

    preds_df = pd.DataFrame({
        "actual":    all_actual,
        "predicted": all_pred,
    })

    logger.info("%s backtesting: %d folds | RMSE=%.4f | MAE=%.4f",
                model.name, len(folds),
                avg_metrics.get("rmse", float("nan")),
                avg_metrics.get("mae", float("nan")))

    return {"metrics": avg_metrics, "folds": folds_df, "predictions": preds_df}


def compare_backtests(results: Dict[str, Dict]) -> pd.DataFrame:
    """Tabla comparativa de modelos backtested.

    results = {model_name: walk_forward_result_dict}
    """
    rows = []
    for model_name, result in results.items():
        row = {"model": model_name, **result.get("metrics", {})}
        rows.append(row)
    df = pd.DataFrame(rows).set_index("model")
    return df.sort_values("rmse") if "rmse" in df.columns else df
