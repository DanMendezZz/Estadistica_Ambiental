"""
Fase 8 — Ciclo estadístico completo: Predios para Conservación.

Línea temática: Predios para Conservación (Pago por Servicios Ambientales — PSA)
Variable: hectáreas bajo esquemas de PSA, serie anual 2010-2025.
Síntesis: crecimiento desde 5,000 ha (2010) → 45,000 ha (2025), con ruptura
          estructural post-2016 (Ley 1819/2016, fondos posconflicto para
          conservación en zonas PDET).

Análisis:
  - EDA + descriptiva anual
  - Tendencia: Mann-Kendall + Sen's slope
  - Detección de ruptura estructural (Chow test / punto de quiebre manual 2016)
  - ARIMA(1,1,0) sobre la serie completa — pronóstico 5 años
  - Reporte HTML

Uso:
    python scripts/fase8_predios_conservacion.py

Salidas en data/output/fase8/:
    - predios_conservacion_datos.csv
    - predios_conservacion_descriptiva.csv
    - predios_conservacion_inferencial.json
    - predios_conservacion_forecast.csv
    - predios_conservacion_reporte.html
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
logger = logging.getLogger("fase8_predios_conservacion")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "predios_conservacion"
VARIABLE = "ha_psa"
INICIO   = 2010
FIN      = 2025
RUPTURA  = 2016  # año de ruptura estructural (Ley 1819/2016)


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos() -> pd.DataFrame:
    """Genera serie anual de hectáreas bajo PSA (2010-2025).

    Modelo en dos fases:
    - 2010-2016: crecimiento lento ~2,000 ha/año (programas piloto CARs).
    - 2017-2025: crecimiento acelerado ~3,500 ha/año (Ley 1819, fondos posconflicto,
      Pago por Servicios Ambientales — Decreto 870/2017).
    - Ruido proporcional a la escala (~±300 ha).
    """
    logger.info("--- Generando datos sintéticos de predios para conservación ---")
    rng = np.random.default_rng(42)

    anios = np.arange(INICIO, FIN + 1)
    n     = len(anios)

    # Fase 1: crecimiento lento 5,000 → 17,000 ha (2010-2016)
    n1      = RUPTURA - INICIO + 1
    fase1   = np.linspace(5_000, 17_000, n1)

    # Fase 2: crecimiento acelerado 17,000 → 45,000 ha (2017-2025)
    n2      = FIN - RUPTURA
    fase2   = np.linspace(17_000, 45_000, n2)

    tendencia = np.concatenate([fase1, fase2])
    # Ruido proporcional (±300 ha) — valores absolutos crecen con la escala
    ruido     = rng.normal(0, 300.0, n)
    ha_psa    = np.clip(tendencia + ruido, 0.0, 200_000.0)

    df = pd.DataFrame({
        "anio":   anios,
        "ha_psa": np.round(ha_psa, 0).astype(int),
    })

    out_path = OUTPUT / "predios_conservacion_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos generados: %d años (%d-%d) | PSA final=%d ha | guardados en %s",
                n, INICIO, FIN, int(ha_psa[-1]), out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='predios_conservacion')."""
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
    """Estadísticas descriptivas por subperíodo (pre/post ruptura)."""
    logger.info("--- EDA + Descriptiva ---")

    serie = df["ha_psa"].astype(float)
    logger.info("Global: media=%.0f ha | mediana=%.0f ha | std=%.0f | [%.0f, %.0f]",
                serie.mean(), serie.median(), serie.std(), serie.min(), serie.max())

    periodos = [
        ("2010-2016 (pre-ruptura)",  (INICIO, RUPTURA)),
        ("2017-2025 (post-ruptura)", (RUPTURA + 1, FIN)),
    ]
    rows = []
    for label, (a, b) in periodos:
        sub = df[(df["anio"] >= a) & (df["anio"] <= b)]["ha_psa"].astype(float)
        rows.append({
            "periodo":              label,
            "n":                    len(sub),
            "media_ha":             round(float(sub.mean()), 0),
            "mediana_ha":           round(float(sub.median()), 0),
            "std_ha":               round(float(sub.std()), 0),
            "min_ha":               round(float(sub.min()), 0),
            "max_ha":               round(float(sub.max()), 0),
            "incremento_total_ha":  round(float(sub.max() - sub.min()), 0),
        })
        logger.info("  %-30s media=%.0f ha | std=%.0f | incr.total=%.0f ha",
                    label, rows[-1]["media_ha"], rows[-1]["std_ha"],
                    rows[-1]["incremento_total_ha"])

    resumen = pd.DataFrame(rows).set_index("periodo")
    out_path = OUTPUT / "predios_conservacion_descriptiva.csv"
    resumen.to_csv(out_path)
    logger.info("Descriptiva guardada: %s", out_path.name)
    return resumen


# ===========================================================================
# 4. INFERENCIAL — MANN-KENDALL + PUNTO DE QUIEBRE
# ===========================================================================

def _chow_f(serie: pd.Series, ruptura_idx: int) -> dict:
    """Chow test simplificado para detectar cambio de pendiente en 'ruptura_idx'.

    Compara el RSS del modelo completo vs la suma de RSS de dos segmentos.
    F = ((RSS_c - RSS_1 - RSS_2) / k) / ((RSS_1 + RSS_2) / (n - 2k))
    donde k=2 (intercepto + pendiente), n=len(serie).
    """
    from scipy import stats as spstats

    t = np.arange(len(serie)).reshape(-1, 1)
    y = serie.values

    # Regresión completa
    t_c  = np.column_stack([np.ones(len(y)), t])
    coef_c, rss_c, *_ = np.linalg.lstsq(t_c, y, rcond=None)
    y_hat_c = t_c @ coef_c
    rss_c   = float(np.sum((y - y_hat_c) ** 2))

    # Segmento 1 (pre-ruptura)
    y1 = y[:ruptura_idx]
    t1 = np.column_stack([np.ones(len(y1)), np.arange(len(y1))])
    coef_1, *_ = np.linalg.lstsq(t1, y1, rcond=None)
    rss_1 = float(np.sum((y1 - t1 @ coef_1) ** 2))

    # Segmento 2 (post-ruptura)
    y2 = y[ruptura_idx:]
    t2 = np.column_stack([np.ones(len(y2)), np.arange(len(y2))])
    coef_2, *_ = np.linalg.lstsq(t2, y2, rcond=None)
    rss_2 = float(np.sum((y2 - t2 @ coef_2) ** 2))

    n, k = len(y), 2
    if (rss_1 + rss_2) == 0 or n <= 2 * k:
        return {"f_stat": float("nan"), "p_value": float("nan"), "ruptura_detectada": False}

    f_stat = ((rss_c - rss_1 - rss_2) / k) / ((rss_1 + rss_2) / (n - 2 * k))
    p_value = float(1 - spstats.f.cdf(f_stat, dfn=k, dfd=n - 2 * k))
    return {
        "f_stat":            round(float(f_stat), 4),
        "p_value":           round(float(p_value), 6),
        "ruptura_detectada": p_value < 0.05,
        "pendiente_pre":     round(float(coef_1[1]), 2),
        "pendiente_post":    round(float(coef_2[1]), 2),
    }


def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall + Chow test de ruptura estructural en 2016."""
    logger.info("--- Inferencial ---")
    resultados: dict = {}

    serie = pd.Series(
        df["ha_psa"].astype(float).values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="ha_psa",
    )

    # Mann-Kendall
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk = mann_kendall(serie)
        ss = sens_slope(serie)
        slope_anual = float(ss.get("slope", 0.0))
        resultados["mann_kendall"] = {
            "tendencia":         mk.get("trend", "unknown"),
            "p_value":           round(float(mk.get("pval", 1.0)), 6),
            "significativo":     mk.get("pval", 1.0) < 0.05,
            "tau":               round(float(mk.get("tau", 0.0)), 4),
            "sen_slope_anual_ha": round(float(slope_anual), 1),
        }
        r = resultados["mann_kendall"]
        logger.info("Mann-Kendall: %s | p=%.6f | slope=%.1f ha/año%s",
                    r["tendencia"], r["p_value"], r["sen_slope_anual_ha"],
                    " [SIGNIFICATIVO]" if r["significativo"] else "")
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # Chow test — ruptura en 2016
    try:
        ruptura_idx = int(df[df["anio"] == RUPTURA].index[0]) - df.index[0] + 1
        chow = _chow_f(serie, ruptura_idx)
        resultados["chow_test"] = {
            "anio_ruptura":    RUPTURA,
            "f_stat":          chow["f_stat"],
            "p_value":         chow["p_value"],
            "ruptura_detectada": chow["ruptura_detectada"],
            "pendiente_pre_ha_anio":  chow.get("pendiente_pre"),
            "pendiente_post_ha_anio": chow.get("pendiente_post"),
        }
        logger.info(
            "Chow test (ruptura=%d): F=%.4f | p=%.6f | %s | pre=%.1f ha/año, post=%.1f ha/año",
            RUPTURA,
            chow["f_stat"],
            chow["p_value"],
            "RUPTURA DETECTADA" if chow["ruptura_detectada"] else "sin ruptura significativa",
            chow.get("pendiente_pre", float("nan")),
            chow.get("pendiente_post", float("nan")),
        )
    except Exception as exc:
        logger.warning("Chow test skipped: %s", exc)

    out_path = OUTPUT / "predios_conservacion_inferencial.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_path.name)
    return resultados


# ===========================================================================
# 5. ARIMA + PRONÓSTICO 5 AÑOS
# ===========================================================================

def modelado_predictivo(df: pd.DataFrame) -> dict:
    """ARIMA(1,1,0) sobre la serie anual — pronóstico 5 años.

    La ruptura estructural ya está en los datos, por lo que ARIMA(1,1,0)
    con diferenciación capta el cambio de nivel. No se usa walk-forward
    (solo 16 observaciones).
    """
    logger.info("--- Modelado predictivo (ARIMA anual) ---")

    serie = pd.Series(
        df["ha_psa"].astype(float).values,
        index=pd.to_datetime(df["anio"].astype(str) + "-01-01"),
        name="ha_psa",
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
            preds_in = np.clip(model.predict(len(serie)), 0.0, 1_000_000.0)
            preds_in = preds_in[-len(serie):]
            from estadistica_ambiental.evaluation.metrics import evaluate
            metrics = evaluate(y_true=serie.values, y_pred=preds_in, domain="general")
            resultados["arima_metrics_insample"] = metrics
            logger.info("ARIMA (insample) — RMSE=%.0f ha | MAE=%.0f ha | R2=%.4f",
                        metrics.get("rmse", float("nan")),
                        metrics.get("mae", float("nan")),
                        metrics.get("r2", float("nan")))
        except Exception as exc_m:
            logger.warning("Métricas insample skipped: %s", exc_m)

        # Pronóstico 5 años (2026-2030)
        horizon       = 5
        forecast_vals = np.clip(model.predict(horizon), 0.0, 1_000_000.0)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(years=1),
            periods=horizon, freq="YS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="ha_psa_forecast")

        fc_path = OUTPUT / "predios_conservacion_forecast.csv"
        forecast.to_csv(fc_path, header=True)
        logger.info("Pronóstico 5 años guardado: %s", fc_path.name)
        for fecha, val in forecast.items():
            logger.info("  %d: %.0f ha", fecha.year, val)

        resultados["forecast"] = {str(k.year): round(float(v), 0) for k, v in forecast.items()}
        resultados["forecast_2030_ha"] = round(float(list(forecast.values())[-1]), 0)

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            y_ref    = serie.copy()
            pred_arr = np.clip(model.predict(len(serie)), 0.0, 1_000_000.0)[-len(serie):]
            report_path = OUTPUT / "predios_conservacion_reporte.html"
            forecast_report(
                y_true=y_ref,
                predictions={"ARIMA(1,1,0)": pred_arr},
                metrics=resultados.get("arima_metrics_insample", {}),
                output=str(report_path),
                title="Predios PSA — Conservación Colombia (2010-2025)",
                variable_name="Hectáreas bajo PSA",
                unit="ha",
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
    logger.info("FASE 8 — PREDIOS PARA CONSERVACIÓN | Hectáreas PSA")
    logger.info("Serie anual %d-%d | ruptura esperada en %d", INICIO, FIN, RUPTURA)
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

    # 4. Inferencial (MK + Chow)
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
    logger.info("RESUMEN EJECUTIVO — Predios para Conservación (PSA)")
    logger.info("  Período: %d-%d | n=%d puntos anuales", INICIO, FIN, len(df))
    logger.info("  PSA %d: %d ha → %d: %d ha",
                INICIO, int(df.loc[df["anio"] == INICIO, "ha_psa"].iloc[0]),
                FIN, int(df.loc[df["anio"] == FIN, "ha_psa"].iloc[0]))
    mk_r = inf.get("mann_kendall", {})
    if mk_r:
        logger.info("  MK: %s | p=%.6f | %.1f ha/año%s",
                    mk_r.get("tendencia", "?"),
                    mk_r.get("p_value", 1.0),
                    mk_r.get("sen_slope_anual_ha", 0.0),
                    " [SIGNIF.]" if mk_r.get("significativo") else "")
    chow = inf.get("chow_test", {})
    if chow:
        logger.info("  Chow (%d): F=%.4f | p=%.6f | %s",
                    RUPTURA, chow.get("f_stat", float("nan")),
                    chow.get("p_value", float("nan")),
                    "RUPTURA DETECTADA" if chow.get("ruptura_detectada") else "sin ruptura signif.")
        logger.info("  Pendiente pre-ruptura: %.1f ha/año | post-ruptura: %.1f ha/año",
                    chow.get("pendiente_pre_ha_anio", float("nan")),
                    chow.get("pendiente_post_ha_anio", float("nan")))
    if pred.get("forecast_2030_ha"):
        logger.info("  Proyección PSA 2030: %.0f ha", pred["forecast_2030_ha"])
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Predios para Conservación completada.")


if __name__ == "__main__":
    main()
