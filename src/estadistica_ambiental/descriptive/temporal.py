"""Estadística descriptiva temporal: STL, ACF, PACF, rolling stats."""

from __future__ import annotations

from typing import Tuple

import pandas as pd


def decompose_stl(
    series: pd.Series,
    period: int,
    robust: bool = True,
) -> pd.DataFrame:
    """Descomposición STL (Seasonal-Trend decomposition using LOESS).

    Returns DataFrame con columnas: observed, trend, seasonal, residual.
    """
    from statsmodels.tsa.seasonal import STL

    stl = STL(series.dropna(), period=period, robust=robust)
    result = stl.fit()
    idx = series.dropna().index
    return pd.DataFrame(
        {
            "observed": result.observed,
            "trend": result.trend,
            "seasonal": result.seasonal,
            "residual": result.resid,
        },
        index=idx,
    )


def acf_values(series: pd.Series, nlags: int = 40) -> pd.Series:
    """Autocorrelación (ACF) hasta nlags."""
    from statsmodels.tsa.stattools import acf

    vals = acf(series.dropna(), nlags=nlags, fft=True)
    return pd.Series(vals, name="acf")


def pacf_values(series: pd.Series, nlags: int = 40) -> pd.Series:
    """Autocorrelación parcial (PACF) hasta nlags."""
    from statsmodels.tsa.stattools import pacf

    vals = pacf(series.dropna(), nlags=nlags)
    return pd.Series(vals, name="pacf")


def rolling_stats(
    series: pd.Series,
    window: int,
    stats: Tuple[str, ...] = ("mean", "std"),
) -> pd.DataFrame:
    """Estadísticas rodantes para detectar cambios de nivel o varianza."""
    roll = series.rolling(window=window, min_periods=window // 2)
    frames = {stat: getattr(roll, stat)() for stat in stats}
    return pd.DataFrame(frames)


def seasonal_summary(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "M",
) -> pd.DataFrame:
    """Agrega la serie por frecuencia (M=mensual, Y=anual, W=semanal).

    Returns: media, mediana, std, min, max por período.
    """
    data = df[[date_col, value_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.set_index(date_col).sort_index()
    resampled = data[value_col].resample(freq)
    return resampled.agg(["mean", "median", "std", "min", "max"]).round(4)
