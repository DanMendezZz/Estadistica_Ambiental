# Plan de Trabajo — Repositorio Estadística Ambiental

> Documento vivo. Cada decisión importante se registra aquí o en `docs/decisiones.md`.
>
> **Repositorio origen (colega):** https://github.com/TomCardeLo/boa-sarima-forecaster
> **Repositorio destino (propio):** https://github.com/DanMendezZz/Estadistica_Ambiental
> **Carpeta local de trabajo:** `D:\Dan\98. IA`
> **Autor:** Dan Méndez
> **Última actualización:** 2026-04-22

---

## 0. Resumen ejecutivo

Construir una plantilla Python reutilizable para proyectos ambientales que cubra el **ciclo estadístico completo**:

1. **Exploratorio (EDA):** carga, tipificación de variables, calidad de datos, visualización.
2. **Descriptivo:** resúmenes, distribuciones, relaciones bivariadas.
3. **Inferencial:** pruebas de hipótesis, intervalos de confianza, estacionariedad.
4. **Predictivo:** modelos de pronóstico comparados y seleccionados por evidencia.

Cada proyecto ambiental (páramos, humedales, hidrología, calidad del aire, etc.) parte de esta plantilla, recorre el ciclo, documenta decisiones y produce reportes automáticos.

---

## 1. Contexto y objetivo

### 1.1 Punto de partida
El repositorio `boa-sarima-forecaster` de Tomás Cárdenas está orientado a pronóstico mensual de demanda financiera (SKUs por país) con ARIMA + Optimización Bayesiana (Optuna TPE). La arquitectura es sólida y modular: ingestión, preprocesamiento, estandarización, métricas, optimizador, modelo. Reutilizable casi íntegramente porque es agnóstica al dominio.

### 1.2 Dominio ambiental — 16 líneas temáticas en 3 bloques
El repo sirve como insumo para 16 líneas ambientales organizadas así (ver `Fuentes.md` para fichas detalladas y los NotebookLM de cada una):

**Bloque A — Líneas de gestión (13)**
1. Áreas protegidas
2. Humedales
3. Páramos
4. Dirección directiva
5. Gestión de riesgo
6. Ordenamiento territorial
7. Oferta hídrica
8. POMCA (Planes de Ordenamiento y Manejo de Cuencas)
9. PUEEA (Programas de Uso Eficiente y Ahorro de Agua)
10. Recurso hídrico
11. Rondas hídricas
12. Sistemas de información ambiental
13. Predios para conservación

**Bloque B — Transversales temáticas (2)**
14. Cambio climático — marco que aporta covariables y escenarios a oferta hídrica, páramos, humedales, gestión de riesgo y recurso hídrico.
15. Calidad del aire — línea temática con series temporales directas (PM2.5, PM10, O3, NO2); es el caso más cercano al MVP heredado de Tomás, con SARIMAX + meteorología.

**Bloque C — Capa técnica transversal (1)**
16. Geoespacial — conjunto de métodos y herramientas (SIG, kriging, análisis espacial). Alimenta transversalmente a todas las líneas con componente espacial: áreas protegidas, humedales, páramos, rondas hídricas, POMCA, predios para conservación, ordenamiento territorial.

### 1.3 Objetivo del repositorio
Dado un dataset ambiental:

- Ejecutar EDA automatizado con tipificación de variables.
- Producir estadística descriptiva e inferencial con reportes.
- Aplicar un catálogo de modelos predictivos.
- Ajustar hiperparámetros con optimización bayesiana (heredado de Tomás).
- Comparar modelos con backtesting uniforme y métricas estandarizadas.
- Emitir un reporte automático con el mejor modelo según evidencia.
- Cuando aplique, incorporar métodos espaciales (kriging, GP) y covariables de cambio climático.

---

## 2. Análisis del repositorio origen

### 2.1 Qué se conserva, adapta o reemplaza

| Módulo original | Propósito (financiero) | Acción en Estadística Ambiental |
|---|---|---|
| `src/sarima_bayes/config.py` | Constantes globales | **CONSERVAR** estructura. Ajustar defaults (frecuencias ambientales). |
| `data_loader.py` | Ingesta Excel de ventas | **ADAPTAR**. CSV/NetCDF/Parquet/SHP desde IDEAM, SIATA, EPA, Copernicus, IGAC. |
| `preprocessor.py` | Meses faltantes, SKUs cero | **ADAPTAR**. Estación/variable en lugar de SKU/país. Imputación específica. |
| `standardization.py` | Moving-average clipping ±1σ | **CONSERVAR con revisión crítica**. Picos ambientales reales ≠ outliers. |
| `metrics.py` | sMAPE, RMSLE, combined | **EXTENDER**. MAE, RMSE, MASE, R², NSE, KGE, pinball, cobertura IC. |
| `optimizer.py` | TPE sobre (p,d,q) | **CONSERVAR** el motor. Extender a SARIMA estacional y otros modelos. |
| `model.py` | SARIMAX con statsmodels | **CONVERTIR** en factoría/registry de modelos. |
| `notebooks/demo.ipynb` | Demo datos sintéticos | **REESCRIBIR** con caso ambiental real. |
| `config.example.yaml` | Rutas y parámetros | **ADAPTAR** a estación/variable/frecuencia/modelos candidatos. |

### 2.2 Lo que NO se copia o se modifica radicalmente
- Terminología financiera: `SKU`, `country`, `forecast_group` → `variable`, `estación`, `zona`, `linea_tematica`.
- Lógica de "representantes" (consolidación SKUs hijos) → agregación espacial de estaciones / agregación por microcuenca.
- La función de costo `0.7·sMAPE + 0.3·RMSLE` asume valores positivos. En ambiente hay variables negativas (temperaturas, anomalías) y RMSLE no aplica.

---

## 3. Ciclo estadístico del repositorio

El repo implementa las cuatro etapas como **módulos independientes y encadenables**. Cada línea temática ejecuta el ciclo completo o solo las etapas relevantes.

### 3.1 Etapa 1 — Análisis Exploratorio de Datos (EDA)

**Objetivo:** entender los datos antes de modelar. Sin EDA sólido, los modelos predictivos son ruido calibrado.

**Submódulos:**

- **Carga y perfilado inicial:** lectura multiformato (CSV, Excel, NetCDF, Parquet, Shapefile), verificación de estructura, tamaño, encoding.
- **Tipificación de variables:** clasificar cada columna como:
  - Numéricas continuas (PM2.5, caudal, temperatura).
  - Numéricas discretas (conteos de especies, número de eventos).
  - Categóricas nominales (estación, tipo de suelo, línea temática).
  - Categóricas ordinales (clase de calidad: buena/media/mala).
  - Temporales (fecha, hora, período).
  - Espaciales (lat/lon, polígono, código DANE/IGAC).
  - Texto libre (observaciones, notas de campo).
- **Calidad de datos:**
  - Valores faltantes (patrón, proporción, MCAR/MAR/MNAR).
  - Duplicados (exactos y por llave lógica estación+fecha).
  - Rangos fuera de plausibilidad física (temperatura = 500°C, pH = 20).
  - Inconsistencias temporales (fechas futuras, saltos).
  - Inconsistencias espaciales (coordenadas fuera del área de estudio).
- **Visualización exploratoria:**
  - Histogramas, densidades, boxplots por variable.
  - Series temporales por estación.
  - Mapas cuando hay componente espacial.
  - Heatmaps de correlación.
  - Gráficos de faltantes (missingno).
- **Reporte automático:** generar HTML con ydata-profiling o sweetviz como línea base + plantilla propia adaptada al dominio ambiental.

**Módulo en el repo:** `src/estadistica_ambiental/eda/`

### 3.2 Etapa 2 — Estadística descriptiva

**Objetivo:** cuantificar la información de la etapa exploratoria con medidas formales.

**Submódulos:**

- **Univariada:**
  - Tendencia central: media, mediana, moda, media truncada.
  - Dispersión: varianza, desviación estándar, rango, IQR, MAD.
  - Forma: asimetría (skewness), curtosis.
  - Posición: cuantiles, percentiles.
  - Resúmenes agrupados por estación, año, mes, línea temática.
- **Bivariada:**
  - Correlaciones: Pearson (lineal), Spearman (monotónica), Kendall (ordinal).
  - Tablas de contingencia para categóricas.
  - Scatter + línea de regresión simple.
  - Análisis de estacionalidad (promedio mensual, ciclo anual).
- **Temporal descriptiva:**
  - Descomposición STL (tendencia + estacionalidad + residuo).
  - Autocorrelación (ACF) y autocorrelación parcial (PACF).
  - Rolling means y rolling stds.

**Módulo en el repo:** `src/estadistica_ambiental/descriptive/`

### 3.3 Etapa 3 — Estadística inferencial

**Objetivo:** probar hipótesis y generalizar de la muestra a la población, con cuantificación de incertidumbre.

**Submódulos:**

- **Pruebas de distribución:**
  - Normalidad: Shapiro-Wilk, Anderson-Darling, Kolmogorov-Smirnov, Q-Q plots.
  - Ajuste a distribuciones específicas (lognormal, gamma, Weibull, Gumbel) — útiles en hidrología y calidad del aire.
- **Comparación de grupos:**
  - t-test y Welch (dos grupos, paramétrico).
  - Mann-Whitney U (no paramétrico).
  - ANOVA de una vía / Kruskal-Wallis (varios grupos).
  - Pruebas post-hoc (Tukey, Dunn).
- **Independencia y asociación:**
  - Chi-cuadrado, test exacto de Fisher (categóricas).
  - Coeficientes de asociación con intervalos de confianza.
- **Estacionariedad (serie temporal):**
  - ADF (Augmented Dickey-Fuller).
  - KPSS.
  - Phillips-Perron.
  - Test de raíz unitaria estacional (HEGY, Canova-Hansen).
- **Cambio estructural / tendencia:**
  - Mann-Kendall (tendencia monotónica, muy usado en ambiente).
  - Pettitt (punto de cambio).
  - Sen's slope (magnitud de tendencia).
- **Intervalos de confianza:**
  - Paramétricos y bootstrap.
  - Para medias, medianas, proporciones, cuantiles extremos (útil en análisis de excedencias de norma ambiental).

**Módulo en el repo:** `src/estadistica_ambiental/inference/`

### 3.4 Etapa 4 — Estadística predictiva

**Objetivo:** pronosticar y comparar modelos con evidencia objetiva.

**Catálogo de modelos** (desarrollado en sección 4).

**Submódulos:**

- `predictive/` — implementaciones con interfaz común.
- `optimization/` — motor Optuna TPE heredado, generalizado.
- `evaluation/` — backtesting (walk-forward, expanding, sliding) y métricas.
- `evaluation/comparison.py` — ranking multi-criterio y selección del mejor.
- `reporting/` — HTML/PDF con series reales vs pronósticos, tabla de métricas, recomendación.

### 3.5 Etapa transversal — Análisis espacial

Aunque no es una etapa del ciclo clásico, se incorpora como **capa transversal** porque varias líneas (páramos, humedales, rondas hídricas, áreas protegidas) son intrínsecamente espaciales.

**Submódulos:**

- **EDA espacial:** mapas de cobertura, densidad de estaciones, huecos espaciales.
- **Descriptiva espacial:** estadísticas agregadas por polígono, cuenca o zona.
- **Inferencia espacial:** tests de autocorrelación (I de Moran, Geary) previos a modelos.
- **Predicción espacio-temporal:** Kriging (ordinario, universal), GP, regresión geográficamente ponderada (GWR), modelos jerárquicos bayesianos.

**Módulo en el repo:** `src/estadistica_ambiental/spatial/` (pendiente de crear en Fase 7 o posterior).

### 3.6 Flujo completo por línea temática

Cada línea sigue este flujo (no todos los pasos aplican siempre):

```
Datos crudos
   ↓ (io/loaders.py)
EDA automatizado → reporte HTML
   ↓ (eda/)
Tipificación y validación de variables → catálogo de variables
   ↓ (eda/variables.py)
Limpieza e imputación → dataset procesado
   ↓ (preprocessing/)
Estadística descriptiva → tablas y gráficos
   ↓ (descriptive/)
Estadística inferencial → pruebas y ADF
   ↓ (inference/)
[Análisis espacial si aplica]
   ↓ (spatial/)
Feature engineering (lags, exógenas, calendario, covariables climáticas)
   ↓ (features/)
Modelado predictivo con optimización bayesiana
   ↓ (predictive/ + optimization/)
Backtesting y comparación → ranking de modelos
   ↓ (evaluation/)
Reporte final → recomendación
   ↓ (reporting/)
Registro en docs/decisiones.md
```

---

## 4. Catálogo de modelos predictivos

No hay modelo ganador universal en pronóstico ambiental. El repo **compara varios** y selecciona con evidencia.

### 4.1 Familia 1 — Estadísticos clásicos (baseline obligatorio)
- **ARIMA (p,d,q)** — heredado. Línea base.
- **SARIMA (p,d,q)(P,D,Q,s)** — imprescindible por estacionalidades ambientales.
- **SARIMAX** (el que mencionó Tomás) — SARIMA + regresores exógenos. Crítico en ambiente: permite usar meteorología e índices climáticos como covariable. La literatura confirma que los factores meteorológicos mejoran sustancialmente la precisión de PM2.5.
- **ETS / Holt-Winters** — baseline rápido.
- **VAR / VECM** — múltiples variables simultáneas (PM2.5, PM10, NO2).

### 4.2 Familia 2 — Descomposición y tendencia
- **Prophet (Meta)** — buen desempeño en calidad del aire para 1 día y 1 semana.
- **NeuralProphet** — versión neuronal.
- **STL + ARIMA** — descomposición loess y ARIMA sobre residuo.

### 4.3 Familia 3 — Machine Learning
- **Random Forest / Extra Trees** — robusto con muchas exógenas.
- **XGBoost / LightGBM** — estándar tabular. Requiere feature engineering.
- **SVR** — competitivo en horizontes cortos.

### 4.4 Familia 4 — Deep Learning
- **LSTM / GRU** — la literatura muestra R² altos (0.99) superando a RF, DT, XGBoost en PM2.5/PM10.
- **CNN-LSTM / Transformer-LSTM** — mayor potencial para pronóstico escalable de calidad del aire.
- **N-BEATS / N-HiTS / TFT** — modernos, exigentes en datos.

### 4.5 Familia 5 — Bayesianos y espaciales
- **PyMC / SARIMA bayesiano** — cuantifica incertidumbre, jerarquía entre estaciones.
- **Kriging / Gaussian Processes** — interpolación espacio-temporal entre estaciones (clave para páramos, humedales, rondas hídricas).
- **INLA / Bayesian Hierarchical** — estructura jerárquica.

### 4.6 MVP recomendado (6 modelos)
1. **SARIMA** (heredado y extendido).
2. **SARIMAX** (con exógenas meteorológicas).
3. **Prophet**.
4. **XGBoost**.
5. **Random Forest**.
6. **LSTM simple**.

---

## 5. Arquitectura propuesta

```
Estadistica_Ambiental/
├── README.md
├── CLAUDE.md                       ← instrucciones para Claude Code (se sube)
├── CLAUDE.local.md                 ← notas personales (en .gitignore)
├── Plan.md                         ← ESTE archivo
├── Fuentes.md                      ← índice de fuentes y NotebookLM por línea
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── config.example.yaml
├── .env.example
│
├── src/
│   └── estadistica_ambiental/
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── io/                     ← ETAPA 0: ingesta
│       │   ├── loaders.py
│       │   └── validators.py
│       │
│       ├── eda/                    ← ETAPA 1: exploratorio
│       │   ├── profiling.py        ← ydata-profiling, sweetviz
│       │   ├── variables.py        ← tipificación de variables
│       │   ├── quality.py          ← faltantes, duplicados, plausibilidad
│       │   └── viz.py              ← histogramas, series, mapas
│       │
│       ├── preprocessing/
│       │   ├── imputation.py       ← interpolación, Kalman, MICE
│       │   ├── outliers.py         ← detección (no siempre clipping)
│       │   └── resampling.py
│       │
│       ├── descriptive/            ← ETAPA 2: descriptiva
│       │   ├── univariate.py
│       │   ├── bivariate.py
│       │   └── temporal.py         ← STL, ACF, PACF, rolling
│       │
│       ├── inference/              ← ETAPA 3: inferencial
│       │   ├── distributions.py    ← normalidad, ajustes
│       │   ├── hypothesis.py       ← t-test, ANOVA, chi2
│       │   ├── stationarity.py     ← ADF, KPSS, HEGY
│       │   ├── trend.py            ← Mann-Kendall, Sen, Pettitt
│       │   └── intervals.py        ← IC paramétricos y bootstrap
│       │
│       ├── spatial/                ← CAPA TRANSVERSAL: espacial
│       │   ├── io.py               ← lectura SHP, GPKG, GeoJSON, raster
│       │   ├── projections.py      ← MAGNA-SIRGAS, CTM12, WGS84
│       │   ├── autocorrelation.py  ← Moran, Geary, Getis-Ord
│       │   ├── interpolation.py    ← IDW, Kriging (ordinario, universal)
│       │   └── viz.py              ← mapas con folium, contextily
│       │
│       ├── features/
│       │   ├── calendar.py
│       │   ├── lags.py
│       │   ├── exogenous.py
│       │   └── climate.py          ← covariables de cambio climático (ONI, ENSO, escenarios)
│       │
│       ├── predictive/             ← ETAPA 4: predictiva
│       │   ├── base.py
│       │   ├── classical.py        ← ARIMA, SARIMA, SARIMAX, ETS
│       │   ├── prophet_model.py
│       │   ├── ml.py               ← RF, XGBoost, LightGBM
│       │   ├── deep.py             ← LSTM, GRU
│       │   ├── bayesian.py         ← PyMC
│       │   ├── spatial_models.py   ← Kriging, GP (enlaza con spatial/)
│       │   └── registry.py
│       │
│       ├── optimization/
│       │   └── bayes_opt.py        ← motor Optuna TPE heredado
│       │
│       ├── evaluation/
│       │   ├── metrics.py          ← MAE, RMSE, sMAPE, MASE, R², NSE, KGE
│       │   ├── backtesting.py
│       │   └── comparison.py
│       │
│       └── reporting/
│           ├── eda_report.py
│           ├── stats_report.py
│           └── forecast_report.py
│
├── data/
│   ├── README.md
│   ├── raw/                        ← en .gitignore
│   ├── processed/                  ← en .gitignore
│   └── output/                     ← en .gitignore
│
├── notebooks/
│   ├── 00_plantilla_ciclo_completo.ipynb      ← plantilla base
│   ├── 01_eda.ipynb
│   ├── 02_descriptiva.ipynb
│   ├── 03_inferencial.ipynb
│   ├── 04_predictiva.ipynb
│   ├── 05_espacial.ipynb                      ← cuando aplique
│   └── lineas_tematicas/                      ← una por línea
│       │
│       ├── bloque_a_gestion/
│       │   ├── areas_protegidas.ipynb
│       │   ├── humedales.ipynb
│       │   ├── paramos.ipynb
│       │   ├── direccion_directiva.ipynb
│       │   ├── gestion_riesgo.ipynb
│       │   ├── ordenamiento_territorial.ipynb
│       │   ├── oferta_hidrica.ipynb
│       │   ├── pomca.ipynb
│       │   ├── pueea.ipynb
│       │   ├── recurso_hidrico.ipynb
│       │   ├── rondas_hidricas.ipynb
│       │   ├── sistemas_informacion_ambiental.ipynb
│       │   └── predios_conservacion.ipynb
│       │
│       ├── bloque_b_transversales/
│       │   ├── cambio_climatico.ipynb
│       │   └── calidad_aire.ipynb
│       │
│       └── bloque_c_tecnicas/
│           └── geoespacial.ipynb
│
├── docs/
│   ├── metodologia.md
│   ├── modelos.md
│   ├── decisiones.md               ← ADRs
│   └── fuentes/                    ← resúmenes extraídos de cada NotebookLM
│       ├── areas_protegidas.md
│       ├── humedales.md
│       ├── paramos.md
│       ├── direccion_directiva.md
│       ├── gestion_riesgo.md
│       ├── ordenamiento_territorial.md
│       ├── oferta_hidrica.md
│       ├── pomca.md
│       ├── pueea.md
│       ├── recurso_hidrico.md
│       ├── rondas_hidricas.md
│       ├── sistemas_informacion_ambiental.md
│       ├── predios_conservacion.md
│       ├── cambio_climatico.md
│       ├── calidad_aire.md
│       └── geoespacial.md
│
└── tests/
    ├── test_loaders.py
    ├── test_eda.py
    ├── test_descriptive.py
    ├── test_inference.py
    ├── test_spatial.py
    ├── test_predictive.py
    └── test_metrics.py
```

---

## 6. Plan por fases

### Fase 0 — Preparación y trazabilidad (semana 1)
- [ ] Fork de `boa-sarima-forecaster`.
- [ ] Inicializar `Estadistica_Ambiental` con README, LICENSE (MIT), `.gitignore`, `pyproject.toml`, `requirements.txt`.
- [ ] Sección "Atribución" en README.
- [ ] Rama `import-from-boa` con commits atómicos.
- [ ] Crear `docs/decisiones.md` (ADRs) y `docs/fuentes/`.
- [ ] Confirmar `CLAUDE.md`, `CLAUDE.local.md`, `Plan.md`, `Fuentes.md` y `.gitignore` listos.
- [ ] Extraer los resúmenes de los 16 NotebookLM a `docs/fuentes/` siguiendo la plantilla de `Fuentes.md` (arrancar por los prioritarios: calidad del aire, oferta hídrica, recurso hídrico, cambio climático).

### Fase 1 — Ingesta y EDA (semanas 2-3)
- [ ] `io/loaders.py` multiformato (CSV, Excel, NetCDF, Parquet, SHP básico).
- [ ] `io/validators.py` con reglas de plausibilidad física por tipo de variable.
- [ ] `eda/variables.py` — tipificador automático de variables.
- [ ] `eda/quality.py` — faltantes, duplicados, rangos.
- [ ] `eda/profiling.py` — integración con ydata-profiling y template propio.
- [ ] `eda/viz.py` — funciones de gráficas estándar.
- [ ] Notebook `01_eda.ipynb` como plantilla reusable.

### Fase 2 — Descriptiva e inferencial (semanas 4-5)
- [ ] `descriptive/univariate.py`, `bivariate.py`, `temporal.py`.
- [ ] `inference/distributions.py`, `hypothesis.py`, `stationarity.py`, `trend.py`, `intervals.py`.
- [ ] Notebooks `02_descriptiva.ipynb` y `03_inferencial.ipynb`.
- [ ] **Hito clave:** Mann-Kendall + Sen's slope funcionando, es la prueba más usada en series ambientales largas.

### Fase 3 — Migración del motor predictivo (semanas 6-7)
- [ ] Copiar y renombrar `src/sarima_bayes/` → `src/estadistica_ambiental/predictive/` + `optimization/`.
- [ ] Portar `config.py`, `metrics.py`, `optimizer.py` casi tal cual.
- [ ] Reescribir `preprocessor.py` → `preprocessing/imputation.py` + `resampling.py`.
- [ ] Evaluar `standardization.py`: clipping opcional, desactivado por defecto.
- [ ] Adaptar `model.py` → `predictive/classical.py` con ARIMA, SARIMA, SARIMAX.
- [ ] Tests básicos (pytest).

### Fase 4 — MVP predictivo con calidad del aire (semanas 8-9)
- [ ] Pipeline end-to-end con dataset público (PM2.5 RMCAB Bogotá — encaja perfecto con el MVP porque es el caso más parecido al original de Tomás).
- [ ] Notebook `04_predictiva.ipynb` y notebook `bloque_b_transversales/calidad_aire.ipynb` como primer caso real.
- [ ] Validar optimización bayesiana sobre (p,d,q)(P,D,Q,s).
- [ ] Generar los 4 archivos de salida del pipeline original.

### Fase 5 — Catálogo de modelos (semanas 10-12)
- [ ] `predictive/base.py` clase abstracta.
- [ ] Implementar ARIMA, SARIMA, SARIMAX, Prophet, XGBoost, Random Forest.
- [ ] `predictive/registry.py` con decoradores.
- [ ] Extender `optimization/bayes_opt.py` a cualquier modelo.
- [ ] LSTM simple.

### Fase 6 — Evaluación y comparación (semanas 13-14)
- [ ] `evaluation/backtesting.py`: walk-forward, expanding, sliding.
- [ ] `evaluation/metrics.py` completas (NSE, KGE, pinball, cobertura IC).
- [ ] `evaluation/comparison.py` ranking multi-criterio.
- [ ] `reporting/forecast_report.py` HTML/PDF.

### Fase 7 — Capa espacial (semanas 15-16)
- [ ] `spatial/io.py`, `spatial/projections.py`, `spatial/autocorrelation.py`, `spatial/interpolation.py`, `spatial/viz.py`.
- [ ] `predictive/spatial_models.py` con Kriging y GP.
- [ ] `features/climate.py` para covariables de cambio climático (ONI, índices ENSO, escenarios).
- [ ] Notebook `05_espacial.ipynb`.

### Fase 8 — Casos por bloque (semanas 17-20)
- [ ] **Bloque A prioritario:** oferta hídrica, recurso hídrico, páramos, gestión de riesgo.
- [ ] **Bloque B:** cambio climático (como productor de covariables) y calidad del aire (ya hecho en Fase 4, pulir).
- [ ] **Bloque C:** geoespacial (ya cubierto en Fase 7, usar como referencia).
- [ ] Resto del Bloque A en iteraciones posteriores.
- [ ] Cada notebook aprovecha su ficha en `docs/fuentes/<linea>.md`.

### Fase 9 — Documentación y cierre (semana 21)
- [ ] `docs/metodologia.md`, `docs/modelos.md`.
- [ ] README con quick start, instalación, tabla de modelos.
- [ ] Tag `v0.1.0` (MVP Fase 4), `v0.5.0` (Fase 6), `v0.8.0` (Fase 7 espacial), `v1.0.0` (Fase 9).

### Fase 10 — Backlog futuro
- Bayesianos jerárquicos con PyMC multi-estación.
- Transformers temporales (TFT, N-BEATS, N-HiTS).
- APIs públicas (Copernicus, OpenAQ, IDEAM, SIATA) para ingesta automática.
- Dashboard Streamlit.
- CI/CD GitHub Actions.

---

## 7. Trazabilidad entre ambos repositorios

### 7.1 A nivel de Git
- **Fork formal** de `boa-sarima-forecaster`.
- **Rama `import-from-boa`**: commits `import:`.
- **Rama `adapt-to-environmental`**: commits `adapt:`.
- **Ramas `feature/*`**: funcionalidades propias.

### 7.2 A nivel de código
- Docstring en cada módulo heredado: `Adaptado de boa-sarima-forecaster/<módulo>.py por Dan Méndez el <fecha>.`
- Comentarios `# heredado sin cambios` y `# adaptado: <razón>`.

### 7.3 A nivel de documentación
- Sección de atribución en README.
- `docs/decisiones.md` (ADRs).
- Tabla de equivalencias en `docs/metodologia.md`.

### 7.4 Tabla de equivalencias

| boa-sarima-forecaster | Estadistica_Ambiental | Cambio |
|---|---|---|
| `src/sarima_bayes/config.py` | `src/estadistica_ambiental/config.py` | Copiar, ajustar defaults |
| `data_loader.py` | `io/loaders.py` + `io/validators.py` | Reescribir multiformato |
| `preprocessor.py` | `preprocessing/imputation.py` + `resampling.py` | Dividir y reemplazar SKU→estación |
| `standardization.py` | `preprocessing/outliers.py` | Conservar, hacer opcional |
| `metrics.py` | `evaluation/metrics.py` | Extender (NSE, KGE) |
| `optimizer.py` | `optimization/bayes_opt.py` | Generalizar |
| `model.py` | `predictive/classical.py` (+ otros) | Factoría de modelos |
| `notebooks/demo.ipynb` | `notebooks/lineas_tematicas/**/*.ipynb` | Reescribir con datos ambientales |

---

## 8. Guía operativa Git

```bash
# 1. Clonar ambos repositorios
git clone https://github.com/TomCardeLo/boa-sarima-forecaster.git
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git

# 2. En Estadistica_Ambiental, rama de importación
cd Estadistica_Ambiental
git checkout -b import-from-boa

# 3. Copiar archivos heredados (en Fase 3)
mkdir -p src/estadistica_ambiental/predictive
mkdir -p src/estadistica_ambiental/optimization
cp ../boa-sarima-forecaster/src/sarima_bayes/model.py src/estadistica_ambiental/predictive/classical.py
cp ../boa-sarima-forecaster/src/sarima_bayes/optimizer.py src/estadistica_ambiental/optimization/bayes_opt.py
cp ../boa-sarima-forecaster/src/sarima_bayes/metrics.py src/estadistica_ambiental/evaluation/metrics.py

# 4. Commit inicial
git add .
git commit -m "import: base modules from boa-sarima-forecaster (attribution: TomCardeLo)"

# 5. Rama de adaptación
git checkout -b adapt-to-environmental

# 6. Merge al MVP predictivo
git checkout main
git merge --no-ff adapt-to-environmental
git tag -a v0.1.0 -m "MVP: ciclo estadistico completo con dataset ambiental"
git push origin main --tags
```

---

## 9. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Clipping de outliers oculta episodios ambientales reales (tormentas, inversiones térmicas). | Alto | Clipping opcional, desactivado por defecto. Documentar. |
| RMSLE no aplica a variables negativas (anomalías, T bajo cero). | Medio | Métrica combinada parametrizable. Default MAE+sMAPE o NSE. |
| Frecuencias horarias → series mucho más largas que mensuales. | Medio | Submuestreo, paralelización por estación, caching. |
| Huecos largos por fallos de sensores. | Alto | Módulo de imputación con varias estrategias. |
| Dependencias pesadas (PyMC, PyTorch, geopandas, pykrige). | Bajo-medio | Instalación modular: `pip install estadistica-ambiental[deep]`, `[bayes]`, `[spatial]`. |
| EDA insuficiente lleva a modelos erróneos. | Alto | EDA es etapa obligatoria antes de predictivo; reporte automático exigido. |
| Variables ambientales no estacionarias → ARIMA falla silenciosamente. | Medio | Pruebas ADF/KPSS obligatorias antes de ARIMA; advertencia explícita. |
| Proyecciones geográficas inconsistentes (lat/lon mezcladas con CTM12). | Medio | `spatial/projections.py` normaliza todo a un SRE estándar del proyecto. |
| Las 16 líneas temáticas tienen datos y objetivos muy distintos. | Medio | Cada notebook se adapta; el `core` se mantiene genérico; transversales (clima, aire, espacial) son librerías horizontales. |

---

## 10. Próximos pasos inmediatos

1. Conversar con Tomás sobre la atribución y alinear convenciones.
2. Fork oficial de `boa-sarima-forecaster`.
3. Estructura de carpetas vacía en `Estadistica_Ambiental` + README con atribución.
4. Poblar `docs/fuentes/` con los resúmenes prioritarios de los NotebookLM (ver `Fuentes.md` sección 6): calidad del aire, oferta hídrica, recurso hídrico, cambio climático.
5. Ejecutar Fase 0 y Fase 1 (EDA).
6. **Primer caso real sugerido (Fase 4):** calidad del aire con PM2.5 de RMCAB Bogotá y meteorología como exógena — replica el MVP del original pero con variable ambiental.

---

## 11. Seguimiento de avance

Usar este registro al final de cada sesión de trabajo:

### 2026-04-22
- Primera versión del plan con análisis del repo origen, catálogo de modelos y arquitectura.
- Creados `CLAUDE.md`, `CLAUDE.local.md` y `.gitignore`.

### 2026-04-22 (actualización)
- Integrado el ciclo estadístico completo: EDA + descriptiva + inferencial + predictiva.
- Agregadas 13 líneas temáticas ambientales.
- Creado archivo `Fuentes.md` como índice de NotebookLM y plantilla de fichas.
- Reorganizada la arquitectura en módulos `eda/`, `descriptive/`, `inference/`, `predictive/`.

### 2026-04-22 (actualización 2)
- Agregadas 3 líneas más: cambio climático, calidad del aire, geoespacial.
- Estructura ahora organizada en 3 bloques: A (gestión, 13), B (transversales temáticas, 2), C (capa técnica, 1).
- Añadido módulo `spatial/` en la arquitectura y capa transversal de análisis espacial.
- Añadido módulo `features/climate.py` para covariables de cambio climático.
- Fase 7 dedicada a la capa espacial; Fase 4 MVP ahora apunta a calidad del aire (caso directo).
- Notebooks reorganizados en subcarpetas por bloque.

<!-- Añadir nuevas entradas arriba siguiendo el formato: ### YYYY-MM-DD -->
