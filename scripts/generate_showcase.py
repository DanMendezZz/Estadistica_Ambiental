"""Genera el showcase HTML de cumplimiento normativo para la estación Kennedy RMCAB.

Usa datos sintéticos calibrados sobre las estadísticas reales RMCAB 2022-2024:
  - PM2.5: media ≈ 18 µg/m³, picos estación seca ≈ 40-50 µg/m³
  - PM10:  media ≈ 34 µg/m³, picos ≈ 70-80 µg/m³
  - Estacionalidad bimodal bogotana (picos en ene-feb y jul-ago)

Salida: docs/showcase/index.html  (directorio que usa GitHub Pages)
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Parámetros del generador ────────────────────────────────────────────────

RNG_SEED      = 42
DATE_START    = "2022-01-01"
DATE_END      = "2024-12-31"
ESTACION      = "Kennedy (RMCAB — Bogotá)"
OUTPUT        = Path(__file__).resolve().parent.parent / "docs" / "showcase" / "index.html"


def _sinteticos_kennedy(rng: np.random.Generator) -> pd.DataFrame:
    """Genera datos diarios representativos de Kennedy RMCAB 2022-2024."""
    fechas = pd.date_range(DATE_START, DATE_END, freq="D")
    n = len(fechas)
    doy = fechas.day_of_year.values.astype(float)

    # Estacionalidad bimodal bogotana (dos estaciones secas: ene-feb y jul-ago)
    peak1_doy = 25.0   # ~25 ene; la fórmula genera el segundo pico en ~jul por armonía
    season = (
        7.0 * np.cos(2 * np.pi * (doy - peak1_doy) / 365)
        + 4.0 * np.cos(4 * np.pi * (doy - peak1_doy) / 365 + np.pi)
    )

    # Efecto día de semana (tráfico laboral Kennedy)
    dow_effect = np.where(fechas.day_of_week < 5, 1.5, -2.0)

    # Ruido gaussiano + episodios de alta contaminación (~5% de días)
    ruido = rng.normal(0, 3.5, n)
    episodios = rng.random(n) < 0.05
    pico = rng.uniform(15, 28, n) * episodios

    # PM2.5 base ≈ 18 µg/m³ (media anual Kennedy real ~17-20)
    pm25 = np.clip(18.0 + season + dow_effect + ruido + pico, 2.0, 120.0)

    # PM10 ≈ 1.75 × PM2.5 + ruido propio (ratio típico Kennedy)
    pm10 = np.clip(pm25 * 1.75 + rng.normal(0, 6, n), 5.0, 200.0)

    # ~3% de datos faltantes (mantenimiento de sensores)
    missing_mask = rng.random(n) < 0.03
    pm25[missing_mask] = np.nan
    pm10[missing_mask] = np.nan

    return pd.DataFrame({"fecha": fechas, "pm25": pm25.round(1), "pm10": pm10.round(1)})


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    df = _sinteticos_kennedy(rng)

    logger.info("Dataset Kennedy: %d días (%s → %s)", len(df), DATE_START, DATE_END)
    logger.info(
        "PM2.5  — media: %.1f  p95: %.1f  máx: %.1f",
        df["pm25"].mean(), df["pm25"].quantile(0.95), df["pm25"].max(),
    )
    logger.info(
        "PM10   — media: %.1f  p95: %.1f  máx: %.1f",
        df["pm10"].mean(), df["pm10"].quantile(0.95), df["pm10"].max(),
    )

    from estadistica_ambiental.reporting.compliance_report import compliance_report

    output_path = compliance_report(
        df,
        variables=["pm25", "pm10"],
        date_col="fecha",
        linea_tematica="calidad_aire",
        output=str(OUTPUT),
        title="Cumplimiento Normativo PM2.5 / PM10 — Estación Kennedy (RMCAB Bogotá)",
    )
    logger.info("Showcase generado: %s", output_path)


if __name__ == "__main__":
    main()
