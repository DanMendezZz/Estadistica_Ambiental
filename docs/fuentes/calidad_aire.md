# Calidad del Aire

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/96050780-400c-4522-945a-211c406dc516
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** B (transversal temática) — Alimenta: gestión de riesgo, sistemas de información ambiental

---

## Resumen ejecutivo

El notebook es una colección de estudios científicos sobre monitoreo, predicción y gestión de calidad del aire con foco en PM2.5. Cubre el ciclo completo: desde preprocesamiento de redes de sensores defectuosos hasta arquitecturas avanzadas de deep learning para pronóstico espacio-temporal, pasando por integración de datos satelitales AOD y sistemas de alerta temprana IoT.

El enfoque dominante es la transición de modelos estadísticos clásicos (ARIMA, regresión) hacia híbridos neuronales, con validación rigurosa por RMSE, MAE, R² y métricas específicas de dominio.

---

## Objetivos

- Monitorear concentraciones de PM2.5, PM10, O3, NO2, CO y SO2 en redes de sensores.
- Predecir episodios de contaminación con anticipación suficiente para alertas tempranas.
- Estimar concentraciones en zonas sin estaciones mediante interpolación satelital y espacial.
- Cuantificar impacto en salud pública y apoyar cumplimiento de normas ambientales.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| PM2.5 | µg/m³ | 0–500 | Horaria / diaria | RMCAB, SIATA, EPA |
| PM10 | µg/m³ | 0–600 | Horaria / diaria | Mismas redes |
| O3 | µg/m³ | 0–600 | Horaria | Estaciones fijas |
| NO2 | µg/m³ | 0–400 | Horaria | Estaciones fijas |
| CO | mg/m³ | 0–50 | Horaria | Estaciones fijas |
| SO2 | µg/m³ | 0–500 | Horaria | Estaciones fijas |
| AOD | adim. | 0–2 | Diaria | MODIS, MISR (satélite) |
| AQI / ICA | índice | 0–500 | Horaria | Calculado |
| Temperatura | °C | –5 a 40 | Horaria | Meteorología |
| Humedad relativa | % | 0–100 | Horaria | Meteorología |
| Velocidad viento | m/s | 0–15 | Horaria | Meteorología |
| Precipitación | mm | 0–100 | Horaria | Meteorología |
| Presión | hPa | 700–1013 | Horaria | Meteorología |

---

## Datos y fuentes

- **Colombia:** RMCAB (Bogotá), SIATA (Antioquia), AMVA, DAGMA (Cali), IDEAM/SISAIRE.
- **Global:** OpenAQ (https://openaq.org) — datos horarios en JSON/CSV.
- **Satélite:** NASA Giovanni (MODIS/MISR), Copernicus CAMS.
- **Modelos de transporte químico:** CMAQ, GEOS-Chem (covariables regionales).
- **Sensores de bajo costo:** PurpleAir, SDS011 — requieren calibración contra referencia.

---

## Indicadores y métricas oficiales

### ICA Colombia — Resolución 2254/2017 (concentraciones reales en µg/m³)

> ⚠️ **Error frecuente:** el ICA colombiano opera en **concentraciones de contaminante (µg/m³)**,
> no en la escala adimensional AQI 0–500 de EPA/US. Los umbrales de abajo son los que
> usa `exceedance_report()` y `hit_rate_ica()` en el repositorio.

| Categoría | PM2.5 (µg/m³) | Color oficial |
|---|---|---|
| Buena | 0 – 12 | `#00E400` verde |
| Aceptable | 12 – 37 | `#FFFF00` amarillo — **umbral norma 24h** |
| Dañina sensibles | 37 – 55 | `#FF7E00` naranja |
| Dañina | 55 – 150 | `#FF0000` rojo |
| Muy dañina | 150 – 250 | `#8F3F97` morado |
| Peligrosa | 250 – 500 | `#7E0023` marrón |

Los colores son **obligatorios en reportes a entidades regulatorias** (CAR, MinAmbiente).
Para PM10, O3, NO2, SO2 y CO los breakpoints están en `config.py → NORMA_CO` y en
`preprocessing/air_quality.py → _ICA_BREAKPOINTS`.

- **Resolución 2254/2017:** PM2.5 anual = 25 µg/m³; PM2.5 24h = 37 µg/m³.
- **Guías OMS 2021:** PM2.5 anual = 5 µg/m³; PM2.5 24h = 15 µg/m³ (más estrictas).

---

## Normativa aplicable (Colombia)

- **Resolución 2254/2017 — MinAmbiente:** Norma nacional de calidad del aire.
- **Decreto 948/1995:** Prevención y control de la contaminación atmosférica.
- **Ley 99/1993 art. 73:** Criterios de calidad ambiental.
- **Protocolo de Monitoreo IDEAM (2010):** Operación de redes y reportes.

---

## Preguntas analíticas típicas

1. ¿Cuántos días al año supera la norma de 24h (37 µg/m³) o la guía OMS (15 µg/m³)?
2. ¿Cuál es la tendencia interanual de PM2.5? (Mann-Kendall + Sen's slope)
3. ¿Qué variables meteorológicas tienen mayor correlación con PM2.5?
4. ¿Es la serie estacionaria? (ADF + KPSS — ADR-004)
5. ¿Qué episodios son contaminación extrema vs. errores de sensor?
6. ¿Hay diferencia significativa entre estaciones o períodos? (t-test / Mann-Whitney)
7. ¿Con qué modelo se puede pronosticar PM2.5 con menor RMSE para 24–72h?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Distribución: lognormal o gamma (cola derecha pesada).
- Estacionariedad: ADF + KPSS obligatorio antes de ARIMA.
- Tendencia: Mann-Kendall + Sen's slope.
- Punto de cambio: Pettitt.
- Excedencias: `inference/intervals.py → exceedance_probability()`.
- Correlación con meteorología: Spearman.

**Imputación de faltantes (por complejidad):**
1. Interpolación lineal — gaps ≤ 3h.
2. Rolling mean (ventana 24h) — gaps medianos.
3. MICE — gaps largos con otras variables disponibles.
4. BRITS / SAITS / GAIN — gaps extremos (>40%).

**Predictiva — jerarquía empírica para PM2.5 horario (validada con datos SISAIRE CAR 2016-2026):**

| Modelo | RMSE típico | HitRate ICA | Rol recomendado |
|---|---|---|---|
| RF / XGBoost / LGB | ~3.7 µg/m³ | ~88% | **Producción** — 32 lag/calendar features |
| AR(1) doble-escala | — | — | Pronóstico con bandas P10/P50/P90 sin reentrenar el RF |
| SARIMAX | ~4.5 µg/m³ | ~75% | Con covariables meteorológicas horarias disponibles |
| SARIMA | ~5.9 µg/m³ | ~69% | **Solo como benchmark estadístico** — no para producción |
| Prophet | variable | — | Estacionalidades múltiples o eventos especiales; NO para series horarias |
| LSTM / GRU | ~10 µg/m³ | ~63% | Necesita >5 años + GPU; última opción |

> **Hallazgo clave (pipeline CAR 2026):** SARIMA es el modelo más débil para PM2.5
> horario — no captura la autocorrelación diaria (ACF significativo hasta lag 48–72h)
> y es computacionalmente prohibitivo en producción.
> XGBoost con lag features es el benchmark real. SARIMAX solo compite cuando se
> tienen covariables meteorológicas horarias completas y sin gaps.

**Nota metodológica — walk-forward con gap para series horarias:**
```python
# OBLIGATORIO para PM2.5 horario (ACF≈0.97 en lag-1h):
walk_forward(model, y, gap=24, n_splits=4)
# Sin gap, R² se infla 8-40 puntos porcentuales por leakage de autocorrelación.
```

**Espacial:**
- Kriging ordinario / universal.
- IDW (más rápido).
- LUR (Land Use Regression) para exposición urbana.
- I de Moran antes de modelos espaciales.

---

## Métodos identificados en el NotebookLM

### Imputación
Media, mediana, moda; Forward/Backward Fill; interpolación lineal;
KNN; MICE; Regresión; MissForest; BRITS; SAITS; GRIN; DynamicSeq2SeqXGB; GAIN/DEGAIN.

### Series de tiempo
VAR, ARIMA, SARIMA, SARIMAX, Prophet, NeuralProphet, STL+ARIMA.

### ML / DL forecasting
RF, XGBoost, LightGBM, Extra Trees, ANN/MLP, ELM, RNN, LSTM, GRU,
Bi-LSTM, Bi-GRU, CNN-LSTM, CNN-GRU, GC-LSTM (espacio-temporal).

### Estadística espacial
GWR, LUR, Kriging universal, Mixed-Effect Models (calibración AOD).

### Métodos complementarios
Descomposición: EMD, EEMD, CEEMDAN, Wavelet. PCA. Fuzzy Logic.
SHAP / LIME (interpretabilidad). Wasserstein Distance. TOST. Diebold-Mariano.

### Métricas de evaluación
RMSE, MAE, R², MAPE, PBIAS, MSE, NSE, Willmott Index, a20-index, TIC, CRPS.

---

## Actores institucionales

| Actor | Rol |
|---|---|
| IDEAM | Norma, SISAIRE, datos históricos nacionales |
| SDA Bogotá | Operación RMCAB |
| SIATA | Red Antioquia-Valle de Aburrá, alertas tempranas |
| MinAmbiente | Regulación (Res. 2254/2017) |
| Alcaldías | Planes de descontaminación |

---

## Riesgos y sesgos en los datos

- **Congelamiento de sensor:** detectar con `eda/quality.py → FreezeInfo`.
- **Deriva del sensor:** especialmente en sensores de bajo costo sin mantenimiento.
- **Gaps por mantenimiento:** patrón MAR — imputar con MICE o rolling mean.
- **PM2.5 > PM10:** error físico imposible — detectar con `io/validators.py` cross-checks.
- **Episodios reales vs. errores:** incendios, festivos, Semana Santa — NO eliminar (ADR-002).
- **Escasez rural:** redes urbanas sobrerepresentadas; usar Kriging para zonas sin cobertura.

---

## Glosario mínimo

- **PM2.5:** Partículas ≤ 2.5 µm. Penetran alvéolos pulmonares.
- **AOD:** Aerosol Optical Depth — medida satelital de partículas en columna atmosférica.
- **AQI / ICA:** Índice de Calidad del Aire — escala 0–500.
- **CMAQ:** Community Multiscale Air Quality — modelo de transporte químico EPA.
- **RMCAB:** Red de Monitoreo de Calidad del Aire de Bogotá.
- **SIATA:** Sistema de Alerta Temprana de Medellín y el Valle de Aburrá.
- **LUR:** Land Use Regression — modelo de exposición urbana.
- **MAR:** Missing At Random — faltantes relacionados con otras variables observadas.
- **MNAR:** Missing Not At Random — faltantes relacionados con el propio valor.

---

## Buenas prácticas metodológicas (lecciones del pipeline SISAIRE CAR 2016-2026)

> Estas lecciones surgieron del análisis de 34 estaciones y ~1.350.000 registros horarios
> de PM2.5 en Cundinamarca. Son transferibles a cualquier red de monitoreo de calidad del aire.

### BP-1 — Walk-forward con gap obligatorio para series horarias

Series con ACF alta (ACF≈0.97 en lag-1h para PM2.5) producen R² inflado si el set de
entrenamiento termina en `t` y el test comienza en `t+1`. Usar `gap=24h` como mínimo:

```python
walk_forward(model, y, horizon=8760, n_splits=4, gap=24)
# Evidencia: LC gap bajó de 0.38 a 0.048 al implementar gap=24h en RF.
```

### BP-2 — Corrección de sesgo por quarter (no por mes) para régimen andino bimodal

Colombia (zona andina) tiene dos ciclos secos y dos lluviosos. La corrección mensual sobreajusta.
Usar corrección por trimestre calibrada sobre residuos del backtesting:

```python
BIAS_QUARTER = {1: +0.03, 2: -0.15, 3: -0.23, 4: -0.07}  # µg/m³, Cundinamarca 2025
pred["predicho_corr"] = pred.apply(
    lambda r: r["predicho"] + BIAS_QUARTER.get(r["quarter"], 0), axis=1)
```

### BP-3 — Criterio de ranking multi-métrica para calidad del aire

El RMSE global mezcla estaciones con escalas distintas (media 8–25 µg/m³ por estación).
Score validado en 34 estaciones SISAIRE:

```
score = 0.30 × RMSE_normalizado      # RMSE / media_estación
      + 0.10 × NRMSE                  # escala-invariante
      + 0.25 × HitRate_ICA            # % días en categoría correcta
      + 0.20 × F1_weighted            # F1 multi-clase ICA
      + 0.15 × Recall_gt55            # recall episodios críticos >55 µg/m³
```

El 15% en `Recall_gt55` es el diferenciador crítico para alertas tempranas:
XGBoost detectó 15.5% de episodios >55 µg/m³ vs. 0% de SARIMA.

### BP-4 — Outliers vs. episodios críticos: validación espacial

Un pico IQR×3.0 sostenido ≥4h con ≥1 estación vecina (dentro de 50km) también elevada
→ episodio real: PRESERVAR con `flag='episodio_critico'`.
Sin confirmación espacial → error de sensor: reemplazar con mediana local limpia.
Ratio estimado en SISAIRE 2016-2026: ~15% de outliers IQR×3 son episodios reales (ADR-002).

### BP-5 — Criterio de exclusión por cobertura en entrenamiento

Si `flag_imputacion != 'original'` > 30% del período → excluir la estación del entrenamiento.
Los datos siguen disponibles para análisis descriptivo y reportes de cobertura.
KNN con >30% de gaps introduce patrones sintéticos que sesgan el modelo.

### BP-6 — Renombres y discontinuidades históricas en ETL

Aplicar dict de normalización de nombres de estaciones **antes** de cualquier join/merge.
En SISAIRE/CAR se encontraron 3 renombres confirmados (2026):
- `TAUSA - ESCUELA` → `TAUSA - URBANO`
- `FUNZA - COLEGIO` → `MOSQUERA - URBANO`
- `NEMOCÓN - PATIO BONITO` → excluir (falla de sensor documentada)

Este patrón aplica igualmente a redes de caudales (IDEAM/DHIME) y estaciones meteorológicas.

### BP-7 — Período de retorno de excedencias como métrica de gestión

Complementa `exceedance_report()` con una métrica intuitiva para gestores:

```python
def exceedance_return_period(series_daily, threshold=37):
    """Período de retorno de un día con PM2.5 > umbral (en días)."""
    pct = (series_daily > threshold).mean()
    return round(1 / pct, 1) if pct > 0 else float('inf')
# Ejemplo: 8.3% días > norma → T_retorno ≈ 12 días
```

---

## Preguntas abiertas / oportunidades

- Calibración automática de sensores de bajo costo vs. estaciones de referencia.
- Modelos bayesianos jerárquicos multi-estación para incertidumbre espacial.
- ENSO/ONI como covariables en SARIMAX (vía `features/climate.py`).
- Nowcasting con datos satelitales en tiempo real para zonas sin cobertura.
- Sistemas de alerta temprana con threshold dinámico adaptado a meteorología.
- Source apportionment con PMF o análisis factorial.

---

## Referencias

- Resolución 2254/2017 — Ministerio de Ambiente y Desarrollo Sostenible, Colombia.
- WHO Air Quality Guidelines 2021 — World Health Organization.
- IDEAM. Protocolo para el Monitoreo y Seguimiento de la Calidad del Aire, 2010.
- Ver NotebookLM fuente para referencias científicas completas.
