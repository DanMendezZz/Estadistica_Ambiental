"""Funciones específicas para preprocesamiento de calidad del aire.

Incluye:
  - Categorización ICA según Resolución 2254/2017 (Colombia)
  - Detección de episodios contaminantes con validación espacial
  - Corrección de sesgo estacional en modelos de pronóstico

Nota: ICA_CATEGORIES en config.py corresponde al Índice de Calidad del Agua
(IDEAM, escala 0-1) y es distinto del ICA de calidad del aire de Res. 2254/2017.
"""

from __future__ import annotations

import logging
from typing import Literal, Tuple

import numpy as np
import pandas as pd

from estadistica_ambiental.config import ICA_BREAKPOINTS, ICA_LABELS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes ICA — Resolución 2254 de 2017 (MinAmbiente Colombia)
# Aplicables a PM2.5, PM10, O₃, NO₂, SO₂, CO
#
# Los breakpoints y etiquetas viven en `config.ICA_BREAKPOINTS` /
# `config.ICA_LABELS` (ADR-005, fuente única de verdad). Aquí se mantienen los
# alias privados por retrocompatibilidad con código que los importaba.
# ---------------------------------------------------------------------------

# Colores oficiales normativa ICA Res. 2254/2017
ICA_COLORS: dict[str, str] = {
    "Buena": "#00E400",
    "Aceptable": "#FFFF00",
    "Dañina sensibles": "#FF7E00",
    "Dañina": "#FF0000",
    "Muy dañina": "#8F3F97",
    "Peligrosa": "#7E0023",
}

# Alias privados — re-exportan las constantes centralizadas en config.py.
_ICA_BREAKPOINTS: dict[str, list[float]] = ICA_BREAKPOINTS
_ICA_LABELS: list[str] = ICA_LABELS


# ---------------------------------------------------------------------------
# Función 1: categorize_ica
# ---------------------------------------------------------------------------


def categorize_ica(
    series: pd.Series,
    pollutant: str = "pm25",
    standard: str = "res_2254_2017",
) -> pd.Series:
    """Categoriza una serie de concentraciones según el ICA de Res. 2254/2017.

    Args:
        series: Serie de valores de concentración del contaminante.
        pollutant: Contaminante. Opciones: 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co'.
            Si no se reconoce, usa los breakpoints de PM2.5 con aviso.
        standard: Norma de referencia. Solo 'res_2254_2017' está implementada;
            el parámetro se reserva para versiones futuras (ej. estándar OMS).

    Returns:
        pd.Series de tipo Categorical con etiquetas:
        "Buena", "Aceptable", "Dañina sensibles", "Dañina", "Muy dañina", "Peligrosa".
        NaN donde la entrada sea NaN.

    Raises:
        ValueError: Si ``standard`` no es reconocido.

    Example:
        >>> import pandas as pd
        >>> from estadistica_ambiental.preprocessing.air_quality import categorize_ica
        >>> s = pd.Series([8.0, 20.0, 40.0, 60.0, 160.0, 300.0])
        >>> categorize_ica(s, pollutant='pm25')
        0             Buena
        1          Aceptable
        2    Dañina sensibles
        3            Dañina
        4         Muy dañina
        5          Peligrosa
        dtype: category
    """
    if standard != "res_2254_2017":
        raise ValueError(f"Norma '{standard}' no implementada. Norma soportada: 'res_2254_2017'.")

    pollutant_key = pollutant.lower().replace(".", "").replace("₂", "2").replace("₃", "3")
    if pollutant_key not in _ICA_BREAKPOINTS:
        logger.warning(
            "Contaminante '%s' no reconocido; se usarán breakpoints de PM2.5. Opciones válidas: %s",
            pollutant,
            list(_ICA_BREAKPOINTS),
        )
        pollutant_key = "pm25"

    bins = _ICA_BREAKPOINTS[pollutant_key]

    categorized = pd.cut(
        series,
        bins=bins,
        labels=_ICA_LABELS,
        right=True,
    )
    return categorized


# ---------------------------------------------------------------------------
# Función 2: flag_spatial_episodes
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km entre dos puntos geográficos (fórmula de Haversine)."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2.0 * R * np.arcsin(np.sqrt(a))


def _build_neighbor_map(
    coords: dict[str, tuple[float, float]],
    active_stations: set[str],
    radius_km: float,
) -> dict[str, list[str]]:
    """Construye mapa estación → lista de vecinos dentro del radio.

    Args:
        coords: Diccionario {estacion: (lat, lon)}.
        active_stations: Conjunto de estaciones presentes en los datos.
        radius_km: Radio de búsqueda en kilómetros.

    Returns:
        Diccionario {estacion: [vecino1, vecino2, ...]}.
    """
    stations = [s for s in coords if s in active_stations]
    neighbors: dict[str, list[str]] = {s: [] for s in stations}
    for i, s1 in enumerate(stations):
        lat1, lon1 = coords[s1]
        for s2 in stations[i + 1 :]:
            lat2, lon2 = coords[s2]
            if _haversine_km(lat1, lon1, lat2, lon2) <= radius_km:
                neighbors[s1].append(s2)
                neighbors[s2].append(s1)
    return neighbors


def flag_spatial_episodes(
    df: pd.DataFrame,
    value_col: str,
    station_col: str,
    datetime_col: str,
    lat_col: str,
    lon_col: str,
    iqr_multiplier: float = 3.0,
    min_consecutive_hours: int = 4,
    distance_km: float = 50.0,
    min_neighbor_stations: int = 1,
) -> pd.DataFrame:
    """Detecta episodios contaminantes reales distinguiéndolos de errores de sensor.

    Aplica un pipeline de tres pasos con trazabilidad completa (ADR-002):
      1. Cap absoluto: valores > percentil 99.9 global se marcan 'cap_absoluto'.
      2. Episodios críticos: secuencias ≥ ``min_consecutive_hours`` horas
         consecutivas sobre IQR×``iqr_multiplier``, confirmadas por al menos
         ``min_neighbor_stations`` estaciones vecinas (a ≤ ``distance_km`` km)
         con elevación simultánea. Se marcan 'episodio_critico' y se PRESERVAN.
      3. Outliers IQR por estación×mes: valores moderados (1.5×IQR) se marcan
         'iqr_soft'; valores extremos (``iqr_multiplier``×IQR) no episódicos se
         marcan 'iqr_hard'.

    Los valores marcados como 'episodio_critico' NO se modifican: son eventos
    reales de contaminación que deben preservarse para análisis normativo.

    Args:
        df: DataFrame con al menos las columnas indicadas en los parámetros.
        value_col: Columna con la concentración del contaminante.
        station_col: Columna identificadora de estación.
        datetime_col: Columna de fecha/hora (dtype datetime o parseable).
        lat_col: Columna de latitud de la estación (decimal, WGS-84).
        lon_col: Columna de longitud de la estación (decimal, WGS-84).
        iqr_multiplier: Multiplicador IQR para umbral extremo. Default 3.0.
        min_consecutive_hours: Mínimo de horas consecutivas para episodio crítico.
            Default 4.
        distance_km: Radio máximo (km) para considerar estaciones vecinas.
            Default 50.
        min_neighbor_stations: Mínimo de vecinas con elevación simultánea para
            confirmar episodio. Default 1. Si una estación no tiene vecinas, el
            criterio temporal es suficiente.

    Returns:
        Copia del DataFrame con columna adicional ``flag_episode`` ∈
        {'original', 'iqr_soft', 'iqr_hard', 'episodio_critico', 'cap_absoluto'}.

    Raises:
        KeyError: Si alguna de las columnas requeridas no existe en ``df``.

    Notes:
        - Requiere pandas y numpy. No requiere geopandas.
        - El cálculo IQR se realiza por combinación estación×mes para capturar
          estacionalidad. Se requieren al menos 10 observaciones por grupo.
        - La detección de horas consecutivas usa un umbral de 1.5 h de brecha
          para tolerar datos faltantes aislados.
    """
    required_cols = {value_col, station_col, datetime_col, lat_col, lon_col}
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(f"Columnas requeridas no encontradas en df: {missing}")

    result = df.copy()
    result[datetime_col] = pd.to_datetime(result[datetime_col])
    result["flag_episode"] = "original"

    # Extraer coordenadas por estación (una fila por estación)
    coords_df = (
        result[[station_col, lat_col, lon_col]]
        .drop_duplicates(subset=[station_col])
        .set_index(station_col)
    )
    coords: dict[str, tuple[float, float]] = {
        s: (row[lat_col], row[lon_col]) for s, row in coords_df.iterrows()
    }

    # ── Paso 1: Cap absoluto (percentil 99.9 global) ───────────────────────────
    cap_value = result[value_col].quantile(0.999)
    mask_cap = result[value_col].notna() & (result[value_col] > cap_value)
    n_cap = int(mask_cap.sum())
    if n_cap > 0:
        result.loc[mask_cap, "flag_episode"] = "cap_absoluto"
        logger.info(
            "'%s': %d valores superan cap absoluto (%.2f). Marcados 'cap_absoluto'.",
            value_col,
            n_cap,
            cap_value,
        )

    # ── Tabla pivote para validación espacial rápida ───────────────────────────
    # Usa valores post-cap, pre-IQR
    active_stations: set[str] = set(result[station_col].unique())
    neighbor_map = _build_neighbor_map(coords, active_stations, distance_km)

    pivot = (
        result.loc[result["flag_episode"] != "cap_absoluto", [datetime_col, station_col, value_col]]
        .groupby([datetime_col, station_col])[value_col]
        .mean()
        .unstack(station_col)
        .sort_index()
    )

    # Columna mes para el IQR por estación×mes
    result["_month"] = result[datetime_col].dt.month

    n_episodios = 0
    n_iqr_hard = 0
    n_iqr_soft = 0

    for station in sorted(result[station_col].unique()):
        mask_st = result[station_col] == station
        vecinos = neighbor_map.get(station, [])
        vecinos = [v for v in vecinos if v in pivot.columns]

        for mes in sorted(result.loc[mask_st, "_month"].unique()):
            mask_mes = mask_st & (result["_month"] == mes)
            mask_orig = (
                mask_mes & (result["flag_episode"] == "original") & result[value_col].notna()
            )
            serie_orig = result.loc[mask_orig, value_col]
            if len(serie_orig) < 10:
                continue

            q1 = serie_orig.quantile(0.25)
            q3 = serie_orig.quantile(0.75)
            iqr = q3 - q1

            soft_upper = q3 + 1.5 * iqr
            soft_lower = q1 - 1.5 * iqr
            hard_upper = q3 + iqr_multiplier * iqr
            hard_lower = q1 - iqr_multiplier * iqr

            # ── Paso 2: Detectar episodios críticos ────────────────────────────
            mask_extremos = mask_orig & (
                (result[value_col] < hard_lower) | (result[value_col] > hard_upper)
            )
            idx_extremos = result.index[mask_extremos]

            if len(idx_extremos) > 0:
                ts_df = (
                    result.loc[idx_extremos, [datetime_col]]
                    .copy()
                    .sort_values(datetime_col)
                    .reset_index()
                )
                ts_df.columns = ["orig_idx", datetime_col]

                # Agrupar en episodios consecutivos (brecha > 1.5 h → nuevo ep.)
                ts_df["gap_h"] = ts_df[datetime_col].diff().dt.total_seconds().fillna(0) / 3600
                ts_df["ep_id"] = (ts_df["gap_h"] > 1.5).cumsum()

                for ep_id, ep_df in ts_df.groupby("ep_id"):
                    if len(ep_df) < min_consecutive_hours:
                        continue  # duración insuficiente → IQR lo manejará

                    t_inicio = ep_df[datetime_col].min()
                    t_fin = ep_df[datetime_col].max()

                    confirmado = False
                    if not vecinos or min_neighbor_stations == 0:
                        # Sin vecinos (estación aislada) → criterio temporal basta
                        confirmado = True
                    else:
                        vecinos_confirmados = 0
                        for vecino in vecinos:
                            if vecino not in pivot.columns:
                                continue
                            vals_vec = pivot.loc[t_inicio:t_fin, vecino].dropna()
                            if vals_vec.empty:
                                continue
                            # Umbral dinámico del vecino en el mismo mes
                            # Solo valores 'original' — excluye cap_absoluto y
                            # medianas ya imputadas de iteraciones anteriores
                            mask_vec_mes = (
                                (result[station_col] == vecino)
                                & (result["_month"] == mes)
                                & (result["flag_episode"] == "original")
                                & result[value_col].notna()
                            )
                            serie_vec = result.loc[mask_vec_mes, value_col]
                            if len(serie_vec) < 10:
                                continue
                            q3v = serie_vec.quantile(0.75)
                            iqrv = q3v - serie_vec.quantile(0.25)
                            umbral_vec = q3v + 1.5 * iqrv
                            if (vals_vec > umbral_vec).any():
                                vecinos_confirmados += 1
                            if vecinos_confirmados >= min_neighbor_stations:
                                confirmado = True
                                break

                    if confirmado:
                        orig_indices = ep_df["orig_idx"].values
                        result.loc[orig_indices, "flag_episode"] = "episodio_critico"
                        n_episodios += len(orig_indices)

            # ── Paso 3: IQR — marcar outliers no episódicos ────────────────────
            # Pre-determinar hard y soft antes de cualquier imputación para que
            # la mediana rolling no se calcule sobre los mismos valores a reemplazar
            base_iqr = mask_mes & (result["flag_episode"] == "original") & result[value_col].notna()
            hard_cond = (result[value_col] < hard_lower) | (result[value_col] > hard_upper)
            soft_cond = (result[value_col] < soft_lower) | (result[value_col] > soft_upper)

            mask_hard = base_iqr & hard_cond
            mask_soft = base_iqr & soft_cond & ~hard_cond  # soft excluye hard
            idx_hard = result.index[mask_hard]
            idx_soft = result.index[mask_soft]

            if idx_hard.empty and idx_soft.empty:
                continue

            # Mediana local con outliers enmascarados (NaN) en la ventana
            serie_clean = result.loc[base_iqr, value_col].copy()
            all_outliers = idx_hard.union(idx_soft)
            serie_clean.loc[serie_clean.index.isin(all_outliers)] = np.nan
            if serie_clean.notna().sum() == 0:
                continue
            mediana_local = serie_clean.rolling(5, center=True, min_periods=1).median()

            if len(idx_hard) > 0:
                result.loc[idx_hard, value_col] = mediana_local.reindex(idx_hard)
                result.loc[idx_hard, "flag_episode"] = "iqr_hard"
                n_iqr_hard += len(idx_hard)

            if len(idx_soft) > 0:
                result.loc[idx_soft, value_col] = mediana_local.reindex(idx_soft)
                result.loc[idx_soft, "flag_episode"] = "iqr_soft"
                n_iqr_soft += len(idx_soft)

    result = result.drop(columns=["_month"])

    flag_counts = result["flag_episode"].value_counts().to_dict()
    logger.info(
        "[flag_spatial_episodes] '%s' — original: %d | cap_absoluto: %d | "
        "episodio_critico: %d (preservado) | iqr_hard: %d | iqr_soft: %d",
        value_col,
        flag_counts.get("original", 0),
        flag_counts.get("cap_absoluto", 0),
        flag_counts.get("episodio_critico", 0),
        flag_counts.get("iqr_hard", 0),
        flag_counts.get("iqr_soft", 0),
    )

    return result


# ---------------------------------------------------------------------------
# Función 3: correct_seasonal_bias
# ---------------------------------------------------------------------------


def correct_seasonal_bias(
    predictions: pd.Series,
    actuals: pd.Series,
    time_col: pd.Series,
    by: Literal["month", "quarter", "week"] = "month",
) -> Tuple[pd.Series, pd.DataFrame]:
    """Calcula y aplica corrección de sesgo estacional a predicciones de modelo.

    El sesgo sistemático ocurre cuando el modelo sobreestima o subestima de
    forma consistente en ciertos períodos (e.g., meses secos vs. lluviosos).
    Esta función calcula el sesgo promedio por período y lo descuenta:

        predicción_corregida = predicción − sesgo_del_período

    Un sesgo positivo (sobreestimación) resulta en corrección hacia abajo;
    un sesgo negativo (subestimación) eleva la predicción.

    Args:
        predictions: Serie de valores predichos por el modelo.
        actuals: Serie de valores reales observados (mismo índice que predictions).
        time_col: Serie de fechas/horas correspondiente a cada observación.
            Debe ser parseable como datetime. Mismo largo que predictions.
        by: Granularidad temporal del sesgo:
            - 'month'   → sesgo por mes del año (1-12).
            - 'quarter' → sesgo por trimestre (1-4).
            - 'week'    → sesgo por semana del año (1-53).

    Returns:
        Tupla ``(predictions_corrected, bias_table)``:
          - ``predictions_corrected``: pd.Series con los valores corregidos,
            mismo índice que ``predictions``. Períodos sin datos de calibración
            se devuelven sin corrección (sesgo = 0) con aviso en log.
          - ``bias_table``: pd.DataFrame con columnas ``['periodo', 'sesgo',
            'n_obs', 'sesgo_std']``. ``sesgo`` > 0 indica sobreestimación.

    Raises:
        ValueError: Si ``by`` no es 'month', 'quarter' o 'week'.
        ValueError: Si ``predictions``, ``actuals`` y ``time_col`` tienen
            longitudes distintas.

    Example:
        >>> preds_ok, bias_df = correct_seasonal_bias(
        ...     predictions=df["predicho"],
        ...     actuals=df["real"],
        ...     time_col=df["datetime"],
        ...     by="month",
        ... )
        >>> bias_df.head()
           periodo   sesgo  n_obs  sesgo_std
        0        1   2.314    720      1.203
        1        2  -0.891    672      0.987
        ...
    """
    valid_by = ("month", "quarter", "week")
    if by not in valid_by:
        raise ValueError(f"Parámetro 'by' debe ser uno de {valid_by}. Recibido: '{by}'.")

    if not (len(predictions) == len(actuals) == len(time_col)):
        raise ValueError(
            "predictions, actuals y time_col deben tener la misma longitud. "
            f"Recibidos: {len(predictions)}, {len(actuals)}, {len(time_col)}."
        )

    time_parsed = pd.to_datetime(time_col.values)

    _period_extractor = {
        "month": lambda t: t.month,
        "quarter": lambda t: t.quarter,
        "week": lambda t: t.isocalendar()[1],
    }
    extractor = _period_extractor[by]

    periods = np.array([extractor(t) for t in time_parsed])

    bias_raw = predictions.values - actuals.values

    # Calcular tabla de sesgo por período
    unique_periods = np.unique(periods)
    rows = []
    for p in unique_periods:
        mask = periods == p
        b_vals = bias_raw[mask]
        valid = b_vals[~np.isnan(b_vals)]
        rows.append(
            {
                "periodo": int(p),
                "sesgo": float(np.mean(valid)) if len(valid) > 0 else 0.0,
                "n_obs": int(len(valid)),
                "sesgo_std": float(np.std(valid, ddof=1)) if len(valid) > 1 else 0.0,
            }
        )

    bias_table = pd.DataFrame(rows).sort_values("periodo").reset_index(drop=True)
    bias_map: dict[int, float] = dict(zip(bias_table["periodo"].astype(int), bias_table["sesgo"]))

    # Aplicar corrección
    corrected_values = predictions.copy()
    for p in unique_periods:
        mask_p = periods == p
        sesgo = bias_map.get(int(p), 0.0)
        corrected_values.iloc[np.where(mask_p)[0]] = predictions.iloc[np.where(mask_p)[0]] - sesgo

    n_sobreestima = int((bias_table["sesgo"] > 0).sum())
    n_subestima = int((bias_table["sesgo"] < 0).sum())
    logger.info(
        "[correct_seasonal_bias] Corrección por '%s': %d períodos con "
        "sobreestimación, %d con subestimación. Sesgo máx: %.3f, mín: %.3f.",
        by,
        n_sobreestima,
        n_subestima,
        float(bias_table["sesgo"].max()),
        float(bias_table["sesgo"].min()),
    )

    return corrected_values, bias_table
