# Gestión del Riesgo de Desastres (GRD) en Colombia

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/62fe34e3-04b0-40ea-bd80-46a79ed82961
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Cambio climático, Oferta hídrica, Ordenamiento territorial, POMCA, Calidad del aire, Geoespacial

---

## Resumen ejecutivo

La Gestión del Riesgo de Desastres (GRD) en Colombia es un proceso social esencial orientado a la formulación, ejecución, seguimiento y evaluación de políticas y acciones permanentes para el conocimiento, la reducción del riesgo y el manejo de desastres. Este marco busca contribuir a la seguridad, el bienestar y la calidad de vida de las personas, garantizando el desarrollo sostenible y la seguridad territorial del país.

Técnicamente, el enfoque integra el uso de inteligencia geoespacial, modelación estadística y probabilística, e inventarios históricos para caracterizar amenazas como movimientos en masa, inundaciones, avenidas torrenciales e incendios forestales. Estos análisis son de obligatorio cumplimiento para la planificación del desarrollo y se materializan como determinantes ambientales en los POT y los POMCA.

---

## Objetivos

- **Conocimiento del riesgo:** Identificar, evaluar y monitorear escenarios de riesgo, amenazas, vulnerabilidades y elementos expuestos mediante estudios técnicos.
- **Reducción del riesgo:** Diseñar e implementar medidas de intervención prospectiva (evitar nuevos riesgos) y correctiva (mitigar riesgos existentes), además de protección financiera.
- **Manejo de desastres:** Preparar la respuesta a emergencias (sistemas de alerta, capacitación), ejecutar la atención integral y planificar la recuperación, rehabilitación y reconstrucción.
- **Planificación territorial:** Incorporar la GRD como determinante ambiental ineludible en el ordenamiento territorial municipal (POT) y de cuencas (POMCA).

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Precipitación | mm | < 1000 a > 7000 mm (media anual) | Diaria / Anual | IDEAM |
| Temperatura | °C | < 6°C a > 24°C (media anual) | Diaria / Anual | IDEAM |
| Pendiente | % | 3-7% (baja) a > 75% (muy alta) | Estática / Actualizada | IGAC / NASA DEM |
| Aceleración Máxima en Roca (PGA) | %g | < 3.9 (Ninguna) a > 124 (Muy alta) | Probabilística (Tr = 475 años) | SGC |
| Profundidad del agua | m | < 0.4 m (Baja) a > 0.8 m (Alta) | Episódica / Modelada | IDEAM / HEC-RAS |
| Velocidad del viento | m/s | < 1.5 a > 4 m/s (media multianual) | Continua / Anual | IDEAM |

---

## Datos y fuentes

- **Cartográficos y geoespaciales:** DEM de la NASA (ALOS PALSAR) e IGAC, coberturas Corine Land Cover e imágenes satelitales (Sentinel, Landsat).
- **Registros históricos:** DesInventar y consolidados de la UNGRD, esenciales para calcular frecuencia y validar modelos.
- **Hidrometeorológicos y climáticos:** Estaciones de monitoreo y mapas de temperatura y precipitación del IDEAM.
- **Geológicos y geotécnicos:** Atlas Geológico de Colombia, mapas de amenaza sísmica y zonificación de movimientos en masa del SGC.
- **Socioeconómicos y de infraestructura:** Censos del DANE, bases del SISBEN e información catastral del IGAC para el análisis de vulnerabilidad social y física.

---

## Indicadores y métricas oficiales

- **IVET (Índice de Vulnerabilidad a Eventos Torrenciales):** Para susceptibilidad y amenaza de avenidas torrenciales.
- **SPI (Índice de Precipitación Estandarizado):** Métrica principal para evaluar sequías y disponibilidad hídrica.
- **Niveles de Amenaza/Vulnerabilidad/Riesgo:** Escalas cualitativas y cuantitativas — Muy Baja, Baja, Media, Alta y Muy Alta.
- **IVH (Índice de Vulnerabilidad Hídrica por desabastecimiento):** Indicador del IDEAM para medir presiones sobre el recurso hídrico.

---

## Normativa aplicable (Colombia)

- **Ley 1523 de 2012:** Adopta la Política Nacional de Gestión del Riesgo de Desastres y crea el SNGRD.
- **Decreto 1807 de 2014 (compilado en Decreto 1077 de 2015):** Reglamenta la incorporación técnica de la gestión del riesgo en los POT mediante estudios básicos y detallados.
- **Decreto 2157 de 2017:** Establece directrices para elaborar los Planes de Gestión del Riesgo de Desastres de Entidades Públicas y Privadas (PGRDEPP).
- **Decreto 1640 de 2012:** Reglamenta la inclusión del riesgo como determinante ambiental en los POMCA.
- **Ley 388 de 1997:** Ley de Desarrollo Territorial, ordena determinar zonas no urbanizables por presentar riesgos.

---

## Preguntas analíticas típicas

1. ¿Cuál es la probabilidad de que un evento físico peligroso se materialice con severidad suficiente para causar pérdidas o daños en un área determinada?
2. ¿Cuál es el grado de susceptibilidad, fragilidad física y socioeconómica de los elementos expuestos ante las amenazas identificadas?
3. ¿Qué restricciones de uso del suelo o medidas de mitigación estructural se deben aplicar en zonas de amenaza alta para prevenir desastres?
4. ¿Cómo incide la variabilidad climática y los escenarios de cambio climático en la frecuencia e intensidad de los factores detonantes a futuro?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Técnicas estadísticas bivariadas para susceptibilidad a movimientos en masa: Pesos de Evidencia (WoE) y análisis discriminante.

**Predictiva:**
- Análisis de estabilidad de laderas (taludes).
- Modelos hidrodinámicos (HEC-RAS) para flujos y profundidades de inundación.
- Machine Learning: Redes Neuronales Recurrentes (LSTM) para predicción de eventos.
- Métodos de evaluación probabilística de amenaza sísmica.

**Espacial:**
- Procesamiento Digital de Imágenes (PDI), álgebra de mapas y SIG.
- Teledetección mediante InSAR/DInSAR para medición de deformación del terreno.
- Índices morfométricos como el Índice de Melton.

---

## Actores institucionales

- **UNGRD:** Unidad Nacional para la Gestión del Riesgo de Desastres, rectora de la coordinación y normatividad interna del SNGRD.
- **IDEAM:** Provee metodologías, datos hidro-climatológicos y monitoreo ambiental.
- **SGC:** Servicio Geológico Colombiano, encargado de información geo-científica, movimientos en masa, amenaza sísmica y volcánica.
- **IGAC:** Instituto Geográfico Agustín Codazzi, ente rector de la cartografía base y datos catastrales.
- **MADS y MVCT:** Ministerio de Ambiente y de Vivienda, para reglamentación y lineamientos de ordenamiento territorial.
- **CARs:** Orientan la dimensión ambiental y la gestión del riesgo a nivel de cuencas (POMCA).

---

## Riesgos y sesgos en los datos

- **Sesgos en inventarios históricos:** DesInventar puede ser incompleta o subjetiva, afectando la certidumbre matemática en modelos de susceptibilidad y amenaza.
- **Limitaciones de escala:** Usar mapas regionales (1:100.000) directamente en el planeamiento urbano sin reducción de escala al detalle (1:2.000 o 1:5.000) puede inducir graves errores.
- **Incertidumbre en vulnerabilidad:** Carencia de información catastral detallada a nivel de parcela para un cálculo riguroso de posibles pérdidas económicas.

---

## Glosario mínimo

- **Amenaza:** Peligro latente de que un evento físico se presente con severidad suficiente para causar daños o pérdidas.
- **Avenida torrencial:** Creciente súbita de agua con alto contenido de materiales de arrastre y alto potencial destructivo.
- **Exposición:** Presencia de personas, infraestructura y medios de subsistencia en el área de afectación de una amenaza.
- **Factores condicionantes:** Características intrínsecas del terreno (geología, relieve) que predisponen a la materialización de un evento.
- **Factores detonantes:** Eventos externos (lluvia, sismo) que desencadenan el evento amenazante.
- **Gestión del riesgo:** Proceso social para conocer, reducir y manejar el riesgo, buscando la protección de personas y el desarrollo sostenible.
- **Movimiento en masa:** Desplazamiento de suelo o roca a lo largo de una ladera (deslizamientos, flujos, caídas).
- **POMCA:** Plan de Ordenación y Manejo de Cuencas Hidrográficas.
- **Resiliencia:** Capacidad de un sistema expuesto a una amenaza para resistir, absorber, adaptarse y recuperarse eficazmente.
- **Riesgo de desastres:** Daños o pérdidas potenciales derivados de la combinación entre amenaza y vulnerabilidad de los elementos expuestos.
- **Susceptibilidad:** Propensión de una zona a presentar eventos amenazantes en función de sus factores condicionantes (sin detonantes).
- **Vulnerabilidad:** Fragilidad física, social, económica o institucional que predispone a sufrir efectos adversos ante un evento físico peligroso.

---

## Preguntas abiertas / oportunidades

- ¿Cómo consolidar y mantener un catastro urbano-rural detallado que alimente directamente y en tiempo real las curvas de fragilidad para los modelos de riesgo?
- ¿De qué manera pueden las metodologías integrar dinámicamente los escenarios proyectados de variabilidad climática interanual y cambio climático a escala local?
- ¿Cómo avanzar desde el análisis unitario de amenazas hacia modelos de "riesgo en cascada" combinando fenómenos hidrológicos y movimientos en masa de gran escala?

---

## Referencias

- Fuentes del notebook: Ley 1523 de 2012, Decreto 1807 de 2014, UNGRD, IDEAM, SGC, IGAC, DesInventar.
