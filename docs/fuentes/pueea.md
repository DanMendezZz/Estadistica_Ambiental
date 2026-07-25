# PUEEA — Programa para el Uso Eficiente y Ahorro del Agua

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/76b05acf-5e9e-46d5-9aba-3d5c2891906c
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, Recurso hídrico, Rondas hídricas, Sistemas de información ambiental

---

## Resumen ejecutivo

La gestión del recurso hídrico en Colombia ha evolucionado hacia una disciplina que integra normatividad ambiental rigurosa y herramientas de ingeniería y ciencia de datos. El eje central es el Programa para el Uso Eficiente y Ahorro del Agua (PUEAA), el cual obliga a los usuarios a optimizar el consumo, controlar pérdidas y proteger ecosistemas. La información de los usuarios y las concesiones se consolida a nivel nacional mediante el Sistema de Información del Recurso Hídrico (SIRH).

Recientemente, el país ha comenzado a explorar y adoptar la analítica predictiva y el aprendizaje no supervisado. Modelos estadísticos y de machine learning (SARIMAX, Prophet, Isolation Forest) ofrecen nuevas capacidades para predecir inundaciones, estimar demandas y detectar anomalías en el consumo, integrando las métricas gubernamentales oficiales para salvaguardar la sostenibilidad hídrica.

---

## Objetivos

- **Garantizar la sostenibilidad hídrica:** Mediante la reducción de pérdidas, la implementación de tecnologías de bajo consumo y la reutilización del agua.
- **Consolidar la gobernanza de datos:** Centralizar información de concesiones, vertimientos y calidad del agua mediante el SIRH.
- **Prevenir el riesgo de desabastecimiento:** Monitorear la oferta y demanda para gestionar eficazmente el recurso durante escenarios de variabilidad climática extrema.
- **Modernizar el monitoreo operativo:** Emplear modelos predictivos para detectar fugas (anomalías) y anticipar caudales.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Caudal (Oferta/Demanda) | L/s o m³/s | > 0 a > 40 L/s (concesiones típicas) | Diaria / Mensual | IDEAM, Aforos in situ |
| DBO₅ | mg/L O₂ | Variable según contaminación | Mensual / Semestral | Laboratorios acreditados |
| Oxígeno Disuelto (OD) | mg/L | Dependiente del tramo | In situ (durante muestreo) | Equipos multiparamétricos |
| Precipitación | mm | Dependiente de zona/época | Diaria / Histórica | Red Hidrometeorológica IDEAM |
| Pérdidas de agua (IANC) | % | Aceptable hasta 30% | Anual / Por facturación | Reportes PUEAA / SUI |

---

## Datos y fuentes

- **Datos hidrometeorológicos:** Registros continuos de caudales, precipitación y temperaturas de la red oficial del IDEAM.
- **Datos administrativos y legales:** Volúmenes de captación, naturaleza jurídica del usuario y número de resoluciones de concesión alojados en el RURH de las CARs.
- **Datos fisicoquímicos e hidrobiológicos:** Muestras de laboratorio (metales pesados, DBO, pH, macroinvertebrados) reportados en Planes de Saneamiento (PSMV) y PORH.
- **Fuentes de información centralizadas:** Estudio Nacional del Agua (ENA) y el SIRH.

---

## Indicadores y métricas oficiales

- **IANC (Índice de Agua No Contabilizada):** Mide la eficiencia del sistema de acueducto y las pérdidas de agua.
- **IVH (Índice de Vulnerabilidad Hídrica por desabastecimiento):** Evalúa el riesgo y la limitación para abastecer la demanda frente a sequías.
- **IUA (Índice de Uso del Agua):** Relación de la cantidad de agua demandada respecto a la oferta hídrica disponible.
- **IRH (Índice de Retención y Regulación Hídrica):** Mide la capacidad de la cuenca para mantener regímenes de caudales estables.
- **ICA / ICAP:** Índices de calidad de agua en fuentes superficiales y de agua potable respectivamente.

---

## Normativa aplicable (Colombia)

- **Ley 373 de 1997:** Establece el Programa para el Uso Eficiente y Ahorro del Agua (PUEAA).
- **Decreto Único 1076 de 2015 + Decreto 1090 de 2018:** Compila normativas ambientales; reglamenta técnicamente el PUEAA.
- **Resolución 1257 de 2018:** Desarrolla la estructura y contenido del PUEAA estándar y del PUEAA Simplificado.
- **Decreto 303 de 2012:** Obliga al reporte mensual de usuarios al RURH-SIRH.
- **Resolución 943 de 2021 (CRA):** Regula los servicios de acueducto y define metas de desincentivo a consumos excesivos.

---

## Preguntas analíticas típicas

1. ¿Qué tramos hidrográficos sufren mayor estrés debido a que el caudal demandado excede la oferta hídrica en años secos?
2. ¿Qué porcentaje de las pérdidas del sistema son técnicas (fugas) versus comerciales (robos), y cómo formular metas para su reducción quinquenal?
3. ¿Cómo se correlaciona la precipitación anómala generada por un fenómeno macroclimático con los picos del IVH a nivel municipal?
4. ¿Cuál es el "caudal bajo" para definir a qué personas naturales les aplica el PUEAA Simplificado sin afectar la equidad del recurso?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Cálculo de rangos, promedios, balances hídricos y correlación lineal (R²) para entender la dispersión o evaluar métricas de calidad y concesiones.

**Predictiva:**
- **SARIMAX:** Modelos autorregresivos con estacionalidad y regresores exógenos climáticos para predecir picos de demanda o eventos de inundación.
- **Prophet:** Algoritmo que descompone eficientemente tendencias complejas, estacionalidad y eventos atípicos sin necesidad de fuerte preprocesamiento.
- **Isolation Forest y Deep Autoencoders:** Detección de anomalías no supervisada en caudales y lecturas de sensores (fugas, fallos técnicos, captaciones ilegales).

**Espacial:**
- Cartografía topológica y perfiles en SIG para ubicar geográficamente a los usuarios del RURH frente a las subzonas hidrográficas.

---

## Actores institucionales

- **MADS:** Dicta la política y marco reglamentario principal (PNGIRH).
- **IDEAM:** Administra el SIRH, formula el Estudio Nacional del Agua (ENA) y opera la red hidrometeorológica oficial.
- **CARs:** Ejercen control, otorgan concesiones y aprueban los PUEAA en cada jurisdicción (CAR Cundinamarca, Corpoboyacá, Cornare).
- **CRA:** Comisión de Regulación de Agua Potable y Saneamiento Básico, define fórmulas de costos y eficiencia en acueductos.

---

## Riesgos y sesgos en los datos

- **Dispersión y subregistro:** Alta heterogeneidad en los datos de caudal y subregistro por parte de los pequeños usuarios (ausencia de medidores de caudal correctos).
- **Problemas de reporte temporal:** Retrasos institucionales y demoras en el cargue de los expedientes físicos al SIRH.
- **Carencia de modelado dinámico histórico:** Indicadores como el IVH se nutren de la oferta/demanda promedio sin considerar la cronología del caudal día a día, por lo que pueden fallar en predecir el impacto en tiempo real de eventos como El Niño.

---

## Glosario mínimo

- **PUEAA:** Programa para el Uso Eficiente y Ahorro del Agua.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **Caudal:** Cantidad o volumen de agua por unidad de tiempo.
- **RURH:** Registro de Usuarios del Recurso Hídrico en el SIRH.
- **IANC:** Índice de Agua No Contabilizada.
- **IVH:** Índice de Vulnerabilidad Hídrica por Desabastecimiento.
- **IUA:** Índice de Uso del Agua.
- **IRH:** Índice de Retención y Regulación Hídrica.
- **Concesión de aguas:** Permiso ambiental para el aprovechamiento de recursos hídricos.
- **Aforo:** Acción de realizar la medición física de un caudal hídrico.
- **Estiaje:** Nivel o caudal hídrico más bajo en tiempos de sequía.
- **Pérdidas de agua:** Volumen de agua captado que no llega al usuario (desperdicio/fuga).
- **SARIMAX:** Modelo predictivo autorregresivo que integra variables ambientales exógenas.
- **Isolation Forest:** Algoritmo no supervisado útil para la detección de consumos atípicos y fugas de agua.

---

## Preguntas abiertas / oportunidades

- ¿Cómo integrar sistemas de medición telemétricos (IoT) directamente a la base de datos del SIRH para evitar reportes erróneos y manuales?
- ¿De qué manera fortalecer las capacidades del personal técnico en CARs con deficiencias operativas y bajo conocimiento de las fuentes de agua subterráneas?
- ¿Cómo masificar el uso del PUEAA Simplificado en zonas rurales para combatir la ilegalidad hídrica sin sobrecargar a los usuarios financieramente?
- ¿Cómo consolidar esquemas de gobernanza regional para unificar los cientos de inventarios y sistemas SIG disgregados en las entidades municipales?

---

## Referencias

- Fuentes del notebook: Ley 373 de 1997, Resolución 1257 de 2018, IDEAM (ENA, SIRH), CARs, CRA, literatura de machine learning aplicado a gestión hídrica.
