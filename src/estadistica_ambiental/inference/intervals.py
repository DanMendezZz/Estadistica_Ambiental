"""Intervalos de confianza paramétricos y bootstrap, y análisis de excedencias normativas."""

from __future__ import annotations

from typing import Callable, Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats as spstats

from estadistica_ambiental.config import (
    NORMA_AGUA_POTABLE,
    NORMA_CO,
    NORMA_OMS,
    NORMA_VERTIMIENTOS,
)


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
    return (
        round(float(np.percentile(medians, lo * 100)), 4),
        round(float(np.percentile(medians, (1 - lo) * 100)), 4),
    )


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
    return (
        round(float(np.percentile(quantiles, lo * 100)), 4),
        round(float(np.percentile(quantiles, (1 - lo) * 100)), 4),
    )


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
    return (
        round(float(np.percentile(boot_stats, lo * 100)), 4),
        round(float(np.percentile(boot_stats, (1 - lo) * 100)), 4),
    )


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
    return {
        "threshold": threshold,
        "n_exceedances": n_exceed,
        "pct_exceed": round(p * 100, 2),
        "return_period_days": round(1 / p, 1) if p > 0 else None,
    }


# ---------------------------------------------------------------------------
# Mapeo variable → normas colombianas relevantes
# Formato: {nombre_variable: [(norma_label, norma_dict, key_en_norma_dict)]}
# ---------------------------------------------------------------------------
_NORMA_MAP: Dict[str, list[tuple[str, dict, str]]] = {
    "pm25": [
        ("Res. 2254/2017 — 24h", NORMA_CO, "pm25_24h"),
        ("Res. 2254/2017 — anual", NORMA_CO, "pm25_annual"),
        ("OMS 2021 — 24h", NORMA_OMS, "pm25_24h"),
        ("OMS 2021 — anual", NORMA_OMS, "pm25_annual"),
    ],
    "pm10": [
        ("Res. 2254/2017 — 24h", NORMA_CO, "pm10_24h"),
        ("Res. 2254/2017 — anual", NORMA_CO, "pm10_annual"),
        ("OMS 2021 — 24h", NORMA_OMS, "pm10_24h"),
        ("OMS 2021 — anual", NORMA_OMS, "pm10_annual"),
    ],
    "o3": [("Res. 2254/2017 — 8h", NORMA_CO, "o3_8h")],
    "no2": [
        ("Res. 2254/2017 — anual", NORMA_CO, "no2_annual"),
        ("OMS 2021 — anual", NORMA_OMS, "no2_annual"),
    ],
    "so2": [("Res. 2254/2017 — 24h", NORMA_CO, "so2_24h")],
    "co": [("Res. 2254/2017 — 8h", NORMA_CO, "co_8h")],
    "od": [("Res. 2115/2007 — agua potable min", NORMA_AGUA_POTABLE, "od_min")],
    "dbo": [
        ("Res. 2115/2007 — agua potable", NORMA_AGUA_POTABLE, "dbo5_max"),
        ("Res. 631/2015 — vertimiento", NORMA_VERTIMIENTOS, "dbo5_max"),
    ],
    "dbo5": [
        ("Res. 2115/2007 — agua potable", NORMA_AGUA_POTABLE, "dbo5_max"),
        ("Res. 631/2015 — vertimiento", NORMA_VERTIMIENTOS, "dbo5_max"),
    ],
    "dqo": [("Res. 631/2015 — vertimiento", NORMA_VERTIMIENTOS, "dqo_max")],
    "sst": [("Res. 631/2015 — vertimiento", NORMA_VERTIMIENTOS, "sst_max")],
    "ph": [
        ("Res. 2115/2007 — agua potable min", NORMA_AGUA_POTABLE, "ph_min"),
        ("Res. 2115/2007 — agua potable max", NORMA_AGUA_POTABLE, "ph_max"),
        ("Res. 631/2015 — vertimiento min", NORMA_VERTIMIENTOS, "ph_min"),
        ("Res. 631/2015 — vertimiento max", NORMA_VERTIMIENTOS, "ph_max"),
    ],
    "conductividad": [("Res. 2115/2007 — agua potable", NORMA_AGUA_POTABLE, "conductividad_max")],
    "nitratos": [("Res. 2115/2007 — agua potable", NORMA_AGUA_POTABLE, "nitratos_max")],
}


def exceedance_report(
    series: pd.Series,
    variable: str,
    frecuencia: str = "24h",
) -> pd.DataFrame:
    """Genera un reporte de cumplimiento normativo para una variable ambiental colombiana.

    Compara la serie contra todas las normas colombianas relevantes para esa variable.

    Args:
        series: Serie de observaciones (ya deben estar en la unidad correcta).
        variable: Nombre de la variable ('pm25', 'dbo5', 'ph', etc.).
        frecuencia: Frecuencia de los datos ('1h', '24h', 'anual', etc.) — informativo.

    Returns:
        DataFrame con una fila por norma, columnas:
        norma, umbral, n_exceedances, pct_exceed, cumple, return_period_days.
    """
    variable_key = variable.lower().replace(" ", "_")
    normas = _NORMA_MAP.get(variable_key, [])
    if not normas:
        return pd.DataFrame(
            columns=[
                "norma",
                "umbral",
                "n_exceedances",
                "pct_exceed",
                "cumple",
                "return_period_days",
            ]
        )

    rows = []
    s = series.dropna()
    n = len(s)

    for label, norma_dict, key in normas:
        umbral = norma_dict.get(key)
        if umbral is None:
            continue
        # Para umbrales mínimos (od_min, ph_min) la excedencia es por debajo
        is_min = key.endswith("_min")
        if is_min:
            n_exceed = int((s < umbral).sum())
        else:
            n_exceed = int((s > umbral).sum())
        p = n_exceed / n if n else 0.0
        rows.append(
            {
                "norma": label,
                "umbral": umbral,
                "tipo": "mínimo" if is_min else "máximo",
                "n_exceedances": n_exceed,
                "pct_exceed": round(p * 100, 2),
                "cumple": n_exceed == 0,
                "return_period_days": round(1 / p, 1) if p > 0 else None,
            }
        )

    return pd.DataFrame(rows)
