"""
Fase 8 — Ciclo estadístico completo: Áreas Protegidas.

Línea temática: Áreas Protegidas (cobertura boscosa como proxy de conservación)
Variable objetivo: cobertura boscosa (ha), serie anual 2000-2024
Frecuencia: anual (25 observaciones) — no aplica ENSO (serie demasiado corta para lag)
Métricas: MAE y RMSE (dominio general — ha siempre ≥ 0)
Análisis especial: Mann-Kendall de deforestación (pérdida anual de cobertura en ha)

Flujo:
  1. Generación/carga de datos sintéticos (cobertura boscosa anual)
  2. Validación básica (rangos físicos)
  3. EDA (tendencias, cambios post-2016)
  4. Descriptiva anual + pérdida acumulada
  5. Inferencial: Mann-Kendall de la tasa de deforestación (pymannkendall),
     ADF/KPSS de la serie de cobertura (ADR-004)
  6. Predictiva: ARIMA(1,1,1) + ARIMA(2,1,0) — walk_forward(domain='general')
     rank_models(domain='general')
     Series anuales cortas → no usar SARIMA estacional (período insuficiente)
  7. Reporte: forecast_report (cobertura boscosa)
     No aplica compliance_report (no hay norma colombiana de umbrales de cobertura
     en excedencia; la comparación es con metas de conservación del SINAP)

Salidas en data/output/reports/:
  - areas_protegidas_forecast.html
  - areas_protegidas_descriptiva.csv
  - areas_protegidas_inferencial.json
  - areas_protegidas_ranking.csv

Uso:
    python scripts/fase8_areas_protegidas.py
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
logger = logging.getLogger("fase8_areas_protegidas")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
RAW    = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "output" / "reports"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "areas_protegidas"
VARIABLE = "cobertura_ha"
AREA_REF = "SINAP_Colombia_Bosque_sintetica"

# Tasa de deforestación de referencia del IDEAM/SMByC (% anual)
TASA_DEFORESTACION_BASE = 0.008   # 0.8%/año histórica
DEFORESTACION_CRITICA_HA = 100_000.0   # ha/año — umbral de alerta IDEAM


# ===========================================================================
# 1. DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_sinteticos(
    start_year: int = 2000,
    end_year: int = 2024,
    seed: int = 42,
) -> pd.DataFrame:
    """Genera cobertura boscosa anual sintética (ha) con dinámica realista.

    Modelo:
    - Base: 1,000,000 ha (cuenca/área protegida andina grande)
    - Pérdida 0.8%/año por deforestación (2000-2015)
    - Recuperación post-2016: +0.2%/año (Acuerdo de Paz → reducción frontera agrícola)
    - Ruido gaussiano σ=5,000 ha (variabilidad en detección satelital)

    El quiebre en 2016 refleja la reducción de deforestación post-Acuerdo de Paz
    documentada por IDEAM/SMByC: entre 2017-2018 hubo repunte por colonización en
    áreas de las FARC, pero 2019-2024 muestra tendencia decreciente en pérdida.
    """
    rng = np.random.default_rng(seed)
    anios = list(range(start_year, end_year + 1))
    n = len(anios)

    cobertura = np.zeros(n)
    cobertura[0] = 1_000_000.0  # ha en 2000

    for i in range(1, n):
        anio = anios[i]
        if anio <= 2015:
            # Deforestación neta -0.8%/año (presión agropecuaria y minería)
            tasa = -TASA_DEFORESTACION_BASE
        elif 2016 <= anio <= 2018:
            # Repunte post-Acuerdo por colonización de zonas antes vedadas
            # Este efecto paradójico está documentado por IDEAM 2017-2019
            tasa = -0.006
        else:
            # Recuperación gradual: reforestación y menor presión agropecuaria
            tasa = -0.003 + 0.002 * ((anio - 2019) / 5)  # mejora progresiva

        ruido_ha = rng.normal(0, 5_000.0)
        cobertura[i] = cobertura[i - 1] * (1 + tasa) + ruido_ha
        cobertura[i] = max(cobertura[i], 500_000.0)  # piso físico razonable

    # Pérdida anual de cobertura (ha)
    perdida_ha = np.concatenate([[0.0], np.diff(cobertura)])   # negativo = deforestación
    deforestacion_ha = np.clip(-perdida_ha, 0, None)  # solo valores de pérdida

    df = pd.DataFrame({
        "anio":              anios,
        "cobertura_ha":      np.round(cobertura, 0),
        "deforestacion_ha":  np.round(deforestacion_ha, 0),
        "area_ref":          AREA_REF,
    })

    out = RAW / "areas_protegidas_sintetica.csv"
    df.to_csv(out, index=False)
    logger.info("Datos sintéticos áreas protegidas: %d años | guardados en %s", n, out.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def cargar_y_validar(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Validación de rangos físicos y preparación de la serie temporal."""
    logger.info("--- Validación Áreas Protegidas ---")

    # Rango físico razonable para cobertura boscosa colombiana
    lo_ha, hi_ha = 100_000.0, 10_000_000.0
    if "cobertura_ha" in df_raw.columns:
        n_out = int(((df_raw["cobertura_ha"] < lo_ha) |
                     (df_raw["cobertura_ha"] > hi_ha)).sum())
        if n_out:
            logger.warning("cobertura_ha: %d valores fuera de [%.0f, %.0f] ha",
                           n_out, lo_ha, hi_ha)

    n_missing = int(df_raw["cobertura_ha"].isna().sum())
    if n_missing:
        logger.warning("cobertura_ha: %d faltantes — interpolación lineal", n_missing)

    # Construir serie con índice datetime anual
    df_raw["fecha"] = pd.to_datetime(df_raw["anio"].astype(str) + "-01-01")
    serie = (
        df_raw.set_index("fecha")["cobertura_ha"]
        .sort_index()
        .astype(float)
        .interpolate(method="linear")
        .dropna()
    )

    pct_perdida = (1 - serie.iloc[-1] / serie.iloc[0]) * 100
    logger.info("Cobertura 2000: %.0f ha | Cobertura final: %.0f ha | Pérdida: %.1f%%",
                serie.iloc[0], serie.iloc[-1], pct_perdida)
    return df_raw, serie


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(df_raw: pd.DataFrame, serie: pd.Series) -> dict:
    """EDA: tendencias, quiebre post-2016, distribución anual."""
    logger.info("--- EDA Áreas Protegidas ---")

    stats = serie.describe()

    # Tasa de cambio anual media
    cambio_anual = serie.pct_change().dropna() * 100
    tasa_media = float(cambio_anual.mean())
    tasa_std   = float(cambio_anual.std())

    # Período pre y post 2016
    pre_2016  = serie[serie.index.year <= 2015]
    post_2016 = serie[serie.index.year > 2015]
    tasa_pre  = float(pre_2016.pct_change().dropna().mean() * 100)
    tasa_post = float(post_2016.pct_change().dropna().mean() * 100)

    # Deforestación histórica
    if "deforestacion_ha" in df_raw.columns:
        def_total = float(df_raw["deforestacion_ha"].sum())
        def_max   = float(df_raw["deforestacion_ha"].max())
        anio_max  = int(df_raw.loc[df_raw["deforestacion_ha"].idxmax(), "anio"])
        n_criticos = int((df_raw["deforestacion_ha"] >= DEFORESTACION_CRITICA_HA).sum())
    else:
        def_total = def_max = anio_max = n_criticos = float("nan")

    logger.info("Cobertura — min: %.0f ha | max: %.0f ha", stats["min"], stats["max"])
    logger.info("Tasa cambio anual media: %.3f%% (σ=%.3f%%)", tasa_media, tasa_std)
    logger.info("Tasa pre-2016: %.3f%% | post-2016: %.3f%%", tasa_pre, tasa_post)
    logger.info("Deforestación total: %.0f ha | pico: %.0f ha (%d) | años críticos: %d",
                def_total, def_max, anio_max, n_criticos)

    return {
        "n_anios": len(serie),
        "cobertura_2000_ha": round(float(serie.iloc[0]), 0),
        "cobertura_final_ha": round(float(serie.iloc[-1]), 0),
        "perdida_total_ha": round(float(serie.iloc[0] - serie.iloc[-1]), 0),
        "perdida_pct": round((1 - serie.iloc[-1] / serie.iloc[0]) * 100, 2),
        "tasa_cambio_media_pct": round(tasa_media, 4),
        "tasa_pre2016_pct": round(tasa_pre, 4),
        "tasa_post2016_pct": round(tasa_post, 4),
        "deforestacion_total_ha": round(def_total, 0),
        "anio_deforestacion_max": anio_max,
        "anios_criticos": n_criticos,
    }


# ===========================================================================
# 4. DESCRIPTIVA
# ===========================================================================

def descriptiva(df_raw: pd.DataFrame, serie: pd.Series) -> pd.DataFrame:
    """Resumen anual: cobertura, deforestación acumulada, tasa."""
    logger.info("--- Descriptiva Áreas Protegidas ---")

    df = pd.DataFrame({
        "anio":          serie.index.year,
        "cobertura_ha":  serie.values,
    })
    df["cambio_ha"]    = df["cobertura_ha"].diff().fillna(0.0).round(0)
    df["cambio_pct"]   = (df["cobertura_ha"].pct_change() * 100).round(3)
    df["acum_perdida"] = (df["cobertura_ha"].iloc[0] - df["cobertura_ha"]).round(0)

    if "deforestacion_ha" in df_raw.columns:
        df = df.merge(
            df_raw[["anio", "deforestacion_ha"]],
            on="anio", how="left",
        )

    logger.info("Cobertura anual (últimos 5 años):")
    for _, row in df.tail(5).iterrows():
        logger.info("  %d: %.0f ha | cambio: %+.0f ha (%.3f%%)",
                    row["anio"], row["cobertura_ha"],
                    row["cambio_ha"], row.get("cambio_pct", float("nan")))

    out = OUTPUT / "areas_protegidas_descriptiva.csv"
    df.to_csv(out, index=False)
    logger.info("Descriptiva guardada: %s", out.name)
    return df


# ===========================================================================
# 5. INFERENCIAL
# ===========================================================================

def inferencial(df_raw: pd.DataFrame, serie: pd.Series) -> dict:
    """Mann-Kendall de deforestación + ADF/KPSS de cobertura.

    Se aplica Mann-Kendall a la serie de deforestación (ha/año), no a la cobertura,
    porque el test detecta tendencia monotónica en la presión (pérdida de bosque),
    que es la variable de política en POMCA/PUEEA/Áreas Protegidas.

    Se usa pymannkendall directamente (mk_test = original_test) como indica el enunciado.
    """
    logger.info("--- Inferencial Áreas Protegidas ---")
    resultados: dict = {}

    # 5.1 Mann-Kendall sobre deforestación anual (ha)
    # La deforestación (no la cobertura) es la variable de tendencia de interés
    try:
        from pymannkendall import original_test as mk_test

        if "deforestacion_ha" in df_raw.columns:
            def_serie = df_raw.set_index("anio")["deforestacion_ha"].sort_index()
        else:
            # Derivar deforestación como pérdida absoluta anual desde la cobertura
            def_serie = (-serie.diff().dropna()).clip(lower=0)
            def_serie.index = def_serie.index.year

        def_clean = def_serie.dropna()
        mk = mk_test(def_clean.values)
        resultados["mann_kendall_deforestacion"] = {
            "tendencia":    mk.trend,
            "h":            bool(mk.h),
            "p_value":      round(float(mk.p), 6),
            "significativo": float(mk.p) < 0.05,
            "tau":          round(float(mk.Tau), 4),
            "sen_slope_ha_anio": round(float(mk.slope), 2),
        }
        mk_r = resultados["mann_kendall_deforestacion"]
        logger.info("Mann-Kendall deforestación: %s (p=%.4f, sig=%s) | Sen slope=%.2f ha/año",
                    mk_r["tendencia"], mk_r["p_value"], mk_r["significativo"],
                    mk_r["sen_slope_ha_anio"])

        # Interpretación de política
        if mk_r["significativo"]:
            if mk.slope < 0:
                logger.info("  -> Tendencia de REDUCCIÓN en deforestación (positivo para conservación)")
            else:
                logger.info("  -> Tendencia de AUMENTO en deforestación (alerta de política)")
        else:
            logger.info("  -> Sin tendencia significativa en deforestación")

    except ImportError:
        logger.warning("pymannkendall no instalado — pip install pymannkendall")
        # Fallback: Mann-Kendall vía módulo interno del proyecto
        try:
            from estadistica_ambiental.inference.trend import mann_kendall
            if "deforestacion_ha" in df_raw.columns:
                def_serie_pd = (
                    df_raw.set_index("anio")["deforestacion_ha"]
                    .sort_index()
                    .dropna()
                )
            else:
                def_serie_pd = (-serie.diff().dropna()).clip(lower=0)
            mk_i = mann_kendall(def_serie_pd)
            resultados["mann_kendall_deforestacion"] = {
                "tendencia": mk_i.get("trend", "unknown"),
                "p_value": mk_i.get("pval", 1.0),
                "significativo": mk_i.get("pval", 1.0) < 0.05,
                "sen_slope_ha_anio": mk_i.get("slope", 0.0),
            }
            logger.info("Mann-Kendall (interno): %s (p=%.4f)",
                        resultados["mann_kendall_deforestacion"]["tendencia"],
                        resultados["mann_kendall_deforestacion"]["p_value"])
        except Exception as exc2:
            logger.warning("Mann-Kendall fallback también falló: %s", exc2)
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # 5.2 ADF + KPSS sobre cobertura boscosa (ADR-004 — antes de ARIMA)
    # Con 25 observaciones ADF es poco potente, pero es obligatorio (ADR-004)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf    = adf_test(serie)
        kpss_r = kpss_test(serie)
        resultados["estacionariedad"] = {
            "adf_stationary": bool(adf["stationary"]),
            "adf_pvalue": round(float(adf["pval"]), 4),
            "kpss_stationary": bool(kpss_r["stationary"]),
            "kpss_pvalue": round(float(kpss_r["pval"]), 4),
            "nota": "n=25 — potencia baja; ADF puede no rechazar H0 con muestras pequeñas",
        }
        est = resultados["estacionariedad"]
        logger.info("ADF: %s (p=%.4f) | KPSS: %s (p=%.4f)",
                    "estacionaria" if est["adf_stationary"] else "no estacionaria",
                    est["adf_pvalue"],
                    "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                    est["kpss_pvalue"])
        logger.info("  Nota: n=%d — con muestras pequeñas ADF tiene poca potencia", len(serie))
    except Exception as exc:
        logger.warning("ADF/KPSS skipped: %s", exc)

    # Guardar
    out = OUTPUT / "areas_protegidas_inferencial.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out.name)
    return resultados


# ===========================================================================
# 6. PREDICTIVA
# ===========================================================================

def predictiva(serie: pd.Series) -> dict:
    """ARIMA(1,1,1) + ARIMA(2,1,0) — walk-forward domain='general'.

    No se usa SARIMA porque la serie es anual (25 obs) y no hay suficientes
    períodos para estimar un componente estacional anual (necesitaría ≥3 ciclos
    completos de periodo P, e.g., P=1 en datos anuales ya no tiene sentido).

    ARIMA(1,1,1): modelo de referencia Box-Jenkins para series con tendencia.
    ARIMA(2,1,0): alternativa con más autocorrelación AR, sin MA — más simple.

    n_splits=3 porque con 25 años y horizon=2, necesitamos al menos 10 años de
    entrenamiento mínimo, lo que deja solo ~7-8 puntos de test en 3 folds.
    """
    logger.info("--- Predictiva Áreas Protegidas (dominio: general) ---")
    logger.info("Serie anual: %d años (%d → %d)",
                len(serie), serie.index.year.min(), serie.index.year.max())

    resultados: dict = {}
    bt_results: dict = {}

    # Convertir índice a frecuencia anual explícita para statsmodels
    serie_a = serie.copy()
    if not isinstance(serie_a.index.freq, type(None)):
        pass
    else:
        # Reasignar frecuencia anual — necesario para que SARIMAX funcione correctamente
        serie_a = serie_a.asfreq("YS")   # año-inicio ('YS' = year start)
        serie_a = serie_a.interpolate(method="linear")

    # 6.1 ARIMA(1,1,1) — baseline Box-Jenkins
    try:
        from estadistica_ambiental.predictive.classical import ARIMAModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_arima111 = ARIMAModel(order=(1, 1, 1))
        logger.info("Entrenando ARIMA(1,1,1)...")
        res = walk_forward(
            model_arima111, serie_a,
            horizon=2,       # 2 años de horizonte
            n_splits=3,      # 3 folds conservadores por tamaño muestral pequeño
            min_train_size=12,  # mínimo 12 años de entrenamiento
            domain="general",
        )
        bt_results["ARIMA(1,1,1)"] = res
        m = res["metrics"]
        resultados["arima111_metrics"] = m
        logger.info("ARIMA(1,1,1) → RMSE=%.0f ha | MAE=%.0f ha | R²=%.4f",
                    m.get("rmse", float("nan")), m.get("mae", float("nan")),
                    m.get("r2", float("nan")))
    except Exception as exc:
        logger.error("ARIMA(1,1,1) falló: %s", exc)

    # 6.2 ARIMA(2,1,0) — modelo alternativo parsimónico
    try:
        from estadistica_ambiental.predictive.classical import ARIMAModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_arima210 = ARIMAModel(order=(2, 1, 0))
        logger.info("Entrenando ARIMA(2,1,0)...")
        res = walk_forward(
            model_arima210, serie_a,
            horizon=2,
            n_splits=3,
            min_train_size=12,
            domain="general",
        )
        bt_results["ARIMA(2,1,0)"] = res
        m = res["metrics"]
        resultados["arima210_metrics"] = m
        logger.info("ARIMA(2,1,0) → RMSE=%.0f ha | MAE=%.0f ha | R²=%.4f",
                    m.get("rmse", float("nan")), m.get("mae", float("nan")),
                    m.get("r2", float("nan")))
    except Exception as exc:
        logger.warning("ARIMA(2,1,0) skipped: %s", exc)

    # 6.3 Ranking multi-criterio
    if len(bt_results) >= 2:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models
            ranking = rank_models(bt_results, domain="general")
            rank_path = OUTPUT / "areas_protegidas_ranking.csv"
            ranking.to_csv(rank_path)
            logger.info("Ranking modelos Áreas Protegidas:")
            for idx, row in ranking.iterrows():
                logger.info("  Rank %d: %s | RMSE=%.0f ha | MAE=%.0f ha | score=%.4f",
                            int(row.get("rank", 0)), idx,
                            row.get("rmse", float("nan")),
                            row.get("mae", float("nan")),
                            row.get("score", float("nan")))
            resultados["mejor_modelo"] = str(ranking.index[0])
            logger.info("Ranking guardado: %s", rank_path.name)
        except Exception as exc:
            logger.warning("rank_models skipped: %s", exc)
    else:
        logger.warning("Menos de 2 modelos — ranking omitido")

    # 6.4 Guardar métricas por fold
    bt_fold_path = OUTPUT / "areas_protegidas_backtesting.csv"
    first_write = True
    for nombre, res in bt_results.items():
        folds_df = res.get("folds", pd.DataFrame())
        if not folds_df.empty:
            folds_df = folds_df.copy()
            folds_df["modelo"] = nombre
            folds_df.to_csv(bt_fold_path, mode="a", header=first_write, index=False)
            first_write = False

    # 6.5 Pronóstico 5 años + forecast_report
    try:
        from estadistica_ambiental.predictive.classical import ARIMAModel
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        model_fc = ARIMAModel(order=(1, 1, 1))
        model_fc.fit(serie_a)
        # 5 años de pronóstico — horizonte relevante para planificación de áreas protegidas
        forecast_vals = np.clip(model_fc.predict(5), 100_000.0, 20_000_000.0)
        logger.info("Pronóstico 5 años: media=%.0f ha | min=%.0f | max=%.0f ha",
                    forecast_vals.mean(), forecast_vals.min(), forecast_vals.max())

        pred_dict: dict = {}
        for nombre, res in bt_results.items():
            preds_df = res.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                pred_dict[nombre] = preds_df["predicted"].values

        metrics_dict = {n: r.get("metrics", {}) for n, r in bt_results.items()}

        if pred_dict:
            min_len = min(len(v) for v in pred_dict.values())
            actual_vals = bt_results[list(bt_results.keys())[0]]["predictions"]["actual"].values
            y_test_ref = pd.Series(actual_vals[:min_len], name="cobertura_obs")

            forecast_report(
                y_true=y_test_ref,
                predictions={k: v[:min_len] for k, v in pred_dict.items()},
                metrics=metrics_dict,
                output=str(OUTPUT / "areas_protegidas_forecast.html"),
                title="Pronóstico de Cobertura Boscosa — Áreas Protegidas Colombia",
                variable_name="Cobertura boscosa",
                unit="ha",
            )
            logger.info("forecast_report guardado: areas_protegidas_forecast.html")

        resultados["forecast_5a_mean"] = round(float(forecast_vals.mean()), 0)
        resultados["forecast_5a_min"]  = round(float(forecast_vals.min()), 0)
        resultados["forecast_5a_max"]  = round(float(forecast_vals.max()), 0)

    except Exception as exc:
        logger.warning("Pronóstico/forecast_report skipped: %s", exc)

    return resultados


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — ÁREAS PROTEGIDAS | Cobertura boscosa anual 2000-2024")
    logger.info("Área: %s", AREA_REF)
    logger.info("=" * 65)

    # 1. Datos — auto-detectar real, sintético como fallback
    parquet_real = RAW / "cobertura_bosques_real.parquet"
    csv_real     = RAW / "cobertura_bosques_real.csv"
    if parquet_real.exists():
        logger.info("Cargando datos reales: %s", parquet_real.name)
        df_raw = pd.read_parquet(parquet_real)
    elif csv_real.exists():
        logger.info("Cargando datos reales: %s", csv_real.name)
        df_raw = pd.read_csv(csv_real)
    else:
        logger.info("Sin datos reales — generando sintéticos (2000-2024)")
        df_raw = generar_datos_sinteticos()

    # 2. Validación
    try:
        df_raw, serie = cargar_y_validar(df_raw)
    except Exception as exc:
        logger.error("Carga/validación falló: %s", exc)
        return

    # 3. EDA
    eda_res: dict = {}
    try:
        eda_res = eda(df_raw, serie)
    except Exception as exc:
        logger.warning("EDA falló: %s", exc)

    # 4. Descriptiva (ENSO no aplica: serie anual corta sin lag significativo)
    try:
        descriptiva(df_raw, serie)
    except Exception as exc:
        logger.warning("Descriptiva falló: %s", exc)

    # 5. Inferencial (Mann-Kendall + ADF/KPSS)
    inf: dict = {}
    try:
        inf = inferencial(df_raw, serie)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)

    # 6. Predictiva
    pred: dict = {}
    try:
        pred = predictiva(serie)
    except Exception as exc:
        logger.error("Predictiva falló: %s", exc)

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — ÁREAS PROTEGIDAS")
    logger.info("  Cobertura 2000: %.0f ha → Final: %.0f ha",
                eda_res.get("cobertura_2000_ha", float("nan")),
                eda_res.get("cobertura_final_ha", float("nan")))
    logger.info("  Pérdida total: %.0f ha (%.1f%%)",
                eda_res.get("perdida_total_ha", float("nan")),
                eda_res.get("perdida_pct", float("nan")))
    logger.info("  Tasa pre-2016: %.3f%% | post-2016: %.3f%%",
                eda_res.get("tasa_pre2016_pct", float("nan")),
                eda_res.get("tasa_post2016_pct", float("nan")))
    logger.info("  Años con deforestación crítica (>%.0f ha): %d",
                DEFORESTACION_CRITICA_HA, eda_res.get("anios_criticos", 0))

    mk = inf.get("mann_kendall_deforestacion", {})
    if mk:
        sig_str = "SIGNIFICATIVO" if mk.get("significativo") else "no significativo"
        logger.info("  Mann-Kendall deforestación: %s (%s, p=%.4f) | %.2f ha/año",
                    mk.get("tendencia", "?"), sig_str, mk.get("p_value", 1.0),
                    mk.get("sen_slope_ha_anio", 0.0))

    arima111 = pred.get("arima111_metrics", {})
    arima210 = pred.get("arima210_metrics", {})
    if arima111:
        logger.info("  ARIMA(1,1,1) → RMSE=%.0f ha | MAE=%.0f ha",
                    arima111.get("rmse", float("nan")), arima111.get("mae", float("nan")))
    if arima210:
        logger.info("  ARIMA(2,1,0) → RMSE=%.0f ha | MAE=%.0f ha",
                    arima210.get("rmse", float("nan")), arima210.get("mae", float("nan")))
    logger.info("  Mejor modelo: %s", pred.get("mejor_modelo", "N/A"))
    logger.info("  Pronóstico 5 años: media=%.0f ha",
                pred.get("forecast_5a_mean", float("nan")))
    logger.info("  Salidas: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Áreas Protegidas completada.")


if __name__ == "__main__":
    main()
