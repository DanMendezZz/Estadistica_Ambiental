# ADR-016 — PyMC como motor bayesiano para Fase 10 (BayesianARIMA + HierarchicalModel)

**Fecha:** 2026-05-07
**Estado:** Aceptado — implementado en v1.3.2

## Contexto

La Fase 10 §10.3 del Plan declaraba "modelos bayesianos PyMC" como ítem futuro,
con el objetivo de cuantificar incertidumbre en pronósticos hidrológicos y
calidad del aire. El módulo `predictive/bayesian.py` existía como stub
(`raise NotImplementedError`) hasta v1.3.1. La pregunta de diseño era doble:
(1) qué motor de inferencia usar (PyMC vs. Stan vs. NumPyro vs. statsmodels
con Bayes empírico), y (2) qué API exponer al usuario sin forzar el aprendizaje
de un DSL probabilístico completo.

## Decisión

**Motor:** **PyMC ≥ 5.9** (no Stan, no NumPyro). Razones:

- API pythonic — no requiere compilar código C++/Stan ni manejar archivos
  externos. El usuario que ya conoce numpy/scipy puede leer y modificar el
  modelo sin aprender un DSL.
- Stack compatible con el resto del repo (numpy, pandas, scipy, statsmodels).
- ArviZ ≥ 0.18 ofrece diagnósticos posterior (R-hat, ESS, traces) integrados
  con xarray, que también usamos en `spatial/` y `predictive/spatial_models`.
- Comunidad activa, documentación en español y ejemplos ambientales/hidrológicos
  preexistentes (Bayesian hydrology, ENSO inference).
- NumPyro (JAX) ofrece más velocidad pero exige instalación de JAX que no se
  puede empaquetar en Pyodide (ver ADR-017) ni distribuir trivialmente vía
  PyPI con wheels para Windows. PyMC sí.

**API expuesta:**

- `BayesianARIMA(p, d, q)` — modelo individual con priors `Normal(0, 1)` para
  AR/MA y `HalfNormal(1)` para σ. Diferenciación de orden d aplicada antes de
  pasar a PyMC; inversión recursiva al simular posterior.
- `HierarchicalModel(group_col)` — partial pooling con `mu_global ~ Normal(0, 10)`,
  `sigma_global ~ HalfNormal(5)` y `mu_group[i] ~ Normal(mu_global, sigma_global)`.
  Compromiso entre no pooling (un modelo por estación) y complete pooling (un
  solo modelo global).
- Ambas clases auto-registradas en `predictive/registry.py` como `bayesian_arima`
  y `hierarchical` cuando `PYMC_AVAILABLE`. Si `pymc` no está instalado, levantan
  `ImportError` claro al construir, no al importar.
- `summary()`, `plot_trace()`, `posterior_predictive_interval()` como helpers
  para diagnóstico y reporte.

**Distribución:** `pymc` y `arviz` viven en el extras opcional `[bayes]`. La
instalación base no los descarga — `pip install estadistica-ambiental[bayes]`
los habilita.

## Justificación de los priors

Los priors elegidos son **débilmente informativos** y conservadores:

- AR/MA con `Normal(0, 1)` — neutro respecto a memoria persistente vs.
  oscilatoria. Centrado en 0 (sin asumir tendencia direccional).
- σ con `HalfNormal(1)` — concentrado en valores pequeños pero con cola hasta
  ~3-5 desviaciones estándar (suficiente para variables ambientales escaladas).
- `mu_global ~ Normal(0, 10)` y `sigma_global ~ HalfNormal(5)` — anchos lo
  suficiente para no constreñir grupos heterogéneos (ej. estaciones urbanas
  vs. rurales).

Estos priors deben re-escalarse si el usuario trabaja con variables crudas en
unidades naturales (mg/L, µg/m³) — recomendado estandarizar antes de pasar a
los modelos. Documentado en docstring.

## Consecuencias

- **Cobertura de tests:** 26 tests bayesianos en `tests/test_bayesian.py`, todos
  con `pytest.importorskip("pymc")` para ejecutar solo cuando `[bayes]` está
  instalado. El CI principal no exige PyMC; un job dedicado lo verifica.
- **Performance:** muestreo NUTS típico para series N≈500 toma 30-60 s en CPU.
  Documentado en docstring. Para N > 5000 advertir explícitamente o sugerir
  `nuts_sampler="nutpie"` en una iteración futura.
- **Limitaciones aceptadas:** PyMC no funciona en Pyodide / JupyterLite (ADR-017).
  Los demos bayesianos no estarán disponibles en el navegador del docs site;
  van como notebook descargable en `notebooks/lineas_tematicas/`.
- **Reevaluar** si emerge un caso de uso real con N > 50_000 observaciones
  jerárquicas (entonces NumPyro/JAX entra en discusión).

## Referencias

- Implementación: `src/estadistica_ambiental/predictive/bayesian.py` (~430 líneas).
- Tests: `tests/test_bayesian.py` (`TestBayesianARIMASpec`, `TestHierarchicalModelSpec`,
  `TestBayesianRegistry`, `TestImportErrorWhenPymcMissing`).
- Plan §13 entry "2026-05-07 — Release v1.3.2 + JupyterLite + Fase 10 (PyMC) + primer satélite".
- Commit: `a583eb5`.
