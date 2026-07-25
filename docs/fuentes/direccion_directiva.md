# Dirección Directiva — Analítica de Datos para la Gestión Pública Ambiental en Colombia

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/bed2246f-cb75-4b91-8ca5-8f1b194ecfd1
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Sistemas de información ambiental, Cambio climático, POMCA, Calidad del aire, Rondas hídricas

---

## Resumen ejecutivo

La gestión pública ambiental en Colombia, enmarcada en el Sistema Nacional Ambiental (SINA), ha evolucionado de un modelo tradicional de reportes documentales hacia una arquitectura basada en la analítica de datos y la toma de decisiones informada por evidencia. Esta transformación busca responder a la inmensa diversidad ecosistémica y a los desafíos del cambio climático mediante la integración de sistemas como el SIAC y la Cuenta Satélite Ambiental (CSA) del DANE.

El uso de ciencia de datos, sistemas de información geográfica e interoperabilidad institucional permite hoy monitorear el desempeño de las Corporaciones Autónomas Regionales (CAR) y medir el impacto de las políticas públicas orientadas al desarrollo sostenible. De este modo, la información ambiental se consolida como el activo estratégico más importante para garantizar la resiliencia climática, el control de la deforestación y la rendición de cuentas frente a compromisos globales como los ODS y el Acuerdo de París.

---

## Objetivos

- **Evaluar el desempeño institucional:** Medir la eficacia, eficiencia y capacidad administrativa de las autoridades ambientales a través de índices oficiales.
- **Monitorear el estado de los recursos:** Cuantificar la disponibilidad, agotamiento, calidad y stock de los activos ambientales (agua, aire, suelo, bosque) frente a las presiones antrópicas.
- **Soportar la toma de decisiones:** Utilizar análisis descriptivos, predictivos y prescriptivos para focalizar inversiones, otorgar licenciamientos y formular instrumentos de ordenamiento (POMCA, PIGCCT).
- **Garantizar transparencia y democratización:** Facilitar el acceso público a la información ambiental, promoviendo la veeduría ciudadana y el cumplimiento de acuerdos internacionales.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Calidad del Aire (PM10 / PM2.5) | µg/m³ | PM10: ≤ 50; PM2.5: ≤ 25 | Diaria / Continua | Redes SVCA / SISAIRE / IDEAM |
| Calidad del Agua Superficial (ICA) | Adimensional | 0 (Muy malo) a 1 (Bueno) | Trimestral / Semestral | Red IDEAM / CARs |
| Tasa de Cambio Cobertura Natural | Hectáreas (ha) | Variable según región | Anual | SMByC / Corine Land Cover |
| Emisiones GEI | Gigagramos CO₂eq | Variable (según sector) | Anual / Bienal | RENARE / SINGEI / IDEAM |
| Consumo Residencial de Agua | L / hab / día | Depende del clima/piso | Anual | SUI (SSPD) / CARs |

---

## Datos y fuentes

- **Tipos de datos:** Estructurados (bases de datos relacionales, hojas de cálculo, series de tiempo) y no estructurados (imágenes satelitales, reportes documentales).
- **Sistemas de Información (SIAC):** SIB (Biodiversidad), SIAM (Marino), SNIF (Forestal), SIRH (Recurso Hídrico), RUNAP (Áreas Protegidas), VITAL (Trámites ambientales).
- **Fuentes de estadística derivada:** Cuenta Satélite Ambiental (CSA) del DANE, integrando Encuestas Anuales (EAM), Encuesta de Calidad de Vida (ECV) y registros del SINA.

---

## Indicadores y métricas oficiales

- **IEDI (Índice de Evaluación del Desempeño Institucional):** Mide el desempeño de las CAR en los componentes misional (eficacia/eficiencia), financiero y administrativo.
- **ICAU (Índice de Calidad Ambiental Urbana):** Agrega indicadores sobre calidad del aire, agua, áreas verdes, espacio público y residuos para evaluar las ciudades.
- **IMG (Indicadores Mínimos de Gestión):** Clasificados en ambientales, de gestión y de desarrollo sostenible, permiten relacionar la intervención institucional con el estado de los recursos naturales.

---

## Normativa aplicable (Colombia)

- **Ley 1931 de 2018:** Establece directrices para la gestión del cambio climático y crea el Sistema Nacional de Información sobre Cambio Climático y el RENARE.
- **Decreto 1076 de 2015:** Decreto Único Reglamentario del Sector Ambiente y Desarrollo Sostenible.
- **Resolución 667 de 2016 (MADS):** Establece los Indicadores Mínimos de Gestión, Desarrollo Sostenible y Ambientales para las CAR.
- **Ley 99 de 1993:** Crea el SINA y otorga funciones de seguimiento y control a las autoridades ambientales.

---

## Preguntas analíticas típicas

**Descriptiva:**
1. ¿Cuál es la concentración promedio anual de material particulado en el municipio X?
2. ¿Qué porcentaje de avance físico tiene el Plan de Acción Cuatrienal (PAC)?

**Predictiva:**
3. ¿Se alcanzará la meta de restauración de ecosistemas a 2027 siguiendo la tendencia actual?
4. ¿Cuál es la probabilidad de ocurrencia de un conflicto de interés o riesgo de corrupción en la contratación pública de un proyecto ambiental?

**Prescriptiva:**
5. ¿Qué áreas deben ser priorizadas para la delimitación de rondas hídricas para mitigar el riesgo de desabastecimiento?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Modelos conceptuales de indicadores: marcos PER (Presión-Estado-Respuesta) y DPSIR (Fuerza Motriz-Presión-Estado-Impacto-Respuesta) promovidos por la OCDE y la ONU.

**Predictiva:**
- Series de tiempo (ARIMA) para pronosticar el avance de metas críticas o la evolución de variables climáticas.
- Machine Learning (Isolation Forest) para detectar anomalías presupuestales.
- Random Forest o Gradient Boosting para clasificar riesgos en contratación.

**Espacial:**
- Análisis multitemporal mediante cartografía y sensores remotos (metodología Corine Land Cover) para medir fragmentación de ecosistemas y tasas de deforestación.

---

## Actores institucionales

- **MADS:** Ente rector, define lineamientos y coordina el SIAC.
- **Institutos de Investigación (IDEAM, Humboldt, SINCHI, INVEMAR, IIAP):** Proveen la base científica y administran subsistemas de información (IDEAM opera las redes meteorológicas y el SMByC).
- **DANE:** Responsable de las estadísticas oficiales macroeconómicas integradas mediante la Cuenta Satélite Ambiental (CSA).
- **CARs y Autoridades Urbanas:** Ejecutan la política a nivel territorial y son fuente primaria de datos de calidad ambiental local e indicadores de gestión.

---

## Riesgos y sesgos en los datos

- **Fragmentación y silos de datos:** La información suele estar dispersa en diferentes instituciones con bajos niveles de interoperabilidad y falta de estandarización en formatos.
- **Sesgo de cobertura espacial:** Las estaciones de monitoreo (calidad del agua y aire) están concentradas principalmente en la región Andina o centros urbanos principales, invisibilizando zonas periféricas.
- **Discontinuidad temporal:** Irregularidad en la frecuencia de las mediciones primarias (ej. monitoreos que no cumplen con la frecuencia mínima trimestral estipulada).
- **Brecha digital:** Limitaciones de infraestructura, conectividad y apropiación de tecnologías de la información a nivel local restringen la participación comunitaria y el reporte continuo de datos.

---

## Glosario mínimo

- **SINA:** Sistema Nacional Ambiental.
- **SIAC:** Sistema de Información Ambiental de Colombia.
- **IEDI:** Índice de Evaluación del Desempeño Institucional.
- **ICAU:** Índice de Calidad Ambiental Urbana.
- **CSA:** Cuenta Satélite Ambiental del DANE.
- **GEI:** Gases de Efecto Invernadero.
- **ODS:** Objetivos de Desarrollo Sostenible.
- **VITAL:** Ventanilla Integral de Trámites Ambientales en Línea.
- **POMCA:** Plan de Ordenación y Manejo de Cuencas Hidrográficas.
- **PER / DPSIR:** Modelos Presión-Estado-Respuesta / Fuerzas Motrices-Presión-Estado-Impacto-Respuesta.
- **RENARE:** Registro Nacional de Reducción de las Emisiones de GEI.
- **SMByC:** Sistema de Monitoreo de Bosques y Carbono.
- **PIGCCT:** Planes Integrales de Gestión del Cambio Climático Territoriales.
- **Corine Land Cover:** Metodología estandarizada para clasificación de coberturas y usos de la tierra.
- **Interoperabilidad:** Capacidad de intercambio de datos sin restricciones técnicas entre sistemas y bases de datos.

---

## Preguntas abiertas / oportunidades

- ¿Cómo lograr una implementación real y automatizada de las capas de interoperabilidad (X-Road y API estandarizadas tipo JSON) entre los distintos subsistemas del SIAC (SIRH, SNIF, VITAL) y el DANE?
- ¿Qué mecanismos de financiación e inversión pueden estructurarse para expandir de manera continua las redes de monitoreo de estaciones físicas (SVCA e hídricas) en regiones no priorizadas actualmente?
- ¿De qué forma se pueden integrar la ciencia de datos avanzada (IA y machine learning) dentro de los procesos operativos cotidianos de las CAR, y no solo a nivel del Ministerio o el DNP?
- ¿Cómo superar la brecha digital y fomentar plataformas colaborativas que permitan la generación de ciencia ciudadana y datos abiertos más robustos desde las comunidades locales?

---

## Referencias

- Fuentes del notebook: Ley 99 de 1993, Ley 1931 de 2018, Resolución 667 de 2016 (MADS), IDEAM, DANE (CSA), Institutos de Investigación SINA.
