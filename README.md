# Estadística Ambiental Colombia

> **Base de conocimiento Python para el ciclo estadístico completo aplicado a datos ambientales colombianos**  
> EDA → Descriptiva → Inferencial → Predictiva → Cumplimiento normativo

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-427%20passed-brightgreen)]()
[![Cobertura](https://img.shields.io/badge/cobertura-80%25-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Normas CO](https://img.shields.io/badge/Normas-Res.%202254%2F2017%20%7C%202115%2F2007%20%7C%20631%2F2015-green)]()

---

## ¿Para qué sirve?

El repositorio resuelve un problema concreto para analistas de entidades ambientales colombianas (MinAmbiente, CAR, IDEAM, CARs): **no hay que partir de cero en cada línea temática**. Provee:

- **Ciclo estadístico estructurado** (EDA → Descriptiva → Inferencial → Predictiva) adaptado al dominio ambiental
- **Normas colombianas centralizadas** (Res. 2254/2017, 2115/2007, 631/2015, índices IDEAM) listas para verificar cumplimiento desde el código
- **16 fichas de conocimiento de dominio** en [`docs/fuentes/`](docs/fuentes/) — variables, rangos físicos, normativa y fuentes oficiales por línea
- **Conectores a fuentes oficiales** (RMCAB Bogotá, SIATA Medellín, IDEAM DHIME, OpenAQ, datos.gov.co)
- **Catálogo de 10 modelos** comparables entre sí: SARIMA, SARIMAX, Prophet, XGBoost, RandomForest, LightGBM, LSTM, GRU, Kriging, PyMC

---

## Instalación

```bash
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git
cd Estadistica_Ambiental
pip install -e ".[dev]"
```

**Extras opcionales:**

```bash
pip install -e ".[ml]"      # xgboost, lightgbm
pip install -e ".[prophet]" # Meta Prophet
pip install -e ".[profile]" # ydata-profiling, sweetviz
pip install -e ".[spatial]" # geopandas, rasterio, pykrige, folium
pip install -e ".[deep]"    # PyTorch — LSTM, GRU
pip install -e ".[fast]"    # polars — carga rápida de parquet grandes
```

**Verificar:**

```bash
python -m pytest tests/ -q
# 427 passed, 1 skipped, 80% coverage
```

---

## Quickstart

### Cargar, validar y analizar

```python
from estadistica_ambiental.io.loaders import load_csv
from estadistica_ambiental.io.validators import validate
from estadistica_ambiental.inference.stationarity import stationarity_report
from estadistica_ambiental.inference.trend import mann_kendall

df = load_csv("data/raw/pm25_rmcab.csv", date_col="fecha")
rep = validate(df, date_col="fecha", linea_tematica="calidad_aire")

ts = df.set_index("fecha")["pm25"]
stationarity_report(ts)          # ADF + KPSS obligatorio pre-ARIMA (ADR-004)
mk = mann_kendall(ts)
print(f"Tendencia: {mk['trend']} | p={mk['pval']:.4f}")
```

### Backtesting multi-modelo y ranking

```python
from estadistica_ambiental.predictive.registry import get_model
from estadistica_ambiental.evaluation.backtesting import walk_forward
from estadistica_ambiental.evaluation.comparison import rank_models

models = {
    "SARIMA":   get_model("sarima"),
    "XGBoost":  get_model("xgboost", lags=[1, 2, 3, 6, 12, 24]),
    "Prophet":  get_model("prophet"),
}
results = {name: walk_forward(model, ts, horizon=24, n_splits=5)
           for name, model in models.items()}
rank_models(results)[["rmse", "mae", "r2", "rank"]]
```

### Cumplimiento normativo y reporte HTML

```python
from estadistica_ambiental.inference.intervals import exceedance_report
from estadistica_ambiental.reporting.compliance_report import compliance_report

print(exceedance_report(ts, variable="pm25"))   # tabla vs. Res. 2254/2017 + OMS 2021
compliance_report(df, variables=["pm25"], linea_tematica="calidad_aire",
                  output="reports/cumplimiento.html")
```

---

## Ejecutar el ciclo completo por línea temática

```bash
# Ciclo completo con datos sintéticos (cualquier línea)
python scripts/run_linea_tematica.py --linea oferta_hidrica
python scripts/run_linea_tematica.py --linea paramos --modelos sarima,xgboost
python scripts/run_linea_tematica.py --list   # ver las 16 líneas disponibles

# Showcase con datos reales (PM2.5 CAR Cundinamarca)
python scripts/fase8_calidad_aire.py
```

Cada ejecución genera en `data/output/fase8/`: reporte EDA, descriptiva CSV, inferencial JSON, backtesting CSV, reporte HTML de cumplimiento y pronóstico interactivo.

---

## Estructura del proyecto

```
src/estadistica_ambiental/
├── config.py               # Normas colombianas, rutas, parámetros ENSO
├── io/                     # loaders, validators (74 variables), connectors
├── eda/                    # profiling, quality, viz
├── preprocessing/          # imputation, outliers (opt-in), air_quality
├── descriptive/            # univariate, bivariate, temporal (STL/ACF)
├── inference/              # stationarity (ADF+KPSS), trend (MK), intervals
├── features/               # lags, calendar, climate (ENSO+lag), exogenous
├── predictive/             # ARIMA/SARIMA/ETS, Prophet, XGBoost/RF/LGB, LSTM
├── optimization/           # bayes_opt.py (Optuna TPE), optimize_sarima()
├── evaluation/             # metrics, walk_forward (gap=), rank_models
└── reporting/              # forecast_report, compliance_report, stats_report

docs/
├── fuentes/                # 16 fichas técnicas de dominio ✅
├── lineas_tematicas.md     # Tablas de líneas, normas, modelos y ADRs
├── decisiones.md           # ADR-001 a ADR-010
├── metodologia.md          # Ciclo estadístico detallado
└── intake_lider.md         # Cuestionario de onboarding (18 preguntas)

notebooks/lineas_tematicas/ # 16 notebooks por línea temática
scripts/
├── run_linea_tematica.py   # CLI unificado para las 16 líneas
└── fase8_calidad_aire.py   # Showcase con datos reales PM2.5 CAR
```

---

## Documentación detallada

- [Líneas temáticas, normas y modelos](docs/lineas_tematicas.md)
- [Catálogo de modelos y métricas](docs/modelos.md)
- [Decisiones de arquitectura (ADR-001 a ADR-010)](docs/decisiones.md)
- [Fichas de dominio por línea](docs/fuentes/)
- [Cuestionario de onboarding para líderes de área](docs/intake_lider.md)

---

## Atribución

Construido sobre el trabajo de **Tomás Cárdenas López** ([@TomCardeLo](https://github.com/TomCardeLo)):

> **[boa-sarima-forecaster](https://github.com/TomCardeLo/boa-sarima-forecaster)** — pipeline SARIMA con optimización bayesiana (Optuna TPE).

Los módulos `optimization/bayes_opt.py`, `evaluation/metrics.py`, `predictive/classical.py` y `config.py` se heredan parcialmente y se adaptan al dominio ambiental. Ver [`CITATION.cff`](CITATION.cff) para cita formal.

---

**Dan Méndez** — Analista de Datos, Gestión Ambiental Institucional, Colombia · [@DanMendezZz](https://github.com/DanMendezZz)

*Construido para las entidades del Sistema Nacional Ambiental (SINA) de Colombia.*
