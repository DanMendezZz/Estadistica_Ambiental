"""Comparación multi-criterio y selección del mejor modelo predictivo."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from estadistica_ambiental.evaluation.metrics import evaluate

logger = logging.getLogger(__name__)

# Pesos por defecto según dominio
_WEIGHTS = {
    "general":     {"rmse": 0.35, "mae": 0.30, "r2": 0.20, "mase": 0.15},
    "hydrology":   {"nse": 0.40, "kge": 0.30, "rmse": 0.20, "pbias": 0.10},
    "air_quality": {"rmse": 0.30, "nrmse": 0.20, "mae": 0.20, "hit_rate_ica": 0.30},
}

# Para métricas donde mayor es mejor, invertimos el signo al normalizar
_HIGHER_IS_BETTER = {"r2", "nse", "kge", "hit_rate_ica"}


def rank_models(
    results: Dict[str, Dict],
    domain: str = "general",
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Ranking multi-criterio de modelos backtestados.

    Args:
        results: {model_name: walk_forward_result} — salida de walk_forward().
        domain: 'general' | 'hydrology' | 'air_quality'.
        weights: Pesos custom {metric: weight}. Sobreescribe defaults.

    Returns:
        DataFrame ordenado por score compuesto (menor es mejor).
    """
    w = weights or _WEIGHTS.get(domain, _WEIGHTS["general"])
    metrics_keys = list(w.keys())

    rows = []
    for name, result in results.items():
        m = result.get("metrics", {})
        row = {"model": name}
        for k in metrics_keys:
            row[k] = m.get(k, np.nan)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("model")
    df_norm = _normalize(df, metrics_keys)

    scores = pd.Series(0.0, index=df.index)
    for metric, weight in w.items():
        if metric in df_norm.columns:
            scores += weight * df_norm[metric]

    df["score"] = scores.round(4)
    df["rank"]  = df["score"].rank(method="min").astype(int)
    df = df.sort_values("rank")

    best = df.index[0]
    logger.info("Mejor modelo: %s (score=%.4f)", best, df.loc[best, "score"])
    return df


def _normalize(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Min-max normalización. Invierte columnas donde mayor = mejor."""
    result = pd.DataFrame(index=df.index)
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].astype(float)
        lo, hi = s.min(), s.max()
        if hi == lo:
            result[col] = 0.0
            continue
        norm = (s - lo) / (hi - lo)
        # lower score = better; para higher-is-better, invertimos
        result[col] = norm if col not in _HIGHER_IS_BETTER else (1 - norm)
    return result


def select_best(
    results: Dict[str, Dict],
    domain: str = "general",
) -> str:
    """Devuelve el nombre del mejor modelo según ranking compuesto."""
    ranking = rank_models(results, domain=domain)
    return str(ranking.index[0])
