# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versiones: [Semver](https://semver.org/lang/es/).

> **Nota sobre versiones iniciales:** Las versiones v0.1.0 → v1.0.0 corresponden a las
> Fases 0-8 del plan de desarrollo, construidas durante un sprint intensivo interno
> el 2026-04-22. No representan releases incrementales independientes sino una
> consolidación retrospectiva. A partir de v1.1.0 las fechas son incrementales reales.

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
