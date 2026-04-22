# Oferta Hídrica Subterránea

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/c4737b81-3ca0-48fa-942d-eac5f1689b8a
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Recurso hídrico, POMCA, Cambio climático, Rondas hídricas

---

## Resumen ejecutivo

El agua subterránea representa una de las fuentes estratégicas más importantes para el abastecimiento humano y la sostenibilidad de los ecosistemas, abasteciendo a una porción fundamental de la población y aportando al caudal base de los ríos. A pesar de su importancia, se enfrenta a riesgos críticos de agotamiento y contaminación derivados de la presión antrópica, la deficiente planificación urbana y el cambio climático. Su gestión integral requiere un balance preciso entre la demanda socioeconómica y la oferta disponible, asegurando su existencia futura.

En Colombia, la administración y conocimiento de la oferta hídrica subterránea se estructura a través de instrumentos de planificación como los Planes de Ordenación y Manejo de Cuencas Hidrográficas (POMCA) y los Planes de Manejo Ambiental de Acuíferos (PMAA). Estos instrumentos se apoyan en el levantamiento estandarizado de información primaria mediante inventarios (FUNIAS), el diseño de redes de monitoreo piezométrico y de calidad, y la formulación de modelos hidrogeológicos conceptuales y numéricos que permiten diagnosticar, proteger y regular el uso sostenible del recurso.

---

## Objetivos

- Identificar y caracterizar las unidades geológicas y la geometría de los sistemas que conforman los acuíferos.
- Cuantificar la oferta hídrica potencial y las reservas de agua subterránea, estimando parámetros hidráulicos (transmisividad, conductividad).
- Evaluar la vulnerabilidad intrínseca de los acuíferos a la contaminación para establecer perímetros de protección en zonas de recarga.
- Caracterizar la demanda y uso actual del agua subterránea para evitar conflictos de sobreexplotación y calcular índices de escasez y uso.
- Implementar redes de monitoreo espacio-temporal (calidad y cantidad) para evaluar la dinámica del acuífero y su interacción con aguas superficiales.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Nivel Estático (Ne) | metros (m) | 3.3 a 30 m o más | Semestral / Continua | Sonda de nivel / Piezómetro |
| Nivel Dinámico (Nd) | metros (m) | > Nivel estático | Semestral (durante bombeo) | Sonda de nivel / Pozo |
| Caudal de Extracción | L/s o m³/año | 1 a 50+ L/s | Diario / Mensual / Anual | Medidor / Concesión CAR |
| Conductividad Eléctrica | µS/cm | ~100 a 1000 µS/cm | Semestral in situ | Equipo multiparamétrico |
| pH | Adimensional | 6.5 a 9.0 | Semestral in situ | Equipo multiparamétrico |
| Temperatura del Agua | °C | 24°C a 37°C | Semestral in situ | Termómetro / Sonda |
| Transmisividad (T) | m²/día | Varía según litología | Única vez (por prueba) | Pruebas de bombeo |
| Recarga Neta / Lluvia | mm/año o mm/mes | Según isoyetas y clima | Mensual / Anual | Estación Meteorológica |

---

## Datos y fuentes

- **Inventarios de Campo (FUNIAS):** Datos tabulares y documentales con coordenadas, características de pozos/aljibes, columnas litológicas y variables fisicoquímicas. Provenientes de censos de usuarios.
- **Información Geográfica y Cartográfica (SIG):** Formatos vectoriales (.shp) y ráster (Modelos Digitales de Elevación) que documentan geología, uso de suelo, edafología e hidrografía. Fuentes: SGC, IDEAM, IGAC, institutos de planificación.
- **Expedientes de Concesión:** Documentos técnicos de CARs con registros de regímenes de bombeo, volúmenes autorizados y pruebas de capacidad.
- **Bases de Datos de Monitoreo:** Formatos Excel/CSV o bases nacionales (SIRH) con series de tiempo de niveles piezométricos y calidad del agua.

---

## Indicadores y métricas oficiales

- **Índice de Uso del Agua (IUA):** Relaciona la demanda socioeconómica con la oferta disponible. Valores >100 indican presión crítica (sobreexplotación).
- **Índice de Escasez del Agua Subterránea:** Evalúa la relación oferta-demanda según metodologías estandarizadas.
- **Índices de Vulnerabilidad GOD y DRASTIC:** GOD evalúa Grado de confinamiento, sustrato Suprayacente y Profundidad. DRASTIC incluye recarga, textura del suelo, topografía, etc.
- **Índice de Reservas Temporalmente Aprovechables (IRTA):** Evalúa la cantidad de agua subterránea disponible para extracción segura.

---

## Normativa aplicable (Colombia)

- **Decreto Único Reglamentario 1076 de 2015:** Compila normativas del sector ambiente. Reglamenta POMCAs, PMAAs y concesiones de agua.
- **Decreto 1640 de 2012:** Reglamenta instrumentos para la planificación, ordenación y manejo de cuencas hidrográficas y sistemas acuíferos.
- **Ley 99 de 1993:** Crea el SINA, otorga funciones a SGC, IDEAM y CARs. Declara zonas de recarga como áreas de protección especial.
- **Decreto 3930 de 2010:** Usos del agua, ordenamiento del recurso hídrico y vertimientos.
- **Resolución 872 de 2006:** Metodología para el cálculo del índice de escasez del agua subterránea.

---

## Preguntas analíticas típicas

1. ¿Cuál es la geometría, espesor y capacidad de almacenamiento de las unidades hidrogeológicas del área?
2. ¿Cuál es la dirección del flujo subterráneo y dónde se ubican las principales zonas de recarga y descarga?
3. ¿El volumen concesionado y extraído supera la oferta disponible o el rendimiento sostenible del acuífero?
4. ¿Existen conexiones hidráulicas directas entre el acuífero y ríos o humedales superficiales?
5. ¿Las características físico-químicas muestran huellas de contaminación antrópica o riesgos para consumo humano?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Estadísticas descriptivas por unidad hidrogeológica (nivel, caudal, calidad).
- Diagramas de Piper y Stiff para tipificar familias de aguas y detectar evolución química.
- Tests de tendencia (Mann-Kendall) en series piezométricas.

**Predictiva:**
- Modelación numérica (MODFLOW + Python/FloPy): diferencias finitas para simular comportamiento de bombeo a largo plazo y seguimiento de contaminantes.
- Modelos de series temporales para proyectar abatimiento de niveles.
- Análisis isotópicos (δ¹⁸O, δ²H) para calcular edades y tiempos de residencia.

**Espacial:**
- Interpolación espacial (IDW, Kriging Empírico Bayesiano - EBK) para mapas de isopiezas y modelos de nivel freático.
- Cálculo de velocidad y aceleración del abatimiento espacial.
- Mapas de vulnerabilidad GOD/DRASTIC con SIG.

---

## Actores institucionales

- **MADS (Ministerio de Ambiente y Desarrollo Sostenible):** Dicta la Política Nacional (PNGIRH) y lineamientos normativos.
- **SGC (Servicio Geológico Colombiano):** Exploración geológica básica, evaluación de reservas e investigación del subsuelo.
- **IDEAM:** Monitoreo nacional (Estudio Nacional del Agua), protocolos técnicos y administración del SIRH.
- **CARs (Corporaciones Autónomas Regionales):** Expiden concesiones, aplican tasas retributivas, ejecutan PMAA y POMCA (ej. CORPOCESAR, CORTOLIMA, CVC).
- **Empresas de Servicios Públicos y Usuarios:** Sector agrícola e industrial que extrae el recurso y aporta datos operativos.

---

## Riesgos y sesgos en los datos

- **Subestimación de la demanda por ilegalidad:** Gran proporción de aprovechamientos (pozos/aljibes) no están legalizados ni concesionados, introduciendo sesgos graves en los balances oferta-demanda.
- **Series de tiempo cortas o discontinuas:** Registros hidrometeorológicos y piezométricos insuficientes para análisis de tendencias climáticas o agotamiento a largo plazo.
- **Problemas constructivos de los pozos de monitoreo:** Muchos pozos carecen de diseño adecuado (mangueras angostas, obstrucciones) que impide mediciones correctas con sondas.
- **Vacíos geológicos a gran profundidad:** Alta dependencia de datos someros; caracterización de acuíferos profundos basada en inferencias indirectas, elevando incertidumbre de los modelos.

---

## Glosario mínimo

- **Acuífero:** Formación geológica permeable que permite almacenar y transmitir agua subterránea.
- **Nivel estático (Ne):** Distancia natural desde el suelo hasta la superficie del agua en un pozo sin bombeo.
- **Nivel dinámico (Nd):** Nivel del agua en un pozo durante la extracción o bombeo.
- **Piezómetro:** Pozo de diámetro estrecho diseñado específicamente para monitoreo hidrogeológico.
- **Transmisividad (T):** Parámetro hidráulico que define la capacidad del acuífero para transmitir agua.
- **Superficie piezométrica:** Superficie imaginaria formada por puntos de igual presión de agua en el subsuelo.
- **Recarga neta:** Volumen de agua superficial o precipitación que se infiltra hasta la zona saturada.
- **FUNIAS:** Formulario Único Nacional para el Inventario de Puntos de Agua Subterránea.
- **PMAA:** Plan de Manejo Ambiental de Acuíferos.
- **Vulnerabilidad intrínseca:** Susceptibilidad natural de un acuífero a ser contaminado desde la superficie.
- **Rendimiento sostenible (Safe yield):** Cantidad de agua que se puede extraer sin provocar efectos adversos a largo plazo.
- **Isótopos ambientales:** Trazadores químicos naturales usados para determinar origen y edad del agua.
- **Cono de abatimiento:** Curva de descenso del nivel freático generada alrededor de un pozo en bombeo.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **IUA:** Índice de Uso del Agua — relación demanda/oferta hídrica disponible.

---

## Preguntas abiertas / oportunidades

- **Monitoreo automatizado a escala:** ¿Cómo financiar e implementar tecnologías telemétricas para datos piezométricos en tiempo real y reducir dependencia de mediciones manuales?
- **Apropiación social:** ¿Cómo integrar a usuarios en la construcción de inventarios (IPAS) y en la gestión directa del recurso?
- **Interacción con cambio climático:** Desarrollar modelos predictivos que evalúen el impacto de alteraciones en precipitación y evapotranspiración sobre zonas de recarga estacionales.
- **Control de acuíferos multicapa:** ¿Cómo mejorar regulaciones para evitar intercomunicación no deseada y contaminación cruzada entre acuíferos someros y profundos?

---

## Referencias

- Fuentes del notebook: documentos técnicos de POMCAs, PMAAs, SGC, IDEAM, IGAC y CARs colombianas.
