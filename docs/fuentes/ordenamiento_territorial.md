# Ordenamiento Territorial y Gestión Ambiental Territorial en Colombia

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/39ceb3fe-99dc-4e17-ba73-87ec88ef3e25
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Gestión de riesgo, POMCA, Rondas hídricas, Cambio climático, Geoespacial, Áreas protegidas

---

## Resumen ejecutivo

El ordenamiento ambiental y territorial en Colombia es un proceso de planificación que busca organizar el uso del suelo de manera armónica con la conservación de la biodiversidad, la gestión del riesgo y el desarrollo socioeconómico. Regulado principalmente por la Ley 388 de 1997 y el Decreto Único Reglamentario 1076 de 2015, este marco jerarquiza las determinantes ambientales (áreas protegidas, rondas hídricas, gestión del riesgo y cambio climático) como "invariantes estructurales" de superior jerarquía que los municipios deben integrar obligatoriamente en sus Planes de Ordenamiento Territorial (POT).

Para superar la desactualización y desarticulación técnica en los territorios, el país avanza en la estandarización de la información geográfica mediante la adopción de modelos como el LADM_COL-POT. Este enfoque, articulado con el Sistema de Administración del Territorio (SAT), promueve la interoperabilidad de datos geoespaciales, permitiendo formular políticas públicas diferenciadas y consolidar modelos de ocupación urbana y rural que garanticen la resiliencia climática y el bienestar poblacional.

---

## Objetivos

- Armonizar la planificación económica y social con la dimensión territorial, asegurando el uso equitativo y racional del suelo.
- Proteger y conservar la Estructura Ecológica Principal (EEP), los ecosistemas estratégicos (páramos, humedales, manglares) y la biodiversidad, garantizando la función ecológica de la propiedad.
- Incorporar la gestión del riesgo de desastres y la adaptación al cambio climático como condicionantes para la ocupación del territorio.
- Garantizar la interoperabilidad de la información espacial mediante la implementación del estándar LADM_COL.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Precipitación y Temperatura | mm, °C | Varía por zona de vida / isoyetas e isotermas | Diaria / Mensual | IDEAM, Redes CAR |
| Calidad del Agua (OD, DBO, DQO, SST, Coliformes) | mg/l, % sat, NMP/1000, pH | DBO: > 0; pH: 0-14 | Periódica (campañas) | IDEAM, CAR, EPM |
| Cobertura y Uso del Suelo | Hectáreas, % | Depende del municipio | Anual / Multitemporal | IGAC, IDEAM (Corine Land Cover) |
| Caudal (Oferta Hídrica) | L/s o m³/s | Varía por subcuenca | Diaria | IDEAM (estaciones hidrométricas) |
| Emisiones / Cargas Contaminantes | Toneladas/año | > 0 (según factor de emisión) | Anual / Proyecciones | Inventarios GEI, DANE, CAR |
| Pendiente del Terreno | Grados (°) | 0° a > 40° | Estática (actualización MDE) | IGAC, ASTER/SRTM |

---

## Datos y fuentes

- **Datos espaciales (Cartografía Básica y Temática):** MDE, imágenes de satélite, ortofotomosaicos, capas vectoriales (Shapefiles, GDB, PostGIS).
- **Bases de datos catastrales y prediales:** Registros alfanuméricos, Unidades Agrícolas Familiares (UAF) y tenencia de la tierra del IGAC y Catastro Multipropósito.
- **Fuentes institucionales secundarias:** Anuarios estadísticos, Encuesta Nacional de Calidad de Vida (ENCV), censos demográficos y agrícolas, plataformas como TerriData o Colombia en Mapas.
- **Datos climáticos y de riesgo:** Series hidroclimáticas, estudios de amenaza, vulnerabilidad y riesgo (AVR) del SGC, UNGRD e IDEAM.

---

## Indicadores y métricas oficiales

- **IACAL:** Índice de Alteración Potencial a la Calidad del Agua; estima la afectación hídrica por presiones socioeconómicas.
- **TCCN:** Indicador de Tasa de Cambio de Coberturas Naturales; mide la pérdida o transformación de coberturas naturales.
- **IDI / MDM:** Índice de Desempeño Integral y Medición del Desempeño Municipal; cuantifican la gestión de las entidades territoriales y resultados de desarrollo.
- **IAR:** Índice de Afectación del Riesgo; mide el riesgo municipal ante inundaciones, flujos torrenciales y deslizamientos.
- **IPM:** Índice de Pobreza Multidimensional; evalúa la capacidad adquisitiva y privaciones en los hogares.

---

## Normativa aplicable (Colombia)

- **Ley 99 de 1993:** Crea el SINA y define el ordenamiento ambiental del territorio.
- **Ley 388 de 1997 (Ley de Desarrollo Territorial):** Establece los POT y consagra la función ecológica de la propiedad.
- **Decreto 1076 de 2015:** Decreto Único Reglamentario del Sector Ambiente. Fija determinantes ambientales y manejo de recursos naturales (rondas hídricas, POMCA).
- **Ley 1523 de 2012:** Política Nacional de Gestión del Riesgo de Desastres, obliga a incluir el riesgo como condicionante territorial.
- **Resolución 658 de 2022 (IGAC) y 0058 de 2025 (Minvivienda):** Adoptan las especificaciones cartográficas y el modelo de datos extendido LADM_COL-POT.

---

## Preguntas analíticas típicas

1. ¿Cuáles son las limitantes y condicionamientos ambientales que restringen el uso del suelo (ecosistemas estratégicos, zonas de alta pendiente)?
2. ¿Qué tipo de coberturas naturales predominan en la cuenca y cuál ha sido su tasa de cambio por la expansión de la frontera agrícola?
3. ¿Cómo inciden los escenarios de variabilidad y cambio climático en la vulnerabilidad de los sistemas estructurantes y asentamientos poblacionales?
4. ¿Las actividades sociales, culturales o económicas actuales están detonando o incrementando las amenazas naturales en el territorio?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Matrices DOFA, árboles de decisión, identificación de conflictos de uso de suelo e inventarios de GEI.

**Predictiva:**
- Modelación hidrológica, evaluación ex ante de impacto de políticas públicas, proyecciones poblacionales, escenarios tendenciales y prospectivos, estadísticas bayesianas.

**Espacial:**
- Econometría espacial: modelos SARAR con matrices de correlación espacial.
- Álgebra de mapas SIG, procesos de topología y validación geográfica orientados en el estándar LADM_COL.

---

## Actores institucionales

- **Nivel nacional:** MADS, MVCT (Ministerio de Vivienda, Ciudad y Territorio), DNP (Departamento Nacional de Planeación).
- **Generadores de información técnica:** IGAC, IDEAM, SGC, DANE, Institutos de investigación (Humboldt, Sinchi, Invemar).
- **Nivel regional/local:** CARs (Cornare, Corpoguavio, Cardique), Alcaldías Municipales, Consejos Territoriales de Planeación y Consejos de Cuenca.

---

## Riesgos y sesgos en los datos

- **Desactualización de instrumentos:** A 2023, cerca del 80-87% de los municipios tenían la vigencia de largo plazo de su POT vencida, basándose en diagnósticos obsoletos.
- **Brecha de capacidades y tecnología:** Muchos entes territoriales carecen de recursos para generar cartografía a escala adecuada (1:10.000 para riesgo) o procesar topología compleja.
- **Fragmentación institucional:** La información del territorio reposa en diversas fuentes (catastral, registral, ambiental) con estándares muchas veces no homologados.
- **Ambigüedad del modelo normativo:** La aplicación real de la ley difiere drásticamente en el campo (falta de control urbano, ocupación informal), por lo que un POT estructurado en SIG puede no reflejar las transformaciones subyacentes.

---

## Glosario mínimo

- **Caudal ambiental:** Volumen de agua necesario para mantener el funcionamiento y resiliencia de los ecosistemas acuáticos.
- **Corine Land Cover:** Metodología estandarizada para la clasificación, cartografía y análisis de coberturas y uso de la tierra.
- **Determinantes ambientales:** Normas de superior jerarquía que regulan el uso espacial y la protección de recursos ambientales dentro del ordenamiento territorial.
- **Estructura Ecológica Principal (EEP):** Conjunto de elementos bióticos y abióticos que sostienen los procesos ecológicos esenciales del territorio.
- **LADM_COL:** Perfil colombiano del modelo de administración de tierras (Land Administration Domain Model), que estandariza los objetos territoriales legales.
- **Ordenamiento territorial:** Política de Estado y proceso planificador para organizar el uso y ocupación del espacio según estrategias socioeconómicas y ecológicas.
- **POT:** Plan de Ordenamiento Territorial; instrumento básico de planificación a largo plazo de municipios (> 100.000 hab.) que regula usos del suelo.
- **POMCA:** Plan de Ordenación y Manejo de Cuencas Hidrográficas; orienta el uso coordinado del suelo, flora y agua en una cuenca.
- **Ronda hídrica:** Área de protección ecológica colindante a un cuerpo de agua, sujeta a acotamiento.
- **SINA:** Sistema Nacional Ambiental.
- **Subregionalización funcional:** Identificación de interdependencias entre municipios más allá de los límites políticos para intervenciones de mayor escala.
- **UAF:** Unidad Agrícola Familiar — medida estándar de terreno agrario para retribución adecuada de una familia.
- **Zonificación ambiental:** Subdivisión del territorio según aptitud, vocación y limitantes de uso frente a la conservación o producción.

---

## Preguntas abiertas / oportunidades

- ¿Cómo garantizar la financiación constante de los municipios pequeños para mantener actualizado su componente cartográfico y sus estudios básicos de gestión del riesgo?
- ¿Cómo medir si la adopción del POT frena verdaderamente la degradación ecosistémica más allá de simplemente contabilizar adopciones de documentos?
- ¿Qué mecanismos articulan los tiempos de actualización de los POMCA con las vigencias de los POT de forma sincrónica para que no se desfase la normatividad ambiental?

---

## Referencias

- Fuentes del notebook: Ley 388 de 1997, Decreto 1076 de 2015, IGAC (Resolución 658 de 2022), LADM_COL-POT, MADS, MVCT, DNP.
