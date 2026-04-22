# POMCA — Plan de Ordenación y Manejo de Cuencas Hidrográficas

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/b31e1fbb-9b42-456a-ace9-2a61e12c8d05
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, Recurso hídrico, Rondas hídricas, Gestión de riesgo, Ordenamiento territorial, Cambio climático, Geoespacial

---

## Resumen ejecutivo

El Plan de Ordenación y Manejo de Cuencas Hidrográficas (POMCA) es el instrumento rector de planificación ambiental territorial en Colombia, diseñado para articular el uso coordinado y sostenible del suelo, el agua, la flora y la fauna. Su finalidad central es mantener el equilibrio entre el aprovechamiento socioeconómico del territorio y la conservación de la estructura físico-biótica de la cuenca, priorizando siempre la gestión integral del recurso hídrico. Se constituye jurídicamente como norma de superior jerarquía y determinante ambiental estricta para la elaboración de los POT municipales y departamentales.

El POMCA se concibe como un proceso continuo y sistemático desarrollado a lo largo de un ciclo de vida con seis fases clave: aprestamiento, diagnóstico, prospectiva y zonificación ambiental, formulación, ejecución, y seguimiento y evaluación. A través de modelos prospectivos y de simulación hidrológica, el plan establece escenarios a mediano y largo plazo para enfrentar presiones demográficas, variabilidad climática y riesgos socio-naturales.

---

## Objetivos

- Planificar el uso coordinado de los recursos naturales (suelo, agua, flora, fauna) para asegurar un desarrollo sostenible de la cuenca.
- Definir la zonificación ambiental categorizando áreas de conservación, protección, recuperación y producción, sirviendo como determinante ambiental frente al ordenamiento municipal.
- Integrar la gestión del riesgo de desastres para reducir la vulnerabilidad frente a eventos extremos y garantizar una ocupación territorial segura.
- Fomentar la gobernanza del agua a través de espacios participativos como el Consejo de Cuenca, articulando instituciones, sectores económicos y sociedad civil.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Precipitación | mm | Series históricas diarias, mensuales, anuales | Diario / Mensual | IDEAM (DHIME) |
| Temperatura | °C | Máxima, mínima y media | Diario / Mensual | IDEAM (DHIME) |
| Caudal medio diario | m³/s o L/s | Régimen hidrológico, series multianuales | Diario | IDEAM, Redes CAR, Empresas Públicas |
| Calidad del Agua (OD, DBO, DQO, SST, Nutrientes) | mg/L, % sat. | Variable según grado de contaminación | Mensual / Ocasional | Red de Monitoreo de Calidad de CARs e IDEAM |
| Coberturas y Usos de la Tierra | Ha / % | Clasificación Corine Land Cover (niveles 1 a 3) | Multianual | IGAC, CARs, Imágenes satelitales |

---

## Datos y fuentes

- **Series temporales hidrológicas y climatológicas:** Estructuradas, del IDEAM mediante DHIME y SIRH.
- **Información georreferenciada:** Formatos Shapefile o geodatabase (escala 1:25.000 a 1:100.000), modelos digitales de terreno (DTM) e imágenes satelitales.
- **Datos socioeconómicos:** Censos de población, proyecciones socioeconómicas e inventarios de usuarios del agua.
- **Fuentes oficiales:** IGAC para cartografía base y suelos; SIAC (SIB, SNIF, SMByC) para ecosistemas y biodiversidad.

---

## Indicadores y métricas oficiales

- **IUA (Índice de Uso del Agua):** Mide la presión de la demanda hídrica frente a la oferta superficial disponible (%).
- **IRH (Índice de Retención y Regulación Hídrica):** Capacidad física de la cuenca para mantener regímenes de caudal base.
- **IVH (Índice de Vulnerabilidad por Desabastecimiento Hídrico):** Relaciona el IUA y el IRH para determinar la fragilidad del suministro en sequías.
- **ICA (Índice de Calidad del Agua):** Califica el estado del recurso para diferentes usos mediante parámetros fisicoquímicos ponderados.
- **IACAL (Índice de Alteración Potencial de la Calidad del Agua):** Evalúa la presión por vertimientos en relación con la oferta hídrica.
- **IARC (Índice de Agua no Retornada a la Cuenca):** Vincula la huella hídrica azul con la disponibilidad del recurso.

---

## Normativa aplicable (Colombia)

- **Decreto Único Reglamentario 1076 de 2015:** Compila normativas del sector ambiental; establece reglas del ordenamiento del recurso hídrico, delimitación y financiación, y el peso de los POMCA como normas de superior jerarquía.
- **Ley 99 de 1993:** Fundamenta el Sistema Nacional Ambiental (SINA) y los mandatos de ordenación.
- **Decreto 1640 de 2012 (compilado en el 1076):** Reglamenta todos los instrumentos técnicos para la planificación, ordenación y manejo de cuencas hidrográficas y acuíferos.
- **Resolución 509 de 2013:** Establece la conformación e integración ciudadana en los Consejos de Cuenca.

---

## Preguntas analíticas típicas

1. ¿Cuál es el balance actual entre la oferta hídrica disponible y la demanda hídrica multisectorial en la cuenca, considerando años hidrológicos secos y medios?
2. ¿Dónde se concentran los conflictos territoriales críticos originados por el uso inadecuado de las tierras frente a su vocación edafológica?
3. ¿Qué tramos de la red hídrica muestran un riesgo inminente de contaminación severa y alteración potencial según el IACAL?
4. ¿Qué ecosistemas e infraestructura vital presentan alta exposición y vulnerabilidad ante eventos hidrometeorológicos extremos?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Análisis geoespaciales con SIG: álgebra de mapas, superposición y matrices de reclasificación para la estructuración de la zonificación ambiental del territorio.

**Predictiva:**
- Modelo SWAT (Soil and Water Assessment Tool): herramienta semi-distribuida que simula a nivel de HRUs (Unidades de Respuesta Hidrológica) los impactos a largo plazo de las prácticas de manejo de suelo y el cambio climático sobre el agua y la escorrentía.

**Espacial:**
- Downscaling estadístico: aplicado en estudios prospectivos para regionalizar variables de modelos climáticos globales a nivel local bajo trayectorias de concentración (RCP 4.5, RCP 8.5).

---

## Actores institucionales

- **MADS:** Dicta la política, marcos regulatorios y directrices nacionales.
- **CARs y Corporaciones de Desarrollo Sostenible:** Responsables técnicas, administrativas y de financiación de la elaboración, ejecución y seguimiento del POMCA. En cuencas compartidas, actúan mediante Comisiones Conjuntas.
- **Consejos de Cuenca:** Instancias representativas con alcaldías, comunidades indígenas/afrocolombianas, organizaciones campesinas, gremios productivos, prestadores de acueducto, universidades y ONG.
- **Institutos de Apoyo Técnico del SINA (IDEAM, IGAC, INVEMAR, SGC):** Proveen cartografía oficial, análisis climatológicos, reportes de calidad ambiental y mapas base.

---

## Riesgos y sesgos en los datos

- **Brechas en el Monitoreo Instrumental:** Grandes porciones geográficas (Orinoquía, Amazonía, Pacífico) carecen de suficientes estaciones meteorológicas continuas, introduciendo errores e incertidumbre al obligar a estimar datos mediante polígonos de Thiessen, IDW o regionalización.
- **Falta de series temporales completas:** Los registros diarios frecuentemente presentan "baches" que deben ser reconstruidos con métodos estadísticos tipo ARIMA, afectando el rigor en los percentiles extremos de sequía o inundación.
- **Ambigüedad en datos de suelos:** La dependencia de mapas edafológicos a escala general (1:100.000) genera extrapolaciones inciertas cuando las CARs requieren precisar determinantes operativas a escala 1:25.000.

---

## Glosario mínimo

- **POMCA:** Plan de Ordenación y Manejo de Cuencas Hidrográficas, instrumento principal de jerarquía ambiental territorial.
- **Cuenca hidrográfica:** Unidad fisiográfica drenada por un sistema interconectado hacia un punto de salida principal, que actúa como un sistema socio-ecológico.
- **Caudal ambiental:** Volumen de agua necesario (calidad y cantidad) para el sostenimiento vital de los ecosistemas acuáticos.
- **Determinantes ambientales:** Directrices restrictivas o vinculantes del POMCA obligatorias al estructurar un POT.
- **Oferta Hídrica Disponible (OHDS):** Fracción del agua escurrida que se puede extraer, habiendo garantizado el caudal ambiental.
- **SWAT:** Modelo hidrológico de base física para pronosticar los impactos del uso del suelo en cuerpos de agua a nivel de cuenca.
- **Consejo de Cuenca:** Plataforma de gobernanza que ejerce funciones consultivas en la formulación de los POMCA.
- **IUA, IRH, IACAL:** Índices de uso del agua, retención hídrica y alteración potencial de la calidad del agua.
- **DHIME:** Sistema de Gestión de Datos Hidrológicos y Meteorológicos del IDEAM.
- **Escorrentía:** Volumen de agua de la lluvia que fluye superficialmente y no es infiltrada, interceptada o evaporada.

---

## Preguntas abiertas / oportunidades

- **Integración efectiva de acuíferos:** Los modelos predominantes (como el IUA) se centran en aguas superficiales. Persiste un vacío analítico sobre la dinámica y oferta de extracciones en la red de aguas subterráneas unificada a la cuenca.
- **Financiación permanente:** Falta cristalizar estrategias para mantener la infraestructura de monitoreo continuo del POMCA a lo largo de su proyección de diez años.
- **Medición directa vs. módulos teóricos en IACAL:** Muchos vertimientos son estimados mediante constantes poblacionales (cargas indirectas). Se requiere mejora monumental en el muestreo real in situ de vertimientos difusos y puntuales agrícolas.

---

## Referencias

- Fuentes del notebook: Decreto 1640 de 2012, Decreto 1076 de 2015, IDEAM (DHIME, SIRH), IGAC, SWAT, literatura de modelación hidrológica en Colombia.
