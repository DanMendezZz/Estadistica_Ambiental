"""
Fase 8 — Ciclo estadístico completo: Rondas Hídricas.

Línea temática: Rondas Hídricas
Variable: ancho de ronda hídrica (m) a lo largo de un río, mediciones mensuales.
Síntesis: media 30 m, degradación lenta en sector urbano, eventos de recuperación
          post-intervención (revegetalización, compra de predios).

Flujo:
  1. Generación de datos sintéticos (rng=42)
  2. Validación con validate(df, linea_tematica='rondas_hidricas')
  3. EDA descriptiva (estadísticas, estacionalidad, gaps)
  4. Tendencia: Mann-Kendall + Sen's slope
  5. Estacionariedad: ADF + KPSS (ADR-004)
  6. SARIMA mensual (serie única por tramo)
  7. Reporte HTML: forecast_report

Uso:
    python scripts/fase8_rondas_hidricas.py

Salidas en data/output/fase8/:
    - rondas_hidricas_datos.csv
    - rondas_hidricas_descriptiva.csv
    - rondas_hidricas_inferencial.json
    - rondas_hidricas_forecast.csv
    - rondas_hidricas_reporte.html
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
logger = logging.getLogger("fase8_rondas_hidricas")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "rondas_hidricas"
VARIABLE = "ancho_ronda_m"
TRAMO    = "Rio_Bogota_Tramo_Urbano"

# Tramos ficticios: diferentes presiones antrópicas
TRAMOS = [
    {"nombre": "Tramo_Periurbano",  "ancho_base": 35.0, "degradacion": -0.04},
    {"nombre": "Tramo_Urbano",      "ancho_base": 22.0, "degradacion": -0.06},
    {"nombre": "Tramo_Rural",       "ancho_base": 48.0, "degradacion": -0.01},
]

INICIO    = "2014-01-01"
N_ANIOS   = 10


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos() -> pd.DataFrame:
    """Genera 10 años de mediciones mensuales de ancho de ronda (m) por tramo.

    Modelo:
    - Degradación lenta por presión urbana (tendencia negativa por tramo).
    - Dos eventos de recuperación: post-2016 y post-2020 (compra de predios).
    - Variación estacional menor (épocas húmedas favorecen vegetación).
    - Ruido gaussiano.
    """
    logger.info("--- Generando datos sintéticos de rondas hídricas ---")
    rng = np.random.default_rng(42)

    n_meses = N_ANIOS * 12
    fechas  = pd.date_range(INICIO, periods=n_meses, freq="MS")
    t       = np.arange(n_meses)
    meses   = fechas.month

    # Estacionalidad: rondas ligeramente más anchas en épocas húmedas
    seasonal = 1.2 * np.sin(2 * np.pi * (meses - 4) / 12)

    # Eventos de recuperación (intervenciones de revegetalización)
    recuperacion = np.where(t >= 30, 3.0, 0.0) + np.where(t >= 72, 2.5, 0.0)

    registros = []
    for tramo in TRAMOS:
        nombre     = tramo["nombre"]
        ancho_base = tramo["ancho_base"]
        degradacion = tramo["degradacion"]  # m/mes

        ancho = (
            ancho_base
            + degradacion * t
            + seasonal
            + recuperacion
            + rng.normal(0, 1.5, n_meses)
        )
        ancho = np.clip(ancho, 5.0, 100.0)  # ronda mínima legal 5 m (Decreto 2811)

        for i, fecha in enumerate(fechas):
            registros.append({
                "fecha":         fecha,
                "tramo":         nombre,
                "ancho_ronda_m": round(float(ancho[i]), 2),
            })

    df = pd.DataFrame(registros)
    logger.info("Datos generados: %d registros (%d tramos × %d meses)",
                len(df), len(TRAMOS), n_meses)
    logger.info("Ancho medio global: %.2f m | std: %.2f m",
                df["ancho_ronda_m"].mean(), df["ancho_ronda_m"].std())

    out_path = OUTPUT / "rondas_hidricas_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("CSV guardado: %s", out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='rondas_hidricas')."""
    logger.info("--- Validación de dominio (rondas_hidricas) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df, date_col="fecha", linea_tematica=LINEA)
        logger.info(report.summary())
        resultados = {
            "n_rows":            report.n_rows,
            "n_cols":            report.n_cols,
            "missing":           report.missing,
            "duplicates_exact":  report.duplicates_exact,
            "has_issues":        report.has_issues(),
        }
        logger.info("Validación OK: issues=%s", report.has_issues())
    except Exception as exc:
        logger.warning("Validación skipped: %s", exc)
    return resultados


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(df: pd.DataFrame) -> dict:
    """Estadísticas descriptivas por tramo y estacionalidad mensual."""
    logger.info("--- EDA Rondas Hídricas ---")
    resumen: dict = {}

    for tramo in df["tramo"].unique():
        sub = df[df["tramo"] == tramo]["ancho_ronda_m"].dropna()
        resumen[tramo] = {
            "n":        len(sub),
            "media":    round(float(sub.mean()), 2),
            "mediana":  round(float(sub.median()), 2),
            "std":      round(float(sub.std()), 2),
            "min":      round(float(sub.min()), 2),
            "max":      round(float(sub.max()), 2),
        }
        logger.info("%-30s media=%.2f m | std=%.2f | [%.1f, %.1f]",
                    tramo,
                    resumen[tramo]["media"],
                    resumen[tramo]["std"],
                    resumen[tramo]["min"],
                    resumen[tramo]["max"])

    # Estacionalidad mensual (todos los tramos)
    mensual = df.groupby(df["fecha"].dt.month)["ancho_ronda_m"].mean().round(2)
    logger.info("Estacionalidad mensual — ancho medio por mes:")
    logger.info("  %s", mensual.to_dict())

    return resumen


# ===========================================================================
# 4. DESCRIPTIVA
# ===========================================================================

def descriptiva(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen anual por tramo."""
    logger.info("--- Descriptiva anual ---")
    df2 = df.copy()
    df2["anio"] = pd.to_datetime(df2["fecha"]).dt.year

    anual = df2.groupby(["anio", "tramo"])["ancho_ronda_m"].agg(
        n="count",
        media="mean",
        mediana="median",
        std="std",
        min="min",
        max="max",
    ).round(2)

    out_path = OUTPUT / "rondas_hidricas_descriptiva.csv"
    anual.to_csv(out_path)
    logger.info("Descriptiva anual guardada: %s (%d filas)", out_path.name, len(anual))
    return anual


# ===========================================================================
# 5. INFERENCIAL (Mann-Kendall + ADF/KPSS)
# ===========================================================================

def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall + Sen's slope + ADF/KPSS sobre el tramo urbano."""
    logger.info("--- Inferencial ---")
    resultados: dict = {}

    # Usar tramo urbano como serie focal
    tramo_focal = "Tramo_Urbano"
    serie = (
        df[df["tramo"] == tramo_focal]
        .set_index("fecha")["ancho_ronda_m"]
        .asfreq("MS")
        .sort_index()
        .dropna()
    )
    logger.info("Serie focal (%s): %d meses", tramo_focal, len(serie))

    # Mann-Kendall
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk  = mann_kendall(serie)
        ss  = sens_slope(serie)
        slope_anual = float(ss.get("slope", 0.0)) * 12
        resultados["mann_kendall"] = {
            "tramo":              tramo_focal,
            "tendencia":          mk.get("trend", "unknown"),
            "p_value":            round(float(mk.get("pval", 1.0)), 6),
            "significativo":      mk.get("pval", 1.0) < 0.05,
            "tau":                round(float(mk.get("tau", 0.0)), 4),
            "sen_slope_anual_m":  round(float(slope_anual), 4),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall (%s): %s | p=%.6f | slope=%.4f m/año%s",
                    tramo_focal,
                    mk_r["tendencia"],
                    mk_r["p_value"],
                    mk_r["sen_slope_anual_m"],
                    " [SIGNIFICATIVO]" if mk_r["significativo"] else "")
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # ADF + KPSS (ADR-004)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf   = adf_test(serie)
        kpss_ = kpss_test(serie)
        resultados["estacionariedad"] = {
            "adf_stationary":  bool(adf.get("stationary", False)),
            "adf_pvalue":      round(float(adf.get("pval", 1.0)), 6),
            "kpss_stationary": bool(kpss_.get("stationary", True)),
            "kpss_pvalue":     round(float(kpss_.get("pval", 0.1)), 6),
        }
        est = resultados["estacionariedad"]
        logger.info("ADF: %s (p=%.6f) | KPSS: %s (p=%.6f)",
                    "estacionaria" if est["adf_stationary"] else "no estacionaria",
                    est["adf_pvalue"],
                    "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                    est["kpss_pvalue"])
    except Exception as exc:
        logger.warning("ADF/KPSS skipped: %s", exc)

    out_path = OUTPUT / "rondas_hidricas_inferencial.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_path.name)
    return resultados


# ===========================================================================
# 6. SARIMA + REPORTE HTML
# ===========================================================================

def modelado_predictivo(df: pd.DataFrame) -> dict:
    """SARIMA(1,1,1)(1,1,1,12) sobre el tramo urbano + reporte HTML."""
    logger.info("--- Modelado predictivo (SARIMA) ---")
    tramo_focal = "Tramo_Urbano"
    serie = (
        df[df["tramo"] == tramo_focal]
        .set_index("fecha")["ancho_ronda_m"]
        .asfreq("MS")
        .sort_index()
        .dropna()
    )
    logger.info("Serie: %d meses (%s → %s)",
                len(serie), serie.index.min().date(), serie.index.max().date())
    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        logger.info("Walk-forward SARIMA(1,1,1)(1,1,1,12) — 4 folds, horizon=6...")
        result = walk_forward(model=model, y=serie, horizon=6, n_splits=4, domain="general")

        metrics = result["metrics"]
        resultados["sarima_metrics"] = metrics
        logger.info("SARIMA — RMSE=%.4f m | MAE=%.4f m | R2=%.4f",
                    metrics.get("rmse", float("nan")),
                    metrics.get("mae", float("nan")),
                    metrics.get("r2", float("nan")))

        # Pronóstico 12 meses
        model_fc = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model_fc.fit(serie)
        forecast_vals = np.clip(model_fc.predict(12), 5.0, 100.0)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(months=1),
            periods=12, freq="MS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="ancho_ronda_forecast_m")
        fc_path  = OUTPUT / "rondas_hidricas_forecast.csv"
        forecast.to_csv(fc_path, header=True)
        logger.info("Pronóstico 12m guardado: %s (media=%.2f m)", fc_path.name, forecast.mean())
        resultados["forecast_12m_media"] = round(float(forecast.mean()), 3)

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            preds_df  = result.get("predictions", pd.DataFrame())
            preds_arr = (
                preds_df["predicted"].values
                if not preds_df.empty and "predicted" in preds_df.columns
                else np.array([])
            )
            report_path = OUTPUT / "rondas_hidricas_reporte.html"
            forecast_report(
                y_true=serie.iloc[-len(preds_arr):] if len(preds_arr) else serie.iloc[-24:],
                predictions={"SARIMA(1,1,1)(1,1,1,12)": preds_arr if len(preds_arr) else forecast.values},
                metrics={"SARIMA(1,1,1)(1,1,1,12)": metrics},
                output=str(report_path),
                title="Pronóstico Ancho de Ronda Hídrica — Tramo Urbano",
                variable_name="Ancho de Ronda",
                unit="m",
            )
            logger.info("Reporte HTML guardado: %s", report_path.name)
        except Exception as exc:
            logger.warning("forecast_report skipped: %s", exc)

    except Exception as exc:
        logger.error("Modelado predictivo falló: %s", exc)
        import traceback
        traceback.print_exc()

    return resultados


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — RONDAS HÍDRICAS | Ancho de ronda mensual sintético")
    logger.info("Tramos: %s", [t["nombre"] for t in TRAMOS])
    logger.info("=" * 65)

    # 1. Datos
    try:
        df = generar_datos()
    except Exception as exc:
        logger.error("Generación de datos falló: %s", exc)
        return

    # 2. Validación
    try:
        validar(df)
    except Exception as exc:
        logger.warning("Validación falló: %s", exc)

    # 3. EDA
    try:
        eda_res = eda(df)
    except Exception as exc:
        logger.warning("EDA falló: %s", exc)
        eda_res = {}

    # 4. Descriptiva
    try:
        descriptiva(df)
    except Exception as exc:
        logger.warning("Descriptiva falló: %s", exc)

    # 5. Inferencial
    try:
        inf = inferencial(df)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)
        inf = {}

    # 6. Modelado predictivo + reporte
    try:
        pred = modelado_predictivo(df)
    except Exception as exc:
        logger.error("Modelado predictivo falló: %s", exc)
        pred = {}

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Rondas Hídricas")
    logger.info("  Período: %s → %s",
                df["fecha"].min().date(), df["fecha"].max().date())
    for tramo, stats in eda_res.items():
        logger.info("  %-30s media=%.2f m | std=%.2f",
                    tramo, stats.get("media", float("nan")), stats.get("std", float("nan")))
    mk_r = inf.get("mann_kendall", {})
    if mk_r:
        logger.info("  MK (Tramo_Urbano): %s | p=%.6f | %.4f m/año%s",
                    mk_r.get("tendencia", "?"),
                    mk_r.get("p_value", 1.0),
                    mk_r.get("sen_slope_anual_m", 0.0),
                    " [SIGNIF.]" if mk_r.get("significativo") else "")
    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMA — RMSE=%.4f m | MAE=%.4f m | R2=%.4f",
                    sarima.get("rmse", float("nan")),
                    sarima.get("mae", float("nan")),
                    sarima.get("r2", float("nan")))
    if pred.get("forecast_12m_media"):
        logger.info("  Pronóstico 12m (media): %.2f m", pred["forecast_12m_media"])
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Rondas Hídricas completada.")


if __name__ == "__main__":
    main()
