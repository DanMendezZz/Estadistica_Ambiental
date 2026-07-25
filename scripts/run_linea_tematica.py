"""Ejecuta el ciclo estadístico completo para cualquier línea temática ambiental.

Uso:
    python scripts/run_linea_tematica.py --linea oferta_hidrica
    python scripts/run_linea_tematica.py --linea paramos --modelos sarima,xgboost
    python scripts/run_linea_tematica.py --linea calidad_aire --datos data/raw/pm25.csv
    python scripts/run_linea_tematica.py --list

Reemplaza los 13 scripts fase8_*_sintetico.py manteniendo el mismo flujo:
  validar → EDA → ENSO → inferencial → predictiva → reporte HTML.
Para el showcase con datos reales (PM2.5 CAR), usar fase8_calidad_aire.py.
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_linea_tematica")

ROOT   = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Configuración por línea temática
# ---------------------------------------------------------------------------

@dataclass
class LineaConfig:
    variable: str
    unidad: str
    domain: str            # "general" | "hydrology" | "air_quality"
    frecuencia: str        # frecuencia de síntesis: "D" diaria, "ME" mensual
    usa_enso: bool
    modelos_default: List[str]
    dist: str = "normal"   # "normal" | "lognormal"
    clip_min: float = 0.0
    clip_max: float = 1e9


LINEAS: dict[str, LineaConfig] = {
    "calidad_aire": LineaConfig(
        variable="pm25", unidad="µg/m³", domain="air_quality",
        frecuencia="D", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.0, clip_max=500.0,
    ),
    "oferta_hidrica": LineaConfig(
        variable="caudal", unidad="m³/s", domain="hydrology",
        frecuencia="D", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.5, clip_max=50000.0,
    ),
    "recurso_hidrico": LineaConfig(
        variable="od", unidad="mg/L", domain="hydrology",
        frecuencia="D", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="normal", clip_min=0.0, clip_max=20.0,
    ),
    "paramos": LineaConfig(
        variable="temperatura", unidad="°C", domain="general",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="normal", clip_min=-5.0, clip_max=20.0,
    ),
    "humedales": LineaConfig(
        variable="nivel_agua", unidad="m", domain="hydrology",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="normal", clip_min=0.0, clip_max=10.0,
    ),
    "cambio_climatico": LineaConfig(
        variable="temperatura", unidad="°C", domain="general",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="normal", clip_min=-10.0, clip_max=40.0,
    ),
    "gestion_riesgo": LineaConfig(
        variable="precipitacion", unidad="mm", domain="general",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.0, clip_max=1500.0,
    ),
    "pomca": LineaConfig(
        variable="caudal", unidad="m³/s", domain="hydrology",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.5, clip_max=10000.0,
    ),
    "pueea": LineaConfig(
        variable="consumo_agua", unidad="m³", domain="hydrology",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.0, clip_max=1e6,
    ),
    "rondas_hidricas": LineaConfig(
        variable="caudal", unidad="m³/s", domain="hydrology",
        frecuencia="ME", usa_enso=True, modelos_default=["sarima", "xgboost"],
        dist="lognormal", clip_min=0.5, clip_max=5000.0,
    ),
    "areas_protegidas": LineaConfig(
        variable="cobertura_ha", unidad="ha", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=0.0, clip_max=1e6,
    ),
    "predios_conservacion": LineaConfig(
        variable="ndvi", unidad="", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=-1.0, clip_max=1.0,
    ),
    "ordenamiento_territorial": LineaConfig(
        variable="superficie_km2", unidad="km²", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=0.0, clip_max=1e5,
    ),
    "sistemas_informacion_ambiental": LineaConfig(
        variable="n_registros", unidad="", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=0.0, clip_max=1e6,
    ),
    "direccion_directiva": LineaConfig(
        variable="indicador", unidad="", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=0.0, clip_max=100.0,
    ),
    "geoespacial": LineaConfig(
        variable="valor", unidad="", domain="general",
        frecuencia="ME", usa_enso=False, modelos_default=["sarima", "random_forest"],
        dist="normal", clip_min=-1e6, clip_max=1e6,
    ),
}


# ---------------------------------------------------------------------------
# Datos sintéticos genéricos
# ---------------------------------------------------------------------------

def generar_sinteticos(cfg: LineaConfig, n_anios: int = 10) -> pd.DataFrame:
    """Serie temporal sintética genérica: distribución + estacionalidad + tendencia + AR(1)."""
    rng  = np.random.default_rng(42)
    freq = "D" if cfg.frecuencia == "D" else "ME"
    n    = n_anios * (365 if freq == "D" else 12)
    fechas = pd.date_range("2014-01-01", periods=n, freq=freq)
    t = np.arange(n)

    period = 365.0 if freq == "D" else 12.0
    seasonal = np.sin(2 * np.pi * t / period)

    # Ruido AR(1) ρ=0.8
    phi, sigma_eps = 0.8, np.sqrt(1 - 0.64)
    noise = np.zeros(n)
    noise[0] = rng.standard_normal()
    for i in range(1, n):
        noise[i] = phi * noise[i - 1] + rng.standard_normal() * sigma_eps

    trend = np.linspace(0, 0.5 * n_anios, n)

    if cfg.dist == "lognormal":
        vals = np.exp(noise * 0.5 + 2) * (1 + 0.3 * seasonal) + trend
    else:
        vals = noise * 5 + 20 + 3 * seasonal + trend

    vals = np.clip(vals, cfg.clip_min, cfg.clip_max).round(3)
    vals[rng.choice(n, size=int(n * 0.03), replace=False)] = np.nan

    return pd.DataFrame({"fecha": fechas, cfg.variable: vals})


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(linea: str, cfg: LineaConfig, df: pd.DataFrame, modelos: List[str]) -> None:
    var = cfg.variable

    # 1. Validación
    try:
        from estadistica_ambiental.io.validators import validate
        rep = validate(df, date_col="fecha", linea_tematica=linea)
        logger.info("Validación: %s", "OK" if not rep.has_issues() else "con issues")
    except Exception as e:
        logger.warning("Validación skipped: %s", e)

    # 2. Serie temporal
    serie = df.set_index("fecha")[var].sort_index().astype(float)
    n_raw = len(serie)
    serie = serie.dropna()
    logger.info("Serie %s: %d obs (%.1f%% válidas) | %s → %s",
                var, len(serie), len(serie) / n_raw * 100,
                serie.index.min().date(), serie.index.max().date())

    # 3. ENSO
    if cfg.usa_enso:
        try:
            from estadistica_ambiental.features.climate import enso_lagged, load_oni
            oni = load_oni()
            if not oni.empty:
                df = enso_lagged(df, oni, date_col="fecha", linea_tematica=linea)
                enso_cols = [c for c in df.columns if "oni" in c]
                logger.info("ENSO aplicado: %s", enso_cols)
        except Exception as e:
            logger.warning("ENSO skipped: %s", e)

    # 4. Estadística inferencial — serie mensual (ADR-004: ADF+KPSS pre-ARIMA)
    serie_m = serie.resample("ME").mean().dropna() if cfg.frecuencia == "D" else serie
    infres: dict = {}

    try:
        from estadistica_ambiental.inference.trend import mann_kendall
        mk = mann_kendall(serie_m)
        infres["mann_kendall"] = {
            "tendencia": mk.get("trend"),
            "p_value": round(float(mk.get("pval", 1.0)), 4),
            "significativo": mk.get("pval", 1.0) < 0.05,
        }
        logger.info("Mann-Kendall: %s (p=%.4f)", mk.get("trend"), mk.get("pval", 1.0))
    except Exception as e:
        logger.warning("Mann-Kendall skipped: %s", e)

    try:
        from estadistica_ambiental.inference.stationarity import adf_test, kpss_test
        adf   = adf_test(serie_m)
        kpss_r = kpss_test(serie_m)
        infres["estacionariedad"] = {
            "adf_stationary":  bool(adf.get("stationary")),
            "adf_pvalue":      round(float(adf.get("pval", 1.0)), 4),
            "kpss_stationary": bool(kpss_r.get("stationary")),
            "kpss_pvalue":     round(float(kpss_r.get("pval", 0.1)), 4),
        }
        logger.info("ADF: %s | KPSS: %s",
                    "estacionaria" if adf.get("stationary") else "no-estacionaria",
                    "estacionaria" if kpss_r.get("stationary") else "no-estacionaria")
    except Exception as e:
        logger.warning("ADF/KPSS skipped: %s", e)

    try:
        from estadistica_ambiental.inference.intervals import exceedance_report
        rep_exc = exceedance_report(serie, variable=var)
        if not rep_exc.empty:
            logger.info("Excedencias normativas detectadas para '%s'", var)
    except Exception as e:
        logger.warning("exceedance_report skipped: %s", e)

    out_inf = OUTPUT / f"inferencial_{linea}.json"
    with open(out_inf, "w", encoding="utf-8") as f:
        json.dump(infres, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_inf.name)

    # 5. Predictiva — walk-forward por modelo
    from estadistica_ambiental.evaluation.backtesting import walk_forward
    from estadistica_ambiental.predictive.registry import get_model

    bt_results: dict = {}
    for nombre in modelos:
        try:
            model = get_model(nombre)
            res   = walk_forward(model, serie_m, horizon=6, n_splits=4, domain=cfg.domain)
            bt_results[nombre] = res
            m = res["metrics"]
            logger.info("%s → RMSE=%.4f | MAE=%.4f | R²=%.4f",
                        nombre.upper(),
                        m.get("rmse", float("nan")),
                        m.get("mae",  float("nan")),
                        m.get("r2",   float("nan")))
        except Exception as e:
            logger.warning("Modelo '%s' skipped: %s", nombre, e)

    if not bt_results:
        logger.warning("Ningún modelo completó el backtesting.")
        return

    # 6. Ranking
    try:
        from estadistica_ambiental.evaluation.comparison import rank_models
        ranking = rank_models(bt_results, domain=cfg.domain)
        ranking.to_csv(OUTPUT / f"ranking_{linea}.csv")
        logger.info("Mejor modelo: %s", ranking.index[0])
    except Exception as e:
        logger.warning("rank_models skipped: %s", e)

    # 7. Reporte HTML de pronóstico
    try:
        from estadistica_ambiental.reporting.forecast_report import forecast_report
        first = list(bt_results.keys())[0]
        preds_df = bt_results[first].get("predictions", pd.DataFrame())
        if not preds_df.empty and "predicted" in preds_df.columns:
            y_true = preds_df["actual"].values
            preds  = {
                k: bt_results[k]["predictions"]["predicted"].values
                for k in bt_results
                if "predicted" in bt_results[k].get("predictions", pd.DataFrame()).columns
            }
            metrics_dict = {k: bt_results[k]["metrics"] for k in bt_results}
            forecast_report(
                y_true=pd.Series(y_true, name=var),
                predictions=preds,
                metrics=metrics_dict,
                output=str(OUTPUT / f"forecast_{linea}.html"),
                title=f"Pronóstico {linea.replace('_', ' ').title()} — {var} ({cfg.unidad})",
                variable_name=var.title(),
                unit=cfg.unidad,
            )
            logger.info("Reporte HTML guardado: forecast_%s.html", linea)
    except Exception as e:
        logger.warning("forecast_report skipped: %s", e)

    logger.info("Salidas en: %s", OUTPUT)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Ciclo estadístico completo para una línea temática ambiental.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python scripts/run_linea_tematica.py --linea oferta_hidrica\n"
            "  python scripts/run_linea_tematica.py --linea paramos --modelos sarima,xgboost\n"
            "  python scripts/run_linea_tematica.py --linea calidad_aire "
            "--datos data/raw/pm25.csv\n"
        ),
    )
    p.add_argument("--linea",   metavar="LINEA",
                   help="Línea temática (ver --list)")
    p.add_argument("--datos",   metavar="RUTA",
                   help="CSV o parquet con datos reales. Sin este flag genera sintéticos.")
    p.add_argument("--modelos", metavar="LISTA",
                   help="Modelos separados por coma: sarima,xgboost,random_forest,ets,prophet")
    p.add_argument("--list",    action="store_true",
                   help="Listar líneas temáticas disponibles y salir.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.list:
        print("Líneas temáticas disponibles:\n")
        for nombre, cfg in LINEAS.items():
            print(f"  {nombre:<45} variable={cfg.variable:<20} domain={cfg.domain}")
        return

    if not args.linea:
        print("Error: especificar --linea o usar --list para ver opciones.")
        raise SystemExit(1)

    linea = args.linea.lower().strip()
    if linea not in LINEAS:
        print(f"Error: línea '{linea}' no reconocida. Usar --list.")
        raise SystemExit(1)

    cfg = LINEAS[linea]

    logger.info("=" * 65)
    logger.info("CICLO ESTADÍSTICO — %s | %s (%s)", linea.upper(), cfg.variable, cfg.unidad)
    logger.info("Dominio: %s | Frecuencia base: %s", cfg.domain, cfg.frecuencia)
    logger.info("=" * 65)

    # Cargar datos
    if args.datos:
        ruta = Path(args.datos)
        if not ruta.exists():
            logger.error("Archivo no encontrado: %s", ruta)
            raise SystemExit(1)
        df = (pd.read_parquet(ruta) if ruta.suffix == ".parquet"
              else pd.read_csv(ruta, parse_dates=["fecha"]))
        logger.info("Datos reales: %d filas desde %s", len(df), ruta.name)
    else:
        logger.info("Sin --datos: generando datos sintéticos...")
        df = generar_sinteticos(cfg)

    modelos = (
        [m.strip() for m in args.modelos.split(",")]
        if args.modelos
        else cfg.modelos_default
    )

    run_pipeline(linea, cfg, df, modelos)

    logger.info("=" * 65)
    logger.info("Completado: %s", linea)
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
