"""Autocorrelación espacial: I de Moran, C de Geary.

Previo a modelos espaciales para verificar que existe dependencia espacial.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def morans_i(
    gdf,
    value_col: str,
    weight_type: str = "queen",
    significance: float = 0.05,
) -> dict:
    """Índice de Moran global para autocorrelación espacial.

    Requiere: pip install pysal esda libpysal (incluido en [spatial]).

    H0: distribución espacialmente aleatoria.
    I > 0 → clustering; I < 0 → dispersión.
    """
    try:
        import libpysal
        from esda.moran import Moran
    except ImportError:
        raise ImportError("pip install pysal esda libpysal  (o [spatial])")

    if weight_type == "queen":
        w = libpysal.weights.Queen.from_dataframe(gdf)
    elif weight_type == "rook":
        w = libpysal.weights.Rook.from_dataframe(gdf)
    else:
        w = libpysal.weights.KNN.from_dataframe(gdf, k=int(weight_type.split("k")[1]))

    w.transform = "r"
    moran = Moran(gdf[value_col], w)

    return {
        "I":           round(float(moran.I), 4),
        "EI":          round(float(moran.EI), 4),
        "p_norm":      round(float(moran.p_norm), 6),
        "p_sim":       round(float(moran.p_sim), 6),
        "z_norm":      round(float(moran.z_norm), 4),
        "significant": float(moran.p_sim) < significance,
        "interpretation": _interpret_moran(float(moran.I), float(moran.p_sim), significance),
    }


def _interpret_moran(moran_i: float, p: float, alpha: float) -> str:
    if p >= alpha:
        return "distribución espacialmente aleatoria (no significativo)"
    if moran_i > 0:
        return "clustering espacial positivo (valores similares agrupados)"
    return "dispersión espacial (valores distintos adyacentes)"


def local_morans_i(gdf, value_col: str, weight_type: str = "queen"):
    """LISA — Moran local para identificar clusters y outliers espaciales.

    Requiere: esda.
    Agrega columnas 'lisa_q' (cuadrante) y 'lisa_p' al GeoDataFrame.
    """
    try:
        import libpysal
        from esda.moran import Moran_Local
    except ImportError:
        raise ImportError("pip install pysal esda libpysal")

    w = libpysal.weights.Queen.from_dataframe(gdf)
    w.transform = "r"
    lisa = Moran_Local(gdf[value_col], w)

    result = gdf.copy()
    result["lisa_q"] = lisa.q        # 1=HH, 2=LH, 3=LL, 4=HL
    result["lisa_p"] = lisa.p_sim
    result["lisa_sig"] = lisa.p_sim < 0.05
    return result
