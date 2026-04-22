# Humedales — Gestión y Monitoreo de Humedales en Colombia

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/ab4788e2-c053-4a43-a76b-b49bf4881cf4
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Cambio climático, Recurso hídrico, Oferta hídrica, Sistemas de información ambiental, Geoespacial

---

## Resumen ejecutivo

Los humedales en Colombia, que abarcan más de 25 millones de hectáreas, son ecosistemas estratégicos y sistemas socioecológicos complejos, fundamentales para la regulación hídrica, la conservación de la biodiversidad y la resiliencia y adaptación ante el cambio climático. A pesar de su importancia, enfrentan graves amenazas por la urbanización, expansión agrícola y contaminación, lo que exige una gestión integral para mantener su integridad ecológica.

Para enfrentar estos retos, Colombia se apoya en el Sistema de Información Ambiental de Colombia (SIAC) y sus subsistemas (SIRH, SIB) para centralizar la información. El monitoreo continuo mediante recolección de datos in situ y sensores remotos permite la formulación y seguimiento de Planes de Manejo Ambiental (PMA) y garantiza el cumplimiento de compromisos internacionales como la Convención Ramsar.

---

## Objetivos

- **Monitorear la integridad ecológica:** Evaluar continuamente la estructura, composición y función de los humedales frente a presiones naturales y antrópicas.
- **Gestión y planificación:** Formular, actualizar e implementar Planes de Manejo Ambiental (PMA) basados en la delimitación, caracterización y zonificación de los ecosistemas.
- **Generación de alertas tempranas:** Predecir y detectar cambios drásticos en la calidad del agua (ej. eutrofización) y fluctuaciones hidrológicas para facilitar la toma de decisiones.
- **Integración de datos:** Fortalecer el repositorio estadístico del SINA mejorando la interoperabilidad de datos a través del SIAC.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Temperatura del agua | °C | Variable por altitud (10°C - 30°C) | Mensual / Continua | Sonda multiparamétrica in situ |
| Oxígeno Disuelto (OD) | mg/L | > 4 mg/L (sistemas sanos) | Quincenal / Mensual | Sonda multiparamétrica in situ |
| pH | Unidades de pH | 6.0 - 8.5 | Quincenal / Mensual | Sonda multiparamétrica in situ |
| Conductividad eléctrica | µS/cm | Dulce (< 1000) a Salobre/Salada | Quincenal / Mensual | Sonda multiparamétrica in situ |
| Transparencia | Metros (m) | Depende de sedimentos | Mensual | Disco de Secchi / Sensor turbidez |
| Nutrientes (Fósforo y Nitrógeno) | mg/L | Bajos (oligotrófico) a altos (eutrófico) | Estacional / Mensual | Muestreo de agua / Laboratorio |
| Nivel del agua / Hidroperiodo | cm o m | Fluctuación estacional | Continuo (cada 2h) | Leveloggers / Regla limnimétrica |

---

## Datos y fuentes

- **Datos in situ:** Levantamiento de información fisicoquímica y biológica primaria (fitoplancton, zooplancton, inventarios de peces, aves y macrófitas) mediante transectos, redes y estaciones de monitoreo.
- **Datos geoespaciales:** Imágenes de satélite multiespectrales y de radar (Sentinel-1, Sentinel-2, Landsat) para evaluar el espejo de agua y coberturas.
- **Bases de datos oficiales:** Subsistemas del SIAC: SIRH, SiB Colombia y catálogos del IGAC e IDEAM.

---

## Indicadores y métricas oficiales

- **Hidrológicos:** Balance hídrico, extensión del espejo de agua e hidroperiodo.
- **Fisicoquímicos:** Índice de estado trófico (basado en Clorofila-a, fósforo y nitrógeno), DBO y DQO.
- **Bióticos:** Diversidad e índices de riqueza de macroinvertebrados, porcentaje de cobertura de vegetación macrófita, abundancia de aves y proporción de especies exóticas/invasoras.
- **Sociales/Presiones:** Número de impactos generados por el ser humano (vertimientos, urbanización, deforestación).

---

## Normativa aplicable (Colombia)

- **Ley 357 de 1997:** Ratificación de la Convención de Ramsar relativa a los humedales de importancia internacional.
- **Política Nacional para Humedales Interiores de Colombia (2002):** Establece lineamientos para la conservación, uso sostenible y rehabilitación.
- **Resolución 157 de 2004:** Reglamenta el uso sostenible y ordena la formulación de planes de manejo ambiental.
- **Resolución 196 de 2006:** Adopta la guía técnica para la formulación de planes de manejo para humedales, incluyendo criterios de delimitación.

---

## Preguntas analíticas típicas

1. ¿Cuál es la tendencia histórica del área del espejo de agua y los pulsos de inundación ante fenómenos de variabilidad climática?
2. ¿Cuál es el estado trófico actual del ecosistema y cuál es su carga crítica de nutrientes antes de sufrir eutrofización irreversible?
3. ¿Cómo impactan las presiones urbanísticas y agrícolas en la integridad ecológica y la calidad del agua del humedal?
4. ¿Qué especies bioindicadoras reflejan mejor los cambios en las condiciones hídricas y fisicoquímicas?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Estadísticas de series de tiempo temporales de caudales, niveles e índices biológicos para establecer líneas base y tendencias multianuales.

**Predictiva:**
- Modelo de Vollenweider: estimación de concentración de fósforo total y predicción de respuestas tróficas (cargas críticas de nutrientes).
- MICMAC: análisis estructural para priorizar variables críticas y modelar escenarios futuros de gestión.

**Espacial:**
- Machine Learning (Random Forest, Redes Neuronales) en Google Earth Engine (GEE) para clasificar coberturas y calcular índices radiométricos (NDWI, MNDWI) para extracción de cuerpos de agua.
- Análisis multitemporal del espejo de agua con Sentinel-1/2 y Landsat.

---

## Actores institucionales

- **MADS:** Órgano rector de la política y lineamientos nacionales.
- **Institutos de Investigación (SINA):** IDEAM, Instituto Humboldt, INVEMAR, SINCHI, IIAP — proveen bases técnicas, monitoreo y generación de indicadores.
- **CARs y Parques Nacionales Naturales (PNN):** Responsables de implementar la gestión local y los PMA.
- **Comunidades y ONGs:** Actores vitales en esquemas de gobernanza territorial y ciencia participativa.

---

## Riesgos y sesgos en los datos

- **Sesgos geográficos:** La mayor parte del monitoreo histórico se concentra en la cuenca Magdalena-Cauca o la región Andina, dejando grandes vacíos en Amazonia, Orinoquia y el Pacífico.
- **Fragmentación tecnológica:** Limitada interoperabilidad de datos y arquitecturas dispares entre autoridades ambientales y los más de 50 sistemas que componen el SIAC.
- **Nubosidad en sensores remotos:** La alta nubosidad en los trópicos interfiere con sensores ópticos, obligando al uso de datos SAR y procesamiento avanzado para evitar subestimaciones del espejo de agua.

---

## Glosario mínimo

- **Humedal:** Geoforma temporal o permanentemente inundada con suelos hídricos y biota adaptada.
- **Sitio Ramsar:** Humedal designado de importancia internacional bajo el tratado de Ramsar.
- **SIAC:** Sistema de Información Ambiental de Colombia.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **PMA:** Plan de Manejo Ambiental, documento rector para la gestión del ecosistema.
- **Hidroperiodo:** Fluctuación y patrón temporal del nivel del agua.
- **Estado trófico:** Nivel de enriquecimiento por nutrientes de un cuerpo de agua.
- **Integridad ecológica:** Capacidad del humedal para mantener su composición, estructura y procesos ecológicos.
- **Resiliencia:** Capacidad de un humedal para absorber perturbaciones sin perder su estructura y funciones vitales.
- **Macrófitas:** Vegetación acuática fundamental para la estructura del ecosistema.
- **Vollenweider:** Modelo de balance de masas utilizado para modelar eutrofización.
- **NDWI:** Índice de Agua de Diferencia Normalizada usado en teledetección.
- **MICMAC:** Software de análisis estructural para evaluación prospectiva.
- **Eutrofización:** Exceso de nutrientes (P y N) que deteriora la calidad del agua.
- **Bioindicador:** Especie biológica utilizada para evaluar la salud del ecosistema.

---

## Preguntas abiertas / oportunidades

- ¿Cómo lograr una integración e interoperabilidad automatizada y en tiempo real de todos los subsistemas del SIAC (SIRH, SNIF, SIB) a nivel nacional y regional?
- ¿De qué manera pueden estandarizarse y financiarse de manera continua los monitoreos bióticos en regiones subrepresentadas (Amazonia, Pacífico)?
- ¿Cómo escalar la integración de ciencia ciudadana y monitoreo participativo para fortalecer el repositorio de estadística del SINA desde los territorios?

---

## Referencias

- Fuentes del notebook: Política Nacional para Humedales 2002, Convención Ramsar, MADS, IDEAM, Instituto Humboldt, INVEMAR.
