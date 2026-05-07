"""
Métricas de evaluación para modelos ambientales.
Adaptado de boa-sarima-forecaster/metrics.py por Dan Méndez — 2026-04-22

Extiende las métricas financieras originales con NSE y KGE (hidrología)
y desactiva RMSLE para variables que pueden ser negativas (ADR-003).
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Métricas básicas
# ---------------------------------------------------------------------------


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean((y_true - y_pred) ** 2))


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """sMAPE — solo válido cuando y_true ≥ 0."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(denom == 0, 0.0, np.abs(y_true - y_pred) / denom)
    return float(np.mean(s) * 100)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """MAPE — solo válido cuando y_true ≠ 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(y_true == 0, 0.0, np.abs((y_true - y_pred) / y_true))
    return float(np.mean(m) * 100)


def mase(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: Optional[np.ndarray] = None,
    m: int = 1,
) -> float:
    """Mean Absolute Scaled Error. Requiere serie de entrenamiento o usa naive."""
    if y_train is None:
        y_train = y_true
    naive_mae = np.mean(np.abs(np.diff(y_train, n=m)))
    return mae(y_true, y_pred) / naive_mae if naive_mae > 0 else np.nan


# ---------------------------------------------------------------------------
# Métricas hidrológicas (estándar para caudal y variables hídricas)
# ---------------------------------------------------------------------------


def nse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Nash-Sutcliffe Efficiency. Rango (-∞, 1]; 1=perfecto, <0=peor que media."""
    denom = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1 - np.sum((y_true - y_pred) ** 2) / denom) if denom > 0 else float("nan")


def kge(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Kling-Gupta Efficiency. Rango (-∞, 1]; 1=perfecto."""
    r = np.corrcoef(y_true, y_pred)[0, 1]
    std_true = np.std(y_true)
    mean_true = np.mean(y_true)
    if std_true < 1e-10:
        logger.warning("kge: std(y_true) ≈ 0 — serie constante o fold degenerado. Retorna nan.")
        return float("nan")
    if abs(mean_true) < 1e-10:
        logger.warning("kge: mean(y_true) ≈ 0 — beta indefinido. Retorna nan.")
        return float("nan")
    alpha = float(np.std(y_pred) / std_true)
    beta = float(np.mean(y_pred) / mean_true)
    return float(1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))


def pbias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Percent Bias (%). Positivo = sobreestimación."""
    total = np.sum(y_true)
    return float((total - np.sum(y_pred)) / total * 100) if abs(total) >= 1e-10 else float("nan")


# ---------------------------------------------------------------------------
# Suite completa
# ---------------------------------------------------------------------------


def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    domain: str = "general",
    y_train: Optional[np.ndarray] = None,
    ica_breakpoints: Optional[dict] = None,
    pollutant: str = "pm25",
) -> dict:
    """Calcula todas las métricas relevantes según el dominio.

    Args:
        domain: 'general' | 'hydrology' | 'air_quality'
        y_train: serie de entrenamiento para MASE (opcional).
        ica_breakpoints: puntos de corte ICA custom para hit_rate_ica.
            Si se provee, tiene precedencia sobre ``pollutant``.
        pollutant: contaminante para seleccionar breakpoints ICA correctos
            ('pm25', 'pm10', 'o3', 'no2', 'so2', 'co'). Solo aplica con
            domain='air_quality' y sin ica_breakpoints explícito.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true, y_pred = y_true[mask], y_pred[mask]

    if len(y_true) == 0:
        raise ValueError("No quedan observaciones válidas después de filtrar NaN.")

    result = {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "r2": r2(y_true, y_pred),
        "mase": mase(y_true, y_pred, y_train),
        "nrmse": nrmse(y_true, y_pred),
    }

    if domain in ("air_quality", "general") and (y_true >= 0).all():
        result["smape"] = smape(y_true, y_pred)
        result["mape"] = mape(y_true, y_pred)

    if domain == "hydrology":
        result["nse"] = nse(y_true, y_pred)
        result["kge"] = kge(y_true, y_pred)
        result["pbias"] = pbias(y_true, y_pred)

    if domain == "air_quality":
        result["hit_rate_ica"] = hit_rate_ica(
            y_true, y_pred, breakpoints=ica_breakpoints, pollutant=pollutant
        )

    return result


# Sentido de optimización por métrica (True = mayor es mejor)
METRIC_DIRECTION: dict[str, bool] = {
    "mae": False,
    "rmse": False,
    "mse": False,
    "r2": True,
    "smape": False,
    "mape": False,
    "mase": False,
    "nrmse": False,
    "nse": True,
    "kge": True,
    "pbias": False,
    "hit_rate_ica": True,
}


def compare_models(results: dict) -> pd.DataFrame:
    """Tabla comparativa de modelos. results = {model_name: metrics_dict}."""
    return pd.DataFrame(results).T.sort_values("rmse")


# ---------------------------------------------------------------------------
# Métricas escala-invariante y calidad del aire
# ---------------------------------------------------------------------------


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """RMSE normalizado por desviación estándar. Estable con ceros y negativos.

    NRMSE = RMSE / std(y_true). Rango (0, inf), escala-invariante.
    NRMSE < 1.0 indica mejor desempeño que el modelo de la media.
    Reemplaza sMAPE cuando la serie contiene valores cercanos a cero.
    Retorna nan si y_true tiene varianza cero (sensor saturado, fold degenerado).
    """
    std_y = float(np.std(y_true))
    if std_y < 1e-10:
        return float("nan")
    return float(rmse(y_true, y_pred) / std_y)


def _get_ica_breakpoints(pollutant: str) -> dict:
    """Devuelve breakpoints ICA en formato {categoría: (lo, hi)} para el contaminante dado.

    Consume `config.ICA_BREAKPOINTS` y `config.ICA_LABELS` (Res. 2254/2017),
    fuente única de verdad centralizada según ADR-005.
    Si el contaminante no se reconoce, usa PM2.5 silenciosamente.
    """
    from estadistica_ambiental.config import ICA_BREAKPOINTS, ICA_LABELS

    key = pollutant.lower().replace(".", "").replace("₂", "2").replace("₃", "3")
    bins = ICA_BREAKPOINTS.get(key, ICA_BREAKPOINTS["pm25"])
    return {label: (bins[i], bins[i + 1]) for i, label in enumerate(ICA_LABELS)}


def _categorize_ica(values: np.ndarray, breakpoints: dict) -> np.ndarray:
    """Asigna categoría ICA a cada valor del arreglo."""
    cats = np.full(len(values), "", dtype=object)
    for label, (lo, hi) in breakpoints.items():
        mask = (values > lo) & (values <= hi)
        cats[mask] = label
    return cats


def hit_rate_ica(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    breakpoints: Optional[dict] = None,
    pollutant: str = "pm25",
) -> float:
    """Porcentaje de predicciones en la misma categoría ICA que el valor real.

    Args:
        y_true: valores reales de concentración (µg/m³, o mg/m³ para CO).
        y_pred: valores predichos de concentración.
        breakpoints: dict con {categoria: (min_excl, max_incl)} personalizado.
            Si se provee, tiene precedencia sobre ``pollutant``.
        pollutant: contaminante para seleccionar breakpoints de Res. 2254/2017.
            Opciones: 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co'. Default: 'pm25'.

    Returns:
        float entre 0.0 y 100.0 (porcentaje de coincidencias de categoría).
    """
    bp = breakpoints if breakpoints is not None else _get_ica_breakpoints(pollutant)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true, y_pred = y_true[mask], y_pred[mask]
    if len(y_true) == 0:
        return float("nan")
    cats_true = _categorize_ica(y_true, bp)
    cats_pred = _categorize_ica(y_pred, bp)
    return float(np.mean(cats_true == cats_pred) * 100)
