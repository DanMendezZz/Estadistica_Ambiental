# CLAUDE.md — Instrucciones para Claude Code

> Este archivo se sube al repo. Contiene instrucciones permanentes para Claude Code en este proyecto.

## Proyecto

Repositorio `Estadistica_Ambiental` de Dan Méndez.
Plantilla Python para el ciclo estadístico completo (EDA → Descriptiva → Inferencial → Predictiva) aplicado a datos ambientales colombianos.

## Estructura clave

- `Plan.md` — plan de trabajo completo, fases y arquitectura
- `Fuentes.md` — índice de NotebookLM y fichas por línea temática
- `docs/decisiones.md` — registro de decisiones (ADRs)
- `docs/fuentes/<linea>.md` — contexto de dominio por línea (cargarlo bajo demanda)
- `src/estadistica_ambiental/` — código fuente
- `notebooks/` — Jupyter notebooks por etapa y línea temática

## Convenciones de código

- Python 3.10+, type hints siempre en funciones públicas
- `ruff` para linting (configurado en `pyproject.toml`)
- Tests en `tests/` con pytest
- Docstrings solo en funciones públicas no obvias; una línea máximo

## Módulos heredados de boa-sarima-forecaster

Cuando adaptes código de `boa-sarima-forecaster/src/sarima_bayes/`, agrega al inicio del módulo:

```python
# Adaptado de boa-sarima-forecaster/<original>.py por Dan Méndez — <fecha>
```

Cambios de nomenclatura: `SKU` → `variable`, `country` → `estacion`, `forecast_group` → `linea_tematica`.

## Reglas de dominio ambiental

- **Outliers:** NO hacer clipping automático. Picos ambientales (episodios de contaminación, crecidas, tormentas) son señal real. El módulo `preprocessing/outliers.py` debe ser explícitamente opcional.
- **RMSLE:** no usar en variables que pueden ser negativas (anomalías de temperatura, etc.). Usar MAE + sMAPE o NSE como default.
- **Estacionariedad:** antes de cualquier ARIMA, ejecutar ADF + KPSS y emitir advertencia si la serie no es estacionaria.
- **Calidad del aire:** para PM2.5, PM10, O3, NO2 — SARIMAX con meteorología es el modelo baseline.
- **Hidrología:** para caudales — NSE (Nash-Sutcliffe Efficiency) y KGE (Kling-Gupta Efficiency) son las métricas estándar.

## Flujo por sesión

1. Leer `Plan.md` para contexto general y fase activa.
2. Si se trabaja en una línea temática, leer `docs/fuentes/<linea>.md`.
3. Registrar decisiones importantes en `docs/decisiones.md`.
4. Al final de sesión, actualizar la sección `## 11. Seguimiento de avance` en `Plan.md`.

## Ramas Git

- `main` — código estable
- `import-from-boa` — commits de importación del repo origen
- `adapt-to-environmental` — adaptaciones al dominio ambiental
- `feature/*` — funcionalidades propias

## Notas locales

Ver `CLAUDE.local.md` (en `.gitignore`) para notas personales de sesión.
