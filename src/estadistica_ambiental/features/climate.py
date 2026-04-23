"""Covariables de cambio climático: índices ENSO, ONI, escenarios.

Estas covariables se usan en modelos predictivos de oferta hídrica,
páramos, humedales y gestión de riesgo cuando hay influencia climática.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from estadistica_ambiental.config import ENSO_LAG_MESES, ENSO_THRESHOLDS

logger = logging.getLogger(__name__)

# URL pública del ONI (Oceanic Niño Index) — NOAA
_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

_SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def load_oni(
    path: Optional[str] = None,
    start_year: int = 1950,
) -> pd.DataFrame:
    """Carga el Índice Oceánico Niño (ONI) de NOAA o desde archivo local.

    El ONI es el índice estándar para clasificar El Niño/La Niña, con
    impacto directo en precipitación y temperatura en Colombia.

    Returns:
        DataFrame con columnas: fecha, oni, fase, intensidad.
    """
    if path and Path(path).exists():
        df = pd.read_csv(path, sep=r"\s+", skiprows=1,
                         names=["year", "season", "anom", "total"])
    else:
        try:
            df = pd.read_csv(_ONI_URL, sep=r"\s+", skiprows=1,
                             names=["year", "season", "anom", "total"])
            logger.info("ONI descargado de NOAA")
        except Exception as e:
            logger.warning("No se pudo descargar ONI: %s. Devolviendo DataFrame vacío.", e)
            return pd.DataFrame(columns=["fecha", "oni", "fase", "intensidad"])

    df["month"] = df["season"].map(_SEASON_TO_MONTH)
    df["fecha"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    df = df[df["year"] >= start_year].dropna(subset=["fecha"])
    df["oni"] = df["anom"].astype(float)
    df["fase"] = df["oni"].apply(_classify_enso)
    df["intensidad"] = df["oni"].apply(_classify_enso_intensity)
    return df[["fecha", "oni", "fase", "intensidad"]].reset_index(drop=True)


def _classify_enso(oni_val: float) -> str:
    """Clasifica el valor ONI en fase ENSO (umbrales NOAA)."""
    if oni_val >= ENSO_THRESHOLDS["nino"]:
        return "niño"
    if oni_val <= ENSO_THRESHOLDS["nina"]:
        return "niña"
    return "neutro"


def _classify_enso_intensity(oni_val: float) -> str:
    """Clasifica la intensidad del evento ENSO."""
    if oni_val >= ENSO_THRESHOLDS["nino_fuerte"]:
        return "fuerte"
    if oni_val >= ENSO_THRESHOLDS["nino"]:
        return "moderado"
    if oni_val <= ENSO_THRESHOLDS["nina_fuerte"]:
        return "fuerte"
    if oni_val <= ENSO_THRESHOLDS["nina"]:
        return "moderado"
    return "neutro"


def enso_dummy(df: pd.DataFrame, oni_df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Une el índice ONI al DataFrame principal y agrega dummies de fase."""
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
    result["_merge_date"] = result[date_col].dt.to_period("M").dt.to_timestamp()
    oni_monthly = oni_df.copy()
    oni_monthly["_merge_date"] = oni_monthly["fecha"].dt.to_period("M").dt.to_timestamp()
    result = result.merge(
        oni_monthly[["_merge_date", "oni", "fase", "intensidad"]],
        on="_merge_date", how="left",
    ).drop(columns=["_merge_date"])
    dummies = pd.get_dummies(result["fase"], prefix="enso", drop_first=False)
    return pd.concat([result, dummies], axis=1)


def enso_lagged(
    df: pd.DataFrame,
    oni_df: pd.DataFrame,
    date_col: str,
    linea_tematica: Optional[str] = None,
    lag_meses: Optional[int] = None,
) -> pd.DataFrame:
    """Une el índice ONI con el lag específico por línea temática colombiana.

    El lag captura el retraso entre la señal ENSO y su respuesta en la variable
    ambiental local (e.g. caudal, PM2.5, nivel de humedal).

    Args:
        df: DataFrame con datos ambientales.
        oni_df: DataFrame devuelto por load_oni().
        date_col: Columna de fechas en df.
        linea_tematica: Nombre de la línea ('oferta_hidrica', 'calidad_aire', etc.).
            Determina el lag automáticamente desde config.ENSO_LAG_MESES.
        lag_meses: Override manual del lag. Tiene precedencia sobre linea_tematica.

    Returns:
        df con columnas oni_lag{n}, fase_lag{n}, intensidad_lag{n}, dummies.
    """
    lag = lag_meses
    if lag is None:
        lag = ENSO_LAG_MESES.get(linea_tematica or "default",
                                  ENSO_LAG_MESES["default"])

    logger.info("ENSO lag aplicado: %d meses (línea: %s)", lag, linea_tematica or "default")

    oni_shifted = oni_df.copy()
    oni_shifted["fecha"] = oni_shifted["fecha"] + pd.DateOffset(months=lag)

    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
    result["_merge_date"] = result[date_col].dt.to_period("M").dt.to_timestamp()
    oni_shifted["_merge_date"] = oni_shifted["fecha"].dt.to_period("M").dt.to_timestamp()

    suffix = f"_lag{lag}"
    result = result.merge(
        oni_shifted[["_merge_date", "oni", "fase", "intensidad"]].rename(columns={
            "oni": f"oni{suffix}",
            "fase": f"fase{suffix}",
            "intensidad": f"intensidad{suffix}",
        }),
        on="_merge_date", how="left",
    ).drop(columns=["_merge_date"])

    dummies = pd.get_dummies(result[f"fase{suffix}"], prefix=f"enso{suffix}", drop_first=False)
    return pd.concat([result, dummies], axis=1)
