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

<!-- Agregar nuevas decisiones arriba, manteniendo numeración incremental -->
