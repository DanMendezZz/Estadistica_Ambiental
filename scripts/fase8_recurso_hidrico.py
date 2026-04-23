"""
Fase 8 — Ciclo estadístico completo: Recurso Hídrico.

Línea temática: Recurso Hídrico (calidad del agua superficial)
Variables: OD (mg/L), DBO5 (mg/L), pH (ud.), SST (mg/L), conductividad (µS/cm)
Frecuencia: mensual, 5 años sintéticos
Norma: Resolución 2115/2007 MinProtección (NORMA_AGUA_POTABLE)
       Resolución 631/2015 MinAmbiente (NORMA_VERTIMIENTOS)
Métricas primarias: NSE y KGE (domain='hydrology')

Flujo:
  1. Generación de datos sintéticos realistas (calidad agua superficial Colombia)
  2. Carga y validación (validate, linea_tematica='recurso_hidrico')
  3. EDA (estadísticas, gaps, correlaciones entre parámetros)
  4. ENSO con lag (enso_lagged, lag=3 meses)
  5. Inferencial: Mann-Kendall por variable, ADF/KPSS (OD), excedencias normativas
  6. Predictiva: SARIMAXModel + XGBoostModel en variable OD
     walk_forward(domain='hydrology'), rank_models(domain='hydrology')
  7. Reporte: compliance_report (Res.2115/2007) + forecast_report (OD)

Uso:
    python scripts/fase8_recurso_hidrico.py

Salidas en data/output/fase8/:
    - recurso_hidrico_sintetico.csv
    - descriptiva_recurso_hidrico.csv
    - inferencial_recurso_hidrico.json
    - backtesting_recurso_hidrico.csv
    - ranking_modelos_recurso_hidrico.csv
    - forecast_recurso_hidrico.html
    - cumplimiento_recurso_hidrico.html
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
logger = logging.getLogger("fase8_recurso_hidrico")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
RAW    = DATA / "raw"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "recurso_hidrico"
ESTACION = "Rio_Bogota_Alicachin_sintetica"

# Variables a analizar (columnas en el DataFrame)
VARIABLES = ["od", "dbo5", "ph", "sst", "conductividad"]

# Variable objetivo para modelado predictivo
VAR_TARGET = "od"


# ===========================================================================
# 1. DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_sinteticos(
    start: str = "2019-01-01",
    end: str = "2023-12-31",
    seed: int = 99,
) -> pd.DataFrame:
    """Genera serie mensual de parámetros de calidad del agua para Colombia.

    Modela el Rio Bogotá tramo Alicachín — mezcla de parámetros típicos
    de un río andino receptor de vertimientos domésticos e industriales.

    Rangos físicos (basados en IDEAM, CAR, EAB):
      OD:           2–9 mg/L (reducido por vertimientos)
      DBO5:         3–80 mg/L (alta carga orgánica)
      pH:           6.5–8.2 (aguas neutras-alcalinas)
      SST:          30–800 mg/L (alta sedimentación)
      Conductividad: 300–1200 µS/cm
    """
    rng = np.random.default_rng(seed)
    fechas = pd.date_range(start, end, freq="ME")
    n = len(fechas)
    t = np.arange(n)

    # ---------- OD (Oxígeno Disuelto mg/L) ----------
    # Menor en época seca (temperatura alta → menor solubilidad) y con > DBO5
    od_base = 5.5  # mg/L — típico río contaminado Andino
    od_seasonal = 1.5 * np.sin(2 * np.pi * t / 12 + np.pi)  # mín en época seca
    od_trend = 0.005 * t  # leve mejoría por políticas (PTAR Canoas)
    od_noise = rng.normal(0, 0.4, n)
    od = np.clip(od_base + od_seasonal + od_trend + od_noise, 0.5, 14.0)

    # ---------- DBO5 (mg/L) ----------
    # Correlación negativa con OD; tendencia decreciente (mejora tratamiento)
    dbo5_base = 30.0
    dbo5_seasonal = 8.0 * np.sin(2 * np.pi * t / 12)  # pico en época seca
    dbo5_trend = -0.08 * t  # mejora ambiental
    dbo5_noise = rng.exponential(scale=4.0, size=n) - 2.0  # sesgo positivo
    dbo5 = np.clip(dbo5_base + dbo5_seasonal + dbo5_trend + dbo5_noise, 1.0, 500.0)

    # ---------- pH ----------
    # Bastante estable, variaciones pequeñas por fotosíntesis y dilución
    ph_base = 7.3
    ph_seasonal = 0.2 * np.cos(2 * np.pi * t / 12)
    ph_noise = rng.normal(0, 0.15, n)
    ph = np.clip(ph_base + ph_seasonal + ph_noise, 5.0, 9.5)

    # ---------- SST (Sólidos Suspendidos Totales mg/L) ----------
    # Picos en épocas de lluvia (arrastre de suelos)
    sst_base = 180.0
    sst_seasonal = 120.0 * np.abs(np.sin(2 * np.pi * t / 12))
    sst_noise = rng.exponential(scale=30.0, size=n)
    sst = np.clip(sst_base + sst_seasonal + sst_noise, 5.0, 2000.0)

    # ---------- Conductividad (µS/cm) ----------
    # Correlaciona con SST y DBO5; mayor en época seca (concentración)
    cond_base = 650.0
    cond_seasonal = 100.0 * np.sin(2 * np.pi * t / 12 - np.pi / 4)
    cond_noise = rng.normal(0, 40.0, n)
    conductividad = np.clip(cond_base + cond_seasonal + cond_noise, 50.0, 3000.0)

    df = pd.DataFrame({
        "fecha":        fechas,
        "estacion":     ESTACION,
        "od":           np.round(od, 2),
        "dbo5":         np.round(dbo5, 2),
        "ph":           np.round(ph, 2),
        "sst":          np.round(sst, 1),
        "conductividad": np.round(conductividad, 0),
    })

    # ~5% datos faltantes (laboratorio, caudal extremo)
    for col in VARIABLES:
        idx_na = rng.choice(n, size=max(1, int(n * 0.05)), replace=False)
        df.loc[idx_na, col] = np.nan

    out = RAW / "recurso_hidrico_sintetico.csv"
    df.to_csv(out, index=False)
    logger.info("Datos sintéticos generados: %d meses | guardados en %s", n, out.name)
    return df


# ===========================================================================
# 2. CARGA Y VALIDACIÓN
# ===========================================================================

def cargar_y_validar(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valida rangos físicos y devuelve DataFrame limpio."""
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

    df = df_raw.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.sort_values("fecha").reset_index(drop=True)

    n_total = len(df)
    logger.info("DataFrame: %d registros mensuales | %s → %s",
                n_total,
                df["fecha"].min().date(),
                df["fecha"].max().date())
    return df_raw, df


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda(df: pd.DataFrame) -> dict:
    """EDA: estadísticas por variable, gaps, correlaciones."""
    logger.info("--- EDA Recurso Hídrico ---")

    resumen: dict = {}
    for var in VARIABLES:
        if var not in df.columns:
            continue
        s = df[var].dropna()
        if len(s) == 0:
            continue
        st = s.describe()
        resumen[var] = {
            "n": int(st.get("count", 0)),
            "media": round(float(st.get("mean", 0)), 3),
            "mediana": round(float(s.median()), 3),
            "std": round(float(st.get("std", 0)), 3),
            "min": round(float(st.get("min", 0)), 3),
            "max": round(float(st.get("max", 0)), 3),
            "pct_faltante": round(df[var].isna().mean() * 100, 2),
        }
        logger.info("%-15s media=%-8.2f std=%-7.2f min=%-7.2f max=%-7.2f NA=%.1f%%",
                    var, resumen[var]["media"], resumen[var]["std"],
                    resumen[var]["min"], resumen[var]["max"], resumen[var]["pct_faltante"])

    # Correlación OD vs DBO5 (antipattern esperado: OD baja cuando DBO5 sube)
    if "od" in df.columns and "dbo5" in df.columns:
        corr_od_dbo5 = df[["od", "dbo5"]].dropna().corr().loc["od", "dbo5"]
        logger.info("Correlación OD-DBO5: %.3f (esperado negativo)", corr_od_dbo5)
        resumen["correlacion_od_dbo5"] = round(float(corr_od_dbo5), 4)

    return resumen


# ===========================================================================
# 4. ENSO CON LAG
# ===========================================================================

def aplicar_enso(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica ENSO con lag=3 meses para recurso hídrico."""
    logger.info("--- ENSO con lag (recurso_hidrico) ---")
    try:
        from estadistica_ambiental.features.climate import enso_lagged, load_oni
        oni = load_oni()
        if oni.empty:
            logger.warning("ONI vacío (red no disponible) — se continúa sin ENSO")
            return df_raw
        df_enso = enso_lagged(df_raw, oni, date_col="fecha", linea_tematica=LINEA)
        from estadistica_ambiental.config import ENSO_LAG_MESES
        lag = ENSO_LAG_MESES.get(LINEA, 3)
        lag_col = f"oni_lag{lag}"
        if lag_col in df_enso.columns:
            oni_vals = df_enso[lag_col].dropna()
            logger.info("ONI lag=%d | registros con ONI: %d | media ONI: %.3f",
                        lag, len(oni_vals), oni_vals.mean())
        return df_enso
    except Exception as e:
        logger.warning("ENSO skipped: %s", e)
        return df_raw


# ===========================================================================
# 5. ESTADÍSTICA DESCRIPTIVA
# ===========================================================================

def descriptiva(df: pd.DataFrame) -> pd.DataFrame:
    """Resúmenes anuales por variable de calidad del agua."""
    logger.info("--- Descriptiva ---")

    if "fecha" not in df.columns:
        logger.warning("Columna 'fecha' no encontrada — descriptiva omitida")
        return pd.DataFrame()

    df2 = df.copy()
    df2["anio"] = pd.to_datetime(df2["fecha"]).dt.year

    frames = []
    for var in VARIABLES:
        if var not in df2.columns:
            continue
        grp = df2.groupby("anio")[var].agg(
            n="count", media="mean", mediana="median", std="std",
            min="min", max="max",
        ).round(3)
        grp.columns = [f"{var}_{c}" for c in grp.columns]
        frames.append(grp)

    if not frames:
        return pd.DataFrame()

    resumen_anual = pd.concat(frames, axis=1)
    out = OUTPUT / "descriptiva_recurso_hidrico.csv"
    resumen_anual.to_csv(out)
    logger.info("Resumen anual guardado: %s (%d años)", out.name, len(resumen_anual))
    return resumen_anual


# ===========================================================================
# 6. ESTADÍSTICA INFERENCIAL
# ===========================================================================

def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall por variable, ADF/KPSS en OD, excedencias normativas."""
    logger.info("--- Inferencial ---")
    resultados: dict = {}

    df2 = df.copy()
    df2.index = pd.to_datetime(df2["fecha"])

    # 6.1 Mann-Kendall por variable
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk_resultados: dict = {}
        for var in VARIABLES:
            if var not in df2.columns:
                continue
            serie_var = df2[var].dropna()
            if len(serie_var) < 10:
                continue
            try:
                mk = mann_kendall(serie_var)
                sd = sens_slope(serie_var)
                mk_resultados[var] = {
                    "tendencia": mk.get("trend", "unknown"),
                    "p_value": round(float(mk.get("pval", 1.0)), 4),
                    "significativo": mk.get("pval", 1.0) < 0.05,
                    "sen_slope_anual": round(float(sd.get("slope", 0.0) * 12), 4),
                }
                logger.info("MK %-15s tendencia=%-15s p=%.4f slope=%.4f/año",
                            var, mk_resultados[var]["tendencia"],
                            mk_resultados[var]["p_value"],
                            mk_resultados[var]["sen_slope_anual"])
            except Exception as e_var:
                logger.warning("MK '%s' skipped: %s", var, e_var)
        resultados["mann_kendall"] = mk_resultados
    except Exception as e:
        logger.warning("Mann-Kendall skipped: %s", e)

    # 6.2 ADF + KPSS en OD (variable objetivo del modelado predictivo)
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        serie_od = df2[VAR_TARGET].dropna()
        if len(serie_od) >= 10:
            adf = adf_test(serie_od)
            kpss_r = kpss_test(serie_od)
            resultados["estacionariedad_od"] = {
                "adf_stationary": bool(adf.get("stationary", False)),
                "adf_pvalue": round(float(adf.get("pval", 1.0)), 4),
                "kpss_stationary": bool(kpss_r.get("stationary", True)),
                "kpss_pvalue": round(float(kpss_r.get("pval", 0.1)), 4),
            }
            est = resultados["estacionariedad_od"]
            logger.info("ADF (OD): %s (p=%.4f) | KPSS (OD): %s (p=%.4f)",
                        "estacionaria" if est["adf_stationary"] else "no estacionaria",
                        est["adf_pvalue"],
                        "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                        est["kpss_pvalue"])
    except Exception as e:
        logger.warning("ADF/KPSS skipped: %s", e)

    # 6.3 Excedencias normativas (Res. 2115/2007 y Res. 631/2015)
    try:
        from estadistica_ambiental.inference.intervals import exceedance_report
        exc_resultados: dict = {}
        vars_con_norma = [v for v in VARIABLES if v in ["od", "dbo5", "ph", "sst", "conductividad"]]
        logger.info("Reporte de excedencias normativas:")
        for var in vars_con_norma:
            if var not in df2.columns:
                continue
            serie_var = df2[var].dropna()
            exc = exceedance_report(serie_var, variable=var)
            if not exc.empty:
                exc_resultados[var] = exc.to_dict(orient="records")
                for _, row in exc.iterrows():
                    cumple_str = "OK" if row.get("cumple", False) else "INCUMPLE"
                    logger.info("  %-15s %-30s umbral=%-6.1f %s (%.1f%%)",
                                var, row.get("norma", "")[:30],
                                row.get("umbral", 0),
                                cumple_str,
                                row.get("pct_exceed", 0))
            else:
                logger.info("  %-15s Sin norma colombiana registrada", var)
        resultados["excedencias"] = exc_resultados
    except Exception as e:
        logger.warning("Excedance report skipped: %s", e)

    # Guardar
    out = OUTPUT / "inferencial_recurso_hidrico.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resultados inferenciales guardados: %s", out.name)
    return resultados


# ===========================================================================
# 7. ESTADÍSTICA PREDICTIVA
# ===========================================================================

def predictiva(df: pd.DataFrame) -> dict:
    """SARIMAX + XGBoost en OD — walk-forward domain='hydrology'."""
    logger.info("--- Predictiva OD (dominio: hidrología) ---")

    # Serie objetivo: OD mensual
    serie_od = (
        df.set_index(pd.to_datetime(df["fecha"]))[VAR_TARGET]
        .dropna()
        .sort_index()
    )
    logger.info("Serie OD: %d meses (%s → %s)",
                len(serie_od), serie_od.index.min().date(), serie_od.index.max().date())

    if len(serie_od) < 24:
        logger.warning("Serie OD muy corta (%d meses) — predictiva omitida", len(serie_od))
        return {}

    resultados: dict = {}
    bt_results: dict = {}

    # 7.1 SARIMAX(1,1,1)(1,1,1,12)
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        model_sarima = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        logger.info("Entrenando SARIMAX(1,1,1)(1,1,1,12) — walk-forward (4 folds, horizon=2)...")
        res_sarima = walk_forward(
            model=model_sarima,
            y=serie_od,
            horizon=2,
            n_splits=4,
            domain="hydrology",
        )
        bt_results["SARIMAX(1,1,1)(1,1,1,12)"] = res_sarima
        m = res_sarima["metrics"]
        resultados["sarima_metrics"] = m
        logger.info("SARIMAX → NSE=%.4f | KGE=%.4f | RMSE=%.4f mg/L | PBIAS=%.2f%%",
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
        logger.info("Entrenando XGBoost — walk-forward (4 folds, horizon=2)...")
        res_xgb = walk_forward(
            model=model_xgb,
            y=serie_od,
            horizon=2,
            n_splits=4,
            domain="hydrology",
        )
        bt_results["XGBoost"] = res_xgb
        m = res_xgb["metrics"]
        resultados["xgb_metrics"] = m
        logger.info("XGBoost → NSE=%.4f | KGE=%.4f | RMSE=%.4f mg/L | PBIAS=%.2f%%",
                    m.get("nse", float("nan")),
                    m.get("kge", float("nan")),
                    m.get("rmse", float("nan")),
                    m.get("pbias", float("nan")))
    except Exception as e:
        logger.warning("XGBoost skipped: %s", e)

    # 7.3 Ranking
    if bt_results:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models
            ranking = rank_models(bt_results, domain="hydrology")
            rank_path = OUTPUT / "ranking_modelos_recurso_hidrico.csv"
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
    bt_fold_path = OUTPUT / "backtesting_recurso_hidrico.csv"
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

    # 7.5 Pronóstico 6 meses + reporte HTML
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.reporting.forecast_report import forecast_report

        model_fc = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model_fc.fit(serie_od)
        forecast_vals = model_fc.predict(6)
        forecast_vals = np.clip(forecast_vals, 0.0, 20.0)
        forecast_idx = pd.date_range(
            start=serie_od.index.max() + pd.DateOffset(months=1),
            periods=6, freq="ME",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="od_forecast")
        logger.info("Pronóstico OD 6 meses: media=%.2f mg/L | min=%.2f | max=%.2f",
                    forecast.mean(), forecast.min(), forecast.max())

        # Comparación visual backtesting
        pred_dict: dict = {}
        for nombre, res in bt_results.items():
            preds_df = res.get("predictions", pd.DataFrame())
            if not preds_df.empty and "predicted" in preds_df.columns:
                pred_dict[nombre] = preds_df["predicted"].values

        metrics_dict = {
            nombre: res.get("metrics", {}) for nombre, res in bt_results.items()
        }

        if pred_dict:
            min_len = min(len(v) for v in pred_dict.values())
            first_key = list(bt_results.keys())[0]
            y_test_ref = pd.Series(
                bt_results[first_key]["predictions"]["actual"].values[:min_len],
                name="od_observado",
            )
            report_path = OUTPUT / "forecast_recurso_hidrico.html"
            forecast_report(
                y_true=y_test_ref,
                predictions={k: v[:min_len] for k, v in pred_dict.items()},
                metrics=metrics_dict,
                output=str(report_path),
                title="Pronóstico OD — Recurso Hídrico Colombia",
                variable_name="Oxígeno Disuelto",
                unit="mg/L",
            )
            logger.info("Reporte de pronóstico guardado: %s", report_path.name)

        resultados["forecast_6m_mean"] = round(float(forecast.mean()), 3)
        resultados["forecast_6m_min"]  = round(float(forecast.min()), 3)
        resultados["forecast_6m_max"]  = round(float(forecast.max()), 3)

    except Exception as e:
        logger.warning("Pronóstico/forecast_report skipped: %s", e)
        import traceback; traceback.print_exc()

    return resultados


# ===========================================================================
# 8. REPORTE DE CUMPLIMIENTO NORMATIVO
# ===========================================================================

def reporte_cumplimiento(df: pd.DataFrame) -> None:
    """Genera reporte HTML cumplimiento Res. 2115/2007 y Res. 631/2015."""
    logger.info("--- Reporte de cumplimiento normativo ---")
    try:
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        # Variables con norma colombiana mapeada en intervals._NORMA_MAP
        vars_norma = [v for v in ["od", "dbo5", "ph", "conductividad"] if v in df.columns]
        if not vars_norma:
            logger.warning("Ninguna variable con norma disponible — reporte omitido")
            return

        df_rep = df[["fecha"] + vars_norma].copy()
        out = str(OUTPUT / "cumplimiento_recurso_hidrico.html")

        compliance_report(
            df_rep,
            variables=vars_norma,
            date_col="fecha",
            linea_tematica=LINEA,
            output=out,
            title="Cumplimiento Normativo — Recurso Hídrico (Res. 2115/2007 | Res. 631/2015)",
        )
        logger.info("Reporte normativo guardado: %s", Path(out).name)
    except Exception as e:
        logger.warning("compliance_report skipped: %s", e)
        import traceback; traceback.print_exc()


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — RECURSO HÍDRICO | Calidad agua mensual Colombia")
    logger.info("Estación: %s", ESTACION)
    logger.info("Variables: %s", ", ".join(VARIABLES))
    logger.info("=" * 65)

    # 1. Datos (verificar si hay datos reales, si no generar sintéticos)
    parquet_real = RAW / "recurso_hidrico_real.parquet"
    csv_real     = RAW / "recurso_hidrico_real.csv"
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
        df_raw, df = cargar_y_validar(df_raw)
    except Exception as e:
        logger.error("Carga/validación falló: %s", e)
        return

    # 3. EDA
    try:
        eda_res = eda(df)
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
        descriptiva(df)
    except Exception as e:
        logger.warning("Descriptiva falló: %s", e)

    # 6. Inferencial
    try:
        inf = inferencial(df)
    except Exception as e:
        logger.warning("Inferencial falló: %s", e)
        inf = {}

    # 7. Predictiva
    try:
        pred = predictiva(df)
    except Exception as e:
        logger.error("Predictiva falló: %s", e)
        import traceback; traceback.print_exc()
        pred = {}

    # 8. Reporte cumplimiento
    try:
        reporte_cumplimiento(df)
    except Exception as e:
        logger.warning("Reporte cumplimiento falló: %s", e)

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — %s", ESTACION)
    logger.info("  Periodo: %s → %s",
                df["fecha"].min().date(), df["fecha"].max().date())

    for var in VARIABLES:
        if var in eda_res:
            r = eda_res[var]
            logger.info("  %-15s media=%.2f | std=%.2f | NA=%.1f%%",
                        var, r.get("media", float("nan")),
                        r.get("std", float("nan")),
                        r.get("pct_faltante", float("nan")))

    mk_res = inf.get("mann_kendall", {})
    for var, mk in mk_res.items():
        if mk.get("significativo", False):
            logger.info("  MK %s: %s (p=%.4f, %.4f/año)",
                        var, mk.get("tendencia", "?"),
                        mk.get("p_value", 1.0),
                        mk.get("sen_slope_anual", 0.0))

    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMAX OD — NSE=%.4f | KGE=%.4f | RMSE=%.4f mg/L",
                    sarima.get("nse", float("nan")),
                    sarima.get("kge", float("nan")),
                    sarima.get("rmse", float("nan")))

    xgb = pred.get("xgb_metrics", {})
    if xgb:
        logger.info("  XGBoost OD — NSE=%.4f | KGE=%.4f | RMSE=%.4f mg/L",
                    xgb.get("nse", float("nan")),
                    xgb.get("kge", float("nan")),
                    xgb.get("rmse", float("nan")))

    mejor = pred.get("mejor_modelo", "N/A")
    logger.info("  Mejor modelo: %s", mejor)
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Recurso Hídrico completada.")


if __name__ == "__main__":
    main()
