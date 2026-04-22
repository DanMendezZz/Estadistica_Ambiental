"""Detección y tratamiento OPCIONAL de outliers en series ambientales.

Por defecto solo detecta y marca (ADR-002): los picos ambientales son señal real.
El clipping es opt-in explícito con treat=True.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def flag_outliers(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    method: str = "iqr",
    threshold: float = 1.5,
    treat: bool = False,
    treatment: str = "clip",
) -> pd.DataFrame:
    """Marca columnas con outliers. Opcionalmente los trata.

    Args:
        df: DataFrame de entrada.
        cols: Columnas a analizar (None = todas numéricas).
        method: 'iqr' | 'zscore' | 'modified_zscore'.
        threshold: Multiplicador IQR o número de desviaciones.
        treat: Si True aplica treatment (clip o nan). Default False (ADR-002).
        treatment: 'clip' recorta a los límites | 'nan' reemplaza por NaN.

    Returns:
        DataFrame con columnas adicionales '<col>_outlier' (bool).
    """
    result = df.copy()
    targets = cols or result.select_dtypes(include="number").columns.tolist()
    targets = [c for c in targets if c in result.columns]

    for col in targets:
        s = result[col]
        lo, hi = _compute_bounds(s.dropna(), method, threshold)
        mask = (s < lo) | (s > hi)
        result[f"{col}_outlier"] = mask
        n = int(mask.sum())

        if n > 0:
            logger.info("'%s': %d outliers detectados por %s [%.2f, %.2f]",
                        col, n, method, lo, hi)

        if treat and n > 0:
            if treatment == "clip":
                result[col] = s.clip(lower=lo, upper=hi)
                logger.warning("'%s': %d valores recortados a [%.2f, %.2f] — ADR-002", col, n, lo, hi)
            elif treatment == "nan":
                result.loc[mask, col] = np.nan
                logger.warning("'%s': %d valores reemplazados por NaN — ADR-002", col, n)

    return result


def _compute_bounds(s: pd.Series, method: str, threshold: float) -> Tuple[float, float]:
    if method == "iqr":
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        return q1 - threshold * iqr, q3 + threshold * iqr

    if method == "zscore":
        mu, sigma = s.mean(), s.std()
        return mu - threshold * sigma, mu + threshold * sigma

    if method == "modified_zscore":
        median = s.median()
        mad = (s - median).abs().median() * 1.4826
        return median - threshold * mad, median + threshold * mad

    raise ValueError(f"method debe ser 'iqr', 'zscore' o 'modified_zscore'. Recibido: '{method}'")
