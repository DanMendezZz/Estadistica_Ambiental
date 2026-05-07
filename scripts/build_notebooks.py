"""Genera los notebooks plantilla para las 15 líneas temáticas restantes.

Tras emitir la plantilla base, aplica los enrichments de dominio definidos
en `scripts/_patches/` (IRH, NDC, AVR, BMWP, ICA, etc.). Los enrichments son
idempotentes — pueden invocarse N veces sin duplicar celdas.

Notebooks con contenido custom (`CUSTOM_NOTEBOOKS`) NO se regeneran desde
plantilla; sólo se les aplican los enrichments si el archivo ya existe.
Esto preserva trabajo manual como `geoespacial.ipynb` (4 casos de uso).
"""

import hashlib
import json
import sys
from pathlib import Path

# Asegurar que el paquete `_patches` sea importable cuando se ejecute como script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _patches import apply_enrichments, apply_guardrails  # noqa: E402

BASE = Path(__file__).resolve().parent.parent / "notebooks"

# Notebooks con contenido custom hand-crafted que NO debe sobrescribirse por
# la plantilla base. Los enrichments registrados sí se les aplican (si la
# clave coincide con `_patches/<linea>.py`).
CUSTOM_NOTEBOOKS: set[str] = {"geoespacial"}

LINEAS = [
    # (path_relativo, nombre_display, variable_ejemplo, unidad, linea_tematica_key, modelos_sugeridos)
    # linea_tematica_key → coincide con config.ENSO_LAG_MESES y docs/fuentes/<key>.md
    # modelos_sugeridos → lista de strings para la celda de modelos
    ("bloque_a_gestion/areas_protegidas",
     "Áreas Protegidas", "cobertura_ha", "ha", "areas_protegidas",
     ["random_forest", "xgboost"]),

    ("bloque_a_gestion/humedales",
     "Humedales", "nivel_agua", "m", "humedales",
     ["sarima", "prophet", "xgboost"]),

    ("bloque_a_gestion/paramos",
     "Páramos", "temperatura", "°C", "paramos",
     ["sarima", "prophet", "xgboost"]),

    ("bloque_a_gestion/direccion_directiva",
     "Dirección Directiva", "indicador", "", "direccion_directiva",
     ["random_forest", "xgboost"]),

    ("bloque_a_gestion/gestion_riesgo",
     "Gestión de Riesgo", "precipitacion", "mm", "gestion_riesgo",
     ["sarima", "sarimax", "xgboost", "random_forest"]),

    ("bloque_a_gestion/ordenamiento_territorial",
     "Ordenamiento Territorial", "superficie_km2", "km²", "ordenamiento_territorial",
     ["random_forest", "xgboost"]),

    ("bloque_a_gestion/oferta_hidrica",
     "Oferta Hídrica", "caudal", "m³/s", "oferta_hidrica",
     ["sarima", "sarimax", "prophet", "xgboost", "random_forest"]),

    ("bloque_a_gestion/pomca",
     "POMCA", "caudal", "m³/s", "pomca",
     ["sarima", "prophet", "xgboost"]),

    ("bloque_a_gestion/pueea",
     "PUEEA", "consumo_agua", "m³", "pueea",
     ["sarima", "sarimax", "prophet", "xgboost"]),

    ("bloque_a_gestion/recurso_hidrico",
     "Recurso Hídrico", "od", "mg/L", "recurso_hidrico",
     ["sarima", "sarimax", "xgboost", "random_forest"]),

    ("bloque_a_gestion/rondas_hidricas",
     "Rondas Hídricas", "caudal", "m³/s", "rondas_hidricas",
     ["sarima", "prophet", "xgboost"]),

    ("bloque_a_gestion/sistemas_informacion_ambiental",
     "Sistemas de Información Ambiental", "n_registros", "", "sistemas_informacion_ambiental",
     ["random_forest", "xgboost"]),

    ("bloque_a_gestion/predios_conservacion",
     "Predios para Conservación", "ndvi", "", "predios_conservacion",
     ["random_forest", "xgboost"]),

    ("bloque_b_transversales/cambio_climatico",
     "Cambio Climático", "temperatura", "°C", "cambio_climatico",
     ["sarima", "sarimax", "prophet", "xgboost"]),

    ("bloque_c_tecnicas/geoespacial",
     "Geoespacial", "valor", "", "geoespacial",
     ["kriging", "random_forest", "xgboost"]),
]


def _stable_id(prefix: str, src: str) -> str:
    """ID determinista por md5 del contenido — mismo resultado entre corridas."""
    return f"{prefix}{hashlib.md5(src.encode('utf-8')).hexdigest()[:12]}"


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src, "id": _stable_id("m", src)}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None, "id": _stable_id("c", src)}


def build_notebook(path_rel, nombre, variable, unidad, linea_key, modelos_sugeridos):
    fuente_key = path_rel.split("/")[-1]
    fuente_file = f"docs/fuentes/{fuente_key}.md"
    bloque = path_rel.split("/")[0].replace("bloque_a_gestion", "A").replace(
        "bloque_b_transversales", "B").replace("bloque_c_tecnicas", "C")

    # Celda de modelos dinámica según la línea temática
    model_entries = []
    for m in modelos_sugeridos:
        if m == "sarima":
            model_entries.append(
                '    "SARIMA":       get_model("sarima", order=(1,1,1), seasonal_order=(1,1,1,12)),'
            )
        elif m == "sarimax":
            model_entries.append(
                '    "SARIMAX":      get_model("sarimax", order=(1,1,1), seasonal_order=(1,1,1,12)),'
            )
        elif m == "prophet":
            model_entries.append(
                '    "Prophet":      get_model("prophet"),'
            )
        elif m == "xgboost":
            model_entries.append(
                '    "XGBoost":      get_model("xgboost", lags=[1,2,3,6,12]),'
            )
        elif m == "random_forest":
            model_entries.append(
                '    "RandomForest": get_model("random_forest", lags=[1,2,3,6,12]),'
            )
        elif m == "kriging":
            model_entries.append(
                '    # "Kriging":   ver spatial/interpolation.py para datos espaciales'
            )
    models_dict = "\n".join(model_entries)

    # ¿Esta línea usa ENSO como covariable?
    usa_enso = linea_key in (
        "oferta_hidrica", "recurso_hidrico", "paramos", "humedales",
        "gestion_riesgo", "pomca", "pueea", "rondas_hidricas", "cambio_climatico",
        "calidad_aire",
    )
    enso_import = (
        "from estadistica_ambiental.features.climate import load_oni, enso_lagged\n"
        "from estadistica_ambiental.config import ENSO_LAG_MESES\n"
        if usa_enso else ""
    )
    enso_cell_src = (
        f'# --- Covariable ENSO (lag específico para {nombre}) ---\n'
        f'# Guard (M-20): avisar si LINEA no tiene lag específico — se aplicará el default.\n'
        f'if LINEA not in ENSO_LAG_MESES:\n'
        f'    _lag_default = ENSO_LAG_MESES["default"]\n'
        f'    print(f"[aviso] \'{{LINEA}}\' sin lag específico en ENSO_LAG_MESES; "\n'
        f'          f"se usará default ({{_lag_default}} meses).")\n'
        f'else:\n'
        f'    print(f"[ok] ENSO lag para \'{{LINEA}}\' = {{ENSO_LAG_MESES[LINEA]}} meses")\n'
        f'\n'
        f'oni = load_oni()  # Descarga ONI desde NOAA\n'
        f'df = enso_lagged(df, oni, date_col="fecha", linea_tematica=LINEA)\n'
        f'print("Columnas ENSO agregadas:", [c for c in df.columns if "oni" in c or "enso" in c])'
    ) if usa_enso else None

    cells = [
        md(f"# {nombre}\n"
           f"\n"
           f"> **Contexto de dominio:** [`{fuente_file}`](../../{fuente_file})  \n"
           f"> **Bloque:** {bloque} | **Línea:** `{linea_key}`  \n"
           f"> **Variable principal:** `{variable}` ({unidad})  \n"
           f"> **Modelos sugeridos:** {', '.join(m.upper() for m in modelos_sugeridos if m != 'kriging')}  \n"
           f"> Flujo: `Plan.md` sección 3 — ciclo estadístico completo.\n"
           f"\n"
           f"**Antes de comenzar:** Leer `{fuente_file}` para entender:\n"
           f"- Variables ambientales clave y sus rangos físicos\n"
           f"- Normativa colombiana aplicable (umbrales normativos)\n"
           f"- Fuentes de datos oficiales y frecuencia de actualización\n"
           f"- Preguntas analíticas típicas de esta línea"),

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
            'from estadistica_ambiental.inference.intervals import exceedance_report\n'
            + enso_import +
            'from estadistica_ambiental.predictive.registry import get_model, list_models\n'
            'from estadistica_ambiental.evaluation.backtesting import walk_forward\n'
            'from estadistica_ambiental.evaluation.comparison import rank_models\n'
            f'from estadistica_ambiental.config import DOCS_FUENTES\n'
            '\n'
            f'LINEA = "{linea_key}"\n'
            f'VARIABLE = "{variable}"\n'
            f'UNIDAD = "{unidad}"\n'
            '\n'
            'print("Setup OK | Modelos disponibles:", list_models())'
        ),

        md(f"## 0b. Contexto de dominio\n"
           f"> Carga la ficha técnica de la línea `{linea_key}` para tener presente "
           f"la normativa, los indicadores y las preguntas analíticas durante el análisis."),
        code(
            f'ficha = DOCS_FUENTES / "{fuente_key}.md"\n'
            'if ficha.exists():\n'
            '    print(ficha.read_text(encoding="utf-8")[:3000])  # primeras 3000 chars\n'
            'else:\n'
            f'    print("Ficha no encontrada en", ficha)'
        ),

        md(f"## 1. Cargar datos\n"
           f"> Colocar el archivo en `data/raw/` y ajustar la ruta.  \n"
           f"> Ver sección **Datos y fuentes** de `{fuente_file}` para las fuentes oficiales."),
        code(
            f'# df = load_csv("data/raw/{fuente_key}.csv", date_col="fecha")\n'
            f'\n'
            f'# --- Datos sintéticos de ejemplo ---\n'
            f'np.random.seed(42)\n'
            f'n = 120\n'
            f'df = pd.DataFrame({{\n'
            f'    "fecha":    pd.date_range("2015-01-01", periods=n, freq="ME"),\n'
            f'    "{variable}": np.random.gamma(3, 5, n) + np.linspace(0, 5, n),\n'
            f'}})\n'
            f'print(f"Shape: {{df.shape}} | Rango: {{df.fecha.min()}} → {{df.fecha.max()}}")\n'
            f'df.head()'
        ),

        md("## 2. Validación y EDA\n"
           f"> `validate()` usa rangos físicos específicos para `{linea_key}` desde `config.py`."),
        code(
            'val = validate(df, date_col="fecha", linea_tematica=LINEA)\n'
            'print(val.summary())'
        ),
        code(
            f'run_eda(df, output=f"data/output/reports/eda_{fuente_key}.html",\n'
            f'       title="EDA — {nombre}", date_col="fecha", use_ydata=False)\n'
            '# Abrir el HTML en el navegador para el reporte completo'
        ),

        md("## 3. Visualización exploratoria"),
        code(
            f'plot_series(df, "fecha", "{variable}", title="{nombre} — {variable} ({unidad})")\n'
            'plt.show()'
        ),
        code(
            f'plot_seasonal_means(df, "fecha", "{variable}", period="month")\n'
            'plt.show()'
        ),
    ]

    # Celda ENSO (solo para líneas que la usan)
    if enso_cell_src:
        cells.append(md("## 3b. Covariable ENSO (ONI)\n"
                        f"> Lag recomendado para `{linea_key}` definido en `config.ENSO_LAG_MESES`."))
        cells.append(code(enso_cell_src))

    cells += [
        md("## 4. Estadística descriptiva"),
        code('summarize(df)'),

        md("## 5. Inferencial\n"
           "> ADR-004: Estacionariedad obligatoria pre-ARIMA (ADF + KPSS juntos)."),
        code(
            f'ts = df.set_index("fecha")["{variable}"].dropna()\n'
            'stationarity_report(ts)'
        ),
        code(
            'mk = mann_kendall(ts)\n'
            'print(f"Tendencia: {mk[\'trend\']} | p={mk[\'pval\']:.4f} | slope={mk[\'slope\']:.6f}")'
        ),

        md(f"## 5b. Análisis de excedencias normativas\n"
           f"> Compara `{variable}` contra las normas colombianas relevantes."),
        code(
            f'rep = exceedance_report(df["{variable}"], variable="{variable}")\n'
            'if rep.empty:\n'
            f'    print("Sin normas colombianas registradas para \'{variable}\'. "\n'
            f'          "Agregar umbral manual a la llamada exceedance_probability().")\n'
            'else:\n'
            '    display(rep)'
        ),

        md("## 6. Preprocesamiento"),
        code(
            f'df_clean = impute(df.copy(), cols=["{variable}"], method="linear")\n'
            f'print(f"Faltantes antes: {{df[\"{variable}\"].isna().sum()}} | "\n'
            f'      f"después: {{df_clean[\"{variable}\"].isna().sum()}}")'
        ),

        md("## 7. Modelos predictivos"),
        code(
            f'ts = df_clean.set_index("fecha")["{variable}"]\n'
            '\n'
            'models = {\n'
            + models_dict + '\n'
            '}\n'
            '\n'
            'results = {}\n'
            'for name, model in models.items():\n'
            '    if name.startswith("#"):\n'
            '        continue\n'
            '    results[name] = walk_forward(model, ts, horizon=6, n_splits=4)\n'
            '    print(f"{name}: RMSE={results[name][\'metrics\'][\'rmse\']:.3f}")'
        ),
        code(
            'rank_models(results)[["rmse","mae","r2","score","rank"]]'
        ),

        md("## 8. Conclusiones\n\n"
           f"- **Línea temática:** {nombre} (`{linea_key}`)\n"
           f"- **Variable analizada:** `{variable}` ({unidad})\n"
           f"- **Modelos ejecutados:** {', '.join(m.upper() for m in modelos_sugeridos if m != 'kriging')}\n"
           "- Completar con hallazgos reales al trabajar con datos de producción.\n\n"
           "### Normativa y referencias\n"
           f"- Ver `{fuente_file}` para normativa colombiana, indicadores oficiales y fuentes de datos.\n"
           "- Registrar decisiones metodológicas en `docs/decisiones.md`."),
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


def enrich_notebook(path: Path, linea_key: str) -> bool:
    """Aplica los enrichments registrados para `linea_key` sobre el notebook
    en `path` (lectura → mutación in-place → reescritura).

    Idempotente: si los enrichments detectan su marker, no duplican celdas.

    Returns True si se aplicó (o ya estaba), False si no hay enrichment
    registrado o si el archivo no existe.
    """
    if not path.exists():
        return False
    nb = json.loads(path.read_text(encoding="utf-8"))
    n_before = len(nb["cells"])
    if not apply_enrichments(linea_key, nb):
        return False
    n_after = len(nb["cells"])
    if n_after != n_before:
        path.write_text(
            json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return True


def apply_guardrails_to_notebook(path: Path, linea_key: str) -> bool:
    """Inserta o reposiciona la sección de Guardrails M-21 (idempotente)."""
    if not path.exists():
        return False
    raw_before = path.read_text(encoding="utf-8")
    nb = json.loads(raw_before)
    apply_guardrails(linea_key, nb)
    raw_after = json.dumps(nb, ensure_ascii=False, indent=1)
    if raw_after != raw_before:
        path.write_text(raw_after, encoding="utf-8")
        return True
    return False


# Notebooks temáticos hand-crafted que viven fuera de LINEAS pero también
# deben recibir guardrails. (linea_key, path_relativo_sin_extension)
EXTRA_GUARDRAIL_TARGETS: list[tuple[str, str]] = [
    ("calidad_aire", "bloque_b_transversales/calidad_aire"),
]


if __name__ == "__main__":
    base_count = 0
    enrich_count = 0
    guard_count = 0
    for path_rel, nombre, variable, unidad, linea_key, modelos in LINEAS:
        out = BASE / "lineas_tematicas" / f"{path_rel}.ipynb"

        if linea_key in CUSTOM_NOTEBOOKS:
            print(f"  {out.name} (custom — base no regenerada)")
        else:
            path = build_notebook(
                path_rel, nombre, variable, unidad, linea_key, modelos
            )
            print(f"  {path.name}")
            base_count += 1

        if enrich_notebook(out, linea_key):
            enrich_count += 1

        if apply_guardrails_to_notebook(out, linea_key):
            guard_count += 1

    for linea_key, path_rel in EXTRA_GUARDRAIL_TARGETS:
        out = BASE / "lineas_tematicas" / f"{path_rel}.ipynb"
        if apply_guardrails_to_notebook(out, linea_key):
            guard_count += 1
            print(f"  {out.name} (guardrails M-21)")

    print(
        f"\n{base_count} notebooks generados desde plantilla, "
        f"{enrich_count} enriquecidos con celdas de dominio, "
        f"{guard_count} con guardrails M-21."
    )
