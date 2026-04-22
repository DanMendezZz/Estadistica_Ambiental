# Páramos — Gestión, Monitoreo y Delimitación de Ecosistemas de Páramo

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/812831f2-26dd-4f56-99c7-1b03c6ae945b
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** A (gestión)
> **Relación con otras líneas:** Oferta hídrica, Cambio climático, Humedales, Gestión de riesgo, Geoespacial

---

## Resumen ejecutivo

Los páramos son ecosistemas de alta montaña exclusivos del neotrópico y vitales para Colombia, país que alberga aproximadamente el 50% de los páramos del mundo. Estos entornos son reconocidos como "fábricas de agua", ya que sus dinámicas hidrológicas, suelos orgánicos profundos (andosoles) y vegetación especializada regulan hasta el 70% del recurso hídrico para el consumo humano y las actividades económicas a nivel nacional. Su conservación y delimitación se han convertido en una prioridad de Estado para contrarrestar amenazas como la minería, la ganadería y la agricultura extensiva.

La gestión de estos ecosistemas combina un profundo marco normativo (liderado por la Ley 1930 de 2018) con herramientas de monitoreo biofísico, análisis geoespacial y modelación hidrológica. La planificación ambiental de los páramos transita entre la conservación estricta, la restauración ecológica y la delimitación de un régimen de usos que promueva la reconversión de actividades agropecuarias hacia prácticas de bajo impacto.

---

## Objetivos

- **Delimitación precisa:** Establecer los límites biogeofísicos de los complejos de páramo a escala 1:25.000 para gestión territorial estricta.
- **Preservación de servicios ecosistémicos:** Proteger la capacidad de captación, retención y regulación hídrica, así como el almacenamiento de carbono.
- **Zonificación y ordenamiento:** Clasificar el territorio paramuno en áreas de preservación, restauración o de uso sostenible.
- **Reconversión productiva:** Diseñar e implementar el desmonte gradual o la sustitución de actividades agropecuarias de alto impacto hacia prácticas ambientalmente sostenibles.
- **Valoración ambiental y saneamiento predial:** Aplicar metodologías para evaluar el grado de conservación de inmuebles ubicados en páramos para fines de saneamiento territorial.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Temperatura media | °C | 7°C - 16°C (alta variación intradiurna) | Continua / Diaria | Estaciones IDEAM / CAR |
| Precipitación vertical | mm/año | 500 - > 3.000 mm/año | Continua / Diaria | Estaciones pluviométricas IDEAM |
| Humedad del suelo (Porosidad) | % | 54% - > 60% | Puntual (campañas) | Muestreos de campo / Laboratorio |
| Cobertura vegetal | % / ha | 0 - 100% por predio o zona | Multitemporal | Imágenes Satelitales (Landsat, Sentinel) |
| Caudal (Escorrentía) | m³/s o mm/año | Dinámico por microcuenca | Diaria / Mensual | Estaciones limnimétricas |
| Calidad del Aire (PM10, PM2.5, Gases) | µg/m³ | Variable según zona | Horaria / Anual | SVCA / Plataforma SISAIRE |

---

## Datos y fuentes

- **Geoespaciales y teledetección:** Imágenes satelitales (Landsat 8, Sentinel-2, ALOS PALSAR), Modelos Digitales de Elevación (DEM) y mapas de coberturas Corine Land Cover. Plataformas como MapBiomas.
- **Hidrometeorológicos:** Series de tiempo climáticas (precipitación, temperatura, humedad relativa) de las redes de monitoreo del IDEAM y CARs.
- **Socioeconómicos y prediales:** Datos demográficos del DANE, SISBEN, bases catastrales del IGAC y cartografía de resguardos o títulos mineros.
- **Biológicos y de especies:** Registros de ocurrencia de especies (ej. frailejones) analizados con modelamiento de distribución espacial.

---

## Indicadores y métricas oficiales

- **IRH (Índice de Retención y Regulación Hídrica):** Mide de 0 a 1 la capacidad de la cuenca para mantener caudales sostenidos (flujo base), producto de la interacción vegetación-suelo.
- **Índice de Aridez:** Fracción de la evapotranspiración potencial respecto a los excedentes hídricos; muestra si una zona es excedentaria o deficitaria de agua.
- **IUA (Índice de Uso del Agua):** Relación porcentual entre la demanda (agrícola, doméstica) y la oferta hídrica superficial.
- **IGC (Índice de Grado de Conservación):** Herramienta que califica porcentualmente la preservación de coberturas naturales, espacios del agua y degradación del suelo en un predio. Escala 1 a 5.
- **ICA (Índice de Calidad del Aire):** Escala adimensional (0-500) del SISAIRE para reportar riesgos a la salud por contaminación atmosférica.

---

## Normativa aplicable (Colombia)

- **Ley 1930 de 2018 (Ley de Páramos):** Dicta disposiciones para la gestión integral de páramos, prohibiendo actividades extractivas y ordenando planes de saneamiento y sustitución.
- **Ley 1450 de 2011 y Ley 1753 de 2015:** Restringieron actividades agropecuarias, hidrocarburos y minería en páramos delimitados. Establecen escala cartográfica obligatoria 1:25.000.
- **Resolución 886 de 2018 (MinAmbiente):** Adopta lineamientos de zonificación y directrices para los programas de sustitución y reconversión de actividades agropecuarias.
- **Resolución 963 de 2025 (IGAC):** Establece la metodología de valoración ambiental para avalúos de bienes inmuebles ubicados en páramos.

---

## Preguntas analíticas típicas

1. ¿Qué métodos de clasificación de imágenes satelitales logran mayor precisión para identificar la frontera entre coberturas paramunas y matrices agrícolas?
2. ¿Cómo se ven afectados los caudales de estiaje y el balance hídrico ante intervenciones antrópicas (pastoreo, cultivo de papa) en andosoles?
3. ¿Cuál es el porcentaje de área predial con coberturas naturales en zonas de rondas hídricas (nacimientos y cauces) que sustenta un avalúo favorable?
4. ¿Qué esquemas de reconversión agroecológica son viables a nivel de economía campesina tradicional, garantizando "bajo impacto"?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Relación Caldas-Lang para clasificación del clima en función del comportamiento altitudinal, térmico y pluviométrico.
- Estadísticas de cobertura por zona y por periodo temporal.

**Predictiva:**
- Modelación hidrológica e hidrogeológica: AvSWAT y WEAP para balances de agua (evapotranspiración, flujo base, escorrentía) frente a escenarios de intervención.
- Machine Learning (Random Forest, SVM, ANN) para clasificación supervisada de imágenes satelitales en mapeo multitemporal de coberturas.
- MaxEnt (Maximum Entropy) para distribución potencial de especies e indicadores paramunos.

**Espacial:**
- Interpolación thin plate smoothing spline para distribución espacial de variables climáticas.
- Análisis multitemporal de cobertura con Landsat/Sentinel (Corine Land Cover, MapBiomas).
- Mapeo de zonas de vida y transición de ecotonas.

---

## Actores institucionales

- **MADS:** Entidad rectora, responsable de promulgar la delimitación definitiva y expedir normas regulatorias.
- **Instituto Humboldt (IAvH):** Generador del área de referencia biogeofísica (Atlas de Páramos a escala 1:100.000) e insumos biológicos para la transición ecosistémica.
- **IDEAM:** Monitoreo de meteorología, hidrología y calidad del aire (SISAIRE); fija estándares de cobertura Corine Land Cover.
- **IGAC:** Suministra cartografía básica, levantamientos de suelos y diseña la valoración ambiental predial.
- **CARs:** Ejecutoras en territorio; formulan planes de manejo, zonificación y programas de sustitución con comunidades locales.

---

## Riesgos y sesgos en los datos

- **Escasez de estaciones de alta montaña:** Déficit y baja representatividad de instrumentos de medición en cotas altas genera grandes incertidumbres climáticas, requiriendo interpolaciones que no captan microclimas locales.
- **Nubosidad persistente:** En sensores ópticos (Landsat/Sentinel), la densa cobertura de nubes limita la obtención de píxeles libres de error, afectando las estimaciones de coberturas.
- **Discrepancias sociodemográficas:** Los censos del DANE, SISBEN y reportes locales frecuentemente difieren en cifras poblacionales sobre ocupantes en áreas restringidas del páramo.
- **Variables hidrológicas subestimadas:** La "precipitación horizontal" (niebla) y la evapotranspiración de especies paramunas rara vez se cuantifican mediante medición directa, apoyándose solo en ecuaciones teóricas.

---

## Glosario mínimo

- **Páramo:** Ecosistema de alta montaña ubicado entre el límite superior del Bosque Andino y el límite inferior glaciar, fundamental para la regulación hídrica.
- **Subpáramo (Páramo Bajo):** Franja de transición altitudinal con alta variabilidad biótica que conecta el bosque andino con el páramo abierto.
- **Corine Land Cover:** Metodología estandarizada adaptada a Colombia para clasificar las coberturas de la tierra a partir de imágenes de satélite.
- **Precipitación horizontal:** Captura e intercepción hídrica de la niebla o el rocío por parte de la vegetación (frailejones, musgos), clave para caudales base.
- **IRH:** Índice de Retención y Regulación Hídrica; capacidad del ecosistema suelo-planta de modular las precipitaciones para asegurar flujos constantes.
- **Andosol:** Suelos derivados de cenizas volcánicas, altamente porosos y oscuros, que retienen enormes cantidades de materia orgánica y humedad.
- **Zonificación:** División del territorio de páramo delimitado en áreas de preservación, restauración y uso sostenible.
- **Reconversión:** Transición de actividades productivas prohibidas y de alto impacto hacia prácticas ambientalmente amigables de bajo impacto.
- **Ecotono:** Zona de transición ecológica entre ecosistemas disímiles donde las especies se entrecruzan y compiten.
- **IGC:** Índice de Grado de Conservación; herramienta para tasar el estado biótico de bienes inmuebles para avalúo catastral-ambiental.
- **AvSWAT / WEAP:** Software de modelos hidrológicos para representar escenarios hídricos de precipitación y escorrentía.
- **SISAIRE:** Subsistema de Información sobre Calidad del Aire de Colombia, gestionado por IDEAM.
- **Saneamiento predial:** Proceso de clarificación jurídica y compra de predios estratégicos en páramos por parte del Estado para su conservación.
- **MaxEnt:** Algoritmo de máxima entropía usado para modelar la distribución potencial de especies en función de variables ambientales.
- **SINA:** Sistema Nacional Ambiental.

---

## Preguntas abiertas / oportunidades

- **Precipitación oculta:** Es perentorio trasladar la teoría hidrológica a estaciones de instrumentación reales en páramos para cuantificar exactamente el aporte volumétrico de la niebla.
- **Definición predial de "Bajo Impacto":** La normatividad requiere herramientas más robustas y métricas objetivas que califiquen cuándo la agricultura itinerante y la ganadería de baja carga cumplen el requisito de conservación de suelos y rondas.
- **Carbono en horizontes profundos:** Existe un vacío en los perfiles edafológicos; casi todas las mediciones de sumideros de carbono se concentran en los primeros 30 cm, obviando las vastas reservas en turberas paramunas.
- **Gestión socioambiental adaptativa:** Las CARs deben establecer planes y censos socioeconómicos locales que estandaricen y concilien metodologías entre diferentes departamentos.

---

## Referencias

- Fuentes del notebook: Ley 1930 de 2018, MADS, Instituto Humboldt (IAvH), IDEAM (SISAIRE), IGAC y CARs regionales.
