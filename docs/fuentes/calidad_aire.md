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

- **ICA Colombia:** Buena (0–25), Aceptable (26–50), Dañina sensibles (51–100), Dañina (101–150), Muy dañina (151–200), Peligrosa (>200).
- **Resolución 2254/2017:** PM2.5 anual = 25 µg/m³; 24h = 37 µg/m³.
- **Guías OMS 2021:** PM2.5 anual = 5 µg/m³; 24h = 15 µg/m³ (más estrictas).

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

**Predictiva (MVP):**
- SARIMA — baseline; estacionalidad diaria/semanal/anual.
- SARIMAX — SARIMA + meteorología (mejora documentada en literatura).
- Prophet — múltiples estacionalidades, robusto a outliers.
- XGBoost / LightGBM — con lag features + calendario.
- LSTM / GRU — horizontes cortos (1–24h) con datos horarios.

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
