"""Guardrails y supuestos metodológicos por línea temática (M-21).

Inserta una sección markdown común (estacionariedad, outliers, métricas,
walk-forward gap, residuos) más un bloque de notas específicas por dominio.
Idempotente: el marker `<!-- GUARDRAILS: <linea_key> -->` evita duplicados.
"""

from __future__ import annotations

from ._helpers import already_enriched, md

# Prefijo único para el marker — evita colisión con `<!-- ENRICHMENT: <key> -->`
# que ya usan los enrichments por dominio.
GUARDRAILS_MARKER_PREFIX = "GUARDRAILS"


def _guardrails_marker(linea_key: str) -> str:
    return f"<!-- {GUARDRAILS_MARKER_PREFIX}: {linea_key} -->"


def _is_guardrailed(cells: list, linea_key: str) -> bool:
    needle = _guardrails_marker(linea_key)
    return any(needle in "".join(c.get("source", "")) for c in cells)


# ---------------------------------------------------------------------------
# Mapeo línea → dominio (para el subtítulo de la sección específica)
# ---------------------------------------------------------------------------

DOMINIO_POR_LINEA: dict[str, str] = {
    "calidad_aire": "Calidad del aire",
    "oferta_hidrica": "Hidrología",
    "recurso_hidrico": "Hidrología / calidad del agua",
    "pomca": "Hidrología / cuencas",
    "pueea": "Hidrología / uso del recurso",
    "rondas_hidricas": "Hidrología / hidráulica",
    "humedales": "Hidrología / ecosistemas",
    "paramos": "Páramos / alta montaña",
    "cambio_climatico": "Cambio climático / MRV",
    "gestion_riesgo": "Gestión del riesgo",
    "areas_protegidas": "Áreas protegidas / GIS",
    "predios_conservacion": "Predios de conservación / GIS",
    "ordenamiento_territorial": "Ordenamiento territorial",
    "direccion_directiva": "Dirección directiva / KPIs",
    "sistemas_informacion_ambiental": "Sistemas de información",
    "geoespacial": "Geoespacial / interpolación",
}


# ---------------------------------------------------------------------------
# Notas específicas por línea (compactas — supuestos no-obvios del dominio)
# ---------------------------------------------------------------------------

ESPECIFICOS: dict[str, str] = {
    "calidad_aire": (
        "- **Frecuencia horaria → diaria:** la norma 24h (Res. 2254/2017) aplica al promedio diario; remuestrear antes de comparar contra umbral.\n"
        "- **ML > SARIMA univariado:** RF/XGBoost con lags `[1,2,3,7,14]` son producción real (RMSE≈3.7 µg/m³, HitRate ICA≈88%). SARIMAX compite sólo con meteorología completa.\n"
        "- **Recall_gt55:** evaluar la detección de episodios críticos (>55 µg/m³) — diferenciador clave (XGBoost ~15%, SARIMA ~0%).\n"
        "- **Lag ENSO = 2 meses** (`ENSO_LAG_MESES['calidad_aire']`)."
    ),
    "oferta_hidrica": (
        "- **NSE / KGE primarias:** R² no es confiable en series con alta variabilidad estacional.\n"
        "- **Lag ENSO = 4 meses** (cuencas Magdalena-Cauca, respuesta hidrológica rezagada).\n"
        "- **Calibración / validación:** mínimo 70/30 split sobre años hidrológicos completos.\n"
        "- **Caudales máximos / mínimos:** preservar — son la señal de eventos críticos (creciente, estiaje)."
    ),
    "recurso_hidrico": (
        "- **NSE / KGE primarias** (igual que oferta hídrica).\n"
        "- **Calidad de agua multivariada:** ICA combina pH, OD, conductividad, turbiedad, DBO5, coliformes — no analizar variables aisladamente.\n"
        "- **Lag ENSO = 3 meses** (calidad responde a precipitación con retardo).\n"
        "- **Normas:** `NORMA_AGUA_POTABLE` (Res. 2115/2007), `NORMA_VERTIMIENTOS` (Res. 631/2015)."
    ),
    "pomca": (
        "- **Indicadores ENA:** IUA, IRH, IACAL, ICA agregados a la cuenca/subcuenca.\n"
        "- **Lag ENSO = 4 meses** (alineado con oferta hídrica).\n"
        "- **Escalas espaciales:** subcuenca → microcuenca → predio — agregar respetando jerarquía."
    ),
    "pueea": (
        "- **Demanda vs. oferta:** comparar contra `IUA_THRESHOLDS` (% del recurso disponible que se usa).\n"
        "- **Lag ENSO = 3 meses.**\n"
        "- **Proyección de demanda:** modelos exponenciales/logísticos en lugar de ARIMA puro."
    ),
    "rondas_hidricas": (
        "- **Distribuciones extremas:** Gumbel / Pearson III sobre caudales máximos anuales — asumir T=2,5,10,25,50,100 años.\n"
        "- **Lag ENSO = 3 meses.**\n"
        "- **Validación con LiDAR / topografía** cuando esté disponible — la ronda hídrica es geomorfológica, no sólo estadística."
    ),
    "humedales": (
        "- **Hidroperiodo:** ciclo anual de inundación; estacionalidad fuerte → SARIMA o Prophet superan a ML sin lags estacionales.\n"
        "- **Lag ENSO = 3 meses.**\n"
        "- **Inventario nacional:** Resolución 157/2004 — ~30,781 humedales registrados en RUNAP/SIAC."
    ),
    "paramos": (
        "- **Gradiente Caldas-Lang:** clasificación bioclimática por altitud (T°, P) — usar para validar coherencia de muestras.\n"
        "- **Lag ENSO = 2 meses** (respuesta rápida a precipitación en alta montaña).\n"
        "- **Variabilidad espacial alta:** kriging con variograma exponencial; verificar Moran's I antes.\n"
        "- **Cobertura:** delimitación 1:25.000 (Atlas Páramos IAvH)."
    ),
    "cambio_climatico": (
        "- **MRV (Medición, Reporte, Verificación):** trazabilidad obligatoria por compromisos NDC.\n"
        "- **Agregados anuales:** los datos diarios introducen ruido — para tendencias decadales usar promedios anuales.\n"
        "- **Lag ENSO = 0** (variable de contexto, sin lag específico).\n"
        "- **Tendencias significativas:** requieren ≥ 30 años (criterio IPCC) — Mann-Kendall con muestras menores es ilustrativo, no concluyente."
    ),
    "gestion_riesgo": (
        "- **Eventos extremos:** distribuciones de cola pesada (GEV / GPD), no normales — Mann-Kendall sobre máximos anuales.\n"
        "- **Lag ENSO = 1 mes** (respuesta rápida en inundaciones / deslizamientos).\n"
        "- **Umbrales determinísticos:** `AMENAZA_PRECIPITACION` (Ley 1523/2012, Decreto 1807/2014).\n"
        "- **Período de retorno** es la métrica de gestión (BP-7) — convertir % excedencia a años."
    ),
    "areas_protegidas": (
        "- **No-serie temporal pura:** indicadores espaciales (cobertura, deforestación, fragmentación) — RF/XGBoost sobre features GIS, no ARIMA.\n"
        "- **Validación cruzada espacial** (no temporal) — la autocorrelación espacial puede inflar métricas.\n"
        "- **Categorías RUNAP:** SINAP, regional, municipal, sociedad civil — agregar respetando categoría."
    ),
    "predios_conservacion": (
        "- **GIS-driven:** indicadores de cobertura y conectividad ecológica — Moran's I antes de modelar.\n"
        "- **No-modelado predictivo de series:** los predios cambian de estado en eventos discretos (compra, restauración)."
    ),
    "ordenamiento_territorial": (
        "- **Largo plazo (POT/POMCA):** horizonte 12 años; tendencias decadales > variabilidad anual.\n"
        "- **Lag ENSO = 6 meses** (respuesta lenta del territorio a forzamiento climático).\n"
        "- **Escalas espaciales:** veredal → municipal → departamental — no mezclar."
    ),
    "direccion_directiva": (
        "- **KPIs ejecutivos:** indicadores agregados — series mensuales/trimestrales, no diarias/horarias.\n"
        "- **Comparabilidad inter-período:** usar misma metodología en todas las mediciones; documentar cambios.\n"
        "- **Reporting trimestral / anual** — evitar conclusiones operativas sobre datos de gestión."
    ),
    "sistemas_informacion_ambiental": (
        "- **Metadata-driven:** énfasis en calidad de datos (completeness, freshness, lineage) — no modelado predictivo.\n"
        "- **Indicadores de cobertura:** % registros con metadatos completos, % datasets actualizados, MTBF de pipelines."
    ),
    "geoespacial": (
        "- **Autocorrelación espacial:** Moran's I antes de modelar regresión sobre datos geográficos.\n"
        "- **Kriging:** verificar variograma teórico (esférico / exponencial / gaussiano) — el ajuste por OLS al variograma empírico no es trivial.\n"
        "- **CRS coherente:** EPSG:4326 (WGS84) para análisis general, EPSG:3116 (MAGNA-SIRGAS Origen Bogotá) para Colombia continental."
    ),
}


_PLANTILLA = """## 7b. Guardrails y supuestos metodológicos
{marker}

> **Antes de publicar resultados**, verificar que se cumplen los supuestos clave del flujo. Esta sección lista los más comunes y los específicos de la línea.

### Supuestos comunes (todas las líneas)

- **Estacionariedad (ADR-004):** ADF + KPSS deben coincidir antes de aplicar ARIMA. Si discrepan, diferenciar conservadoramente o usar modelos no-ARIMA (Prophet, ML).
- **Outliers (ADR-002):** los picos ambientales son señal real (eventos, episodios). No aplicar clipping automático — sólo `preprocessing/outliers.py` opt-in y documentado.
- **Métrica primaria (ADR-003):** RMSLE NO en variables que pueden ser negativas o cero. Usar MAE + sMAPE (o NSE / KGE en hidrología) como default.
- **Tamaño muestral mínimo:** ARIMA requiere ≥ 36 observaciones; STL anual con datos diarios, ≥ 2 ciclos completos.
- **Residuos (post-fit):** verificar normalidad (Jarque-Bera) e independencia (Ljung-Box, lag = 12). Residuos correlacionados → modelo subespecificado.
- **Walk-forward con gap (BP-1):** series con ACF ≥ 0.7 inflan R². Usar `gap ≥ horizonte` en `walk_forward()`.
- **Normas oficiales:** usar `config.NORMA_*` y `config.*_THRESHOLDS` — nunca umbrales hardcodeados en el notebook (ADR-005).

### Supuestos específicos — {dominio}

{especificos}

### Antes de presentar a la autoridad ambiental

- Reportar intervalos de confianza, no sólo el punto estimado.
- Documentar el período de los datos, los gaps y el método de imputación usado.
- Registrar decisiones metodológicas no triviales en `docs/decisiones.md` (ADRs).
"""


_CLOSERS = ("## 8. Conclusiones", "## 8. Reporte final", "## 9. Cómo adaptar")


def _find_target_index(cells: list) -> int:
    """Índice donde insertar la sección de guardrails (antes del primer closer)."""
    for i, c in enumerate(cells):
        if c["cell_type"] != "markdown":
            continue
        src_i = "".join(c.get("source", ""))
        if any(closer in src_i for closer in _CLOSERS):
            return i
    return len(cells)


def _find_existing_guardrails_idx(cells: list, linea_key: str) -> int:
    """Índice de la celda guardrails existente (-1 si no hay)."""
    needle = _guardrails_marker(linea_key)
    for i, c in enumerate(cells):
        if needle in "".join(c.get("source", "")):
            return i
    return -1


def apply_guardrails(linea_key: str, nb: dict) -> bool:
    """Inserta la sección de guardrails antes del primer closer (idempotente).

    Si ya existe pero está mal ubicada (posterior a un closer), la mueve.

    Returns:
        True siempre (operación idempotente).
    """
    cells: list = nb["cells"]
    target = _find_target_index(cells)
    existing = _find_existing_guardrails_idx(cells, linea_key)

    if existing >= 0:
        # Ya está. Verificar si está bien ubicada (justo antes de un closer).
        if existing == target - 1 or existing == target:
            return True
        # Mala ubicación: removerla; el target se recalcula tras la remoción.
        cells.pop(existing)
        target = _find_target_index(cells)

    dominio = DOMINIO_POR_LINEA.get(linea_key, "General")
    especificos = ESPECIFICOS.get(
        linea_key,
        "- (sin notas específicas para esta línea — verificar supuestos comunes y consultar `docs/fuentes/<linea>.md`)",
    )
    src = _PLANTILLA.format(
        marker=_guardrails_marker(linea_key),
        dominio=dominio,
        especificos=especificos,
    )
    cells.insert(target, md(src))
    return True


__all__ = ["apply_guardrails", "DOMINIO_POR_LINEA", "ESPECIFICOS"]
