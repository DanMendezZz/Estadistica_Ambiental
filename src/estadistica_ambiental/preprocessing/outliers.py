"""Detección y tratamiento OPCIONAL de outliers en series ambientales.

Por defecto solo detecta y marca (ADR-002): los picos ambientales son señal real.
El clipping es opt-in explícito con treat=True.

Funciones:
  - flag_outliers: detección puntual univariada (IQR / z-score / modified z-score).
  - detect_regional_episodes: episodios sostenidos con confirmación espacial entre
    estaciones vecinas. Variante genérica de la lógica de calidad del aire,
    aplicable a cualquier variable ambiental (PM2.5, caudal, temperatura, etc.).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def flag_outliers(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    method: str = "iqr",
    threshold: float = 1.5,
    treat: bool = False,
    treatment: str = "clip",
) -> pd.DataFrame:
    """Marca columnas con outliers. Opcionalmente los trata.

    Args:
        df: DataFrame de entrada.
        cols: Columnas a analizar (None = todas numéricas).
        method: 'iqr' | 'zscore' | 'modified_zscore'.
        threshold: Multiplicador IQR o número de desviaciones.
        treat: Si True aplica treatment (clip o nan). Default False (ADR-002).
        treatment: 'clip' recorta a los límites | 'nan' reemplaza por NaN.

    Returns:
        DataFrame con columnas adicionales '<col>_outlier' (bool).
    """
    result = df.copy()
    targets = cols or result.select_dtypes(include="number").columns.tolist()
    targets = [c for c in targets if c in result.columns]

    for col in targets:
        s = result[col]
        lo, hi = _compute_bounds(s.dropna(), method, threshold)
        mask = (s < lo) | (s > hi)
        result[f"{col}_outlier"] = mask
        n = int(mask.sum())

        if n > 0:
            logger.info("'%s': %d outliers detectados por %s [%.2f, %.2f]", col, n, method, lo, hi)

        if treat and n > 0:
            if treatment == "clip":
                result[col] = s.clip(lower=lo, upper=hi)
                logger.warning(
                    "'%s': %d valores recortados a [%.2f, %.2f] — ADR-002", col, n, lo, hi
                )
            elif treatment == "nan":
                result.loc[mask, col] = np.nan
                logger.warning("'%s': %d valores reemplazados por NaN — ADR-002", col, n)

    return result


def _compute_bounds(s: pd.Series, method: str, threshold: float) -> Tuple[float, float]:
    if method == "iqr":
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        return q1 - threshold * iqr, q3 + threshold * iqr

    if method == "zscore":
        mu, sigma = s.mean(), s.std()
        return mu - threshold * sigma, mu + threshold * sigma

    if method == "modified_zscore":
        median = s.median()
        mad = (s - median).abs().median() * 1.4826
        return median - threshold * mad, median + threshold * mad

    raise ValueError(f"method debe ser 'iqr', 'zscore' o 'modified_zscore'. Recibido: '{method}'")


# ---------------------------------------------------------------------------
# Episodios regionales con confirmación espacial (M-01, feedback CAR §3.1.A)
# ---------------------------------------------------------------------------


def _haversine_km_arr(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km entre dos puntos geográficos (Haversine)."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    return float(2.0 * R * np.arcsin(np.sqrt(a)))


def detect_regional_episodes(
    df: pd.DataFrame,
    value_col: str,
    station_col: str,
    datetime_col: str,
    lat_col: str,
    lon_col: str,
    iqr_hard_mult: float = 3.0,
    iqr_soft_mult: float = 1.5,
    min_duration_hours: int = 4,
    neighbor_radius_km: float = 50.0,
    min_neighbors_confirmed: int = 1,
    max_gap_hours: float = 1.5,
) -> pd.DataFrame:
    """Detecta episodios regionales sostenidos con confirmación espacial.

    Algoritmo (variante genérica de ``flag_spatial_episodes`` para cualquier
    variable ambiental, validado en producción CAR §3.1.A):

      1. Por estación: calcular Q1, Q3, IQR sobre los valores no-NaN.
      2. Marcar como candidatos los puntos > Q3 + ``iqr_hard_mult`` × IQR.
      3. Agrupar candidatos consecutivos en episodios (brecha máxima
         ``max_gap_hours``) y descartar episodios con duración < ``min_duration_hours``.
      4. Para cada episodio sobreviviente, validar contra estaciones vecinas
         dentro de ``neighbor_radius_km`` (Haversine): se requieren al menos
         ``min_neighbors_confirmed`` vecinos con valor > Q3_vecino + ``iqr_soft_mult`` × IQR
         en la misma ventana temporal.
      5. Episodios confirmados → ``flag_episode = "regional"`` (señal real).
         Candidatos no confirmados → ``flag_episode = "puntual"`` (probable
         falla de sensor o variabilidad local).

    A diferencia de ``flag_spatial_episodes`` (calidad del aire), esta función:
      - NO modifica los valores (no imputa, no recorta).
      - NO aplica cap absoluto (eso es decisión opt-in del usuario).
      - NO segmenta por mes (asume estacionariedad por estación).
      - Es genérica: aplica a PM2.5, caudal, temperatura, precipitación, etc.

    Args:
        df: DataFrame con observaciones de múltiples estaciones.
        value_col: Columna con la variable a evaluar.
        station_col: Columna identificadora de estación.
        datetime_col: Columna temporal (datetime o parseable).
        lat_col: Latitud de la estación (decimal, WGS-84).
        lon_col: Longitud de la estación (decimal, WGS-84).
        iqr_hard_mult: Multiplicador IQR para umbral fuerte (default 3.0).
        iqr_soft_mult: Multiplicador IQR para confirmación en vecinos (default 1.5).
        min_duration_hours: Duración mínima del episodio en horas (default 4).
        neighbor_radius_km: Radio de búsqueda de vecinas en km (default 50).
        min_neighbors_confirmed: Vecinas mínimas con elevación simultánea para
            confirmar el episodio (default 1). Si una estación queda aislada
            (ningún vecino dentro del radio), el criterio temporal basta.
        max_gap_hours: Brecha máxima en horas para considerar candidatos como
            parte del mismo episodio (default 1.5 — tolera 1 dato faltante).

    Returns:
        Copia del DataFrame con columna adicional ``flag_episode`` ∈
        ``{"original", "puntual", "regional"}``.

    Raises:
        KeyError: Si alguna columna requerida no existe en ``df``.

    Example:
        >>> df = pd.DataFrame({
        ...     "fecha": pd.date_range("2024-01-01", periods=10, freq="h").tolist() * 2,
        ...     "estacion": ["A"] * 10 + ["B"] * 10,
        ...     "lat": [4.6] * 10 + [4.65] * 10,
        ...     "lon": [-74.1] * 10 + [-74.15] * 10,
        ...     "pm25": [...]  # con pico sostenido en ambas estaciones
        ... })
        >>> out = detect_regional_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        >>> out["flag_episode"].value_counts()
    """
    required = {value_col, station_col, datetime_col, lat_col, lon_col}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Columnas requeridas no encontradas en df: {missing}")

    result = df.copy()
    result[datetime_col] = pd.to_datetime(result[datetime_col])
    result["flag_episode"] = "original"

    # --- mapa de coordenadas y vecindario por estación ---
    coords_df = (
        result[[station_col, lat_col, lon_col]]
        .drop_duplicates(subset=[station_col])
        .set_index(station_col)
    )
    coords: Dict[str, Tuple[float, float]] = {
        s: (float(row[lat_col]), float(row[lon_col])) for s, row in coords_df.iterrows()
    }
    stations = list(coords.keys())
    neighbors: Dict[str, List[str]] = {s: [] for s in stations}
    for i, s1 in enumerate(stations):
        lat1, lon1 = coords[s1]
        for s2 in stations[i + 1 :]:
            lat2, lon2 = coords[s2]
            if _haversine_km_arr(lat1, lon1, lat2, lon2) <= neighbor_radius_km:
                neighbors[s1].append(s2)
                neighbors[s2].append(s1)

    # --- pivot estación×tiempo para validación de vecinos ---
    pivot = (
        result[[datetime_col, station_col, value_col]]
        .groupby([datetime_col, station_col])[value_col]
        .mean()
        .unstack(station_col)
        .sort_index()
    )

    n_regional = 0
    n_puntual = 0

    for station in stations:
        mask_st = result[station_col] == station
        serie = result.loc[mask_st & result[value_col].notna(), value_col]
        if len(serie) < 10:
            logger.debug("'%s': estación '%s' con <10 obs, omitida.", value_col, station)
            continue

        q1 = serie.quantile(0.25)
        q3 = serie.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue

        hard_threshold = q3 + iqr_hard_mult * iqr
        candidatos_mask = mask_st & (result[value_col] > hard_threshold) & result[value_col].notna()
        idx_cand = result.index[candidatos_mask]
        if len(idx_cand) == 0:
            continue

        ts_df = (
            result.loc[idx_cand, [datetime_col]]
            .sort_values(datetime_col)
            .reset_index()
            .rename(columns={"index": "orig_idx"})
        )
        ts_df["gap_h"] = ts_df[datetime_col].diff().dt.total_seconds().fillna(0.0) / 3600.0
        ts_df["ep_id"] = (ts_df["gap_h"] > max_gap_hours).cumsum()

        vecinos_estacion = [v for v in neighbors[station] if v in pivot.columns]

        for _, ep_df in ts_df.groupby("ep_id"):
            if len(ep_df) < min_duration_hours:
                continue

            t_ini = ep_df[datetime_col].min()
            t_fin = ep_df[datetime_col].max()
            orig_idx = ep_df["orig_idx"].to_numpy()

            confirmado = False
            if not vecinos_estacion or min_neighbors_confirmed == 0:
                # estación aislada o usuario no exige confirmación
                confirmado = True
            else:
                count_ok = 0
                for vec in vecinos_estacion:
                    vals_vec = pivot.loc[t_ini:t_fin, vec].dropna()
                    if vals_vec.empty:
                        continue
                    serie_vec = result.loc[
                        (result[station_col] == vec) & result[value_col].notna(), value_col
                    ]
                    if len(serie_vec) < 10:
                        continue
                    q3v = serie_vec.quantile(0.75)
                    iqrv = q3v - serie_vec.quantile(0.25)
                    if iqrv <= 0:
                        continue
                    soft_thr_vec = q3v + iqr_soft_mult * iqrv
                    if (vals_vec > soft_thr_vec).any():
                        count_ok += 1
                    if count_ok >= min_neighbors_confirmed:
                        confirmado = True
                        break

            label = "regional" if confirmado else "puntual"
            result.loc[orig_idx, "flag_episode"] = label
            if confirmado:
                n_regional += len(orig_idx)
            else:
                n_puntual += len(orig_idx)

    logger.info(
        "[detect_regional_episodes] '%s' — regional: %d (preservado) | puntual: %d | "
        "umbrales IQR×%.1f hard / IQR×%.1f vecino | radio %.0f km",
        value_col,
        n_regional,
        n_puntual,
        iqr_hard_mult,
        iqr_soft_mult,
        neighbor_radius_km,
    )
    return result
