# Estadística Ambiental Colombia

> **Base de conocimiento Python para el ciclo estadístico completo aplicado a datos ambientales colombianos**  
> EDA → Descriptiva → Inferencial → Predictiva → Cumplimiento normativo

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-427%20passed-brightgreen)]()
[![Cobertura](https://img.shields.io/badge/cobertura-80%25-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Normas CO](https://img.shields.io/badge/Normas-Res.%202254%2F2017%20%7C%202115%2F2007%20%7C%20631%2F2015-green)]()

---

## ¿Para qué sirve este repositorio?

Este proyecto nació dentro de las direcciones técnicas de una entidad ambiental colombiana donde **el analista de datos es el único perfil de ciencia de datos** enfrentado a 16 líneas temáticas simultáneas: calidad del aire, oferta hídrica, páramos, humedales, gestión del riesgo, POMCA, ordenamiento territorial, y más.

El repositorio resuelve un problema concreto: **no hay que partir de cero en cada línea temática**. Provee:

- Un **ciclo estadístico estructurado** y reproducible adaptado al dominio ambiental colombiano
- **Normas colombianas centralizadas** (Res. 2254/2017, 2115/2007, 631/2015, índices IDEAM) para verificar cumplimiento directamente desde el código
- **Conectores a fuentes oficiales** (IDEAM DHIME, RMCAB Bogotá, SIATA Medellín, OpenAQ, datos.gov.co)
- **16 fichas de conocimiento de dominio** generadas desde bases de conocimiento especializadas, listas para contextualizar cualquier análisis
- **16 scripts ejecutables** que recorren el ciclo completo por línea temática y generan reportes HTML listos para entregar
- **Catálogo de 10 modelos** comparables entre sí: desde SARIMA clásico hasta XGBoost y modelos bayesianos espaciales

Está pensado para investigadores y analistas que trabajan en o para entidades como el **Ministerio de Ambiente y Desarrollo Sostenible**, **CAR Cundinamarca**, **IDEAM**, **CORNARE**, **CORANTIOQUIA** y otras Corporaciones Autónomas Regionales.

---

## Contexto institucional

La gestión ambiental en Colombia opera bajo un marco normativo robusto y datos dispersos en múltiples sistemas (SIRH, SIAC, RMCAB, SIATA, SMByC). Este repositorio integra ese contexto directamente en el código:

| Reto institucional | Solución en el repo |
|---|---|
| Datos en múltiples formatos (CSV, NetCDF, SHP, XLSX) | `io/loaders.py` — carga unificada |
| Normas distintas por línea temática | `config.py` — todas las normas centralizadas |
| Validación física de variables ambientales | `io/validators.py` — 74 variables con rangos por ecosistema |
| Reportes de excedencias para entidades reguladoras | `reporting/compliance_report.py` — HTML con semáforo normativo |
| Influencia del ENSO (El Niño/La Niña) en variables hídricas | `features/climate.py` — lag diferenciado por línea temática |
| Acceso a datos oficiales dispersos | `io/connectors.py` — RMCAB, SIATA, DHIME, OpenAQ, datos.gov.co |
| Entender el contexto antes de analizar | `docs/intake_lider.md` — cuestionario de 18 preguntas para líderes de área |

---

## Las 16 líneas temáticas

Organizadas en 3 bloques según su rol en la gestión ambiental:

### Bloque A — Gestión ambiental (13 líneas)

| # | Línea | Variable principal | Norma clave |
|---|---|---|---|
| 01 | Áreas Protegidas | Cobertura boscosa (ha) | CONPES 4050/2021 |
| 02 | Humedales | Nivel del agua / hidroperiodo (m) | Res. 157/2004 |
| 03 | Páramos | Temperatura / precipitación | Ley 1930/2018 |
| 04 | Dirección Directiva | Indicadores IEDI / ICAU | Res. 667/2016 |
| 05 | Gestión de Riesgo | Precipitación / pendiente | Ley 1523/2012 |
| 06 | Ordenamiento Territorial | Cobertura / uso del suelo (ha) | Ley 388/1997 |
| 07 | Oferta Hídrica | Caudal / nivel piezométrico (m³/s) | Dec. 1076/2015 |
| 08 | POMCA | Caudal / calidad del agua | Dec. 1640/2012 |
| 09 | PUEEA | Consumo de agua / IANC (%) | Ley 373/1997 |
| 10 | Recurso Hídrico | OD / DBO₅ / pH | Res. 2115/2007 |
| 11 | Rondas Hídricas | Caudal / ancho de faja (m) | Res. 957/2018 |
| 12 | Sistemas de Información | Deforestación (ha) / GEI | Ley 99/1993 |
| 13 | Predios para Conservación | NDVI / área PSA (ha) | Dec. 1007/2018 |

### Bloque B — Transversales temáticas (2 líneas)

| # | Línea | Rol | Alimenta a |
|---|---|---|---|
| 14 | Cambio Climático | Marco de covariables y escenarios CC | Oferta hídrica, páramos, gestión de riesgo |
| 15 | Calidad del Aire | Serie temporal con SARIMAX + meteorología | Gestión de riesgo, sistemas de información |

### Bloque C — Capa técnica transversal (1 línea)

| # | Capa | Rol | Alimenta a |
|---|---|---|---|
| 16 | Geoespacial | SIG, Kriging, GWR, Moran, CTM12 | Todas las líneas con componente espacial |

Cada línea tiene su ficha técnica completa en [`docs/fuentes/`](docs/fuentes/) con: variables clave, rangos físicos, normativa colombiana, métodos estadísticos sugeridos, actores institucionales, riesgos en los datos y preguntas de investigación abiertas.

---

## Ciclo estadístico

```
Datos brutos (CSV / NetCDF / SHP / XLSX / API)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  ETAPA 1 — EDA (obligatoria)                        │
│  Tipificación · Calidad · Perfilado · Visualización │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  ETAPA 2 — Descriptiva                              │
│  Univariada · Bivariada · Temporal (STL / ACF)      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  ETAPA 3 — Inferencial                              │
│  Normalidad · Estacionariedad (ADF+KPSS) ·          │
│  Mann-Kendall · Sen's slope · Excedencias normativas│
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  ETAPA 4 — Predictiva                               │
│  SARIMA / SARIMAX · Prophet · XGBoost · RF · LSTM   │
│  Walk-forward · Optuna TPE · Ranking multi-criterio │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  CAPA TRANSVERSAL — Espacial                        │
│  Kriging · GWR · I de Moran · Proyecciones (CTM12)  │
└─────────────────────────────────────────────────────┘
                     │
                     ▼
     Reportes HTML (pronóstico · cumplimiento normativo · estadística)
```

---

## Ejecutar el ciclo completo por línea temática

Los 16 scripts en `scripts/` recorren el ciclo estadístico completo con datos reales o sintéticos y generan 6 artefactos listos para entregar:

```bash
python scripts/fase8_calidad_aire.py
```

**Salidas generadas:**

| Artefacto | Descripción |
|---|---|
| `eda_red_car.html` | Perfilado interactivo de la serie (ydata-profiling) |
| `descriptiva.csv` | Tabla con media, mediana, asimetría, curtosis, cuantiles |
| `inferencial.json` | ADF + KPSS + Mann-Kendall + excedencias normativas |
| `backtesting.csv` | Resultados walk-forward por modelo (MAE, RMSE, R²) |
| `cumplimiento.html` | Semáforo normativo Res. 2254/2017 + OMS 2021 |
| `forecast.html` | Serie real vs. pronóstico con Chart.js interactivo |

Scripts disponibles:

```
scripts/
├── fase8_calidad_aire.py          fase8_humedales.py
├── fase8_calidad_aire_multimodel.py  fase8_paramos.py
├── fase8_oferta_hidrica.py        fase8_pomca.py
├── fase8_recurso_hidrico.py       fase8_pueea.py
├── fase8_cambio_climatico.py      fase8_rondas_hidricas.py
├── fase8_areas_protegidas.py      fase8_ordenamiento_territorial.py
├── fase8_gestion_riesgo.py        fase8_sistemas_informacion.py
├── fase8_predios_conservacion.py  fase8_direccion_directiva.py
└── build_notebooks.py             # Regenera los 16 notebooks temáticos
```

---

## Normas colombianas integradas

Todas las normas están centralizadas en `config.py` y disponibles en el código sin hardcodear umbrales:

```python
from estadistica_ambiental.config import (
    NORMA_CO,           # Res. 2254/2017 — calidad del aire
    NORMA_OMS,          # Guías OMS 2021
    NORMA_AGUA_POTABLE, # Res. 2115/2007
    NORMA_VERTIMIENTOS, # Res. 631/2015
    IUA_THRESHOLDS,     # IDEAM — Índice de Uso del Agua
    IRH_THRESHOLDS,     # IDEAM — Índice de Retención Hídrica
    ICA_CATEGORIES,     # IDEAM — Índice de Calidad del Agua
    ENSO_THRESHOLDS,    # NOAA — Clasificación ONI (El Niño/La Niña)
    ENSO_LAG_MESES,     # Lag hidrológico por línea temática (Colombia)
)
```

### Verificar cumplimiento normativo en una línea

```python
from estadistica_ambiental.inference.intervals import exceedance_report

# Compara la serie contra TODAS las normas colombianas para PM2.5
rep = exceedance_report(df["pm25"], variable="pm25")
print(rep)
# ──────────────────────────────────────────────────────────
#                   norma   umbral    tipo  n_exceedances  pct_exceed  cumple
# Res. 2254/2017 — 24h      37.0   máximo             42       11.5%  False
# Res. 2254/2017 — anual    25.0   máximo            168       46.0%  False
# OMS 2021 — 24h            15.0   máximo            289       79.2%  False
# OMS 2021 — anual           5.0   máximo            362       99.2%  False
```

### Generar reporte HTML de cumplimiento

```python
from estadistica_ambiental.reporting.compliance_report import compliance_report

compliance_report(
    df,
    variables=["pm25", "pm10", "o3"],
    date_col="fecha",
    linea_tematica="calidad_aire",
    output="reports/cumplimiento_aire_2024.html",
)
# Genera HTML con semáforo por variable, tabla de excedencias,
# series temporales con línea de norma superpuesta y contexto de dominio.
```

### Reporte estadístico descriptivo + inferencial

```python
from estadistica_ambiental.reporting.stats_report import stats_report

stats_report(
    df,
    variable="pm25",
    linea_tematica="calidad_aire",
    output="reports/estadistica_pm25.html",
)
# Genera HTML con descriptiva completa, ADF+KPSS, Mann-Kendall y excedencias.
```

---

## Conectores a fuentes de datos colombianas

```python
from estadistica_ambiental.io.connectors import (
    load_openaq,        # API OpenAQ v3 — calidad del aire (RMCAB, SIATA, etc.)
    load_rmcab,         # Red de Monitoreo de Bogotá (requiere token SDA gratuito)
    load_siata_aire,    # SIATA Medellín / Antioquia
    load_ideam_dhime,   # IDEAM DHIME — datos hidrometeorológicos (descarga manual)
    load_smbyc_alertas, # SMByC — alertas de deforestación (Shapefile/GeoJSON)
    list_datasets_co,   # Búsqueda en datos.gov.co
)

# Ejemplo: PM2.5 en estación Kennedy, RMCAB Bogotá
df_aire = load_openaq(location_id=225433, parameter="pm25", date_from="2024-01-01")

# Ejemplo: buscar datasets hídricos en datos.gov.co
datasets = list_datasets_co(query="calidad agua rio bogota")
```

---

## Datos incluidos

El repositorio incluye un conjunto de datos reales y datos sintéticos para poder ejecutar todos los scripts sin necesidad de credenciales externas:

| Dataset | Tipo | Tamaño | Descripción |
|---|---|---|---|
| `calidad_aire_CAR_2016_2026.parquet` | Real | 8.7 MB | PM2.5 horario (10 años), red de monitoreo CAR Cundinamarca — estación focal Mochuelo |
| `calidad_aire_CAR_2016_2026.csv` | Real | 85 MB | Mismo dataset en CSV descomprimido |
| `oferta_hidrica_sintetica.csv` | Sintético | 185 KB | Caudales diarios para demostración |
| `recurso_hidrico_sintetico.csv` | Sintético | 4.2 KB | Parámetros de calidad de agua |
| `areas_protegidas_sintetica.csv` | Sintético | 1.4 KB | Cobertura boscosa temporal |
| `pomca_sintetica.csv` | Sintético | 543 KB | Caudales en cuenca |

---

## Instalación

**Requisitos:** Python 3.10+

```bash
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git
cd Estadistica_Ambiental
pip install -e ".[dev]"
```

### Extras opcionales (dependencias pesadas)

```bash
pip install -e ".[spatial]"  # geopandas, rasterio, pykrige, pysal, folium
pip install -e ".[deep]"     # PyTorch — LSTM, GRU
pip install -e ".[bayes]"    # PyMC — modelos bayesianos jerárquicos
pip install -e ".[netcdf]"   # netCDF4, h5netcdf — datos IDEAM / Copernicus
```

### Verificar instalación

```bash
python -m pytest tests/ -q
# 427 passed, 1 skipped, 80% coverage
```

---

## Uso rápido

### 1. Cargar y validar datos ambientales

```python
from estadistica_ambiental.io.loaders import load_csv
from estadistica_ambiental.io.validators import validate

df = load_csv("data/raw/pm25_rmcab.csv", date_col="fecha")

# Validación con rangos físicos específicos para calidad del aire
rep = validate(df, date_col="fecha", linea_tematica="calidad_aire")
print(rep.summary())
```

### 2. EDA automático

```python
from estadistica_ambiental.eda.profiling import run_eda

run_eda(df, output="reports/eda_pm25.html", title="PM2.5 Kennedy 2024")
# → HTML interactivo con distribuciones, correlaciones, faltantes, estacionalidad
```

### 3. Ciclo inferencial

```python
from estadistica_ambiental.inference.stationarity import stationarity_report
from estadistica_ambiental.inference.trend import mann_kendall, sens_slope

ts = df.set_index("fecha")["pm25"]

# ADF + KPSS (obligatorio antes de ARIMA — ADR-004)
stationarity_report(ts)

# Tendencia Mann-Kendall
mk = mann_kendall(ts)
print(f"Tendencia: {mk['trend']} | p={mk['pval']:.4f} | slope={sens_slope(ts):.4f} µg/m³/día")
```

### 4. Modelos predictivos con backtesting

```python
from estadistica_ambiental.predictive.registry import get_model
from estadistica_ambiental.evaluation.backtesting import walk_forward
from estadistica_ambiental.evaluation.comparison import rank_models

models = {
    "SARIMA":       get_model("sarima", order=(1,1,1), seasonal_order=(1,1,1,24)),
    "SARIMAX":      get_model("sarimax", order=(1,1,1), seasonal_order=(1,1,1,24)),
    "Prophet":      get_model("prophet"),
    "XGBoost":      get_model("xgboost", lags=[1,2,3,6,12,24]),
    "RandomForest": get_model("random_forest", lags=[1,2,3,6,12,24]),
}

results = {name: walk_forward(model, ts, horizon=24, n_splits=5)
           for name, model in models.items()}

rank_models(results)[["rmse", "mae", "r2", "score", "rank"]]
```

### 5. Covariable ENSO con lag específico

```python
from estadistica_ambiental.features.climate import load_oni, enso_lagged

# Descarga ONI desde NOAA y aplica lag de 4 meses para oferta hídrica
oni = load_oni()
df = enso_lagged(df, oni, date_col="fecha", linea_tematica="oferta_hidrica")
# → agrega columnas: oni_lag4, fase_lag4, intensidad_lag4, enso_lag4_niño, enso_lag4_niña
```

### 6. Detección de anomalías

```python
from estadistica_ambiental.evaluation.anomaly import detect_anomalies, anomaly_summary

flags = detect_anomalies(ts)
print(anomaly_summary(flags))
# → tabla con fechas, valores y severidad de cada anomalía detectada
```

---

## Estructura del proyecto

```
estadistica_ambiental/
│
├── src/estadistica_ambiental/
│   ├── config.py              # Normas colombianas, rutas, parámetros globales
│   ├── io/
│   │   ├── loaders.py         # CSV, Excel, Parquet, NetCDF, Shapefile
│   │   ├── validators.py      # 74 variables con rangos físicos por ecosistema
│   │   └── connectors.py      # RMCAB, SIATA, DHIME, OpenAQ, SMByC, datos.gov.co
│   ├── eda/
│   │   ├── profiling.py       # Reporte HTML automático (ydata-profiling)
│   │   ├── variables.py       # Tipificador automático (7 tipos)
│   │   ├── quality.py         # Faltantes, gaps, sensores congelados
│   │   └── viz.py             # 8 funciones gráficas estándar
│   ├── preprocessing/
│   │   ├── imputation.py      # 8 métodos (linear, Kalman, MICE...)
│   │   ├── outliers.py        # Flags IQR/z-score (sin clipping automático)
│   │   ├── resampling.py      # Alineación de frecuencias
│   │   └── air_quality.py     # flag_spatial_episodes, categorize_ica, correct_seasonal_bias
│   ├── descriptive/
│   │   ├── univariate.py      # summarize() con medidas de forma
│   │   ├── bivariate.py       # Pearson, Spearman, Kendall, chi²
│   │   └── temporal.py        # STL, ACF, PACF, rolling stats
│   ├── inference/
│   │   ├── distributions.py   # Shapiro-Wilk, KS, Anderson; ajuste a 6 distribuciones
│   │   ├── hypothesis.py      # t-test, Mann-Whitney, ANOVA, Kruskal-Wallis
│   │   ├── stationarity.py    # ADF + KPSS (obligatorio pre-ARIMA)
│   │   ├── trend.py           # Mann-Kendall, Sen's slope, Pettitt
│   │   └── intervals.py       # IC bootstrap + exceedance_report() normativo
│   ├── spatial/
│   │   ├── io.py              # SHP, GPKG, GeoTIFF, NetCDF
│   │   ├── projections.py     # MAGNA-SIRGAS, CTM12 (EPSG:9377), WGS84
│   │   ├── autocorrelation.py # I de Moran global y local (LISA)
│   │   ├── interpolation.py   # IDW, Kriging ordinario (pykrige)
│   │   └── viz.py             # Mapas folium, coropletas
│   ├── features/
│   │   ├── lags.py            # Lags, rolling stats, diferencias
│   │   ├── calendar.py        # Variables cíclicas seno/coseno
│   │   ├── exogenous.py       # Alineación de covariables meteorológicas
│   │   └── climate.py         # ONI (ENSO) + enso_lagged() con lag por línea
│   ├── predictive/
│   │   ├── base.py            # BaseModel ABC — interfaz común
│   │   ├── classical.py       # ARIMA, SARIMA, SARIMAX, ETS
│   │   ├── prophet_model.py   # Meta Prophet
│   │   ├── ml.py              # XGBoost, RandomForest, LightGBM
│   │   ├── deep.py            # LSTM, GRU (requiere [deep])
│   │   ├── bayesian.py        # PyMC (requiere [bayes])
│   │   ├── spatial_models.py  # Kriging, Gaussian Processes
│   │   └── registry.py        # get_model(), list_models(), register()
│   ├── optimization/
│   │   └── bayes_opt.py       # Optuna TPE — búsqueda bayesiana de hiperparámetros
│   ├── evaluation/
│   │   ├── metrics.py         # MAE, RMSE, R², sMAPE + NSE, KGE, PBIAS
│   │   ├── backtesting.py     # Walk-forward (expanding / sliding window)
│   │   ├── comparison.py      # Ranking multi-criterio, select_best()
│   │   └── anomaly.py         # detect_anomalies(), anomaly_summary()
│   └── reporting/
│       ├── forecast_report.py  # HTML con pronóstico vs. serie real
│       ├── compliance_report.py # HTML con semáforo de cumplimiento normativo
│       └── stats_report.py    # HTML con descriptiva + ADF/KPSS + Mann-Kendall
│
├── docs/
│   ├── fuentes/               # 16 fichas técnicas de dominio (una por línea) ✅
│   ├── metodologia.md         # Descripción del ciclo estadístico
│   ├── modelos.md             # Catálogo de modelos con cuándo usar cada uno
│   ├── decisiones.md          # ADR-001 a ADR-010 — decisiones de arquitectura
│   ├── intake_lider.md        # Cuestionario de onboarding para líderes de área (18 preguntas)
│   └── intake_output_template.md  # Template de respuesta estructurada
│
├── notebooks/
│   ├── 00_plantilla_ciclo_completo.ipynb  # Plantilla maestra (10 secciones)
│   ├── 01_eda.ipynb / 02_descriptiva.ipynb / ...
│   └── lineas_tematicas/                  # 16 notebooks por línea temática
│       ├── bloque_a_gestion/              # 13 notebooks
│       ├── bloque_b_transversales/        # 2 notebooks
│       └── bloque_c_tecnicas/             # 1 notebook (geoespacial)
│
├── tests/                     # 427 tests (pytest, cobertura 80%)
│   └── test_regression_pr6.py # 21 tests de regresión — 10 bugs corregidos
├── scripts/
│   ├── build_notebooks.py     # Genera los 16 notebooks temáticos
│   └── fase8_*.py             # 16 scripts de ciclo completo por línea
└── pyproject.toml             # Dependencias, ruff, pytest, coverage
```

---

## Catálogo de modelos

| Familia | Modelos | Cuándo usar |
|---|---|---|
| **Clásicos** | ARIMA, SARIMA, SARIMAX, ETS | Serie estacionaria o diferenciable; estacionalidad conocida |
| **Descomposición** | Prophet, STL+ARIMA | Estacionalidades múltiples; datos con días festivos o eventos atípicos |
| **ML** | XGBoost, RandomForest, LightGBM | Covariables exógenas; relaciones no lineales; datos tabulares |
| **Deep Learning** | LSTM, GRU | Series largas (> 5 años horarios); patrones temporales complejos |
| **Bayesianos/Espaciales** | Kriging, GP, PyMC | Interpolación espacial; incertidumbre cuantificada; modelos jerárquicos |

**Métricas por dominio** (configuradas automáticamente):

| Dominio | Métricas primarias |
|---|---|
| Calidad del aire | MAE, RMSE, R² |
| Hidrología (caudal) | NSE (Nash-Sutcliffe), KGE (Kling-Gupta), PBIAS |
| General | MAE, RMSE, R² |

---

## Base de conocimiento de dominio

Las fichas en [`docs/fuentes/`](docs/fuentes/) contienen, para cada línea temática:

- **Variables ambientales clave** con unidades, rangos físicos y frecuencia de medición
- **Normativa colombiana aplicable** (número de Decreto/Resolución)
- **Fuentes de datos oficiales** (IDEAM, SGC, IGAC, CARs, institutos SINA)
- **Preguntas analíticas típicas** que se responden con los datos
- **Métodos estadísticos sugeridos** (descriptiva, predictiva, espacial)
- **Riesgos y sesgos conocidos** en los datos de esa línea
- **Preguntas abiertas** para investigación futura

Estas fichas se generaron mediante consultas paralelas a bases de conocimiento especializadas en legislación, hidrología, calidad ambiental y gestión territorial colombiana.

**Uso en una sesión de análisis:**

```python
from estadistica_ambiental.config import DOCS_FUENTES

# Leer la ficha de dominio de la línea activa
ficha = (DOCS_FUENTES / "oferta_hidrica.md").read_text(encoding="utf-8")
print(ficha[:3000])
```

---

## Decisiones de arquitectura (ADRs)

El archivo [`docs/decisiones.md`](docs/decisiones.md) registra las 10 decisiones técnicas clave:

| ADR | Decisión |
|---|---|
| ADR-001 | Herencia de `boa-sarima-forecaster` (Tomás Cárdenas) — atribución explícita |
| ADR-002 | Outliers **NO** automáticos — picos ambientales son señal real |
| ADR-003 | Métricas por dominio — NSE/KGE para hidrología; RMSLE desactivado en variables negativas |
| ADR-004 | ADF + KPSS **obligatorios** antes de cualquier ARIMA |
| ADR-005 | Normas colombianas centralizadas en `config.py` |
| ADR-006 | Validación con rangos físicos específicos por línea temática |
| ADR-007 | Lags ENSO diferenciados por línea temática (literatura hidrológica colombiana) |
| ADR-008 | `compliance_report()` como artefacto separado del reporte predictivo |
| ADR-009 | Conectores a fuentes colombianas como módulo `io/connectors.py` |
| ADR-010 | 10 bugs corregidos en PR #6 con tests de regresión dedicados |

---

## Para investigadores y analistas de campo

### Flujo de onboarding con un líder de área

Antes de abrir un notebook, el cuestionario `docs/intake_lider.md` recopila en 18 preguntas el contexto institucional, las variables disponibles, las normas aplicables y las preguntas analíticas prioritarias. Esto evita iterar sobre modelos sin entender el dominio.

```
Líder de área
  → Completa intake_lider.md (18 preguntas)
      ↓
Dan + Claude
  → Activan línea temática + cargan datos reales
  → Ejecutan notebook correspondiente (ej. calidad_aire.ipynb)
      ↓
  Iteran: mejoran datos → ajustan modelo → generan reporte
      ↓
  Entregan HTML con pronóstico + recomendación normativa
```

### Pasos rápidos para un analista nuevo

1. **Clona el repo** e instala con `pip install -e ".[dev]"`
2. **Lee la ficha de tu línea** en `docs/fuentes/<linea>.md`
3. **Abre el notebook** en `notebooks/lineas_tematicas/` — tiene el ciclo completo preconfigurado con datos sintéticos
4. **Reemplaza los datos sintéticos** por tus datos reales (CSV del DHIME, RMCAB, o tu sistema interno)
5. **Ajusta el modelo** según el diagnóstico de estacionariedad y la estacionalidad de tu variable
6. **Ejecuta el script** `scripts/fase8_<linea>.py` para regenerar todos los reportes en un solo paso

Para agregar una línea temática nueva o adaptar el código a otra entidad, el punto de entrada es `scripts/build_notebooks.py` para los notebooks y `config.py` para los umbrales normativos.

---

## Atribución

Este repositorio se construye sobre el trabajo de **Tomás Cárdenas López** ([@TomCardeLo](https://github.com/TomCardeLo)):

> **[boa-sarima-forecaster](https://github.com/TomCardeLo/boa-sarima-forecaster)**  
> Pipeline modular de pronóstico con SARIMA y optimización bayesiana (Optuna TPE).

Los módulos `optimization/bayes_opt.py`, `evaluation/metrics.py`, `predictive/classical.py` y `config.py` se heredan parcialmente de ese repositorio y se adaptan al dominio ambiental colombiano. Cada módulo heredado lleva en su encabezado:

```python
# Adaptado de boa-sarima-forecaster/<módulo>.py por Dan Méndez — <fecha>
```

---

## Autor

**Dan Méndez** — Analista de Datos, Gestión Ambiental Institucional, Colombia  
GitHub: [@DanMendezZz](https://github.com/DanMendezZz)

---

*Construido para las entidades del Sistema Nacional Ambiental (SINA) de Colombia.*  
*Ministerio de Ambiente · CARs · IDEAM · Institutos de Investigación Ambiental*
