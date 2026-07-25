# Líneas temáticas, normas y modelos

Documentación extendida del repositorio `estadistica-ambiental`.

---

## Las 16 líneas temáticas

Organizadas en 3 bloques según su rol en la gestión ambiental.

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

Cada línea tiene su ficha técnica en [`docs/fuentes/`](fuentes/) con: variables clave, rangos físicos, normativa colombiana, métodos sugeridos, actores institucionales, riesgos y preguntas de investigación abiertas.

---

## Normas colombianas integradas

Todas centralizadas en `config.py` — sin hardcodear umbrales en notebooks:

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

---

## Catálogo de modelos

| Familia | Modelos | Cuándo usar |
|---|---|---|
| **Clásicos** | ARIMA, SARIMA, SARIMAX, ETS | Serie estacionaria o diferenciable; estacionalidad conocida |
| **Descomposición** | Prophet, STL+ARIMA | Estacionalidades múltiples; datos con días festivos |
| **ML** | XGBoost, RandomForest, LightGBM | Covariables exógenas; relaciones no lineales |
| **Deep Learning** | LSTM, GRU | Series largas (> 5 años horarios); patrones complejos |
| **Bayesianos/Espaciales** | Kriging, GP, PyMC | Interpolación espacial; incertidumbre cuantificada |

**Métricas por dominio** (configuradas automáticamente en `walk_forward`):

| Dominio | Métricas primarias |
|---|---|
| Calidad del aire | MAE, RMSE, R², hit_rate_ica |
| Hidrología (caudal) | NSE (Nash-Sutcliffe), KGE (Kling-Gupta), PBIAS |
| General | MAE, RMSE, R², sMAPE |

---

## Ciclo estadístico

```
Datos brutos (CSV / NetCDF / SHP / XLSX / API)
        │
        ▼
ETAPA 1 — EDA: Tipificación · Calidad · Perfilado · Visualización
        │
        ▼
ETAPA 2 — Descriptiva: Univariada · Bivariada · Temporal (STL / ACF)
        │
        ▼
ETAPA 3 — Inferencial: ADF+KPSS · Mann-Kendall · Excedencias normativas
        │
        ▼
ETAPA 4 — Predictiva: SARIMA/SARIMAX · Prophet · XGBoost · RF · LSTM
          Walk-forward · Optuna TPE · Ranking multi-criterio
        │
        ▼
CAPA TRANSVERSAL — Espacial: Kriging · GWR · I de Moran · CTM12
        │
        ▼
Reportes HTML (pronóstico · cumplimiento normativo · estadística)
```

---

## Decisiones de arquitectura (ADRs)

Ver [`decisiones.md`](decisiones.md) para el registro completo. Resumen:

| ADR | Decisión |
|---|---|
| ADR-001 | Herencia de `boa-sarima-forecaster` — atribución explícita |
| ADR-002 | Outliers NO automáticos — picos ambientales son señal real |
| ADR-003 | NSE/KGE para hidrología; RMSLE desactivado en variables negativas |
| ADR-004 | ADF + KPSS obligatorios antes de cualquier ARIMA |
| ADR-005 | Normas colombianas centralizadas en `config.py` |
| ADR-006 | Validación con rangos físicos específicos por línea temática |
| ADR-007 | Lags ENSO diferenciados por línea temática |
| ADR-008 | `compliance_report()` separado del reporte predictivo |
| ADR-009 | Conectores a fuentes colombianas en `io/connectors.py` |
| ADR-010 | 10 bugs corregidos en PR #6 con tests de regresión dedicados |

---

## Contexto institucional

La gestión ambiental en Colombia opera bajo un marco normativo robusto y datos dispersos en múltiples sistemas (SIRH, SIAC, RMCAB, SIATA, SMByC). Este repositorio integra ese contexto directamente en el código:

| Reto institucional | Solución en el repo |
|---|---|
| Datos en múltiples formatos (CSV, NetCDF, SHP, XLSX) | `io/loaders.py` — carga unificada |
| Normas distintas por línea temática | `config.py` — único punto de verdad regulatorio |
| Validación física de variables ambientales | `io/validators.py` — 74 variables con rangos por ecosistema |
| Reportes de excedencias para entidades reguladoras | `reporting/compliance_report.py` — HTML con semáforo normativo |
| Influencia del ENSO en variables hídricas | `features/climate.py` — lag diferenciado por línea temática |
| Acceso a datos oficiales dispersos | `io/connectors.py` — RMCAB, SIATA, DHIME, OpenAQ, datos.gov.co |
| Onboarding con líderes de área | `docs/intake_lider.md` — cuestionario de 18 preguntas |
