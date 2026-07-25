# API Reference

Esta página documenta la API pública del paquete `estadistica_ambiental`. La documentación se
genera automáticamente a partir de los docstrings con [mkdocstrings](https://mkdocstrings.github.io/).

> Solo se documentan las funciones y clases con docstrings públicos. Los módulos internos
> (`__pycache__`, helpers privados con `_` inicial) se omiten.

---

## I/O

### io.connectors

::: estadistica_ambiental.io.connectors
    options:
      show_source: false
      heading_level: 4

### io.loaders

::: estadistica_ambiental.io.loaders
    options:
      show_source: false
      heading_level: 4

### io.validators

::: estadistica_ambiental.io.validators
    options:
      show_source: false
      heading_level: 4

---

## EDA

### eda.profiling

::: estadistica_ambiental.eda.profiling
    options:
      show_source: false
      heading_level: 4

### eda.quality

::: estadistica_ambiental.eda.quality
    options:
      show_source: false
      heading_level: 4

### eda.variables

::: estadistica_ambiental.eda.variables
    options:
      show_source: false
      heading_level: 4

### eda.viz

::: estadistica_ambiental.eda.viz
    options:
      show_source: false
      heading_level: 4

---

## Preprocesamiento

### preprocessing.air_quality

::: estadistica_ambiental.preprocessing.air_quality
    options:
      show_source: false
      heading_level: 4

### preprocessing.imputation

::: estadistica_ambiental.preprocessing.imputation
    options:
      show_source: false
      heading_level: 4

### preprocessing.outliers

::: estadistica_ambiental.preprocessing.outliers
    options:
      show_source: false
      heading_level: 4

### preprocessing.resampling

::: estadistica_ambiental.preprocessing.resampling
    options:
      show_source: false
      heading_level: 4

---

## Estadística descriptiva

### descriptive.univariate

::: estadistica_ambiental.descriptive.univariate
    options:
      show_source: false
      heading_level: 4

### descriptive.bivariate

::: estadistica_ambiental.descriptive.bivariate
    options:
      show_source: false
      heading_level: 4

### descriptive.temporal

::: estadistica_ambiental.descriptive.temporal
    options:
      show_source: false
      heading_level: 4

---

## Inferencia

### inference.distributions

::: estadistica_ambiental.inference.distributions
    options:
      show_source: false
      heading_level: 4

### inference.hypothesis

::: estadistica_ambiental.inference.hypothesis
    options:
      show_source: false
      heading_level: 4

### inference.intervals

::: estadistica_ambiental.inference.intervals
    options:
      show_source: false
      heading_level: 4

### inference.stationarity

::: estadistica_ambiental.inference.stationarity
    options:
      show_source: false
      heading_level: 4

### inference.trend

::: estadistica_ambiental.inference.trend
    options:
      show_source: false
      heading_level: 4

---

## Modelos predictivos

### predictive.base

::: estadistica_ambiental.predictive.base
    options:
      show_source: false
      heading_level: 4

### predictive.classical

::: estadistica_ambiental.predictive.classical
    options:
      show_source: false
      heading_level: 4

### predictive.ml

::: estadistica_ambiental.predictive.ml
    options:
      show_source: false
      heading_level: 4

### predictive.deep

> Requiere `pip install estadistica-ambiental[deep]` (PyTorch + Lightning).

::: estadistica_ambiental.predictive.deep
    options:
      show_source: false
      heading_level: 4

### predictive.bayesian

> Requiere `pip install estadistica-ambiental[bayes]` (PyMC + ArviZ). Ver
> [ADR-016](adr/ADR-016-pymc-bayesiano-fase10.md).

::: estadistica_ambiental.predictive.bayesian
    options:
      show_source: false
      heading_level: 4

### predictive.prophet_model

> Requiere `pip install estadistica-ambiental[prophet]`.

::: estadistica_ambiental.predictive.prophet_model
    options:
      show_source: false
      heading_level: 4

### predictive.residual_ar

::: estadistica_ambiental.predictive.residual_ar
    options:
      show_source: false
      heading_level: 4

### predictive.spatial_models

::: estadistica_ambiental.predictive.spatial_models
    options:
      show_source: false
      heading_level: 4

### predictive.registry

::: estadistica_ambiental.predictive.registry
    options:
      show_source: false
      heading_level: 4

---

## Evaluación

### evaluation.metrics

::: estadistica_ambiental.evaluation.metrics
    options:
      show_source: false
      heading_level: 4

### evaluation.backtesting

::: estadistica_ambiental.evaluation.backtesting
    options:
      show_source: false
      heading_level: 4

### evaluation.anomaly

::: estadistica_ambiental.evaluation.anomaly
    options:
      show_source: false
      heading_level: 4

### evaluation.comparison

::: estadistica_ambiental.evaluation.comparison
    options:
      show_source: false
      heading_level: 4

---

## Features

### features.climate

::: estadistica_ambiental.features.climate
    options:
      show_source: false
      heading_level: 4

### features.lags

::: estadistica_ambiental.features.lags
    options:
      show_source: false
      heading_level: 4

### features.calendar

::: estadistica_ambiental.features.calendar
    options:
      show_source: false
      heading_level: 4

### features.exogenous

::: estadistica_ambiental.features.exogenous
    options:
      show_source: false
      heading_level: 4

---

## Optimización

### optimization.bayes_opt

::: estadistica_ambiental.optimization.bayes_opt
    options:
      show_source: false
      heading_level: 4

---

## Análisis espacial

> Requiere `pip install estadistica-ambiental[spatial]` (geopandas + rasterio +
> pysal + esda + folium). Ver ADR-013 en [`decisiones.md`](decisiones.md).

### spatial.io

::: estadistica_ambiental.spatial.io
    options:
      show_source: false
      heading_level: 4

### spatial.projections

::: estadistica_ambiental.spatial.projections
    options:
      show_source: false
      heading_level: 4

### spatial.analysis

::: estadistica_ambiental.spatial.analysis
    options:
      show_source: false
      heading_level: 4

### spatial.autocorrelation

::: estadistica_ambiental.spatial.autocorrelation
    options:
      show_source: false
      heading_level: 4

### spatial.interpolation

::: estadistica_ambiental.spatial.interpolation
    options:
      show_source: false
      heading_level: 4

### spatial.viz

::: estadistica_ambiental.spatial.viz
    options:
      show_source: false
      heading_level: 4

---

## Reporting

### reporting.compliance_report

::: estadistica_ambiental.reporting.compliance_report
    options:
      show_source: false
      heading_level: 4

### reporting.forecast_report

::: estadistica_ambiental.reporting.forecast_report
    options:
      show_source: false
      heading_level: 4

### reporting.stats_report

::: estadistica_ambiental.reporting.stats_report
    options:
      show_source: false
      heading_level: 4

---

## Configuración

### config

::: estadistica_ambiental.config
    options:
      show_source: false
      heading_level: 4
