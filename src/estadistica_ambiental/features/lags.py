"""Feature engineering: lags, rolling stats y diferencias para series ambientales."""

from __future__ import annotations

from typing import List

import pandas as pd


def add_lags(
    df: pd.DataFrame,
    col: str,
    lags: List[int],
    drop_na: bool = False,
) -> pd.DataFrame:
    """Agrega columnas lag_N para la variable objetivo."""
    result = df.copy()
    for lag in lags:
        result[f"{col}_lag{lag}"] = result[col].shift(lag)
    if drop_na:
        result = result.dropna()
    return result


def add_rolling_features(
    df: pd.DataFrame,
    col: str,
    windows: List[int],
    stats: List[str] = ("mean", "std", "min", "max"),
    drop_na: bool = False,
) -> pd.DataFrame:
    """Agrega estadísticas rodantes para capturar tendencia local."""
    result = df.copy()
    for w in windows:
        roll = result[col].rolling(w, min_periods=max(1, w // 2))
        for stat in stats:
            result[f"{col}_roll{w}_{stat}"] = getattr(roll, stat)()
    if drop_na:
        result = result.dropna()
    return result


def add_diff_features(
    df: pd.DataFrame,
    col: str,
    orders: List[int] = (1,),
) -> pd.DataFrame:
    """Agrega diferencias de orden N (útil para eliminar tendencia)."""
    result = df.copy()
    for order in orders:
        result[f"{col}_diff{order}"] = result[col].diff(order)
    return result
