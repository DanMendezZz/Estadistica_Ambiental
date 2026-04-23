"""
Fase 8 — Ciclo estadístico completo con datos reales de calidad del aire.

Fuente: Red CAR Cundinamarca | PM2.5 horario 2017-2026
Estación focal: BOGOTA RURAL - MOCHUELO (baseline) + análisis de red completa
Norma: Resolución 2254/2017 MinAmbiente Colombia

Flujo:
  1. Carga y validación
  2. EDA (calidad, distribución, estacionalidad)
  3. Estadística descriptiva (resúmenes anuales, mensuales)
  4. Inferencial (Mann-Kendall, ADF/KPSS, excedencias normativas)
  5. Predictiva (SARIMA walk-forward backtesting)
  6. Reporte de cumplimiento normativo (HTML)

Uso:
    python scripts/fase8_calidad_aire.py

Salidas en data/output/fase8/:
    - eda_red_car.html
    - descriptiva_mochuelo.csv
    - inferencial_mochuelo.json
    - backtesting_mochuelo.csv
    - cumplimiento_mochuelo.html
    - forecast_mochuelo.html
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
# Configuración de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fase8")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RAW     = DATA / "raw"
OUTPUT  = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

PARQUET   = RAW / "calidad_aire_CAR_2016_2026.parquet"
ESTACION  = "BOGOTA RURAL - MOCHUELO"
VARIABLE  = "pm25"
POLLUTANT = "pm25"


# ===========================================================================
# 1. CARGA Y VALIDACIÓN
# ===========================================================================

def cargar_datos() -> tuple[pd.DataFrame, pd.Series]:
    """Carga el parquet, filtra la estación focal y agrega a diario."""
    logger.info("Cargando datos desde %s", PARQUET.name)
    df_raw = pd.read_parquet(PARQUET)

    # Estación focal
    df = df_raw[df_raw["estacion"] == ESTACION].copy()
    df = df.sort_values("fecha").reset_index(drop=True)
    logger.info("Registros horarios para %s: %d", ESTACION, len(df))
    logger.info("Periodo: %s → %s", df["fecha"].min().date(), df["fecha"].max().date())

    # Promedio diario (norma colombiana usa promedio 24h)
    serie_diaria: pd.Series = (
        df.set_index("fecha")[VARIABLE]
        .resample("D")
        .mean()
        .rename("pm25")
    )
    serie_diaria = serie_diaria.dropna()
    logger.info("Serie diaria: %d días", len(serie_diaria))
    return df, serie_diaria


def validar(df: pd.DataFrame) -> None:
    """Valida rangos físicos usando el módulo io/validators."""
    try:
        from estadistica_ambiental.io.validators import validate
        validate(df.rename(columns={"fecha": "fecha", VARIABLE: "pm25"}),
                 date_col="fecha", linea_tematica="calidad_aire")
        logger.info("Validación de dominio: OK")
    except Exception as e:
        logger.warning("Validación skipped: %s", e)


# ===========================================================================
# 2. EDA
# ===========================================================================

def eda_red_completa(df_raw: pd.DataFrame) -> dict:
    """EDA de la red completa CAR: cobertura, distribución, estaciones."""
    logger.info("--- EDA red completa CAR ---")

    n_estaciones = df_raw["estacion"].nunique()
    periodo = f"{df_raw['fecha'].min().date()} → {df_raw['fecha'].max().date()}"
    stats_globales = df_raw["pm25"].describe()

    # Cobertura por estación (% días con datos vs periodo total)
    total_dias = (df_raw["fecha"].max() - df_raw["fecha"].min()).days + 1
    cobertura = (
        df_raw.groupby("estacion")["fecha"]
        .apply(lambda s: s.dt.date.nunique())
        .div(total_dias)
        .mul(100)
        .round(1)
        .sort_values(ascending=False)
    )

    # Media PM2.5 por estación
    media_por_estacion = (
        df_raw.groupby("estacion")["pm25"]
        .mean()
        .round(2)
        .sort_values(ascending=False)
    )

    logger.info("Red CAR: %d estaciones | Periodo: %s", n_estaciones, periodo)
    logger.info("PM2.5 media global: %.2f µg/m³ (σ=%.2f)", stats_globales["mean"], stats_globales["std"])
    logger.info("Estación más contaminada: %s (%.1f µg/m³)",
                media_por_estacion.index[0], media_por_estacion.iloc[0])
    logger.info("Estación más limpia: %s (%.1f µg/m³)",
                media_por_estacion.index[-1], media_por_estacion.iloc[-1])

    return {
        "n_estaciones": n_estaciones,
        "periodo": periodo,
        "stats_globales": stats_globales.to_dict(),
        "media_por_estacion": media_por_estacion.to_dict(),
        "cobertura_pct": cobertura.to_dict(),
    }


def eda_estacion(serie: pd.Series) -> dict:
    """EDA detallado de la estación focal."""
    logger.info("--- EDA %s ---", ESTACION)

    stats = serie.describe()

    # Norma colombiana (24h PM2.5): Res. 2254/2017
    try:
        from estadistica_ambiental.config import NORMA_CO
        norma_24h = NORMA_CO.get("pm25", {}).get("24h", 37.0)
    except Exception:
        norma_24h = 37.0

    pct_excede_co  = (serie > norma_24h).mean() * 100
    pct_excede_oms = (serie > 15.0).mean() * 100

    # Gaps
    idx_completo = pd.date_range(serie.index.min(), serie.index.max(), freq="D")
    n_gaps = len(idx_completo) - len(serie)

    logger.info("PM2.5 media: %.2f µg/m³ | mediana: %.2f", stats["mean"], stats["50%"])
    logger.info("Máximo: %.1f µg/m³ | p95: %.1f | p99: %.1f",
                stats["max"], serie.quantile(0.95), serie.quantile(0.99))
    logger.info("Excede norma CO (%.0f µg/m³): %.1f%% de días", norma_24h, pct_excede_co)
    logger.info("Excede guía OMS (15 µg/m³): %.1f%% de días", pct_excede_oms)
    logger.info("Gaps en serie diaria: %d días (%.1f%%)",
                n_gaps, n_gaps / len(idx_completo) * 100)

    return {
        "stats": stats.to_dict(),
        "pct_excede_norma_co_24h": round(pct_excede_co, 2),
        "pct_excede_oms_15": round(pct_excede_oms, 2),
        "n_gaps_diarios": n_gaps,
    }


# ===========================================================================
# 3. ESTADÍSTICA DESCRIPTIVA
# ===========================================================================

def descriptiva(serie: pd.Series) -> pd.DataFrame:
    """Resúmenes anuales y mensuales de PM2.5."""
    logger.info("--- Descriptiva ---")
    df = serie.to_frame("pm25")
    df["anio"]  = df.index.year
    df["mes"]   = df.index.month

    # Resumen anual
    anual = df.groupby("anio")["pm25"].agg(
        n="count",
        media="mean",
        mediana="median",
        std="std",
        p95=lambda x: x.quantile(0.95),
        max="max",
    ).round(2)

    # Resumen mensual (promedio sobre años)
    mensual = df.groupby("mes")["pm25"].agg(
        media="mean",
        std="std",
    ).round(2)

    logger.info("Tendencia anual (últimos 5 años):")
    for anio, row in anual.tail(5).iterrows():
        logger.info("  %d: media=%.1f µg/m³ | p95=%.1f | n=%d",
                    anio, row["media"], row["p95"], int(row["n"]))

    # Mes más contaminado
    mes_max = mensual["media"].idxmax()
    logger.info("Mes más contaminado: %02d (media %.1f µg/m³)", mes_max, mensual.loc[mes_max, "media"])

    out_path = OUTPUT / "descriptiva_mochuelo.csv"
    anual.to_csv(out_path)
    logger.info("Resumen anual guardado: %s", out_path.name)

    return anual


# ===========================================================================
# 4. ESTADÍSTICA INFERENCIAL
# ===========================================================================

def inferencial(serie: pd.Series) -> dict:
    """Mann-Kendall, ADF/KPSS, excedencias normativas."""
    logger.info("--- Inferencial ---")
    resultados: dict = {}

    # 4.1 Mann-Kendall (tendencia)
    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk    = mann_kendall(serie)
        slope_dict = sens_slope(serie)
        slope_val  = slope_dict.get("slope", mk.get("slope", 0.0))
        resultados["mann_kendall"] = {
            "tendencia": mk.get("trend", "unknown"),
            "p_value": round(float(mk.get("pval", 1.0)), 4),
            "significativo": mk.get("pval", 1.0) < 0.05,
            "sen_slope_anual": round(float(slope_val * 365), 4),
        }
        mk_r = resultados["mann_kendall"]
        logger.info("Mann-Kendall: tendencia=%s | p=%.4f | Sen slope=%.3f µg/m³/año",
                    mk_r["tendencia"], mk_r["p_value"], mk_r["sen_slope_anual"])
    except Exception as e:
        logger.warning("Mann-Kendall skipped: %s", e)

    # 4.2 Estacionariedad ADF + KPSS
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        # Usar muestra de los últimos 2 años para velocidad
        serie_2a = serie.last("730D")
        adf = adf_test(serie_2a)
        kpss = kpss_test(serie_2a)
        resultados["estacionariedad"] = {
            "adf_stationary": bool(adf.get("is_stationary", False)),
            "adf_pvalue": round(float(adf.get("p_value", 1.0)), 4),
            "kpss_stationary": bool(kpss.get("is_stationary", True)),
            "kpss_pvalue": round(float(kpss.get("p_value", 0.1)), 4),
        }
        est = resultados["estacionariedad"]
        logger.info("ADF: %s (p=%.4f) | KPSS: %s (p=%.4f)",
                    "estacionaria" if est["adf_stationary"] else "no estacionaria",
                    est["adf_pvalue"],
                    "estacionaria" if est["kpss_stationary"] else "no estacionaria",
                    est["kpss_pvalue"])
    except Exception as e:
        logger.warning("ADF/KPSS skipped: %s", e)

    # 4.3 Excedencias normativas
    try:
        from estadistica_ambiental.inference.intervals import exceedance_report
        exc = exceedance_report(serie, variable="pm25")
        if not exc.empty:
            resultados["excedencias"] = exc.to_dict(orient="records")
            logger.info("Reporte de excedencias (normas colombianas):")
            for _, row in exc.iterrows():
                logger.info("  %-30s umbral=%-6.1f excede=%.1f%%",
                            row.get("norma", ""), row.get("umbral", 0),
                            row.get("pct_exceed", 0))
    except Exception as e:
        logger.warning("Excedance report skipped: %s", e)

    # Guardar
    out_path = OUTPUT / "inferencial_mochuelo.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resultados inferenciales guardados: %s", out_path.name)

    return resultados


# ===========================================================================
# 5. ESTADÍSTICA PREDICTIVA
# ===========================================================================

def predictiva(serie: pd.Series) -> dict:
    """SARIMA walk-forward backtesting en últimos 2 años."""
    logger.info("--- Predictiva ---")

    # Usar últimos 2 años para velocidad (730 días)
    serie_2a = serie.last("730D").dropna()
    logger.info("Serie para modelado: %d días (%s → %s)",
                len(serie_2a), serie_2a.index.min().date(), serie_2a.index.max().date())

    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        # SARIMA(1,1,1)(1,1,1,7) — estacionalidad semanal
        model = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 7))

        logger.info("Entrenando SARIMA(1,1,1)(1,1,1,7) — walk-forward (5 folds)...")
        result = walk_forward(
            model=model,
            y=serie_2a,
            horizon=7,
            n_splits=5,
            domain="air_quality",
            pollutant=POLLUTANT,
        )

        metrics = result["metrics"]
        resultados["sarima_metrics"] = metrics
        logger.info("SARIMA walk-forward: RMSE=%.3f | MAE=%.3f | R2=%.3f | hit_rate_ica=%.1f%%",
                    metrics.get("rmse", float("nan")),
                    metrics.get("mae", float("nan")),
                    metrics.get("r2", float("nan")),
                    metrics.get("hit_rate_ica", float("nan")))

        # Guardar métricas por fold
        if not result["folds"].empty:
            fold_path = OUTPUT / "backtesting_mochuelo.csv"
            result["folds"].to_csv(fold_path, index=False)
            logger.info("Métricas por fold guardadas: %s", fold_path.name)

        # Pronóstico de los próximos 30 días
        logger.info("Generando pronóstico de 30 días...")
        model_full = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 7))
        model_full.fit(serie_2a)
        forecast_vals = model_full.predict(30)
        forecast_idx  = pd.date_range(
            start=serie_2a.index.max() + pd.Timedelta(days=1),
            periods=30, freq="D",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="pm25_forecast")
        forecast.clip(lower=0, inplace=True)

        forecast_path = OUTPUT / "forecast_30d_mochuelo.csv"
        forecast.to_csv(forecast_path, header=True)
        logger.info("Pronóstico guardado: %s (media=%.1f µg/m³)",
                    forecast_path.name, forecast.mean())

        resultados["forecast_30d_mean"]  = round(float(forecast.mean()), 2)
        resultados["forecast_30d_max"]   = round(float(forecast.max()), 2)

        # Reporte HTML de pronóstico
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            report_path = OUTPUT / "forecast_mochuelo.html"
            preds_series = result.get("predictions", pd.DataFrame())
            preds_arr = (preds_series["predicted"].values
                         if not preds_series.empty and "predicted" in preds_series.columns
                         else np.array([]))
            forecast_report(
                y_true=serie_2a.iloc[-len(preds_arr):] if len(preds_arr) else serie_2a,
                predictions={"SARIMA(1,1,1)(1,1,1,7)": preds_arr},
                metrics={"SARIMA(1,1,1)(1,1,1,7)": metrics},
                output=str(report_path),
                title="Pronóstico PM2.5 — Bogotá Rural Mochuelo",
                variable_name="PM2.5",
                unit="µg/m³",
            )
            logger.info("Reporte de pronóstico guardado: %s", report_path.name)
        except Exception as e:
            logger.warning("forecast_report skipped: %s", e)

    except Exception as e:
        logger.error("Modelado predictivo falló: %s", e)
        import traceback
        traceback.print_exc()

    return resultados


# ===========================================================================
# 6. REPORTE DE CUMPLIMIENTO NORMATIVO
# ===========================================================================

def reporte_cumplimiento(serie: pd.Series) -> None:
    """Genera reporte HTML de cumplimiento normativo."""
    logger.info("--- Reporte de cumplimiento normativo ---")
    try:
        from estadistica_ambiental.reporting.compliance_report import compliance_report
        df_rep = serie.to_frame("pm25").reset_index().rename(columns={"index": "fecha"})
        out_path = str(OUTPUT / "cumplimiento_mochuelo.html")
        compliance_report(
            df_rep,
            variables=["pm25"],
            linea_tematica="calidad_aire",
            output=out_path,
        )
        logger.info("Reporte normativo guardado: %s", Path(out_path).name)
    except Exception as e:
        logger.warning("compliance_report skipped: %s", e)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 60)
    logger.info("FASE 8 — Calidad del Aire | Red CAR Cundinamarca")
    logger.info("Estación focal: %s", ESTACION)
    logger.info("=" * 60)

    # 1. Carga
    df_raw, serie_diaria = cargar_datos()
    validar(df_raw)

    # 2. EDA (red + estación) — en paralelo conceptual
    eda_red  = eda_red_completa(df_raw)
    eda_est  = eda_estacion(serie_diaria)

    # 3. Descriptiva
    anual = descriptiva(serie_diaria)

    # 4. Inferencial
    inf = inferencial(serie_diaria)

    # 5. Predictiva
    pred = predictiva(serie_diaria)

    # 6. Reporte normativo
    reporte_cumplimiento(serie_diaria)

    # Resumen final
    logger.info("=" * 60)
    logger.info("RESUMEN EJECUTIVO — %s", ESTACION)
    logger.info("  Periodo: %s → %s",
                serie_diaria.index.min().date(), serie_diaria.index.max().date())
    logger.info("  PM2.5 media diaria: %.2f µg/m³", serie_diaria.mean())
    logger.info("  Excede norma CO (37 µg/m³, 24h): %.1f%% de días",
                eda_est["pct_excede_norma_co_24h"])
    logger.info("  Excede guía OMS (15 µg/m³): %.1f%% de días",
                eda_est["pct_excede_oms_15"])

    mk = inf.get("mann_kendall", {})
    if mk:
        logger.info("  Tendencia (Mann-Kendall): %s (p=%.4f, %.3f µg/m³/año)",
                    mk.get("tendencia", "?"), mk.get("p_value", 1.0), mk.get("sen_slope_anual", 0.0))

    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMA RMSE: %.3f µg/m³ | hit_rate_ica: %.1f%%",
                    sarima.get("rmse", float("nan")),
                    sarima.get("hit_rate_ica", float("nan")))

    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 60)
    logger.info("Fase 8 completada.")


if __name__ == "__main__":
    main()
