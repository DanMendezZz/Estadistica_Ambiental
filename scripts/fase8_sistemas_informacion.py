"""
Fase 8 — Ciclo estadístico completo: Sistemas de Información Ambiental.

Línea temática: Sistemas de Información Ambiental
Variable: cobertura de estaciones de monitoreo activas (%), serie anual 2000-2025.
Síntesis: crecimiento desde 20% (2000) → 85% (2025), con aceleración post-2012
          (inversión SINA, SIAC, IDEAM) y una meseta en 2017-2019 (recortes).

Análisis:
  - EDA + descriptiva por período
  - Tendencia: Mann-Kendall + Sen's slope
  - Tasa de crecimiento anual (%)
  - ARIMA(1,1,0) sobre la serie anual — pronóstico 5 años

Uso:
    python scripts/fase8_sistemas_informacion.py

Salidas en data/output/fase8/:
    - sistemas_informacion_datos.csv
    - sistemas_informacion_descriptiva.csv
    - sistemas_informacion_tasas.csv
    - sistemas_informacion_inferencial.json
    - sistemas_informacion_forecast.csv
    - sistemas_informacion_reporte.html
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
logger = logging.getLogger("fase8_sistemas_informacion")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "sistemas_informacion"
VARIABLE = "cobertura_estaciones_pct"
INICIO   = 2000
FIN      = 2025


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos() -> pd.DataFrame:
    """Genera serie anual de cobertura de estaciones activas (2000-2025).

    Modelo:
    - Crecimiento logístico suave de 20% → 85%.
    - Aceleración 2012-2016 (expansión SIAC, fondos GEF/BID).
    - Meseta leve 2017-2019 (austeridad presupuestal).
    - Ruido gaussiano ±2%.
    """
    logger.info("--- Generando datos sintéticos de sistemas de información ---")
    rng = np.random.default_rng(42)

    anios = np.arange(INICIO, FIN + 1)
    n     = len(anios)
    t     = np.arange(n)

    # Curva logística: L=85, k=0.22, t0=12 (inflexión ~2012)
    L, k, t0 = 85.0, 0.22, 12
    logistica  = L / (1 + np.exp(-k * (t - t0)))

    # Ajuste inicial (partimos de 20%, no de 0)
    logistica = logistica - logistica[0] + 20.0

    # Meseta 2017-2019 (recortes presupuestales): reducción temporal de la pendiente
    for i, a in enumerate(anios):
        if 2017 <= a <= 2019:
            logistica[i] = logistica[i] - 2.0 * (a - 2016)

    ruido    = rng.normal(0, 2.0, n)
    cobertura = np.clip(logistica + ruido, 0.0, 100.0)

    df = pd.DataFrame({
        "anio":                   anios,
        "cobertura_estaciones_pct": np.round(cobertura, 2),
    })

    out_path = OUTPUT / "sistemas_informacion_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos generados: %d años (%d-%d) | cobertura final=%.1f%% | guardados en %s",
                n, INICIO, FIN, cobertura[-1], out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='sistemas_informacion')."""
    logger.info("--- Validación de dominio ---")
    df_val = df.copy()
    df_val["fecha"] = pd.to_datetime(df_val["anio"].astype(str) + "-01-01")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df_val, date_col="fecha", linea_tematica=LINEA)
        logger.info(report.summary())
        resultados = {
            "n_rows":    report.n_rows,
            "n_cols":    report.n_cols,
            "missing":   report.missing,
            "has_issues": report.has_issues(),
        }
        logger.info("Validación OK: issues=%s", report.has_issues())
    except Exception as exc:
        logger.warning("Validación skipped: %s", exc)
    return resultados


# ===========================================================================
# 3. EDA + DESCRIPTIVA
# ===========================================================================

def eda_descriptiva(df: pd.DataFrame) -> pd.DataFrame:
    """Estadísticas descriptivas por subperíodo + tasas de crecimiento."""
    logger.info("--- EDA + Descriptiva ---")

    serie = df["cobertura_estaciones_pct"]
    logger.info("Global: media=%.2f%% | mediana=%.2f%% | std=%.2f%% | [%.1f, %.1f]",
                serie.mean(), serie.median(), serie.std(), serie.min(), serie.max())

    periodos = [
        ("2000-2005", (2000, 2005)),
        ("2006-2011", (2006, 2011)),
        ("2012-2016", (2012, 2016)),
        ("2017-2025", (2017, 2025)),
    ]
    rows = []
    for label, (a, b) in periodos:
        sub = df[(df["anio"] >= a) & (df["anio"] <= b)]["cobertura_estaciones_pct"]
        rows.append({
            "periodo": label,
            "n":       len(sub),
            "media":   round(float(sub.mean()), 2),
            "mediana": round(float(sub.median()), 2),
            "std":     round(float(sub.std()), 2),
            "min":     round(float(sub.min()), 2),
            "max":     round(float(sub.max()), 2),
        })
        logger.info("  %-12s: media=%.1f%% | [%.1f, %.1f]",
                    label, rows[-1]["media"], rows[-1]["min"], rows[-1]["max"])

    resumen = pd.DataFrame(rows).set_index("periodo")
    out_path = OUTPUT / "sistemas_informacion_descriptiva.csv"
    resumen.to_csv(out_path)
    logger.info("Descriptiva guardada: %s", out_path.name)
    return resumen


def calcular_tasas(df: pd.DataFrame) -> pd.DataFrame:
    """Tasa de crecimiento anual (%) de la cobertura."""
    logger.info("--- Tasas de crecimiento anual ---")
    df2 = df.copy().sort_values("anio")
    df2["tasa_crecimiento_pct"] = df2["cobertura_estaciones_pct"].pct_change() * 100
    df2["incremento_pp"] = df2["cobertura_estaciones_pct"].diff()  # puntos porcentuales

    logger.info("Tasa media de crecimiento: %.2f%%/año",
                df2["tasa_crecimiento_pct"].dropna().mean())
    logger.info("Mayor salto: +%.1f pp (año %d)",
                df2["incremento_pp"].max(),
                int(df2.loc[df2["incremento_pp"].idxmax(), "anio"]))

    out_path = OUTPUT / "sistemas_informacion_tasas.csv"
    df2.to_csv(out_path, index=False)
    logger.info("Tasas guardadas: %s", out_path.name)
    return df2


# ===========================================================================
# 4. INFERENCIAL — MANN-KENDALL
# ===========================================================================

def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall sobre la serie completa."""
    logger.info("--- Inferencial (Mann-Kendall) ---")
    resultados: dict = {}

    serie = pd.Series(
        df["cobertura_estaciones_pct"].values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="cobertura_estaciones_pct",
    )

    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk = mann_kendall(serie)
        ss = sens_slope(serie)
        slope_anual = float(ss.get("slope", 0.0))
        resultados["mann_kendall"] = {
            "n":                    len(serie),
            "tendencia":            mk.get("trend", "unknown"),
            "p_value":              round(float(mk.get("pval", 1.0)), 6),
            "significativo":        mk.get("pval", 1.0) < 0.05,
            "tau":                  round(float(mk.get("tau", 0.0)), 4),
            "sen_slope_anual_pp":   round(float(slope_anual), 4),
        }
        r = resultados["mann_kendall"]
        logger.info("Mann-Kendall: %s | p=%.6f | slope=%.4f pp/año%s",
                    r["tendencia"], r["p_value"], r["sen_slope_anual_pp"],
                    " [SIGNIFICATIVO]" if r["significativo"] else "")
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    out_path = OUTPUT / "sistemas_informacion_inferencial.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_path.name)
    return resultados


# ===========================================================================
# 5. ARIMA ANUAL + PRONÓSTICO 5 AÑOS
# ===========================================================================

def modelado_predictivo(df: pd.DataFrame) -> dict:
    """ARIMA(1,1,0) sobre la serie anual — pronóstico 5 años.

    Sin walk-forward: serie de 26 puntos, frecuencia anual, sin estacionalidad.
    ARIMA(1,1,0) captura la tendencia con autorregresión de primer orden.
    """
    logger.info("--- Modelado predictivo (ARIMA anual) ---")

    serie = pd.Series(
        df["cobertura_estaciones_pct"].values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="cobertura_estaciones_pct",
    ).asfreq("YS")

    logger.info("Serie: %d años (%s → %s)",
                len(serie), serie.index.min().date(), serie.index.max().date())
    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel

        model = SARIMAXModel(order=(1, 1, 0), seasonal_order=(0, 0, 0, 0))
        logger.info("Ajustando ARIMA(1,1,0) sobre serie completa...")
        model.fit(serie)

        # Métricas insample
        try:
            preds_in = np.clip(model.predict(len(serie)), 0.0, 100.0)
            preds_in = preds_in[-len(serie):]
            from estadistica_ambiental.evaluation.metrics import evaluate
            metrics = evaluate(y_true=serie.values, y_pred=preds_in, domain="general")
            resultados["arima_metrics_insample"] = metrics
            logger.info("ARIMA (insample) — RMSE=%.4f | MAE=%.4f | R2=%.4f",
                        metrics.get("rmse", float("nan")),
                        metrics.get("mae", float("nan")),
                        metrics.get("r2", float("nan")))
        except Exception as exc_m:
            logger.warning("Métricas insample skipped: %s", exc_m)

        # Pronóstico 5 años (2026-2030)
        horizon = 5
        forecast_vals = np.clip(model.predict(horizon), 0.0, 100.0)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(years=1),
            periods=horizon, freq="YS",
        )
        forecast = pd.Series(
            forecast_vals, index=forecast_idx, name="cobertura_forecast_pct"
        )

        fc_path = OUTPUT / "sistemas_informacion_forecast.csv"
        forecast.to_csv(fc_path, header=True)
        logger.info("Pronóstico 5 años guardado: %s", fc_path.name)
        for fecha, val in forecast.items():
            logger.info("  %d: %.2f%%", fecha.year, val)

        resultados["forecast"] = {str(k.year): round(float(v), 2) for k, v in forecast.items()}

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            y_ref    = serie.iloc[-10:].copy()
            pred_arr = np.clip(model.predict(10)[-len(y_ref):], 0.0, 100.0)
            report_path = OUTPUT / "sistemas_informacion_reporte.html"
            forecast_report(
                y_true=y_ref,
                predictions={"ARIMA(1,1,0)": pred_arr},
                metrics=resultados.get("arima_metrics_insample", {}),
                output=str(report_path),
                title="Cobertura de Monitoreo Ambiental — Sistemas de Información",
                variable_name="Cobertura Estaciones Activas",
                unit="%",
            )
            logger.info("Reporte HTML guardado: %s", report_path.name)
        except Exception as exc_r:
            logger.warning("forecast_report skipped: %s", exc_r)

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
    logger.info("FASE 8 — SISTEMAS DE INFORMACIÓN AMBIENTAL")
    logger.info("Variable: cobertura de estaciones activas (%%) | %d-%d", INICIO, FIN)
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

    # 3. EDA + Descriptiva
    try:
        eda_descriptiva(df)
    except Exception as exc:
        logger.warning("EDA/Descriptiva falló: %s", exc)

    # 4. Tasas de crecimiento
    try:
        calcular_tasas(df)
    except Exception as exc:
        logger.warning("Tasas skipped: %s", exc)

    # 5. Inferencial
    try:
        inf = inferencial(df)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)
        inf = {}

    # 6. Modelado predictivo
    try:
        pred = modelado_predictivo(df)
    except Exception as exc:
        logger.error("Modelado predictivo falló: %s", exc)
        pred = {}

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Sistemas de Información Ambiental")
    logger.info("  Período: %d-%d | n=%d puntos anuales", INICIO, FIN, len(df))
    logger.info("  Cobertura %d: %.1f%% → %d: %.1f%%",
                INICIO,
                float(df.loc[df["anio"] == INICIO, "cobertura_estaciones_pct"].iloc[0]),
                FIN,
                float(df.loc[df["anio"] == FIN, "cobertura_estaciones_pct"].iloc[0]))
    mk_r = inf.get("mann_kendall", {})
    if mk_r:
        logger.info("  MK: %s | p=%.6f | %.4f pp/año%s",
                    mk_r.get("tendencia", "?"),
                    mk_r.get("p_value", 1.0),
                    mk_r.get("sen_slope_anual_pp", 0.0),
                    " [SIGNIF.]" if mk_r.get("significativo") else "")
    if pred.get("forecast"):
        logger.info("  Pronóstico cobertura 2030: %.1f%%",
                    list(pred["forecast"].values())[-1])
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Sistemas de Información Ambiental completada.")


if __name__ == "__main__":
    main()
