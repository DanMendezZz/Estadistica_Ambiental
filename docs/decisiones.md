# Registro de decisiones (ADRs)

> Cada decisión técnica o de arquitectura relevante se registra aquí.
> Formato: `## ADR-NNN — Título`, fecha, contexto, decisión, consecuencias.

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

<!-- Agregar nuevas decisiones arriba, manteniendo numeración incremental -->
