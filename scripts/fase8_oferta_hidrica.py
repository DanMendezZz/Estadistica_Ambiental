"""
Fase 8 — Ciclo estadístico completo: Oferta Hídrica.

Línea temática: Oferta Hídrica (caudal superficial, índice IUA)
Variable objetivo: caudal (m³/s)
Frecuencia: diaria, 10 años sintéticos (log-normal + estacionalidad anual)
Normas: IUA_THRESHOLDS (IDEAM/ENA), métricas primarias NSE y KGE

Flujo:
  1. Generación de datos sintéticos realistas (caudal diario)
  2. Carga y validación (validate, linea_tematica='oferta_hidrica')
  3. EDA (estadísticas, gaps, distribución log-normal)
  4. ENSO con lag (enso_lagged, lag=4 meses — cuencas Magdalena-Cauca)
  5. Inferencial: Mann-Kendall, ADF/KPSS, cálculo IUA orientativo
  6. Predictiva: SARIMAXModel + XGBoostModel
     walk_forward(domain='hydrology'), rank_models(domain='hydrology')
  7. Reporte: compliance_report (IUA) + forecast_report (caudal)

Uso:
    python scripts/fase8_oferta_hidrica.py

Salidas en data/output/fase8/:
    - datos_sinteticos_oferta_hidrica.csv
    - descriptiva_oferta_hidrica.csv
    - inferencial_oferta_hidrica.json
    - backtesting_oferta_hidrica.csv
    - ranking_modelos_oferta_hidrica.csv
    - forecast_oferta_hidrica.html
    - cumplimiento_iua_oferta_hidrica.html
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
logger = logging.getLogger("fase8_oferta_hidrica")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
RAW    = DATA / "raw"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "oferta_hidrica"
VARIABLE = "caudal"
ESTACION = "Rio_Magdalena_Girardot_sintetica"

# Demanda hídrica anual sintética (m³/s) para calcular IUA orientativo
DEMANDA_ANUAL_M3S = 120.0


# ===========================================================================
# 1. DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_sinteticos(
    start: str = "2014-01-01",
    end: str = "2023-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """Genera serie diaria de caudal (m³/s) realista para Colombia.

    Modelo: log-normal con estacionalidad anual bimodal (ríos Andinos Colombia).
    Media base ~350 m³/s (río tipo cuenca media Magdalena), sigma log-normal = 0.6.
    Estacionalidad bimodal (picos en abril-mayo y octubre-noviembre).
    Tendencia decreciente suave (-0.5 m³/s/año) por cambio climático.
    Ruido diario con autocorrelación AR(1) ρ=0.85.
    """
    rng = np.random.default_rng(seed)
    fechas = pd.date_range(start, end, freq="D")
    n = len(fechas)

    # Tendencia lineal
    trend = np.linspace(0, -0.5 * 10, n)  # -0.5 m³/s/año × 10 años

    # Estacionalidad anual bimodal (régimen hidrológico Andino colombiano)
    t = np.arange(n)
    seasonal = (
        60.0 * np.sin(2 * np.pi * (t - 90) / 365.25)   # pico ~abril
        + 40.0 * np.sin(4 * np.pi * (t - 60) / 365.25)  # segundo pico ~octubre
        + 20.0 * np.cos(6 * np.pi * t / 365.25)          # tercer armónico
    )

    # Ruido AR(1) con escala log-normal
    ruido_gauss = np.zeros(n)
    ruido_gauss[0] = rng.standard_normal()
    for i in range(1, n):
        ruido_gauss[i] = 0.85 * ruido_gauss[i - 1] + rng.standard_normal() * np.sqrt(1 - 0.85**2)

    # Base log-normal: media 350 m³/s, σ = 0.6 en escala log
    mu_log = np.log(350) - 0.6**2 / 2
    base = np.exp(mu_log + 0.6 * ruido_gauss)

    # Combinar
    caudal = base + seasonal + trend
    # Garantizar valores físicamente posibles (≥ 0.5 m³/s caudal mínimo ecológico)
    caudal = np.clip(caudal, 0.5, 50000.0)

    df = pd.DataFrame({
        "fecha":   fechas,
        "caudal":  np.round(caudal, 2),
        "estacion": ESTACION,
    })

    # Introducir ~3% datos faltantes (mantenimiento sensor, episodios de creciente)
    idx_na = rng.choice(n, size=int(n * 0.03), replace=False)
    df.loc[idx_na, "caudal"] = np.nan

    out = RAW / "oferta_hidrica_sintetica.csv"
    df.to_csv(out, index=False)
    logger.info("Datos sintéticos generados: %d días | guardados en %s", n, out.name)
    return df


# ===========================================================================
# 2. CARGA Y VALIDACIÓN
# ===========================================================================

def cargar_y_validar(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Valida rangos y devuelve serie limpia de caudal."""
    logger.info("--- Carga y validación ---")

    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df_raw, date_col="fecha", linea_tematica=LINEA)
        logger.info("Validación completada. Issues: %s", report.has_issues())
        if report.range_violations:
            logger.warning("Violaciones de rango: %s", list(report.range_violations.keys()))
        if report.missing:
            for col, pct in report.missing.items():
                logger.info("  Faltantes '%s': %.1f%%", col, pct)
    except Exception as e:
        logger.warning("Validación skipped: %s", e)

    # Serie temporal indexada
    serie = (
        df_raw.set_index("fecha")["caudal"]
        .sort_index()
        .astype(float)
    )
    n_antes = len(serie)
    serie = serie.dropna()
    logger.info("Serie caudal: %d días (%.1f%% válidos) | %s → %s",
                len(serie),
                len(serie) / n_antes * 100,
                serie.index.min().date(),
                serie.index.max().date())
    return df_raw, serie


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(serie: pd.Series) -> dict:
    """EDA: estadísticas, gaps, distribución log-normal."""
    logger.info("--- EDA Oferta Hídrica ---")

    stats = serie.describe()
    idx_completo = pd.date_range(serie.index.min(), serie.index.max(), freq="D")
    n_gaps = len(idx_completo) - len(serie)

    # Distribución empírica
    p10, p25, p50, p75, p90 = (
        serie.quantile(q) for q in (0.1, 0.25, 0.5, 0.75, 0.9)
    )
    cv = stats["std"] / stats["mean"] if stats["mean"] > 0 else float("nan")

    # Estacionalidad mensual
    mensual = serie.resample("ME").mean()
    mes_max = mensual.groupby(mensual.index.month).mean().idxmax()
    mes_min = mensual.groupby(mensual.index.month).mean().idxmin()

    logger.info("Caudal medio: %.1f m³/s | mediana: %.1f | σ: %.1f | CV: %.2f",
                stats["mean"], stats["50%"], stats["std"], cv)
    logger.info("Percentiles: p10=%.1f | p25=%.1f | p75=%.1f | p90=%.1f | máx=%.1f",
                p10, p25, p75, p90, stats["max"])
    logger.info("Estacionalidad: mes húmedo=%02d | mes seco=%02d", mes_max, mes_min)
    logger.info("Gaps en serie diaria: %d días (%.1f%%)",
                n_gaps, n_gaps / len(idx_completo) * 100)

    return {
        "n_dias": len(serie),
        "media_m3s": round(float(stats["mean"]), 2),
        "mediana_m3s": round(float(stats["50%"]), 2),
        "std_m3s": round(float(stats["std"]), 2),
        "cv": round(float(cv), 3),
        "p10": round(float(p10), 2),
        "p90": round(float(p90), 2),
        "max_m3s": round(float(stats["max"]), 2),
        "n_gaps_diarios": n_gaps,
        "mes_max_caudal": int(mes_max),
        "mes_min_caudal": int(mes_min),
    }


# ===========================================================================
# 4. ENSO CON LAG
# ===========================================================================

def aplicar_enso(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica ENSO con lag=4 meses para oferta hídrica."""
    logger.info("--- ENSO con lag (oferta_hidrica) ---")
    try:
        from estadistica_ambiental.features.climate import enso_lagged, load_oni
        oni = load_oni()
        if oni.empty:
            logger.warning("ONI vacío (red no disponible) — se continúa sin ENSO")
            return df_raw
        df_enso = enso_lagged(df_raw, oni, date_col="fecha", linea_tematica=LINEA)
        from estadistica_ambiental.config import ENSO_LAG_MESES
        lag = ENSO_LAG_MESES.get(LINEA, 4)
        lag_col = f"oni_lag{lag}"
        if lag_col in df_enso.columns:
            oni_vals = df_enso[lag_col].dropna()
            logger.info("ONI lag=%d | registros con ONI: %d | media ONI: %.3f",
                        lag, len(oni_vals), oni_vals.mean())
            fase_col = f"fase_lag{lag}"
            if fase_col in df_enso.columns:
                fases = df_enso[fase_col].value_counts()
                logger.info("Distribución fases ENSO: %s", fases.to_dict())
        return df_enso
    except Exception as e:
        logger.warning("ENSO skipped: %s", e)
        return df_raw


# ===========================================================================
# 5. ESTADÍSTICA DESCRIPTIVA
# ===========================================================================

def descriptiva(serie: pd.Series) -> pd.DataFrame:
    """Resúmenes anuales y mensuales de caudal."""
    logger.info("--- Descriptiva ---")
    df = serie.to_frame("caudal")
    df["anio"] = df.index.year
    df["mes"]  = df.index.month

    # Resumen anual
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

    out = OUTPUT / "descriptiva_oferta_hidrica.csv"
    anual.to_csv(out)
    logger.info("Resumen anual guardado: %s", out.name)
    return anual


# ===========================================================================
# 6. ESTADÍSTICA INFERENCIAL
# ===========================================================================

def calcular_iua(serie_caudal: pd.Series, demanda_m3s: float = DEMANDA_ANUAL_M3S) -> dict:
    """Calcula el Índice de Uso del Agua (IUA) orientativo anual.

    IUA = (Demanda / Oferta) × 100
    Oferta anual = caudal medio anual × s/año.
    Umbrales IDEAM: bajo <20%, moderado 20-50%, alto 50-100%, crítico >100%.
    """
    from estadistica_ambiental.config import IUA_THRESHOLDS
    oferta_anual_m3s = float(serie_caudal.mean())
    iua = (demanda_m3s / oferta_anual_m3s) * 100 if oferta_anual_m3s > 0 else float("nan")

    if iua <= IUA_THRESHOLDS["bajo"]:
        categoria = "bajo"
    elif iua <= IUA_THRESHOLDS["moderado"]:
        categoria = "moderado"
    elif iua <= IUA_THRESHOLDS["alto"]:
        categoria = "alto"
    else:
        categoria = "critico"

    logger.info("IUA orientativo: %.1f%% → categoría: %s (demanda=%.1f m³/s, oferta media=%.1f m³/s)",
                iua, categoria, demanda_m3s, oferta_anual_m3s)
    return {
        "iua_pct": round(iua, 2),
        "categoria_iua": categoria,
        "oferta_media_m3s": round(oferta_anual_m3s, 2),
        "demanda_m3s": demanda_m3s,
    }


def inferencial(serie: pd.Series) -> dict:
    """Mann-Kendall, ADF/KPSS, IUA."""
    logger.info("--- Inferencial ---")
    resultados: dict = {}

    # 6.1 IUA
    try:
        resultados["iua"] = calcular_iua(serie)
    except Exception as e:
        logger.warning("IUA skipped: %s", e)

    # 6.2 Mann-Kendall (usar serie mensual — más eficiente que diaria)
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        serie_mensual = serie.resample("ME").mean().dropna()
        mk = mann_kendall(serie_mensual)
        slope_dict = sens_slope(serie_mensual)
        slope_mensual = slope_dict.get("slope", mk.get("slope", 0.0))
        resultados["mann_kendall"] = {
            "tendencia": mk.get("trend", "unknown"),
            "p_value": round(float(mk.get("pval", 1.0)), 4),
            "significativo": mk.get("pval", 1.0) < 0.05,
            "sen_slope_anual_m3s": round(float(slope_mensual * 12), 4),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall: tendencia=%s | p=%.4f | Sen slope=%.3f m³/s/año",
                    mk_r["tendencia"], mk_r["p_value"], mk_r["sen_slope_anual_m3s"])
    except Exception as e:
        logger.warning("Mann-Kendall skipped: %s", e)

    # 6.3 ADF + KPSS (serie mensual — ADR-004)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        serie_mensual = serie.resample("ME").mean().dropna()
        adf = adf_test(serie_mensual)
        kpss_r = kpss_test(serie_mensual)
        resultados["estacionariedad"] = {
            "adf_stationary": bool(adf.get("stationary", False)),
            "adf_pvalue": round(float(adf.get("pval", 1.0)), 4),
            "kpss_stationary": bool(kpss_r.get("stationary", True)),
            "kpss_pvalue": round(float(kpss_r.get("pval", 0.1)), 4),
        }
        est = resultados["estacionariedad"]
        logger.info("ADF: %s (p=%.4f) | KPSS: %s (p=%.4f)",
                    "estacionaria" if est["adf_stationary"] else "no estacionaria",
                    est["adf_pvalue"],
                    "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                    est["kpss_pvalue"])
    except Exception as e:
        logger.warning("ADF/KPSS skipped: %s", e)

    # Guardar
    out = OUTPUT / "inferencial_oferta_hidrica.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resultados inferenciales guardados: %s", out.name)
    return resultados


# ===========================================================================
# 7. ESTADÍSTICA PREDICTIVA
# ===========================================================================

def predictiva(serie: pd.Series) -> dict:
    """SARIMAX + XGBoost — walk-forward con domain='hydrology'."""
    logger.info("--- Predictiva (dominio: hidrología) ---")

    # Usar serie mensual (más robusta para SARIMA, suficiente para backtesting)
    serie_m = serie.resample("ME").mean().dropna()
    logger.info("Serie mensual: %d meses (%s → %s)",
                len(serie_m), serie_m.index.min().date(), serie_m.index.max().date())

    resultados: dict = {}
    bt_results: dict = {}  # para rank_models

    # 7.1 SARIMAX(1,1,1)(1,1,1,12) — estacionalidad anual
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_sarima = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        logger.info("Entrenando SARIMAX(1,1,1)(1,1,1,12) — walk-forward (5 folds, horizon=3)...")
        res_sarima = walk_forward(
            model=model_sarima,
            y=serie_m,
            horizon=3,
            n_splits=5,
            domain="hydrology",
        )
        bt_results["SARIMAX(1,1,1)(1,1,1,12)"] = res_sarima
        m = res_sarima["metrics"]
        resultados["sarima_metrics"] = m
        logger.info("SARIMAX → NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s | PBIAS=%.2f%%",
                    m.get("nse", float("nan")),
                    m.get("kge", float("nan")),
                    m.get("rmse", float("nan")),
                    m.get("pbias", float("nan")))
    except Exception as e:
        logger.error("SARIMAX falló: %s", e)
        import traceback; traceback.print_exc()

    # 7.2 XGBoost
    try:
        from estadistica_ambiental.predictive.ml import XGBoostModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_xgb = XGBoostModel(lags=[1, 2, 3, 6, 12])
        logger.info("Entrenando XGBoost — walk-forward (5 folds, horizon=3)...")
        res_xgb = walk_forward(
            model=model_xgb,
            y=serie_m,
            horizon=3,
            n_splits=5,
            domain="hydrology",
        )
        bt_results["XGBoost"] = res_xgb
        m = res_xgb["metrics"]
        resultados["xgb_metrics"] = m
        logger.info("XGBoost → NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s | PBIAS=%.2f%%",
                    m.get("nse", float("nan")),
                    m.get("kge", float("nan")),
                    m.get("rmse", float("nan")),
                    m.get("pbias", float("nan")))
    except Exception as e:
        logger.warning("XGBoost skipped: %s", e)

    # 7.3 Ranking multi-criterio
    if bt_results:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models
            ranking = rank_models(bt_results, domain="hydrology")
            rank_path = OUTPUT / "ranking_modelos_oferta_hidrica.csv"
            ranking.to_csv(rank_path)
            logger.info("Ranking de modelos (hydrology):")
            for idx, row in ranking.iterrows():
                logger.info("  Rank %d: %s | NSE=%.4f | KGE=%.4f | score=%.4f",
                            int(row.get("rank", 0)), idx,
                            row.get("nse", float("nan")),
                            row.get("kge", float("nan")),
                            row.get("score", float("nan")))
            resultados["mejor_modelo"] = str(ranking.index[0])
            logger.info("Ranking guardado: %s", rank_path.name)
        except Exception as e:
            logger.warning("rank_models skipped: %s", e)

    # 7.4 Guardar métricas por fold
    bt_fold_path = OUTPUT / "backtesting_oferta_hidrica.csv"
    first_write = True
    for nombre, res in bt_results.items():
        folds_df = res.get("folds", pd.DataFrame())
        if not folds_df.empty:
            folds_df = folds_df.copy()
            folds_df["modelo"] = nombre
            folds_df.to_csv(bt_fold_path, mode="a",
                            header=first_write, index=False)
            first_write = False
    if bt_fold_path.exists():
        logger.info("Métricas por fold guardadas: %s", bt_fold_path.name)

    # 7.5 Pronóstico 12 meses — mejor modelo disponible
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        model_fc = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model_fc.fit(serie_m)
        forecast_vals = model_fc.predict(12)
        forecast_vals = np.clip(forecast_vals, 0.5, 50000.0)
        forecast_idx = pd.date_range(
            start=serie_m.index.max() + pd.DateOffset(months=1),
            periods=12, freq="ME",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="caudal_forecast")
        logger.info("Pronóstico 12 meses: media=%.1f m³/s | min=%.1f | max=%.1f",
                    forecast.mean(), forecast.min(), forecast.max())

        # Reporte HTML de pronóstico
        # Extraer predicciones de backtesting para comparación visual
        pred_dict: dict = {}
        for nombre, res in bt_results.items():
            preds_df = res.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                pred_dict[nombre] = preds_df["predicted"].values

        metrics_dict: dict = {
            nombre: res.get("metrics", {}) for nombre, res in bt_results.items()
        }

        if pred_dict:
            # Serie observada del período de test (igual longitud que predicciones)
            min_len = min(len(v) for v in pred_dict.values())
            y_test_ref = pd.Series(
                bt_results[list(bt_results.keys())[0]]["predictions"]["actual"].values[:min_len],
                name="caudal_observado",
            )
            report_path = OUTPUT / "forecast_oferta_hidrica.html"
            forecast_report(
                y_true=y_test_ref,
                predictions={k: v[:min_len] for k, v in pred_dict.items()},
                metrics=metrics_dict,
                output=str(report_path),
                title="Pronóstico de Caudal — Oferta Hídrica Colombia",
                variable_name="Caudal",
                unit="m³/s",
            )
            logger.info("Reporte de pronóstico guardado: %s", report_path.name)

        resultados["forecast_12m_mean"] = round(float(forecast.mean()), 2)
        resultados["forecast_12m_min"]  = round(float(forecast.min()), 2)
        resultados["forecast_12m_max"]  = round(float(forecast.max()), 2)

    except Exception as e:
        logger.warning("Pronóstico/forecast_report skipped: %s", e)
        import traceback; traceback.print_exc()

    return resultados


# ===========================================================================
# 8. REPORTE DE CUMPLIMIENTO (IUA)
# ===========================================================================

def reporte_cumplimiento(serie: pd.Series, iua_info: dict) -> None:
    """Genera reporte HTML de cumplimiento normativo hídrico (IUA)."""
    logger.info("--- Reporte de cumplimiento IUA ---")
    try:
        from estadistica_ambiental.reporting.compliance_report import compliance_report
        from estadistica_ambiental.config import IUA_THRESHOLDS

        # El módulo de cumplimiento trabaja con variables mapeadas en _NORMA_MAP.
        # Para IUA usamos la variable 'iua' con umbral personalizado (sin norma estándar).
        # Calculamos el IUA como serie mensual y reportamos frente a umbrales IDEAM.
        serie_m = serie.resample("ME").mean().dropna()
        oferta = float(serie_m.mean())
        iua_serie = pd.Series(
            (DEMANDA_ANUAL_M3S / serie_m.values) * 100,
            index=serie_m.index,
            name="iua",
        )

        df_rep = pd.DataFrame({"fecha": iua_serie.index, "iua": iua_serie.values})

        out = str(OUTPUT / "cumplimiento_iua_oferta_hidrica.html")
        compliance_report(
            df_rep,
            variables=["iua"],
            date_col="fecha",
            linea_tematica=LINEA,
            output=out,
            title="Índice de Uso del Agua (IUA) — Oferta Hídrica",
            custom_thresholds={"iua": IUA_THRESHOLDS["moderado"]},
        )
        logger.info("Reporte IUA guardado: %s", Path(out).name)
    except Exception as e:
        logger.warning("compliance_report skipped: %s", e)
        import traceback; traceback.print_exc()


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — OFERTA HÍDRICA | Caudal diario sintético Colombia")
    logger.info("Estación: %s", ESTACION)
    logger.info("=" * 65)

    # 1. Datos (verificar si hay datos reales, si no generar sintéticos)
    parquet_real = RAW / "oferta_hidrica_real.parquet"
    csv_real     = RAW / "oferta_hidrica_real.csv"
    if parquet_real.exists():
        logger.info("Cargando datos reales desde %s", parquet_real.name)
        df_raw = pd.read_parquet(parquet_real)
    elif csv_real.exists():
        logger.info("Cargando datos reales desde %s", csv_real.name)
        df_raw = pd.read_csv(csv_real, parse_dates=["fecha"])
    else:
        logger.info("No se encontraron datos reales — generando datos sintéticos")
        df_raw = generar_datos_sinteticos()

    # 2. Validación
    try:
        df_raw, serie = cargar_y_validar(df_raw)
    except Exception as e:
        logger.error("Carga/validación falló: %s", e)
        return

    # 3. EDA
    try:
        eda_res = eda(serie)
    except Exception as e:
        logger.warning("EDA falló: %s", e)
        eda_res = {}

    # 4. ENSO
    try:
        df_enso = aplicar_enso(df_raw)
    except Exception as e:
        logger.warning("ENSO falló: %s", e)
        df_enso = df_raw

    # 5. Descriptiva
    try:
        descriptiva(serie)
    except Exception as e:
        logger.warning("Descriptiva falló: %s", e)

    # 6. Inferencial
    try:
        inf = inferencial(serie)
    except Exception as e:
        logger.warning("Inferencial falló: %s", e)
        inf = {}

    # 7. Predictiva
    try:
        pred = predictiva(serie)
    except Exception as e:
        logger.error("Predictiva falló: %s", e)
        import traceback; traceback.print_exc()
        pred = {}

    # 8. Reporte cumplimiento
    try:
        iua_info = inf.get("iua", {})
        reporte_cumplimiento(serie, iua_info)
    except Exception as e:
        logger.warning("Reporte cumplimiento falló: %s", e)

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — %s", ESTACION)
    logger.info("  Periodo: %s → %s",
                serie.index.min().date(), serie.index.max().date())
    logger.info("  Caudal medio: %.2f m³/s", eda_res.get("media_m3s", float("nan")))
    logger.info("  CV (variabilidad): %.2f", eda_res.get("cv", float("nan")))

    iua = inf.get("iua", {})
    if iua:
        logger.info("  IUA: %.1f%% → categoría %s",
                    iua.get("iua_pct", float("nan")), iua.get("categoria_iua", "?"))

    mk = inf.get("mann_kendall", {})
    if mk:
        logger.info("  Mann-Kendall: %s (p=%.4f | %.3f m³/s/año)",
                    mk.get("tendencia", "?"), mk.get("p_value", 1.0),
                    mk.get("sen_slope_anual_m3s", 0.0))

    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMAX — NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s",
                    sarima.get("nse", float("nan")),
                    sarima.get("kge", float("nan")),
                    sarima.get("rmse", float("nan")))

    xgb = pred.get("xgb_metrics", {})
    if xgb:
        logger.info("  XGBoost — NSE=%.4f | KGE=%.4f | RMSE=%.2f m³/s",
                    xgb.get("nse", float("nan")),
                    xgb.get("kge", float("nan")),
                    xgb.get("rmse", float("nan")))

    mejor = pred.get("mejor_modelo", "N/A")
    logger.info("  Mejor modelo: %s", mejor)
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Oferta Hídrica completada.")


if __name__ == "__main__":
    main()
