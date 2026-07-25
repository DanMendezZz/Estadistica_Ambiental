"""Pruebas de normalidad y ajuste a distribuciones para datos ambientales."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
from scipy import stats as spstats

_ENV_DISTRIBUTIONS = ["norm", "lognorm", "gamma", "weibull_min", "gumbel_r", "expon"]


def normality_tests(series: pd.Series, alpha: float = 0.05) -> pd.DataFrame:
    """Batería de pruebas de normalidad: Shapiro-Wilk, K-S, Anderson-Darling."""
    s = series.dropna().values
    results = []

    # Shapiro-Wilk (mejor para n < 5000)
    if len(s) <= 5000:
        stat, p = spstats.shapiro(s)
        results.append(
            {
                "test": "Shapiro-Wilk",
                "statistic": round(stat, 4),
                "pval": round(p, 6),
                "normal": p >= alpha,
            }
        )

    # Kolmogorov-Smirnov contra normal estándarizada
    s_norm = (s - s.mean()) / s.std() if s.std() > 0 else s
    stat, p = spstats.kstest(s_norm, "norm")
    results.append(
        {
            "test": "Kolmogorov-Smirnov",
            "statistic": round(stat, 4),
            "pval": round(p, 6),
            "normal": p >= alpha,
        }
    )

    # Anderson-Darling
    res = spstats.anderson(s, dist="norm")
    # usa significancia 5% (índice 2 en la tabla de valores críticos)
    crit = res.critical_values[2]
    results.append(
        {
            "test": "Anderson-Darling",
            "statistic": round(res.statistic, 4),
            "pval": None,
            "normal": res.statistic < crit,
        }
    )

    return pd.DataFrame(results)


def fit_distribution(
    series: pd.Series,
    distributions: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Ajusta varias distribuciones teóricas y devuelve ranking por AIC."""
    s = series.dropna().values
    dists = distributions or _ENV_DISTRIBUTIONS
    rows = []

    for dist_name in dists:
        try:
            dist = getattr(spstats, dist_name)
            params = dist.fit(s)
            log_l = np.sum(dist.logpdf(s, *params))
            k = len(params)
            aic = 2 * k - 2 * log_l
            ks_stat, ks_p = spstats.kstest(s, dist_name, args=params)
            rows.append(
                {
                    "distribucion": dist_name,
                    "params": str(
                        {
                            p: round(v, 4)
                            for p, v in zip(dist.shapes.split(",") if dist.shapes else [], params)
                        }
                    ),
                    "log_likelihood": round(log_l, 2),
                    "aic": round(aic, 2),
                    "ks_stat": round(ks_stat, 4),
                    "ks_pval": round(ks_p, 6),
                    "buen_ajuste": ks_p >= 0.05,
                }
            )
        except Exception:
            continue

    return pd.DataFrame(rows).sort_values("aic")
