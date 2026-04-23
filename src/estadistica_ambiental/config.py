"""Configuración central del proyecto Estadística Ambiental.
Adaptado de boa-sarima-forecaster/config.py por Dan Méndez — 2026-04-22
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_RAW = Path(os.getenv("DATA_RAW_DIR", str(ROOT_DIR / "data" / "raw")))
DATA_PROCESSED = Path(os.getenv("DATA_PROCESSED_DIR", str(ROOT_DIR / "data" / "processed")))
DATA_OUTPUT = Path(os.getenv("DATA_OUTPUT_DIR", str(ROOT_DIR / "data" / "output")))
REPORTS_DIR = DATA_OUTPUT / "reports"
DOCS_FUENTES = ROOT_DIR / "docs" / "fuentes"

# ---------------------------------------------------------------------------
# Backtesting defaults (heredados y ajustados)
# ---------------------------------------------------------------------------

DEFAULT_N_TRIALS = 50  # trials Optuna por modelo
DEFAULT_HORIZON = 12  # pasos de pronóstico
DEFAULT_N_SPLITS = 5  # folds de walk-forward
DEFAULT_MIN_TRAIN_PCT = 0.5  # % mínimo para entrenamiento

# ---------------------------------------------------------------------------
# Dominio ambiental — frecuencias típicas
# ---------------------------------------------------------------------------

FREQ_HOURLY = "h"
FREQ_DAILY = "D"
FREQ_MONTHLY = "ME"
FREQ_YEARLY = "YE"

# Estacionalidades por frecuencia (para SARIMA)
SEASONAL_PERIOD = {
    "h": 24,  # ciclo diario en datos horarios
    "D": 365,  # ciclo anual en datos diarios (usar 7 para semanal)
    "ME": 12,  # ciclo anual en datos mensuales
    "YE": 1,
}

# ---------------------------------------------------------------------------
# Norma colombiana — Calidad del Aire
# Resolución 2254 de 2017 — MinAmbiente
# ---------------------------------------------------------------------------

NORMA_CO: dict[str, float] = {
    "pm25_annual": 25.0,  # µg/m³ (norma anual)
    "pm25_24h": 37.0,  # µg/m³ (norma 24h)
    "pm10_annual": 40.0,  # µg/m³
    "pm10_24h": 75.0,  # µg/m³
    "o3_8h": 100.0,  # µg/m³
    "no2_annual": 40.0,  # µg/m³
    "so2_24h": 50.0,  # µg/m³
    "co_8h": 10.0,  # mg/m³
}

# Guías OMS 2021
NORMA_OMS: dict[str, float] = {
    "pm25_annual": 5.0,
    "pm25_24h": 15.0,
    "pm10_annual": 15.0,
    "pm10_24h": 45.0,
    "o3_8h": 100.0,
    "no2_annual": 10.0,
}

# ---------------------------------------------------------------------------
# Norma colombiana — Calidad del Agua Potable
# Resolución 2115 de 2007 — MinProtección / MinAmbiente
# Parámetros con mayor relevancia analítica
# ---------------------------------------------------------------------------

NORMA_AGUA_POTABLE: dict[str, float] = {
    "ph_min": 6.5,  # unidades pH
    "ph_max": 9.0,
    "od_min": 4.0,  # mg/L — mínimo para consumo seguro
    "turbiedad_max": 2.0,  # NTU (unidades de turbiedad)
    "color_max": 15.0,  # UPC (unidades de platino cobalto)
    "conductividad_max": 1000.0,  # µS/cm
    "nitratos_max": 50.0,  # mg/L NO₃⁻
    "nitritos_max": 0.1,  # mg/L NO₂⁻
    "fosforo_max": 0.5,  # mg/L P total
    "coliformes_totales": 0.0,  # NMP/100 mL — deben ser cero
    "coliformes_fecales": 0.0,  # NMP/100 mL — deben ser cero
    "dbo5_max": 2.0,  # mg/L (agua para consumo)
}

# ---------------------------------------------------------------------------
# Norma colombiana — Vertimientos a Cuerpos Hídricos
# Resolución 631 de 2015 — MinAmbiente  (valores típicos sector doméstico)
# ---------------------------------------------------------------------------

NORMA_VERTIMIENTOS: dict[str, float] = {
    "ph_min": 6.0,
    "ph_max": 9.0,
    "dbo5_max": 90.0,  # mg/L (sector doméstico / municipal)
    "dqo_max": 200.0,  # mg/L
    "sst_max": 90.0,  # mg/L sólidos suspendidos totales
    "od_min": 4.0,  # mg/L — debe mantenerse en el cuerpo receptor
    "temperatura_max": 40.0,  # °C al punto de vertimiento
}

# ---------------------------------------------------------------------------
# Índices hídricos — Umbrales de presión (IDEAM / ENA)
# Fuente: Estudio Nacional del Agua, Res. 872/2006
# ---------------------------------------------------------------------------

IUA_THRESHOLDS: dict[str, float] = {
    "bajo": 20.0,  # % — Demanda < 20% de la oferta → presión baja
    "moderado": 50.0,  # % — entre 20-50% → presión moderada
    "alto": 100.0,  # % — entre 50-100% → presión alta
    # > 100% → sobreexplotación crítica
}

IRH_THRESHOLDS: dict[str, float] = {
    "muy_baja": 0.2,  # Baja capacidad de retención y regulación hídrica
    "baja": 0.4,
    "moderada": 0.6,
    "alta": 0.8,
    # > 0.8 → muy alta regulación
}

IVH_LABELS: dict[str, tuple[float, float]] = {
    # (IRH_threshold, IUA_threshold) → categoría
    # IVH se obtiene combinando IRH e IUA; estos son rangos del IUA
    # con IRH < 0.5 (baja retención)
    "bajo": (0.0, 20.0),
    "medio": (20.0, 50.0),
    "alto": (50.0, 100.0),
    "muy_alto": (100.0, 1e9),
}

# ---------------------------------------------------------------------------
# Índice de Calidad del Agua (ICA) — IDEAM
# Escala 0-1 (ponderación de OD, DBO, DQO, SST, conductividad, pH, N, P)
# ---------------------------------------------------------------------------

ICA_CATEGORIES: dict[str, tuple[float, float]] = {
    "muy_malo": (0.00, 0.25),
    "malo": (0.25, 0.50),
    "regular": (0.50, 0.70),
    "bueno": (0.70, 0.90),
    "excelente": (0.90, 1.00),
}

# ---------------------------------------------------------------------------
# Índices de Deforestación — SMByC / IDEAM
# Umbrales para clasificar alertas tempranas (ATD)
# ---------------------------------------------------------------------------

DEFORESTACION_ALERTAS: dict[str, float] = {
    "minima_ha": 100.0,  # ha — umbral mínimo para reportar en ATD
    "critica_ha": 10000.0,  # ha — deforestación crítica en el período
    "tasa_anual_critica_pct": 1.0,  # % anual de pérdida de cobertura → alerta
}

# ---------------------------------------------------------------------------
# ENSO — Clasificación ONI (Oceanic Niño Index)
# Fuente: NOAA Climate Prediction Center
# ---------------------------------------------------------------------------

ENSO_THRESHOLDS: dict[str, float] = {
    "nino_fuerte": 1.5,  # ONI >= 1.5 → El Niño fuerte/muy fuerte
    "nino": 0.5,  # ONI >= 0.5 → El Niño
    "nina": -0.5,  # ONI <= -0.5 → La Niña
    "nina_fuerte": -1.5,  # ONI <= -1.5 → La Niña fuerte/muy fuerte
}

# Lag recomendado (meses) entre ONI y respuesta hidrológica por línea temática.
# Basado en literatura colombiana (cuencas Magdalena-Cauca y Andina).
ENSO_LAG_MESES: dict[str, int] = {
    "calidad_aire": 2,  # El Niño reduce lluvia → menor dispersión → PM2.5 sube
    "oferta_hidrica": 4,  # Sequía rezagada ~4 meses en cuencas Magdalena-Cauca
    "recurso_hidrico": 3,  # Calidad del agua responde en ~3 meses
    "pomca": 4,  # Mismo lag que oferta hídrica
    "pueea": 3,
    "paramos": 2,  # Páramos responden rápido a precipitación
    "humedales": 3,  # Hidroperiodo rezagado ~3 meses
    "rondas_hidricas": 3,
    "gestion_riesgo": 1,  # Riesgo (inundaciones) más inmediato
    "cambio_climatico": 0,  # Variable de contexto, sin lag específico
    "ordenamiento_territorial": 6,  # Muy largo plazo
    "default": 3,  # Lag por defecto si la línea no está especificada
}

# ---------------------------------------------------------------------------
# Niveles de Amenaza / Riesgo (Gestión del Riesgo)
# Ley 1523 de 2012 / Decreto 1807 de 2014
# ---------------------------------------------------------------------------

NIVELES_AMENAZA: list[str] = ["muy_baja", "baja", "media", "alta", "muy_alta"]

# Umbrales de precipitación (mm/día) para clasificar amenaza por inundación
AMENAZA_PRECIPITACION: dict[str, float] = {
    "baja": 50.0,  # mm/día
    "media": 100.0,
    "alta": 150.0,
    "muy_alta": 200.0,
}

# ---------------------------------------------------------------------------
# Rangos de temperatura por ecosistema colombiano (para validación)
# Fuentes: IDEAM, Atlas de Colombia, fichas de dominio
# ---------------------------------------------------------------------------

RANGO_TEMP_ECOSISTEMA: dict[str, tuple[float, float]] = {
    "paramo": (2.0, 16.0),  # °C — Páramos (hasta 4200 m.s.n.m.)
    "bosque_andino": (9.0, 22.0),  # °C — Bosque andino (2000-3200 m)
    "tierra_fria": (12.0, 18.0),  # °C — Zonas cafeteras altas
    "tierra_templada": (18.0, 24.0),  # °C — Zonas cafeteras medias
    "tierra_calida": (24.0, 35.0),  # °C — Llanura, costa, Orinoquía
}
