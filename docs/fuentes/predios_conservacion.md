# Predios para Conservación y Pagos por Servicios Ambientales (PSA)

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/bc27c5cb-f0fc-4b91-8b78-3c670c7f328a
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, Áreas protegidas, Páramos, Ordenamiento territorial, Geoespacial, Cambio climático

---

## Resumen ejecutivo

La gestión de predios para conservación en Colombia se fundamenta principalmente en el Artículo 111 de la Ley 99 de 1993, el cual declara de interés público las Áreas de Importancia Estratégica para la Conservación del Recurso Hídrico (AIECRH) que abastecen acueductos. Históricamente, las entidades territoriales han estado obligadas a destinar el 1% de sus ingresos corrientes para la adquisición de estas tierras; sin embargo, con normativas como la Ley 2320 de 2023 y el Decreto 1007 de 2018, este enfoque se ha modernizado. Hoy en día, los recursos priorizan el mantenimiento, la restauración ecológica, las Soluciones Basadas en la Naturaleza (SbN) y los esquemas de Pagos por Servicios Ambientales (PSA).

Para la efectiva implementación de esta política pública, el país avanza en el uso de inteligencia geoespacial y administración de tierras, apalancándose en la interoperabilidad de datos a través de modelos como el LADM_COL y el Catastro Multipropósito. Además, el monitoreo ambiental emplea imágenes satelitales de alta recurrencia (Sentinel-2) para asegurar que los incentivos entregados a las comunidades rurales realmente se traduzcan en la preservación y recuperación del capital natural.

---

## Objetivos

- **Proteger el recurso hídrico:** Garantizar la provisión de agua para consumo humano mediante la conservación de páramos, nacimientos y zonas de recarga de acuíferos.
- **Implementar incentivos económicos:** Desplegar esquemas de PSA que compensen a propietarios u ocupantes por conservar o restaurar la cobertura vegetal, evitando la deforestación.
- **Asegurar la inversión territorial:** Garantizar que los municipios y departamentos inviertan al menos el 1% de sus ingresos corrientes en áreas estratégicas registradas oficialmente.
- **Modernizar la administración territorial:** Identificar física, jurídica y económicamente los predios a través del Catastro Multipropósito y el modelo LADM_COL.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| NDVI (Índice de Vegetación de Diferencia Normalizada) | Adimensional | -1 a 1 (Bosques: 0.3 a 0.8) | ~5 días | Imágenes satelitales (Sentinel-2) |
| Extensión de cobertura natural preservada/restaurada | Hectáreas (ha) | Variable según predio | Anual / Multitemporal | Imágenes satelitales / SIG (IDEAM, IGAC) |
| Índice Topográfico de Humedad (TWI) | Adimensional | Variable por topografía | Estática / Periódica | Modelos de Elevación Digital (DEM) |
| Costo de oportunidad del suelo | $/ha/año | Variable según actividad agropecuaria local | Anual / Proyecto | Evaluaciones económicas / Entidades territoriales |
| Relación Beneficio Ambiental / Costo (RBC) | Adimensional | RBC < 1 (Ineficiente); RBC > 1 (Eficiente) | Por proyecto | Evaluaciones de viabilidad financiera |

---

## Datos y fuentes

- **Datos geoespaciales y teledetección:** Imágenes ópticas multiespectrales (Sentinel-2, Landsat) e imágenes de radar (Sentinel-1, PALSAR) para cartografiar el uso del suelo y detectar cambios en la cobertura boscosa.
- **Datos catastrales:** Información física, jurídica y económica de predios centralizada en el Repositorio de Datos Maestros (RDM) y administrada bajo el estándar LADM_COL y el Catastro Multipropósito.
- **Registros ambientales:** El Registro Único de Ecosistemas y Áreas Ambientales (REAA) y el RUNAP.
- **Microdatos socioeconómicos:** Encuestas y registros administrativos para calcular índices de vulnerabilidad (SISBEN) y costo de oportunidad. Requieren procesos de anonimización.

---

## Indicadores y métricas oficiales

- **Porcentaje de ingresos corrientes:** Inversión obligatoria de mínimo el 1% de los ingresos de libre destinación de entes territoriales.
- **Indicadores de monitoreo hídrico:** Índice de uso de agua, índice de retención y regulación hídrica, y calidad del agua.
- **Exactitud temática de clasificación:** Porcentaje de fiabilidad de los mapas de cobertura boscosa (idealmente > 85% con algoritmos como Random Forest).
- **Número de hectáreas bajo acuerdos PSA:** Superficie total protegida mediante acuerdos voluntarios.

---

## Normativa aplicable (Colombia)

- **Ley 99 de 1993 (Art. 108 y 111):** Declara de interés público las áreas de importancia estratégica para el recurso hídrico y establece la obligación de inversión del 1%.
- **Ley 2320 de 2023:** Modifica el Art. 111 integrando Soluciones Basadas en la Naturaleza (SbN), adaptación al cambio climático, restauración y obligatoriedad del REAA.
- **Decreto Ley 870 de 2017:** Establece los lineamientos y principios del Pago por Servicios Ambientales (PSA).
- **Decreto 1007 de 2018:** Reglamenta los componentes del PSA y la adquisición de predios, definiendo sus modalidades y gastos asociados.

---

## Preguntas analíticas típicas

1. ¿Cuál es la relación costo-efectividad (RBC) entre adquirir un predio y otorgar un incentivo de PSA transitorio?
2. ¿Qué áreas tienen mayor prioridad para el abastecimiento hídrico mediante técnicas de Evaluación Multicriterio Espacial (MCDA)?
3. ¿Cómo ha variado la cobertura de bosque en el polígono del predio incentivado según las series temporales de Sentinel-2?
4. ¿Están los beneficiarios del PSA priorizados adecuadamente según la pequeña propiedad y su vulnerabilidad socioeconómica?

---

## Métodos estadísticos sugeridos

**Predictiva:**
- Machine Learning (Random Forest, Redes Neuronales, SVM) para procesar imágenes satelitales (Sentinel-2) y clasificar coberturas forestales o deforestación en tiempo casi real (NRT).

**Espacial:**
- **AHP (Analytic Hierarchy Process):** Para sopesar variables como litología, uso del suelo e índices topográficos para priorizar zonas de recarga hídrica.
- **Modelos de datos relacionales:** Uso del modelo estandarizado ISO 19152 (LADM_COL) para interrelacionar Derechos, Restricciones y Responsabilidades (RRR) con los objetos territoriales espaciales.

---

## Actores institucionales

- **Nivel nacional:** MADS, IDEAM, IGAC, Departamento Nacional de Planeación (DNP).
- **Nivel regional/local:** CARs, municipios, distritos y departamentos (encargados de focalizar áreas y administrar recursos).
- **Iniciativas privadas y mixtas:** Esquemas como BancO2, aliados corporativos y fondos de agua que cofinancian los PSA.

---

## Riesgos y sesgos en los datos

- **Riesgos de privacidad y seguridad:** La publicación de microdatos catastrales o financieros de los beneficiarios de PSA puede exponer a las poblaciones rurales. Obligatorio utilizar técnicas de anonimización (supresión local, microagregación, adición de ruido).
- **Sesgos ópticos por nubosidad:** En zonas tropicales, los satélites ópticos (Sentinel-2) sufren de alta nubosidad, lo que puede sesgar la detección de deforestación. Se mitiga fusionando datos con sensores de radar (Sentinel-1).
- **Rezago catastral:** La falta de actualización en la información de linderos y titularidad puede generar conflictos jurídicos al firmar acuerdos de PSA o adquirir predios.

---

## Glosario mínimo

- **AIECRH:** Áreas de Importancia Estratégica para la Conservación del Recurso Hídrico.
- **PSA:** Pago por Servicios Ambientales; incentivo económico o en especie por conservar o restaurar.
- **LADM_COL:** Perfil colombiano del Land Administration Domain Model (ISO 19152) para estandarizar datos de tierras.
- **Catastro Multipropósito:** Inventario predial integral (físico, jurídico, económico) interoperable.
- **REAA:** Registro Único de Ecosistemas y Áreas Ambientales.
- **RUNAP:** Registro Único Nacional de Áreas Protegidas.
- **Costo de oportunidad:** Beneficio económico sacrificado al dejar de realizar la actividad productiva más representativa en favor de la conservación.
- **NDVI:** Índice de Vegetación de Diferencia Normalizada, indicador de vigor vegetal.
- **Sentinel-2:** Satélite del programa Copernicus que provee imágenes multiespectrales globales gratuitas.
- **SbN:** Soluciones Basadas en la Naturaleza.
- **RRR:** Derechos, Restricciones y Responsabilidades en el marco de administración de tierras.
- **Microdato:** Dato a nivel de unidad de observación (individuo, predio) usado en estadística.
- **Anonimización:** Proceso para eliminar la posibilidad de identificar sujetos en un conjunto de datos.
- **POMCA:** Plan de Ordenación y Manejo de Cuencas Hidrográficas.
- **OTL:** Objeto Territorial Legal, base para la gestión de la información de tierras bajo LADM.

---

## Preguntas abiertas / oportunidades

- **Sostenibilidad financiera a largo plazo:** El PSA está diseñado como un incentivo transitorio (acuerdos de hasta 5 años). Es un reto crítico garantizar cambios de comportamiento permanentes y el desarrollo de actividades productivas sostenibles que no dependan indefinidamente del pago.
- **Enfoque de restauración activa vs. aislamiento:** Las normativas actuales a veces restringen la inversión a la estricta "preservación" o adquisición, limitando opciones para agroecosistemas sostenibles o restauración productiva que beneficiarían más a los pequeños propietarios.
- **Integración efectiva de la información:** Aún existen cuellos de botella para integrar los silos de información ambiental (CARs, IDEAM) con la información catastral y registral (IGAC, SNR), que es precisamente lo que intenta resolver la adopción universal del LADM_COL y el RDM.

---

## Referencias

- Fuentes del notebook: Ley 99 de 1993, Ley 2320 de 2023, Decreto Ley 870 de 2017, Decreto 1007 de 2018, IDEAM, IGAC, BancO2.
