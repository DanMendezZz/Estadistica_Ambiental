# Sistemas de Información Ambiental — SIAC (Sistema de Información Ambiental de Colombia)

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/ec194313-e870-4121-b75d-8cc2e0a716a6
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Todas las líneas temáticas — el SIAC es la plataforma de datos transversal del SINA

---

## Resumen ejecutivo

El Sistema de Información Ambiental de Colombia (SIAC) es el conjunto integrado de actores, políticas, procesos y tecnologías responsables de gestionar la información ambiental a nivel nacional. Su estructura opera mediante una arquitectura federada compuesta por múltiples subsistemas temáticos (SIRH, SIB, SMByC, RUA) encargados de procesar datos especializados que permiten monitorear los ecosistemas y los impactos antrópicos.

Este sistema estratégico tiene como propósito fundamental facilitar la generación de conocimiento, apoyar la toma de decisiones basada en evidencias, impulsar la educación y promover la participación social para el desarrollo sostenible del país. A pesar de los importantes avances en la consolidación de portales y la producción de datos oficiales, el SIAC enfrenta el reto de superar la fragmentación tecnológica, mejorar la interoperabilidad entre sus subsistemas y democratizar el acceso a la información para reducir las brechas en los territorios.

---

## Objetivos

- Generar y divulgar información oficial sobre la superficie de bosque natural, deforestación y emitir alertas tempranas.
- Cuantificar reservas de carbono y las emisiones/absorciones de GEI asociadas a la degradación forestal.
- Apoyar la formulación de políticas y regulaciones mediante la recolección de datos sobre la presión ejercida sobre los recursos naturales (agua, aire, suelo).
- Democratizar la información ambiental de forma transparente, libre y oportuna, empoderando a la ciudadanía y a los actores locales en la gestión de riesgos.
- Fortalecer la capacidad institucional y la interoperabilidad de las autoridades ambientales y los subsistemas del SINA.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Deforestación / Cambio de bosque | Hectáreas (ha) / km² | N/A (varía por núcleo/región) | Trimestral (Alertas) / Anual (Reporte) | SMByC (IDEAM) |
| Carga contaminante vertida (DBO y SST) | Millones de Toneladas | DBO: ~1.39 M ton / SST: ~1.35 M ton (2020) | Anual | SIRH (IDEAM) |
| Metales pesados en biosólidos (Cadmio, Plomo) | mg/kg | Cadmio: 39-85 / Plomo: 300-840 | Semestral | Productores PTAR / Decreto 1287 |
| Emisiones GEI y Transferencia Contaminantes | Toneladas / kg | Según umbrales de normatividad | Anual | RETC / RUA (Establecimientos) |
| Coberturas de la tierra | Hectáreas (ha) | N/A | Anual | IGAC / IDEAM |

---

## Datos y fuentes

- **Datos geoespaciales / Raster:** Imágenes satelitales (Landsat, Planet) para monitoreo de coberturas y deforestación, cartografía base y modelos digitales de elevación.
- **Datos alfanuméricos y estructurados:** Formularios tabulares en lenguajes estándar (JSON, UTF-8) provenientes de reportes de industrias y prestadores de servicios.
- **Fuentes de información:** Institutos de Investigación (IDEAM, INVEMAR, Humboldt, Sinchi, IIAP), CARs, ANLA, PNNC y el sector productivo.

---

## Indicadores y métricas oficiales

- **Tasa de deforestación nacional y regional:** Con alertas tempranas (ATD) del SMByC.
- **Indicadores de la línea base ambiental regional e ICAU:** Índice de Calidad Ambiental Urbano.
- **Indicadores marinos y costeros:** Extensión de manglar, distribución de especies amenazadas, calidad de las aguas para la preservación de la biodiversidad.
- **Proporción de superficie cubierta por bosques y vulnerabilidad de asentamientos humanos.**

---

## Normativa aplicable (Colombia)

- **Ley 99 de 1993:** Crea el Sistema Nacional Ambiental (SINA) y establece la base del Sistema de Información Ambiental.
- **Decreto 1076 de 2015:** Decreto Único Reglamentario del Sector Ambiente; dicta la coordinación del SIAC y el SIUR.
- **Resolución 839 de 2023:** Adopta el RETC (Registro de Emisiones y Transferencia de Contaminantes) y lo integra operativamente en el RUA.
- **Decreto 1287 de 2014:** Regula las condiciones y criterios técnicos, físicos y microbiológicos para el uso de biosólidos generados en PTAR.
- **Ley 1712 de 2014:** Ley de Transparencia y Derecho de Acceso a la Información Pública.

---

## Preguntas analíticas típicas

1. ¿Qué cantidad de contaminantes se están emitiendo o transfiriendo en un periodo de tiempo y a qué medio (agua, suelo, aire) llegan?
2. ¿Cuáles son las áreas o ecosistemas con mayor núcleo o densidad de deforestación y cuáles son las actividades económicas o socioculturales subyacentes?
3. ¿Están cumpliendo los establecimientos de un sector con los valores máximos permisibles de vertimientos y emisiones reportados en el RUA?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Inventarios nacionales de gases de efecto invernadero y reportes agregados para caracterizar cambios en coberturas a nivel de departamentos, municipios o veredas.

**Predictiva:**
- Elaboración de escenarios y proyecciones usando modelos logísticos o econometría espacial para determinar el riesgo y el comportamiento futuro de la deforestación.

**Espacial:**
- Procesamiento digital de imágenes (calibración radiométrica, normalización, máscaras de nubes/agua), teledetección y Análisis de Componentes Principales (PCA) para la detección de cambios en coberturas forestales.

---

## Actores institucionales

- **MADS:** Ente rector y orientador del sistema.
- **IDEAM:** Administrador y coordinador técnico-tecnológico del SIAC, SMByC, RUA y otros subsistemas centrales.
- **Institutos Científicos (INVEMAR, Humboldt, Sinchi, IIAP):** Productores de conocimiento e investigación especializada.
- **Autoridades Ambientales (CARs y Autoridades Urbanas):** Entidades encargadas del suministro, validación y gestión de la información territorial y el licenciamiento en sus jurisdicciones.

---

## Riesgos y sesgos en los datos

- **Fragmentación y baja interoperabilidad:** La existencia de sistemas y plataformas desconectados genera silos de información y dificultades para acceder a datos unificados, propiciando posibles incongruencias.
- **Brechas de capacidad técnica:** Diferencias marcadas de presupuesto, herramientas tecnológicas (SIG) y personal capacitado entre las distintas CARs.
- **Riesgos de submuestreo:** Durante la caracterización de agentes de la deforestación, la falta de delimitación puede ocasionar que áreas omitidas queden clasificadas engañosamente (sesgo de muestreo).
- **Sobrecarga institucional:** La exigencia continua de nuevos reportes derivados de obligaciones internacionales y nacionales puede desbordar la capacidad operativa y de almacenamiento actual del IDEAM.

---

## Glosario mínimo

- **SIAC:** Sistema de Información Ambiental de Colombia.
- **SINA:** Sistema Nacional Ambiental.
- **SMByC:** Sistema de Monitoreo de Bosques y Carbono.
- **RUA:** Registro Único Ambiental.
- **RETC:** Registro de Emisiones y Transferencia de Contaminantes.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **SIB Colombia:** Sistema de Información sobre Biodiversidad de Colombia.
- **RUNAP:** Registro Único Nacional de Áreas Protegidas.
- **VITAL:** Ventanilla Integral de Trámites Ambientales en Línea.
- **Biosólido:** Subproducto estabilizado resultante de someter los lodos de las PTAR a procesos de tratamiento.
- **Metadato:** Datos acerca del contenido, calidad y condición de un producto geográfico o alfanumérico.
- **SINGEI:** Sistema de Inventario Nacional de Gases Efecto Invernadero.
- **IDE:** Infraestructura de Datos Espaciales.
- **Analítica predictiva:** Técnica que identifica la ocurrencia de eventos futuros a partir de registros y variables históricas.
- **DBO:** Demanda Bioquímica de Oxígeno — métrica común de contaminación en agua.

---

## Preguntas abiertas / oportunidades

- **Interoperabilidad profunda:** ¿Cómo transitar de un "portal de enlaces" hacia un modelo unificado real (arquitecturas de Data Lakehouse) que integre en su totalidad al SIRH, RUA, RETC y los reportes de las corporaciones territoriales?
- **Brecha digital comunitaria:** ¿Qué estrategias no digitales y participativas pueden solventar la exclusión de poblaciones rurales sin buena conexión a internet?
- **Calidad de datos e incentivos al reporte:** Existen formatos obsoletos en sistemas como el SUI (Superintendencia de Servicios Públicos) que no se ajustan a normativas vigentes (ej. Biosólidos vs. Lodos), impidiendo tener el volumen y calidad real de los datos del país.
- **Sostenibilidad financiera:** La estructura de financiamiento del esquema informático del IDEAM y el SIAC presenta signos de desfinanciación de cara a la exigencia tecnológica que demandan los grandes volúmenes de datos ambientales en tiempo real.

---

## Referencias

- Fuentes del notebook: Ley 99 de 1993, Decreto 1076 de 2015, Resolución 839 de 2023, IDEAM, INVEMAR, Instituto Humboldt, SINCHI, IIAP, CARs.
