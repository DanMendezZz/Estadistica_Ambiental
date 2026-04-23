"""
Fase 8 — Ciclo estadístico completo: Páramos.

Línea temática: Páramos
Datos: sintéticos (temperatura, precipitación, cobertura vegetal)
       3 estaciones ficticias a distintas altitudes, 20 años mensuales (2004-2023)

Flujo:
  1. Generación de datos sintéticos de páramo
  2. Validación con validate(df, linea_tematica="paramos")
  3. EDA: distribución por estación, estacionalidad
  4. Tendencia temperatura: Mann-Kendall (esperamos tendencia positiva por CC)
  5. ENSO lagged: enso_lagged(df, oni, linea_tematica='paramos')  [lag=2 meses]
  6. Estacionariedad ADF + KPSS
  7. STL descomposición (period=12)
  8. SARIMA baseline + walk-forward backtesting
  9. Métricas: MAE, RMSE, R² (domain="general")
  10. Reporte HTML de pronóstico

Uso:
    python scripts/fase8_paramos.py

Salidas en data/output/fase8/:
    - paramos_datos_sinteticos.csv
    - paramos_validacion.json
    - paramos_tendencia.json
    - paramos_stl.csv
    - paramos_backtesting.csv
    - paramos_forecast.csv
    - forecast_paramos.html
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
logger = logging.getLogger("fase8_paramos")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Estaciones ficticias de páramo
# ---------------------------------------------------------------------------
ESTACIONES = [
    {"nombre": "Chingaza_Alta",   "altitud": 3800, "temp_base": 6.0},
    {"nombre": "Sumapaz_Media",   "altitud": 3400, "temp_base": 9.0},
    {"nombre": "Guerrero_Baja",   "altitud": 3100, "temp_base": 11.5},
]
N_ANIOS = 20
INICIO  = "2004-01-01"


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos_paramos() -> pd.DataFrame:
    """Genera 20 años de datos mensuales sintéticos para 3 estaciones de páramo.

    - Temperatura: N(base, 3) + tendencia +0.03°C/año + estacionalidad anual
    - Precipitación: log-N calibrada con 2 temporadas (apr-oct húmedo, nov-mar seco)
    - Cobertura vegetal: tendencia negativa leve + efecto ENSO sintético
    """
    logger.info("--- Generando datos sintéticos de páramos ---")
    rng = np.random.default_rng(2024)

    n_meses = N_ANIOS * 12
    fechas = pd.date_range(INICIO, periods=n_meses, freq="MS")
    meses  = fechas.month
    anios  = fechas.year
    t      = np.arange(n_meses)  # índice temporal

    # Tendencia de temperatura (°C/mes)
    trend_temp = 0.03 / 12  # 0.03°C/año → por mes

    # Estacionalidad anual temperatura (más cálido en ago-sep, más frío en dic-ene)
    seasonal_temp = 1.5 * np.sin(2 * np.pi * (meses - 1) / 12 - np.pi / 2)

    # Factor húmedo/seco precipitación
    # Temporadas húmedas: abr-may y oct-nov (bimodal Andes)
    precip_seasonal = np.where(
        (meses >= 4) & (meses <= 5),  1.8,   # temporada húmeda 1
        np.where(
        (meses >= 9) & (meses <= 11), 1.6,   # temporada húmeda 2 (oct-nov)
        np.where(
        (meses == 6) | (meses == 7),  0.7,   # verano (junio-julio: más seco)
        0.8                                   # dic-mar seco
        ))
    )

    registros = []
    for est in ESTACIONES:
        nombre    = est["nombre"]
        temp_base = est["temp_base"]

        # Temperatura con tendencia + estacionalidad + ruido
        temperatura = (
            temp_base
            + trend_temp * t
            + seasonal_temp
            + rng.normal(0, 1.2, n_meses)
        )
        temperatura = np.clip(temperatura, -5.0, 16.0)

        # Precipitación log-normal (mm/mes)
        # Páramos: ~800-2500 mm/año; media ~100-150 mm/mes
        # Escala según altitud (más húmedo en media-baja)
        factor_altitud = 1.0 if est["altitud"] >= 3600 else 1.3
        mu_log    = np.log(90 * factor_altitud * precip_seasonal)
        sigma_log = 0.5
        precip_base = rng.lognormal(mu_log, sigma_log)
        precipitacion = np.clip(precip_base, 0, 2000)

        # Cobertura vegetal (%)
        # Tendencia negativa leve -0.05%/año + ruido
        cob_base   = 78.0 if est["altitud"] >= 3600 else 72.0
        cobertura  = (
            cob_base
            - 0.05 / 12 * t          # pérdida gradual
            + 2 * np.sin(2 * np.pi * t / 12)  # variación anual
            + rng.normal(0, 1.5, n_meses)
        )
        cobertura = np.clip(cobertura, 30, 100)

        for i, fecha in enumerate(fechas):
            registros.append({
                "fecha":        fecha,
                "estacion":     nombre,
                "altitud":      est["altitud"],
                "temperatura":  round(float(temperatura[i]), 2),
                "precipitacion": round(float(precipitacion[i]), 1),
                "cobertura_vegetal": round(float(cobertura[i]), 1),
            })

    df = pd.DataFrame(registros)
    logger.info("Datos sintéticos generados: %d registros (%d estaciones × %d meses)",
                len(df), len(ESTACIONES), n_meses)
    logger.info("Temperatura media global: %.2f°C | std: %.2f",
                df["temperatura"].mean(), df["temperatura"].std())
    logger.info("Precipitación media: %.1f mm/mes | máx: %.1f",
                df["precipitacion"].mean(), df["precipitacion"].max())
    logger.info("Cobertura vegetal media: %.1f%%", df["cobertura_vegetal"].mean())

    out_path = OUTPUT / "paramos_datos_sinteticos.csv"
    df.to_csv(out_path, index=False)
    logger.info("Datos guardados: %s", out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar_paramos(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='paramos')."""
    logger.info("--- Validación de dominio (páramos) ---")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df, date_col="fecha", linea_tematica="paramos")
        logger.info(report.summary())
        resultados = {
            "n_rows": report.n_rows,
            "n_cols": report.n_cols,
            "missing": report.missing,
            "duplicates_exact": report.duplicates_exact,
            "range_violations": {
                k: {kk: vv for kk, vv in v.items() if kk != "range"}
                for k, v in report.range_violations.items()
            },
            "has_issues": report.has_issues(),
        }
        if not report.has_issues():
            logger.info("Validación: sin problemas detectados.")
        else:
            logger.warning("Validación: se detectaron problemas. Ver reporte.")
    except Exception as e:
        logger.warning("Validación skipped: %s", e)

    out_path = OUTPUT / "paramos_validacion.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Validación guardada: %s", out_path.name)
    return resultados


# ===========================================================================
# 3. EDA
# ===========================================================================

def eda_paramos(df: pd.DataFrame) -> None:
    """EDA por estación y estacionalidad mensual."""
    logger.info("--- EDA Páramos ---")

    for est in df["estacion"].unique():
        sub = df[df["estacion"] == est]
        logger.info("Estación %s (alt=%dm): T=%.2f°C | P=%.1fmm | Cob=%.1f%%",
                    est,
                    int(sub["altitud"].iloc[0]),
                    sub["temperatura"].mean(),
                    sub["precipitacion"].mean(),
                    sub["cobertura_vegetal"].mean())

    # Estacionalidad mensual (todas las estaciones)
    mensual = df.groupby(df["fecha"].dt.month).agg(
        temp_media=("temperatura", "mean"),
        precip_media=("precipitacion", "mean"),
        cob_media=("cobertura_vegetal", "mean"),
    ).round(2)
    logger.info("Estacionalidad mensual (promedio 3 estaciones):")
    for mes, row in mensual.iterrows():
        logger.info("  Mes %02d: T=%.2f°C | P=%.1fmm | Cob=%.1f%%",
                    mes, row["temp_media"], row["precip_media"], row["cob_media"])


# ===========================================================================
# 4. TENDENCIA TEMPERATURA — MANN-KENDALL
# ===========================================================================

def tendencia_temperatura(df: pd.DataFrame) -> dict:
    """Mann-Kendall sobre temperatura de cada estación (esperamos tendencia positiva)."""
    logger.info("--- Tendencia de temperatura (Mann-Kendall) ---")
    resultados: dict = {}

    for est in df["estacion"].unique():
        serie = (
            df[df["estacion"] == est]
            .set_index("fecha")["temperatura"]
            .asfreq("MS")
            .sort_index()
        )
        try:
            from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
            mk = mann_kendall(serie)
            ss = sens_slope(serie)
            slope_anual = ss["slope"] * 12
            resultados[est] = {
                "tendencia": mk.get("trend", "unknown"),
                "p_value": round(float(mk.get("pval", 1.0)), 6),
                "significativo": mk.get("pval", 1.0) < 0.05,
                "tau": round(float(mk.get("tau", 0.0)), 4),
                "sen_slope_por_mes": round(float(ss["slope"]), 6),
                "sen_slope_por_anio": round(float(slope_anual), 4),
            }
            mk_r = resultados[est]
            logger.info("  %s: tendencia=%s | p=%.6f | %s | slope=%.4f°C/año",
                        est,
                        mk_r["tendencia"],
                        mk_r["p_value"],
                        "SIGNIFICATIVO" if mk_r["significativo"] else "no signif.",
                        mk_r["sen_slope_por_anio"])
        except Exception as e:
            logger.warning("Mann-Kendall para %s falló: %s", est, e)

    out_path = OUTPUT / "paramos_tendencia.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resultados de tendencia guardados: %s", out_path.name)
    return resultados


# ===========================================================================
# 5. ENSO LAGGED
# ===========================================================================

def _generar_oni_sintetico_paramos() -> "pd.DataFrame":
    """ONI sintético AR(1) para el período de datos de páramos (2004-2023)."""
    import pandas as _pd
    import numpy as _np
    from estadistica_ambiental.config import ENSO_THRESHOLDS
    rng = _np.random.default_rng(42)
    n = N_ANIOS * 12
    phi = 0.85
    sigma = 0.6 * _np.sqrt(1 - phi ** 2)
    oni_vals = _np.zeros(n)
    oni_vals[0] = rng.normal(0, 0.6)
    for t in range(1, n):
        oni_vals[t] = phi * oni_vals[t - 1] + rng.normal(0, sigma)
    oni_vals = _np.clip(oni_vals, -2.5, 2.5)
    fechas = _pd.date_range(INICIO, periods=n, freq="MS")
    fase = _pd.Series(oni_vals).apply(lambda v: (
        "niño" if v >= ENSO_THRESHOLDS["nino"] else
        "niña" if v <= ENSO_THRESHOLDS["nina"] else "neutro"
    ))
    intensidad = _pd.Series(oni_vals).apply(lambda v: (
        "fuerte" if v >= ENSO_THRESHOLDS["nino_fuerte"] or v <= ENSO_THRESHOLDS["nina_fuerte"]
        else ("moderado" if v >= ENSO_THRESHOLDS["nino"] or v <= ENSO_THRESHOLDS["nina"]
              else "neutro")
    ))
    return _pd.DataFrame({
        "fecha": fechas,
        "oni": _np.round(oni_vals, 2),
        "fase": fase.values,
        "intensidad": intensidad.values,
    })


def aplicar_enso_lag(df: pd.DataFrame) -> pd.DataFrame:
    """enso_lagged(df, oni, linea_tematica='paramos') — lag=2 meses."""
    logger.info("--- ENSO lagged (lag=2 meses para páramos) ---")
    try:
        from estadistica_ambiental.features.climate import load_oni, enso_lagged

        oni = load_oni()
        if oni.empty:
            logger.warning("ONI descargado vacío — usando ONI sintético para páramos.")
            oni = _generar_oni_sintetico_paramos()

        df_enso = enso_lagged(
            df.copy(),
            oni_df=oni,
            date_col="fecha",
            linea_tematica="paramos",
        )
        lag_col = [c for c in df_enso.columns if c.startswith("oni_lag")]
        if lag_col:
            lag_stats = df_enso[lag_col[0]].describe()
            logger.info("ONI lag aplicado (%s): media=%.3f | std=%.3f",
                        lag_col[0], lag_stats["mean"], lag_stats["std"])
        logger.info("Columnas ENSO añadidas: %s",
                    [c for c in df_enso.columns if "lag" in c or "enso" in c.lower()])
        return df_enso
    except Exception as e:
        logger.warning("ENSO lagged skipped: %s — continuando sin covariable ENSO.", e)
        return df


# ===========================================================================
# 6. ESTACIONARIEDAD
# ===========================================================================

def estacionariedad_paramos(df: pd.DataFrame, estacion: str) -> dict:
    """ADF + KPSS sobre temperatura de la estación media."""
    logger.info("--- Estacionariedad temperatura (%s) ---", estacion)
    serie = (
        df[df["estacion"] == estacion]
        .set_index("fecha")["temperatura"]
        .asfreq("MS")
        .sort_index()
        .dropna()
    )
    resultados: dict = {}
    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf  = adf_test(serie)
        kpss = kpss_test(serie)
        resultados = {
            "adf_stationary": bool(adf.get("stationary", False)),
            "adf_pvalue": round(float(adf.get("pval", 1.0)), 6),
            "kpss_stationary": bool(kpss.get("stationary", True)),
            "kpss_pvalue": round(float(kpss.get("pval", 0.1)), 6),
        }
        logger.info("ADF: %s (p=%.6f) | KPSS: %s (p=%.6f)",
                    "estacionaria" if resultados["adf_stationary"] else "NO estacionaria",
                    resultados["adf_pvalue"],
                    "estacionaria" if resultados["kpss_stationary"] else "NO estacionaria",
                    resultados["kpss_pvalue"])
    except Exception as e:
        logger.warning("Estacionariedad skipped: %s", e)
    return resultados


# ===========================================================================
# 7. DESCOMPOSICIÓN STL
# ===========================================================================

def descomposicion_stl(df: pd.DataFrame, estacion: str) -> pd.DataFrame:
    """STL period=12 sobre temperatura de la estación focal."""
    logger.info("--- STL temperatura (%s) ---", estacion)
    serie = (
        df[df["estacion"] == estacion]
        .set_index("fecha")["temperatura"]
        .asfreq("MS")
        .sort_index()
    )
    try:
        from estadistica_ambiental.descriptive.temporal import decompose_stl
        stl = decompose_stl(serie, period=12, robust=True)
        logger.info("STL — trend std: %.4f | seasonal amp: %.4f | residual std: %.4f",
                    stl["trend"].std(), stl["seasonal"].abs().mean(), stl["residual"].std())

        out_path = OUTPUT / "paramos_stl.csv"
        stl.to_csv(out_path)
        logger.info("STL guardado: %s", out_path.name)
        return stl
    except Exception as e:
        logger.warning("STL skipped: %s", e)
        return pd.DataFrame()


# ===========================================================================
# 8 & 9. SARIMA BASELINE + BACKTESTING
# ===========================================================================

def modelado_predictivo(df: pd.DataFrame, estacion: str) -> dict:
    """SARIMA(1,0,1)(1,1,1,12) sobre temperatura + walk-forward backtesting."""
    logger.info("--- Modelado predictivo temperatura (%s) ---", estacion)
    serie = (
        df[df["estacion"] == estacion]
        .set_index("fecha")["temperatura"]
        .asfreq("MS")
        .sort_index()
        .dropna()
    )
    logger.info("Serie temperatura: %d meses (%s → %s)",
                len(serie), serie.index.min().date(), serie.index.max().date())
    resultados: dict = {}

    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        # SARIMA(1,0,1)(1,1,1,12) — temperatura anual estacional
        model = SARIMAXModel(
            order=(1, 0, 1),
            seasonal_order=(1, 1, 1, 12),
        )

        logger.info("Entrenando SARIMA(1,0,1)(1,1,1,12) — walk-forward (5 folds, horizon=6 meses)...")
        result = walk_forward(
            model=model,
            y=serie,
            horizon=6,
            n_splits=5,
            domain="general",
        )

        metrics = result["metrics"]
        resultados["sarima_metrics"] = metrics
        logger.info("SARIMA Páramos — RMSE=%.4f | MAE=%.4f | R2=%.4f",
                    metrics.get("rmse", float("nan")),
                    metrics.get("mae", float("nan")),
                    metrics.get("r2", float("nan")))

        # Guardar folds
        if not result["folds"].empty:
            fold_path = OUTPUT / "paramos_backtesting.csv"
            result["folds"].to_csv(fold_path, index=False)
            logger.info("Métricas por fold guardadas: %s", fold_path.name)

        # Pronóstico 12 meses
        logger.info("Generando pronóstico de 12 meses...")
        model_full = SARIMAXModel(order=(1, 0, 1), seasonal_order=(1, 1, 1, 12))
        model_full.fit(serie)
        forecast_vals = model_full.predict(12)
        forecast_idx  = pd.date_range(
            start=serie.index.max() + pd.DateOffset(months=1),
            periods=12, freq="MS",
        )
        forecast = pd.Series(forecast_vals, index=forecast_idx, name="temperatura_forecast")
        forecast = forecast.clip(-5.0, 16.0)

        forecast_path = OUTPUT / "paramos_forecast.csv"
        forecast.to_csv(forecast_path, header=True)
        logger.info("Pronóstico 12m guardado: %s (media=%.2f°C)", forecast_path.name, forecast.mean())
        resultados["forecast_12m_media"] = round(float(forecast.mean()), 3)
        resultados["forecast_12m_max"]   = round(float(forecast.max()), 3)

        # Reporte HTML
        try:
            from estadistica_ambiental.reporting.forecast_report import forecast_report
            preds_df  = result.get("predictions", pd.DataFrame())
            preds_arr = (preds_df["predicted"].values
                         if not preds_df.empty and "predicted" in preds_df.columns
                         else np.array([]))
            report_path = OUTPUT / "forecast_paramos.html"
            forecast_report(
                y_true=serie.iloc[-len(preds_arr):] if len(preds_arr) else serie.iloc[-24:],
                predictions={"SARIMA(1,0,1)(1,1,1,12)": preds_arr if len(preds_arr) else forecast.values},
                metrics={"SARIMA(1,0,1)(1,1,1,12)": metrics},
                output=str(report_path),
                title="Pronóstico Temperatura — Páramos Colombia",
                variable_name="Temperatura",
                unit="°C",
            )
            logger.info("Reporte HTML guardado: %s", report_path.name)
        except Exception as e:
            logger.warning("forecast_report skipped: %s", e)

    except Exception as e:
        logger.error("Modelado predictivo páramos falló: %s", e)
        import traceback
        traceback.print_exc()

    return resultados


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — Páramos | Temperatura, Precipitación, Cobertura Vegetal")
    logger.info("Datos: SINTÉTICOS (20 años, 3 estaciones)")
    logger.info("=" * 65)

    # 1. Generar datos
    try:
        df = generar_datos_paramos()
    except Exception as e:
        logger.error("Generación de datos falló: %s", e)
        return

    # 2. Validación
    try:
        val = validar_paramos(df)
    except Exception as e:
        logger.warning("Validación falló: %s", e)
        val = {}

    # 3. EDA
    try:
        eda_paramos(df)
    except Exception as e:
        logger.warning("EDA falló: %s", e)

    # 4. Tendencia temperatura
    try:
        tend = tendencia_temperatura(df)
    except Exception as e:
        logger.warning("Tendencia falló: %s", e)
        tend = {}

    # 5. ENSO lagged
    try:
        df_enso = aplicar_enso_lag(df)
    except Exception as e:
        logger.warning("ENSO lag falló: %s", e)
        df_enso = df

    # Estación focal para análisis univariado
    estacion_focal = ESTACIONES[1]["nombre"]  # Sumapaz_Media

    # 6. Estacionariedad
    try:
        est = estacionariedad_paramos(df, estacion_focal)
    except Exception as e:
        logger.warning("Estacionariedad falló: %s", e)
        est = {}

    # 7. STL
    try:
        stl = descomposicion_stl(df, estacion_focal)
    except Exception as e:
        logger.warning("STL falló: %s", e)
        stl = pd.DataFrame()

    # 8 & 9. Modelado predictivo
    try:
        pred = modelado_predictivo(df, estacion_focal)
    except Exception as e:
        logger.warning("Modelado predictivo falló: %s", e)
        pred = {}

    # Resumen final
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Páramos")
    logger.info("  Estaciones: %s", [e["nombre"] for e in ESTACIONES])
    logger.info("  Período: %s → %s",
                df["fecha"].min().date(), df["fecha"].max().date())
    logger.info("  Temperatura media global: %.2f°C", df["temperatura"].mean())
    logger.info("  Precipitación media: %.1f mm/mes", df["precipitacion"].mean())
    logger.info("  Cobertura vegetal media: %.1f%%", df["cobertura_vegetal"].mean())

    if tend:
        for est_nom, mk_r in tend.items():
            logger.info("  Tendencia T (%s): %s (p=%.6f, %.4f°C/año)%s",
                        est_nom,
                        mk_r.get("tendencia", "?"),
                        mk_r.get("p_value", 1.0),
                        mk_r.get("sen_slope_por_anio", 0.0),
                        " [SIGNIF.]" if mk_r.get("significativo") else "")

    sarima = pred.get("sarima_metrics", {})
    if sarima:
        logger.info("  SARIMA RMSE: %.4f°C | MAE: %.4f°C | R2: %.4f",
                    sarima.get("rmse", float("nan")),
                    sarima.get("mae", float("nan")),
                    sarima.get("r2", float("nan")))

    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Páramos completada.")


if __name__ == "__main__":
    main()
