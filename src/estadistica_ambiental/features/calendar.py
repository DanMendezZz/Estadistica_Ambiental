"""Features de calendario para series ambientales colombianas."""

from __future__ import annotations

import pandas as pd


def add_calendar_features(
    df: pd.DataFrame,
    date_col: str,
    features: tuple = ("hour", "dayofweek", "month", "quarter", "dayofyear"),
    cyclical: bool = True,
) -> pd.DataFrame:
    """Agrega variables de calendario como features numéricas.

    Con cyclical=True codifica como seno/coseno para preservar la
    estructura cíclica (e.g. hora 23 ≈ hora 0).
    """
    import numpy as np
    result = df.copy()
    dates = pd.to_datetime(result[date_col], errors="coerce")

    _periods = {"hour": 24, "dayofweek": 7, "month": 12,
                "quarter": 4, "dayofyear": 365}

    for feat in features:
        vals = getattr(dates.dt, feat)
        if cyclical and feat in _periods:
            period = _periods[feat]
            result[f"{feat}_sin"] = np.sin(2 * np.pi * vals / period)
            result[f"{feat}_cos"] = np.cos(2 * np.pi * vals / period)
        else:
            result[feat] = vals

    return result
