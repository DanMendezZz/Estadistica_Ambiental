"""Configuración central del proyecto Estadística Ambiental.
Adaptado de boa-sarima-forecaster/config.py por Dan Méndez — 2026-04-22
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

ROOT_DIR       = Path(__file__).parent.parent.parent
DATA_RAW       = Path(os.getenv("DATA_RAW_DIR",       str(ROOT_DIR / "data" / "raw")))
DATA_PROCESSED = Path(os.getenv("DATA_PROCESSED_DIR", str(ROOT_DIR / "data" / "processed")))
DATA_OUTPUT    = Path(os.getenv("DATA_OUTPUT_DIR",    str(ROOT_DIR / "data" / "output")))
REPORTS_DIR    = DATA_OUTPUT / "reports"

# ---------------------------------------------------------------------------
# Backtesting defaults (heredados y ajustados)
# ---------------------------------------------------------------------------

DEFAULT_N_TRIALS      = 50      # trials Optuna por modelo
DEFAULT_HORIZON       = 12      # pasos de pronóstico
DEFAULT_N_SPLITS      = 5       # folds de walk-forward
DEFAULT_MIN_TRAIN_PCT = 0.5     # % mínimo para entrenamiento

# ---------------------------------------------------------------------------
# Dominio ambiental — frecuencias típicas
# ---------------------------------------------------------------------------

FREQ_HOURLY  = "h"
FREQ_DAILY   = "D"
FREQ_MONTHLY = "ME"
FREQ_YEARLY  = "YE"

# Estacionalidades por frecuencia (para SARIMA)
SEASONAL_PERIOD = {
    "h":  24,     # ciclo diario en datos horarios
    "D":  365,    # ciclo anual en datos diarios (usar 7 para semanal)
    "ME": 12,     # ciclo anual en datos mensuales
    "YE": 1,
}

# ---------------------------------------------------------------------------
# Umbrales normativos colombianos (calidad del aire)
# Resolución 2254 de 2017 — MinAmbiente
# ---------------------------------------------------------------------------

NORMA_CO = {
    "pm25_annual":  25.0,   # µg/m³ (norma anual)
    "pm25_24h":     37.0,   # µg/m³ (norma 24h)
    "pm10_annual":  40.0,   # µg/m³
    "pm10_24h":     75.0,   # µg/m³
    "o3_8h":       100.0,   # µg/m³
    "no2_annual":   40.0,   # µg/m³
    "so2_24h":      50.0,   # µg/m³
    "co_8h":        10.0,   # mg/m³
}

# Guías OMS 2021
NORMA_OMS = {
    "pm25_annual":  5.0,
    "pm25_24h":    15.0,
    "pm10_annual": 15.0,
    "pm10_24h":    45.0,
    "o3_8h":      100.0,
    "no2_annual":  10.0,
}
