# Empezar

Esta guía cubre la instalación del paquete y un quick start de uso típico.

## Requisitos

- Python **3.10 o superior**
- Acceso a `pip` y a un entorno virtual (recomendado: `venv`, `uv` o `conda`)
- Git para clonar el repo o instalar desde GitHub

## Instalación

### Desde PyPI (recomendado)

```bash
pip install estadistica-ambiental
```

Para pinear a una versión exacta (en producción / repos satélite):

```bash
pip install "estadistica-ambiental==1.3.2"
```

### Desde GitHub (commits sin tag, ramas o forks)

```bash
pip install "git+https://github.com/DanMendezZz/Estadistica_Ambiental.git@main"
pip install "git+https://github.com/DanMendezZz/Estadistica_Ambiental.git@v1.3.2"
```

### Desde un clon local (para desarrollar el repo)

```bash
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git
cd Estadistica_Ambiental
pip install -e ".[dev]"
```

### Extras opcionales

El paquete declara grupos de dependencias opcionales en `pyproject.toml`:

| Extra | Para qué sirve |
|---|---|
| `ml` | XGBoost y LightGBM para modelos de calidad del aire |
| `prophet` | Forecasting con Prophet |
| `profile` | `ydata-profiling`, `sweetviz`, `missingno`, `plotly` |
| `deep` | PyTorch + Lightning (modelos profundos) |
| `bayes` | PyMC + ArviZ (modelos jerárquicos bayesianos) |
| `spatial` | Geopandas, Rasterio, PySAL, ESDA, Folium, etc. |
| `netcdf` | Lectura de NetCDF y HDF5 |
| `dev` | Pytest, Ruff, pre-commit, JupyterLab |
| `docs` | mkdocs-material y mkdocstrings (este sitio) |

Instalar varios a la vez:

```bash
pip install -e ".[ml,spatial,profile]"
```

## Quick start

### Cargar y validar datos

```python
from estadistica_ambiental.io.loaders import load_csv
from estadistica_ambiental.io.validators import validate

df = load_csv("data/raw/pm25_kennedy.csv", date_col="fecha")
df = validate(df, date_col="fecha", linea_tematica="calidad_aire")
```

### Excedencias normativas

```python
from estadistica_ambiental.inference.intervals import exceedance_report

reporte = exceedance_report(df["pm25"], variable="pm25")
print(reporte)  # tabla con normas CO (Res. 2254/2017) y OMS 2021
```

### ENSO con lag por línea temática

```python
from estadistica_ambiental.features.climate import enso_lagged, load_oni

oni = load_oni()
df = enso_lagged(df, oni, date_col="fecha", linea_tematica="oferta_hidrica")
```

### Reporte HTML de cumplimiento

```python
from estadistica_ambiental.reporting.compliance_report import compliance_report

compliance_report(
    df,
    variables=["pm25", "od"],
    linea_tematica="calidad_aire",
    output="data/output/reports/cumplimiento.html",
)
```

## Siguientes pasos

- Revisa la **[Metodología](metodologia.md)** para entender el ciclo EDA → Descriptiva → Inferencial → Predictiva.
- Explora las **[Líneas temáticas](lineas_tematicas.md)** y elige la que aplica a tu caso.
- Consulta el **[catálogo de modelos](modelos.md)** para decidir qué método usar.
- Lee las **[decisiones de diseño](decisiones.md)** (ADRs) antes de modificar arquitectura.
- Revisa la **[API Reference](api.md)** para detalles de cada función.

## Notebooks de ejemplo

En el repositorio:

- `notebooks/lineas_tematicas/` — 15 notebooks, uno por línea temática, con el flujo completo aplicado.
- `notebooks/00_template.ipynb` — plantilla genérica para iniciar un nuevo análisis.

Para regenerar todos los notebooks desde plantilla:

```bash
python scripts/build_notebooks.py
```
