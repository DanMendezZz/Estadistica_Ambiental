# Estadística Ambiental

Plantilla Python reutilizable para proyectos de estadística aplicada al medio ambiente. Cubre el ciclo estadístico completo: EDA → Descriptiva → Inferencial → Predictiva.

## Objetivo

Dado un dataset ambiental (calidad del aire, hidrología, páramos, humedales, etc.), ejecutar el ciclo estadístico completo con modelos comparados y reportes automáticos.

## Líneas temáticas

16 líneas organizadas en 3 bloques (ver [`Fuentes.md`](Fuentes.md)):

- **Bloque A** — 13 líneas de gestión ambiental (áreas protegidas, humedales, páramos, oferta hídrica, etc.)
- **Bloque B** — 2 transversales temáticas (calidad del aire, cambio climático)
- **Bloque C** — 1 capa técnica transversal (geoespacial)

## Instalación rápida

```bash
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git
cd Estadistica_Ambiental
pip install -e ".[dev]"
```

Instalación modular (dependencias pesadas opcionales):

```bash
pip install -e ".[deep]"    # LSTM, GRU (PyTorch)
pip install -e ".[bayes]"   # PyMC, modelos bayesianos
pip install -e ".[spatial]" # geopandas, pykrige, pysal
```

## Uso básico

```python
from estadistica_ambiental.io.loaders import load_csv
from estadistica_ambiental.eda.profiling import run_eda
from estadistica_ambiental.inference.stationarity import adf_test
from estadistica_ambiental.predictive.registry import ModelRegistry

df = load_csv("data/raw/pm25_rmcab.csv", date_col="fecha", value_col="pm25")
run_eda(df, output="reports/eda_pm25.html")
adf_test(df["pm25"])
```

## Estructura

```
src/estadistica_ambiental/
├── io/           # Ingesta multiformato (CSV, NetCDF, Parquet, SHP)
├── eda/          # Perfilado, tipificación, calidad, visualización
├── preprocessing/ # Imputación, outliers, remuestreo
├── descriptive/  # Univariada, bivariada, temporal (STL, ACF)
├── inference/    # Distribuciones, hipótesis, estacionariedad, tendencia
├── spatial/      # Kriging, GWR, autocorrelación espacial
├── features/     # Lags, calendario, exógenas, covariables climáticas
├── predictive/   # ARIMA, SARIMA, Prophet, XGBoost, RF, LSTM
├── optimization/ # Motor Optuna TPE (Bayesian hyperparameter search)
├── evaluation/   # Backtesting, métricas (NSE, KGE, RMSE, MAE)
└── reporting/    # Reportes HTML/PDF automáticos
```

## MVP recomendado (6 modelos comparados)

1. SARIMA
2. SARIMAX (con covariables meteorológicas)
3. Prophet
4. XGBoost
5. Random Forest
6. LSTM simple

## Atribución

Este repositorio deriva del trabajo de **Tomás Cárdenas** en [`boa-sarima-forecaster`](https://github.com/TomCardeLo/boa-sarima-forecaster).

Los módulos heredados se identifican en el código con el docstring:

```python
# Adaptado de boa-sarima-forecaster/<módulo>.py por Dan Méndez — <fecha>
```

Módulos con mayor herencia: `optimization/bayes_opt.py`, `predictive/classical.py`, `evaluation/metrics.py`.

## Documentación

- [`Plan.md`](Plan.md) — plan de trabajo completo y fases
- [`Fuentes.md`](Fuentes.md) — índice de NotebookLM por línea temática
- [`docs/decisiones.md`](docs/decisiones.md) — registro de decisiones (ADRs)
- [`docs/fuentes/`](docs/fuentes/) — fichas de dominio por línea temática

## Autor

Dan Méndez — 2026
