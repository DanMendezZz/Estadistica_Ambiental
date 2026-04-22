"""Intervalos de confianza paramétricos y bootstrap."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as spstats


def ci_mean(series: pd.Series, confidence: float = 0.95) -> Tuple[float, float]:
    """IC paramétrico para la media (t de Student)."""
    s = series.dropna()
    n = len(s)
    se = spstats.sem(s)
    h = se * spstats.t.ppf((1 + confidence) / 2, df=n - 1)
    return (round(float(s.mean() - h), 4), round(float(s.mean() + h), 4))


def ci_median_bootstrap(
    series: pd.Series,
    confidence: float = 0.95,
    n_boot: int = 2000,
    random_state: int = 42,
) -> Tuple[float, float]:
    """IC bootstrap para la mediana (no paramétrico)."""
    rng = np.random.default_rng(random_state)
    s = series.dropna().values
    boot = rng.choice(s, size=(n_boot, len(s)), replace=True)
    medians = np.median(boot, axis=1)
    lo = (1 - confidence) / 2
    return (round(float(np.percentile(medians, lo * 100)), 4),
            round(float(np.percentile(medians, (1 - lo) * 100)), 4))


def ci_quantile_bootstrap(
    series: pd.Series,
    q: float = 0.95,
    confidence: float = 0.90,
    n_boot: int = 2000,
    random_state: int = 42,
) -> Tuple[float, float]:
    """IC bootstrap para un cuantil arbitrario (útil para excedencias de norma)."""
    rng = np.random.default_rng(random_state)
    s = series.dropna().values
    boot = rng.choice(s, size=(n_boot, len(s)), replace=True)
    quantiles = np.quantile(boot, q, axis=1)
    lo = (1 - confidence) / 2
    return (round(float(np.percentile(quantiles, lo * 100)), 4),
            round(float(np.percentile(quantiles, (1 - lo) * 100)), 4))


def ci_bootstrap(
    series: pd.Series,
    statistic: Callable,
    confidence: float = 0.95,
    n_boot: int = 2000,
    random_state: int = 42,
) -> Tuple[float, float]:
    """IC bootstrap genérico para cualquier estadístico."""
    rng = np.random.default_rng(random_state)
    s = series.dropna().values
    boot_stats = [statistic(rng.choice(s, size=len(s), replace=True)) for _ in range(n_boot)]
    lo = (1 - confidence) / 2
    return (round(float(np.percentile(boot_stats, lo * 100)), 4),
            round(float(np.percentile(boot_stats, (1 - lo) * 100)), 4))


def exceedance_probability(
    series: pd.Series,
    threshold: float,
) -> dict:
    """Probabilidad de excedencia de un umbral (e.g. norma ambiental).

    Útil para PM2.5 vs norma OMS (15 µg/m³) o norma colombiana (37 µg/m³).
    """
    s = series.dropna()
    n = len(s)
    n_exceed = int((s > threshold).sum())
    p = n_exceed / n if n else 0.0
    ci = ci_quantile_bootstrap(series, q=threshold / s.max() if s.max() > 0 else 0.95)
    return {
        "threshold":     threshold,
        "n_exceedances": n_exceed,
        "pct_exceed":    round(p * 100, 2),
        "return_period_days": round(1 / p, 1) if p > 0 else None,
    }
