"""
Fase 8 — Comparación multi-modelo PM2.5 | Red CAR Cundinamarca

Modelos comparados:
  1. SARIMA(p,d,q)(P,D,Q,7) — orden optimizado con Optuna (Bayesian TPE)
  2. XGBoost — lags temporales + features de calendario
  3. Random Forest — mismo feature set que XGBoost

Evaluación: walk-forward backtesting | domain='air_quality' | pollutant='pm25'
Ranking: rank_models con pesos rmse=0.30, nrmse=0.20, mae=0.20, hit_rate_ica=0.30
Post-procesamiento: corrección de sesgo estacional sobre mejor modelo

Salidas en data/output/fase8/:
  - ranking_modelos_mochuelo.csv
  - anomalias_residuos.csv
  - forecast_multimodelo.html
  - ica_forecast_30d.csv          (categorías ICA del pronóstico)
"""
from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fase8_multi")

ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

PARQUET   = DATA / "raw" / "calidad_aire_CAR_2016_2026.parquet"
ESTACION  = "BOGOTA RURAL - MOCHUELO"
POLLUTANT = "pm25"
HORIZONTE = 7    # días a predecir por fold
N_FOLDS   = 5
N_TRIALS  = 30   # trials Optuna para optimizar SARIMA


# ---------------------------------------------------------------------------
# 1. CARGA
# ---------------------------------------------------------------------------

def cargar() -> pd.Series:
    logger.info("Cargando datos: %s", ESTACION)
    df = pd.read_parquet(PARQUET)
    df = df[df["estacion"] == ESTACION].sort_values("fecha")
    serie = df.set_index("fecha")["pm25"].resample("D").mean().dropna()
    # Últimos 2 años para velocidad de comparación
    serie = serie.last("730D")
    logger.info("Serie: %d días | %s → %s | media=%.1f µg/m³",
                len(serie), serie.index.min().date(), serie.index.max().date(), serie.mean())
    return serie


# ---------------------------------------------------------------------------
# 2. SARIMA CON OPTIMIZACIÓN BAYESIANA
# ---------------------------------------------------------------------------

def optimizar_sarima(serie: pd.Series) -> dict:
    """Encuentra el mejor orden SARIMA con Optuna TPE."""
    logger.info("Optimizando SARIMA con Optuna (%d trials)...", N_TRIALS)
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        from estadistica_ambiental.predictive.classical import SARIMAXModel

        def objetivo(trial):
            p = trial.suggest_int("p", 0, 3)
            d = trial.suggest_int("d", 0, 1)
            q = trial.suggest_int("q", 0, 3)
            P = trial.suggest_int("P", 0, 2)
            D = trial.suggest_int("D", 0, 1)
            Q = trial.suggest_int("Q", 0, 2)
            try:
                model = SARIMAXModel(order=(p, d, q), seasonal_order=(P, D, Q, 7))
                model.fit(serie)
                return model.aic
            except Exception:
                return 1e6

        study = optuna.create_study(direction="minimize",
                                    sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objetivo, n_trials=N_TRIALS, n_jobs=1)
        bp = study.best_params
        best_order = (bp["p"], bp["d"], bp["q"])
        best_seasonal = (bp["P"], bp["D"], bp["Q"], 7)
        logger.info("Mejor SARIMA: order=%s seasonal=%s AIC=%.1f",
                    best_order, best_seasonal, study.best_value)
        return {"order": best_order, "seasonal_order": best_seasonal, "aic": study.best_value}
    except Exception as e:
        logger.warning("Optimización Optuna falló (%s); usando (1,1,1)(1,1,1,7)", e)
        return {"order": (1, 1, 1), "seasonal_order": (1, 1, 1, 7), "aic": None}


# ---------------------------------------------------------------------------
# 3. FEATURE ENGINEERING PARA ML
# ---------------------------------------------------------------------------

def build_features(serie: pd.Series, lags: list[int] = None) -> pd.DataFrame:
    """Construye DataFrame de features temporales para XGBoost/RF."""
    if lags is None:
        lags = [1, 2, 3, 7, 14, 30]
    df = serie.to_frame("pm25")
    for lag in lags:
        df[f"lag_{lag}"] = df["pm25"].shift(lag)
    df["dow"]     = df.index.dayofweek
    df["mes"]     = df.index.month
    df["semana"]  = df.index.isocalendar().week.astype(int)
    df["trimestre"] = df.index.quarter
    # Rolling stats (usando shift para evitar leakage)
    df["roll7_mean"]  = df["pm25"].shift(1).rolling(7,  min_periods=3).mean()
    df["roll14_std"]  = df["pm25"].shift(1).rolling(14, min_periods=7).std()
    df["roll30_mean"] = df["pm25"].shift(1).rolling(30, min_periods=14).mean()
    return df.dropna()


# ---------------------------------------------------------------------------
# 4. WALK-FORWARD PERSONALIZADO PARA ML
# ---------------------------------------------------------------------------

def wf_ml(model_cls, serie: pd.Series, model_kwargs: dict,
          n_splits: int = N_FOLDS, horizon: int = HORIZONTE) -> dict:
    """Walk-forward expanding para modelos ML con features temporales."""
    from estadistica_ambiental.evaluation.metrics import evaluate

    df_full = build_features(serie)
    feature_cols = [c for c in df_full.columns if c != "pm25"]
    n = len(df_full)
    min_train = max(int(n * 0.5), horizon * 5)
    step = max(1, (n - min_train) // n_splits)

    folds, all_actual, all_pred = [], [], []

    for fold_idx in range(n_splits):
        train_end = min_train + fold_idx * step
        test_end  = min(train_end + horizon, n)
        if test_end > n or train_end >= n:
            break

        train_df = df_full.iloc[:train_end]
        test_df  = df_full.iloc[train_end:test_end]

        X_train, y_train = train_df[feature_cols].values, train_df["pm25"].values
        X_test,  y_test  = test_df[feature_cols].values,  test_df["pm25"].values

        try:
            mdl = model_cls(**model_kwargs)
            mdl.fit(X_train, y_train)
            preds = mdl.predict(X_test).clip(min=0)
            m = evaluate(y_test, preds, domain="air_quality", pollutant=POLLUTANT)
            folds.append({"fold": fold_idx, **m})
            all_actual.extend(y_test)
            all_pred.extend(preds)
        except Exception as e:
            logger.warning("Fold %d ML falló: %s", fold_idx, e)

    if not folds:
        return {"metrics": {}, "predictions": pd.DataFrame()}

    avg = pd.DataFrame(folds).drop(columns=["fold"]).mean().round(4).to_dict()
    preds_df = pd.DataFrame({"actual": all_actual, "predicted": all_pred})
    logger.info("%s WF: RMSE=%.3f | MAE=%.3f | hit_rate_ica=%.1f%%",
                model_cls.__name__, avg.get("rmse", np.nan),
                avg.get("mae", np.nan), avg.get("hit_rate_ica", np.nan))
    return {"metrics": avg, "predictions": preds_df}


# ---------------------------------------------------------------------------
# 5. PIPELINE PRINCIPAL
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("FASE 8 — Comparación Multi-Modelo PM2.5 | %s", ESTACION)
    logger.info("=" * 60)

    serie = cargar()
    resultados: dict[str, dict] = {}

    # ── 5.1 SARIMA optimizado ────────────────────────────────────────────────
    logger.info("--- Modelo 1: SARIMA optimizado ---")
    sarima_config = optimizar_sarima(serie)
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.evaluation.backtesting import walk_forward

        sarima = SARIMAXModel(
            order=sarima_config["order"],
            seasonal_order=sarima_config["seasonal_order"],
        )
        res_sarima = walk_forward(
            model=sarima, y=serie,
            horizon=HORIZONTE, n_splits=N_FOLDS,
            domain="air_quality", pollutant=POLLUTANT,
        )
        resultados["SARIMA_opt"] = res_sarima
        m = res_sarima["metrics"]
        logger.info("SARIMA_opt: RMSE=%.3f | MAE=%.3f | R2=%.3f | hit_rate_ica=%.1f%%",
                    m.get("rmse", np.nan), m.get("mae", np.nan),
                    m.get("r2", np.nan), m.get("hit_rate_ica", np.nan))
    except Exception as e:
        logger.error("SARIMA_opt falló: %s", e)

    # ── 5.2 XGBoost ─────────────────────────────────────────────────────────
    logger.info("--- Modelo 2: XGBoost ---")
    try:
        from xgboost import XGBRegressor
        res_xgb = wf_ml(
            XGBRegressor,
            serie,
            model_kwargs={
                "n_estimators": 200, "max_depth": 5,
                "learning_rate": 0.05, "subsample": 0.8,
                "colsample_bytree": 0.8, "random_state": 42,
                "verbosity": 0,
            },
        )
        resultados["XGBoost"] = res_xgb
    except ImportError:
        logger.warning("xgboost no instalado; skipping")
    except Exception as e:
        logger.error("XGBoost falló: %s", e)

    # ── 5.3 Random Forest ───────────────────────────────────────────────────
    logger.info("--- Modelo 3: Random Forest ---")
    try:
        from sklearn.ensemble import RandomForestRegressor
        res_rf = wf_ml(
            RandomForestRegressor,
            serie,
            model_kwargs={"n_estimators": 200, "max_depth": 8,
                          "random_state": 42, "n_jobs": -1},
        )
        resultados["RandomForest"] = res_rf
    except Exception as e:
        logger.error("RandomForest falló: %s", e)

    # ── 5.4 Ranking multi-criterio ──────────────────────────────────────────
    logger.info("--- Ranking multi-criterio ---")
    if resultados:
        try:
            from estadistica_ambiental.evaluation.comparison import rank_models, select_best
            ranking = rank_models(resultados, domain="air_quality")
            logger.info("Ranking:")
            for modelo in ranking.index:
                r = ranking.loc[modelo]
                logger.info("  #%d %-15s RMSE=%.3f | hit_ica=%.1f%% | score=%.4f",
                            int(r["rank"]), modelo,
                            r.get("rmse", np.nan), r.get("hit_rate_ica", np.nan),
                            r["score"])
            mejor = select_best(resultados, domain="air_quality")
            logger.info("Mejor modelo: %s", mejor)

            rank_path = OUTPUT / "ranking_modelos_mochuelo.csv"
            ranking.to_csv(rank_path)
            logger.info("Ranking guardado: %s", rank_path.name)
        except Exception as e:
            logger.error("Ranking falló: %s", e)
            mejor = next(iter(resultados))

    # ── 5.5 Corrección de sesgo estacional sobre mejor modelo ───────────────
    logger.info("--- Corrección de sesgo estacional ---")
    try:
        from estadistica_ambiental.preprocessing.air_quality import correct_seasonal_bias
        mejor_preds = resultados.get(mejor, {}).get("predictions", pd.DataFrame())
        if not mejor_preds.empty:
            n_pred = len(mejor_preds)
            time_col = pd.Series(serie.index[-n_pred:])
            corregidas, tabla_sesgo = correct_seasonal_bias(
                predictions=pd.Series(mejor_preds["predicted"].values),
                actuals=pd.Series(mejor_preds["actual"].values),
                time_col=time_col,
                by="month",
            )
            sesgo_path = OUTPUT / f"sesgo_estacional_{mejor.lower()}.csv"
            tabla_sesgo.to_csv(sesgo_path, index=False)
            logger.info("Sesgo estacional corregido | tabla guardada: %s", sesgo_path.name)
    except Exception as e:
        logger.warning("Corrección sesgo skipped: %s", e)

    # ── 5.6 Detección de anomalías en residuos ──────────────────────────────
    logger.info("--- Detección de anomalías en residuos ---")
    try:
        from estadistica_ambiental.evaluation.anomaly import detect_anomalies, anomaly_summary
        mejor_preds = resultados.get(mejor, {}).get("predictions", pd.DataFrame())
        if not mejor_preds.empty:
            anom_df = detect_anomalies(
                mejor_preds["actual"].values,
                mejor_preds["predicted"].values,
                threshold=2.5,
            )
            summary = anomaly_summary(anom_df)
            logger.info("Anomalías en residuos: %d/%d (%.1f%%) | umbral=%.4f",
                        summary["n_anomalies"], summary["n_total"],
                        summary["pct_anomalies"], summary["threshold_value"])
            anom_path = OUTPUT / "anomalias_residuos.csv"
            anom_df.to_csv(anom_path)
            logger.info("Anomalías guardadas: %s", anom_path.name)
    except Exception as e:
        logger.warning("Detección anomalías skipped: %s", e)

    # ── 5.7 Pronóstico 30 días con mejor modelo + categorías ICA ────────────
    logger.info("--- Pronóstico 30 días + categorías ICA ---")
    try:
        from estadistica_ambiental.predictive.classical import SARIMAXModel
        from estadistica_ambiental.preprocessing.air_quality import categorize_ica

        model_final = SARIMAXModel(
            order=sarima_config["order"],
            seasonal_order=sarima_config["seasonal_order"],
        )
        model_final.fit(serie)
        forecast_vals = np.clip(model_final.predict(30), 0, None)
        forecast_idx  = pd.date_range(
            serie.index.max() + pd.Timedelta(days=1), periods=30, freq="D"
        )
        forecast_s = pd.Series(forecast_vals, index=forecast_idx, name="pm25_forecast")
        cats = categorize_ica(forecast_s, pollutant=POLLUTANT)
        ica_df = pd.DataFrame({"fecha": forecast_idx, "pm25_forecast": forecast_vals,
                               "categoria_ica": cats.values})
        ica_path = OUTPUT / "ica_forecast_30d.csv"
        ica_df.to_csv(ica_path, index=False)

        cat_counts = ica_df["categoria_ica"].value_counts()
        logger.info("Categorías ICA del pronóstico 30d:")
        for cat, cnt in cat_counts.items():
            logger.info("  %-20s %d días", cat, cnt)
        logger.info("ICA forecast guardado: %s", ica_path.name)
    except Exception as e:
        logger.warning("Pronóstico ICA skipped: %s", e)

    # ── 5.8 Reporte HTML multi-modelo ──────────────────────────────────────
    logger.info("--- Generando reporte HTML multi-modelo ---")
    try:
        from estadistica_ambiental.reporting.forecast_report import forecast_report
        y_true_rep = None
        preds_rep  = {}
        metrics_rep = {}
        for nombre, res in resultados.items():
            preds = res.get("predictions", pd.DataFrame())
            if not preds.empty:
                arr = preds["predicted"].values
                if y_true_rep is None:
                    y_true_rep = serie.iloc[-len(arr):]
                preds_rep[nombre]  = arr
                metrics_rep[nombre] = res.get("metrics", {})
        if y_true_rep is not None and preds_rep:
            report_path = OUTPUT / "forecast_multimodelo.html"
            forecast_report(
                y_true=y_true_rep,
                predictions=preds_rep,
                metrics=metrics_rep,
                output=str(report_path),
                title="Comparación Multi-Modelo PM2.5 — Bogotá Rural Mochuelo",
                variable_name="PM2.5",
                unit="µg/m³",
            )
            logger.info("Reporte multi-modelo guardado: %s", report_path.name)
    except Exception as e:
        logger.warning("Reporte HTML skipped: %s", e)

    # ── Resumen final ────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("RESUMEN MULTI-MODELO — %s", ESTACION)
    for nombre, res in resultados.items():
        m = res.get("metrics", {})
        logger.info("  %-15s RMSE=%.3f | MAE=%.3f | R2=%.3f | hit_ica=%.1f%%",
                    nombre,
                    m.get("rmse", np.nan), m.get("mae", np.nan),
                    m.get("r2", np.nan),   m.get("hit_rate_ica", np.nan))
    logger.info("Salidas en: %s", OUTPUT)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
