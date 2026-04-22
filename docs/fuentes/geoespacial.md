# Geoespacial — Capa técnica transversal

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/d8dddf1a-463b-4d6b-91b7-bb3832e661f8
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** C (capa técnica)
> **Alimenta a:** Áreas protegidas, humedales, páramos, rondas hídricas, POMCA, predios para conservación, ordenamiento territorial, gestión de riesgo, cambio climático

---

## Resumen

La capa geoespacial es el conjunto de herramientas, métodos y datos que permiten representar, analizar y modelar variables ambientales en el espacio geográfico. No es una línea de gestión en sí misma, sino el soporte transversal que alimenta a todas las demás líneas temáticas del repositorio. Incluye datos raster, vectoriales y de redes, así como métodos de interpolación espacial, autocorrelación y regresión geográficamente ponderada.

---

## Tipos de capas geográficas

- **Raster:** Imágenes multiespectrales (Landsat 8/9, Sentinel-2, ALOS PALSAR), Modelos Digitales de Elevación (DEM/SRTM), mapas de estimación de densidad de Kernel para hotspots de deforestación (cuadrículas de 4 ha), y datos de humedad del suelo (SMAP L4).
- **Vector (puntos, líneas, polígonos):** Áreas administrativas, zonificación hidrográfica, delimitación de territorios (resguardos indígenas, coberturas Corine Land Cover), georreferenciación de estaciones hidrometeorológicas.
- **Redes:** Modelado de accesibilidad y movilidad territorial — vías como polilíneas con atributos de fricción o tiempo de viaje para estimar accesibilidad a servicios públicos o cuencas.

---

## Fuentes de datos geoespaciales

| Fuente | Qué entrega | Formato | Licencia |
|---|---|---|---|
| IGAC | Cartografía básica oficial, geodesia, catastro | SHP, GPKG, GDB | Pública |
| IDEAM | DHIME (estaciones hidrometeorológicas), coberturas de la tierra, SMByC, pronósticos | Raster, SHP, CSV | Pública |
| MADS / SIAC | Plataformas institucionales (RENARE, VITAL) | API REST, SHP | Pública |
| Copernicus (ESA) | Sentinel-1 (radar), Sentinel-2 (óptico), C3S (clima) | NetCDF, GeoTIFF | Pública/Abierta |
| NASA / SERVIR | ALOS PALSAR (DEM, radar), SMAP L4 (humedad suelo), Landsat | GeoTIFF, NetCDF | Pública |
| DANE | Estadísticas socioeconómicas, Encuesta de Calidad de Vida | CSV, XLSX | Pública |

---

## Sistemas de referencia espacial (SRE)

- **MAGNA-SIRGAS (EPSG:4686):** Marco Geocéntrico Nacional de Referencia para Colombia. Equivalente oficial, compatible con sistemas GNSS globales (elipsoide GRS 1980). Usar para datos en coordenadas geográficas.
- **Origen Nacional CTM12 (EPSG:9377):** Proyección Transversa de Mercator Secante, único origen a nivel nacional (Resolución IGAC 370 de 2021). Falso Este: 5.000.000 m; Falso Norte: 2.000.000 m. Usar para datos proyectados en metros.
- **WGS84 (EPSG:4326):** Sistema global usado en GPS y servicios web. Usar para interoperabilidad con plataformas internacionales.
- **Pseudo-Mercator Web (EPSG:3857):** Para visualización en mapas web (Google Maps, OpenStreetMap). No usar para cálculos de área o distancia.
- **Orígenes locales anteriores:** MAGNA Bogotá (EPSG:3116), MAGNA Oeste (EPSG:3115), MAGNA Cali (EPSG:6249) — usar solo para compatibilidad con datos históricos.

---

## Métodos espaciales aplicables

- **Interpolación:**
  - Kriging Ordinario y Universal: Mejor estimador lineal insesgado, modela la autocorrelación espacial con variograma. Más preciso que IDW para propiedades físicas del suelo en zonas no muestreadas.
  - IDW (Distancia Inversa Ponderada): Método determinístico, más simple. Menor precisión predictiva que Kriging en estudios de suelos colombianos.
  - Splines.

- **Autocorrelación espacial:**
  - I de Moran (global y local): Determina si un fenómeno (deforestación, contaminación) está agrupado, disperso o es aleatorio.
  - C de Geary, G* de Getis-Ord: Para hotspots y coldspots locales.

- **Regresión espacial:**
  - GWR (Regresión Geográficamente Ponderada): Modelo local que asume no-estacionariedad espacial. Los coeficientes varían en el territorio. Ideal para modelar cómo los impulsores de deforestación o la accesibilidad a servicios cambian de impacto según la región.
  - SAR, SEM: Modelos de autocorrelación espacial global.

- **Análisis de vecindad:**
  - Matrices de contigüidad reina/torre, k-vecinos, distancia.

- **Modelos de datos relacionales para tierras:**
  - LADM_COL (ISO 19152): Para interrelacionar derechos, restricciones y responsabilidades (RRR) con objetos territoriales espaciales.

---

## Librerías Python

| Librería | Para qué |
|---|---|
| `geopandas` | Vector, operaciones espaciales, I/O SHP/GPKG |
| `rasterio` / `rioxarray` | Raster — lectura, escritura, reproyección |
| `xarray` | Raster multi-dimensional (tiempo + espacio), NetCDF |
| `pykrige` | Kriging (ordinario, universal, indicador) |
| `pysal` / `esda` / `spreg` | Estadística espacial, autocorrelación I de Moran, regresión espacial |
| `shapely` | Geometría vectorial |
| `pyproj` | Proyecciones y reproyecciones |
| `folium` / `contextily` | Visualización en mapas interactivos |
| `WhiteboxTools` | Extracción de redes de drenaje (D8), HAND, análisis geomorfométrico |

**Nota:** Aunque el ecosistema Python integra estas herramientas, los documentos del notebook destacan fuertemente el uso del entorno estadístico R con librerías como `gstat`, `geoR` y `sp` para procesos complejos de Kriging e interpolación espacial, combinados con algoritmos integrados en QGIS/ArcGIS (K-means, DBSCAN).

---

## Problemas típicos y mitigaciones

- **Proyecciones mixtas:** La coexistencia histórica de múltiples orígenes cartográficos generaba áreas de traslape, discontinuidad espacial y ambigüedades en coordenadas. Solución: migrar bases de datos al Origen Nacional CTM12.
- **Estaciones dispersas y vacíos de datos:** Las estaciones de monitoreo están agrupadas heterogéneamente (alta densidad en zona andina, baja en Orinoquía/Amazonía). Solución: imputación avanzada con MissForest o interpolaciones geoestadísticas.
- **Resoluciones mixtas y nubosidad:** En ambientes andinos y amazónicos, imágenes ópticas limitadas por nubosidad deben complementarse con datos de radar (SAR/Sentinel-1).
- **Capas base desactualizadas:** Dependencia de mapas edafológicos a escala general (1:100.000) que requieren validación in situ al usarse a escalas de detalle (1:25.000).

---

## Integración con el ciclo estadístico del repo

- **EDA espacial:** Mapas temáticos, evaluación de estacionariedad e isotropía, cálculo de medias y desviaciones espaciales, I de Moran para detectar agrupamientos.
- **Descriptiva espacial:** Estadísticas por polígono (municipio, cuenca, zona de vida), densidad de Kernel, análisis de puntos calientes.
- **Inferencia espacial:** Tests de autocorrelación antes de modelar. Modelos Causales Gráficos (DAG) para planificar relaciones de confusión entre variables ambientales.
- **Predicción espacio-temporal:** ARIMA, Prophet o LSTM + Procesos Gaussianos para predecir concentraciones de contaminantes, anomalías climáticas e incertidumbres en espacio y tiempo.

---

## Actores institucionales

- **IGAC:** Máxima autoridad técnica en geodesia, cartografía básica oficial y catastro.
- **IDEAM:** Provee DHIME, mapas de ecosistemas y coberturas, SMByC.
- **MADS / SIAC:** RENARE y plataformas tecnológicas institucionales.
- **NASA / Copernicus:** Proveedores de datos abiertos satelitales (Sentinel, SMAP L4, Landsat). Iniciativas: Hub Regional de Copernicus y NASA-SERVIR.
- **DANE:** Certifica la calidad estadística de los datos y gestiona la Cuenta Satélite Ambiental.

---

## Preguntas analíticas típicas

1. ¿Dónde se agrupan de forma estadísticamente significativa los eventos ambientales críticos (hotspots)? — Resuelto con Kernel o I de Moran.
2. ¿Cómo varían localmente los factores de expansión o impacto (deforestación, accesibilidad urbana)? — Resuelto con GWR.
3. ¿Cuáles son las variables exógenas que mayor variabilidad espacial o predictiva introducen al modelo ante el cambio climático? — Resuelto con Random Forest y Análisis de Incertidumbre.

---

## Módulo sugerido en el repo

`src/estadistica_ambiental/spatial/` (pendiente de crear en fase futura).

---

## Preguntas abiertas / oportunidades

- ¿Cómo asegurar la trazabilidad de los metadatos locales e integrar conocimientos comunitarios y datos locales dispersos con datos satelitales nacionales?
- ¿De qué manera pueden estandarizarse los algoritmos de clasificación de ML (Deep Learning en nubes de puntos LiDAR) para generalizarse en biomas heterogéneos sin requerir costoso muestreo constante?
- ¿Cómo perfeccionar el cierre de brechas de incertidumbre a nivel de línea base para eventos de impacto histórico y escenarios de mitigación/adaptación con datos limitados?

---

## Referencias

- Fuentes del notebook: IGAC (Resolución 370 de 2021 — CTM12), IDEAM (DHIME, SMByC), NASA/SERVIR, Copernicus, literatura de geoestadística y SIG para Colombia.
