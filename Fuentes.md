# Fuentes — Contexto de dominio por línea temática

> Este archivo es el **índice maestro** de fuentes de conocimiento de dominio para el repositorio `Estadistica_Ambiental`. Enlaza los NotebookLM de cada línea temática y define cómo traer ese conocimiento a archivos locales que Claude Code pueda leer.
>
> **Última actualización:** 2026-04-22

---

## 1. Por qué este archivo existe

Para que Claude Code tenga contexto de dominio de cada línea temática al planificar código y modelos, se usa este flujo:

```
NotebookLM (remoto, tu cuenta Google)
        ↓
Tú extraes resúmenes / fichas / notas clave
        ↓
Guardas en docs/fuentes/<linea>.md  (local, en el repo)
        ↓
Claude Code lee el .md local cuando lo necesite
```

Los archivos `docs/fuentes/*.md` son lectura opcional: Claude Code los consulta solo cuando se trabaja en esa línea temática específica. Esto mantiene el contexto general liviano y carga conocimiento de dominio "bajo demanda".

---

## 2. Estructura de las 16 líneas temáticas

Se agrupan en tres bloques según su rol:

### Bloque A — Líneas de gestión ambiental (13)
Cada una es un área temática de la gestión ambiental institucional. Son las líneas "clásicas" del plan de trabajo.

### Bloque B — Líneas temáticas transversales (2)
**Cambio climático** y **Calidad del aire** atraviesan o complementan varias líneas del bloque A. Cambio climático es un marco que afecta oferta hídrica, páramos, humedales y gestión de riesgo. Calidad del aire es una línea temática propia, con fuerte componente de series temporales y donde SARIMAX + meteorología da resultados directos.

### Bloque C — Capa técnica transversal (1)
**Geoespacial** es más un **conjunto de herramientas y métodos** (SIG, kriging, análisis espacial) que una línea de gestión. Alimenta transversalmente a páramos, humedales, rondas hídricas, áreas protegidas y predios para conservación. Su ficha se estructura distinto: inventario de capas, métodos espaciales, librerías.

---

## 3. Índice completo de NotebookLM

### Bloque A — Líneas de gestión (13)

| # | Línea temática | NotebookLM | Archivo local destino |
|---|---|---|---|
| 01 | Áreas protegidas | https://notebooklm.google.com/notebook/d504d45a-8e08-4100-8a1e-b73552f55b52 | `docs/fuentes/areas_protegidas.md` |
| 02 | Humedales | https://notebooklm.google.com/notebook/ab4788e2-c053-4a43-a76b-b49bf4881cf4 | `docs/fuentes/humedales.md` |
| 03 | Páramos | https://notebooklm.google.com/notebook/812831f2-26dd-4f56-99c7-1b03c6ae945b | `docs/fuentes/paramos.md` |
| 04 | Dirección directiva | https://notebooklm.google.com/notebook/bed2246f-cb75-4b91-8ca5-8f1b194ecfd1 | `docs/fuentes/direccion_directiva.md` |
| 05 | Gestión de riesgo | https://notebooklm.google.com/notebook/62fe34e3-04b0-40ea-bd80-46a79ed82961 | `docs/fuentes/gestion_riesgo.md` |
| 06 | Ordenamiento territorial | https://notebooklm.google.com/notebook/39ceb3fe-99dc-4e17-ba73-87ec88ef3e25 | `docs/fuentes/ordenamiento_territorial.md` |
| 07 | Oferta hídrica | https://notebooklm.google.com/notebook/c4737b81-3ca0-48fa-942d-eac5f1689b8a | `docs/fuentes/oferta_hidrica.md` |
| 08 | POMCA | https://notebooklm.google.com/notebook/b31e1fbb-9b42-456a-ace9-2a61e12c8d05 | `docs/fuentes/pomca.md` |
| 09 | PUEEA | https://notebooklm.google.com/notebook/76b05acf-5e9e-46d5-9aba-3d5c2891906c | `docs/fuentes/pueea.md` |
| 10 | Recurso hídrico | https://notebooklm.google.com/notebook/be2d8b70-bfda-4925-8624-8a8e8290201a | `docs/fuentes/recurso_hidrico.md` |
| 11 | Rondas hídricas | https://notebooklm.google.com/notebook/56006897-784c-4430-9514-85a42c801cf8 | `docs/fuentes/rondas_hidricas.md` |
| 12 | Sistemas de información ambiental | https://notebooklm.google.com/notebook/ec194313-e870-4121-b75d-8cc2e0a716a6 | `docs/fuentes/sistemas_informacion_ambiental.md` |
| 13 | Predios para conservación | https://notebooklm.google.com/notebook/bc27c5cb-f0fc-4b91-8b78-3c670c7f328a | `docs/fuentes/predios_conservacion.md` |

### Bloque B — Transversales temáticas (2)

| # | Línea | NotebookLM | Archivo local destino | Alimenta a (bloque A) |
|---|---|---|---|---|
| 14 | Cambio climático | https://notebooklm.google.com/notebook/c5870ed5-6bf0-4705-ad8c-738f2d6e439e | `docs/fuentes/cambio_climatico.md` | Oferta hídrica, páramos, humedales, gestión de riesgo, recurso hídrico |
| 15 | Calidad del aire | https://notebooklm.google.com/notebook/96050780-400c-4522-945a-211c406dc516 | `docs/fuentes/calidad_aire.md` | Gestión de riesgo, sistemas de información ambiental |

### Bloque C — Capa técnica transversal (1)

| # | Capa | NotebookLM | Archivo local destino | Alimenta a |
|---|---|---|---|---|
| 16 | Geoespacial | https://notebooklm.google.com/notebook/d8dddf1a-463b-4d6b-91b7-bb3832e661f8 | `docs/fuentes/geoespacial.md` | Todas las líneas con componente espacial (áreas protegidas, humedales, páramos, rondas hídricas, POMCA, predios para conservación, ordenamiento territorial) |

---

## 4. Cómo extraer contenido de un NotebookLM a un `.md` local

Abre el notebook en Google y pídele que genere la información en el formato más útil. Ejemplos de prompts:

### Prompt A — Ficha técnica compacta (para bloques A y B)
```
Genérame una ficha técnica de máximo 1500 palabras con:
1. Resumen ejecutivo (1-2 párrafos).
2. Objetivos principales de esta línea temática.
3. Variables ambientales clave que se manejan.
4. Tipos de datos y fuentes (dónde vienen, frecuencia, formato).
5. Métricas e indicadores oficiales o normativos asociados.
6. Normativa colombiana aplicable (con números de decreto/resolución si las hay).
7. Preguntas analíticas típicas que se responden con estos datos.
8. Métodos estadísticos o modelos que se han usado o se podrían usar.
9. Actores institucionales involucrados.
10. Riesgos o sesgos conocidos en los datos.
Usa bullets cuando sea posible, prosa corta cuando no.
```

### Prompt B — Glosario técnico
```
Lista los 30 términos técnicos más usados en esta línea temática, cada uno con
definición de 1-2 frases. Formato markdown con ## Término seguido de la definición.
```

### Prompt C — Preguntas de investigación sin resolver
```
¿Qué preguntas abiertas, problemas de datos o áreas de mejora identificas en
esta línea temática, que podrían beneficiarse de análisis estadístico o modelos
predictivos?
```

### Prompt D — Capa técnica (solo para Geoespacial, bloque C)
```
Genérame una ficha técnica sobre los aspectos geoespaciales y SIG con:
1. Tipos de capas geográficas (raster, vector, redes) que se manejan.
2. Fuentes de datos geoespaciales usadas (IGAC, IDEAM, MinAmbiente, Copernicus, otras).
3. Sistemas de referencia espacial típicos (MAGNA-SIRGAS, WGS84, CTM12, etc.).
4. Métodos espaciales y geoestadísticos aplicables: kriging, IDW, análisis de
   vecindad, autocorrelación espacial (Moran, Geary), regresión geográficamente
   ponderada (GWR).
5. Librerías Python recomendadas (geopandas, rasterio, rioxarray, xarray,
   pykrige, pysal, shapely, fiona).
6. Problemas típicos: proyecciones, resoluciones mixtas, interpolación entre
   estaciones dispersas, invarianza temporal de las capas base.
7. Integración con el ciclo estadístico del repo (EDA espacial, descriptiva
   espacial, inferencia espacial, predicción espacio-temporal).
```

Copia la respuesta al archivo `.md` correspondiente. Si el notebook tiene citas a fuentes, cópialas al final como referencias.

---

## 5. Plantilla estándar para cada ficha

### 5.1 Plantilla para bloques A y B (líneas temáticas)

```markdown
# <Nombre de la línea temática>

> **NotebookLM fuente:** <URL>
> **Última sincronización:** YYYY-MM-DD
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión) | B (transversal temática)
> **Relación con otras líneas:** <línea_1>, <línea_2>  (solo si aplica)

---

## Resumen ejecutivo
<1-2 párrafos con lo esencial de la línea>

## Objetivos
- ...

## Variables ambientales clave
| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Datos y fuentes
- ...

## Indicadores y métricas oficiales
- ...

## Normativa aplicable (Colombia)
- ...

## Preguntas analíticas típicas
1. ...

## Métodos estadísticos sugeridos
**Descriptiva / inferencial:**
- ...

**Predictiva:**
- ...

**Espacial (si aplica):**
- ...

## Actores institucionales
- ...

## Riesgos y sesgos en los datos
- ...

## Glosario mínimo
- **Término:** definición.

## Preguntas abiertas / oportunidades
- ...

## Referencias
- ...
```

### 5.2 Plantilla para el bloque C (capa técnica geoespacial)

```markdown
# Geoespacial — Capa técnica transversal

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/d8dddf1a-463b-4d6b-91b7-bb3832e661f8
> **Última sincronización:** YYYY-MM-DD
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** C (capa técnica)
> **Alimenta a:** áreas protegidas, humedales, páramos, rondas hídricas, POMCA, predios para conservación, ordenamiento territorial

---

## Resumen
<Qué rol cumple la capa geoespacial en el repo>

## Tipos de capas
- **Raster:** ...
- **Vector (puntos, líneas, polígonos):** ...
- **Redes:** ...

## Fuentes de datos geoespaciales
| Fuente | Qué entrega | Formato | Licencia |
|---|---|---|---|
| IGAC | ... | SHP, GPKG | ... |
| IDEAM | ... | NetCDF, TIFF | ... |
| Copernicus | ... | NetCDF | ... |

## Sistemas de referencia espacial (SRE)
- MAGNA-SIRGAS (EPSG:4686)
- MAGNA-SIRGAS / CTM12 (EPSG:9377)
- WGS84 (EPSG:4326)
- Pseudo-Mercator Web (EPSG:3857)
<cuándo usar cada uno>

## Métodos espaciales aplicables
- **Interpolación:** IDW, Kriging (ordinario, universal, indicador), splines.
- **Autocorrelación espacial:** I de Moran global y local, C de Geary, G* de Getis-Ord.
- **Regresión espacial:** GWR (geographically weighted regression), SAR, SEM.
- **Análisis de vecindad:** matrices de contigüidad reina/torre, k-vecinos, distancia.
- **Análisis de patrones de puntos:** K de Ripley, función L.

## Librerías Python
| Librería | Para qué |
|---|---|
| `geopandas` | Vector, operaciones espaciales, I/O SHP/GPKG |
| `rasterio` / `rioxarray` | Raster |
| `xarray` | Raster multi-dimensional (tiempo + espacio) |
| `pykrige` | Kriging |
| `pysal` / `esda` / `spreg` | Estadística espacial, autocorrelación, regresión espacial |
| `shapely` | Geometría |
| `pyproj` | Proyecciones y reproyecciones |
| `folium` / `contextily` | Visualización en mapas |

## Problemas típicos y mitigaciones
- **Proyecciones mixtas:** ...
- **Resoluciones mixtas:** ...
- **Estaciones dispersas:** ...
- **Capas base desactualizadas:** ...

## Integración con el ciclo estadístico del repo
- **EDA espacial:** mapas de cobertura, densidad, huecos.
- **Descriptiva espacial:** estadísticas por polígono, por cuenca, por zona.
- **Inferencia espacial:** tests de autocorrelación antes de modelar.
- **Predicción espacio-temporal:** Kriging, GP, modelos jerárquicos.

## Módulo sugerido en el repo
`src/estadistica_ambiental/spatial/` (pendiente de crear en Fase futura).

## Referencias
- ...
```

---

## 6. Orden de prioridad sugerido para extraer fichas

No hay que extraer las 16 de golpe. Sugerencia de prioridad según utilidad para validar el pipeline:

**Prioridad alta (series temporales cuantitativas claras, arrancamos aquí):**
1. **Calidad del aire** (B) — el caso más directo para SARIMAX + meteorología, replica el caso de Tomás con variable ambiental.
2. **Oferta hídrica** (A) — caudales y precipitación, base de toda la gestión hídrica.
3. **Recurso hídrico** (A) — complementa oferta hídrica con calidad.
4. **Cambio climático** (B) — aporta marco y covariables a todas las demás.

**Prioridad media:**
5. **Páramos** (A)
6. **Gestión de riesgo** (A)
7. **Humedales** (A)
8. **Geoespacial** (C) — sirve mejor si ya hay casos concretos en los que aplicar métodos espaciales.

**Prioridad media-baja:**
9. Rondas hídricas
10. POMCA
11. PUEEA

**Prioridad baja inicialmente (más normativas/de gestión que de datos temporales):**
12. Áreas protegidas
13. Ordenamiento territorial
14. Predios para conservación
15. Sistemas de información ambiental
16. Dirección directiva

*Este orden puede cambiar. La idea es empezar por las líneas que den ejemplos concretos de series temporales o espaciales para validar el pipeline completo (ciclo estadístico) y luego extenderlo al resto.*

---

## 7. Estado de las fichas

Marca aquí el progreso. Actualiza el estado y la fecha cuando completes cada ficha.

### Bloque A — Gestión (13)

| # | Línea | Estado | Última actualización |
|---|---|---|---|
| 01 | Áreas protegidas | ☐ Pendiente | — |
| 02 | Humedales | ☐ Pendiente | — |
| 03 | Páramos | ☐ Pendiente | — |
| 04 | Dirección directiva | ☐ Pendiente | — |
| 05 | Gestión de riesgo | ☐ Pendiente | — |
| 06 | Ordenamiento territorial | ☐ Pendiente | — |
| 07 | Oferta hídrica | ☐ Pendiente | — |
| 08 | POMCA | ☐ Pendiente | — |
| 09 | PUEEA | ☐ Pendiente | — |
| 10 | Recurso hídrico | ☐ Pendiente | — |
| 11 | Rondas hídricas | ☐ Pendiente | — |
| 12 | Sistemas de información ambiental | ☐ Pendiente | — |
| 13 | Predios para conservación | ☐ Pendiente | — |

### Bloque B — Transversales temáticas (2)

| # | Línea | Estado | Última actualización |
|---|---|---|---|
| 14 | Cambio climático | ☐ Pendiente | — |
| 15 | Calidad del aire | ☐ Pendiente | — |

### Bloque C — Capa técnica (1)

| # | Capa | Estado | Última actualización |
|---|---|---|---|
| 16 | Geoespacial | ☐ Pendiente | — |

Formato de estado:
- ☐ Pendiente
- 🟡 En progreso
- ✅ Completa
- 🔄 Requiere actualización

---

## 8. Cómo las usa Claude Code

Cuando trabajes en Claude Code sobre una línea específica (por ejemplo, el notebook `lineas_tematicas/calidad_aire.ipynb`), pídele explícitamente:

> "Lee `docs/fuentes/calidad_aire.md` y úsalo como contexto para este notebook."

Para líneas que se alimentan de transversales (por ejemplo, oferta hídrica que usa cambio climático como covariable):

> "Lee `docs/fuentes/oferta_hidrica.md` y también `docs/fuentes/cambio_climatico.md` porque vamos a incluir escenarios climáticos."

Para cualquier trabajo con componente espacial:

> "Lee `docs/fuentes/geoespacial.md` además de la ficha de la línea específica."

Puedes también referenciarlos en la cabecera de cada notebook:

```python
# Notebook: Calidad del aire
# Contexto: docs/fuentes/calidad_aire.md
# Covariables: docs/fuentes/cambio_climatico.md (si aplica)
# Plan de trabajo: Plan.md, sección 3 (ciclo estadístico)
```

De esta forma, cada sesión carga solo el contexto relevante y no se sobrecarga la ventana de Claude Code.
