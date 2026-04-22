"""Genera los notebooks plantilla para las 15 líneas temáticas restantes."""

import json
from pathlib import Path

BASE = Path("D:/Dan/98. IA/Estadistica_Ambiental/notebooks")

LINEAS = [
    # (path_relativo, nombre_display, variable_ejemplo, unidad)
    ("bloque_a_gestion/areas_protegidas",        "Áreas Protegidas",                "cobertura_ha",    "ha"),
    ("bloque_a_gestion/humedales",               "Humedales",                       "nivel_agua",      "m"),
    ("bloque_a_gestion/paramos",                 "Páramos",                         "temperatura",     "°C"),
    ("bloque_a_gestion/direccion_directiva",     "Dirección Directiva",             "indicador",       ""),
    ("bloque_a_gestion/gestion_riesgo",          "Gestión de Riesgo",               "precipitacion",   "mm"),
    ("bloque_a_gestion/ordenamiento_territorial","Ordenamiento Territorial",         "superficie_km2",  "km²"),
    ("bloque_a_gestion/oferta_hidrica",          "Oferta Hídrica",                  "caudal",          "m³/s"),
    ("bloque_a_gestion/pomca",                   "POMCA",                           "caudal",          "m³/s"),
    ("bloque_a_gestion/pueea",                   "PUEEA",                           "consumo_agua",    "m³"),
    ("bloque_a_gestion/recurso_hidrico",         "Recurso Hídrico",                 "ph",              ""),
    ("bloque_a_gestion/rondas_hidricas",         "Rondas Hídricas",                 "caudal",          "m³/s"),
    ("bloque_a_gestion/sistemas_informacion_ambiental","Sistemas de Información Ambiental","n_registros",""),
    ("bloque_a_gestion/predios_conservacion",    "Predios para Conservación",       "area_ha",         "ha"),
    ("bloque_b_transversales/cambio_climatico",  "Cambio Climático",                "temperatura",     "°C"),
    ("bloque_c_tecnicas/geoespacial",            "Geoespacial",                     "valor",           ""),
]


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src, "id": f"m{abs(hash(src[:20])):08x}"}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None, "id": f"c{abs(hash(src[:20])):08x}"}


def build_notebook(path_rel, nombre, variable, unidad):
    fuente_key = path_rel.split("/")[-1]
    fuente_file = f"docs/fuentes/{fuente_key}.md"
    bloque = path_rel.split("/")[0].replace("bloque_a_gestion", "A").replace(
        "bloque_b_transversales", "B").replace("bloque_c_tecnicas", "C")

    cells = [
        md(f"# {nombre}\n"
           f"> **Contexto de dominio:** `{fuente_file}`  \n"
           f"> **Bloque:** {bloque}  \n"
           f"> **Variable principal:** {variable} ({unidad})  \n"
           f"> Ejecutar `Plan.md` sección 3 (ciclo estadístico completo)."),

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
            'from estadistica_ambiental.eda.viz import plot_series, plot_seasonal_means\n'
            'from estadistica_ambiental.preprocessing.imputation import impute\n'
            'from estadistica_ambiental.descriptive.univariate import summarize\n'
            'from estadistica_ambiental.inference.stationarity import stationarity_report\n'
            'from estadistica_ambiental.inference.trend import mann_kendall\n'
            'from estadistica_ambiental.predictive.registry import get_model, list_models\n'
            'from estadistica_ambiental.evaluation.backtesting import walk_forward\n'
            'from estadistica_ambiental.evaluation.comparison import rank_models\n'
            '\n'
            'print("Setup OK | Modelos disponibles:", list_models())'
        ),

        md(f"## 1. Cargar datos\n"
           f"> Colocar el archivo en `data/raw/` y ajustar la ruta.  \n"
           f"> Documentar la fuente en `{fuente_file}`."),
        code(
            f'# df = load_csv("data/raw/{fuente_key}.csv", date_col="fecha")\n'
            f'\n'
            f'# --- Datos sintéticos de ejemplo ---\n'
            f'np.random.seed(42)\n'
            f'n = 120\n'
            f'df = pd.DataFrame({{\n'
            f'    "fecha":      pd.date_range("2015-01-01", periods=n, freq="ME"),\n'
            f'    "{variable}": np.random.gamma(3, 5, n) + np.linspace(0, 5, n),\n'
            f'}})\n'
            f'df.head()'
        ),

        md("## 2. Validación y EDA"),
        code(
            'val = validate(df, date_col="fecha")\n'
            'print(val.summary())\n'
            'cat = classify(df)\n'
            'print(cat.summary())'
        ),
        code(
            'run_eda(df, output=f"data/output/reports/eda_{fuente_key}.html",\n'
            f'       title="EDA — {nombre}", date_col="fecha", use_ydata=False)\n'
            '# Abrir el HTML en el navegador para el reporte completo'
        ),

        md("## 3. Visualización exploratoria"),
        code(
            f'plot_series(df, "fecha", "{variable}", title="{nombre}")\n'
            'plt.show()'
        ),
        code(
            f'plot_seasonal_means(df, "fecha", "{variable}", period="month")\n'
            'plt.show()'
        ),

        md("## 4. Estadística descriptiva"),
        code('summarize(df)'),

        md("## 5. Inferencial"),
        code(
            f'ts = df.set_index("fecha")["{variable}"].dropna()\n'
            'stationarity_report(ts)'
        ),
        code(
            'mk = mann_kendall(ts)\n'
            'print(f"Tendencia: {mk[\'trend\']} | p={mk[\'pval\']:.4f} | slope={mk[\'slope\']:.6f}")'
        ),

        md("## 6. Preprocesamiento"),
        code(
            f'df_clean = impute(df.copy(), cols=["{variable}"], method="linear")'
        ),

        md("## 7. Modelos predictivos"),
        code(
            f'ts = df_clean.set_index("fecha")["{variable}"]\n'
            '\n'
            'models = {\n'
            '    "SARIMA":      get_model("sarima", order=(1,1,1), seasonal_order=(1,1,1,12)),\n'
            '    "XGBoost":     get_model("xgboost", lags=[1,2,3,6,12]),\n'
            '    "RandomForest":get_model("random_forest", lags=[1,2,3,6,12]),\n'
            '}\n'
            '\n'
            'results = {}\n'
            'for name, model in models.items():\n'
            '    results[name] = walk_forward(model, ts, horizon=6, n_splits=4)\n'
            '    print(f"{name}: RMSE={results[name][\'metrics\'][\'rmse\']:.3f}")'
        ),
        code(
            'rank_models(results)[["rmse","mae","r2","score","rank"]]'
        ),

        md("## 8. Conclusiones\n\n"
           f"- Variable analizada: **{variable}** ({unidad})\n"
           f"- Fuente de dominio: `{fuente_file}`\n"
           "- Completar con hallazgos reales al trabajar con datos de producción.\n\n"
           "### Referencias\n"
           f"- Ver `{fuente_file}` para normativa, indicadores y fuentes de datos."),
    ]

    nb = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

    out = BASE / "lineas_tematicas" / f"{path_rel}.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    for args in LINEAS:
        path = build_notebook(*args)
        print(f"  {path.name}")
    print(f"\n{len(LINEAS)} notebooks generados.")
