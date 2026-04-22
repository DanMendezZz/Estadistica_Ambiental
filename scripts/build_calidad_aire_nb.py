"""Genera el notebook MVP de calidad del aire."""

import json
from pathlib import Path

OUT = Path("D:/Dan/98. IA/Estadistica_Ambiental/notebooks/lineas_tematicas/bloque_b_transversales/calidad_aire.ipynb")


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src, "id": f"m{abs(hash(src[:20])):08x}"}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None, "id": f"c{abs(hash(src[:20])):08x}"}


cells = [
    md("# Calidad del Aire — PM2.5 RMCAB Bogotá\n"
       "> **Contexto:** `docs/fuentes/calidad_aire.md`  \n"
       "> **Plan:** `Plan.md` Fase 4 — MVP predictivo  \n"
       "> **Variable:** PM2.5 (µg/m³) | **Fuente:** RMCAB Bogotá  \n"
       "> **Objetivo:** Ciclo estadístico completo + comparación de modelos + reporte automático"),

    md("## 0. Setup"),
    code(
        'import warnings; warnings.filterwarnings("ignore")\n'
        'import pandas as pd\n'
        'import numpy as np\n'
        'import matplotlib.pyplot as plt\n'
        '\n'
        'from estadistica_ambiental.io.loaders import load_csv\n'
        'from estadistica_ambiental.io.validators import validate\n'
        'from estadistica_ambiental.eda.variables import classify\n'
        'from estadistica_ambiental.eda.quality import assess_quality\n'
        'from estadistica_ambiental.eda.profiling import run_eda\n'
        'from estadistica_ambiental.eda.viz import plot_series, plot_seasonal_means, plot_correlation_heatmap\n'
        'from estadistica_ambiental.preprocessing.imputation import impute\n'
        'from estadistica_ambiental.descriptive.univariate import summarize\n'
        'from estadistica_ambiental.descriptive.temporal import decompose_stl\n'
        'from estadistica_ambiental.inference.stationarity import stationarity_report\n'
        'from estadistica_ambiental.inference.trend import mann_kendall\n'
        'from estadistica_ambiental.inference.intervals import exceedance_probability\n'
        'from estadistica_ambiental.predictive.classical import SARIMAXModel\n'
        'from estadistica_ambiental.predictive.ml import XGBoostModel, RandomForestModel\n'
        'from estadistica_ambiental.evaluation.metrics import evaluate\n'
        'from estadistica_ambiental.evaluation.backtesting import walk_forward, compare_backtests\n'
        'from estadistica_ambiental.evaluation.comparison import rank_models\n'
        'from estadistica_ambiental.reporting.forecast_report import forecast_report\n'
        'from estadistica_ambiental.config import NORMA_CO, NORMA_OMS\n'
        '\n'
        'print("Setup OK")'
    ),

    md("## 1. Datos\n"
       "> Dataset sintético representativo de RMCAB.  \n"
       "> Reemplazar con CSV real en `data/raw/` cuando esté disponible."),
    code(
        'np.random.seed(42)\n'
        'n = 365 * 3\n'
        'fechas = pd.date_range("2020-01-01", periods=n, freq="D")\n'
        '\n'
        'trend    = np.linspace(12, 18, n)\n'
        'seasonal = 6 * np.sin(2 * np.pi * np.arange(n) / 365 - np.pi/2)\n'
        'noise    = np.random.normal(0, 3, n)\n'
        'episodes = np.where(np.random.random(n) < 0.03, np.random.uniform(50, 120, n), 0)\n'
        'pm25     = np.clip(trend + seasonal + noise + episodes, 0, None)\n'
        '\n'
        'temp    = 13 + 4*np.sin(2*np.pi*np.arange(n)/365) + np.random.normal(0,1,n)\n'
        'humedad = 75 + 10*np.sin(2*np.pi*np.arange(n)/365 + np.pi) + np.random.normal(0,5,n)\n'
        'viento  = np.abs(np.random.normal(2, 1, n))\n'
        '\n'
        'missing_idx = np.random.choice(n, int(n*0.05), replace=False)\n'
        'pm25[missing_idx] = np.nan\n'
        '\n'
        'df = pd.DataFrame({"fecha": fechas, "pm25": pm25,\n'
        '                   "temperatura": temp.round(1),\n'
        '                   "humedad": humedad.round(1), "viento": viento.round(2)})\n'
        'print(f"Dataset: {df.shape[0]:,} filas | Faltantes PM2.5: {df.pm25.isna().sum()}")\n'
        'df.head()'
    ),

    md("## 2. Validación y EDA"),
    code(
        'val = validate(df, date_col="fecha")\n'
        'print(val.summary())'
    ),
    code(
        'quality = assess_quality(df, date_col="fecha")\n'
        'print(quality.summary())'
    ),
    code(
        'report_path = run_eda(df, output="data/output/reports/eda_calidad_aire.html",\n'
        '                      title="EDA PM2.5 RMCAB Bogotá",\n'
        '                      date_col="fecha", use_ydata=False)\n'
        'print(f"Reporte: {report_path}")'
    ),

    md("## 3. Visualización"),
    code(
        'fig = plot_series(df, "fecha", "pm25", title="PM2.5 diario — RMCAB Bogotá")\n'
        'ax = fig.axes[0]\n'
        'ax.axhline(NORMA_CO["pm25_24h"],  color="red",    ls="--", lw=1,\n'
        '           label=f"Norma CO 24h ({NORMA_CO[\'pm25_24h\']} µg/m³)")\n'
        'ax.axhline(NORMA_OMS["pm25_24h"], color="orange", ls="--", lw=1,\n'
        '           label=f"Guía OMS ({NORMA_OMS[\'pm25_24h\']} µg/m³)")\n'
        'ax.legend(fontsize=8)\n'
        'plt.show()'
    ),
    code(
        'plot_seasonal_means(df, "fecha", "pm25", period="month")\n'
        'plt.show()'
    ),

    md("## 4. Estadística descriptiva"),
    code('summarize(df)'),
    code(
        'exc = exceedance_probability(df["pm25"].dropna(), threshold=NORMA_CO["pm25_24h"])\n'
        'exc_oms = exceedance_probability(df["pm25"].dropna(), threshold=NORMA_OMS["pm25_24h"])\n'
        'print(f"Norma CO:  {exc[\'n_exceedances\']} días ({exc[\'pct_exceed\']:.1f}%)")\n'
        'print(f"Guía OMS:  {exc_oms[\'n_exceedances\']} días ({exc_oms[\'pct_exceed\']:.1f}%)")'
    ),

    md("## 5. Inferencial"),
    code(
        'pm25_clean = df.set_index("fecha")["pm25"].dropna()\n'
        'stationarity_report(pm25_clean)'
    ),
    code(
        'mk = mann_kendall(pm25_clean)\n'
        'print(f"Tendencia: {mk[\'trend\']} | p={mk[\'pval\']:.4f} | slope={mk[\'slope\']:.4f} µg/m³/día")'
    ),
    code(
        'stl = decompose_stl(pm25_clean, period=365)\n'
        'fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)\n'
        'for ax, col, lbl in zip(axes,\n'
        '    ["observed","trend","seasonal","residual"],\n'
        '    ["Observado","Tendencia","Estacionalidad","Residuo"]):\n'
        '    ax.plot(stl[col], lw=1, color="#1a5276")\n'
        '    ax.set_ylabel(lbl, fontsize=8)\n'
        '    ax.grid(alpha=0.3)\n'
        'fig.suptitle("STL — PM2.5", fontweight="bold")\n'
        'plt.tight_layout(); plt.show()'
    ),

    md("## 6. Preprocesamiento"),
    code(
        'df_imp = impute(df.copy(), cols=["pm25"], method="linear")\n'
        'print(f"Faltantes antes={df.pm25.isna().sum()} | después={df_imp.pm25.isna().sum()}")'
    ),

    md("## 7. Modelos predictivos"),
    code(
        'ts = df_imp.set_index("fecha")["pm25"]\n'
        'X  = df_imp.set_index("fecha")[["temperatura","humedad","viento"]]\n'
        '\n'
        'models = {\n'
        '    "SARIMAX":      SARIMAXModel(order=(1,1,1), seasonal_order=(1,1,1,7)),\n'
        '    "XGBoost":      XGBoostModel(lags=[1,2,3,7,14]),\n'
        '    "RandomForest": RandomForestModel(lags=[1,2,3,7,14]),\n'
        '}\n'
        '\n'
        'results = {}\n'
        'for name, model in models.items():\n'
        '    print(f"Evaluando {name}...", end=" ")\n'
        '    results[name] = walk_forward(model, ts, horizon=7, n_splits=4)\n'
        '    print(f"RMSE={results[name][\'metrics\'][\'rmse\']:.3f}")'
    ),
    code(
        'ranking = rank_models(results, domain="air_quality")\n'
        'ranking[["rmse","mae","r2","score","rank"]]'
    ),

    md("## 8. Reporte final"),
    code(
        'train, test = ts.iloc[:-30], ts.iloc[-30:]\n'
        'X_tr,  X_te = X.iloc[:-30],  X.iloc[-30:]\n'
        '\n'
        'preds = {}\n'
        'for name, model in models.items():\n'
        '    model.fit(train, X_tr if name=="SARIMAX" else None)\n'
        '    preds[name] = model.predict(30, X_te if name=="SARIMAX" else None)\n'
        '\n'
        'mets = {n: evaluate(test.values, p, domain="air_quality") for n, p in preds.items()}\n'
        'rpt  = forecast_report(test, preds, mets,\n'
        '    output="data/output/reports/forecast_calidad_aire.html",\n'
        '    title="Pronóstico PM2.5 RMCAB", variable_name="PM2.5", unit="µg/m³")\n'
        'print(f"Reporte: {rpt}")'
    ),

    md("## 9. Conclusiones\n\n"
       "- Ver excedencias de norma en sección 4.\n"
       "- Ver tendencia Mann-Kendall en sección 5.\n"
       "- Ver mejor modelo en ranking sección 7.\n\n"
       "### Datos reales sugeridos\n"
       "- [RMCAB](http://rmcab.ambientebogota.gov.co/)\n"
       "- [SIATA](https://siata.gov.co)\n"
       "- [OpenAQ](https://openaq.org)"),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "cells": cells,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook creado: {OUT}")
