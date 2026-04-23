"""
Fase 8 — Ciclo estadístico completo: Gestión del Riesgo.

Línea temática: Gestión del Riesgo
Variable principal: precipitación acumulada mensual (mm/mes)
Análisis: riesgo por inundación — excedencias, temporadas extremas
Datos: auto-detecta reales en data/raw/; usa sintéticos como fallback
       (sintético: 1990-2025, media 120 mm/mes, bimodal, eventos ENSO)

Flujo:
  1. Carga o generación de datos (precipitación mensual 1990-2025)
  2. Validación con validate(df, linea_tematica="gestion_riesgo")
  3. EDA de calidad profunda (assess_quality)
  4. Estadística descriptiva + distribución de percentiles de riesgo
  5. Análisis de excedencias: exceedance_report con umbral de alerta >300mm/mes
  6. Estacionariedad ADF + KPSS (ADR-004)
  7. Descomposición STL (period=12)
  8. ENSO lagged — lag=1 mes (config.ENSO_LAG_MESES["gestion_riesgo"])
  9. Modelado predictivo: SARIMA + ETS — walk_forward(domain='general')
  10. Ranking multi-criterio rank_models() con RMSE, MAE, sMAPE
  11. Compliance report HTML con umbrales de precipitación personalizados
  12. Reporte HTML de pronóstico

Métricas: RMSE, MAE, sMAPE (domain='general')
Umbral de alerta: >300 mm/mes = riesgo alto de inundación (Ley 1523/2012)

Nota sobre umbral 300 mm/mes:
  No existe norma técnica colombiana con exactamente 300 mm/mes como límite
  legal de alerta temprana. Este umbral es empírico: corresponde al percentil
  ~85-90 de la distribución histórica en cuencas andinas con riesgo de
  inundación (Ideam, ENA 2022; POTs municipales con estudios de amenaza).
  Para uso operativo, reemplazar con el umbral definido en el PMGRD o POMCA
  de la cuenca de interés.

Salidas en data/output/reports/:
    - gestion_riesgo_forecast.html
    - cumplimiento_precipitacion.html

Salidas intermedias en data/output/fase8/:
    - gestion_riesgo_datos.csv
    - gestion_riesgo_validacion.json
    - gestion_riesgo_exceedances.csv
    - gestion_riesgo_stl.csv
    - gestion_riesgo_backtesting.csv
    - gestion_riesgo_forecast_12m.csv

Uso:
    python scripts/fase8_gestion_riesgo.py
"""
from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fase8_gestion_riesgo")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
OUTPUT   = ROOT / "data" / "output" / "fase8"
REPORTS  = ROOT / "data" / "output" / "reports"
OUTPUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Parámetros del sintético
# ---------------------------------------------------------------------------
INICIO_SINTETICO   = "1990-01"
FIN_SINTETICO      = "2025-12"
PRECIP_MEDIA       = 120.0    # mm/mes — media histórica referencia Andina
PRECIP_AMP_ANUAL   = 60.0     # mm — amplitud estacional bimodal
RHO_AR1            = 0.55     # AR(1) — persistencia de anomalías mensuales
SIGMA_RUIDO        = 28.0     # mm — variabilidad intra-mensual
PROB_EXTREMO       = 0.04     # probabilidad mensual de evento extremo ENSO
EXTREMO_MED        = 250.0    # mm adicionales en evento extremo (La Niña)
EXTREMO_SD         = 60.0     # variabilidad del evento extremo
PRECIP_MIN         = 0.0      # mm/mes — precipitación no puede ser negativa
PRECIP_MAX         = 2000.0   # mm/mes — límite físico colombia (validators.py)

# Umbral de alerta de precipitación para análisis de riesgo de inundación
# > 300 mm/mes: zona de riesgo alto, según POTs y estudios ENA (IDEAM).
# Este valor es empírico — reemplazar con el umbral de tu PMGRD / POMCA.
UMBRAL_ALERTA_MM   = 300.0

# Nombres candidatos de archivo de datos reales
REAL_DATA_CANDIDATES = [
    "gestion_riesgo_precipitacion.csv",
    "precipitacion_mensual.csv",
    "precip_mensual_riesgo.csv",
]


# ===========================================================================
# 1. CARGA O GENERACIÓN DE DATOS
# ===========================================================================

def cargar_o_generar_datos() -> tuple[pd.DataFrame, bool]:
    """Auto-detecta datos reales en data/raw/; genera sintéticos como fallback.

    Returns:
        (DataFrame con columnas fecha, precipitacion_mm), es_sintetico: bool
    """
    for nombre in REAL_DATA_CANDIDATES:
        ruta = DATA_RAW / nombre
        if ruta.exists():
            logger.info("Datos reales encontrados: %s", ruta)
            df = pd.read_csv(ruta, parse_dates=["fecha"])
            logger.info("  %d registros (%s → %s)",
                        len(df), df["fecha"].min().date(), df["fecha"].max().date())
            return df, False

    logger.info("Sin datos reales en data/raw/. Generando datos sintéticos de precipitación...")
    return _generar_sintetico(), True


def _generar_sintetico() -> pd.DataFrame:
    """Genera serie mensual sintética de precipitación acumulada (mm/mes) 1990-2025.

    Modelo:
        precip[t] = μ + A_bimodal(t) + AR(1)[t] + eventos_extremos[t]

    Componentes:
    - Media 120 mm/mes, consistente con cuencas andinas del centro de Colombia
      (Cuenca del Bogotá, cuencas cafeteras ~ 1000-2000 mm/año).
    - Estacionalidad bimodal: picos en abril y octubre (temporadas húmedas
      andinas). Usamos suma de dos sinusoidales con desfase de 6 meses.
    - AR(1) con ρ=0.55: persistencia de anomalías (El Niño seco consecutivo,
      La Niña húmeda consecutiva) sin integración completa.
    - Eventos extremos: La Niña produce pulsos de precipitación alta
      (probabilidad 4% mensual, ~ 3 eventos extremos por año en promedio).
      Los eventos El Niño se modelan como reducción via ONI sintético en el paso 8.
    - No se eliminan picos extremos (ADR-002): son señal real de riesgo.
    """
    rng = np.random.default_rng(2024)
    fechas = pd.date_range(INICIO_SINTETICO, FIN_SINTETICO, freq="MS")
    n = len(fechas)
    mes = fechas.month.values
    anio = fechas.year.values
    t = np.arange(n)

    # Estacionalidad bimodal: primer pico abril (mes 4), segundo pico octubre (mes 10)
    # Se modela como suma de dos cosenos desfasados 6 meses
    seasonal = (
        PRECIP_AMP_ANUAL * 0.65 * np.cos(2 * np.pi * (mes - 4) / 12)
        + PRECIP_AMP_ANUAL * 0.35 * np.cos(2 * np.pi * (mes - 10) / 12)
    )

    # AR(1) con ruido blanco
    sigma_innov = SIGMA_RUIDO * np.sqrt(1 - RHO_AR1 ** 2)
    ar1 = np.zeros(n)
    ar1[0] = rng.normal(0, SIGMA_RUIDO)
    for i in range(1, n):
        ar1[i] = RHO_AR1 * ar1[i - 1] + rng.normal(0, sigma_innov)

    # Eventos extremos (La Niña / lluvias anómalas)
    # Se concentran en temporadas bimodales para mayor realismo
    extremos = np.zeros(n)
    mask_humedas = np.isin(mes, [3, 4, 5, 9, 10, 11])  # MAMSON bimodal
    for i in range(n):
        if mask_humedas[i] and rng.random() < PROB_EXTREMO:
            extremos[i] = rng.normal(EXTREMO_MED, EXTREMO_SD)

    # Precipitación total
    precip = PRECIP_MEDIA + seasonal + ar1 + extremos
    # Clipeamos solo el mínimo (no puede llover negativo); el máximo lo dejamos
    # sin clip por encima de PRECIP_MAX solo si supera el límite físico absoluto
    precip = np.clip(precip, PRECIP_MIN, PRECIP_MAX)

    df = pd.DataFrame({
        "fecha":            fechas,
        "precipitacion_mm": np.round(precip, 1),
        "estacion":         "Red_IDEAM_Sintetico",
    })
    logger.info("Sintético generado: %d meses (%s → %s)", n,
                fechas[0].strftime("%Y-%m"), fechas[-1].strftime("%Y-%m"))
    logger.info("  Media=%.1fmm | std=%.1fmm | min=%.1fmm | max=%.1fmm",
                df["precipitacion_mm"].mean(), df["precipitacion_mm"].std(),
                df["precipitacion_mm"].min(), df["precipitacion_mm"].max())
    n_extremos = int((extremos > 0).sum())
    logger.info("  Eventos extremos simulados: %d (%.1f%%)",
                n_extremos, n_extremos / n * 100)

    out_path = OUTPUT / "gestion_riesgo_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos sintéticos guardados: %s", out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar_datos(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='gestion_riesgo').

    'gestion_riesgo' no tiene rangos específicos en _LINEA_RANGES, por lo
    que se usan los rangos base de precipitacion_mes (0-2000 mm/mes)
    definidos en PHYSICAL_RANGES. El validador detectará valores físicamente
    imposibles y duplicados de fecha.
    """
    logger.info("--- Validación de dominio (gestion_riesgo) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate

        # Renombramos la columna para que el validador reconozca el rango
        # físico de precipitacion_mes en PHYSICAL_RANGES
        df_val = df.rename(columns={"precipitacion_mm": "precipitacion_mes"})
        report = validate(df_val, date_col="fecha", linea_tematica="gestion_riesgo")
        logger.info(report.summary())
        resultados = {
            "n_rows":           report.n_rows,
            "n_cols":           report.n_cols,
            "missing":          report.missing,
            "duplicates_exact": report.duplicates_exact,
            "range_violations": {
                k: {kk: vv for kk, vv in v.items() if kk != "range"}
                for k, v in report.range_violations.items()
            },
            "has_issues":       report.has_issues(),
        }
        logger.info("Validación: %s", "con issues" if report.has_issues() else "sin problemas")
    except Exception as e:
        logger.warning("Validación skipped: %s", e)

    out_path = OUTPUT / "gestion_riesgo_validacion.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Validación guardada: %s", out_path.name)
    return resultados


# ===========================================================================
# 3. EDA DE CALIDAD PROFUNDA
# ===========================================================================

def eda_calidad(df: pd.DataFrame) -> None:
    """Análisis profundo de calidad de datos con assess_quality."""
    logger.info("--- EDA: calidad profunda ---")
    try:
        from estadistica_ambiental.eda.quality import assess_quality
        report = assess_quality(df, date_col="fecha", numeric_cols=["precipitacion_mm"])
        logger.info(report.summary())
    except Exception as e:
        logger.warning("assess_quality skipped: %s", e)


# ===========================================================================
# 4. ESTADÍSTICA DESCRIPTIVA
# ===========================================================================

def estadistica_descriptiva(df: pd.DataFrame) -> None:
    """Descriptiva completa + distribución de percentiles de riesgo."""
    logger.info("--- Estadística descriptiva ---")
    s = df["precipitacion_mm"]
    logger.info("  N=%d | media=%.1fmm | std=%.1fmm | mediana=%.1fmm",
                len(s), s.mean(), s.std(), s.median())
    logger.info("  min=%.1fmm | p25=%.1fmm | p75=%.1fmm | p90=%.1fmm | max=%.1fmm",
                s.min(), s.quantile(0.25), s.quantile(0.75),
                s.quantile(0.90), s.max())

    # Percentiles de riesgo operativo
    umbrales = {
        "Alerta temprana (p75)":  float(s.quantile(0.75)),
        "Alerta media    (p85)":  float(s.quantile(0.85)),
        "Alerta alta     (p90)":  float(s.quantile(0.90)),
        "Alerta crítica  (p95)":  float(s.quantile(0.95)),
        "Umbral Riesgo PMGRD":    UMBRAL_ALERTA_MM,
    }
    logger.info("Percentiles de riesgo (precipitación mm/mes):")
    for nombre, valor in umbrales.items():
        n_exceed = int((s > valor).sum())
        logger.info("  %-28s %.1f mm → %d meses excedidos (%.1f%%)",
                    nombre, valor, n_exceed, n_exceed / len(s) * 100)

    # Estacionalidad mensual
    mensual = (
        df.groupby(df["fecha"].dt.month)["precipitacion_mm"]
        .agg(["mean", "std", "max"])
        .round(1)
    )
    logger.info("Estacionalidad mensual precipitación:")
    for mes, row in mensual.iterrows():
        flag = " (*)" if row["mean"] > PRECIP_MEDIA * 1.3 else ""
        logger.info("  Mes %02d: media=%6.1fmm | std=%5.1fmm | max=%6.1fmm%s",
                    mes, row["mean"], row["std"], row["max"], flag)


# ===========================================================================
# 5. ANÁLISIS DE EXCEDENCIAS (ADR-008 adaptado)
# ===========================================================================

def analisis_excedencias(serie: pd.Series) -> pd.DataFrame:
    """Análisis de excedencias del umbral de alerta de precipitación.

    La precipitación no tiene normas colombianas en el sentido de Res. 2254
    (calidad del aire) ni Res. 2115 (agua potable). Por ello, usamos
    exceedance_probability() directamente con el umbral empírico de riesgo
    definido en UMBRAL_ALERTA_MM.

    Se construye manualmente una tabla de excedencias compatible con el
    formato de exceedance_report() para poder invocar compliance_report()
    con un umbral personalizado (custom_thresholds).

    Umbral 300 mm/mes: ver nota al inicio del módulo sobre su origen.
    """
    logger.info("--- Análisis de excedencias (umbral=%g mm/mes) ---", UMBRAL_ALERTA_MM)
    try:
        from estadistica_ambiental.inference.intervals import exceedance_probability, ci_quantile_bootstrap

        # Probabilidad de excedencia del umbral de riesgo
        exc = exceedance_probability(serie, threshold=UMBRAL_ALERTA_MM)
        logger.info("  P(precip > %g mm/mes) = %.2f%% (%d meses excedidos)",
                    UMBRAL_ALERTA_MM,
                    exc["pct_exceed"],
                    exc["n_exceedances"])
        if exc["return_period_days"]:
            logger.info("  Período de retorno: %.1f meses", exc["return_period_days"])

        # IC bootstrap del percentil 95 (para estimación de eventos extremos)
        # Útil para el informe técnico de amenaza por inundación
        ci_p95 = ci_quantile_bootstrap(serie, q=0.95, confidence=0.90, n_boot=2000)
        logger.info("  IC90 del percentil 95: [%.1f, %.1f] mm/mes", ci_p95[0], ci_p95[1])

        # Tabla de excedencias por temporada (bimodal)
        df_temp = serie.to_frame("precipitacion_mm")
        df_temp.index = pd.to_datetime(df_temp.index)
        df_temp["temporada"] = df_temp.index.month.map(
            lambda m: "Húmeda-1 (MAM)" if m in (3, 4, 5)
            else "Húmeda-2 (SON)" if m in (9, 10, 11)
            else "Seca"
        )
        logger.info("Excedencias por temporada (> %g mm/mes):", UMBRAL_ALERTA_MM)
        for temporada, grp in df_temp.groupby("temporada"):
            n = int((grp["precipitacion_mm"] > UMBRAL_ALERTA_MM).sum())
            logger.info("  %-20s %d meses (%.1f%%)", temporada, n, n / len(grp) * 100)

        # Guardar tabla de excedencias
        rows = [
            {
                "umbral_mm":       UMBRAL_ALERTA_MM,
                "clasificacion":   "Riesgo alto (PMGRD / POT empírico)",
                "n_exceedances":   exc["n_exceedances"],
                "pct_exceed":      exc["pct_exceed"],
                "return_period_m": exc["return_period_days"],
                "p95_ic90_lo":     ci_p95[0],
                "p95_ic90_hi":     ci_p95[1],
            }
        ]
        df_exc = pd.DataFrame(rows)
        out_path = OUTPUT / "gestion_riesgo_exceedances.csv"
        df_exc.to_csv(out_path, index=False)
        logger.info("Tabla de excedencias guardada: %s", out_path.name)
        return df_exc

    except Exception as e:
        logger.warning("Análisis de excedencias skipped: %s", e)
        return pd.DataFrame()


# ===========================================================================
# 6. ESTACIONARIEDAD — ADF + KPSS (ADR-004)
# ===========================================================================

def estacionariedad(serie: pd.Series) -> dict:
    """ADF + KPSS obligatorios antes de ARIMA (ADR-004).

    La precipitación mensual suele ser estacionaria en media (sin tendencia
    secular fuerte) pero puede mostrar cambios de varianza. Si ADF rechaza
    la raíz unitaria y KPSS no rechaza la estacionariedad, usamos d=0.
    En caso contrario, usamos d=1 en SARIMA.
    """
    logger.info("--- Estacionariedad (ADF + KPSS) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf  = adf_test(serie)
        kpss = kpss_test(serie)
        resultados = {
            "adf_stationary":  bool(adf["stationary"]),
            "adf_pvalue":      round(float(adf["pval"]), 6),
            "kpss_stationary": bool(kpss["stationary"]),
            "kpss_pvalue":     round(float(kpss["pval"]), 6),
        }
        logger.info("ADF:  %s (p=%.6f)",
                    "estacionaria" if resultados["adf_stationary"] else "NO estacionaria",
                    resultados["adf_pvalue"])
        logger.info("KPSS: %s (p=%.6f)",
                    "estacionaria" if resultados["kpss_stationary"] else "NO estacionaria",
                    resultados["kpss_pvalue"])

        if resultados["adf_stationary"] and resultados["kpss_stationary"]:
            logger.info("  Diagnóstico conjunto: ESTACIONARIA — d=0 en SARIMA")
        elif not resultados["adf_stationary"] and not resultados["kpss_stationary"]:
            logger.info("  Diagnóstico conjunto: NO estacionaria — usar d=1")
        else:
            logger.info("  Diagnóstico conjunto: evidencia mixta — revisar ACF/PACF")
    except Exception as e:
        logger.warning("Estacionariedad skipped: %s", e)
    return resultados


# ===========================================================================
# 7. DESCOMPOSICIÓN STL
# ===========================================================================

def descomposicion_stl(serie: pd.Series) -> pd.DataFrame:
    """STL (period=12) sobre precipitación mensual.

    La estacionalidad bimodal se captura porque STL no impone una forma
    sinusoidal simple — extrae el patrón mensual promedio de la señal.
    robust=True es importante porque los eventos extremos (La Niña)
    actúan como outliers que distorsionarían la descomposición clásica.
    """
    logger.info("--- STL (period=12, robust=True) ---")
    try:
        from estadistica_ambiental.descriptive.temporal import decompose_stl
        stl = decompose_stl(serie, period=12, robust=True)
        logger.info("STL — trend std=%.2f | seasonal amp=%.2fmm | residual std=%.2f",
                    stl["trend"].std(),
                    stl["seasonal"].abs().mean(),
                    stl["residual"].std())
        out_path = OUTPUT / "gestion_riesgo_stl.csv"
        stl.to_csv(out_path)
        logger.info("STL guardado: %s", out_path.name)
        return stl
    except Exception as e:
        logger.warning("STL skipped: %s", e)
        return pd.DataFrame()


# ===========================================================================
# 8. ENSO LAGGED (ADR-007)
# ===========================================================================

def _generar_oni_sintetico(n_meses: int, inicio: str) -> pd.DataFrame:
    """ONI sintético AR(1) — fallback si NOAA no está disponible."""
    from estadistica_ambiental.config import ENSO_THRESHOLDS
    rng = np.random.default_rng(42)
    phi, sigma = 0.85, 0.6 * np.sqrt(1 - 0.85 ** 2)
    oni_vals = np.zeros(n_meses)
    oni_vals[0] = rng.normal(0, 0.6)
    for i in range(1, n_meses):
        oni_vals[i] = phi * oni_vals[i - 1] + rng.normal(0, sigma)
    oni_vals = np.clip(oni_vals, -2.5, 2.5)
    fechas = pd.date_range(inicio, periods=n_meses, freq="MS")
    fase = pd.Series(oni_vals).apply(
        lambda v: "niño" if v >= ENSO_THRESHOLDS["nino"] else
                  "niña" if v <= ENSO_THRESHOLDS["nina"] else "neutro"
    )
    intensidad = pd.Series(oni_vals).apply(
        lambda v: "fuerte" if (v >= ENSO_THRESHOLDS["nino_fuerte"] or
                               v <= ENSO_THRESHOLDS["nina_fuerte"])
                  else ("moderado" if (v >= ENSO_THRESHOLDS["nino"] or
                                       v <= ENSO_THRESHOLDS["nina"])
                        else "neutro")
    )
    return pd.DataFrame({
        "fecha": fechas, "oni": np.round(oni_vals, 2),
        "fase": fase.values, "intensidad": intensidad.values,
    })


def aplicar_enso_lag(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica ENSO lagged con lag leído de config.ENSO_LAG_MESES["gestion_riesgo"].

    El lag de 1 mes para gestión de riesgo refleja que las inundaciones
    responden casi de forma inmediata a la forzante ENSO: los eventos
    El Niño (ONI > 0.5) reducen precipitación en la mayoría del país,
    mientras que La Niña (ONI < -0.5) incrementa el riesgo de inundación.
    El lag de 1 mes permite anticipar el riesgo con un ciclo de desfase
    teleconexión → anomalía de precipitación → inundación.
    Referencia: IDEAM Boletín ENSO; UNGRD análisis histórico inundaciones.
    (ADR-007: usar enso_lagged() en lugar de enso_dummy()).
    """
    logger.info("--- ENSO lagged ---")
    try:
        from estadistica_ambiental.features.climate import load_oni, enso_lagged
        from estadistica_ambiental.config import ENSO_LAG_MESES

        lag = ENSO_LAG_MESES.get("gestion_riesgo", 1)
        logger.info("  Lag configurado para gestion_riesgo: %d mes(es) (config.ENSO_LAG_MESES)", lag)

        oni = load_oni()
        if oni.empty:
            logger.warning("  ONI no descargado — usando ONI sintético.")
            n_meses = len(df) + lag + 12
            inicio_str = str(pd.to_datetime(df["fecha"].iloc[0]).strftime("%Y-%m"))
            # Extraer fecha de inicio de la serie para el ONI sintético
            primer_anio = pd.to_datetime(df["fecha"].iloc[0]).year
            oni_inicio = f"{max(primer_anio - 1, 1980)}-01"
            oni = _generar_oni_sintetico(n_meses + 24, oni_inicio)

        df_out = enso_lagged(
            df.copy(),
            oni_df=oni,
            date_col="fecha",
            linea_tematica="gestion_riesgo",
        )
        lag_col = [c for c in df_out.columns if c.startswith("oni_lag")]
        if lag_col:
            stats = df_out[lag_col[0]].describe()
            logger.info("  %s: media=%.3f | std=%.3f", lag_col[0], stats["mean"], stats["std"])
        enso_cols = [c for c in df_out.columns if "lag" in c or "enso" in c.lower()]
        logger.info("  Columnas ENSO añadidas: %s", enso_cols)

        # Log estadística por fase ENSO
        fase_col = [c for c in df_out.columns if c.startswith("fase_lag")]
        if fase_col and fase_col[0] in df_out.columns:
            df_out_copy = df_out.copy()
            df_out_copy["fase_enso"] = df_out_copy[fase_col[0]]
            precip_por_fase = df_out_copy.groupby("fase_enso")["precipitacion_mm"].agg(["mean", "max"])
            logger.info("Precipitación media por fase ENSO (mm/mes):")
            for fase, row in precip_por_fase.iterrows():
                logger.info("  %-10s media=%.1fmm | max=%.1fmm", fase, row["mean"], row["max"])

        return df_out
    except Exception as e:
        logger.warning("ENSO lagged skipped: %s — continuando sin covariable ENSO.", e)
        return df


# ===========================================================================
# 9 & 10. MODELADO PREDICTIVO — SARIMA + ETS + COMPARACIÓN
# ===========================================================================

def modelado_predictivo(serie: pd.Series, stat_result: dict) -> dict:
    """SARIMA + ETS — walk_forward(domain='general'), rank_models().

    Modelos:
    - SARIMA(1,0,1)(1,1,1,12): d=0 si estacionaria, d=1 si no.
      Diferenciación estacional D=1 captura el ciclo anual de precipitación.
    - ETS multiplicativo: la varianza de precipitación crece con la media
      (más lluvia → más variabilidad en meses húmedos); el modelo
      multiplicativo captura esta heteroscedasticidad mejor que el aditivo.

    Métricas: RMSE, MAE, sMAPE (domain='general').
    sMAPE es apropiado aquí porque la precipitación siempre es ≥ 0
    y las series no tienen valores cercanos a cero en meses húmedos.
    (ADR-003: no usar RMSLE en variables que pueden tener ceros).
    """
    logger.info("--- Modelado predictivo (SARIMA + ETS) ---")
    logger.info("Serie: %d meses (%s → %s)",
                len(serie), serie.index.min().strftime("%Y-%m"),
                serie.index.max().strftime("%Y-%m"))

    # Elegir d según el diagnóstico de estacionariedad
    adf_stat  = stat_result.get("adf_stationary", True)
    kpss_stat = stat_result.get("kpss_stationary", True)
    d = 0 if (adf_stat and kpss_stat) else 1
    logger.info("  Orden de integración d=%d (ADF=%s, KPSS=%s)",
                d,
                "estacionaria" if adf_stat else "NO",
                "estacionaria" if kpss_stat else "NO")

    resultados_bt: dict = {}
    preds_test:    dict = {}
    metrics_test:  dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel, ETSModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward
        from estadistica_ambiental.evaluation.comparison import rank_models

        sarima_name = f"SARIMA(1,{d},1)(1,1,1,12)"

        # -- SARIMA --
        sarima = SARIMAXModel(
            order=(1, d, 1),
            seasonal_order=(1, 1, 1, 12),
        )
        logger.info("Walk-forward %s — 5 folds, horizon=6 meses...", sarima_name)
        bt_sarima = walk_forward(
            model=sarima,
            y=serie,
            horizon=6,
            n_splits=5,
            domain="general",
        )
        resultados_bt[sarima_name] = bt_sarima
        m_s = bt_sarima["metrics"]
        logger.info("  %s — RMSE=%.2f | MAE=%.2f | sMAPE=%.2f%%",
                    sarima_name,
                    m_s.get("rmse", float("nan")),
                    m_s.get("mae", float("nan")),
                    m_s.get("smape", float("nan")))

        # -- ETS multiplicativo --
        # El error multiplicativo captura que la varianza de precipitación
        # escala con la magnitud de la serie (más común en variables
        # positivas con fuerte estacionalidad multiplicativa).
        ets = ETSModel(
            trend="add",
            seasonal="mul",       # multiplicativo: varianza proporcional a la media
            seasonal_periods=12,
            damped_trend=False,   # sin amortiguamiento para precipitación con ciclos regulares
        )
        ets_name = "ETS_mul_estacional"
        logger.info("Walk-forward %s — 5 folds, horizon=6 meses...", ets_name)
        bt_ets = walk_forward(
            model=ets,
            y=serie,
            horizon=6,
            n_splits=5,
            domain="general",
        )
        resultados_bt[ets_name] = bt_ets
        m_e = bt_ets["metrics"]
        logger.info("  %s — RMSE=%.2f | MAE=%.2f | sMAPE=%.2f%%",
                    ets_name,
                    m_e.get("rmse", float("nan")),
                    m_e.get("mae", float("nan")),
                    m_e.get("smape", float("nan")))

        # -- Ranking multi-criterio (general) --
        # Pesos default: rmse=0.35, mae=0.30, r2=0.20, mase=0.15
        ranking = rank_models(resultados_bt, domain="general")
        logger.info("Ranking de modelos (domain='general'):")
        logger.info("\n%s", ranking.to_string())
        mejor = str(ranking.index[0])
        logger.info("Mejor modelo: %s (score=%.4f)", mejor, float(ranking.loc[mejor, "score"]))

        # Guardar métricas por fold del mejor modelo
        bt_mejor = resultados_bt[mejor]
        if not bt_mejor["folds"].empty:
            fold_path = OUTPUT / "gestion_riesgo_backtesting.csv"
            bt_mejor["folds"].to_csv(fold_path, index=False)
            logger.info("Métricas por fold guardadas: %s", fold_path.name)

        # Pronóstico 12 meses
        logger.info("Generando pronóstico 12 meses con %s...", mejor)
        if "SARIMA" in mejor:
            model_final = SARIMAXModel(order=(1, d, 1), seasonal_order=(1, 1, 1, 12))
        else:
            model_final = ETSModel(trend="add", seasonal="mul",
                                   seasonal_periods=12, damped_trend=False)
        model_final.fit(serie)
        forecast_vals = model_final.predict(12)
        forecast_vals = np.clip(forecast_vals, PRECIP_MIN, PRECIP_MAX)
        forecast_idx = pd.date_range(
            start=serie.index.max() + pd.DateOffset(months=1),
            periods=12, freq="MS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="precipitacion_mm_forecast")
        fcast_path = OUTPUT / "gestion_riesgo_forecast_12m.csv"
        forecast.to_csv(fcast_path, header=True)
        logger.info("Pronóstico 12m: media=%.1fmm | [%.1f, %.1f]",
                    forecast.mean(), forecast.min(), forecast.max())
        n_alertas = int((forecast > UMBRAL_ALERTA_MM).sum())
        logger.info("  Meses pronosticados en zona de alerta (>%gmm): %d",
                    UMBRAL_ALERTA_MM, n_alertas)

        # Preparar datos para reportes
        for model_name, bt in resultados_bt.items():
            preds_df = bt.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                preds_test[model_name] = preds_df["predicted"].values
            else:
                preds_test[model_name] = forecast_vals
            metrics_test[model_name] = bt["metrics"]

        n_preds = max(len(v) for v in preds_test.values()) if preds_test else 24
        y_test  = serie.iloc[-n_preds:] if n_preds <= len(serie) else serie

        return {
            "ranking":      ranking,
            "mejor_modelo": mejor,
            "d":            d,
            "preds_test":   preds_test,
            "metrics_test": metrics_test,
            "y_test":       y_test,
            "forecast_12m": forecast,
        }

    except Exception as e:
        logger.error("Modelado predictivo falló: %s", e)
        import traceback
        traceback.print_exc()
        return {}


# ===========================================================================
# 11. COMPLIANCE REPORT — UMBRALES PERSONALIZADOS (ADR-008 adaptado)
# ===========================================================================

def generar_compliance_report(df: pd.DataFrame) -> None:
    """Genera reporte HTML de cumplimiento de umbrales de precipitación.

    compliance_report() está diseñado para normas colombianas de calidad
    del aire y agua (Res. 2254, 2115, 631). Para precipitación no existe
    una norma con umbral único y nacional; por eso se usa el parámetro
    custom_thresholds con el umbral de riesgo PMGRD definido en este script.

    El reporte muestra la proporción de meses que superan el umbral de
    alerta, lo que es útil para informes de gestión de riesgo municipal.
    """
    logger.info("--- Generando compliance report (umbrales personalizados) ---")
    try:
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        # compliance_report espera columna con nombre reconocido.
        # Como 'precipitacion_mm' no está en _NORMA_MAP, se usa solo el
        # umbral personalizado (custom_thresholds).
        df_rep = df[["fecha", "precipitacion_mm"]].copy()

        out_path = compliance_report(
            df=df_rep,
            variables=["precipitacion_mm"],
            date_col="fecha",
            linea_tematica="gestion_riesgo",
            output=str(REPORTS / "cumplimiento_precipitacion.html"),
            title="Análisis de Excedencias de Precipitación — Gestión del Riesgo",
            custom_thresholds={
                # 300 mm/mes: umbral empírico de riesgo alto por inundación
                # (POTs municipales con amenaza media-alta, cuencas andinas)
                "precipitacion_mm": UMBRAL_ALERTA_MM,
            },
        )
        logger.info("Compliance report guardado: %s", out_path)
    except Exception as e:
        logger.warning("compliance_report skipped: %s", e)


# ===========================================================================
# 12. REPORTE HTML DE PRONÓSTICO
# ===========================================================================

def generar_reporte_forecast(resultados: dict, serie: pd.Series) -> None:
    """Genera reporte HTML con métricas RMSE, MAE, sMAPE."""
    logger.info("--- Generando reporte de pronóstico ---")
    if not resultados:
        logger.warning("Sin resultados de modelado — reporte no generado.")
        return
    try:
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        y_test       = resultados.get("y_test",       serie.iloc[-12:])
        preds_test   = resultados.get("preds_test",   {})
        metrics_test = resultados.get("metrics_test", {})
        mejor        = resultados.get("mejor_modelo", "—")
        d            = resultados.get("d", 0)

        # Alinear longitudes
        n_test = len(y_test)
        preds_aligned = {}
        for name, arr in preds_test.items():
            if len(arr) >= n_test:
                preds_aligned[name] = arr[-n_test:]
            else:
                pad = np.full(n_test - len(arr), float(serie.mean()))
                preds_aligned[name] = np.concatenate([pad, arr])

        report_path = REPORTS / "gestion_riesgo_forecast.html"
        forecast_report(
            y_true=y_test,
            predictions=preds_aligned,
            metrics=metrics_test,
            output=str(report_path),
            title=f"Pronóstico Precipitación — Gestión del Riesgo | Mejor: {mejor}",
            variable_name="Precipitación acumulada",
            unit="mm/mes",
        )
        logger.info("Reporte HTML guardado: %s", report_path)
    except Exception as e:
        logger.warning("forecast_report skipped: %s", e)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 70)
    logger.info("FASE 8 — Gestión del Riesgo | Precipitación acumulada (mm/mes)")
    logger.info("Métricas: RMSE, MAE, sMAPE (domain='general')")
    logger.info("Umbral alerta: > %.0f mm/mes (riesgo alto de inundación)", UMBRAL_ALERTA_MM)
    logger.info("ENSO: lag leído de config.ENSO_LAG_MESES['gestion_riesgo']")
    logger.info("=" * 70)

    # 1. Cargar o generar datos
    try:
        df, es_sintetico = cargar_o_generar_datos()
    except Exception as e:
        logger.error("Carga de datos falló: %s", e)
        return
    logger.info("Fuente de datos: %s", "SINTÉTICOS" if es_sintetico else "REALES")

    # 2. Validación
    try:
        validar_datos(df)
    except Exception as e:
        logger.warning("Validación falló: %s", e)

    # 3. EDA de calidad profunda
    try:
        eda_calidad(df)
    except Exception as e:
        logger.warning("EDA falló: %s", e)

    # 4. Estadística descriptiva
    try:
        estadistica_descriptiva(df)
    except Exception as e:
        logger.warning("Descriptiva falló: %s", e)

    # Construir serie indexada para pasos subsiguientes
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    serie: pd.Series = (
        df.set_index("fecha")["precipitacion_mm"]
        .asfreq("MS")
        .fillna(method="ffill")  # imputación simple para posibles gaps
    )
    serie.name = "precipitacion_mm"

    # 5. Análisis de excedencias
    try:
        analisis_excedencias(serie)
    except Exception as e:
        logger.warning("Excedencias falló: %s", e)

    # 6. Estacionariedad
    stat_result: dict = {}
    try:
        stat_result = estacionariedad(serie)
    except Exception as e:
        logger.warning("Estacionariedad falló: %s", e)

    # 7. STL
    try:
        descomposicion_stl(serie)
    except Exception as e:
        logger.warning("STL falló: %s", e)

    # 8. ENSO lagged
    try:
        df_enso = aplicar_enso_lag(df[["fecha", "precipitacion_mm"]].copy())
    except Exception as e:
        logger.warning("ENSO lag falló: %s", e)

    # 9 & 10. Modelado predictivo + ranking
    try:
        resultados = modelado_predictivo(serie, stat_result)
    except Exception as e:
        logger.warning("Modelado falló: %s", e)
        resultados = {}

    # 11. Compliance report
    try:
        generar_compliance_report(df)
    except Exception as e:
        logger.warning("Compliance report falló: %s", e)

    # 12. Reporte HTML de pronóstico
    try:
        generar_reporte_forecast(resultados, serie)
    except Exception as e:
        logger.warning("Reporte forecast falló: %s", e)

    # Resumen ejecutivo
    logger.info("=" * 70)
    logger.info("RESUMEN EJECUTIVO — Gestión del Riesgo")
    logger.info("  Período: %s → %s",
                df["fecha"].min().strftime("%Y-%m"), df["fecha"].max().strftime("%Y-%m"))
    logger.info("  N meses: %d", len(serie))
    logger.info("  Precipitación media: %.1fmm | std: %.1fmm", serie.mean(), serie.std())
    n_alertas_hist = int((serie > UMBRAL_ALERTA_MM).sum())
    logger.info("  Meses históricos > %gmm: %d (%.1f%%)",
                UMBRAL_ALERTA_MM, n_alertas_hist, n_alertas_hist / len(serie) * 100)
    if resultados:
        mejor = resultados.get("mejor_modelo", "—")
        m = resultados.get("metrics_test", {}).get(mejor, {})
        logger.info("  Mejor modelo: %s", mejor)
        logger.info("    RMSE=%.2fmm | MAE=%.2fmm | sMAPE=%.2f%%",
                    m.get("rmse", float("nan")),
                    m.get("mae", float("nan")),
                    m.get("smape", float("nan")))
        fc = resultados.get("forecast_12m")
        if fc is not None:
            n_alertas_fc = int((fc > UMBRAL_ALERTA_MM).sum())
            logger.info("  Pronóstico 12m: media=%.1fmm | meses en alerta: %d",
                        fc.mean(), n_alertas_fc)
    logger.info("  Reportes:")
    logger.info("    - %s", REPORTS / "gestion_riesgo_forecast.html")
    logger.info("    - %s", REPORTS / "cumplimiento_precipitacion.html")
    logger.info("  Salidas intermedias: %s", OUTPUT)
    logger.info("=" * 70)
    logger.info("Fase 8 Gestión del Riesgo completada.")


if __name__ == "__main__":
    main()
