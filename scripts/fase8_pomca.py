"""
Fase 8 — Ciclo estadístico completo: POMCA (Plan de Ordenación y Manejo de Cuencas).

Línea temática: POMCA
Variable objetivo: caudal diario (m³/s) en cuenca hidrográfica andina colombiana
Frecuencia: diaria, 2000-2025 (sintética si no hay real en data/raw/caudal_cuenca_real.parquet)
Normas: IUA_THRESHOLDS (IDEAM/ENA), IRH_THRESHOLDS (IDEAM/ENA)
Métricas primarias: NSE y KGE (dominio hydrology — ADR-003)

Flujo:
  1. Generación/carga de datos (caudal diario bimodal andino, AR(1) ρ=0.9)
  2. Validación (validate, linea_tematica='pomca')
  3. EDA (calidad, gaps, distribución)
  4. ENSO con lag=4 meses (pomca ↔ oferta_hidrica — config.ENSO_LAG_MESES)
  5. Descriptiva anual/mensual + IUA mensual
  6. Inferencial: ADF/KPSS, Mann-Kendall de caudal
  7. Predictiva: SARIMAXModel + ETSModel — walk_forward(domain='hydrology')
     rank_models(domain='hydrology')
  8. Reportes: forecast_report (caudal) + compliance_report (IUA con umbral moderado)

Salidas en data/output/reports/:
  - pomca_forecast.html
  - pomca_cumplimiento_iua.html
  - pomca_descriptiva.csv
  - pomca_inferencial.json
  - pomca_ranking.csv

Uso:
    python scripts/fase8_pomca.py
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
logger = logging.getLogger("fase8_pomca")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT    = Path(__file__).parent.parent
RAW     = ROOT / "data" / "raw"
OUTPUT  = ROOT / "data" / "output" / "reports"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "pomca"
VARIABLE = "caudal"
ESTACION = "Cuenca_Hidrografica_Andina_POMCA_sintetica"

# Demanda hídrica mensual estimada (m³/s) para IUA orientativo.
# Representa usos doméstico + agrícola + industrial típico de cuenca media andina.
DEMANDA_M3S = 32.0


# ===========================================================================
# 1. DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_sinteticos(
    start: str = "2000-01-01",
    end: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """Genera caudal diario sintético realista para cuenca andina colombiana.

    Modelo estocástico:
    - Base: media 80 m³/s (cuenca andina media), escala log-normal σ=0.55
    - Estacionalidad bimodal andina: picos en abril y octubre (régimen bimodal)
    - Autocorrelación AR(1) ρ=0.9 — caudales son muy persistentes
    - Eventos de estiaje severo: 3 episodios El Niño en el período (reducción >60%)
    - Tendencia decreciente suave (-0.4 m³/s/año) como señal de cambio climático

    El AR(1) con ρ=0.9 captura la memoria hidrológica: en cuencas andinas
    los caudales de mañana dependen fuertemente de los de hoy (almacenamiento
    en suelo y acuíferos).
    """
    rng = np.random.default_rng(seed)
    fechas = pd.date_range(start, end, freq="D")
    n = len(fechas)
    t = np.arange(n)

    # Estacionalidad bimodal andina (dos picos lluviosos: mar-may y sep-nov)
    seasonal = (
        35.0 * np.sin(2 * np.pi * (t - 75) / 365.25)    # pico ~abril
        + 20.0 * np.sin(4 * np.pi * (t - 60) / 365.25)  # segundo pico ~oct
        + 8.0 * np.cos(6 * np.pi * t / 365.25)           # tercer armónico
    )

    # Tendencia lineal descendente (presión sobre la cuenca)
    n_years = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    trend = np.linspace(0, -0.4 * n_years, n)

    # AR(1) ρ=0.9 en escala gaussiana
    ruido = np.zeros(n)
    ruido[0] = rng.standard_normal()
    rho = 0.9
    for i in range(1, n):
        ruido[i] = rho * ruido[i - 1] + rng.standard_normal() * np.sqrt(1 - rho**2)

    # Base log-normal con media 80 m³/s
    mu_log = np.log(80) - 0.55**2 / 2
    base = np.exp(mu_log + 0.55 * ruido)

    caudal = base + seasonal + trend

    # Eventos de estiaje severo (El Niño fuerte): 2002, 2010, 2016
    # En Colombia, El Niño reduce la precipitación Andina en 40-70%
    for yr_inicio, duracion_dias in [(2002, 180), (2010, 210), (2016, 150)]:
        idx_ini = (pd.Timestamp(f"{yr_inicio}-06-01") - pd.Timestamp(start)).days
        idx_fin = min(idx_ini + duracion_dias, n)
        if 0 <= idx_ini < n:
            caudal[idx_ini:idx_fin] *= rng.uniform(0.25, 0.42,
                                                    size=idx_fin - idx_ini)

    # Garantizar positivo (caudal mínimo ecológico ≥ 0.5 m³/s)
    caudal = np.clip(caudal, 0.5, 50_000.0)

    df = pd.DataFrame({
        "fecha":   fechas,
        "caudal":  np.round(caudal, 2),
        "estacion": ESTACION,
    })

    # Simular ~2.5% datos faltantes (mantenimiento limnímetro, crecientes)
    idx_na = rng.choice(n, size=int(n * 0.025), replace=False)
    df.loc[idx_na, "caudal"] = np.nan

    out = RAW / "pomca_sintetica.csv"
    df.to_csv(out, index=False)
    logger.info("Datos sintéticos POMCA: %d días | guardados en %s", n, out.name)
    return df


# ===========================================================================
# 2. CARGA Y VALIDACIÓN
# ===========================================================================

def cargar_y_validar(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Valida rangos físicos y devuelve serie limpia de caudal."""
    logger.info("--- Validación POMCA ---")
    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df_raw, date_col="fecha", linea_tematica=LINEA)
        logger.info("Validación: issues=%s", report.has_issues())
        if report.range_violations:
            logger.warning("Violaciones de rango: %s", list(report.range_violations.keys()))
        for col, pct in report.missing.items():
            if pct > 0:
                logger.info("  Faltantes '%s': %.1f%%", col, pct)
    except Exception as exc:
        logger.warning("Validación skipped: %s", exc)

    serie = (
        df_raw.set_index("fecha")["caudal"]
        .sort_index()
        .astype(float)
    )
    n_antes = len(serie)
    serie = serie.dropna()
    logger.info(
        "Serie caudal: %d días (%.1f%% válidos) | %s → %s",
        len(serie), len(serie) / n_antes * 100,
        serie.index.min().date(), serie.index.max().date(),
    )
    return df_raw, serie


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(serie: pd.Series) -> dict:
    """EDA: estadísticas de caudal, distribución, gaps y calidad."""
    logger.info("--- EDA POMCA ---")

    stats = serie.describe()
    cv = stats["std"] / stats["mean"] if stats["mean"] > 0 else float("nan")

    # Distribución empírica — percentiles hidrológicos estándar
    pcts = {f"p{int(q*100)}": float(serie.quantile(q))
            for q in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)}

    # Completitud temporal
    idx_completo = pd.date_range(serie.index.min(), serie.index.max(), freq="D")
    n_gaps = len(idx_completo) - len(serie)

    # Estacionalidad mensual
    mensual = serie.resample("ME").mean()
    mes_humedo = mensual.groupby(mensual.index.month).mean().idxmax()
    mes_seco   = mensual.groupby(mensual.index.month).mean().idxmin()

    # Años de estiaje severo (p10 < 30% de la media)
    umbral_estiaje = float(stats["mean"]) * 0.30
    anual_min = serie.resample("YE").min()
    anios_estiaje = int((anual_min < umbral_estiaje).sum())

    logger.info("Caudal — media: %.1f m³/s | mediana: %.1f | max: %.1f | CV: %.2f",
                stats["mean"], stats["50%"], stats["max"], cv)
    logger.info("Percentiles: p10=%.1f | p50=%.1f | p90=%.1f m³/s",
                pcts["p10"], pcts["p50"], pcts["p90"])
    logger.info("Mes húmedo: %02d | Mes seco: %02d | Años estiaje severo: %d",
                mes_humedo, mes_seco, anios_estiaje)
    logger.info("Gaps diarios: %d (%.1f%%)", n_gaps, n_gaps / len(idx_completo) * 100)

    return {
        "n_dias": len(serie),
        "media_m3s": round(float(stats["mean"]), 2),
        "mediana_m3s": round(float(stats["50%"]), 2),
        "max_m3s": round(float(stats["max"]), 2),
        "std_m3s": round(float(stats["std"]), 2),
        "cv": round(float(cv), 3),
        **{k: round(v, 2) for k, v in pcts.items()},
        "mes_humedo": int(mes_humedo),
        "mes_seco": int(mes_seco),
        "anios_estiaje_severo": anios_estiaje,
        "n_gaps_diarios": n_gaps,
    }


# ===========================================================================
# 4. ENSO CON LAG
# ===========================================================================

def aplicar_enso(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica covariable ENSO con lag=4 meses (línea pomca — equivale a oferta_hidrica)."""
    logger.info("--- ENSO con lag (pomca) ---")
    try:
        from estadistica_ambiental.features.climate import enso_lagged, load_oni
        from estadistica_ambiental.config import ENSO_LAG_MESES
        oni = load_oni()
        if oni.empty:
            logger.warning("ONI vacío (sin red) — continuando sin ENSO")
            return df_raw
        df_enso = enso_lagged(df_raw, oni, date_col="fecha", linea_tematica=LINEA)
        lag = ENSO_LAG_MESES.get(LINEA, 4)
        oni_col = f"oni_lag{lag}"
        if oni_col in df_enso.columns:
            fase_col = f"fase_lag{lag}"
            fases = df_enso[fase_col].value_counts().to_dict() if fase_col in df_enso.columns else {}
            logger.info("ENSO lag=%d meses | fases: %s", lag, fases)
        return df_enso
    except Exception as exc:
        logger.warning("ENSO skipped: %s", exc)
        return df_raw


# ===========================================================================
# 5. DESCRIPTIVA
# ===========================================================================

def descriptiva(serie: pd.Series) -> pd.DataFrame:
    """Resúmenes anuales de caudal + IUA mensual."""
    logger.info("--- Descriptiva POMCA ---")

    df = serie.to_frame("caudal")
    df["anio"] = df.index.year
    df["mes"]  = df.index.month

    # Resumen anual con percentiles hidrológicos
    anual = df.groupby("anio")["caudal"].agg(
        n="count",
        media="mean",
        mediana="median",
        std="std",
        min="min",
        max="max",
        p10=lambda x: x.quantile(0.10),
        p90=lambda x: x.quantile(0.90),
    ).round(2)

    logger.info("Resumen anual (últimos 5 años):")
    for anio, row in anual.tail(5).iterrows():
        logger.info("  %d: media=%.1f m³/s | p10=%.1f | p90=%.1f | n=%d",
                    anio, row["media"], row["p10"], row["p90"], int(row["n"]))

    out = OUTPUT / "pomca_descriptiva.csv"
    anual.to_csv(out)
    logger.info("Descriptiva guardada: %s", out.name)
    return anual


def calcular_iua_mensual(serie: pd.Series) -> pd.Series:
    """IUA mensual = (Demanda estimada / Oferta mensual media) × 100.

    Oferta mensual = caudal medio mensual (m³/s).
    DEMANDA_M3S es constante anual — simplificación orientativa.
    En un POMCA real se usarían datos de concesiones y demanda sectorial.
    """
    from estadistica_ambiental.config import IUA_THRESHOLDS

    oferta_m = serie.resample("ME").mean().dropna()
    # IUA como % — evitar división por cero con máscara
    iua_m = (DEMANDA_M3S / oferta_m.replace(0, np.nan)) * 100.0
    iua_m.name = "iua"

    # Clasificar cada mes
    def categorizar(v: float) -> str:
        if v <= IUA_THRESHOLDS["bajo"]:
            return "bajo"
        if v <= IUA_THRESHOLDS["moderado"]:
            return "moderado"
        if v <= IUA_THRESHOLDS["alto"]:
            return "alto"
        return "critico"

    cat = iua_m.apply(categorizar)
    logger.info("IUA mensual — media: %.1f%% | máx: %.1f%% | meses críticos: %d",
                iua_m.mean(), iua_m.max(), int((cat == "critico").sum()))
    return iua_m


# ===========================================================================
# 6. INFERENCIAL
# ===========================================================================

def inferencial(serie: pd.Series) -> dict:
    """ADF + KPSS (ADR-004) + Mann-Kendall de caudal mensual."""
    logger.info("--- Inferencial POMCA ---")
    resultados: dict = {}

    serie_m = serie.resample("ME").mean().dropna()

    # 6.1 ADF + KPSS — obligatorios antes de ARIMA (ADR-004)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf  = adf_test(serie_m)
        kpss_r = kpss_test(serie_m)
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

    # 6.2 Mann-Kendall — tendencia en caudal anual
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        serie_a = serie.resample("YE").mean().dropna()
        mk = mann_kendall(serie_a)
        slope_d = sens_slope(serie_a)
        slope_anual = slope_d.get("slope", mk.get("slope", 0.0))
        resultados["mann_kendall"] = {
            "tendencia": mk.get("trend", "unknown"),
            "p_value": round(float(mk.get("pval", 1.0)), 4),
            "significativo": mk.get("pval", 1.0) < 0.05,
            "sen_slope_anual_m3s": round(float(slope_anual), 4),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall caudal: %s (p=%.4f) | Sen slope=%.3f m³/s/año",
                    mk_r["tendencia"], mk_r["p_value"], mk_r["sen_slope_anual_m3s"])
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # Guardar
    out = OUTPUT / "pomca_inferencial.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out.name)
    return resultados


# ===========================================================================
# 7. PREDICTIVA
# ===========================================================================

def predictiva(serie: pd.Series) -> dict:
    """SARIMAX(1,1,1)(1,1,1,12) + ETS — walk-forward domain='hydrology'.

    Usamos serie mensual porque la diaria (9000+ observaciones) hace que
    SARIMA sea computacionalmente costoso sin ganancia en NSE/KGE para POMCA.
    ETS (Holt-Winters aditivo) es un segundo modelo robusto no-lineal para ranking.
    """
    logger.info("--- Predictiva POMCA (dominio: hidrología) ---")

    serie_m = serie.resample("ME").mean().dropna()
    logger.info("Serie mensual: %d meses (%s → %s)",
                len(serie_m), serie_m.index.min().date(), serie_m.index.max().date())

    resultados: dict = {}
    bt_results: dict = {}

    # 7.1 SARIMAX(1,1,1)(1,1,1,12)
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_sarima = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        logger.info("Entrenando SARIMAX(1,1,1)(1,1,1,12)...")
        res = walk_forward(model_sarima, serie_m, horizon=3, n_splits=5,
                           domain="hydrology")
        bt_results["SARIMAX(1,1,1)(1,1,1,12)"] = res
        m = res["metrics"]
        resultados["sarima_metrics"] = m
        logger.info("SARIMAX → NSE=%.4f | KGE=%.4f | RMSE=%.2f | PBIAS=%.2f%%",
                    m.get("nse", float("nan")), m.get("kge", float("nan")),
                    m.get("rmse", float("nan")), m.get("pbias", float("nan")))
    except Exception as exc:
        logger.error("SARIMAX falló: %s", exc)

    # 7.2 ETS (Holt-Winters aditivo) — benchmark alternativo
    try:
        from estadistica_ambiental.predictive.classical import ETSModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_ets = ETSModel(trend="add", seasonal="add", seasonal_periods=12)
        logger.info("Entrenando ETS (Holt-Winters aditivo)...")
        res = walk_forward(model_ets, serie_m, horizon=3, n_splits=5,
                           domain="hydrology")
        bt_results["ETS_HoltWinters"] = res
        m = res["metrics"]
        resultados["ets_metrics"] = m
        logger.info("ETS → NSE=%.4f | KGE=%.4f | RMSE=%.2f | PBIAS=%.2f%%",
                    m.get("nse", float("nan")), m.get("kge", float("nan")),
                    m.get("rmse", float("nan")), m.get("pbias", float("nan")))
    except Exception as exc:
        logger.warning("ETS skipped: %s", exc)

    # 7.3 Ranking multi-criterio (NSE + KGE + RMSE + PBIAS)
    if len(bt_results) >= 2:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models
            ranking = rank_models(bt_results, domain="hydrology")
            rank_path = OUTPUT / "pomca_ranking.csv"
            ranking.to_csv(rank_path)
            logger.info("Ranking modelos POMCA (hydrology):")
            for idx, row in ranking.iterrows():
                logger.info("  Rank %d: %s | NSE=%.4f | KGE=%.4f | score=%.4f",
                            int(row.get("rank", 0)), idx,
                            row.get("nse", float("nan")),
                            row.get("kge", float("nan")),
                            row.get("score", float("nan")))
            resultados["mejor_modelo"] = str(ranking.index[0])
            logger.info("Ranking guardado: %s", rank_path.name)
        except Exception as exc:
            logger.warning("rank_models skipped: %s", exc)
    else:
        logger.warning("Menos de 2 modelos entrenados — ranking omitido")

    # 7.4 Guardar métricas por fold
    bt_fold_path = OUTPUT / "pomca_backtesting.csv"
    first_write = True
    for nombre, res in bt_results.items():
        folds_df = res.get("folds", pd.DataFrame())
        if not folds_df.empty:
            folds_df = folds_df.copy()
            folds_df["modelo"] = nombre
            folds_df.to_csv(bt_fold_path, mode="a", header=first_write, index=False)
            first_write = False

    # 7.5 Pronóstico 12 meses con SARIMAX (mejor modelo baseline)
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        model_fc = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model_fc.fit(serie_m)
        forecast_vals = np.clip(model_fc.predict(12), 0.5, 50_000.0)
        forecast_idx = pd.date_range(
            start=serie_m.index.max() + pd.DateOffset(months=1),
            periods=12, freq="ME",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="caudal_forecast")
        logger.info("Pronóstico 12 meses: media=%.1f | min=%.1f | max=%.1f m³/s",
                    forecast.mean(), forecast.min(), forecast.max())

        # Construir predicciones del período de test para el HTML
        pred_dict: dict = {}
        for nombre, res in bt_results.items():
            preds_df = res.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                pred_dict[nombre] = preds_df["predicted"].values

        metrics_dict = {n: r.get("metrics", {}) for n, r in bt_results.items()}

        if pred_dict:
            min_len = min(len(v) for v in pred_dict.values())
            actual_vals = bt_results[list(bt_results.keys())[0]]["predictions"]["actual"].values
            y_test_ref = pd.Series(actual_vals[:min_len], name="caudal_obs")

            forecast_report(
                y_true=y_test_ref,
                predictions={k: v[:min_len] for k, v in pred_dict.items()},
                metrics=metrics_dict,
                output=str(OUTPUT / "pomca_forecast.html"),
                title="Pronóstico de Caudal — POMCA Colombia",
                variable_name="Caudal",
                unit="m³/s",
            )
            logger.info("forecast_report guardado: pomca_forecast.html")

        resultados["forecast_12m_mean"] = round(float(forecast.mean()), 2)
        resultados["forecast_12m_min"]  = round(float(forecast.min()), 2)
        resultados["forecast_12m_max"]  = round(float(forecast.max()), 2)

    except Exception as exc:
        logger.warning("Pronóstico/forecast_report skipped: %s", exc)

    return resultados


# ===========================================================================
# 8. REPORTE DE CUMPLIMIENTO (IUA)
# ===========================================================================

def reporte_cumplimiento(serie: pd.Series) -> None:
    """Reporte HTML de cumplimiento normativo del IUA (IDEAM/ENA).

    compliance_report no tiene norma estándar para IUA en _NORMA_MAP,
    por eso usamos custom_thresholds para el umbral moderado (50%).
    """
    logger.info("--- Reporte cumplimiento IUA (POMCA) ---")
    try:
        from estadistica_ambiental.reporting.compliance_report import compliance_report
        from estadistica_ambiental.config import IUA_THRESHOLDS

        iua_m = calcular_iua_mensual(serie)
        df_rep = pd.DataFrame({
            "fecha": iua_m.index,
            "iua": iua_m.values,
        }).reset_index(drop=True)

        compliance_report(
            df_rep,
            variables=["iua"],
            date_col="fecha",
            linea_tematica=LINEA,
            output=str(OUTPUT / "pomca_cumplimiento_iua.html"),
            title="Índice de Uso del Agua (IUA) — POMCA",
            # Umbral moderado IDEAM como referencia normativa (Res. 872/2006)
            custom_thresholds={"iua": IUA_THRESHOLDS["moderado"]},
        )
        logger.info("compliance_report guardado: pomca_cumplimiento_iua.html")
    except Exception as exc:
        logger.warning("compliance_report skipped: %s", exc)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — POMCA | Caudal diario bimodal andino | 2000-2025")
    logger.info("Estación: %s", ESTACION)
    logger.info("=" * 65)

    # 1. Datos — auto-detectar real, sintético como fallback
    parquet_real = RAW / "caudal_cuenca_real.parquet"
    csv_real     = RAW / "caudal_cuenca_real.csv"
    if parquet_real.exists():
        logger.info("Cargando datos reales: %s", parquet_real.name)
        df_raw = pd.read_parquet(parquet_real)
    elif csv_real.exists():
        logger.info("Cargando datos reales: %s", csv_real.name)
        df_raw = pd.read_csv(csv_real, parse_dates=["fecha"])
    else:
        logger.info("Sin datos reales — generando sintéticos (2000-2025)")
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
        eda_res = eda(serie)
    except Exception as exc:
        logger.warning("EDA falló: %s", exc)

    # 4. ENSO con lag
    try:
        aplicar_enso(df_raw)
    except Exception as exc:
        logger.warning("ENSO falló: %s", exc)

    # 5. Descriptiva
    try:
        descriptiva(serie)
    except Exception as exc:
        logger.warning("Descriptiva falló: %s", exc)

    # 6. Inferencial
    inf: dict = {}
    try:
        inf = inferencial(serie)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)

    # 7. Predictiva
    pred: dict = {}
    try:
        pred = predictiva(serie)
    except Exception as exc:
        logger.error("Predictiva falló: %s", exc)

    # 8. Reporte cumplimiento IUA
    try:
        reporte_cumplimiento(serie)
    except Exception as exc:
        logger.warning("Reporte IUA falló: %s", exc)

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — POMCA")
    logger.info("  Período: %s → %s",
                serie.index.min().date(), serie.index.max().date())
    logger.info("  Caudal medio: %.2f m³/s | CV: %.2f",
                eda_res.get("media_m3s", float("nan")), eda_res.get("cv", float("nan")))
    logger.info("  Años estiaje severo: %d", eda_res.get("anios_estiaje_severo", 0))

    mk = inf.get("mann_kendall", {})
    if mk:
        logger.info("  Mann-Kendall: %s (p=%.4f) | %.3f m³/s/año",
                    mk.get("tendencia"), mk.get("p_value"), mk.get("sen_slope_anual_m3s"))

    sarima = pred.get("sarima_metrics", {})
    ets    = pred.get("ets_metrics", {})
    if sarima:
        logger.info("  SARIMAX → NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s",
                    sarima.get("nse", float("nan")), sarima.get("kge", float("nan")),
                    sarima.get("rmse", float("nan")))
    if ets:
        logger.info("  ETS     → NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s",
                    ets.get("nse", float("nan")), ets.get("kge", float("nan")),
                    ets.get("rmse", float("nan")))
    logger.info("  Mejor modelo: %s", pred.get("mejor_modelo", "N/A"))
    logger.info("  Pronóstico 12m: media=%.1f m³/s",
                pred.get("forecast_12m_mean", float("nan")))
    logger.info("  Salidas: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 POMCA completada.")


if __name__ == "__main__":
    main()
