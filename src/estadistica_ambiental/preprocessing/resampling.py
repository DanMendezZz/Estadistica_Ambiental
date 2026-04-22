"""Remuestreo y agregación temporal de series ambientales."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import pandas as pd


def resample(
    df: pd.DataFrame,
    date_col: str,
    value_cols: Optional[List[str]] = None,
    freq: str = "D",
    agg: Union[str, Dict[str, str]] = "mean",
    min_count: int = 1,
) -> pd.DataFrame:
    """Remuestrea a una frecuencia objetivo.

    Args:
        df: DataFrame con serie temporal.
        date_col: Columna de fechas.
        value_cols: Columnas a agregar (None = todas numéricas).
        freq: Frecuencia destino (e.g. 'H', 'D', 'W', 'ME', 'YE').
        agg: Función de agregación ('mean', 'sum', 'max', 'min') o dict
             por columna {'pm25': 'mean', 'lluvia': 'sum'}.
        min_count: Mínimo de observaciones válidas para producir resultado.
    """
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.set_index(date_col).sort_index()

    targets = value_cols or data.select_dtypes(include="number").columns.tolist()
    targets = [c for c in targets if c in data.columns]

    if isinstance(agg, str):
        resampled = data[targets].resample(freq)
        result = getattr(resampled, agg)(min_count=min_count) if agg == "sum" else getattr(resampled, agg)()
    else:
        result = pd.DataFrame(index=data[targets].resample(freq).mean().index)
        for col, func in agg.items():
            if col in data.columns:
                rs = data[col].resample(freq)
                result[col] = getattr(rs, func)()

    return result.reset_index()


def align_frequencies(
    dfs: List[pd.DataFrame],
    date_cols: List[str],
    target_freq: str = "D",
    agg: str = "mean",
) -> List[pd.DataFrame]:
    """Alinea múltiples DataFrames a la misma frecuencia temporal."""
    return [resample(df, dc, freq=target_freq, agg=agg)
            for df, dc in zip(dfs, date_cols)]


def fill_missing_timestamps(
    df: pd.DataFrame,
    date_col: str,
    freq: str,
) -> pd.DataFrame:
    """Inserta timestamps faltantes con NaN para hacer la serie regular."""
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    full_idx = pd.date_range(data[date_col].min(), data[date_col].max(), freq=freq)
    data = data.set_index(date_col).reindex(full_idx)
    data.index.name = date_col
    return data.reset_index()
