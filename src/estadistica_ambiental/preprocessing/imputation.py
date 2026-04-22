"""Imputación de datos faltantes para series ambientales.

Estrategias ordenadas de menor a mayor complejidad:
  forward_fill → linear → mean/median → rolling_mean → kalman → mice
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def impute(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    method: str = "linear",
    **kwargs,
) -> pd.DataFrame:
    """Aplica el método de imputación seleccionado a las columnas numéricas.

    Métodos disponibles:
      'ffill'        Forward fill (última observación conocida).
      'bfill'        Backward fill.
      'linear'       Interpolación lineal temporal.
      'mean'         Reemplaza por media de la columna.
      'median'       Reemplaza por mediana de la columna.
      'rolling_mean' Media rodante (window kwarg, default=24).
      'kalman'       Filtro de Kalman simple (requiere pykalman).
      'mice'         Imputación múltiple (requiere scikit-learn).
    """
    result = df.copy()
    targets = cols or result.select_dtypes(include="number").columns.tolist()
    targets = [c for c in targets if c in result.columns]

    _dispatch = {
        "ffill":        _ffill,
        "bfill":        _bfill,
        "linear":       _linear,
        "mean":         _mean,
        "median":       _median,
        "rolling_mean": _rolling_mean,
        "kalman":       _kalman,
        "mice":         _mice,
    }
    if method not in _dispatch:
        raise ValueError(f"Método '{method}' no soportado. Opciones: {list(_dispatch)}")

    fn = _dispatch[method]
    for col in targets:
        n_before = int(result[col].isna().sum())
        result[col] = fn(result[col], **kwargs)
        n_after = int(result[col].isna().sum())
        if n_before:
            logger.info("'%s' [%s]: %d faltantes → %d restantes", col, method, n_before, n_after)

    return result


# ---------------------------------------------------------------------------
# Métodos individuales
# ---------------------------------------------------------------------------

def _ffill(s: pd.Series, **_) -> pd.Series:
    return s.ffill()


def _bfill(s: pd.Series, **_) -> pd.Series:
    return s.bfill()


def _linear(s: pd.Series, **_) -> pd.Series:
    return s.interpolate(method="linear", limit_direction="both")


def _mean(s: pd.Series, **_) -> pd.Series:
    return s.fillna(s.mean())


def _median(s: pd.Series, **_) -> pd.Series:
    return s.fillna(s.median())


def _rolling_mean(s: pd.Series, window: int = 24, **_) -> pd.Series:
    roll = s.rolling(window=window, min_periods=1, center=True).mean()
    return s.fillna(roll)


def _kalman(s: pd.Series, **_) -> pd.Series:
    """Filtro de Kalman simple para series univariadas con ruido gaussiano."""
    try:
        from pykalman import KalmanFilter
    except ImportError:
        logger.warning("pykalman no instalado — usando interpolación lineal como fallback")
        return _linear(s)

    values = s.values.astype(float)
    obs_mask = ~np.isnan(values)
    kf = KalmanFilter(
        transition_matrices=[1],
        observation_matrices=[1],
        initial_state_mean=np.nanmean(values),
        em_vars=["transition_covariance", "observation_covariance"],
    )
    masked = np.ma.array(values, mask=~obs_mask)
    state_means, _ = kf.smooth(masked)
    result = s.copy()
    result[~obs_mask] = state_means[~obs_mask, 0]
    return result


def _mice(df_col_context: pd.Series, **_) -> pd.Series:
    """MICE via IterativeImputer de scikit-learn (columna individual)."""
    try:
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer
    except ImportError:
        logger.warning("scikit-learn no instalado — usando interpolación lineal como fallback")
        return _linear(df_col_context)

    arr = df_col_context.values.reshape(-1, 1)
    imp = IterativeImputer(random_state=42, max_iter=10)
    result = imp.fit_transform(arr).flatten()
    return pd.Series(result, index=df_col_context.index, name=df_col_context.name)
