"""Pruebas de hipótesis paramétricas y no paramétricas."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
from scipy import stats as spstats


def ttest(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    groups: Optional[List] = None,
    alpha: float = 0.05,
    equal_var: bool = False,
) -> dict:
    """t-test de Welch (equal_var=False) o Student entre dos grupos."""
    cats = groups or df[group_col].dropna().unique().tolist()
    if len(cats) != 2:
        raise ValueError(f"ttest requiere exactamente 2 grupos. Encontrados: {cats}")
    a = df.loc[df[group_col] == cats[0], value_col].dropna().values
    b = df.loc[df[group_col] == cats[1], value_col].dropna().values
    stat, p = spstats.ttest_ind(a, b, equal_var=equal_var)
    return {"test": "Welch t-test" if not equal_var else "Student t-test",
            "groups": cats, "statistic": round(stat, 4), "pval": round(p, 6),
            "significant": p < alpha, "alpha": alpha}


def mannwhitney(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    groups: Optional[List] = None,
    alpha: float = 0.05,
) -> dict:
    """Mann-Whitney U — alternativa no paramétrica al t-test."""
    cats = groups or df[group_col].dropna().unique().tolist()
    if len(cats) != 2:
        raise ValueError("mannwhitney requiere exactamente 2 grupos.")
    a = df.loc[df[group_col] == cats[0], value_col].dropna().values
    b = df.loc[df[group_col] == cats[1], value_col].dropna().values
    stat, p = spstats.mannwhitneyu(a, b, alternative="two-sided")
    return {"test": "Mann-Whitney U", "groups": cats,
            "statistic": round(stat, 4), "pval": round(p, 6),
            "significant": p < alpha, "alpha": alpha}


def anova(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """ANOVA de una vía para múltiples grupos."""
    groups = [df.loc[df[group_col] == g, value_col].dropna().values
              for g in df[group_col].dropna().unique()]
    stat, p = spstats.f_oneway(*groups)
    return {"test": "ANOVA una vía", "statistic": round(stat, 4),
            "pval": round(p, 6), "significant": p < alpha, "alpha": alpha}


def kruskalwallis(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Kruskal-Wallis — alternativa no paramétrica a ANOVA."""
    groups = [df.loc[df[group_col] == g, value_col].dropna().values
              for g in df[group_col].dropna().unique()]
    stat, p = spstats.kruskal(*groups)
    return {"test": "Kruskal-Wallis", "statistic": round(stat, 4),
            "pval": round(p, 6), "significant": p < alpha, "alpha": alpha}
