"""Enrichments por línea temática integrados a build_notebooks.py.

Cada submódulo (uno por línea) expone una función `apply(nb)` que modifica
in-place el dict del notebook (`{"cells": [...], ...}`) e inserta celdas
de enriquecimiento de dominio (IRH, NDC, AVR, BMWP, ICA, etc.).

Las funciones son **idempotentes**: si detectan el marker de enriquecimiento
ya presente en `nb["cells"]`, no hacen nada.

Diseño:
    ENRICHMENTS: dict[linea_key, callable]   # mapping pública
    apply_enrichments(linea_key, nb)         # punto de entrada
"""

from __future__ import annotations

from typing import Callable, Dict

from . import (
    areas_protegidas,
    cambio_climatico,
    direccion_directiva,
    geoespacial,
    gestion_riesgo,
    humedales,
    oferta_hidrica,
    ordenamiento_territorial,
    paramos,
    pomca,
    predios_conservacion,
    pueea,
    recurso_hidrico,
    rondas_hidricas,
    sistemas_informacion_ambiental,
)
from ._guardrails import apply_guardrails  # noqa: F401  (M-21)

ENRICHMENTS: Dict[str, Callable[[dict], None]] = {
    "areas_protegidas": areas_protegidas.apply,
    "cambio_climatico": cambio_climatico.apply,
    "direccion_directiva": direccion_directiva.apply,
    "geoespacial": geoespacial.apply,
    "gestion_riesgo": gestion_riesgo.apply,
    "humedales": humedales.apply,
    "oferta_hidrica": oferta_hidrica.apply,
    "ordenamiento_territorial": ordenamiento_territorial.apply,
    "paramos": paramos.apply,
    "pomca": pomca.apply,
    "predios_conservacion": predios_conservacion.apply,
    "pueea": pueea.apply,
    "recurso_hidrico": recurso_hidrico.apply,
    "rondas_hidricas": rondas_hidricas.apply,
    "sistemas_informacion_ambiental": sistemas_informacion_ambiental.apply,
}


def apply_enrichments(linea_key: str, nb: dict) -> bool:
    """Aplica el enrichment correspondiente a `linea_key` sobre `nb` (in-place).

    Returns:
        True si se aplicó (o ya estaba aplicado idempotentemente),
        False si no hay enrichment registrado para esa línea.
    """
    fn = ENRICHMENTS.get(linea_key)
    if fn is None:
        return False
    fn(nb)
    return True


__all__ = ["ENRICHMENTS", "apply_enrichments", "apply_guardrails"]
