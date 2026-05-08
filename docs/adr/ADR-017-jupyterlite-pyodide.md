# ADR-017 — JupyterLite + Pyodide para notebooks ejecutables en el navegador

**Fecha:** 2026-05-07
**Estado:** Aceptado — desplegado en v1.3.2

## Contexto

Una base de conocimiento metodológica gana valor si los lectores pueden
ejecutar los ejemplos sin instalar nada. Las opciones evaluadas:

1. **Binder** (mybinder.org) — entornos efímeros con Jupyter completo. Ejecuta
   código Python real (no WASM). Limitaciones: arranque lento (1-3 min),
   colas en horas pico, sin garantía de uptime, dependiente de un servicio
   externo a la organización.
2. **Google Colab** — fácil pero requiere cuenta Google y empuja al usuario
   fuera del docs site.
3. **JupyterLite + Pyodide** — Python compilado a WebAssembly que ejecuta en el
   navegador del lector. Sin servidor, sin cuenta, integrable directamente al
   sitio mkdocs. Limitaciones: no todas las librerías corren en WASM, primera
   carga ~30-60 s (descarga del runtime).
4. **Quarto/marimo** — alternativas más nuevas que JupyterLite. Marimo todavía
   inmaduro para mkdocs; Quarto es otro stack completo.

## Decisión

**Adoptar JupyterLite + Pyodide kernel** integrado al docs site (mkdocs material).

**Build:** step `Build JupyterLite (Pyodide notebooks)` en
`.github/workflows/docs.yml` antes de `mkdocs build`. Genera estáticos en
`docs/lite/_dist/` que mkdocs sirve sin más procesamiento.

**Empaquetado del repo en Pyodide:** `lite_requirements.txt` lista lo que se
inyecta en el kernel. El paquete `estadistica-ambiental` se instala desde el
wheel publicado en PyPI.

**Demos incluidos:**
- `01_calidad_demo.ipynb` — `assess_quality` sobre serie sintética PM2.5.
- `02_tendencia_mann_kendall.ipynb` — Mann-Kendall + Sen slope.
- `03_excedencias_normativas.ipynb` — `exceedance_report` contra Res. 2254 y OMS.

Estos cubren los flujos de inferencia básicos sin requerir las dependencias
pesadas (geopandas, xgboost, prophet, pymc, torch, optuna).

**Landing page:** `docs/notebooks.md` con iframe a `lite/_dist/lab/index.html`
y caveats explícitos sobre Pyodide (primera carga, sin escritura a disco,
sin geo/ml/bayes).

## Limitaciones aceptadas

Documentadas explícitamente en `docs/notebooks.md` para no engañar al lector:

| Capacidad | Disponible en Pyodide |
| --- | --- |
| `pandas`, `numpy`, `scipy`, `statsmodels` | ✅ |
| `matplotlib`, `seaborn` | ✅ |
| `pymannkendall`, `hydroeval` | ✅ (pure Python) |
| `scikit-learn` | ✅ (oficial Pyodide) |
| `geopandas`, `rasterio`, `pyproj`, `pysal` | ❌ (requieren GDAL nativo) |
| `xgboost`, `lightgbm` | ❌ (binarios C++) |
| `prophet` | ❌ (requiere Stan) |
| `pymc`, `arviz` | ❌ (no compilan en WASM) |
| `torch`, `lightning` | ❌ |
| `optuna` | ❌ (sqlalchemy issues en Pyodide < 0.26) |

Los notebooks que dependen de estas librerías se distribuyen como `.ipynb`
descargables en `notebooks/lineas_tematicas/` y se ejecutan localmente con
`pip install estadistica-ambiental[<extra>]`.

## Consecuencias

- El docs site se vuelve **autocontenido** — sin redirección a Binder/Colab.
- El CI de docs gana ~2-3 minutos por el step de jupyter-lite build. Aceptable.
- `[docs]` extras requiere `jupyterlite-core>=0.3`,
  `jupyterlite-pyodide-kernel>=0.3`, `jupyter-server>=2.10`. Documentado.
- `mkdocs.yml` necesita `validation: { unrecognized_links: ignore }` porque
  `notebooks.md` referencia `lite/_dist/...` que no existe en el repo (se
  genera en CI). Sin este relax, `mkdocs build --strict` aborta localmente.
- El pipeline `[bayes]` y `[deep]` sigue requiriendo instalación local. La
  experiencia "ejecuta en navegador" cubre solo el subconjunto base.
- **Reevaluar** cuando Pyodide ≥ 0.27 estabilice soporte para más binarios
  (especialmente xgboost y geopandas) — entonces se podrán agregar más demos.

## Referencias

- Configs: `jupyter-lite.json`, `jupyter_lite_config.json`,
  `lite_requirements.txt`.
- Workflow: `.github/workflows/docs.yml` (step "Build JupyterLite").
- Landing: `docs/notebooks.md`.
- Demos: `docs/lite/files/*.ipynb`.
- Plan §13 entry "2026-05-07 — Release v1.3.2 + JupyterLite + Fase 10 + primer satélite".
- Commit: `a7fd911`.
