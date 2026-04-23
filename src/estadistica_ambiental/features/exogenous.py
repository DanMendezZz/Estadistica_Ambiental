"""Preparación de variables exógenas para modelos SARIMAX y ML."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd


def align_exogenous(
    df_target: pd.DataFrame,
    df_exog: pd.DataFrame,
    date_col_target: str,
    date_col_exog: str,
    exog_cols: Optional[List[str]] = None,
    freq: str = "D",
    fill_method: str = "linear",
) -> pd.DataFrame:
    """Alinea un DataFrame de exógenas con la serie objetivo por fecha.

    Remuestrea las exógenas a la frecuencia de la serie objetivo,
    rellena faltantes y hace merge. Útil para combinar datos de
    calidad del aire con meteorología de diferente resolución temporal.
    """
    from estadistica_ambiental.preprocessing.resampling import resample

    cols = exog_cols or [c for c in df_exog.columns if c != date_col_exog]

    exog_resampled = resample(df_exog, date_col_exog, value_cols=cols, freq=freq)
    exog_resampled = exog_resampled.set_index(date_col_exog)
    exog_resampled = exog_resampled[cols].interpolate(method=fill_method)

    target = df_target.copy()
    target[date_col_target] = pd.to_datetime(target[date_col_target], errors="coerce")
    result = target.set_index(date_col_target).join(exog_resampled, how="left")
    return result.reset_index()


def create_exog_matrix(
    df: pd.DataFrame,
    cols: List[str],
    date_col: str,
    train_end_idx: int,
) -> Dict[str, pd.DataFrame]:
    """Divide las exógenas en train y future para SARIMAX."""
    data = df.set_index(date_col) if date_col in df.columns else df
    X_train  = data[cols].iloc[:train_end_idx]
    X_future = data[cols].iloc[train_end_idx:]
    return {"train": X_train, "future": X_future}


def meteorological_features(
    df: pd.DataFrame,
    temp_col: Optional[str] = None,
    wind_col: Optional[str] = None,
    humidity_col: Optional[str] = None,
    rain_col: Optional[str] = None,
) -> pd.DataFrame:
    """Genera features derivados de variables meteorológicas.

    - Índice de confort térmico (temperatura × humedad)
    - Indicador de lluvia binario
    - Velocidad de viento al cuadrado (proxy de dispersión)
    """
    result = df.copy()

    if temp_col and humidity_col and temp_col in df.columns and humidity_col in df.columns:
        result["heat_index"] = (
            -8.784695 + 1.61139411 * df[temp_col] + 2.338549 * df[humidity_col]
            - 0.14611605 * df[temp_col] * df[humidity_col]
        )

    if wind_col and wind_col in df.columns:
        result[f"{wind_col}_sq"] = df[wind_col] ** 2

    if rain_col and rain_col in df.columns:
        result["lluvia_bin"] = (df[rain_col] > 0.1).astype(int)

    return result
