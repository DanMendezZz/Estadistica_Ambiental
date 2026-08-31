"""Configuración central del proyecto Estadística Ambiental.
Adaptado de boa-sarima-forecaster/config.py por Dan Méndez — 2026-04-22
"""

from __future__ import annotations

import math
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

# Carpeta externa con descargas SISAIRE (`CAR_<año>.csv`). Definir en el sistema
# con `setx SISAIRE_LOCAL_DIR "<ruta>"` (Windows) o exportar en .bashrc / .env;
# queda `None` si no está configurada — el repo no asume nunca esa ruta.
SISAIRE_LOCAL_DIR: Path | None = (
    Path(os.environ["SISAIRE_LOCAL_DIR"]) if os.environ.get("SISAIRE_LOCAL_DIR") else None
)

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
# Verificado 2026-07-25 contra el texto oficial (Diario Oficial No. 50.415):
# valores de la Tabla 1 (Art. 2), vigentes desde el Parágrafo 1 del Art. 2
# (1-jul-2018 en adelante). La Tabla 2 (Art. 3) fija metas que solo rigen
# desde el 1-ene-2030; NO usar esos valores como umbral vigente hoy.
# ---------------------------------------------------------------------------

NORMA_CO: dict[str, float] = {
    "pm25_annual": 25.0,  # µg/m³ (norma anual)
    "pm25_24h": 37.0,  # µg/m³ (norma 24h, Parágrafo 1 Art. 2)
    "pm10_annual": 50.0,  # µg/m³ (Tabla 1; la meta 2030 es 30.0, aún no vigente)
    "pm10_24h": 75.0,  # µg/m³ (Parágrafo 1 Art. 2)
    "o3_8h": 100.0,  # µg/m³
    "no2_annual": 60.0,  # µg/m³ (Tabla 1; la meta 2030 es 40.0, aún no vigente)
    "so2_24h": 50.0,  # µg/m³
    "co_8h": 5.0,  # mg/m³ (Tabla 1: 5.000 µg/m³)
}

# Índice de Calidad del Aire (ICA), Res. 2254/2017 Arts. 19 y 20 (Tablas 5 y 6)
# (no "Anexo 3": esta resolución no tiene un anexo con ese número; verificado
# 2026-07-25 contra el texto oficial completo).
# Breakpoints (límites superiores inclusivos) por contaminante.
# Categorías ordenadas: Buena, Aceptable, Dañina sensibles, Dañina, Muy dañina, Peligrosa.
# Unidades: µg/m³, salvo CO que va en mg/m³.
# Fuente única de verdad — consumida por preprocessing/air_quality.py y evaluation/metrics.py.
ICA_BREAKPOINTS: dict[str, list[float]] = {
    # PM2.5 — promedio 24h (µg/m³)
    "pm25": [-math.inf, 12.0, 37.0, 55.0, 150.0, 250.0, math.inf],
    # PM10 — promedio 24h (µg/m³)
    "pm10": [-math.inf, 54.0, 154.0, 254.0, 354.0, 424.0, math.inf],
    # Ozono O₃ — promedio 8h (µg/m³)
    "o3": [-math.inf, 100.0, 160.0, 215.0, 265.0, 800.0, math.inf],
    # NO₂ — promedio 1h (µg/m³)
    "no2": [-math.inf, 100.0, 190.0, 677.0, 1221.0, 2350.0, math.inf],
    # SO₂ — promedio 24h (µg/m³)
    "so2": [-math.inf, 50.0, 100.0, 360.0, 649.0, 1000.0, math.inf],
    # CO, promedio 8h (mg/m³). Verificado 2026-07-25: los valores anteriores
    # (4.4, 9.4, 12.4, 15.4, 30.4) eran la tabla AQI de CO de la EPA en ppm,
    # mal etiquetada como mg/m³; nunca fueron los cortes colombianos. Los de
    # abajo vienen de la Tabla No. 6 (Art. 20) de la Res. 2254/2017, extraídos
    # de una tabla incrustada como imagen en el PDF oficial (no texto
    # seleccionable), con un corte (el 2º) reconstruido por consistencia
    # aritmética del factor ppm->mg/m3 tras una revision que detecto un digito
    # de OCR mal transcrito (10.189 -> 10.789; ver
    # test_ica_co_breakpoints_conversion_consistente). Reverificar contra el
    # PDF oficial de alta resolucion si la precision exacta del corte importa
    # para un caso de uso especifico.
    "co": [-math.inf, 5.094, 10.789, 14.254, 17.688, 34.867, math.inf],
}

# Etiquetas oficiales (en orden) de las categorías ICA — Res. 2254/2017.
ICA_LABELS: list[str] = [
    "Buena",
    "Aceptable",
    "Dañina sensibles",
    "Dañina",
    "Muy dañina",
    "Peligrosa",
]

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
# Verificado 2026-07-25 contra el texto oficial (37 artículos completos).
# ---------------------------------------------------------------------------

NORMA_AGUA_POTABLE: dict[str, float] = {
    "ph_min": 6.5,  # unidades pH (Art. 4)
    "ph_max": 9.0,  # Art. 4
    # od_min: sin respaldo normativo vigente para agua potable. Ver NORMA_FUENTES
    # ("agua_potable_od_dbo5"): es un valor de referencia técnica, no una norma
    # colombiana exigible hoy para este uso.
    "od_min": 4.0,  # mg/L: valor de referencia técnica, no normativo (ver nota arriba)
    "turbiedad_max": 2.0,  # NTU (Art. 2, Cuadro 1)
    "color_max": 15.0,  # UPC (Art. 2, Cuadro 1)
    "conductividad_max": 1000.0,  # µS/cm (Art. 3)
    "nitratos_max": 10.0,  # mg/L NO₃⁻ (Art. 6, Cuadro 3). No 50: ese valor no
    # tiene respaldo en la norma colombiana verificada; el límite real vigente
    # es 10.0.
    "nitritos_max": 0.1,  # mg/L NO₂⁻ (Art. 6, Cuadro 3)
    "fosforo_max": 0.5,  # mg/L: la norma lo expresa como "Fosfatos (PO4³⁻)"
    # (Art. 7, Cuadro 4), no como "Fósforo Total (P)": mismo valor, nomenclatura
    # distinta a la de otras fuentes.
    "coliformes_totales": 0.0,  # NMP/100 mL, deben ser cero (Art. 11, Cuadro 5)
    "coliformes_fecales": 0.0,  # NMP/100 mL: la norma exige E. coli en cero
    # (Art. 11, Cuadro 5); "coliformes fecales" es el término histórico equivalente.
    # dbo5_max: igual que od_min, sin respaldo normativo vigente para agua potable.
    "dbo5_max": 2.0,  # mg/L: valor de referencia técnica, no normativo (ver nota arriba)
}

# ---------------------------------------------------------------------------
# Norma colombiana — Vertimientos a Cuerpos Hídricos
# Resolución 631 de 2015, MinAmbiente (valores típicos sector doméstico:
# prestadores de alcantarillado con carga ≤625 kg/día DBO5, Art. 8)
# Verificado 2026-07-25 contra el texto oficial (Diario Oficial No. 49.486).
# ---------------------------------------------------------------------------

NORMA_VERTIMIENTOS: dict[str, float] = {
    "ph_min": 6.0,  # Art. 8
    "ph_max": 9.0,  # Art. 8
    "dbo5_max": 90.0,  # mg/L (Art. 8, columna de prestadores ≤625 kg/día)
    "dqo_max": 180.0,  # mg/L (misma columna; 200.0 pertenece a la columna de
    # soluciones individuales unifamiliares/bifamiliares, que no define DBO5)
    "sst_max": 90.0,  # mg/L sólidos suspendidos totales (Art. 8)
    # od_min: sin respaldo normativo vigente. Ver NORMA_FUENTES
    # ("vertimientos_od"): hoy el OD exigible en el cuerpo receptor se fija
    # caso por caso vía PORH (Decreto 1076/2015), no por un valor nacional fijo.
    "od_min": 4.0,  # mg/L: valor de referencia técnica, no normativo (ver nota arriba)
    "temperatura_max": 40.0,  # °C al punto de vertimiento (Art. 5)
}

# ---------------------------------------------------------------------------
# NORMA_FUENTES: procedencia legal de los umbrales normativos anteriores.
# Verificado 2026-07-25 (ver docs/decisiones.md ADR-020). Cada entrada indica
# codigo, articulo, url_oficial y fecha_verificacion; consumido por
# tests/test_config_normas.py para detectar umbrales sin fuente o con
# verificacion vencida (>12 meses).
# ---------------------------------------------------------------------------

NORMA_FUENTES: dict[str, dict[str, str]] = {
    "NORMA_CO": {
        "codigo": "Resolución 2254 de 2017 (MinAmbiente)",
        "articulo": "Art. 2 y Parágrafo 1 (Tabla 1, valores vigentes desde 2018-07-01)",
        "url_oficial": "https://www.minambiente.gov.co/documento-normativa/resolucion-2254-de-2017/",
        "fecha_verificacion": "2026-07-25",
        "estado": "vigente",
    },
    "ICA_BREAKPOINTS": {
        "codigo": "Resolución 2254 de 2017 (MinAmbiente)",
        "articulo": "Arts. 19 y 20 (Tablas 5 y 6). Los cortes de CO se extrajeron de una "
        "tabla incrustada como imagen (OCR); reverificar contra el PDF oficial de alta "
        "resolución si la precisión exacta del último dígito importa",
        "url_oficial": "https://www.minambiente.gov.co/documento-normativa/resolucion-2254-de-2017/",
        "fecha_verificacion": "2026-07-25",
        "estado": "vigente",
    },
    "NORMA_OMS": {
        "codigo": "OMS, Guías mundiales de calidad del aire (2021)",
        "articulo": "Tabla 3.1 (niveles guía anuales y de corto plazo)",
        "url_oficial": "https://www.who.int/publications/i/item/9789240034228",
        "fecha_verificacion": "2026-07-25",
        "estado": "guia_no_vinculante: referencia internacional, no es norma colombiana exigible",
    },
    "NORMA_AGUA_POTABLE": {
        "codigo": "Resolución 2115 de 2007 (MinProtección Social / MinAmbiente)",
        "articulo": "Arts. 2 a 11 (Cuadros 1 a 5): pH, turbiedad, color, conductividad, "
        "nitratos, nitritos, fosfatos, coliformes",
        "url_oficial": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Resolucion/30030110",
        "fecha_verificacion": "2026-07-25",
        "estado": "vigente",
        # od_min y dbo5_max NO estan cubiertos por esta cita; su fuente real
        # esta documentada aparte en NORMA_FUENTES["agua_potable_od_dbo5"].
        "excluye": ["od_min", "dbo5_max"],
    },
    "agua_potable_od_dbo5": {
        "codigo": "Decreto 1594 de 1984, Art. 45, DEROGADO por Art. 79 del "
        "Decreto 3930 de 2010 (hoy Decreto 1076/2015, Libro 2, Parte 2, Título 3)",
        "articulo": "Art. 45 (histórico, uso 'preservación de flora y fauna', "
        "no 'consumo humano'); sin reemplazo por valor fijo nacional",
        "url_oficial": "https://www.minambiente.gov.co/wp-content/uploads/2021/10/"
        "decreto-1076-de-2015.pdf",
        "fecha_verificacion": "2026-07-25",
        "estado": "derogado_sin_reemplazo_fijo: hoy se fija por PORH caso a caso",
    },
    "NORMA_VERTIMIENTOS": {
        "codigo": "Resolución 631 de 2015 (MinAmbiente)",
        "articulo": "Arts. 5 y 8 (Tabla sector doméstico/municipal, columna ≤625 kg/día DBO5)",
        "url_oficial": "https://normas.cra.gov.co/gestor/docs/resolucion_minambienteds_0631_2015.htm",
        "fecha_verificacion": "2026-07-25",
        "estado": "vigente",
        # od_min NO esta cubierto por esta cita; ver NORMA_FUENTES["vertimientos_od"].
        "excluye": ["od_min"],
    },
    "vertimientos_od": {
        "codigo": "Decreto 1594 de 1984, Art. 45, DEROGADO por Art. 79 del "
        "Decreto 3930 de 2010 (hoy Decreto 1076/2015, Libro 2, Parte 2, Título 3)",
        "articulo": "Art. 45 (histórico); sin reemplazo por valor fijo nacional",
        "url_oficial": "https://www.minambiente.gov.co/wp-content/uploads/2021/10/"
        "decreto-1076-de-2015.pdf",
        "fecha_verificacion": "2026-07-25",
        "estado": "derogado_sin_reemplazo_fijo: hoy se fija por PORH caso a caso",
    },
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
# Marco institucional: Ley 1523 de 2012 (SNGRD) y Decreto 1807 de 2014.
# Verificado 2026-07-25: ninguna de las dos normas fija umbrales numéricos de
# precipitación; son marco de competencias y metodología (estudios básicos/
# detallados), no una tabla de valores. Los cortes de abajo son una convención
# metodológica propia sin respaldo normativo formal confirmado; no incluir en
# NORMA_FUENTES como si fueran ley.
# ---------------------------------------------------------------------------

NIVELES_AMENAZA: list[str] = ["muy_baja", "baja", "media", "alta", "muy_alta"]

# Umbrales de precipitación (mm/día) para clasificar amenaza por inundación
# (convención metodológica propia, ver nota arriba; no viene de la Ley 1523/2012
# ni del Decreto 1807/2014)
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
