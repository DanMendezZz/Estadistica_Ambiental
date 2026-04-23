"""Estadística descriptiva bivariada para datos ambientales."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
from scipy import stats as spstats


def correlation_matrix(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    method: str = "pearson",
) -> pd.DataFrame:
    """Matriz de correlación con p-valores para columnas numéricas.

    Returns DataFrame con MultiIndex (coef, pval) por par de variables.
    """
    num = df[cols].select_dtypes(include="number") if cols else df.select_dtypes(include="number")
    return num.corr(method=method)


def correlation_table(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    method: str = "pearson",
    min_abs_corr: float = 0.0,
) -> pd.DataFrame:
    """Tabla larga con pares (var1, var2, corr, pval) — más legible que la matriz."""
    num = df[cols].select_dtypes(include="number") if cols else df.select_dtypes(include="number")
    col_list = num.columns.tolist()
    rows = []
    for i, c1 in enumerate(col_list):
        for c2 in col_list[i + 1:]:
            s1 = num[c1].dropna()
            s2 = num[c2].dropna()
            common = s1.index.intersection(s2.index)
            if len(common) < 3:
                continue
            a, b = s1.loc[common].values, s2.loc[common].values
            if method == "pearson":
                r, p = spstats.pearsonr(a, b)
            elif method == "spearman":
                r, p = spstats.spearmanr(a, b)
            elif method == "kendall":
                r, p = spstats.kendalltau(a, b)
            else:
                raise ValueError("method debe ser pearson, spearman o kendall")
            if abs(r) >= min_abs_corr:
                rows.append({"var1": c1, "var2": c2,
                             "correlation": round(r, 4), "pval": round(p, 6),
                             "n": len(common)})
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("correlation", key=abs, ascending=False)


def contingency_table(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    normalize: Optional[str] = None,
) -> pd.DataFrame:
    """Tabla de contingencia. normalize: None | 'index' | 'columns' | 'all'."""
    norm = normalize if normalize is not None else False
    return pd.crosstab(df[col1], df[col2], normalize=norm)


def chi2_test(df: pd.DataFrame, col1: str, col2: str) -> dict:
    """Chi-cuadrado de independencia entre dos variables categóricas."""
    ct = contingency_table(df, col1, col2)
    chi2, p, dof, expected = spstats.chi2_contingency(ct)
    return {
        "statistic": round(chi2, 4),
        "pval":      round(p, 6),
        "dof":       dof,
        "interpretation": "dependientes" if p < 0.05 else "independientes",
    }
