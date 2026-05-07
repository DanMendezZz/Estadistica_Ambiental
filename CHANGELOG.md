# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versiones: [Semver](https://semver.org/lang/es/).

> **Nota sobre versiones iniciales:** Las versiones v0.1.0 → v1.0.0 corresponden a las
> Fases 0-8 del plan de desarrollo, construidas durante un sprint intensivo interno
> el 2026-04-22. No representan releases incrementales independientes sino una
> consolidación retrospectiva. A partir de v1.1.0 las fechas son incrementales reales.

---

## [1.3.2] — 2026-05-07

### Agregado
- `release.yml` — JOB 6 `publish-pypi` activado con **Trusted Publishing
  (OIDC)** contra PyPI real. Pending publisher registrado en
  `pypi.org/manage/account/publishing/` para `estadistica-ambiental`.
  A partir de esta versión, cada tag `v*.*.*` publica automáticamente
  en PyPI real (además de TestPyPI).

### Corregido
- `src/estadistica_ambiental/__init__.py` — `__version__` desincronizado
  con `pyproject.toml` (estaba hardcodeado en `"1.0.0"` desde v1.0.0).
  Ahora refleja la versión real del paquete.

---

## [1.3.1] — 2026-05-07

### Corregido
- `release.yml` — el job `publish-testpypi` ahora usa **Trusted Publishing
  (OIDC)** en lugar de un token API que nunca estuvo configurado. Requiere
  registrar el publisher una vez en `test.pypi.org/manage/account/publishing/`
  (ver comentarios en el workflow).
- Sin cambios funcionales en el paquete — wheel/sdist idénticos a v1.3.0.
  Esta versión existe únicamente para validar el flujo de publicación
  automatizada con la corrección del workflow.

---

## [1.3.0] — 2026-05-07

### Agregado
- **`examples/`** — 6 scripts runnables y autocontenidos (con fallback a datos
  sintéticos): `00_quickstart`, `01_calidad_aire_pm25`, `02_oferta_hidrica_caudal`,
  `03_paramos_iuh`, `04_cambio_climatico_co2`, `05_eda_generico`. Pensados para
  onboarding rápido sin abrir un notebook completo.
- **`notebooks/showcases/calidad_aire_sisaire_real.ipynb`** — notebook end-to-end
  que consume `load_sisaire_local()` real (con fallback sintético) y recorre
  carga → validación → calidad → resampling → descriptiva → excedencias →
  Mann-Kendall → métricas → reporte HTML de cumplimiento.
- **Conectores genéricos adicionales** en `io/connectors.py`:
  - `load_datos_gov_co_dataset(dataset_id, where, select, limit, app_token)` —
    cliente SODA para `datos.gov.co/resource/<id>.json` con paginación
    `$offset`/`$limit` y soporte de `X-App-Token`.
  - `load_ideam_dhime_csv(path, parametro, fecha_col_candidates)` — lector
    robusto para exports CSV de DHIME (auto-skip de líneas de metadata,
    detección de columnas fecha/valor, fallback utf-8/latin-1, sniff de
    delimitador).
- **Documentación navegable** — sitio `mkdocs-material` + `mkdocstrings` con:
  - `mkdocs.yml` (theme Material en español, paleta light/dark, search
    multilingüe, snippets para inyectar `CHANGELOG.md`).
  - `docs/index.md`, `docs/getting-started.md`, `docs/api.md` (API reference
    auto-generada para 21 sub-módulos), `docs/changelog.md`.
  - Workflow `.github/workflows/docs.yml` para deploy automático a `gh-pages`.
  - Extra opcional `[docs]` en `pyproject.toml`.
- **Empaquetado para PyPI** — `python -m build` produce sdist + wheel limpios
  (`dist/estadistica_ambiental-1.3.0*`). `twine check` PASSED.
  Comando de upload manual: `python -m twine upload dist/estadistica_ambiental-1.3.0*`
  (requiere token PyPI configurado en `~/.pypirc` o variable de entorno
  `TWINE_PASSWORD`).
- README: nuevas secciones **"Snippets cortos por línea temática"**, **"Notebook
  end-to-end con datos reales"** y **"Documentación navegable"**.

### Tests
- 8 tests nuevos: `TestLoadDatosGovCoDataset` (4) + `TestLoadIdeamDhimeCsv` (4)
  con mocks de `requests.get` y archivos sintéticos en `tmp_path`.
- Suite total: **592 passed, 19 skipped, 4 xfailed** (sin regresiones).

### Notas
- Esta versión consolida el patrón **base ↔ satélite**: el repo expone más
  conectores y onboarding pero mantiene su rol de base de conocimiento.
  Productos finales siguen viviendo en repos satélite que pinean a este tag.

---

## [1.2.0] — 2026-05-07

### Agregado
- `io.connectors.load_sisaire_local(anios, parametro, estaciones, path)`:
  lee descargas locales del portal SISAIRE/CAR (`CAR_<año>.csv`) sin
  duplicar archivos al repo. Normaliza encabezados
  (`Estacion`→`estacion`, `Fecha inicial`→`fecha`, `PM2.5`→`pm25`),
  fallback de encoding utf-8/latin-1, errores claros si la ruta no está
  configurada.
- `config.SISAIRE_LOCAL_DIR` (`Path | None`) leído de la variable de
  entorno `SISAIRE_LOCAL_DIR`. El repo nunca asume una ruta fija.
- `NOMBRES_CORRECTOS` extendido con `FECHA INICIAL` y `FECHA FINAL`.
- README: nueva sección **"Datos reales (uso opcional, sin duplicar)"**
  y nueva sección **"Consumir desde otro proyecto"** (instalación pip+git,
  pinning a tag, patrón base ↔ repo satélite).

### Tests
- `TestLoadSisaireLocal` (8 nuevos): single year, multi-year concat, glob,
  filtro por estación, FileNotFoundError sin env, parámetro inexistente.
- Smoke test contra datos reales: 219.108 registros / 31 estaciones / 2024.

### Notas de arquitectura
- Se ratifica que este repo es **base de conocimiento + librería** —
  productos finales (dashboards Streamlit, pipelines productivos,
  reportes ejecutivos) van en repos satélite que importan
  `estadistica_ambiental` como dependencia.

---

## [1.0.0] — 2026-04-22 (primer release público — consolidación Fases 0-8)

### Agregado
- API pública completa: `from estadistica_ambiental import *` expone 20 símbolos.
- `predictive/deep.py`: LSTMModel y GRUModel con ventana deslizante y graceful ImportError.
- `predictive/spatial_models.py`: KrigingInterpolator y SpatioTemporalKriging.
- `predictive/bayesian.py`: stub BayesianARIMA y HierarchicalModel (Fase 10).
- `reporting/stats_report.py`: reporte HTML con descriptiva + ADF/KPSS + Mann-Kendall.
- LSTM y GRU registrados automáticamente en `predictive/registry.py` si PyTorch está disponible.
- `docs/fuentes/calidad_aire.md`: ficha completa extraída del NotebookLM (2026-04-22).
- `notebooks/00_plantilla_ciclo_completo.ipynb`: plantilla maestra reusable.
- 15 notebooks adicionales para Bloques A, B, C (líneas temáticas restantes).
- `CHANGELOG.md`: este archivo.

### Corregido
- `evaluation/comparison.py`: normalización invertida para métricas higher-is-better (R², NSE, KGE).

### Tests
- 199 tests en verde + 1 skip (geopandas opcional).

---

## [0.8.0] — 2026-04-22

### Agregado
- Fase 7 — Capa espacial completa: `spatial/io.py`, `projections.py`,
  `interpolation.py` (IDW + Kriging), `autocorrelation.py` (Moran, LISA), `viz.py`.
- `config.py`: normas colombianas y OMS para calidad del aire (Res. 2254/2017).
- `features/exogenous.py`: alineación de exógenas y features meteorológicos.
- `features/climate.py`: ONI/ENSO desde NOAA, clasificación niño/niña/neutro, dummies.
- `evaluation/comparison.py`: ranking multi-criterio y `select_best()`.
- `reporting/forecast_report.py`: HTML con Chart.js real vs. pronósticos.
- `docs/metodologia.md` y `docs/modelos.md`.
- Tags v0.1.0, v0.5.0, v0.8.0, v1.0.0 en GitHub.

---

## [0.5.0] — 2026-04-22

### Agregado
- Fase 5-6 — Catálogo de modelos y evaluación:
  - `predictive/ml.py`: XGBoostModel, RandomForestModel, LightGBMModel.
  - `predictive/prophet_model.py`: Prophet con exógenas.
  - `predictive/registry.py`: `get_model()`, `list_models()`, `register()`.
  - `evaluation/backtesting.py`: walk-forward expanding/sliding.
- `features/lags.py`, `features/calendar.py` con codificación cíclica.

---

## [0.1.0] — 2026-04-22

### Agregado
- Fase 0 — Estructura completa del repositorio.
- Fase 1 — `io/loaders.py`, `io/validators.py`, `eda/variables.py`,
  `eda/quality.py`, `eda/profiling.py`, `eda/viz.py`.
- Fase 2 — `descriptive/univariate.py`, `bivariate.py`, `temporal.py`;
  `inference/distributions.py`, `hypothesis.py`, `stationarity.py`,
  `trend.py`, `intervals.py`.
- Fase 3 — `preprocessing/imputation.py`, `outliers.py`, `resampling.py`;
  `predictive/base.py`, `classical.py` (ARIMA/SARIMA/SARIMAX/ETS);
  `optimization/bayes_opt.py`; `evaluation/metrics.py`.
- Fase 4 — Notebook MVP calidad del aire PM2.5 RMCAB Bogotá.
- 16 notebooks (1 MVP + 15 plantillas por línea temática).
- 4 ADRs en `docs/decisiones.md`.
- Atribución a `boa-sarima-forecaster` (TomCardeLo).
