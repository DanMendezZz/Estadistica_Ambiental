"""Estadística descriptiva univariada para variables ambientales."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


def summarize(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    group_col: Optional[str] = None,
    percentiles: List[float] = [0.05, 0.25, 0.50, 0.75, 0.95],
) -> pd.DataFrame:
    """Resumen estadístico completo para columnas numéricas.

    Incluye: n, media, mediana, moda, desv. estándar, varianza, CV,
    IQR, MAD, asimetría, curtosis, percentiles, min, max.
    Soporta agrupación por variable categórica (e.g. estación).
    """
    num_cols = cols or df.select_dtypes(include="number").columns.tolist()
    num_cols = [c for c in num_cols if c in df.columns]

    if group_col and group_col in df.columns:
        groups = df[group_col].dropna().unique()
        frames = []
        for grp in sorted(groups):
            sub = df[df[group_col] == grp]
            stats = _compute_stats(sub[num_cols], percentiles)
            stats.insert(0, "grupo", str(grp))
            frames.append(stats)
        return pd.concat(frames, ignore_index=True)

    return _compute_stats(df[num_cols], percentiles)


def _compute_stats(df: pd.DataFrame, percentiles: List[float]) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col].dropna()
        n = len(s)
        if n == 0:
            continue
        mean = s.mean()
        std = s.std()
        row: Dict[str, Union[str, float, int]] = {
            "variable": col,
            "n": n,
            "n_missing": int(df[col].isna().sum()),
            "mean": round(mean, 4),
            "median": round(s.median(), 4),
            "mode": round(float(s.mode().iloc[0]), 4) if len(s.mode()) else np.nan,
            "std": round(std, 4),
            "variance": round(s.var(), 4),
            "cv_%": round(std / mean * 100, 2) if mean != 0 else np.nan,
            "iqr": round(float(s.quantile(0.75) - s.quantile(0.25)), 4),
            "mad": round(float((s - s.median()).abs().median()), 4),
            "skewness": round(float(s.skew()), 4),
            "kurtosis": round(float(s.kurtosis()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
        }
        for p in percentiles:
            row[f"p{int(p * 100)}"] = round(float(s.quantile(p)), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def frequency_table(series: pd.Series, normalize: bool = True) -> pd.DataFrame:
    """Tabla de frecuencias para variable categórica u ordinal."""
    counts = series.value_counts(dropna=False)
    pct = series.value_counts(normalize=True, dropna=False) * 100
    df = pd.DataFrame({"n": counts, "pct": pct.round(2)})
    df.index.name = series.name or "valor"
    return df.reset_index()
