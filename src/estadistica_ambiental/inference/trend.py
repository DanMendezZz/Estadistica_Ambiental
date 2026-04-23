"""Detección de tendencia en series ambientales.

Mann-Kendall + Sen's slope son el estándar en hidrología y calidad del aire
para series largas con distribución no normal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mann_kendall(series: pd.Series, alpha: float = 0.05) -> dict:
    """Test de Mann-Kendall para tendencia monotónica.

    Requiere: pip install pymannkendall
    """
    try:
        import pymannkendall as mk
    except ImportError:
        raise ImportError("Instalar pymannkendall: pip install pymannkendall")

    s = series.dropna()
    result = mk.original_test(s, alpha=alpha)
    return {
        "test":        "Mann-Kendall",
        "trend":       result.trend,           # increasing / decreasing / no trend
        "h":           result.h,               # True si hay tendencia significativa
        "pval":        round(result.p, 6),
        "z":           round(result.z, 4),
        "tau":         round(result.Tau, 4),
        "s":           result.s,
        "var_s":       result.var_s,
        "slope":       round(result.slope, 6), # Sen's slope
        "intercept":   round(result.intercept, 4),
        "alpha":       alpha,
    }


def sens_slope(series: pd.Series) -> dict:
    """Sen's slope estimator — magnitud robusta de tendencia."""
    s = series.dropna().values
    n = len(s)
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            if j != i:
                slopes.append((s[j] - s[i]) / (j - i))
    slope = float(np.median(slopes))
    intercept = float(np.median(s) - slope * np.median(np.arange(n)))
    return {"slope": round(slope, 6), "intercept": round(intercept, 4)}


def pettitt_test(series: pd.Series, alpha: float = 0.05) -> dict:
    """Test de Pettitt para detección de punto de cambio.

    Requiere: pip install pymannkendall (incluye pettitt)
    """
    try:
        import pymannkendall as mk
    except ImportError:
        raise ImportError("Instalar pymannkendall: pip install pymannkendall")

    s = series.dropna()
    result = mk.pettitt_test(s, alpha=alpha)
    cp_idx = int(result.cp)
    cp_date = s.index[cp_idx] if hasattr(s.index, '__getitem__') else cp_idx
    return {
        "test":            "Pettitt",
        "change_point_idx": cp_idx,
        "change_point_date": str(cp_date),
        "u":               result.U,
        "pval":            round(result.p, 6),
        "significant":     result.h,
        "alpha":           alpha,
    }
