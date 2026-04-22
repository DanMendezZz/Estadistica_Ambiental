"""
Métricas de evaluación para modelos ambientales.
Adaptado de boa-sarima-forecaster/metrics.py por Dan Méndez — 2026-04-22

Extiende las métricas financieras originales con NSE y KGE (hidrología)
y desactiva RMSLE para variables que pueden ser negativas (ADR-003).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


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
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0


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
    return float(1 - np.sum((y_true - y_pred) ** 2) / denom) if denom > 0 else -np.inf


def kge(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Kling-Gupta Efficiency. Rango (-∞, 1]; 1=perfecto."""
    r = np.corrcoef(y_true, y_pred)[0, 1]
    alpha = np.std(y_pred) / np.std(y_true) if np.std(y_true) > 0 else np.nan
    beta  = np.mean(y_pred) / np.mean(y_true) if np.mean(y_true) != 0 else np.nan
    return float(1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))


def pbias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Percent Bias (%). Positivo = sobreestimación."""
    return float(np.sum(y_true - y_pred) / np.sum(y_true) * 100) if np.sum(y_true) != 0 else np.nan


# ---------------------------------------------------------------------------
# Suite completa
# ---------------------------------------------------------------------------

def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    domain: str = "general",
    y_train: Optional[np.ndarray] = None,
) -> dict:
    """Calcula todas las métricas relevantes según el dominio.

    Args:
        domain: 'general' | 'hydrology' | 'air_quality'
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true, y_pred = y_true[mask], y_pred[mask]

    result = {
        "mae":   round(mae(y_true, y_pred), 4),
        "rmse":  round(rmse(y_true, y_pred), 4),
        "r2":    round(r2(y_true, y_pred), 4),
        "mase":  round(mase(y_true, y_pred, y_train), 4),
    }

    if domain in ("air_quality", "general") and (y_true >= 0).all():
        result["smape"] = round(smape(y_true, y_pred), 4)
        result["mape"]  = round(mape(y_true, y_pred), 4)

    if domain == "hydrology":
        result["nse"]   = round(nse(y_true, y_pred), 4)
        result["kge"]   = round(kge(y_true, y_pred), 4)
        result["pbias"] = round(pbias(y_true, y_pred), 4)

    return result


def compare_models(results: dict) -> pd.DataFrame:
    """Tabla comparativa de modelos. results = {model_name: metrics_dict}."""
    return pd.DataFrame(results).T.sort_values("rmse")
