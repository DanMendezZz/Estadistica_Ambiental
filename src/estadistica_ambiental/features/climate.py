"""Covariables de cambio climático: índices ENSO, ONI, escenarios.

Estas covariables se usan en modelos predictivos de oferta hídrica,
páramos, humedales y gestión de riesgo cuando hay influencia climática.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# URL pública del ONI (Oceanic Niño Index) — NOAA
_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


def load_oni(
    path: Optional[str] = None,
    start_year: int = 1950,
) -> pd.DataFrame:
    """Carga el Índice Oceánico Niño (ONI) de NOAA o desde archivo local.

    El ONI es el índice estándar para clasificar El Niño/La Niña, con
    impacto directo en precipitación y temperatura en Colombia.

    Returns DataFrame con columnas: fecha, oni, fase (niño/niña/neutro).
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
            return pd.DataFrame(columns=["fecha", "oni", "fase"])

    season_to_month = {
        "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
        "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
    }
    df["month"] = df["season"].map(season_to_month)
    df["fecha"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    df = df[df["year"] >= start_year].dropna(subset=["fecha"])
    df["oni"] = df["anom"].astype(float)
    df["fase"] = df["oni"].apply(_classify_enso)
    return df[["fecha", "oni", "fase"]].reset_index(drop=True)


def _classify_enso(oni_val: float) -> str:
    """Clasifica el valor ONI en fase ENSO."""
    if oni_val >= 0.5:
        return "niño"
    if oni_val <= -0.5:
        return "niña"
    return "neutro"


def enso_dummy(df: pd.DataFrame, oni_df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Une el índice ONI al DataFrame principal y agrega dummies de fase."""
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
    result["_merge_date"] = result[date_col].dt.to_period("M").dt.to_timestamp()
    oni_monthly = oni_df.copy()
    oni_monthly["_merge_date"] = oni_monthly["fecha"].dt.to_period("M").dt.to_timestamp()
    result = result.merge(
        oni_monthly[["_merge_date", "oni", "fase"]],
        on="_merge_date", how="left",
    ).drop(columns=["_merge_date"])
    dummies = pd.get_dummies(result["fase"], prefix="enso", drop_first=False)
    return pd.concat([result, dummies], axis=1)
