"""
Detección de anomalías en predicciones de modelos.
Adaptado de tesis-renare-v4/residual_analysis.py por Dan Méndez — 2026-04-22

El error relativo |real - pred| / (|real| + 1) es estable con valores
cercanos a cero y negativos, lo que lo hace adecuado para variables
ambientales de escala variable (emisiones, caudal, concentraciones).
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np
import pandas as pd


def detect_anomalies(
    y_true: Union[np.ndarray, pd.Series],
    y_pred: Union[np.ndarray, pd.Series],
    threshold: float = 2.0,
    relative: bool = True,
    index: Optional[pd.Index] = None,
) -> pd.DataFrame:
    """Detecta registros donde el error del modelo supera threshold desviaciones estándar.

    Lógica:
        - Si relative=True:  error_rel = |real - pred| / (|real| + 1)
        - Si relative=False: error_rel = |real - pred|  (error absoluto)
        - Anomalía: error_rel > mean(error_rel) + threshold * std(error_rel)

    Args:
        y_true:    valores reales observados.
        y_pred:    valores predichos por el modelo.
        threshold: número de desviaciones estándar sobre la media para declarar anomalía.
        relative:  si True usa error relativo (recomendado para series con ceros).
        index:     índice opcional (ej. fechas) para el DataFrame resultante.

    Returns:
        DataFrame con columnas:
            - y_true:     valor real
            - y_pred:     valor predicho
            - error:      residual (y_true - y_pred)
            - error_rel:  error relativo o absoluto según parámetro relative
            - is_anomaly: booleano — True si supera el umbral
        Ordenado por error_rel descendente.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true y y_pred deben tener la misma longitud ({len(y_true)} vs {len(y_pred)})."
        )

    error = y_true - y_pred

    if relative:
        error_rel = np.abs(error) / (np.abs(y_true) + 1.0)
    else:
        error_rel = np.abs(error)

    # Usar nanmean/nanstd para que gaps NaN en series ambientales no anulen el umbral
    umbral = float(np.nanmean(error_rel) + threshold * np.nanstd(error_rel))
    is_anomaly = error_rel > umbral

    idx = index if index is not None else pd.RangeIndex(len(y_true))

    df = pd.DataFrame(
        {
            "y_true": y_true,
            "y_pred": y_pred,
            "error": error,
            "error_rel": error_rel,
            "is_anomaly": is_anomaly,
        },
        index=idx,
    )
    # Guardar umbral y threshold para que anomaly_summary reporte valores exactos
    df.attrs["umbral"] = umbral
    df.attrs["threshold"] = threshold

    return df.sort_values("error_rel", ascending=False)


def anomaly_summary(anomaly_df: pd.DataFrame, threshold: float = 2.0) -> dict:
    """Resumen estadístico del DataFrame producido por detect_anomalies().

    Args:
        anomaly_df: salida de detect_anomalies().
        threshold:  mismo valor usado en detect_anomalies(); se usa solo como
                    fallback si anomaly_df.attrs no tiene 'umbral' guardado.

    Returns:
        dict con:
            - n_total:         número total de registros evaluados
            - n_anomalies:     cantidad de anomalías detectadas
            - pct_anomalies:   porcentaje de anomalías sobre el total
            - mean_error_rel:  error relativo medio (toda la serie)
            - std_error_rel:   desviación estándar del error relativo (ddof=0)
            - threshold_value: umbral exacto aplicado en detect_anomalies
            - max_error_rel:   error relativo máximo observado
    """
    n_total = len(anomaly_df)
    n_anomalies = int(anomaly_df["is_anomaly"].sum())
    pct = n_anomalies / n_total * 100 if n_total > 0 else 0.0

    err_rel = anomaly_df["error_rel"].values
    mean_er = float(np.nanmean(err_rel))
    std_er = float(np.nanstd(err_rel))  # ddof=0, igual que detect_anomalies

    # Preferir el umbral exacto almacenado en attrs; recalcular si no está
    threshold_val = anomaly_df.attrs.get(
        "umbral",
        mean_er + anomaly_df.attrs.get("threshold", threshold) * std_er,
    )

    return {
        "n_total": n_total,
        "n_anomalies": n_anomalies,
        "pct_anomalies": round(pct, 2),
        "mean_error_rel": round(mean_er, 4),
        "std_error_rel": round(std_er, 4),
        "threshold_value": round(float(threshold_val), 4),
        "max_error_rel": round(float(np.nanmax(err_rel)), 4),
    }
