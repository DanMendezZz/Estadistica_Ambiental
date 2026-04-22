# Geoespacial — Capa técnica transversal

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/d8dddf1a-463b-4d6b-91b7-bb3832e661f8
> **Última sincronización:** —
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** C (capa técnica)
> **Alimenta a:** áreas protegidas, humedales, páramos, rondas hídricas, POMCA, predios para conservación, ordenamiento territorial

---

## Resumen

*Pendiente — extraer del NotebookLM usando el Prompt D de `Fuentes.md`.*

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

## Métodos espaciales aplicables

- **Interpolación:** IDW, Kriging (ordinario, universal, indicador), splines.
- **Autocorrelación espacial:** I de Moran global y local, C de Geary, G* de Getis-Ord.
- **Regresión espacial:** GWR, SAR, SEM.
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

## Módulo en el repo

`src/estadistica_ambiental/spatial/` (Fase 7)

## Referencias

- ...
