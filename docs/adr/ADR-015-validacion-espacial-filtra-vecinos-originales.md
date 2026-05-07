# ADR-015 — Validación espacial de outliers debe filtrar vecinos `flag_outlier == "original"` (B2)

**Fecha:** 2026-05-07
**Estado:** Aceptado — corregido en este repo
**Origen:** Proyecto hermano CAR (`02_Preprocesamiento/01_outliers_iqr.py` paso 2) —
documentado en `Plan/Feedback/feed_aire.md` §"Bug fix B2 — Vecino sin filtro flag_outlier"
y en `Plan/Feedback/repo_estadistica_ambiental_feedback.md` §3.1.D.

## Contexto

Cuando un episodio sostenido en una estación se valida contra estaciones vecinas
("¿también estuvo elevado el vecino en la misma ventana?"), el umbral del vecino se
calcula con su propio Q1/Q3/IQR mensuales. El patrón "original" (con bug) era:

```python
# El Q3 del vecino se calcula sobre TODA su serie, incluyendo valores
# que ya fueron intervenidos en iteraciones anteriores
vecino_q3 = df_vecino["pm25"].quantile(0.75)
umbral_vec = vecino_q3 + 1.5 * iqr_vec
```

### Síntoma del bug

El loop de validación procesa estaciones secuencialmente. Cuando le toca el turno
a la estación N, las estaciones 1..N-1 ya tuvieron sus outliers reemplazados por la
mediana local (paso 3 del pipeline) o etiquetados como `cap_absoluto`. Si la
estación N es **vecina** de alguna de esas estaciones ya intervenidas, el cálculo
del Q3 del vecino mezcla:
- Valores reales originales.
- Medianas locales (artificialmente cercanas al centro de la distribución).
- Valores capeados (truncados al percentil 99.9).

Esto **aplana la distribución del vecino**, baja Q3 e IQR, y baja por tanto el
umbral `Q3 + 1.5×IQR` con el que se confirma el episodio en la estación N. El
sesgo va siempre en el mismo sentido: **más episodios se confirman como
"regionales"** de los que realmente lo son. La confirmación se vuelve recursivamente
optimista.

### Por qué pasó desapercibido

- Sin un test que comparase resultados con/sin filtro, el sesgo es invisible: no
  hay excepción, no hay NaN, las cuentas finales tienen sentido.
- El bug es **dependiente del orden de iteración**: la primera estación procesada
  no sufre del bug (no hay vecinos intervenidos todavía). Solo las últimas
  estaciones del loop ven el efecto completo.
- En tests unitarios con 2-3 estaciones, el efecto era marginal o nulo.
- A nivel agregado, los conteos de "regional vs puntual" no eran obviamente
  incorrectos (el patrón meteorológico real produce muchos episodios regionales
  reales en Bogotá invierno).

### Cómo se descubrió en CAR

Durante la Sesión S2 (2026-04-23 mañana) del pipeline CAR, al re-ejecutar el
pipeline con un orden de estaciones diferente (alfabético vs por código DANE), los
conteos de episodios regionales por estación cambiaban hasta en un 8%. Eso fue la
señal: un algoritmo determinista no debe depender del orden de procesamiento.
La inspección reveló que el Q3 del vecino estaba siendo calculado sobre la serie
ya intervenida. Ver `Plan/Feedback/feed_aire.md` líneas 429-437.

## Decisión

Cualquier estadístico de un vecino usado para confirmar/descartar un episodio en
otra estación **debe restringirse a observaciones con `flag_outlier == "original"`**
(o equivalente: el flag inicial antes de cualquier intervención).

```python
# Filtro explícito: solo valores no intervenidos del vecino
mask_vec_mes = (
    (result[station_col] == vecino)
    & (result["_month"] == mes)
    & (result["flag_episode"] == "original")
    & result[value_col].notna()
)
serie_vec = result.loc[mask_vec_mes, value_col]
q3v = serie_vec.quantile(0.75)
iqrv = q3v - serie_vec.quantile(0.25)
umbral_vec = q3v + 1.5 * iqrv
```

El mismo principio aplica al pivot estación×tiempo usado para verificar la
elevación simultánea: debe excluir valores ya marcados como `cap_absoluto` o
imputados.

## Estado en este repo

`flag_spatial_episodes()` en `src/estadistica_ambiental/preprocessing/air_quality.py`
ya implementa el filtro correcto en los dos puntos críticos:

| Punto | Línea | Código clave |
|---|---|---|
| Filtro del pivot espacial — excluye `cap_absoluto` antes del unstack | `air_quality.py:258` | `result.loc[result["flag_episode"] != "cap_absoluto", ...]` |
| Filtro del Q1/Q3/IQR de la propia estación | `air_quality.py:279-281` | `mask_mes & (result["flag_episode"] == "original") & ...` |
| Filtro del Q3/IQR del vecino para umbral de confirmación | `air_quality.py:336-341` | `(result[station_col] == vecino) & ... & (result["flag_episode"] == "original") & result[value_col].notna()` |

`detect_regional_episodes()` en `src/estadistica_ambiental/preprocessing/outliers.py`
es por construcción **inmune al bug**:
- No imputa valores: solo etiqueta `original` / `regional` / `puntual`
  (ver docstring `outliers.py:137` "NO modifica los valores").
- El cálculo de Q1/Q3/IQR del vecino (`outliers.py:265-271`) opera sobre la serie
  cruda, ya que ningún valor cambió jamás durante el flujo.

`flag_outliers()` (`outliers.py:24-69`) tampoco aplica: es una API univariada que
no compara con vecinos espaciales.

ADR-010 (PR #6, §7 "`flag_spatial_episodes` determinismo") ya cubrió la corrección
en el código de producción. Este ADR-015 lo eleva a una **regla de diseño
arquitectónico**: cualquier futura API de "spatial outlier confirmation" debe
documentar explícitamente cómo filtra vecinos para evitar confirmaciones
recursivamente sesgadas.

## Lección aprendida

Algoritmos que iteran sobre estaciones (o cualquier entidad) y modifican el estado
del DataFrame en cada iteración deben tratar el estado del vecino como
**inmutable a efectos del cálculo de umbrales**. La regla mnemotécnica:

> "Cuando preguntas algo a un vecino, pregunta por su versión original — no por
> la versión que tu propio algoritmo le dejó."

La señal canaria del bug es: **el resultado del algoritmo cambia con el orden de
iteración**. Si una corrida con estaciones ordenadas alfabéticamente difiere de
otra con orden por código, hay un acoplamiento entre iteraciones que debe
romperse.

Equivalentes en otros dominios:
- Algoritmos jerárquicos (Bayesianos): los hyperparámetros del nivel padre no se
  re-estiman con los priors del nivel hijo.
- Cross-validation espacial: en LOO-CV geográfico, el modelo del fold k no ve
  ningún punto del fold k.
- Calibración entre estaciones (cokriging): la matriz de covarianza se calcula
  con datos no intervenidos, no con los re-imputados.

## Consecuencias

- El resultado de `flag_spatial_episodes` es ahora **determinista respecto al
  orden de iteración** (test `tests/test_regression_pr6.py::test_b2_orden_estaciones_estable`).
- Cualquier extensión futura (ej. clustering espacial de episodios, kriging
  bayesiano sobre flags) debe heredar el mismo invariante: las estadísticas
  inter-estación se calculan sobre observaciones `original`.
- Este ADR es referenciado desde el docstring de `flag_spatial_episodes` y de
  `detect_regional_episodes`.
