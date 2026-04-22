"""Genera el notebook plantilla maestra del ciclo estadístico completo."""

import json
from pathlib import Path

OUT = Path("D:/Dan/98. IA/Estadistica_Ambiental/notebooks/00_plantilla_ciclo_completo.ipynb")


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src, "id": f"m{abs(hash(src[:24])):08x}"}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None, "id": f"c{abs(hash(src[:24])):08x}"}


cells = [
    md(
        "# Plantilla — Ciclo Estadístico Completo\n\n"
        "> **Uso:** copiar esta plantilla para cada nueva línea temática.  \n"
        "> Ajustar: `LINEA`, `VARIABLE`, `UNIDAD`, `DATE_COL`, `ruta del archivo`.  \n"
        "> Consultar `Plan.md` sección 3 y `docs/fuentes/<linea>.md` antes de ejecutar.\n\n"
        "```\n"
        "Flujo: Carga → Validación → EDA → Descriptiva → Inferencial\n"
        "       → Preprocesamiento → Modelos → Backtesting → Reporte\n"
        "```"
    ),

    md("## 0. Configuración del proyecto"),
    code(
        '# ── Ajustar por línea temática ──────────────────────────────────────\n'
        'LINEA    = "calidad_aire"          # key en docs/fuentes/\n'
        'VARIABLE = "pm25"                  # columna objetivo\n'
        'UNIDAD   = "µg/m³"\n'
        'DATE_COL = "fecha"\n'
        'DOMINIO  = "air_quality"           # general | hydrology | air_quality\n'
        'HORIZONTE = 7                      # pasos de pronóstico\n'
        'N_SPLITS  = 4                      # folds de backtesting\n'
        '# ────────────────────────────────────────────────────────────────────\n'
        '\n'
        'import warnings; warnings.filterwarnings("ignore")\n'
        'import pandas as pd\n'
        'import numpy as np\n'
        'import matplotlib.pyplot as plt\n'
        '\n'
        'import estadistica_ambiental as ea\n'
        'from estadistica_ambiental.eda.viz import (\n'
        '    plot_series, plot_missing_heatmap, plot_histogram,\n'
        '    plot_seasonal_means, plot_correlation_heatmap,\n'
        ')\n'
        'from estadistica_ambiental.descriptive.temporal import (\n'
        '    decompose_stl, acf_values, pacf_values,\n'
        ')\n'
        'from estadistica_ambiental.descriptive.bivariate import correlation_table\n'
        'from estadistica_ambiental.inference.distributions import normality_tests\n'
        'from estadistica_ambiental.inference.hypothesis import mannwhitney\n'
        'from estadistica_ambiental.config import NORMA_CO, NORMA_OMS\n'
        '\n'
        'print(f"estadistica_ambiental v{ea.__version__}")\n'
        'print("Modelos disponibles:", ea.list_models())'
    ),

    md("## 1. Ingesta de datos"),
    code(
        '# Opción A: cargar desde archivo real\n'
        '# df = ea.load(f"data/raw/{LINEA}.csv", date_col=DATE_COL)\n'
        '\n'
        '# Opción B: datos sintéticos de prueba (reemplazar con reales)\n'
        'np.random.seed(42)\n'
        'n = 120\n'
        'df = pd.DataFrame({\n'
        '    DATE_COL: pd.date_range("2015-01-01", periods=n, freq="ME"),\n'
        '    VARIABLE: np.random.gamma(3, 5, n) + np.linspace(0, 8, n),\n'
        '    "temperatura": np.random.normal(14, 3, n),\n'
        '    "humedad":     np.random.normal(70, 10, n),\n'
        '})\n'
        '# Introducir 5% de faltantes\n'
        'df.loc[df.sample(frac=0.05).index, VARIABLE] = np.nan\n'
        '\n'
        'print(f"Shape: {df.shape} | Faltantes: {df[VARIABLE].isna().sum()}")\n'
        'df.head()'
    ),

    md("## 2. Validación de calidad (física + estadística)"),
    code(
        '# Rangos físicos y duplicados\n'
        'val = ea.validate(df, date_col=DATE_COL)\n'
        'print(val.summary())'
    ),
    code(
        '# Catálogo de variables\n'
        'cat = ea.classify(df)\n'
        'print(cat.summary())'
    ),
    code(
        '# Calidad profunda: gaps, freeze, outliers estadísticos\n'
        'quality = ea.assess_quality(df, date_col=DATE_COL)\n'
        'print(quality.summary())'
    ),

    md("## 3. EDA automático"),
    code(
        'report_path = ea.run_eda(\n'
        '    df,\n'
        '    output=f"data/output/reports/eda_{LINEA}.html",\n'
        '    title=f"EDA — {LINEA.replace(\'_\', \' \').title()}",\n'
        '    date_col=DATE_COL,\n'
        '    use_ydata=False,\n'
        ')\n'
        'print(f"Reporte EDA: {report_path}")'
    ),

    md("## 4. Visualización exploratoria"),
    code(
        'fig = plot_series(df, DATE_COL, VARIABLE,\n'
        '                  title=f"{VARIABLE} ({UNIDAD})")\n'
        'plt.show()'
    ),
    code(
        'plot_missing_heatmap(df, date_col=DATE_COL)\n'
        'plt.show()'
    ),
    code(
        'plot_seasonal_means(df, DATE_COL, VARIABLE, period="month")\n'
        'plt.show()'
    ),
    code(
        'plot_histogram(df, VARIABLE)\n'
        'plt.show()'
    ),
    code(
        'plot_correlation_heatmap(df)\n'
        'plt.show()'
    ),

    md("## 5. Estadística descriptiva"),
    code(
        'ea.summarize(df)'
    ),
    code(
        'corr = correlation_table(df, method="spearman")\n'
        'corr.head(10)'
    ),

    md("## 6. Estadística inferencial"),
    code(
        '# Prueba de normalidad\n'
        'normality_tests(df[VARIABLE].dropna())'
    ),
    code(
        '# Estacionariedad (obligatorio antes de ARIMA — ADR-004)\n'
        'ts_index = df.set_index(DATE_COL)[VARIABLE].dropna()\n'
        'ea.stationarity_report(ts_index)'
    ),
    code(
        '# Tendencia Mann-Kendall\n'
        'mk = ea.mann_kendall(ts_index)\n'
        'print(f"Tendencia: {mk[\'trend\']} | p={mk[\'pval\']:.4f} | slope={mk[\'slope\']:.6f} {UNIDAD}/período")'
    ),
    code(
        '# Descomposición STL\n'
        'from estadistica_ambiental.descriptive.temporal import decompose_stl\n'
        'stl = decompose_stl(ts_index, period=12)\n'
        'fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)\n'
        'for ax, col, lbl in zip(axes, ["observed","trend","seasonal","residual"],\n'
        '                         ["Observado","Tendencia","Estacionalidad","Residuo"]):\n'
        '    ax.plot(stl[col], color="#1a5276", lw=1)\n'
        '    ax.set_ylabel(lbl, fontsize=8)\n'
        '    ax.grid(alpha=0.3)\n'
        'fig.suptitle(f"STL — {VARIABLE}", fontweight="bold")\n'
        'plt.tight_layout(); plt.show()'
    ),
    code(
        '# ACF y PACF\n'
        'fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 3))\n'
        'acf = acf_values(ts_index, nlags=24)\n'
        'pacf_v = pacf_values(ts_index, nlags=24)\n'
        'ax1.stem(acf, markerfmt="C0o", linefmt="C0-", basefmt="k-"); ax1.set_title("ACF")\n'
        'ax2.stem(pacf_v, markerfmt="C1o", linefmt="C1-", basefmt="k-"); ax2.set_title("PACF")\n'
        'plt.tight_layout(); plt.show()'
    ),
    code(
        '# Probabilidad de excedencia (si aplica norma)\n'
        'if VARIABLE in ("pm25", "pm10"):\n'
        '    norma_key = f"{VARIABLE}_24h"\n'
        '    if norma_key in NORMA_CO:\n'
        '        exc = ea.exceedance_probability(df[VARIABLE].dropna(), NORMA_CO[norma_key])\n'
        '        print(f"Excedencias norma CO ({NORMA_CO[norma_key]} {UNIDAD}): "\n'
        '              f"{exc[\'n_exceedances\']} días ({exc[\'pct_exceed\']:.1f}%)")'
    ),

    md("## 7. Preprocesamiento"),
    code(
        '# Imputación de faltantes\n'
        'df_clean = ea.impute(df.copy(), cols=[VARIABLE], method="linear")\n'
        'print(f"Faltantes antes={df[VARIABLE].isna().sum()} | después={df_clean[VARIABLE].isna().sum()}")'
    ),

    md("## 8. Modelos predictivos — comparación"),
    code(
        'ts = df_clean.set_index(DATE_COL)[VARIABLE]\n'
        '\n'
        'models = {\n'
        '    "SARIMA":       ea.get_model("sarima",        order=(1,1,1), seasonal_order=(1,1,1,12)),\n'
        '    "XGBoost":      ea.get_model("xgboost",       lags=[1,2,3,6,12]),\n'
        '    "RandomForest": ea.get_model("random_forest", lags=[1,2,3,6,12]),\n'
        '}\n'
        '\n'
        'results = {}\n'
        'for name, model in models.items():\n'
        '    results[name] = ea.walk_forward(\n'
        '        model, ts, horizon=HORIZONTE, n_splits=N_SPLITS, domain=DOMINIO\n'
        '    )\n'
        '    print(f"{name:15s} RMSE={results[name][\'metrics\'][\'rmse\']:.3f}")'
    ),
    code(
        '# Ranking multi-criterio\n'
        'ranking = ea.rank_models(results, domain=DOMINIO)\n'
        'print(f"Mejor modelo: {ea.select_best(results, domain=DOMINIO)}")\n'
        'ranking[["rmse","mae","r2","score","rank"]]'
    ),
    code(
        'ea.compare_backtests(results)'
    ),

    md("## 9. Reporte final"),
    code(
        '# Pronóstico del mejor modelo en los últimos N periodos\n'
        'N_TEST = HORIZONTE * 2\n'
        'train, test = ts.iloc[:-N_TEST], ts.iloc[-N_TEST:]\n'
        '\n'
        'best_name = ea.select_best(results, domain=DOMINIO)\n'
        'best_model = models[best_name]\n'
        'best_model.fit(train)\n'
        'preds = {best_name: best_model.predict(N_TEST)}\n'
        'mets  = {best_name: ea.evaluate(test.values, preds[best_name], domain=DOMINIO)}\n'
        '\n'
        'rpt = ea.forecast_report(\n'
        '    test, preds, mets,\n'
        '    output=f"data/output/reports/forecast_{LINEA}.html",\n'
        '    title=f"Pronóstico {VARIABLE} — {LINEA}",\n'
        '    variable_name=VARIABLE, unit=UNIDAD,\n'
        ')\n'
        'print(f"Reporte: {rpt}")'
    ),
    code(
        '# Reporte estadístico descriptivo + inferencial\n'
        'rpt_stats = ea.stats_report(\n'
        '    df_clean,\n'
        '    output=f"data/output/reports/stats_{LINEA}.html",\n'
        '    title=f"Estadística — {LINEA}",\n'
        '    date_col=DATE_COL,\n'
        ')\n'
        'print(f"Reporte estadístico: {rpt_stats}")'
    ),

    md(
        "## 10. Registro de decisiones\n\n"
        "Agregar al final de `docs/decisiones.md` cualquier decisión relevante:\n\n"
        "```\n"
        "## ADR-XXX — <Título>\n"
        "**Fecha:** YYYY-MM-DD | **Estado:** Aceptado\n"
        "**Contexto:** ...\n"
        "**Decisión:** ...\n"
        "**Consecuencias:** ...\n"
        "```\n\n"
        "Y actualizar `Plan.md` sección 11 (seguimiento de avance)."
    ),
]

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "cells": cells,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook master template: {OUT}")
