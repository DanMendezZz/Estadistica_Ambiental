"""Pruebas de estacionariedad para series ambientales.

ADF y KPSS son obligatorias antes de aplicar ARIMA (ADR-004).
"""

from __future__ import annotations

import logging

import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

logger = logging.getLogger(__name__)


def adf_test(series: pd.Series, alpha: float = 0.05, regression: str = "c") -> dict:
    """Augmented Dickey-Fuller.

    H0: la serie tiene raíz unitaria (no estacionaria).
    Rechazar H0 → estacionaria.
    """
    s = series.dropna()
    result = adfuller(s, regression=regression, autolag="AIC")
    stat, p, lags, nobs, crit = result[0], result[1], result[2], result[3], result[4]
    stationary = p < alpha
    if not stationary:
        logger.warning("ADF: serie NO estacionaria (p=%.4f). Considerar diferenciación.", p)
    return {
        "test":        "ADF",
        "statistic":   round(stat, 4),
        "pval":        round(p, 6),
        "lags_used":   lags,
        "n_obs":       nobs,
        "critical_1%": round(crit["1%"], 4),
        "critical_5%": round(crit["5%"], 4),
        "stationary":  stationary,
        "alpha":       alpha,
    }


def kpss_test(series: pd.Series, alpha: float = 0.05, regression: str = "c") -> dict:
    """KPSS (Kwiatkowski-Phillips-Schmidt-Shin).

    H0: la serie ES estacionaria.
    Rechazar H0 → no estacionaria.
    """
    s = series.dropna()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stat, p, lags, crit = kpss(s, regression=regression, nlags="auto")
    stationary = p >= alpha
    return {
        "test":        "KPSS",
        "statistic":   round(stat, 4),
        "pval":        round(p, 6),
        "lags_used":   lags,
        "critical_1%": round(crit["1%"], 4),
        "critical_5%": round(crit["5%"], 4),
        "stationary":  stationary,
        "alpha":       alpha,
    }


def stationarity_report(series: pd.Series, alpha: float = 0.05) -> pd.DataFrame:
    """Ejecuta ADF + KPSS y devuelve diagnóstico consolidado.

    Interpretación conjunta (tabla de Hylleberg-Mizon):
      ADF no rechaza H0 + KPSS rechaza H0 → claramente no estacionaria
      ADF rechaza H0 + KPSS no rechaza H0 → claramente estacionaria
      Ambos rechazados / ninguno rechazado → evidencia mixta
    """
    adf  = adf_test(series, alpha)
    kpss_r = kpss_test(series, alpha)

    if adf["stationary"] and kpss_r["stationary"]:
        diagnosis = "estacionaria"
    elif not adf["stationary"] and not kpss_r["stationary"]:
        diagnosis = "no estacionaria"
    else:
        diagnosis = "evidencia mixta — revisar manualmente"

    rows = [
        {**adf,    "conclusion": diagnosis},
        {**kpss_r, "conclusion": diagnosis},
    ]
    return pd.DataFrame(rows)
