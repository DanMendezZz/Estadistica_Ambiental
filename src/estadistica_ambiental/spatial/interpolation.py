"""Interpolación espacial: IDW y Kriging (ordinario, universal).

Usado para mapear contaminantes o variables hídricas entre estaciones dispersas.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def idw(
    points: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    value_col: str,
    grid_lat: np.ndarray,
    grid_lon: np.ndarray,
    power: float = 2.0,
) -> np.ndarray:
    """Interpolación por Distancia Inversa Ponderada (IDW).

    Args:
        points: DataFrame con estaciones de observación.
        grid_lat, grid_lon: Grids de puntos objetivo (meshgrid).
        power: Exponente del IDW (2 = estándar).

    Returns:
        Array 2D con valores interpolados en la grilla.
    """
    obs_lat = points[lat_col].values
    obs_lon = points[lon_col].values
    obs_val = points[value_col].values

    shape = grid_lat.shape
    flat_lat = grid_lat.ravel()
    flat_lon = grid_lon.ravel()

    result = np.zeros(len(flat_lat))
    for i, (qlat, qlon) in enumerate(zip(flat_lat, flat_lon)):
        dist = np.sqrt((obs_lat - qlat) ** 2 + (obs_lon - qlon) ** 2)
        if np.any(dist == 0):
            result[i] = obs_val[dist == 0][0]
        else:
            w = 1.0 / dist ** power
            result[i] = np.sum(w * obs_val) / np.sum(w)

    return result.reshape(shape)


def ordinary_kriging(
    points: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    value_col: str,
    grid_lat: np.ndarray,
    grid_lon: np.ndarray,
    variogram_model: str = "spherical",
) -> Tuple[np.ndarray, np.ndarray]:
    """Kriging ordinario vía pykrige.

    Requiere: pip install pykrige (incluido en [spatial]).

    Returns:
        (z_interpolated, z_variance) — ambos arrays 2D.
    """
    try:
        from pykrige.ok import OrdinaryKriging
    except ImportError:
        raise ImportError("pip install pykrige  (o pip install estadistica-ambiental[spatial])")

    ok = OrdinaryKriging(
        x=points[lon_col].values,
        y=points[lat_col].values,
        z=points[value_col].values,
        variogram_model=variogram_model,
        verbose=False,
        enable_plotting=False,
    )
    z, ss = ok.execute("grid", grid_lon[0, :], grid_lat[:, 0])
    return np.array(z), np.array(ss)
