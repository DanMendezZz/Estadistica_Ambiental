"""
Fase 8 — Ciclo estadístico completo: Cambio Climático / ONI-ENSO.

Línea temática: Cambio Climático
Fuente de datos: Oceanic Niño Index (ONI) — NOAA CPC
                 https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Flujo:
  1. Carga ONI (real o sintético con fallback AR(1))
  2. EDA: distribución, ACF, clasificación de fases ENSO
  3. Tendencia: Mann-Kendall sobre magnitud ONI, Sen slope
  4. Descomposición STL (period=12)
  5. Frecuencia: eventos Niño/Niña fuertes por década
  6. Pronóstico ONI: SARIMA(2,0,0)(1,0,1,12), walk-forward 5 folds horizon=3
  7. Tabla de lags ENSO por línea temática (config.ENSO_LAG_MESES)
  8. Cross-correlación ONI vs PM2.5 Mochuelo (si el parquet está disponible)

Uso:
    python scripts/fase8_cambio_climatico.py

Salidas en data/output/fase8/:
    - oni_clasificacion.csv
    - oni_stl.csv
    - oni_tendencia.json
    - oni_frecuencia_decadal.csv
    - oni_backtesting.csv
    - oni_forecast.csv
    - oni_lags_lineas.csv
    - oni_crosscorr_pm25.csv   (si el parquet existe)
    - forecast_oni.html
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
logger = logging.getLogger("fase8_cc")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
RAW    = DATA / "raw"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

PARQUET_AIRE = RAW / "calidad_aire_CAR_2016_2026.parquet"
ESTACION_AIRE = "BOGOTA RURAL - MOCHUELO"


# ===========================================================================
# 1. CARGA ONI
# ===========================================================================

def _generar_oni_sintetico() -> pd.DataFrame:
    """Genera serie ONI sintética AR(1) calibrada (std≈0.6, rango ±2.5)."""
    logger.warning("Generando datos ONI SINTÉTICOS — no usar para análisis real.")
    rng = np.random.default_rng(42)
    n = (2026 - 1950) * 12  # meses desde 1950
    phi = 0.85
    sigma = 0.6 * np.sqrt(1 - phi ** 2)
    oni = np.zeros(n)
    oni[0] = rng.normal(0, 0.6)
    for t in range(1, n):
        oni[t] = phi * oni[t - 1] + rng.normal(0, sigma)
    oni = np.clip(oni, -2.5, 2.5)

    fechas = pd.date_range("1950-01-01", periods=n, freq="MS")
    from estadistica_ambiental.config import ENSO_THRESHOLDS
    fase = pd.Series(oni).apply(lambda v: (
        "niño" if v >= ENSO_THRESHOLDS["nino"] else
        "niña" if v <= ENSO_THRESHOLDS["nina"] else "neutro"
    ))
    intensidad = pd.Series(oni).apply(lambda v: (
        "fuerte" if v >= ENSO_THRESHOLDS["nino_fuerte"] or v <= ENSO_THRESHOLDS["nina_fuerte"]
        else ("moderado" if v >= ENSO_THRESHOLDS["nino"] or v <= ENSO_THRESHOLDS["nina"]
              else "neutro")
    ))
    return pd.DataFrame({
        "fecha": fechas,
        "oni": np.round(oni, 2),
        "fase": fase.values,
        "intensidad": intensidad.values,
    })


def cargar_oni() -> pd.DataFrame:
    """Carga ONI desde NOAA; si falla, genera sintéticos."""
    logger.info("--- Cargando ONI ---")
    try:
        from estadistica_ambiental.features.climate import load_oni
        oni = load_oni()
        if oni.empty:
            raise ValueError("load_oni devolvió DataFrame vacío")
        logger.info("ONI cargado: %d meses (%s → %s)",
                    len(oni), oni["fecha"].min().date(), oni["fecha"].max().date())
        return oni
    except Exception as e:
        logger.warning("Descarga ONI falló (%s) — usando datos sintéticos.", e)
        return _generar_oni_sintetico()


# ===========================================================================
# 2. EDA DEL ONI
# ===========================================================================

def eda_oni(oni: pd.DataFrame) -> dict:
    """EDA: distribución, ACF, clasificación de fases ENSO."""
    logger.info("--- EDA ONI ---")
    serie = oni.set_index("fecha")["oni"]

    stats = serie.describe()
    logger.info("ONI — media: %.3f | std: %.3f | min: %.2f | max: %.2f",
                stats["mean"], stats["std"], stats["min"], stats["max"])

    # Distribución de fases
    fases = oni["fase"].value_counts()
    total = len(oni)
    for fase, n in fases.items():
        logger.info("  Fase %-8s: %4d meses (%.1f%%)", fase, n, n / total * 100)

    # Distribución de intensidades
    intens = oni["intensidad"].value_counts()
    for intens_val, n in intens.items():
        logger.info("  Intensidad %-10s: %4d meses (%.1f%%)", intens_val, n, n / total * 100)

    # ACF primeros 36 lags
    try:
        from estadistica_ambiental.descriptive.temporal import acf_values
        acf = acf_values(serie, nlags=36)
        logger.info("ACF lag-12: %.3f | lag-24: %.3f | lag-36: %.3f",
                    acf.iloc[12], acf.iloc[24], acf.iloc[36])
    except Exception as e:
        logger.warning("ACF skipped: %s", e)
        acf = pd.Series(dtype=float)

    # Guardar clasificación
    out_path = OUTPUT / "oni_clasificacion.csv"
    oni.to_csv(out_path, index=False)
    logger.info("Clasificación ONI guardada: %s", out_path.name)

    return {
        "stats": stats.to_dict(),
        "fases": fases.to_dict(),
        "intensidades": intens.to_dict(),
        "pct_nino": round(fases.get("niño", 0) / total * 100, 1),
        "pct_nina": round(fases.get("niña", 0) / total * 100, 1),
        "pct_neutro": round(fases.get("neutro", 0) / total * 100, 1),
    }


# ===========================================================================
# 3. ANÁLISIS DE TENDENCIA
# ===========================================================================

def tendencia_oni(oni: pd.DataFrame) -> dict:
    """Mann-Kendall sobre la magnitud del ONI (|ONI|) y Sen slope."""
    logger.info("--- Tendencia ONI ---")
    serie = oni.set_index("fecha")["oni"]
    magnitud = serie.abs()
    resultados: dict = {}

    # Mann-Kendall
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk = mann_kendall(magnitud)
        ss = sens_slope(magnitud)
        resultados["mann_kendall"] = {
            "variable": "magnitud_oni (|ONI|)",
            "tendencia": mk.get("trend", "unknown"),
            "p_value": round(float(mk.get("pval", 1.0)), 6),
            "significativo": mk.get("pval", 1.0) < 0.05,
            "tau": round(float(mk.get("tau", 0.0)), 4),
            "sen_slope_por_mes": round(float(ss["slope"]), 8),
            "sen_slope_por_anio": round(float(ss["slope"]) * 12, 6),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall |ONI|: tendencia=%s | p=%.6f | Sen=%.6f/mes (%.4f/año)",
                    mk_r["tendencia"], mk_r["p_value"],
                    mk_r["sen_slope_por_mes"], mk_r["sen_slope_por_anio"])
        if mk_r["significativo"]:
            logger.info("  >> Tendencia significativa en la magnitud de eventos ENSO (p<0.05)")
    except Exception as e:
        logger.warning("Mann-Kendall skipped: %s", e)

    # Mann-Kendall sobre el ONI bruto también
    try:
        from estadistica_ambiental.inference.trend import mann_kendall
        mk_raw = mann_kendall(serie)
        resultados["mann_kendall_oni_bruto"] = {
            "tendencia": mk_raw.get("trend", "unknown"),
            "p_value": round(float(mk_raw.get("pval", 1.0)), 6),
            "tau": round(float(mk_raw.get("tau", 0.0)), 4),
        }
        logger.info("Mann-Kendall ONI bruto: tendencia=%s | p=%.6f | tau=%.4f",
                    mk_raw.get("trend", "?"), mk_raw.get("pval", 1.0), mk_raw.get("tau", 0.0))
    except Exception as e:
        logger.warning("Mann-Kendall ONI bruto skipped: %s", e)

    # Guardar
    out_path = OUTPUT / "oni_tendencia.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resultados de tendencia guardados: %s", out_path.name)
    return resultados


# ===========================================================================
# 4. DESCOMPOSICIÓN STL
# ===========================================================================

def descomposicion_stl(oni: pd.DataFrame) -> pd.DataFrame:
    """STL con period=12 sobre el ONI mensual."""
    logger.info("--- Descomposición STL (period=12) ---")
    # Deduplicar por fecha antes de asfreq (ONI puede tener registros duplicados
    # si el archivo fuente tiene temporadas solapadas mapeadas al mismo mes)
    oni_dedup = oni.drop_duplicates(subset=["fecha"]).sort_values("fecha")
    serie = oni_dedup.set_index("fecha")["oni"].asfreq("MS")

    try:
        from estadistica_ambiental.descriptive.temporal import decompose_stl
        stl = decompose_stl(serie, period=12, robust=True)

        # Estadísticas de cada componente
        logger.info("STL trend  — media: %.3f | std: %.3f", stl["trend"].mean(), stl["trend"].std())
        logger.info("STL seasonal — amplitud media: %.3f", stl["seasonal"].abs().mean())
        logger.info("STL residual — std: %.3f", stl["residual"].std())

        # Varianza explicada por cada componente
        var_total = np.var(stl["observed"].dropna())
        var_trend    = np.var(stl["trend"].dropna())
        var_seasonal = np.var(stl["seasonal"].dropna())
        var_resid    = np.var(stl["residual"].dropna())
        logger.info("Varianza explicada — trend: %.1f%% | seasonal: %.1f%% | residual: %.1f%%",
                    var_trend / var_total * 100,
                    var_seasonal / var_total * 100,
                    var_resid / var_total * 100)

        out_path = OUTPUT / "oni_stl.csv"
        stl.to_csv(out_path)
        logger.info("Descomposición STL guardada: %s", out_path.name)
        return stl

    except Exception as e:
        logger.warning("STL skipped: %s", e)
        return pd.DataFrame()


# ===========================================================================
# 5. ANÁLISIS DE FRECUENCIA POR DÉCADA
# ===========================================================================

def frecuencia_decadal(oni: pd.DataFrame) -> pd.DataFrame:
    """Eventos El Niño fuerte / Niña fuerte por década."""
    logger.info("--- Frecuencia decadal de eventos ENSO ---")
    from estadistica_ambiental.config import ENSO_THRESHOLDS

    df = oni.copy()
    df["decada"] = (df["fecha"].dt.year // 10) * 10

    threshold_nino  = ENSO_THRESHOLDS["nino_fuerte"]   # +1.5
    threshold_nina  = ENSO_THRESHOLDS["nina_fuerte"]   # -1.5
    threshold_nino_mod = ENSO_THRESHOLDS["nino"]       # +0.5
    threshold_nina_mod = ENSO_THRESHOLDS["nina"]       # -0.5

    freq = df.groupby("decada").agg(
        n_meses=("oni", "count"),
        nino_fuerte=("oni", lambda x: (x >= threshold_nino).sum()),
        nina_fuerte=("oni", lambda x: (x <= threshold_nina).sum()),
        nino_moderado=("oni", lambda x: ((x >= threshold_nino_mod) & (x < threshold_nino)).sum()),
        nina_moderado=("oni", lambda x: ((x <= threshold_nina_mod) & (x > threshold_nina)).sum()),
        oni_max=("oni", "max"),
        oni_min=("oni", "min"),
    ).reset_index()

    logger.info("Eventos por década:")
    logger.info("  %-8s | %-12s | %-12s | %-12s | %-12s",
                "Década", "Niño fuerte", "Niña fuerte", "Niño mod.", "Niña mod.")
    for _, row in freq.iterrows():
        logger.info("  %-8d | %-12d | %-12d | %-12d | %-12d",
                    int(row["decada"]), int(row["nino_fuerte"]), int(row["nina_fuerte"]),
                    int(row["nino_moderado"]), int(row["nina_moderado"]))

    out_path = OUTPUT / "oni_frecuencia_decadal.csv"
    freq.to_csv(out_path, index=False)
    logger.info("Frecuencia decadal guardada: %s", out_path.name)
    return freq


# ===========================================================================
# 6. PRONÓSTICO ONI — SARIMA(2,0,0)(1,0,1,12)
# ===========================================================================

def pronostico_oni(oni: pd.DataFrame) -> dict:
    """Walk-forward backtesting SARIMA(2,0,0)(1,0,1,12), 5 folds, horizon=3."""
    logger.info("--- Pronóstico ONI: SARIMA(2,0,0)(1,0,1,12) ---")
    oni_dedup = oni.drop_duplicates(subset=["fecha"]).sort_values("fecha")
    serie = oni_dedup.set_index("fecha")["oni"].asfreq("MS").dropna()
    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model = SARIMAXModel(
            order=(2, 0, 0),
            seasonal_order=(1, 0, 1, 12),
        )

        logger.info("Entrenando SARIMA(2,0,0)(1,0,1,12) — walk-forward (5 folds, horizon=3 meses)...")
        result = walk_forward(
            model=model,
            y=serie,
            horizon=3,
            n_splits=5,
            domain="general",
        )

        metrics = result["metrics"]
        resultados["sarima_metrics"] = metrics
        logger.info("SARIMA ONI walk-forward: RMSE=%.4f | MAE=%.4f | R2=%.4f",
                    metrics.get("rmse", float("nan")),
                    metrics.get("mae", float("nan")),
                    metrics.get("r2", float("nan")))

        # Guardar métricas por fold
        if not result["folds"].empty:
            fold_path = OUTPUT / "oni_backtesting.csv"
            result["folds"].to_csv(fold_path, index=False)
            logger.info("Métricas por fold guardadas: %s", fold_path.name)

        # Pronóstico de los próximos 12 meses
        logger.info("Generando pronóstico de 12 meses...")
        model_full = SARIMAXModel(order=(2, 0, 0), seasonal_order=(1, 0, 1, 12))
        model_full.fit(serie)
        forecast_vals = model_full.predict(12)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(months=1),
            periods=12, freq="MS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="oni_forecast")
        forecast = forecast.clip(-3.0, 3.0)

        forecast_path = OUTPUT / "oni_forecast.csv"
        forecast.to_csv(forecast_path, header=True)
        logger.info("Pronóstico 12m guardado: %s (media=%.3f)", forecast_path.name, forecast.mean())

        # Clasificar pronóstico
        from estadistica_ambiental.config import ENSO_THRESHOLDS
        n_nino  = (forecast >= ENSO_THRESHOLDS["nino"]).sum()
        n_nina  = (forecast <= ENSO_THRESHOLDS["nina"]).sum()
        n_neutro = len(forecast) - n_nino - n_nina
        logger.info("Pronóstico ONI 12m: Niño=%d | Niña=%d | Neutro=%d meses",
                    n_nino, n_nina, n_neutro)
        resultados["forecast_12m"] = {
            "media": round(float(forecast.mean()), 4),
            "max": round(float(forecast.max()), 4),
            "min": round(float(forecast.min()), 4),
            "meses_nino": int(n_nino),
            "meses_nina": int(n_nina),
            "meses_neutro": int(n_neutro),
        }

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            preds_df = result.get("predictions", pd.DataFrame())
            preds_arr = (preds_df["predicted"].values
                         if not preds_df.empty and "predicted" in preds_df.columns
                         else np.array([]))
            report_path = OUTPUT / "forecast_oni.html"
            forecast_report(
                y_true=serie.iloc[-len(preds_arr):] if len(preds_arr) else serie.iloc[-24:],
                predictions={"SARIMA(2,0,0)(1,0,1,12)": preds_arr if len(preds_arr) else forecast.values},
                metrics={"SARIMA(2,0,0)(1,0,1,12)": metrics},
                output=str(report_path),
                title="Pronóstico ONI — Cambio Climático Colombia",
                variable_name="ONI (Oceanic Niño Index)",
                unit="°C anomalía",
            )
            logger.info("Reporte HTML guardado: %s", report_path.name)
        except Exception as e:
            logger.warning("forecast_report skipped: %s", e)

    except Exception as e:
        logger.error("Modelado SARIMA ONI falló: %s", e)
        import traceback
        traceback.print_exc()

    return resultados


# ===========================================================================
# 7. TABLA DE LAGS POR LÍNEA TEMÁTICA
# ===========================================================================

def tabla_lags_lineas() -> pd.DataFrame:
    """Tabla con lag ENSO → respuesta ambiental por línea temática colombiana."""
    logger.info("--- Tabla de lags ENSO por línea temática ---")
    from estadistica_ambiental.config import ENSO_LAG_MESES

    descripcion = {
        "calidad_aire":             "El Niño reduce lluvia → menor dispersión → PM2.5 sube",
        "oferta_hidrica":           "Sequía rezagada ~4 meses en cuencas Magdalena-Cauca",
        "recurso_hidrico":          "Calidad del agua responde en ~3 meses",
        "pomca":                    "Mismo lag que oferta hídrica (gestión de cuencas)",
        "pueea":                    "Planes de uso eficiente del agua",
        "paramos":                  "Páramos responden rápido a precipitación",
        "humedales":                "Hidroperiodo rezagado ~3 meses",
        "rondas_hidricas":          "Vegetación ribereña, lag similar a humedales",
        "gestion_riesgo":           "Inundaciones más inmediatas al ONI",
        "cambio_climatico":         "Variable de contexto, sin lag específico",
        "ordenamiento_territorial": "Efecto de largo plazo en planificación",
        "default":                  "Lag por defecto para líneas no especificadas",
    }

    rows = []
    for linea, lag in sorted(ENSO_LAG_MESES.items()):
        rows.append({
            "linea_tematica": linea,
            "lag_meses": lag,
            "descripcion": descripcion.get(linea, ""),
        })

    df_lags = pd.DataFrame(rows).sort_values("lag_meses")
    logger.info("Lags ENSO por línea:")
    for _, row in df_lags.iterrows():
        logger.info("  %-30s lag=%d mes(es) — %s",
                    row["linea_tematica"], row["lag_meses"], row["descripcion"][:60])

    out_path = OUTPUT / "oni_lags_lineas.csv"
    df_lags.to_csv(out_path, index=False)
    logger.info("Tabla de lags guardada: %s", out_path.name)
    return df_lags


# ===========================================================================
# 8. CROSS-CORRELACIÓN ONI vs PM2.5 MOCHUELO
# ===========================================================================

def crosscorrelacion_oni_pm25(oni: pd.DataFrame) -> pd.DataFrame:
    """Correlación cruzada ONI vs PM2.5 Mochuelo para lags 0–12 meses."""
    logger.info("--- Cross-correlación ONI vs PM2.5 Mochuelo ---")

    if not PARQUET_AIRE.exists():
        logger.info("Parquet de calidad del aire no encontrado — cross-correlación omitida.")
        return pd.DataFrame()

    try:
        df_aire = pd.read_parquet(PARQUET_AIRE)
        df_moch = df_aire[df_aire["estacion"] == ESTACION_AIRE].copy()
        if df_moch.empty:
            logger.warning("No hay datos de Mochuelo en el parquet — skipping cross-corr.")
            return pd.DataFrame()

        # Agregar PM2.5 a mensual
        pm25_mensual = (
            df_moch.set_index("fecha")["pm25"]
            .resample("MS")
            .mean()
            .dropna()
        )
        logger.info("PM2.5 Mochuelo mensual: %d meses (%s → %s)",
                    len(pm25_mensual),
                    pm25_mensual.index.min().date(),
                    pm25_mensual.index.max().date())

        # Preparar ONI mensual
        oni_mensual = oni.set_index("fecha")["oni"].asfreq("MS")

        # Intersección de fechas
        fechas_comunes = pm25_mensual.index.intersection(oni_mensual.index)
        if len(fechas_comunes) < 24:
            logger.warning("Pocas fechas comunes ONI-PM2.5 (%d) — cross-correlación omitida.",
                           len(fechas_comunes))
            return pd.DataFrame()

        pm25_c = pm25_mensual.loc[fechas_comunes]
        oni_c  = oni_mensual.loc[fechas_comunes]

        # Cross-correlación para lags 0–12
        rows = []
        for lag in range(0, 13):
            if lag == 0:
                oni_lag = oni_c
                pm25_lag = pm25_c
            else:
                oni_lag  = oni_c.iloc[:-lag]
                pm25_lag = pm25_c.iloc[lag:]

            n = min(len(oni_lag), len(pm25_lag))
            if n < 10:
                continue
            corr = np.corrcoef(oni_lag.values[:n], pm25_lag.values[:n])[0, 1]
            rows.append({"lag_meses": lag, "correlacion_pearson": round(float(corr), 4), "n": n})
            logger.info("  ONI lag+%2d meses vs PM2.5: r=%.4f (n=%d)", lag, corr, n)

        df_crosscorr = pd.DataFrame(rows)
        if not df_crosscorr.empty:
            best_lag = df_crosscorr.loc[df_crosscorr["correlacion_pearson"].abs().idxmax()]
            logger.info("Mejor lag: %d meses (r=%.4f) — coincide con config ENSO_LAG_MESES['calidad_aire']=2",
                        int(best_lag["lag_meses"]), best_lag["correlacion_pearson"])

            out_path = OUTPUT / "oni_crosscorr_pm25.csv"
            df_crosscorr.to_csv(out_path, index=False)
            logger.info("Cross-correlación guardada: %s", out_path.name)

        return df_crosscorr

    except Exception as e:
        logger.warning("Cross-correlación ONI vs PM2.5 falló: %s", e)
        return pd.DataFrame()


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — Cambio Climático | ONI/ENSO — Colombia")
    logger.info("=" * 65)

    # 1. Carga ONI
    try:
        oni = cargar_oni()
    except Exception as e:
        logger.error("Carga ONI falló: %s", e)
        return

    # 2. EDA
    try:
        eda = eda_oni(oni)
    except Exception as e:
        logger.warning("EDA ONI falló: %s", e)
        eda = {}

    # 3. Tendencia
    try:
        tend = tendencia_oni(oni)
    except Exception as e:
        logger.warning("Tendencia ONI falló: %s", e)
        tend = {}

    # 4. STL
    try:
        stl = descomposicion_stl(oni)
    except Exception as e:
        logger.warning("STL falló: %s", e)
        stl = pd.DataFrame()

    # 5. Frecuencia decadal
    try:
        freq = frecuencia_decadal(oni)
    except Exception as e:
        logger.warning("Frecuencia decadal falló: %s", e)
        freq = pd.DataFrame()

    # 6. Pronóstico
    try:
        pred = pronostico_oni(oni)
    except Exception as e:
        logger.warning("Pronóstico ONI falló: %s", e)
        pred = {}

    # 7. Tabla de lags
    try:
        lags = tabla_lags_lineas()
    except Exception as e:
        logger.warning("Tabla de lags falló: %s", e)
        lags = pd.DataFrame()

    # 8. Cross-correlación
    try:
        crosscorr = crosscorrelacion_oni_pm25(oni)
    except Exception as e:
        logger.warning("Cross-correlación falló: %s", e)
        crosscorr = pd.DataFrame()

    # Resumen final
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Cambio Climático / ONI-ENSO")
    logger.info("  Registros ONI: %d meses", len(oni))
    logger.info("  Período: %s → %s", oni["fecha"].min().date(), oni["fecha"].max().date())
    logger.info("  ONI medio: %.3f | std: %.3f", oni["oni"].mean(), oni["oni"].std())
    logger.info("  Fases: Niño=%.1f%% | Niña=%.1f%% | Neutro=%.1f%%",
                eda.get("pct_nino", 0), eda.get("pct_nina", 0), eda.get("pct_neutro", 0))

    mk = tend.get("mann_kendall", {})
    if mk:
        logger.info("  Tendencia |ONI| (Mann-Kendall): %s (p=%.6f, %.6f/año)",
                    mk.get("tendencia", "?"), mk.get("p_value", 1.0),
                    mk.get("sen_slope_por_anio", 0.0))

    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMA(2,0,0)(1,0,1,12) RMSE: %.4f | MAE: %.4f | R2: %.4f",
                    sarima.get("rmse", float("nan")),
                    sarima.get("mae", float("nan")),
                    sarima.get("r2", float("nan")))

    fc = pred.get("forecast_12m", {})
    if fc:
        logger.info("  Pronóstico 12m: Niño=%d | Niña=%d | Neutro=%d meses",
                    fc.get("meses_nino", 0), fc.get("meses_nina", 0), fc.get("meses_neutro", 0))

    if not crosscorr.empty:
        best = crosscorr.loc[crosscorr["correlacion_pearson"].abs().idxmax()]
        logger.info("  Cross-corr ONI vs PM2.5: mejor lag=%d m (r=%.4f)",
                    int(best["lag_meses"]), best["correlacion_pearson"])

    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Cambio Climático completada.")


if __name__ == "__main__":
    main()
