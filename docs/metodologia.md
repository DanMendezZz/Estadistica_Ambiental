# Metodología — Estadística Ambiental

> Describe el ciclo estadístico implementado, las decisiones de diseño y
> la relación con el repositorio origen `boa-sarima-forecaster`.

---

## 1. Ciclo estadístico completo

El repositorio implementa cuatro etapas encadenables e independientes:

```
Datos crudos
   ↓ io/loaders.py + io/validators.py
EDA → catálogo de variables + calidad + reporte HTML
   ↓ eda/variables.py + eda/quality.py + eda/profiling.py + eda/viz.py
Estadística descriptiva → resúmenes, correlaciones, STL, ACF
   ↓ descriptive/univariate.py + bivariate.py + temporal.py
Estadística inferencial → distribuciones, hipótesis, estacionariedad, tendencia
   ↓ inference/distributions.py + hypothesis.py + stationarity.py + trend.py + intervals.py
[Análisis espacial] → Kriging, Moran, GWR
   ↓ spatial/
Feature engineering → lags, calendario, exógenas, ENSO
   ↓ features/
Preprocesamiento → imputación, outliers, remuestreo
   ↓ preprocessing/
Modelos predictivos → ARIMA, SARIMA, SARIMAX, Prophet, XGBoost, RF, LSTM
   ↓ predictive/ + optimization/
Backtesting + comparación multi-criterio
   ↓ evaluation/
Reporte final HTML
   ↓ reporting/
```

---

## 2. Módulos y responsabilidades

### 2.1 Ingesta (`io/`)

| Módulo | Responsabilidad |
|---|---|
| `loaders.py` | Lectura multiformato: CSV, Excel, Parquet, NetCDF, SHP/GPKG |
| `validators.py` | Rangos de plausibilidad física para 30+ variables colombianas |

### 2.2 EDA (`eda/`)

| Módulo | Responsabilidad |
|---|---|
| `variables.py` | Tipificador automático: 7 tipos (continua, discreta, nominal, ordinal, temporal, espacial, texto) |
| `quality.py` | MCAR/MAR/MNAR, gaps temporales, congelamiento de sensor, cross-checks |
| `profiling.py` | Reporte HTML autocontenido + integración opcional ydata-profiling/sweetviz |
| `viz.py` | 8 funciones estándar (series, faltantes, histograma, boxplot, correlación, estacional, multi-series, scatter) |

### 2.3 Preprocesamiento (`preprocessing/`)

| Módulo | Responsabilidad |
|---|---|
| `imputation.py` | 8 métodos: ffill, bfill, linear, mean, median, rolling_mean, Kalman, MICE |
| `outliers.py` | IQR, z-score, modified z-score — solo flags por default (ADR-002) |
| `resampling.py` | Remuestreo, alineación de frecuencias, timestamps faltantes |

### 2.4 Descriptiva (`descriptive/`)

| Módulo | Responsabilidad |
|---|---|
| `univariate.py` | Resumen completo con agrupación; tabla de frecuencias |
| `bivariate.py` | Correlación (Pearson/Spearman/Kendall), contingencia, chi-cuadrado |
| `temporal.py` | STL, ACF, PACF, rolling stats, resumen estacional |

### 2.5 Inferencial (`inference/`)

| Módulo | Responsabilidad |
|---|---|
| `distributions.py` | Normalidad (Shapiro-Wilk, KS, Anderson-Darling), ajuste a 6 distribuciones |
| `hypothesis.py` | t-test Welch, Mann-Whitney, ANOVA, Kruskal-Wallis |
| `stationarity.py` | ADF + KPSS con diagnóstico conjunto (ADR-004) |
| `trend.py` | Mann-Kendall, Sen's slope, Pettitt |
| `intervals.py` | IC paramétrico (media), bootstrap (mediana, cuantiles), excedencia de norma |

### 2.6 Espacial (`spatial/`)

| Módulo | Responsabilidad |
|---|---|
| `io.py` | Lectura de vectores (SHP/GPKG/GeoJSON), raster (GeoTIFF), NetCDF |
| `projections.py` | MAGNA-SIRGAS, CTM12, WGS84; clip a Colombia |
| `interpolation.py` | IDW (puro numpy), Kriging ordinario (pykrige) |
| `autocorrelation.py` | Índice de Moran global y local LISA (pysal/esda) |
| `viz.py` | Mapas folium de estaciones, coropletas, resultado de Kriging |

### 2.7 Features (`features/`)

| Módulo | Responsabilidad |
|---|---|
| `lags.py` | Lags, rolling stats, diferencias |
| `calendar.py` | Variables de calendario con codificación cíclica seno/coseno |
| `exogenous.py` | Alineación de exógenas, heat index, features meteorológicos |
| `climate.py` | ONI (ENSO) desde NOAA, clasificación niño/niña/neutro, dummies |

### 2.8 Predictiva (`predictive/`)

| Módulo | Responsabilidad |
|---|---|
| `base.py` | `BaseModel` ABC con interfaz `fit/predict/fit_predict` |
| `classical.py` | ARIMA, SARIMA, SARIMAX, ETS (statsmodels) |
| `prophet_model.py` | Prophet con exógenas opcionales |
| `ml.py` | XGBoost, RandomForest, LightGBM con lag features automáticos |
| `registry.py` | `get_model()`, `list_models()`, `register()` |

### 2.9 Evaluación (`evaluation/`)

| Módulo | Responsabilidad |
|---|---|
| `metrics.py` | MAE, RMSE, R², sMAPE, MASE + NSE, KGE, PBIAS (hidrología) |
| `backtesting.py` | Walk-forward expanding/sliding; `compare_backtests()` |
| `comparison.py` | Ranking multi-criterio por dominio; `select_best()` |

### 2.10 Reportes (`reporting/`)

| Módulo | Responsabilidad |
|---|---|
| `forecast_report.py` | HTML con métricas, gráfico Chart.js real vs. pronósticos |
| `eda_report.py` | (ver `eda/profiling.py`) |

---

## 3. Herencia de boa-sarima-forecaster

Ver `docs/decisiones.md` ADR-001 y tabla de equivalencias en `README.md`.

Los módulos con mayor herencia son `optimization/bayes_opt.py`,
`evaluation/metrics.py` y `predictive/classical.py`.

---

## 4. Decisiones de diseño clave

Ver `docs/decisiones.md` para el registro completo (ADRs).

| ADR | Decisión |
|---|---|
| ADR-001 | Fork y herencia de boa-sarima-forecaster con atribución explícita |
| ADR-002 | Outliers NO se eliminan automáticamente — picos ambientales son señal real |
| ADR-003 | Métricas por dominio: NSE+KGE para hidrología, sMAPE solo cuando y≥0 |
| ADR-004 | ADF+KPSS obligatorios antes de ARIMA; advertencia explícita si no estacionaria |
