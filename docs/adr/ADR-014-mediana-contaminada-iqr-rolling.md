# ADR-014 — Mediana contaminada en IQR rolling (B1)

**Fecha:** 2026-05-07
**Estado:** Aceptado — corregido en este repo
**Origen:** Proyecto hermano CAR (`02_Preprocesamiento/01_outliers_iqr.py` paso 3) —
documentado en `Plan/Feedback/feed_aire.md` §"Bug fix B1 — Mediana contaminada en IQR" y
en `Plan/Feedback/repo_estadistica_ambiental_feedback.md` §3.1.D.

## Contexto

El pipeline de calidad del aire de CAR aplicaba reemplazo por mediana rolling sobre
los outliers detectados con IQR. El patrón "original" (con bug) era:

```python
# Calcula la mediana sobre la serie completa, incluidos los outliers que
# justamente vamos a reemplazar
df["pm25_roll_med"] = df["pm25"].rolling(24).median()
df.loc[df["flag"] == "iqr_hard", "pm25"] = df["pm25_roll_med"]
```

### Síntoma del bug

Cuando una ventana rolling de 24 h contiene varios outliers consecutivos (un episodio
de polución de varias horas), la mediana resultante queda contaminada por los propios
valores extremos a reemplazar. Resultado: el "valor imputado" sigue siendo
artificialmente alto y conserva una porción del sesgo del outlier original. Si además
el reemplazo se hace en cascada (outlier i+1 ya parcialmente imputado se incluye en la
ventana del outlier i+2), el sesgo se propaga hacia adelante.

### Por qué pasó desapercibido

- El reemplazo no producía NaNs ni excepciones — los valores reemplazados eran
  numéricamente plausibles (entre el outlier y la mediana real).
- Los tests unitarios pasaban con outliers aislados (1 punto): la ventana rolling
  contenía suficientes valores limpios para que la contaminación fuera marginal.
- El sesgo solo se hace evidente con episodios sostenidos (≥4 h consecutivas
  sobre umbral), que son precisamente los que más importan en gestión de calidad
  del aire.

### Cómo se descubrió en CAR

Durante la Sesión S2 (2026-04-23 mañana) del pipeline CAR, al comparar la
distribución de `pm25_imputado` contra la mediana del mes en valores `original`,
los percentiles altos (p90, p95) del imputado quedaron sistemáticamente por encima
de los percentiles equivalentes en valores limpios. La inspección manual de
episodios reveló que los reemplazos seguían un patrón monotónicamente decreciente
(la cola del episodio "ensuciaba" la imputación de su cabeza). Ver
`Plan/Feedback/feed_aire.md` líneas 414-425.

## Decisión

El patrón correcto exige **pre-determinar los índices de outliers antes de calcular
la mediana** y enmascararlos como NaN durante el cálculo:

```python
# 1. Determinar índices ANTES de imputar
idx_hard = result.index[mask_hard]
idx_soft = result.index[mask_soft]

# 2. Copia limpia con outliers como NaN
serie_clean = result.loc[base_iqr, value_col].copy()
all_outliers = idx_hard.union(idx_soft)
serie_clean.loc[serie_clean.index.isin(all_outliers)] = np.nan

# 3. Calcular mediana rolling sobre la serie ya limpia
mediana_local = serie_clean.rolling(5, center=True, min_periods=1).median()

# 4. Recién ahora reemplazar
result.loc[idx_hard, value_col] = mediana_local.reindex(idx_hard)
result.loc[idx_soft, value_col] = mediana_local.reindex(idx_soft)
```

`min_periods=1` permite que la ventana avance aunque haya NaNs, y `center=True`
distribuye el contexto simétricamente alrededor del punto a imputar.

## Estado en este repo

`flag_spatial_episodes()` en `src/estadistica_ambiental/preprocessing/air_quality.py`
ya implementa el patrón correcto:

| Paso | Línea | Código clave |
|---|---|---|
| Pre-determinar `idx_hard` e `idx_soft` antes de imputar | `air_quality.py:362-369` | `base_iqr = mask_mes & (result["flag_episode"] == "original") ...` |
| NaN-maskear los outliers en la copia local | `air_quality.py:375-377` | `serie_clean.loc[serie_clean.index.isin(all_outliers)] = np.nan` |
| Rolling median sobre la serie limpia | `air_quality.py:380` | `mediana_local = serie_clean.rolling(5, center=True, min_periods=1).median()` |
| Reemplazo posterior con `reindex` | `air_quality.py:382-389` | `result.loc[idx_hard, value_col] = mediana_local.reindex(idx_hard)` |

`flag_outliers()` (`outliers.py:24-69`) NO sufre este bug porque usa clipping a los
límites IQR (no rolling median replacement) y porque `treat=False` por defecto
(ADR-002 — los picos ambientales se preservan como señal real).

`detect_regional_episodes()` (`outliers.py:105-298`) tampoco aplica imputación: solo
clasifica candidatos como `regional` o `puntual` y deja los valores originales
intactos (ver docstring línea 137: "NO modifica los valores").

ADR-010 (PR #6, §8 "Mediana de imputación limpia") ya cubrió la corrección de este
bug específico en el módulo `air_quality.py`. Este ADR-014 lo eleva a una **lección
de diseño general**: cualquier API futura que combine detección y reemplazo basado
en estadísticos de ventana móvil debe seguir el mismo patrón.

## Lección aprendida

Cuando se mezcla detección (umbral basado en estadísticos) con reemplazo (mediana,
media, otra agregación), **separar el cálculo del estadístico del muestreo de los
valores a reemplazar**. La regla mnemotécnica es:

> "La estadística de imputación debe calcularse sobre datos que NO incluyan
> aquello que vas a imputar."

Equivalentes en otros dominios:
- En cross-validation, no se calcula la media del scaler con los datos de test.
- En interpolación de series, los puntos NaN no entran al cálculo del polinomio.
- En bootstrap, los outliers detectados no participan del re-muestreo si se quieren
  intervalos robustos.

## Consecuencias

- El test `tests/test_regression_pr6.py::test_b1_mediana_no_contaminada`
  protege la corrección.
- Cualquier nuevo módulo de imputación basado en ventanas móviles debe documentar
  explícitamente cómo aísla los valores a imputar del cálculo del estadístico.
- Este ADR es referenciado desde el docstring de `flag_spatial_episodes`.
