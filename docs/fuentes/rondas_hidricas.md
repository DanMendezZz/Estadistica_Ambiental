# Rondas Hídricas y Sistema de Información del Recurso Hídrico (SIRH)

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/56006897-784c-4430-9514-85a42c801cf8
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, Recurso hídrico, POMCA, Geoespacial, Ordenamiento territorial

---

## Resumen ejecutivo

El Sistema de Información de Recurso Hídrico (SIRH) es el instrumento definido por la Política Nacional para la Gestión Integral del Recurso Hídrico para integrar, estandarizar y articular la información sobre el agua generada por el IDEAM y las autoridades ambientales en Colombia. Este sistema permite la administración de datos de oferta, demanda, calidad y riesgo, siendo el repositorio oficial para la consolidación de los usuarios del recurso hídrico y la base para las Evaluaciones Regionales del Agua.

Las rondas hídricas son áreas de transición (ecotonos) entre los ecosistemas terrestres y acuáticos que juegan un papel fundamental en la regulación hídrica, la conservación de la biodiversidad y la mitigación de riesgos. Su acotamiento pasó de ser una medida estática de 30 metros a un análisis funcional y multidimensional amparado por la Resolución 957 de 2018. Este proceso técnico integra criterios geomorfológicos, hidrológicos y ecosistémicos, y sus resultados deben reportarse integralmente al SIRH e incorporarse en el ordenamiento territorial de los municipios.

---

## Objetivos

- Estandarizar el acopio, registro y consulta de información cuantitativa y cualitativa del recurso hídrico a nivel nacional mediante el SIRH.
- Definir el límite físico de las rondas hídricas mediante la superposición funcional de los componentes geomorfológico, hidrológico y ecosistémico.
- Establecer directrices y estrategias de manejo ambiental (preservación, restauración o uso sostenible) para proteger las fuentes de agua y prevenir riesgos por inundación.
- Integrar los resultados del acotamiento en los instrumentos de planificación territorial (POT, POMCA) como normas de superior jerarquía y determinantes ambientales.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Caudal | m³/s o L/s | Depende del cuerpo de agua | Diaria / Mensual | Estaciones hidrológicas (IDEAM/CAR) |
| Nivel del agua | Metros (m) | Variable por pulsos de inundación | Diaria / Mensual | Limnígrafos, huellas de inundación |
| Precipitación | Milímetros (mm) | Variable según zona de vida | Diaria / Mensual | Estaciones meteorológicas (IDEAM) |
| Ancho de faja paralela | Metros (m) | 0 a 30 m (o mayor por criterio hidrológico) | Única (por estudio) | Análisis espacial / Modelación |
| Altura de la vegetación (Dosel) | Metros (m) | Depende de la zona de vida | Única (por estudio) | LiDAR, levantamiento en campo |

---

## Datos y fuentes

- **Topográficos y espaciales:** Modelos Digitales de Elevación (MDE), imágenes LiDAR, levantamientos batimétricos y fotografías aéreas históricas.
- **Hidroclimáticos:** Series temporales (mínimo 15 años de registro sistemático) de precipitación, caudales y niveles del IDEAM o CARs.
- **Administrativos:** Resoluciones de concesiones de agua, permisos de vertimientos y datos catastrales administrados mediante el Registro de Usuarios del Recurso Hídrico (RURH) en el SIRH.
- **Socioculturales:** Cartografía social, entrevistas y bases de datos de quejas o reclamos (PQRS) para la identificación de inundaciones históricas y conflictos socioambientales.

---

## Indicadores y métricas oficiales

- **QBR (Índice de calidad del bosque de ribera):** Mide el grado de alteración y la calidad de la cobertura riparia.
- **RFV (Índice de evaluación del bosque de ribera):** Evalúa el estado y la estructura del ecosistema ribereño.
- **Indicadores de Avance Institucional:** Número de usuarios, predios, fuentes y concesiones reportadas mensualmente por las CARs en el SIRH.
- **Área Acotada:** Superficie (ha) de rondas hídricas con límite físico definido e integradas a los POMCA.

---

## Normativa aplicable (Colombia)

- **Ley 1450 de 2011 (Art. 206):** Asigna a las CARs la competencia de efectuar el acotamiento de las rondas hídricas (faja paralela y área aferente).
- **Decreto 1076 de 2015 (modificado por Decreto 2245 de 2017):** Define los criterios técnicos funcionales para el acotamiento y las pautas para su manejo ambiental.
- **Resolución 957 de 2018 (MADS):** Adopta formalmente la "Guía técnica de criterios para el acotamiento de las rondas hídricas en Colombia".
- **Decreto 1323 de 2007 y Decreto 303 de 2012:** Reglamentan el SIRH y el Registro de Usuarios del Recurso Hídrico (RURH).

---

## Preguntas analíticas típicas

1. ¿Cuál es el área de terreno requerida para garantizar el tránsito seguro de una creciente con período de retorno (Tr) de 100 años en cauces severamente alterados?
2. ¿Cómo afecta la implementación de una ronda hídrica a las infraestructuras de servicios públicos y a las prácticas socioeconómicas en la llanura de inundación?
3. ¿Cuáles son las variables de rugosidad y topografía necesarias para calibrar adecuadamente un modelo hidrodinámico 2D en una zona de planicie?
4. ¿Qué impacto tiene la falta de datos hidrológicos sistemáticos sobre la delimitación final de la ronda, y cómo puede suplirse mediante el conocimiento local?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Análisis de frecuencia de caudales máximos con distribuciones de probabilidad extremas (Gumbel, Mixta Fréchet Tipo I, Log-Pearson Tipo III) para períodos de retorno de 15 o 100 años.

**Predictiva:**
- Modelos de transformación lluvia-escorrentía calibrados y validados para caudales en cuencas no instrumentadas.
- Modelos hidráulicos y cuasi-bidimensionales (HEC-RAS) para simular la superficie del flujo de inundación.
- Deep Learning (arquitectura U-NET) sobre imágenes SAR/Sentinel-1 para detección automatizada de áreas inundadas.

**Espacial:**
- Geomorfometría: análisis multicriterio para priorización de cuerpos de agua.
- WhiteboxTools: extracción de redes de drenaje (algoritmo D8) y cálculo de elevación relativa (HAND — Height Above Nearest Drainage).
- Análisis espacial LiDAR para determinación del dosel ripario.

---

## Actores institucionales

- **MADS:** Rector de la política ambiental y creador de los lineamientos técnicos normativos.
- **IDEAM:** Entidad coordinadora y administradora del SIRH; proveedora de información hidroclimatológica oficial.
- **CARs:** Autoridades responsables de ejecutar los estudios de acotamiento a nivel regional y reportar periódicamente al SIRH (CAR Cundinamarca, CORPOAMAZONIA, CORNARE).
- **Municipios y Distritos:** Entidades territoriales obligadas a incorporar el acotamiento de las rondas hídricas en sus POT.

---

## Riesgos y sesgos en los datos

- **Carencia de datos históricos sistemáticos:** La falta de estaciones hidrometeorológicas con series mayores a 15 años obliga a utilizar modelos indirectos o memorias locales, aumentando la incertidumbre estadística.
- **Asimetrías institucionales:** Diferencias en capacidades humanas, financieras y tecnológicas entre autoridades ambientales generan inconsistencias y retrasos en el reporte de datos al SIRH.
- **Errores espaciales y topográficos:** Uso de MDE de baja resolución o errores al convertir sistemas de coordenadas pueden derivar en manchas de inundación inexactas.
- **Conflictos de interés socioeconómico:** Sesgos potenciales por resistencia comunitaria o presiones de infraestructura al momento de trazar la "zona de flujo preferente" en suelos ya urbanizados.

---

## Glosario mínimo

- **Acotamiento:** Proceso mediante el cual la autoridad ambiental define el límite físico de la ronda hídrica.
- **Banca llena:** Nivel del cauce permanente con capacidad hidráulica para transitar el flujo de crecientes ordinarias.
- **Cauce permanente:** Faja de terreno ocupada por los niveles máximos ordinarios de un cuerpo de agua sin desbordarse.
- **Ecotono:** Región de transición ecológica y dinámica entre los medios terrestre y acuático.
- **Geomorfometría:** Extracción y análisis cuantitativo de la topografía a partir de modelos digitales de elevación.
- **Línea de mareas máximas:** Elevación máxima de la influencia del mar en cuerpos hídricos por pleamar.
- **Ronda hídrica:** Faja paralela a la línea de cauce permanente (hasta 30 m) sumada al área de protección aferente, sujeta a manejo ambiental.
- **RURH:** Registro de Usuarios del Recurso Hídrico.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **Sistemas lénticos / lóticos:** Ecosistemas de aguas estancadas (lagos, humedales) y aguas corrientes (ríos, arroyos), respectivamente.

---

## Preguntas abiertas / oportunidades

- ¿Cómo optimizar el fortalecimiento de las capacidades tecnológicas y el personal técnico en las CARs para asegurar el reporte riguroso y continuo al SIRH?
- ¿Qué mecanismos se requieren para lograr interoperabilidad entre el SIRH y otros subsistemas del SIAC, así como con el Catastro Multipropósito?
- ¿Cómo resolver los inminentes conflictos jurídicos y prediales en tramos donde el acotamiento funcional (creciente de 100 años) colisiona con zonas urbanas densamente pobladas?
- ¿Cómo estandarizar el uso de tecnologías avanzadas de bajo costo (drones, WhiteboxTools, IA) para democratizar la delimitación geomorfométrica en todo el país?

---

## Referencias

- Fuentes del notebook: Resolución 957 de 2018 MADS, Decreto 1076 de 2015, IDEAM, CARs colombianas.
