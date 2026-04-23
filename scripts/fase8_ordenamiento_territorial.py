"""
Fase 8 — Ciclo estadístico completo: Ordenamiento Territorial.

Línea temática: Ordenamiento Territorial
Variable: porcentaje de suelo bajo conflicto de uso (%), serie anual 1990-2024.
Síntesis: tendencia creciente 45% → 65% (1990-2016), luego descenso parcial
          tras acciones correctivas post-acuerdo de paz y POT ajustados.

Análisis:
  - Descriptivo anual (media, percentiles, tendencia visual)
  - Mann-Kendall sobre la serie completa y por subperíodo (pre/post 2016)
  - SARIMA(1,0,0)(0,0,0,0) anual — sin walk-forward (serie de solo 35 puntos)
  - Reporte HTML con pronóstico 5 años

Nota: Serie corta (35 años), frecuencia anual → se omite walk-forward;
      se ajusta SARIMA sobre la serie completa y se pronostica hacia adelante.

Uso:
    python scripts/fase8_ordenamiento_territorial.py

Salidas en data/output/fase8/:
    - ordenamiento_datos.csv
    - ordenamiento_descriptiva.csv
    - ordenamiento_inferencial.json
    - ordenamiento_forecast.csv
    - ordenamiento_reporte.html
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
logger = logging.getLogger("fase8_ordenamiento_territorial")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "ordenamiento_territorial"
VARIABLE = "conflicto_uso_pct"
INICIO   = 1990
FIN      = 2024


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos() -> pd.DataFrame:
    """Genera serie anual de % de suelo bajo conflicto de uso (1990-2024).

    Modelo:
    - Crecimiento sostenido 45% → 65% (1990-2016): expansión agropecuaria
      sobre zonas protegidas y de reserva.
    - Post-2016: descenso gradual (~-0.5%/año) por POT ajustados, compra de
      predios ambientales y zonas de reserva campesina.
    - Ruido gaussiano moderado (±1.5%) que refleja variación inter-municipal.
    """
    logger.info("--- Generando datos sintéticos de ordenamiento territorial ---")
    rng = np.random.default_rng(42)

    anios = np.arange(INICIO, FIN + 1)
    n     = len(anios)

    # Fase 1 (1990-2016): crecimiento lineal 45 → 65 %
    n1 = 2016 - INICIO + 1
    fase1 = np.linspace(45.0, 65.0, n1)

    # Fase 2 (2017-2024): descenso parcial -0.5 %/año
    n2 = FIN - 2016
    fase2 = np.linspace(65.0, 65.0 - 0.5 * n2, n2)

    tendencia = np.concatenate([fase1, fase2])
    ruido     = rng.normal(0, 1.5, n)
    conflicto = np.clip(tendencia + ruido, 20.0, 90.0)

    df = pd.DataFrame({
        "anio":              anios,
        "conflicto_uso_pct": np.round(conflicto, 2),
    })

    out_path = OUTPUT / "ordenamiento_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos generados: %d años (%d--%d) | media=%.2f%% | guardados en %s",
                n, INICIO, FIN, df["conflicto_uso_pct"].mean(), out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='ordenamiento_territorial')."""
    logger.info("--- Validación de dominio ---")
    # El validador espera columna de fecha; creamos una columna 'fecha' anual.
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
    """Estadísticas descriptivas por subperíodo y global."""
    logger.info("--- EDA + Descriptiva ---")

    serie = df["conflicto_uso_pct"]
    logger.info("Global: media=%.2f%% | mediana=%.2f%% | std=%.2f%% | [%.1f, %.1f]",
                serie.mean(), serie.median(), serie.std(), serie.min(), serie.max())

    # Por subperíodo
    periodos = [
        ("1990-2000", (1990, 2000)),
        ("2001-2010", (2001, 2010)),
        ("2011-2016", (2011, 2016)),
        ("2017-2024", (2017, 2024)),
    ]
    rows = []
    for label, (a, b) in periodos:
        sub = df[(df["anio"] >= a) & (df["anio"] <= b)]["conflicto_uso_pct"]
        rows.append({
            "periodo": label,
            "n":       len(sub),
            "media":   round(float(sub.mean()), 2),
            "mediana": round(float(sub.median()), 2),
            "std":     round(float(sub.std()), 2),
            "min":     round(float(sub.min()), 2),
            "max":     round(float(sub.max()), 2),
        })
        logger.info("  %-12s: media=%.2f%% | std=%.2f%% | [%.1f, %.1f]",
                    label, rows[-1]["media"], rows[-1]["std"],
                    rows[-1]["min"], rows[-1]["max"])

    resumen = pd.DataFrame(rows).set_index("periodo")
    out_path = OUTPUT / "ordenamiento_descriptiva.csv"
    resumen.to_csv(out_path)
    logger.info("Descriptiva guardada: %s", out_path.name)
    return resumen


# ===========================================================================
# 4. INFERENCIAL — MANN-KENDALL
# ===========================================================================

def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall global y por subperíodo (pre/post 2016)."""
    logger.info("--- Inferencial (Mann-Kendall) ---")
    resultados: dict = {}

    serie_completa = pd.Series(
        df["conflicto_uso_pct"].values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="conflicto_uso_pct",
    )

    subperiodos = {
        "completo":  serie_completa,
        "pre_2016":  serie_completa[:"2016"],
        "post_2016": serie_completa["2017":],
    }

    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope

        for nombre, serie in subperiodos.items():
            if len(serie) < 4:
                logger.warning("Subperíodo '%s' muy corto (%d puntos) — omitido", nombre, len(serie))
                continue
            mk = mann_kendall(serie)
            ss = sens_slope(serie)
            slope_anual = float(ss.get("slope", 0.0))  # ya es anual (freq YE)
            resultados[nombre] = {
                "n":                  len(serie),
                "tendencia":          mk.get("trend", "unknown"),
                "p_value":            round(float(mk.get("pval", 1.0)), 6),
                "significativo":      mk.get("pval", 1.0) < 0.05,
                "tau":                round(float(mk.get("tau", 0.0)), 4),
                "sen_slope_anual_pct": round(float(slope_anual), 4),
            }
            r = resultados[nombre]
            logger.info("MK %-12s: %s | p=%.6f | slope=%.4f%%/año%s",
                        nombre, r["tendencia"], r["p_value"], r["sen_slope_anual_pct"],
                        " [SIGNIF.]" if r["significativo"] else "")
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    out_path = OUTPUT / "ordenamiento_inferencial.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_path.name)
    return resultados


# ===========================================================================
# 5. SARIMA ANUAL + PRONÓSTICO 5 AÑOS
# ===========================================================================

def modelado_predictivo(df: pd.DataFrame) -> dict:
    """ARIMA(1,1,1) sobre la serie anual — sin walk-forward (serie corta).

    Con 35 observaciones y frecuencia anual no hay estacionalidad (S=1),
    por lo que se usa un ARIMA simple con diferenciación para la tendencia.
    Se pronostica 5 años hacia adelante.
    """
    logger.info("--- Modelado predictivo (ARIMA anual) ---")

    serie = pd.Series(
        df["conflicto_uso_pct"].values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="conflicto_uso_pct",
    ).asfreq("YS")

    logger.info("Serie: %d años (%s → %s)",
                len(serie), serie.index.min().date(), serie.index.max().date())
    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel

        # ARIMA(1,1,1) — diferenciación capta la tendencia cambiante
        model = SARIMAXModel(order=(1, 1, 1), seasonal_order=(0, 0, 0, 0))
        logger.info("Ajustando ARIMA(1,1,1) sobre serie completa (sin walk-forward)...")
        model.fit(serie)

        # Métricas en muestra (insample residuales)
        try:
            preds_in = model.predict(len(serie))
            preds_in = np.clip(preds_in[-len(serie):], 20.0, 90.0)
            from estadistica_ambiental.evaluation.metrics import evaluate
            metrics = evaluate(
                y_true=serie.values,
                y_pred=preds_in,
                domain="general",
            )
            resultados["arima_metrics_insample"] = metrics
            logger.info("ARIMA (insample) — RMSE=%.4f%% | MAE=%.4f%% | R2=%.4f",
                        metrics.get("rmse", float("nan")),
                        metrics.get("mae", float("nan")),
                        metrics.get("r2", float("nan")))
        except Exception as exc_m:
            logger.warning("Métricas insample skipped: %s", exc_m)

        # Pronóstico 5 años (2025-2029)
        horizon = 5
        forecast_vals = np.clip(model.predict(horizon), 20.0, 90.0)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(years=1),
            periods=horizon, freq="YS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="conflicto_uso_forecast_pct")

        fc_path = OUTPUT / "ordenamiento_forecast.csv"
        forecast.to_csv(fc_path, header=True)
        logger.info("Pronóstico 5 años guardado: %s", fc_path.name)
        for fecha, val in forecast.items():
            logger.info("  %d: %.2f%%", fecha.year, val)

        resultados["forecast"] = {str(k.year): round(float(v), 2) for k, v in forecast.items()}
        resultados["forecast_media_pct"] = round(float(forecast.mean()), 2)

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            # Comparación visual: observado últimos 10 años vs. forecast
            y_ref = serie.iloc[-10:].copy()
            pred_arr = np.concatenate([
                model.predict(10)[-len(y_ref):],
            ])
            pred_arr = np.clip(pred_arr, 20.0, 90.0)
            report_path = OUTPUT / "ordenamiento_reporte.html"
            forecast_report(
                y_true=y_ref,
                predictions={"ARIMA(1,1,1)": pred_arr},
                metrics=resultados.get("arima_metrics_insample", {}),
                output=str(report_path),
                title="Conflicto de Uso del Suelo — Ordenamiento Territorial Colombia",
                variable_name="Conflicto de Uso del Suelo",
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
    logger.info("FASE 8 — ORDENAMIENTO TERRITORIAL | Conflicto de Uso del Suelo")
    logger.info("Serie anual %d-%d (sintética)", INICIO, FIN)
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

    # 4. Inferencial
    try:
        inf = inferencial(df)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)
        inf = {}

    # 5. Modelado predictivo
    try:
        pred = modelado_predictivo(df)
    except Exception as exc:
        logger.error("Modelado predictivo falló: %s", exc)
        pred = {}

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Ordenamiento Territorial")
    logger.info("  Período: %d-%d | n=%d puntos anuales", INICIO, FIN, len(df))
    logger.info("  Conflicto de uso — media global: %.2f%%",
                df["conflicto_uso_pct"].mean())
    mk_c = inf.get("completo", {})
    if mk_c:
        logger.info("  MK global: %s | p=%.6f | %.4f%%/año%s",
                    mk_c.get("tendencia", "?"),
                    mk_c.get("p_value", 1.0),
                    mk_c.get("sen_slope_anual_pct", 0.0),
                    " [SIGNIF.]" if mk_c.get("significativo") else "")
    mk_post = inf.get("post_2016", {})
    if mk_post:
        logger.info("  MK post-2016: %s | p=%.6f | %.4f%%/año",
                    mk_post.get("tendencia", "?"),
                    mk_post.get("p_value", 1.0),
                    mk_post.get("sen_slope_anual_pct", 0.0))
    if pred.get("forecast"):
        logger.info("  Pronóstico 2025-2029: %s", pred["forecast"])
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Ordenamiento Territorial completada.")


if __name__ == "__main__":
    main()
