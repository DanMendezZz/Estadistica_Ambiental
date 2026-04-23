"""
Fase 8 — Ciclo estadístico completo: Humedales.

Línea temática: Humedales
Variable principal: nivel de agua (m) — serie diaria en humedal colombiano
Datos: auto-detecta reales en data/raw/; usa sintéticos como fallback

Flujo:
  1. Carga o generación de datos (nivel de agua diario)
  2. Validación con validate(df, linea_tematica="humedales")
  3. EDA de calidad profunda (assess_quality)
  4. Estadística descriptiva + estacionalidad mensual
  5. Estacionariedad ADF + KPSS (obligatorio antes de ARIMA, ADR-004)
  6. Descomposición STL (period=365 en diaria → resampleamos a mensual)
  7. ENSO lagged — lag leído de config.ENSO_LAG_MESES["humedales"] (ADR-007)
  8. Modelado predictivo: SARIMA + ETS — walk_forward(domain='hydrology')
  9. Ranking multi-criterio rank_models() con NSE, KGE, RMSE
  10. Reporte HTML de pronóstico + notas de dominio

Métricas primarias: NSE, KGE (hidrología — ADR-003)
Métricas secundarias: RMSE, MAE

Sin cumplimiento normativo directo para nivel de agua (no existen límites en
Res. 2254 ni Res. 2115 para esta variable) — se omite compliance_report().

Salidas en data/output/reports/:
    - humedales_forecast.html

Salidas intermedias en data/output/fase8/:
    - humedales_datos.csv
    - humedales_validacion.json
    - humedales_stl.csv
    - humedales_backtesting.csv
    - humedales_forecast_12m.csv

Uso:
    python scripts/fase8_humedales.py
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
logger = logging.getLogger("fase8_humedales")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT      = Path(__file__).parent.parent
DATA_RAW  = ROOT / "data" / "raw"
OUTPUT    = ROOT / "data" / "output" / "fase8"
REPORTS   = ROOT / "data" / "output" / "reports"
OUTPUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Parámetros de generación sintética
# ---------------------------------------------------------------------------
INICIO_SINTETICO = "2010-01-01"
FIN_SINTETICO    = "2023-12-31"
NIVEL_MEDIA      = 0.8      # m — nivel medio del humedal
NIVEL_AMP_ANUAL  = 0.35     # m — amplitud estacional pico (abr-may)
RHO_AR1          = 0.7      # coeficiente AR(1) — persistencia del nivel
SIGMA_RUIDO      = 0.06     # desviación estándar del ruido blanco (m)
PROB_INUNDACION  = 0.015    # probabilidad diaria de evento de inundación
NIVEL_PICO_MED   = 1.8      # m — nivel medio durante inundación
NIVEL_MAX        = 10.0     # m — límite físico (rango humedal, validators.py "nivel_rio")
NIVEL_MIN        = 0.0      # m

# Nombre del archivo de datos reales (si existe)
REAL_DATA_CANDIDATES = [
    "humedales_nivel.csv",
    "humedal_nivel_agua.csv",
    "nivel_humedal.csv",
]


# ===========================================================================
# 1. CARGA O GENERACIÓN DE DATOS
# ===========================================================================

def cargar_o_generar_datos() -> tuple[pd.DataFrame, bool]:
    """Auto-detecta datos reales; usa sintéticos como fallback.

    Returns:
        (DataFrame con columnas fecha, nivel_agua, estacion), es_sintetico: bool
    """
    for nombre in REAL_DATA_CANDIDATES:
        ruta = DATA_RAW / nombre
        if ruta.exists():
            logger.info("Datos reales encontrados: %s", ruta)
            df = pd.read_csv(ruta, parse_dates=["fecha"])
            logger.info("  %d registros cargados (%s → %s)",
                        len(df), df["fecha"].min().date(), df["fecha"].max().date())
            return df, False

    logger.info("Sin datos reales en data/raw/. Generando datos sintéticos de nivel de agua...")
    return _generar_sintetico(), True


def _generar_sintetico() -> pd.DataFrame:
    """Genera serie diaria sintética de nivel de agua en humedal colombiano.

    Modelo: nivel[t] = μ + A_anual(t) + AR(1) + eventos_inundacion
    - Media 0.8 m, fluctuación estacional máxima en abril-mayo (temporada
      húmeda bimodal andina — Chingaza, La Conejera, Jaboque).
    - AR(1) con ρ=0.7 capta persistencia hidrológica del humedal.
    - Eventos de inundación aleatorios simulan pulsos de llenado por lluvia
      intensa o desborde (no se eliminan: picos son señal real, ADR-002).
    - Tendencia nula (±0): nivel no tiene deriva secular en el sintético.
    """
    rng = np.random.default_rng(2024)
    fechas = pd.date_range(INICIO_SINTETICO, FIN_SINTETICO, freq="D")
    n = len(fechas)
    mes = fechas.month.values

    # Estacionalidad: pico en abril (mes 4) y mayo (mes 5)
    # Usamos una función sinusoidal con máximo en mes 4.5 → angulo 2π*(4.5-1)/12
    angulo_pico = 2 * np.pi * (4.5 - 1) / 12
    seasonal = NIVEL_AMP_ANUAL * np.cos(2 * np.pi * (mes - 1) / 12 - angulo_pico)

    # AR(1) con ruido blanco
    sigma_innov = SIGMA_RUIDO * np.sqrt(1 - RHO_AR1 ** 2)
    ar1 = np.zeros(n)
    ar1[0] = rng.normal(0, SIGMA_RUIDO)
    for t in range(1, n):
        ar1[t] = RHO_AR1 * ar1[t - 1] + rng.normal(0, sigma_innov)

    # Nivel base
    nivel = NIVEL_MEDIA + seasonal + ar1

    # Eventos de inundación: pulsos aleatorios (+nivel alto, decaimiento 7-14 días)
    # Representan eventos de lluvia extrema — señal real, no se clipean (ADR-002)
    inundaciones = rng.random(n) < PROB_INUNDACION
    idx_inund = np.where(inundaciones)[0]
    for idx in idx_inund:
        duracion = rng.integers(7, 15)
        magnitud = rng.normal(NIVEL_PICO_MED, 0.3)
        for d in range(min(duracion, n - idx)):
            decaimiento = np.exp(-d / 5)  # decaimiento exponencial ~5 días
            nivel[idx + d] += magnitud * decaimiento

    # Clip solo para valores físicamente imposibles (fuera del rango del sensor)
    nivel = np.clip(nivel, NIVEL_MIN, NIVEL_MAX)

    df = pd.DataFrame({
        "fecha":       fechas,
        "nivel_agua":  np.round(nivel, 3),
        "estacion":    "Humedal_La_Conejera_Sintetico",
    })
    logger.info("Sintético generado: %d días (%s → %s)",
                n, fechas[0].date(), fechas[-1].date())
    logger.info("  Nivel medio=%.3fm | std=%.3fm | min=%.3fm | max=%.3fm",
                df["nivel_agua"].mean(), df["nivel_agua"].std(),
                df["nivel_agua"].min(), df["nivel_agua"].max())
    logger.info("  Eventos de inundación simulados: %d", int(inundaciones.sum()))

    out_path = OUTPUT / "humedales_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos sintéticos guardados: %s", out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar_humedales(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='humedales').

    La línea 'humedales' en validators.py tiene rangos específicos para
    temperatura_agua, pH, OD, conductividad y nivel_rio.
    Para 'nivel_agua' se usará el rango genérico nivel_rio (0-10 m).
    """
    logger.info("--- Validación de dominio (humedales) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate

        # Renombramos nivel_agua → nivel_rio para que el validador reconozca
        # el rango de dominio [0, 10] m definido en _LINEA_RANGES["humedales"]
        df_val = df.rename(columns={"nivel_agua": "nivel_rio"})
        report = validate(df_val, date_col="fecha", linea_tematica="humedales")
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

    out_path = OUTPUT / "humedales_validacion.json"
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
        report = assess_quality(df, date_col="fecha", numeric_cols=["nivel_agua"])
        logger.info(report.summary())
    except Exception as e:
        logger.warning("assess_quality skipped: %s", e)


# ===========================================================================
# 4. ESTADÍSTICA DESCRIPTIVA
# ===========================================================================

def estadistica_descriptiva(df: pd.DataFrame) -> None:
    """Descriptiva básica + estacionalidad mensual del nivel de agua."""
    logger.info("--- Estadística descriptiva ---")
    s = df["nivel_agua"]
    logger.info("  N=%d | media=%.3fm | std=%.3fm | mediana=%.3fm",
                len(s), s.mean(), s.std(), s.median())
    logger.info("  min=%.3fm | p25=%.3fm | p75=%.3fm | max=%.3fm",
                s.min(), s.quantile(0.25), s.quantile(0.75), s.max())

    # Estacionalidad mensual
    mensual = (
        df.groupby(df["fecha"].dt.month)["nivel_agua"]
        .agg(["mean", "std", "min", "max"])
        .round(3)
    )
    logger.info("Estacionalidad mensual nivel de agua (m):")
    for mes, row in mensual.iterrows():
        logger.info("  Mes %02d: media=%.3f | std=%.3f | [%.3f, %.3f]",
                    mes, row["mean"], row["std"], row["min"], row["max"])

    # Percentil 95 — indicativo de nivel de alerta empírico
    p95 = float(s.quantile(0.95))
    logger.info("  Percentil 95 (nivel alto): %.3fm", p95)


# ===========================================================================
# 5. ESTACIONARIEDAD — ADF + KPSS (ADR-004)
# ===========================================================================

def estacionariedad(serie_mensual: pd.Series) -> dict:
    """ADF + KPSS obligatorios antes de ajustar ARIMA (ADR-004).

    Se aplica sobre la serie mensual (promedio diario → mensual) para
    evitar ruido de alta frecuencia y reducir el costo computacional.
    El test sobre la serie diaria larga (>5000 obs) daría el mismo resultado.
    """
    logger.info("--- Estacionariedad (ADF + KPSS) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf  = adf_test(serie_mensual)
        kpss = kpss_test(serie_mensual)
        resultados = {
            "adf_stationary": bool(adf["stationary"]),
            "adf_pvalue":     round(float(adf["pval"]), 6),
            "kpss_stationary": bool(kpss["stationary"]),
            "kpss_pvalue":    round(float(kpss["pval"]), 6),
        }
        logger.info("ADF:  %s (p=%.6f)",
                    "estacionaria" if resultados["adf_stationary"] else "NO estacionaria",
                    resultados["adf_pvalue"])
        logger.info("KPSS: %s (p=%.6f)",
                    "estacionaria" if resultados["kpss_stationary"] else "NO estacionaria",
                    resultados["kpss_pvalue"])

        if resultados["adf_stationary"] and resultados["kpss_stationary"]:
            logger.info("  Diagnóstico conjunto: serie ESTACIONARIA — d=0 en ARIMA")
        elif not resultados["adf_stationary"] and not resultados["kpss_stationary"]:
            logger.info("  Diagnóstico conjunto: NO estacionaria — usar d=1 en ARIMA")
        else:
            logger.info("  Diagnóstico conjunto: evidencia mixta — revisar manualmente")
    except Exception as e:
        logger.warning("Estacionariedad skipped: %s", e)
    return resultados


# ===========================================================================
# 6. DESCOMPOSICIÓN STL
# ===========================================================================

def descomposicion_stl(serie_mensual: pd.Series) -> pd.DataFrame:
    """STL period=12 sobre serie mensual de nivel de agua.

    Se trabaja con datos mensuales (resampleados desde la serie diaria)
    porque STL con period=365 en la serie diaria es muy lento y la
    componente estacional ya es visible a escala mensual.
    """
    logger.info("--- STL (period=12) ---")
    try:
        from estadistica_ambiental.descriptive.temporal import decompose_stl
        stl = decompose_stl(serie_mensual, period=12, robust=True)
        logger.info("STL — trend std=%.4f | seasonal amp=%.4f | residual std=%.4f",
                    stl["trend"].std(),
                    stl["seasonal"].abs().mean(),
                    stl["residual"].std())
        out_path = OUTPUT / "humedales_stl.csv"
        stl.to_csv(out_path)
        logger.info("STL guardado: %s", out_path.name)
        return stl
    except Exception as e:
        logger.warning("STL skipped: %s", e)
        return pd.DataFrame()


# ===========================================================================
# 7. ENSO LAGGED (ADR-007)
# ===========================================================================

def _generar_oni_sintetico(n_meses: int, inicio: str) -> pd.DataFrame:
    """ONI sintético AR(1) para el período de análisis.

    Se usa cuando la descarga de NOAA falla (sin conexión o cambio de URL).
    El proceso AR(1) con φ=0.85 reproduce la autocorrelación característica
    del ONI (escala de variación interanual de 12-18 meses).
    """
    from estadistica_ambiental.config import ENSO_THRESHOLDS
    rng = np.random.default_rng(42)
    phi, sigma = 0.85, 0.6 * np.sqrt(1 - 0.85 ** 2)
    oni_vals = np.zeros(n_meses)
    oni_vals[0] = rng.normal(0, 0.6)
    for t in range(1, n_meses):
        oni_vals[t] = phi * oni_vals[t - 1] + rng.normal(0, sigma)
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
        "fecha":      fechas,
        "oni":        np.round(oni_vals, 2),
        "fase":       fase.values,
        "intensidad": intensidad.values,
    })


def aplicar_enso_lag(df_mensual: pd.DataFrame) -> pd.DataFrame:
    """Aplica ENSO lagged sobre la serie mensual de nivel de agua.

    El lag se lee de config.ENSO_LAG_MESES["humedales"] (actualmente 3 meses).
    El lag captura el retraso entre el forzamiento climático ENSO y su
    respuesta en el hidroperiodo del humedal: la precipitación anómala
    asociada a El Niño/La Niña tarda ~3 meses en traducirse en cambios
    significativos del nivel (buffer del suelo saturado y vegetación).
    Referencia: literatura colombiana Magdalena-Cauca y Estudio Nacional del Agua.
    (ADR-007: usar enso_lagged() en lugar de enso_dummy()).
    """
    logger.info("--- ENSO lagged ---")
    try:
        from estadistica_ambiental.features.climate import load_oni, enso_lagged
        from estadistica_ambiental.config import ENSO_LAG_MESES

        lag = ENSO_LAG_MESES.get("humedales", 3)
        logger.info("  Lag configurado para humedales: %d meses (config.ENSO_LAG_MESES)", lag)

        oni = load_oni()
        if oni.empty:
            logger.warning("  ONI no descargado — usando ONI sintético.")
            n_meses = len(df_mensual)
            inicio_str = str(df_mensual["fecha"].iloc[0].date())
            oni = _generar_oni_sintetico(n_meses + lag + 12, inicio_str)

        df_out = enso_lagged(
            df_mensual.copy(),
            oni_df=oni,
            date_col="fecha",
            linea_tematica="humedales",
        )
        lag_col = [c for c in df_out.columns if c.startswith("oni_lag")]
        if lag_col:
            stats = df_out[lag_col[0]].describe()
            logger.info("  %s: media=%.3f | std=%.3f", lag_col[0], stats["mean"], stats["std"])
        enso_cols = [c for c in df_out.columns if "lag" in c or "enso" in c.lower()]
        logger.info("  Columnas ENSO añadidas: %s", enso_cols)
        return df_out
    except Exception as e:
        logger.warning("ENSO lagged skipped: %s — continuando sin covariable ENSO.", e)
        return df_mensual


# ===========================================================================
# 8 & 9. MODELADO PREDICTIVO — SARIMA + ETS + COMPARACIÓN
# ===========================================================================

def modelado_predictivo(serie_mensual: pd.Series) -> dict:
    """SARIMA y ETS — walk-forward con domain='hydrology', rank_models().

    Modelos:
    - SARIMA(1,1,1)(1,1,1,12): captura tendencia (d=1) y estacionalidad anual.
      Parámetros conservadores por la naturaleza no estacionaria del nivel.
    - ETS aditivo: Holt-Winters con estacionalidad y amortiguación de tendencia.
      Robusto cuando hay quiebres estructurales por eventos de inundación.

    Métricas primarias según ADR-003 para hidrología: NSE, KGE.
    NSE < 0 indica que el modelo es peor que la media de la serie.
    KGE penaliza simultáneamente sesgo, dispersión y correlación.
    """
    logger.info("--- Modelado predictivo (SARIMA + ETS) ---")
    logger.info("Serie mensual: %d meses (%s → %s)",
                len(serie_mensual),
                serie_mensual.index.min().date(),
                serie_mensual.index.max().date())

    resultados_bt: dict = {}
    preds_test:    dict = {}
    metrics_test:  dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel, ETSModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward
        from estadistica_ambiental.evaluation.comparison import rank_models
        from estadistica_ambiental.evaluation.metrics import evaluate

        # -- SARIMA(1,1,1)(1,1,1,12) --
        # d=1: la serie mensual de nivel suele ser I(1) por la tendencia estacional
        # interanual; la diferenciación d=1 elimina la raíz unitaria.
        sarima = SARIMAXModel(
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
        )
        logger.info("Walk-forward SARIMA(1,1,1)(1,1,1,12) — 5 folds, horizon=6 meses...")
        bt_sarima = walk_forward(
            model=sarima,
            y=serie_mensual,
            horizon=6,
            n_splits=5,
            domain="hydrology",
        )
        resultados_bt["SARIMA(1,1,1)(1,1,1,12)"] = bt_sarima
        m_s = bt_sarima["metrics"]
        logger.info("  SARIMA — RMSE=%.4f | MAE=%.4f | NSE=%.4f | KGE=%.4f",
                    m_s.get("rmse", float("nan")),
                    m_s.get("mae", float("nan")),
                    m_s.get("nse", float("nan")),
                    m_s.get("kge", float("nan")))

        # -- ETS aditivo amortiguado --
        # Holt-Winters aditivo con damped_trend=True para series con hidroperiodo
        # irregular — el amortiguamiento evita que la tendencia de corto plazo
        # se extrapole de forma irrealista en el horizonte de 6 meses.
        ets = ETSModel(
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            damped_trend=True,
        )
        logger.info("Walk-forward ETS (Holt-Winters aditivo amortiguado) — 5 folds, horizon=6 meses...")
        bt_ets = walk_forward(
            model=ets,
            y=serie_mensual,
            horizon=6,
            n_splits=5,
            domain="hydrology",
        )
        resultados_bt["ETS_Holt_Winters"] = bt_ets
        m_e = bt_ets["metrics"]
        logger.info("  ETS   — RMSE=%.4f | MAE=%.4f | NSE=%.4f | KGE=%.4f",
                    m_e.get("rmse", float("nan")),
                    m_e.get("mae", float("nan")),
                    m_e.get("nse", float("nan")),
                    m_e.get("kge", float("nan")))

        # -- Ranking multi-criterio (hydrology) --
        # Pesos: NSE=0.40, KGE=0.30, RMSE=0.20, pbias=0.10
        ranking = rank_models(resultados_bt, domain="hydrology")
        logger.info("Ranking de modelos (domain='hydrology'):")
        logger.info("\n%s", ranking.to_string())
        mejor = str(ranking.index[0])
        logger.info("Mejor modelo: %s (score=%.4f)", mejor, float(ranking.loc[mejor, "score"]))

        # Guardar métricas por fold del mejor modelo
        bt_mejor = resultados_bt[mejor]
        if not bt_mejor["folds"].empty:
            fold_path = OUTPUT / "humedales_backtesting.csv"
            bt_mejor["folds"].to_csv(fold_path, index=False)
            logger.info("Métricas por fold guardadas: %s", fold_path.name)

        # Pronóstico 12 meses — re-entrena el mejor modelo con todos los datos
        logger.info("Generando pronóstico 12 meses con %s...", mejor)
        if "SARIMA" in mejor:
            model_final = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        else:
            model_final = ETSModel(trend="add", seasonal="add",
                                   seasonal_periods=12, damped_trend=True)
        model_final.fit(serie_mensual)
        forecast_vals = model_final.predict(12)
        forecast_vals = np.clip(forecast_vals, NIVEL_MIN, NIVEL_MAX)
        forecast_idx = pd.date_range(
            start=serie_mensual.index.max() + pd.DateOffset(months=1),
            periods=12, freq="MS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="nivel_agua_forecast_m")
        fcast_path = OUTPUT / "humedales_forecast_12m.csv"
        forecast.to_csv(fcast_path, header=True)
        logger.info("Pronóstico 12m: media=%.3fm | [%.3f, %.3f]",
                    forecast.mean(), forecast.min(), forecast.max())

        # Preparar datos para el reporte (usar predicciones del backtesting)
        for model_name, bt in resultados_bt.items():
            preds_df = bt.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                preds_test[model_name] = preds_df["predicted"].values
            else:
                preds_test[model_name] = forecast_vals
            metrics_test[model_name] = bt["metrics"]

        # Serie de test para el reporte (últimos pasos del backtesting)
        n_preds = max(len(v) for v in preds_test.values()) if preds_test else 24
        y_test = serie_mensual.iloc[-n_preds:] if n_preds <= len(serie_mensual) else serie_mensual

        return {
            "ranking":      ranking,
            "mejor_modelo": mejor,
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
# 10. REPORTE HTML
# ===========================================================================

def generar_reporte(resultados: dict, serie_mensual: pd.Series) -> None:
    """Genera reporte HTML de pronóstico con métricas hidrológicas NSE y KGE."""
    logger.info("--- Generando reporte HTML ---")
    if not resultados:
        logger.warning("Sin resultados de modelado — reporte no generado.")
        return
    try:
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        y_test       = resultados.get("y_test",       serie_mensual.iloc[-12:])
        preds_test   = resultados.get("preds_test",   {})
        metrics_test = resultados.get("metrics_test", {})
        mejor        = resultados.get("mejor_modelo", "—")

        # Alinear longitudes de predicciones con y_test
        n_test = len(y_test)
        preds_aligned = {}
        for name, arr in preds_test.items():
            if len(arr) >= n_test:
                preds_aligned[name] = arr[-n_test:]
            else:
                # Rellenar con la media si el array es más corto
                pad = np.full(n_test - len(arr), float(serie_mensual.mean()))
                preds_aligned[name] = np.concatenate([pad, arr])

        report_path = REPORTS / "humedales_forecast.html"
        forecast_report(
            y_true=y_test,
            predictions=preds_aligned,
            metrics=metrics_test,
            output=str(report_path),
            title=f"Pronóstico Nivel de Agua — Humedales Colombia | Mejor: {mejor}",
            variable_name="Nivel de agua",
            unit="m",
        )
        logger.info("Reporte HTML guardado: %s", report_path)
    except Exception as e:
        logger.warning("forecast_report skipped: %s", e)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 70)
    logger.info("FASE 8 — Humedales | Nivel de agua (m)")
    logger.info("Métricas primarias: NSE, KGE (domain='hydrology')")
    logger.info("ENSO: lag leído de config.ENSO_LAG_MESES['humedales']")
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
        validar_humedales(df)
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

    # Resampleamos a mensual para STL, ENSO y modelado
    # (la serie diaria de nivel es muy larga para SARIMA sin preproceso)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    serie_mensual: pd.Series = (
        df.set_index("fecha")["nivel_agua"]
        .resample("MS")
        .mean()
        .dropna()
    )
    serie_mensual.name = "nivel_agua"
    logger.info("Serie mensual: %d meses (%s → %s)",
                len(serie_mensual),
                serie_mensual.index.min().date(),
                serie_mensual.index.max().date())

    # 5. Estacionariedad
    try:
        estacionariedad(serie_mensual)
    except Exception as e:
        logger.warning("Estacionariedad falló: %s", e)

    # 6. STL
    try:
        descomposicion_stl(serie_mensual)
    except Exception as e:
        logger.warning("STL falló: %s", e)

    # Preparar DataFrame mensual para ENSO
    df_mensual = serie_mensual.reset_index()
    df_mensual.columns = ["fecha", "nivel_agua"]

    # 7. ENSO lagged
    try:
        df_enso = aplicar_enso_lag(df_mensual)
    except Exception as e:
        logger.warning("ENSO lag falló: %s", e)
        df_enso = df_mensual

    # 8 & 9. Modelado predictivo + ranking
    try:
        resultados = modelado_predictivo(serie_mensual)
    except Exception as e:
        logger.warning("Modelado falló: %s", e)
        resultados = {}

    # 10. Reporte HTML
    try:
        generar_reporte(resultados, serie_mensual)
    except Exception as e:
        logger.warning("Reporte HTML falló: %s", e)

    # Resumen ejecutivo
    logger.info("=" * 70)
    logger.info("RESUMEN EJECUTIVO — Humedales")
    logger.info("  Período: %s → %s",
                df["fecha"].min().date(), df["fecha"].max().date())
    logger.info("  N registros diarios: %d | N meses: %d", len(df), len(serie_mensual))
    logger.info("  Nivel medio: %.3fm | std: %.3fm", df["nivel_agua"].mean(), df["nivel_agua"].std())
    if resultados:
        mejor = resultados.get("mejor_modelo", "—")
        m = resultados.get("metrics_test", {}).get(mejor, {})
        logger.info("  Mejor modelo: %s", mejor)
        logger.info("    NSE=%.4f | KGE=%.4f | RMSE=%.4fm | MAE=%.4fm",
                    m.get("nse", float("nan")),
                    m.get("kge", float("nan")),
                    m.get("rmse", float("nan")),
                    m.get("mae", float("nan")))
        fc = resultados.get("forecast_12m")
        if fc is not None:
            logger.info("  Pronóstico 12m: media=%.3fm | [%.3f, %.3f]",
                        fc.mean(), fc.min(), fc.max())
    logger.info("  Reporte: %s", REPORTS / "humedales_forecast.html")
    logger.info("  Salidas intermedias: %s", OUTPUT)
    logger.info("=" * 70)
    logger.info("Fase 8 Humedales completada.")


if __name__ == "__main__":
    main()
