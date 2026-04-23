"""
Fase 8 — Ciclo estadístico completo: PUEEA (Plan de Uso Eficiente y Ahorro del Agua).

Línea temática: PUEEA
Variable objetivo: consumo mensual de agua (m³/mes) por sector (doméstico + industrial)
Frecuencia: mensual, 2010-2025 (sintética si no hay real)
Métricas: RMSE, MAE, sMAPE (dominio general — consumo siempre ≥ 0)
Análisis de eficiencia: consumo real vs meta de reducción 15% (IDEAM)

Flujo:
  1. Generación/carga de datos sintéticos realistas
  2. Validación
  3. EDA (calidad, distribución por sector)
  4. ENSO con lag=3 meses (pueea — según config.ENSO_LAG_MESES)
  5. Descriptiva mensual y por sector
  6. Inferencial: ADF/KPSS, Mann-Kendall de tendencia de consumo
  7. Análisis de eficiencia: meta 15% IDEAM
  8. Predictiva: SARIMA(1,1,1)(1,0,1,12) + ETS — walk_forward(domain='general')
     rank_models(domain='general')
  9. Reportes: forecast_report (consumo total) — sin compliance_report
     ya que PUEEA no tiene norma de excedencia sino meta de reducción

Salidas en data/output/reports/:
  - pueea_forecast.html
  - pueea_descriptiva.csv
  - pueea_inferencial.json
  - pueea_ranking.csv
  - pueea_eficiencia.csv

Uso:
    python scripts/fase8_pueea.py
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
logger = logging.getLogger("fase8_pueea")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
RAW    = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "output" / "reports"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "pueea"
VARIABLE = "consumo_total"
ESTACION = "Municipio_Andino_PUEEA_sintetico"

# Meta de reducción IDEAM — 15% de ahorro respecto a línea base 2010
META_REDUCCION_PCT = 0.15


# ===========================================================================
# 1. DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_sinteticos(
    start: str = "2010-01",
    end: str = "2024-12",
    seed: int = 42,
) -> pd.DataFrame:
    """Genera consumo mensual sintético de agua (m³/mes) por sector.

    Modelo:
    - Doméstico: 120,000 m³/mes base, crecimiento 1.5%/año (urbanización)
    - Industrial: 80,000 m³/mes base, crecimiento 1.5%/año (industria en expansión)
    - Estacionalidad débil: temporada seca (dic-feb) eleva consumo doméstico ~12%
    - Outliers en temporada seca: 5 meses con picos de demanda (+25-40%)
    - Ruido AR(1) ρ=0.6 — consumo mensual tiene memoria moderada

    El crecimiento 1.5%/año refleja la tasa histórica de aumento de demanda hídrica
    urbana en municipios andinos colombianos (IDEAM, ENA 2018).
    """
    rng = np.random.default_rng(seed)
    fechas = pd.period_range(start, end, freq="M").to_timestamp()
    n = len(fechas)
    t = np.arange(n)

    # Tasa de crecimiento mensual (1.5%/año → 0.125%/mes)
    tasa_mensual = 1.015 ** (1 / 12) - 1
    crecimiento = (1 + tasa_mensual) ** t

    # Estacionalidad mensual (ciclo anual, pico en enero y agosto)
    mes = pd.DatetimeIndex(fechas).month
    seasonal_factor = 1.0 + 0.12 * np.cos(2 * np.pi * (mes - 1) / 12)

    # AR(1) ρ=0.6 — ruido correlacionado
    ruido = np.zeros(n)
    ruido[0] = rng.standard_normal()
    for i in range(1, n):
        ruido[i] = 0.6 * ruido[i - 1] + rng.standard_normal() * np.sqrt(1 - 0.6**2)

    # Volúmenes base por sector (m³/mes)
    dom_base = 120_000.0
    ind_base  = 80_000.0
    sigma_rel = 0.06  # variabilidad relativa del 6%

    dom = dom_base * crecimiento * seasonal_factor * (1 + sigma_rel * ruido)
    ind = ind_base * crecimiento * (1 + sigma_rel * 0.7 * ruido)

    # Outliers en temporada seca (dic-feb): 5 eventos de demanda pico
    # Representa restricciones del sistema que elevan presión sobre el recurso
    idx_dic_feb = np.where(mes <= 2)[0]
    if len(idx_dic_feb) >= 5:
        outlier_idx = rng.choice(idx_dic_feb, size=5, replace=False)
        for oi in outlier_idx:
            factor = rng.uniform(1.25, 1.40)
            dom[oi] *= factor

    consumo_total = dom + ind
    consumo_total = np.clip(consumo_total, 10_000.0, 1_000_000.0)

    df = pd.DataFrame({
        "fecha":           fechas,
        "consumo_dom":     np.round(dom, 0),
        "consumo_ind":     np.round(ind, 0),
        "consumo_total":   np.round(consumo_total, 0),
        "estacion":        ESTACION,
    })

    out = RAW / "pueea_sintetica.csv"
    df.to_csv(out, index=False)
    logger.info("Datos sintéticos PUEEA: %d meses | guardados en %s", n, out.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def cargar_y_validar(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Valida plausibilidad física y devuelve serie de consumo total."""
    logger.info("--- Validación PUEEA ---")

    # Validación manual de rangos: consumo mensual urbano Colombia 50k-500k m³/mes
    for col in ("consumo_total", "consumo_dom", "consumo_ind"):
        if col in df_raw.columns:
            n_neg = int((df_raw[col] < 0).sum())
            if n_neg:
                logger.warning("'%s': %d valores negativos (imposibles)", col, n_neg)

    serie = (
        df_raw.set_index("fecha")["consumo_total"]
        .sort_index()
        .astype(float)
    )
    n_missing = int(serie.isna().sum())
    if n_missing:
        logger.warning("Consumo total: %d valores faltantes — se imputa con interpolación lineal",
                       n_missing)
        # Interpolación lineal para faltantes en consumo: el consumo varía suavemente
        serie = serie.interpolate(method="linear", limit=3)
        serie = serie.dropna()

    logger.info("Serie consumo total: %d meses | %s → %s",
                len(serie), serie.index.min().date(), serie.index.max().date())
    return df_raw, serie


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(df_raw: pd.DataFrame, serie: pd.Series) -> dict:
    """EDA: distribución, tendencia visual, estacionalidad, outliers."""
    logger.info("--- EDA PUEEA ---")

    stats = serie.describe()
    cv = stats["std"] / stats["mean"] if stats["mean"] > 0 else float("nan")

    # Estacionalidad mensual
    mensual_media = serie.groupby(serie.index.month).mean()
    mes_max = int(mensual_media.idxmax())
    mes_min = int(mensual_media.idxmin())

    # Outliers estadísticos (IQR)
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    n_outliers = int(((serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)).sum())

    # Participación por sector (promedio histórico)
    if "consumo_dom" in df_raw.columns and "consumo_ind" in df_raw.columns:
        dom_pct = float(df_raw["consumo_dom"].mean() / df_raw["consumo_total"].mean() * 100)
        ind_pct = float(df_raw["consumo_ind"].mean() / df_raw["consumo_total"].mean() * 100)
    else:
        dom_pct = ind_pct = float("nan")

    logger.info("Consumo total — media: %.0f m³/mes | mediana: %.0f | CV: %.2f",
                stats["mean"], stats["50%"], cv)
    logger.info("Outliers IQR: %d (%.1f%%)", n_outliers, n_outliers / len(serie) * 100)
    logger.info("Pico de demanda: mes %02d | valle: mes %02d", mes_max, mes_min)
    logger.info("Participación: doméstico=%.1f%% | industrial=%.1f%%", dom_pct, ind_pct)

    return {
        "n_meses": len(serie),
        "media_m3mes": round(float(stats["mean"]), 0),
        "mediana_m3mes": round(float(stats["50%"]), 0),
        "max_m3mes": round(float(stats["max"]), 0),
        "cv": round(float(cv), 3),
        "n_outliers_iqr": n_outliers,
        "mes_pico_demanda": mes_max,
        "mes_valle_demanda": mes_min,
        "dom_pct": round(dom_pct, 1),
        "ind_pct": round(ind_pct, 1),
    }


# ===========================================================================
# 4. ENSO CON LAG
# ===========================================================================

def aplicar_enso(df_raw: pd.DataFrame) -> pd.DataFrame:
    """ENSO con lag=3 meses (pueea — demanda de agua responde a sequía con ~3 meses).

    En años El Niño la demanda hídrica aumenta porque la precipitación baja
    y la población depende más del suministro del sistema de acueducto.
    """
    logger.info("--- ENSO con lag (pueea) ---")
    try:
        from estadistica_ambiental.features.climate import enso_lagged, load_oni
        from estadistica_ambiental.config import ENSO_LAG_MESES
        oni = load_oni()
        if oni.empty:
            logger.warning("ONI vacío (sin red) — sin covariable ENSO")
            return df_raw
        df_enso = enso_lagged(df_raw, oni, date_col="fecha", linea_tematica=LINEA)
        lag = ENSO_LAG_MESES.get(LINEA, 3)
        fase_col = f"fase_lag{lag}"
        if fase_col in df_enso.columns:
            fases = df_enso[fase_col].value_counts().to_dict()
            logger.info("ENSO lag=%d meses | fases: %s", lag, fases)
        return df_enso
    except Exception as exc:
        logger.warning("ENSO skipped: %s", exc)
        return df_raw


# ===========================================================================
# 5. DESCRIPTIVA
# ===========================================================================

def descriptiva(serie: pd.Series, df_raw: pd.DataFrame) -> pd.DataFrame:
    """Resúmenes anuales de consumo por sector."""
    logger.info("--- Descriptiva PUEEA ---")

    df = serie.to_frame("consumo_total")
    df["anio"] = df.index.year

    anual = df.groupby("anio")["consumo_total"].agg(
        n="count",
        suma="sum",
        media="mean",
        min="min",
        max="max",
    ).round(0)

    if "consumo_dom" in df_raw.columns:
        df_raw_indexed = df_raw.set_index("fecha")
        dom_anual = df_raw_indexed["consumo_dom"].resample("YE").sum()
        ind_anual = df_raw_indexed["consumo_ind"].resample("YE").sum()
        dom_anual.index = dom_anual.index.year
        ind_anual.index = ind_anual.index.year
        anual["consumo_dom"] = dom_anual.reindex(anual.index).round(0)
        anual["consumo_ind"] = ind_anual.reindex(anual.index).round(0)

    logger.info("Consumo anual (últimos 5 años):")
    for anio, row in anual.tail(5).iterrows():
        logger.info("  %d: total=%.0f m³/año | media mensual=%.0f m³/mes",
                    anio, row["suma"], row["media"])

    out = OUTPUT / "pueea_descriptiva.csv"
    anual.to_csv(out)
    logger.info("Descriptiva guardada: %s", out.name)
    return anual


# ===========================================================================
# 6. ANÁLISIS DE EFICIENCIA
# ===========================================================================

def analisis_eficiencia(serie: pd.Series) -> pd.DataFrame:
    """Calcula consumo real vs meta de reducción 15% (IDEAM).

    Línea base = promedio del primer año completo de datos.
    Meta = línea_base × (1 - 0.15).
    """
    logger.info("--- Análisis de eficiencia PUEEA ---")

    # Línea base: promedio mensual del primer año con datos completos
    primer_anio = serie.index.year.min()
    linea_base = float(serie[serie.index.year == primer_anio].mean())
    meta = linea_base * (1 - META_REDUCCION_PCT)

    anual_media = serie.resample("YE").mean()
    df_ef = pd.DataFrame({
        "anio": anual_media.index.year,
        "consumo_medio_m3mes": anual_media.values.round(0),
        "linea_base_m3mes": linea_base,
        "meta_15pct_m3mes": round(meta, 0),
        "deficit_meta": (anual_media.values - meta).round(0),
        "cumple_meta": anual_media.values <= meta,
    })

    n_cumple = int(df_ef["cumple_meta"].sum())
    logger.info("Línea base PUEEA: %.0f m³/mes | Meta 15%%: %.0f m³/mes",
                linea_base, meta)
    logger.info("Años que cumplen la meta: %d / %d", n_cumple, len(df_ef))

    out = OUTPUT / "pueea_eficiencia.csv"
    df_ef.to_csv(out, index=False)
    logger.info("Eficiencia guardada: %s", out.name)
    return df_ef


# ===========================================================================
# 7. INFERENCIAL
# ===========================================================================

def inferencial(serie: pd.Series) -> dict:
    """ADF/KPSS + Mann-Kendall de tendencia de consumo."""
    logger.info("--- Inferencial PUEEA ---")
    resultados: dict = {}

    # 7.1 ADF + KPSS — requeridos antes de ARIMA (ADR-004)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf    = adf_test(serie)
        kpss_r = kpss_test(serie)
        resultados["estacionariedad"] = {
            "adf_stationary": bool(adf["stationary"]),
            "adf_pvalue": round(float(adf["pval"]), 4),
            "kpss_stationary": bool(kpss_r["stationary"]),
            "kpss_pvalue": round(float(kpss_r["pval"]), 4),
        }
        est = resultados["estacionariedad"]
        logger.info("ADF: %s (p=%.4f) | KPSS: %s (p=%.4f)",
                    "estacionaria" if est["adf_stationary"] else "no estacionaria",
                    est["adf_pvalue"],
                    "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                    est["kpss_pvalue"])
    except Exception as exc:
        logger.warning("ADF/KPSS skipped: %s", exc)

    # 7.2 Mann-Kendall — tendencia de largo plazo en consumo
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk = mann_kendall(serie)
        slope_d = sens_slope(serie)
        slope_anual = slope_d.get("slope", mk.get("slope", 0.0)) * 12
        resultados["mann_kendall"] = {
            "tendencia": mk.get("trend", "unknown"),
            "p_value": round(float(mk.get("pval", 1.0)), 4),
            "significativo": mk.get("pval", 1.0) < 0.05,
            "sen_slope_anual_m3": round(float(slope_anual), 0),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall consumo: %s (p=%.4f) | Sen slope=%.0f m³/año",
                    mk_r["tendencia"], mk_r["p_value"], mk_r["sen_slope_anual_m3"])
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # Guardar
    out = OUTPUT / "pueea_inferencial.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out.name)
    return resultados


# ===========================================================================
# 8. PREDICTIVA
# ===========================================================================

def predictiva(serie: pd.Series) -> dict:
    """SARIMA(1,1,1)(1,0,1,12) + ETS — walk-forward domain='general'.

    Se usa d=1 (una diferenciación) porque el consumo tiene tendencia creciente.
    D=0 en la parte estacional porque la estacionalidad es débil (CV < 15%).
    La elección ARIMA(1,1,1)(1,0,1,12) es el modelo parsimónico de Box-Jenkins
    para series de consumo con tendencia suave y estacionalidad débil.

    domain='general' porque el consumo de agua (m³/mes) siempre ≥ 0,
    así que sMAPE y MAE son métricas válidas (ADR-003 no aplica restricción RMSLE).
    """
    logger.info("--- Predictiva PUEEA (dominio: general) ---")
    logger.info("Serie mensual: %d meses (%s → %s)",
                len(serie), serie.index.min().date(), serie.index.max().date())

    resultados: dict = {}
    bt_results: dict = {}

    # 8.1 SARIMA(1,1,1)(1,0,1,12) — estacionalidad débil, tendencia fuerte
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_sarima = SARIMAXModel(
            order=(1, 1, 1),
            seasonal_order=(1, 0, 1, 12),   # D=0: estacionalidad no integrada (débil)
        )
        logger.info("Entrenando SARIMA(1,1,1)(1,0,1,12)...")
        res = walk_forward(model_sarima, serie, horizon=6, n_splits=5,
                           domain="general")
        bt_results["SARIMA(1,1,1)(1,0,1,12)"] = res
        m = res["metrics"]
        resultados["sarima_metrics"] = m
        logger.info("SARIMA → RMSE=%.0f | MAE=%.0f | sMAPE=%.2f%%",
                    m.get("rmse", float("nan")), m.get("mae", float("nan")),
                    m.get("smape", float("nan")))
    except Exception as exc:
        logger.error("SARIMA falló: %s", exc)

    # 8.2 ETS (Holt-Winters multiplicativo) — adecuado para tendencia + estacionalidad débil
    try:
        from estadistica_ambiental.predictive.classical import ETSModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        # Multiplicativo porque la amplitud de la estacionalidad crece con el nivel
        model_ets = ETSModel(trend="add", seasonal="add", seasonal_periods=12,
                             damped_trend=True)
        logger.info("Entrenando ETS (Holt-Winters, damped trend)...")
        res = walk_forward(model_ets, serie, horizon=6, n_splits=5, domain="general")
        bt_results["ETS_HoltWinters"] = res
        m = res["metrics"]
        resultados["ets_metrics"] = m
        logger.info("ETS → RMSE=%.0f | MAE=%.0f | sMAPE=%.2f%%",
                    m.get("rmse", float("nan")), m.get("mae", float("nan")),
                    m.get("smape", float("nan")))
    except Exception as exc:
        logger.warning("ETS skipped: %s", exc)

    # 8.3 Ranking multi-criterio (RMSE + MAE + R² + MASE)
    if len(bt_results) >= 2:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models
            ranking = rank_models(bt_results, domain="general")
            rank_path = OUTPUT / "pueea_ranking.csv"
            ranking.to_csv(rank_path)
            logger.info("Ranking modelos PUEEA:")
            for idx, row in ranking.iterrows():
                logger.info("  Rank %d: %s | RMSE=%.0f | MAE=%.0f | score=%.4f",
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

    # 8.4 Guardar métricas por fold
    bt_fold_path = OUTPUT / "pueea_backtesting.csv"
    first_write = True
    for nombre, res in bt_results.items():
        folds_df = res.get("folds", pd.DataFrame())
        if not folds_df.empty:
            folds_df = folds_df.copy()
            folds_df["modelo"] = nombre
            folds_df.to_csv(bt_fold_path, mode="a", header=first_write, index=False)
            first_write = False

    # 8.5 Pronóstico 12 meses + forecast_report
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        model_fc = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 0, 1, 12))
        model_fc.fit(serie)
        forecast_vals = np.clip(model_fc.predict(12), 10_000.0, 2_000_000.0)
        logger.info("Pronóstico 12 meses: media=%.0f | min=%.0f | max=%.0f m³/mes",
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
            y_test_ref = pd.Series(actual_vals[:min_len], name="consumo_obs")

            forecast_report(
                y_true=y_test_ref,
                predictions={k: v[:min_len] for k, v in pred_dict.items()},
                metrics=metrics_dict,
                output=str(OUTPUT / "pueea_forecast.html"),
                title="Pronóstico de Consumo de Agua — PUEEA Colombia",
                variable_name="Consumo",
                unit="m³/mes",
            )
            logger.info("forecast_report guardado: pueea_forecast.html")

        resultados["forecast_12m_mean"] = round(float(forecast_vals.mean()), 0)
        resultados["forecast_12m_min"]  = round(float(forecast_vals.min()), 0)
        resultados["forecast_12m_max"]  = round(float(forecast_vals.max()), 0)

    except Exception as exc:
        logger.warning("Pronóstico/forecast_report skipped: %s", exc)

    return resultados


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — PUEEA | Consumo mensual de agua | 2010-2025")
    logger.info("Estación: %s", ESTACION)
    logger.info("=" * 65)

    # 1. Datos — auto-detectar real, sintético como fallback
    parquet_real = RAW / "consumo_agua_real.parquet"
    csv_real     = RAW / "consumo_agua_real.csv"
    if parquet_real.exists():
        logger.info("Cargando datos reales: %s", parquet_real.name)
        df_raw = pd.read_parquet(parquet_real)
    elif csv_real.exists():
        logger.info("Cargando datos reales: %s", csv_real.name)
        df_raw = pd.read_csv(csv_real, parse_dates=["fecha"])
    else:
        logger.info("Sin datos reales — generando sintéticos (2010-2025)")
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

    # 4. ENSO
    try:
        aplicar_enso(df_raw)
    except Exception as exc:
        logger.warning("ENSO falló: %s", exc)

    # 5. Descriptiva
    try:
        descriptiva(serie, df_raw)
    except Exception as exc:
        logger.warning("Descriptiva falló: %s", exc)

    # 6. Análisis de eficiencia (meta 15% IDEAM)
    try:
        analisis_eficiencia(serie)
    except Exception as exc:
        logger.warning("Análisis de eficiencia falló: %s", exc)

    # 7. Inferencial
    inf: dict = {}
    try:
        inf = inferencial(serie)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)

    # 8. Predictiva
    pred: dict = {}
    try:
        pred = predictiva(serie)
    except Exception as exc:
        logger.error("Predictiva falló: %s", exc)

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — PUEEA")
    logger.info("  Período: %s → %s",
                serie.index.min().date(), serie.index.max().date())
    logger.info("  Consumo medio: %.0f m³/mes | CV: %.2f",
                eda_res.get("media_m3mes", float("nan")),
                eda_res.get("cv", float("nan")))
    logger.info("  Outliers (IQR): %d meses", eda_res.get("n_outliers_iqr", 0))
    logger.info("  Participación doméstico: %.1f%% | industrial: %.1f%%",
                eda_res.get("dom_pct", float("nan")), eda_res.get("ind_pct", float("nan")))

    mk = inf.get("mann_kendall", {})
    if mk:
        logger.info("  Mann-Kendall: %s (p=%.4f) | %.0f m³/año",
                    mk.get("tendencia"), mk.get("p_value"), mk.get("sen_slope_anual_m3"))

    sarima = pred.get("sarima_metrics", {})
    ets    = pred.get("ets_metrics", {})
    if sarima:
        logger.info("  SARIMA → RMSE=%.0f | MAE=%.0f | sMAPE=%.2f%%",
                    sarima.get("rmse", float("nan")), sarima.get("mae", float("nan")),
                    sarima.get("smape", float("nan")))
    if ets:
        logger.info("  ETS    → RMSE=%.0f | MAE=%.0f | sMAPE=%.2f%%",
                    ets.get("rmse", float("nan")), ets.get("mae", float("nan")),
                    ets.get("smape", float("nan")))
    logger.info("  Mejor modelo: %s", pred.get("mejor_modelo", "N/A"))
    logger.info("  Pronóstico 12m: media=%.0f m³/mes",
                pred.get("forecast_12m_mean", float("nan")))
    logger.info("  Salidas: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 PUEEA completada.")


if __name__ == "__main__":
    main()
