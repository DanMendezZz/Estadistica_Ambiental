# Cambio Climático — Contabilidad de Carbono, MRV y Modelado Predictivo de Emisiones

> **NotebookLM fuente:** https://notebooklm.google.com/notebook/c5870ed5-6bf0-4705-ad8c-738f2d6e439e
> **Última sincronización:** 2026-04-22
> **Responsable de la ficha:** Dan Méndez
> **Bloque:** B (transversal temática)
> **Alimenta a:** Oferta hídrica, páramos, humedales, gestión de riesgo, recurso hídrico

---

## Resumen ejecutivo

Colombia ha establecido un ambicioso marco de gobernanza climática para cumplir con su Contribución Determinada a Nivel Nacional (NDC), la cual busca reducir el 51% de las emisiones de Gases de Efecto Invernadero (GEI) para el 2030. El pilar operativo de esta meta es el Sistema de Monitoreo, Reporte y Verificación (MRV) y el Registro Nacional de Reducción de Emisiones (RENARE), plataformas diseñadas para contabilizar y registrar iniciativas de mitigación como REDD+, MDL y NAMAs.

Para garantizar la integridad ambiental y evitar la sobreestimación de créditos de carbono, el país se encuentra en una transición metodológica desde factores de emisión por defecto (Tier 1) hacia enfoques de alta resolución (Tier 2 y 3). Esta transición se apoya en inteligencia artificial y Machine Learning (Random Forest, XGBoost) capaces de cruzar datos satelitales y administrativos para predecir, validar y estandarizar los factores de emisión, asegurando transparencia frente a los mercados internacionales de carbono bajo el Acuerdo de París.

---

## Objetivos

- **Contabilidad precisa:** Cuantificar emisiones y remociones de GEI mediante un sistema MRV robusto que alimente el Inventario Nacional (INGEI).
- **Trazabilidad y transparencia:** Registrar iniciativas de mitigación en RENARE para evitar doble contabilidad de reducciones.
- **Validación predictiva:** Implementar modelos de Machine Learning para auditar y predecir factores de emisión, asegurando líneas base conservadoras (especialmente en REDD+).
- **Cumplimiento normativo:** Alinear proyectos de carbono nacionales con directrices del IPCC, estándares de certificación (Verra, Cercarbono) y la NDC de Colombia.

---

## Variables ambientales clave

| Variable | Unidad | Rango típico | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Densidad de Biomasa (Aérea/Subterránea) | tC/ha o tCO₂e/ha | 2.5 - 160 tC/ha | Anual / Bienal | IDEAM (SMByC), IFN, Copernicus |
| Pérdida/Ganancia Cobertura Arbórea | Hectáreas o % | Variable por proyecto | Anual | SMByC, Global Forest Watch |
| Factor de Emisión Red Eléctrica | kgCO₂e/kWh | ~0.24 - 0.38 | Anual | UPME, Balance Nacional de Energía |
| Consumo de Combustibles (Datos de Actividad) | Galones, m³, TJ | Depende del sector | Mensual / Anual | UPME (FECOC), Ecopetrol, SICOM |
| Humedad del Suelo / Temperatura | % / °C | Dinámico | Diaria / Mensual | Copernicus Climate Data Store |

---

## Datos y fuentes

- **Geoespaciales y teledetección:** Imágenes Landsat, mapas de cobertura boscosa y deforestación. Formatos: Raster, Shapefile, GeoJSON. Fuentes: SMByC (IDEAM), Global Forest Watch.
- **Tabulares estructurados (administrativos):** Registros de consumo energético, metadatos de proyectos (vintage year, estado de registro, estándar certificador). Formatos: CSV, bases de datos SQL/API. Fuentes: UPME, RENARE, CAD Trust.
- **Climatológicos e hidrológicos:** Variables biofísicas continuas que afectan sumideros de carbono y gases no-CO₂. Formatos: NetCDF, API REST. Fuentes: Copernicus C3S, IDEAM.

---

## Indicadores y métricas oficiales

- **Emisiones netas/brutas:** Medidas en toneladas de CO₂ equivalente (tCO₂e) por año.
- **Nivel de Referencia de Emisiones Forestales (NREF):** Línea base nacional o subnacional de deforestación histórica.
- **Potencial de Calentamiento Global (PCG):** Métrica para homogeneizar distintos GEI (CH₄, N₂O) a CO₂e.
- **Porcentaje de cumplimiento NDC:** Reducción porcentual respecto al tope máximo de 169.440 kt CO₂eq proyectado a 2030.

---

## Normativa aplicable (Colombia)

- **Ley 1753 de 2015 (Art. 175):** Crea el Registro Nacional de Reducción de Emisiones (RENARE).
- **Decreto 926 de 2017:** Establece el mecanismo de no causación del impuesto nacional al carbono.
- **Ley 1931 de 2018:** Directrices para la gestión del cambio climático y creación del SNICC.
- **Resolución 1447 de 2018 (MADS):** Reglamenta el sistema MRV, reglas para RENARE y mecanismos para evitar la doble contabilidad.
- **Resolución 418 de 2024 (MADS):** Transfiere la administración técnica de RENARE del IDEAM al MADS.

---

## Preguntas analíticas típicas

1. ¿Existe riesgo de sobreestimación (líneas base infladas) en créditos generados por proyectos REDD+ frente a la deforestación real medida satelitalmente?
2. ¿Qué variables climáticas y socioeconómicas son los principales impulsores de emisiones en el sector AFOLU y Transporte?
3. ¿Existe doble contabilidad o traslape geográfico entre diferentes iniciativas de mitigación registradas en RENARE?
4. ¿Las metodologías de cálculo (Tiers) usadas por los proyectos son consistentes con las directrices del IPCC y el NREF nacional?

---

## Métodos estadísticos sugeridos

**Descriptiva / inferencial:**
- Coeficiente de Información Máxima (MIC) para detectar relaciones no lineales complejas en ecosistemas.
- Simulaciones de Monte Carlo para análisis de incertidumbre en factores de emisión.

**Predictiva:**
- **Random Forest:** Ideal para AFOLU/REDD+ al cruzar variables espaciales de alta dimensionalidad (biomasa, pérdida forestal) sin sobreajuste crítico.
- **XGBoost / CatBoost:** Recomendado para NAMAs e industria con datos tabulares estructurados (consumos de combustibles, eficiencias térmicas).
- **LSTM:** Redes neuronales recurrentes para modelar dependencias temporales y estacionalidad del factor de la red eléctrica.
- **Modelos XAI (SHAP, LIME):** Para identificar qué variables determinan un factor de emisión específico, evitando cajas negras en la auditoría climática.

**Espacial:**
- Análisis de traslape y superposición geográfica entre proyectos de carbono (SIG en la nube).
- Mapas de deforestación y pérdida de cobertura mediante teledetección (SMByC, GFW).

---

## Actores institucionales

- **MADS:** Administrador de RENARE y rector de la política climática.
- **IDEAM:** Responsable del INGEI y del Sistema de Monitoreo de Bosques y Carbono (SMByC).
- **UPME:** Genera factores de emisión de combustibles y balances energéticos (FECOC).
- **Organismos de Validación y Verificación (OVV):** Verra, Gold Standard, Cercarbono, ColCX.

---

## Riesgos y sesgos en los datos

- **Inconsistencias de escala y unidades:** Errores en RENARE que confunden kg con tCO₂e, distorsionando la contabilidad agregada.
- **Sesgo de sobreestimación (over-crediting):** Tendencia de los desarrolladores a elegir metodologías o escenarios base que maximizan artificialmente los créditos REDD+ reclamados.
- **Mezcla de Tiers metodológicos:** Excesiva dependencia de factores globales por defecto (Tier 1) que no reflejan la realidad biofísica de Colombia.
- **Falta de interoperabilidad:** Riesgo de doble conteo si el registro nacional no se enlaza con plataformas globales (como CAD Trust).

---

## Glosario mínimo

- **AD (Datos de Actividad):** Medida cuantitativa de la actividad humana que genera emisiones (ej. galones de diésel o hectáreas deforestadas).
- **AFOLU:** Agricultura, Silvicultura y Otros Usos de la Tierra. Sector crítico en Colombia.
- **CAD Trust:** Plataforma global descentralizada para conectar registros de carbono e impedir la doble contabilidad.
- **Doble contabilidad:** Situación donde una misma reducción de GEI es usada más de una vez para demostrar el cumplimiento de metas.
- **EF (Factor de Emisión):** Coeficiente técnico que relaciona el dato de actividad con la cantidad de GEI liberado.
- **Fugas:** Emisiones de GEI desplazadas fuera de los límites de un proyecto como consecuencia de su implementación.
- **GEI:** Gases de Efecto Invernadero (CO₂, CH₄, N₂O, etc.).
- **INGEI:** Inventario Nacional de Emisiones y Absorciones de Gases de Efecto Invernadero.
- **MRV:** Sistema de Monitoreo, Reporte y Verificación.
- **NREF:** Nivel de Referencia de Emisiones Forestales; la línea base nacional de deforestación.
- **PCG:** Potencial de Calentamiento Global. Compara el impacto de cualquier GEI relativo al CO₂.
- **REDD+:** Reducción de Emisiones por Deforestación y Degradación forestal.
- **RENARE:** Registro Nacional de Reducción de las Emisiones y Remociones de GEI.
- **SHAP:** Enfoque de IA explicable (basado en teoría de juegos) para interpretar la importancia de variables en modelos predictivos.
- **Tier (Niveles IPCC):** Grado de complejidad metodológica (Tier 1: por defecto global; Tier 2: nacional; Tier 3: alta resolución espacial).

---

## Preguntas abiertas / oportunidades

- ¿Cómo automatizar la detección de superposiciones espaciales entre proyectos en RENARE usando SIG en la nube?
- ¿De qué manera el país puede regular la migración obligatoria de factores Tier 1 a Tier 2 o 3 para proyectos privados?
- ¿Cómo escalar el uso de Meta-Learning (MAML) para modelar proyectos de mitigación emergentes sin series históricas suficientes?
- Asegurar la plena conexión criptográfica de metadatos bajo el Artículo 6 del Acuerdo de París usando estándares como CAD Trust y AEF.

---

## Referencias

- Fuentes del notebook: documentos del MADS, IDEAM (INGEI, SMByC), UPME, Verra, Cercarbono y literatura de Machine Learning aplicado a contabilidad de carbono.
