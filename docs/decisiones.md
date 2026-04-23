# Registro de decisiones (ADRs)

> Cada decisión técnica o de arquitectura relevante se registra aquí.
> Formato: `## ADR-NNN — Título`, fecha, contexto, decisión, consecuencias.
>
> **Nota sobre fechas:** ADR-001 a ADR-010 fueron documentados el 2026-04-22 durante
> el sprint inicial de construcción del repositorio (Fases 0-8). La fecha refleja
> cuándo se formalizó la decisión, no necesariamente cuándo se tomó.

---

## ADR-001 — Herencia de boa-sarima-forecaster

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** El repositorio `boa-sarima-forecaster` de Tomás Cárdenas implementa un pipeline SARIMA con optimización Bayesiana (Optuna TPE) para pronóstico de demanda financiera. La arquitectura es modular y agnóstica al dominio.

**Decisión:** Hacer fork formal y heredar los módulos `optimizer.py`, `metrics.py`, `model.py` y `config.py`. Adaptar `preprocessor.py` y `data_loader.py` al dominio ambiental. No copiar lógica específica de SKUs/países ni la función de costo financiera (`0.7·sMAPE + 0.3·RMSLE`).

**Consecuencias:**
- Atribución explícita en README y en cada módulo heredado.
- Rama `import-from-boa` para trazabilidad.
- Deuda técnica: la función de costo debe reemplazarse (RMSLE no aplica a variables negativas).

---

## ADR-002 — Outliers opcionales por defecto

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** El módulo `standardization.py` del repo origen hace clipping a ±1σ usando moving average. En ambiente, los picos extremos son señal real (episodios de contaminación, crecidas, tormentas de polvo). Eliminarlos sesga los modelos.

**Decisión:** El módulo `preprocessing/outliers.py` tendrá clipping **desactivado por defecto**. Cualquier transformación es opt-in explícito con `clip=True`.

**Consecuencias:** Mayor fidelidad a la realidad ambiental. Los modelos deben ser robustos a valores extremos.

---

## ADR-003 — Métricas estándar por dominio

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** Las métricas del repo origen (sMAPE, RMSLE) están diseñadas para variables positivas en contexto financiero. Variables ambientales incluyen temperaturas negativas, anomalías y diferencias.

**Decisión:**
- Default general: MAE + RMSE + R²
- Hidrología: NSE (Nash-Sutcliffe) + KGE (Kling-Gupta) como métricas primarias
- Series de calidad del aire: sMAPE solo cuando PM ≥ 0 garantizado
- RMSLE: explícitamente desactivado en variables que pueden ser negativas

**Consecuencias:** `evaluation/metrics.py` necesita parámetro `domain` o checks de negatividad.

---

## ADR-004 — Ciclo estadístico como flujo obligatorio

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** La tentación en proyectos de ML es ir directo al modelo. En datos ambientales, las series tienen huecos, outliers físicos y no-estacionariedad que invalidan modelos si no se tratan.

**Decisión:** EDA es etapa obligatoria antes de la etapa predictiva. El pipeline emite error si se intenta ejecutar modelos sin pasar por `eda/quality.py`. Las pruebas de estacionariedad (ADF + KPSS) son obligatorias antes de ARIMA.

**Consecuencias:** Mayor fricción inicial; menor riesgo de modelos entrenados sobre datos corruptos.

---

## ADR-005 — Normas colombianas centralizadas en config.py

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** Las normas ambientales colombianas estaban dispersas o ausentes en el código. Cada notebook o función las repetía como constantes locales, generando inconsistencias.

**Decisión:** Todas las normas regulatorias colombianas se centralizan en `config.py` como diccionarios con nombre explícito:
- `NORMA_CO` — Res. 2254/2017 (calidad del aire)
- `NORMA_OMS` — Guías OMS 2021
- `NORMA_AGUA_POTABLE` — Res. 2115/2007
- `NORMA_VERTIMIENTOS` — Res. 631/2015
- `IUA_THRESHOLDS`, `IRH_THRESHOLDS`, `ICA_CATEGORIES` — índices hídricos IDEAM
- `ENSO_THRESHOLDS`, `ENSO_LAG_MESES` — clasificación ONI y lags por línea
- `DEFORESTACION_ALERTAS`, `RANGO_TEMP_ECOSISTEMA` — umbrales SMByC y temperatura por ecosistema

**Consecuencias:** Un único punto de verdad para umbrales normativos. Cambiar una norma (ej. actualización de la Res. 2254) requiere modificar solo `config.py`.

---

## ADR-006 — Validación de rangos físicos con especificidad por línea temática

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** El validador original tenía rangos genéricos para 30 variables. Al aplicarse a líneas temáticas específicas (páramos, oferta hídrica subterránea), los rangos eran incorrectos: temperatura del páramo tiene máx. 16°C, no 45°C; conductividad de aguas subterráneas llega a 3000 µS/cm, no 5000.

**Decisión:** `validators.py` mantiene `PHYSICAL_RANGES` como base (74 variables) más un diccionario `_LINEA_RANGES` con sobrescrituras por línea. `validate()` acepta el parámetro `linea_tematica=` que aplica los rangos específicos antes que los personalizados:

```python
validate(df, date_col="fecha", linea_tematica="paramos")
```

**Consecuencias:** Más falsos positivos eliminados. El analista recibe advertencias relevantes para su dominio específico en lugar de alertas genéricas.

---

## ADR-007 — Lags ENSO diferenciados por línea temática

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** La función `enso_dummy()` aplicaba el ONI sin lag. La respuesta hidrológica/ambiental al ENSO varía por ecosistema: páramos responden en ~2 meses, cuencas andinas en ~4 meses, calidad del aire en ~2 meses.

**Decisión:** Se crea `enso_lagged()` en `features/climate.py` que aplica el lag correspondiente desde `config.ENSO_LAG_MESES` según la línea temática. El lag es configurable explícitamente si el analista tiene evidencia específica:

```python
enso_lagged(df, oni, date_col="fecha", linea_tematica="oferta_hidrica")  # lag=4 automático
enso_lagged(df, oni, date_col="fecha", lag_meses=6)                      # override manual
```

Se agrega también `_classify_enso_intensity()` que distingue eventos moderados de fuertes (umbral ±1.5 ONI).

**Consecuencias:** Covariables ENSO más representativas para cada modelo. Los notebooks regenerados incluyen la celda ENSO solo en las líneas donde aplica.

---

## ADR-008 — Reporte de cumplimiento normativo como artefacto separado

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** El `forecast_report.py` solo muestra métricas predictivas. Para las entidades ambientales colombianas, el producto más importante no es el pronóstico sino saber si los datos superan las normas (Resoluciones, Guías OMS, IUA crítico).

**Decisión:** Se crea `reporting/compliance_report.py` con `compliance_report()` que genera un HTML independiente con:
- Semáforo por variable (verde/amarillo/rojo según excedencias)
- Tabla de excedencias con cada norma colombiana aplicable, umbral, tipo (mínimo/máximo) y período de retorno
- Series temporales con línea de norma superpuesta
- Contexto de dominio extraído de `docs/fuentes/<linea>.md`

La lógica de cálculo vive en `inference/intervals.py::exceedance_report()` (testeable de forma aislada). El reporte es el envoltorio HTML.

**Consecuencias:** Separación entre lógica estadística (testeable) y presentación (HTML). `exceedance_report()` puede usarse sin generar HTML.

---

## ADR-009 — Conectores a fuentes de datos ambientales colombianas como módulo io

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** Las 16 fichas de dominio referencian consistentemente las mismas fuentes de datos oficiales (IDEAM DHIME, RMCAB, SIATA, OpenAQ, SMByC, datos.gov.co). Sin conectores estandarizados, cada notebook reimplementa el acceso de forma ad-hoc.

**Decisión:** Se crea `io/connectors.py` con conectores para cada fuente. Las fuentes con API pública (OpenAQ v3) devuelven DataFrames directamente. Las fuentes sin API (IDEAM DHIME) proveen un loader flexible para archivos descargados manualmente con instrucciones claras en el docstring.

**Consecuencias:** Un punto único de acceso a datos. Las instrucciones de descarga manual están en el código (docstring), no en documentación externa que se desactualiza.

---

## ADR-010 — Correcciones de correctitud en módulos de calidad del aire (PR #6)

**Fecha:** 2026-04-22
**Estado:** Aceptado

**Contexto:** La revisión automatizada (ultrareview) de la rama `review/air-quality-modules` detectó 10 bugs de correctitud en los módulos `evaluation/metrics.py`, `evaluation/anomaly.py`, `optimization/bayes_opt.py`, `predictive/base.py` y `preprocessing/air_quality.py`. Ninguno causaba crash; todos producían resultados silenciosamente incorrectos.

**Decisiones tomadas:**

1. **Breakpoints ICA por contaminante** — `evaluate()`, `hit_rate_ica()` y `walk_forward()` aceptan `pollutant='pm25'`. El helper `_get_ica_breakpoints()` importa `_ICA_BREAKPOINTS` de `preprocessing/air_quality.py` (fuente única de verdad de Res. 2254/2017). Antes, PM10, O3, NO2, SO2 y CO recibían silenciosamente los umbrales de PM2.5.

2. **NaN en métricas de calidad del aire** — `hit_rate_ica()` filtra pares NaN antes de categorizar (igual que `evaluate()`). `detect_anomalies()` usa `np.nanmean`/`np.nanstd` en lugar de `np.mean`/`np.std`; guarda `umbral` y `threshold` en `df.attrs` para que `anomaly_summary()` reporte el umbral exactamente aplicado.

3. **`nrmse` con varianza cero** — Retorna `float('nan')` cuando `std(y_true) < 1e-10`, consistente con `r2`, `mase`, `kge` y `pbias`. La alternativa (epsilon `1e-8`) producía valores astronómicos que colapsaban el ranking min-max de `rank_models`.

4. **Penalidad de Optuna sign-aware** — `objetivo_robusto` usa `penalty = ±OPTIMIZER_PENALTY` según `direction`. Para `direction='maximize'` (R², KGE, NSE, `hit_rate_ica`), devolver `+1e6` hacía que TPE convergiera hacia configuraciones que lanzaban excepciones. `OptimizationResult.__post_init__` usa `abs(best_score)` para el sentinel check.

5. **`TrialPruned` re-lanzado** — `except optuna.TrialPruned: raise` antes del catch genérico. Sin esto, el `MedianPruner` configurado explícitamente en el código era completamente inoperante.

6. **Fallback preserve best** — El branch de excepción de `optimize_model` consulta `study.best_trial` antes de caer al `warm_starts[0]`. `n_trials` reporta `len(study.trials)` (reales ejecutados), no el presupuesto pedido. `build_model` usa `best_p or {}` en lugar de `best_p` (falsiness guard incorrecta para dict vacío).

7. **`flag_spatial_episodes` determinismo** — `mask_vec_mes` filtra por `flag_episode == 'original'`, excluyendo valores `cap_absoluto` y medianas ya imputadas de iteraciones anteriores. El mismo filtro ya se aplicaba al pivot (línea 259) — se extendió al loop interno.

8. **Mediana de imputación limpia** — Paso 3 de `flag_spatial_episodes` pre-determina `idx_hard` e `idx_soft` antes de cualquier imputación, NaN-maskea esas posiciones en `serie_clean`, y usa una sola `mediana_local` para ambos grupos. Antes, el rolling window incluía los propios outliers a reemplazar.

**Consecuencias:** 21 tests de regresión en `tests/test_regression_pr6.py` protegen cada corrección. La API pública de `evaluate`, `hit_rate_ica`, `walk_forward` y `anomaly_summary` es retrocompatible (parámetros nuevos con defaults que reproducen el comportamiento anterior correcto). El comportamiento anterior incorrecto no era semánticamente válido, por lo que no se necesita deprecation period.

---

<!-- Agregar nuevas decisiones arriba, manteniendo numeración incremental -->
