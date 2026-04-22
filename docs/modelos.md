# Catálogo de modelos predictivos

> Referencia de los modelos disponibles en `src/estadistica_ambiental/predictive/`.
> Para agregar un modelo nuevo: implementar `BaseModel` y registrar con `registry.register()`.

---

## Familia 1 — Estadísticos clásicos (baseline obligatorio)

### ARIMA
- **Módulo:** `predictive/classical.py` → `ARIMAModel`
- **Interfaz:** `get_model("arima", order=(p,d,q))`
- **Cuándo usar:** baseline rápido, series estacionarias o con pocas observaciones.
- **Limitaciones:** no captura estacionalidad, sin exógenas.

### SARIMA
- **Módulo:** `predictive/classical.py` → `SARIMAModel`
- **Interfaz:** `get_model("sarima", order=(p,d,q), seasonal_order=(P,D,Q,s))`
- **Cuándo usar:** series con estacionalidad clara (PM2.5 anual, caudales mensuales).
- **Parámetros `s`:** 12 (mensual→anual), 7 (diario→semanal), 24 (horario→diario).

### SARIMAX
- **Módulo:** `predictive/classical.py` → `SARIMAXModel`
- **Interfaz:** `get_model("sarimax", order=..., seasonal_order=...)`
- **Cuándo usar:** calidad del aire con covariables meteorológicas (temperatura, viento, humedad).
- **Literatura:** mejora sustancial vs. SARIMA puro en PM2.5.

### ETS / Holt-Winters
- **Módulo:** `predictive/classical.py` → `ETSModel`
- **Interfaz:** `get_model("ets", trend="add", seasonal="add", seasonal_periods=12)`
- **Cuándo usar:** baseline rápido con estacionalidad suave.

---

## Familia 2 — Descomposición y tendencia

### Prophet
- **Módulo:** `predictive/prophet_model.py` → `ProphetModel`
- **Instalación:** `pip install prophet`
- **Interfaz:** `get_model("prophet")` (no en registry por defecto — añadir con `register()`)
- **Cuándo usar:** horizontes medios (1 día a 1 semana), estacionalidades múltiples, outliers.
- **Nota:** autodetecta la frecuencia de la serie.

---

## Familia 3 — Machine Learning

### XGBoost
- **Módulo:** `predictive/ml.py` → `XGBoostModel`
- **Interfaz:** `get_model("xgboost", lags=[1,2,3,7,14])`
- **Cuándo usar:** muchas variables exógenas, relaciones no lineales.
- **Feature engineering:** lag features automáticos internos.

### Random Forest
- **Módulo:** `predictive/ml.py` → `RandomForestModel`
- **Interfaz:** `get_model("random_forest", lags=[1,2,3,7,14])`
- **Cuándo usar:** robusto con datos ruidosos, requiere menos tuning que XGBoost.

### LightGBM
- **Módulo:** `predictive/ml.py` → `LightGBMModel`
- **Instalación:** incluida en requirements.txt
- **Interfaz:** `get_model("lightgbm", lags=[1,2,3,7,14])`
- **Cuándo usar:** datasets grandes, más rápido que XGBoost.

---

## Familia 4 — Deep Learning (Fase futura)

| Modelo | Módulo destino | Estado |
|---|---|---|
| LSTM simple | `predictive/deep.py` | Pendiente |
| GRU | `predictive/deep.py` | Pendiente |
| CNN-LSTM | `predictive/deep.py` | Pendiente |
| N-BEATS | `predictive/deep.py` | Pendiente |

Requiere: `pip install estadistica-ambiental[deep]` (PyTorch + Lightning).

---

## Familia 5 — Bayesianos y espaciales (Fase futura)

| Modelo | Módulo destino | Estado |
|---|---|---|
| Kriging / GP | `predictive/spatial_models.py` | Parcial (interpolation.py) |
| SARIMA bayesiano | `predictive/bayesian.py` | Pendiente |
| Jerárquico multi-estación | `predictive/bayesian.py` | Pendiente |

Requiere: `pip install estadistica-ambiental[bayes]` (PyMC + ArviZ).

---

## MVP recomendado

Para un dataset ambiental nuevo, comparar estos 4 en orden:

1. **SARIMA** — entender el baseline estadístico puro.
2. **SARIMAX** — añadir covariables meteorológicas o climáticas.
3. **XGBoost** — captura no linealidades que SARIMA pierde.
4. **Prophet** — si hay múltiples estacionalidades o eventos especiales.

Usar `evaluation/comparison.py → rank_models()` para selección automática.

---

## Agregar un modelo nuevo

```python
from estadistica_ambiental.predictive.base import BaseModel
from estadistica_ambiental.predictive.registry import register
import numpy as np

class NaiveModel(BaseModel):
    name = "Naive"

    def fit(self, y, X=None):
        self._last = float(y.iloc[-1])
        self._fitted = True
        return self

    def predict(self, horizon, X_future=None):
        return np.full(horizon, self._last)

register("naive", NaiveModel)
```

---

## Optimización de hiperparámetros

Todos los modelos son compatibles con `optimization/bayes_opt.py`:

```python
from estadistica_ambiental.optimization.bayes_opt import optimize, sarima_search_space
from estadistica_ambiental.evaluation.metrics import rmse
import optuna

def objective(trial):
    params = sarima_search_space(trial)
    model = SARIMAModel(order=(params["p"], params["d"], params["q"]),
                        seasonal_order=(params["P"], params["D"], params["Q"], params["s"]))
    result = walk_forward(model, ts, horizon=7, n_splits=3)
    return result["metrics"]["rmse"]

study = optimize(objective, n_trials=50)
```
