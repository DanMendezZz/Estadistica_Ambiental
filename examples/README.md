# Examples — Estadistica_Ambiental

Snippets cortos y runnables que muestran cómo usar la librería para tareas
típicas del ciclo estadístico en datos ambientales colombianos.

> Estos ejemplos son **plantillas mínimas** — no reemplazan los notebooks
> de `notebooks/lineas_tematicas/`, que contienen el flujo completo y
> el contexto de dominio. Para algo en producción, copia el snippet a
> tu propio repo satélite y adáptalo.

## Uso

Todos los scripts son ejecutables directamente:

```bash
python examples/00_quickstart.py
python examples/01_calidad_aire_pm25.py
```

Cada script es **autocontenido**: si no encuentra datos reales (p. ej.
`SISAIRE_LOCAL_DIR` no configurada), genera datos sintéticos para que
puedas ver el flujo end-to-end sin descargar nada.

## Índice

| Script | Línea temática | Demuestra |
|---|---|---|
| `00_quickstart.py` | — | Cargar → validar → describir → reportar (mínimo viable) |
| `01_calidad_aire_pm25.py` | calidad_aire | `load_sisaire_local`, `exceedance_report`, ICA |
| `02_oferta_hidrica_caudal.py` | oferta_hidrica | NSE/KGE, ENSO con lag, descomposición temporal |
| `03_paramos_iuh.py` | paramos | IRH, gradiente Caldas-Lang, validación por dominio |
| `04_cambio_climatico_co2.py` | cambio_climatico | Mann-Kendall, Sen slope, Pettitt |
| `05_eda_generico.py` | — | `run_eda` + perfilado + reporte HTML |

## Tabla de imports rápidos

```python
# I/O
from estadistica_ambiental.io.connectors import load_sisaire_local, load_openaq
from estadistica_ambiental.io.validators import validate

# Inferencia y cumplimiento
from estadistica_ambiental.inference.intervals import exceedance_report
from estadistica_ambiental.inference.stationarity import adf_test
from estadistica_ambiental.inference.trend import mann_kendall

# Features climáticos
from estadistica_ambiental.features.climate import enso_lagged, load_oni

# Reportes
from estadistica_ambiental.reporting.compliance_report import compliance_report
from estadistica_ambiental.reporting.stats_report import stats_report
```

## Convenciones en los snippets

- Las salidas (HTML, CSV) se escriben a `data/output/examples/` (creada al vuelo).
- Las funciones de descarga real (`load_sisaire_local`, `load_openaq`) se
  envuelven en try/except para caer a sintético.
- Los snippets asumen `pip install -e ".[ml,profile]"` mínimo.
