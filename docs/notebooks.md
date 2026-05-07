# Notebooks interactivos

Ejecuta notebooks de `estadistica-ambiental` **directamente en tu navegador**, sin instalar nada.
La página corre [JupyterLite](https://jupyterlite.readthedocs.io/) con kernel
[Pyodide](https://pyodide.org/) — Python compilado a WebAssembly.

[Abrir JupyterLite en pantalla completa :material-launch:](lite/_dist/lab/index.html){ .md-button .md-button--primary target="_blank" }

<iframe
  src="lite/_dist/lab/index.html"
  width="100%"
  height="800"
  style="border: 1px solid #ccc; border-radius: 4px;"
  title="JupyterLite — Estadística Ambiental">
</iframe>

## Notebooks disponibles

| Notebook | Demuestra | Tiempo aprox. |
|---|---|---|
| `01_calidad_demo.ipynb` | `assess_quality` + `summarize` sobre PM2.5 sintético | ~1 min |
| `02_tendencia_mann_kendall.ipynb` | `mann_kendall` (Sen slope) sobre serie mensual | ~1 min |
| `03_excedencias_normativas.ipynb` | `exceedance_report` con normas Res. 2254/2017 y OMS | ~1 min |

## Cómo funciona

1. La primera vez que abres un notebook, el navegador descarga Pyodide (~10 MB) y luego
   `estadistica-ambiental` desde PyPI vía `piplite.install(...)`. Total: 30-60 s en buena conexión.
2. Cada notebook es **independiente y reproducible**: usa datos sintéticos generados con `numpy`,
   no requiere acceso a archivos ni a la red más allá de PyPI.
3. Tus cambios al notebook se guardan en el almacenamiento local del navegador (no se suben a
   ningún servidor). Para empezar limpio: `Ctrl/Cmd + Shift + Delete` en tu navegador.

## Limitaciones de Pyodide

JupyterLite ejecuta Python en el navegador, lo cual impone restricciones:

- **Funcionan:** `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `seaborn`,
  `pymannkendall`, `scikit-learn`. Es decir, todo el ciclo EDA → descriptiva → inferencial básico.
- **No funcionan en navegador:** `geopandas`, `rasterio`, `xgboost`, `lightgbm`, `prophet`,
  `pymc`, `torch`, `optuna` (requieren binarios nativos o motores de BD).
- **Acceso a datos:** sin descargas remotas grandes ni `load_sisaire_local()` (no hay
  filesystem local). Los demos usan datos sintéticos.

Para uso productivo o con datos reales, [instala localmente](getting-started.md):

```bash
pip install estadistica-ambiental
```

## Construcción local

El sitio JupyterLite se construye en CI (`.github/workflows/docs.yml`) antes del deploy de mkdocs.
Para reproducirlo localmente:

```bash
pip install -e ".[docs]"
jupyter lite build --contents docs/lite/files --output-dir docs/lite/_dist
mkdocs serve
```
