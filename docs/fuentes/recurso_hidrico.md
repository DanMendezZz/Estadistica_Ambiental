# Recurso Hídrico — Plan de Ordenamiento del Recurso Hídrico (PORH)

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/be2d8b70-bfda-4925-8624-8a8e8290201a
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, POMCA, Cambio climático, Sistemas de información ambiental

---

## Resumen ejecutivo

El Plan de Ordenamiento del Recurso Hídrico (PORH) es el principal instrumento de planificación estratégica en Colombia para la gestión del agua. Su propósito fundamental es fijar la destinación, clasificación y usos de los cuerpos de agua continentales superficiales y marinos, estableciendo las normas, condiciones y programas de seguimiento necesarios para mantener y recuperar la calidad del recurso en un horizonte mínimo de diez años.

Este proceso se articula dentro del Sistema Nacional Ambiental (SINA) y se desarrolla en fases metodológicas que incluyen la declaratoria, el diagnóstico, la identificación de usos potenciales y la elaboración del plan. Para su formulación técnica, se apoya en modelos de simulación de calidad del agua, índices de alteración potencial y análisis geoespaciales que permiten cuantificar las cargas contaminantes y determinar la capacidad asimilativa de las fuentes hídricas frente al desarrollo socioeconómico.

---

## Objetivos

- Establecer la clasificación de las aguas y fijar su destinación y posibilidades de uso.
- Definir los objetivos de calidad a alcanzar en el corto, mediano y largo plazo.
- Establecer las normas de preservación de la calidad para asegurar la conservación biológica y el desarrollo de las especies.
- Determinar prohibiciones o condicionamientos para actividades productivas o descargas de vertimientos en zonas específicas.
- Estructurar programas de monitoreo y seguimiento para verificar la efectividad del ordenamiento.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| pH | Unidades | 5.0 - 9.0 | Mensual / Campaña | Monitoreo in situ con sonda |
| Oxígeno Disuelto (OD) | mg/L O₂ o % | > 4 mg/L (según uso) | Mensual / Campaña | Monitoreo in situ |
| DBO₅ | mg/L O₂ | Variable según carga | Mensual / Campaña | Análisis de laboratorio |
| DQO | mg/L O₂ | Variable según carga | Mensual / Campaña | Análisis de laboratorio |
| Sólidos Suspendidos Totales (SST) | mg/L | Variable (< 100 mg/L típico) | Mensual / Campaña | Análisis de laboratorio |
| Caudal | m³/s o L/s | Depende de la cuenca | Diario / Campaña | Aforo en campo / Estaciones |
| Coliformes Fecales / Totales | NMP/100 mL | < 1000 a > 20000 | Mensual / Campaña | Análisis microbiológico |

---

## Datos y fuentes

- **Datos hidrometeorológicos:** Series de tiempo históricas de caudales, precipitación y temperatura del IDEAM y CARs. Formato tabular (Excel, CSV).
- **Datos de monitoreo de calidad:** Resultados de campañas de aforo y muestreo fisicoquímico, microbiológico e hidrobiológico. Formato tabular y reportes de laboratorio.
- **Datos geoespaciales:** MDT, mapas de coberturas (Corine Land Cover) e imágenes satelitales (Sentinel-2). Formatos raster y vectorial (Shapefile).
- **Registros administrativos:** Censos de usuarios, concesiones de agua y permisos de vertimiento consolidados en el RURH y el SIRH.

---

## Indicadores y métricas oficiales

- **IACAL:** Índice de Alteración Potencial de la Calidad del Agua; evalúa presión por contaminación.
- **ICA:** Índice de Calidad del Agua; agregación ponderada de OD, SST, DQO, conductividad, pH, nitrógeno y fósforo.
- **ICO:** Índices de Contaminación — ICOMO (materia orgánica) e ICOSUS (sólidos suspendidos).
- **BMWP-Col:** Índice biológico con macroinvertebrados bentónicos para calificar calidad ecológica del agua.
- **IRH e IUA:** Índices de Retención y Regulación Hídrica y de Uso del Agua Superficial.

---

## Normativa aplicable (Colombia)

- **Decreto 1076 de 2015:** Decreto Único Reglamentario del Sector Ambiente. Libro 2, Parte 2, Título 3 regula el ordenamiento del recurso hídrico y vertimientos.
- **Decreto 3930 de 2010:** Reglamenta usos del agua y residuos líquidos.
- **Resolución 0751 de 2018 (MADS):** Guía Técnica para la Formulación de Planes de Ordenamiento del Recurso Hídrico Continental Superficial.
- **Decreto 1594 de 1984:** Antecedente fundamental en criterios de calidad y usos del agua.
- **Resolución 631 de 2015:** Parámetros y límites máximos permisibles en vertimientos puntuales.
- **Decreto 2667 de 2012:** Tasas retributivas por vertimientos.

---

## Preguntas analíticas típicas

1. ¿Cuál es la capacidad de asimilación y autodepuración del cuerpo de agua frente a escenarios de carga contaminante actual y futura?
2. ¿Qué impactos causan los vertimientos domésticos e industriales durante condiciones hidrológicas críticas (estiaje)?
3. ¿Cuáles son las metas de reducción de carga contaminante para cumplir objetivos de calidad en los próximos 10 años?
4. ¿Qué restricciones se deben aplicar en el ordenamiento territorial para evitar desabastecimiento o toxicidad crónica?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Estadísticas descriptivas de parámetros fisicoquímicos por tramo de río y periodo hidrológico.
- Análisis multivariado (RDA) para correlacionar factores fisicoquímicos con comunidades biológicas.
- Tests de tendencia (Mann-Kendall) sobre series históricas de calidad.

**Predictiva:**
- Modelación dinámica de calidad del agua: QUAL2K, QUAL2Kw, CE-QUAL-W2 para simular perfiles y transporte de solutos.
- Machine Learning (XGBoost, Random Forest) para predecir potabilidad, modelar inundaciones o clasificar índices de antropización.

**Espacial:**
- Interpolación geoestadística y extracción de índices espectrales (Sentinel-2) para estimar turbidez y clorofila-a.
- Delimitación de zonas de mezcla y análisis de dispersión de plumas de vertimiento.

---

## Actores institucionales

- **MADS:** Rector de la política, emite normativas y guías técnicas.
- **IDEAM:** Lineamientos de modelación, redes nacionales de monitoreo, Estudio Nacional del Agua.
- **CARs y Autoridades Ambientales:** Formulan y hacen seguimiento a los PORH (CAR, CORPOCHIVOR, CORTOLIMA, CORANTIOQUIA).
- **Empresas de Servicios Públicos y Municipios:** Principales usuarios y generadores de vertimientos; deben ejecutar PSMV.

---

## Riesgos y sesgos en los datos

- **Resolución temporal y espacial limitada:** Los monitoreos en campo son imágenes puntuales; sin redes robustas no se captura la variabilidad temporal completa.
- **Incertidumbre paramétrica:** Los modelos matemáticos presentan alta incertidumbre por falta de series largas y constantes biocinéticas tropicales.
- **Datos atípicos y vacíos:** Históricos con outliers no reportados y laboratorios con límites de detección insuficientes.
- **Variabilidad climática no integrada:** Análisis frecuentemente basados en medias históricas que no reflejan eventos extremos por cambio climático.

---

## Glosario mínimo

- **PORH:** Plan de Ordenamiento del Recurso Hídrico.
- **Caudal ambiental:** Volumen de agua necesario para mantener la funcionalidad y resiliencia de los ecosistemas acuáticos.
- **Carga contaminante:** Masa de una sustancia vertida por unidad de tiempo.
- **Capacidad de asimilación:** Capacidad de un cuerpo hídrico para aceptar y degradar contaminantes.
- **DBO₅:** Demanda Bioquímica de Oxígeno a cinco días; indicador de contaminación orgánica.
- **DQO:** Demanda Química de Oxígeno; medida de contaminación química global.
- **Zona de mezcla:** Área post-vertimiento donde se permite sobrepasar criterios de calidad mientras se homogeniza la pluma.
- **Objetivo de calidad:** Valores meta de parámetros definidos para alcanzar usos asignados a futuro.
- **Tasa retributiva:** Cobro económico por unidad de carga contaminante vertida al medio.
- **SIRH:** Sistema de Información del Recurso Hídrico.
- **Macroinvertebrados bénticos:** Organismos acuáticos utilizados como bioindicadores ecológicos.
- **Escorrentía:** Volumen de agua que fluye sobre la superficie del suelo hacia las corrientes.
- **Eutrofización:** Enriquecimiento anómalo de nutrientes en un ecosistema acuático.
- **Vertimiento puntual:** Descarga canalizada directamente a un cuerpo hídrico en un sitio específico.
- **PSMV:** Plan de Saneamiento y Manejo de Vertimientos.

---

## Preguntas abiertas / oportunidades

- ¿Cómo integrar de forma más sistemática las interacciones entre aguas subterráneas y superficiales dentro de la modelación del PORH?
- ¿De qué manera puede el Machine Learning suplir vacíos de redes de monitoreo in situ en cuencas de difícil acceso?
- ¿Cómo articular variaciones por proyecciones de cambio climático extremo dentro del horizonte a 10 años del PORH?
- ¿Qué esquemas de bajo costo en sensores IoT se pueden escalar para monitoreo en tiempo real de objetivos de calidad?

---

## Referencias

- Fuentes del notebook: documentos técnicos del MADS, IDEAM, CARs y literatura de modelación de calidad del agua (QUAL2K, CE-QUAL-W2).
