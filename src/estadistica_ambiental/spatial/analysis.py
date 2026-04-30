"""Análisis espacial: traslapes poligonales y estadísticas zonales.

Operaciones fundamentales para análisis de iniciativas GEI, áreas protegidas
y agregación de variables ambientales por unidades político-administrativas.
"""

from __future__ import annotations

import logging
from typing import List, Union

import numpy as np

logger = logging.getLogger(__name__)

_PROJ_COLOMBIA = 9377  # CTM12 — cálculo preciso de áreas en Colombia (Res. IGAC 370/2021)


def intersection_area(
    gdf1,
    gdf2,
    id_col1: str,
    id_col2: str,
) -> "geopandas.GeoDataFrame":
    """Calcula áreas de traslape entre dos capas poligonales.

    Reprojecta a CTM12 (EPSG:9377) para precisión métrica en Colombia.
    Usa overlay vectorizado de geopandas (no bucle anidado).

    Args:
        gdf1: Primera capa poligonal (ej: iniciativas REDD+).
        gdf2: Segunda capa poligonal (ej: áreas protegidas, páramos).
        id_col1: Columna identificadora única en gdf1.
        id_col2: Columna identificadora única en gdf2.

    Returns:
        GeoDataFrame con columnas: id_col1, id_col2, intersection_area_m2,
        pct_of_<id_col1>, pct_of_<id_col2>, geometry (CRS de gdf1).
    """
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("pip install geopandas shapely  (o [spatial])")

    if gdf1.crs != gdf2.crs:
        gdf2 = gdf2.to_crs(gdf1.crs)

    n1, n2 = len(gdf1), len(gdf2)
    if n1 * n2 > 100_000:
        logger.warning(
            "intersection_area: %d × %d = %d combinaciones potenciales — puede ser lento.",
            n1, n2, n1 * n2,
        )

    gdf1_proj = gdf1[[id_col1, gdf1.geometry.name]].to_crs(epsg=_PROJ_COLOMBIA)
    gdf2_proj = gdf2[[id_col2, gdf2.geometry.name]].to_crs(epsg=_PROJ_COLOMBIA)

    areas1 = gdf1_proj.set_index(id_col1).geometry.area
    areas2 = gdf2_proj.set_index(id_col2).geometry.area

    overlay = gpd.overlay(gdf1_proj, gdf2_proj, how="intersection", keep_geom_type=False)

    if overlay.empty:
        logger.warning("No se encontraron traslapes entre las dos capas.")
        return gpd.GeoDataFrame(
            columns=[id_col1, id_col2, "intersection_area_m2",
                     f"pct_of_{id_col1}", f"pct_of_{id_col2}"],
            geometry=[],
            crs=gdf1.crs,
        )

    overlay["intersection_area_m2"] = overlay.geometry.area
    overlay[f"pct_of_{id_col1}"] = overlay.apply(
        lambda r: (r["intersection_area_m2"] / areas1.get(r[id_col1], np.nan)) * 100, axis=1
    )
    overlay[f"pct_of_{id_col2}"] = overlay.apply(
        lambda r: (r["intersection_area_m2"] / areas2.get(r[id_col2], np.nan)) * 100, axis=1
    )

    logger.info(
        "intersection_area: %d traslapes encontrados entre '%s' y '%s'",
        len(overlay), id_col1, id_col2,
    )
    return overlay.to_crs(gdf1.crs)


def zonal_statistics(
    raster_path: Union[str],
    zones_gdf,
    zone_id_col: str,
    stats: List[str] = None,
) -> "geopandas.GeoDataFrame":
    """Agrega valores de raster por zonas poligonales (municipios, departamentos).

    Equivalente a QGIS "Zonal Statistics" o ArcGIS "Zonal Statistics as Table".
    Caso de uso típico: emisiones GEI o deforestación por municipio/departamento.

    Args:
        raster_path: Ruta a GeoTIFF (deforestación, emisiones, NDVI, etc.)
        zones_gdf: GeoDataFrame con polígonos de zonas.
        zone_id_col: Columna de identificación única (ej: 'CODIGO_DANE').
        stats: Estadísticas a calcular. Default: ['mean', 'sum', 'std', 'min', 'max'].
            Opciones adicionales: 'count', 'median'.

    Returns:
        GeoDataFrame original con columnas adicionales para cada estadística.
    """
    if stats is None:
        stats = ["mean", "sum", "std", "min", "max"]

    try:
        import rasterio
        from rasterio.mask import mask as rmask
    except ImportError:
        raise ImportError("pip install rasterio  (o [spatial])")

    _stat_funcs = {
        "mean": np.nanmean,
        "sum": np.nansum,
        "std": np.nanstd,
        "min": np.nanmin,
        "max": np.nanmax,
        "count": lambda x: float(np.sum(~np.isnan(x))),
        "median": np.nanmedian,
    }
    invalid = set(stats) - set(_stat_funcs)
    if invalid:
        raise ValueError(f"Estadísticas no soportadas: {invalid}. Opciones: {list(_stat_funcs)}")

    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        nodata = src.nodata

    zones = zones_gdf.to_crs(raster_crs) if zones_gdf.crs != raster_crs else zones_gdf.copy()

    stat_results: dict = {zone_id_col: [], **{s: [] for s in stats}}

    for _, zone_row in zones.iterrows():
        zone_id = zone_row[zone_id_col]
        stat_results[zone_id_col].append(zone_id)

        try:
            with rasterio.open(raster_path) as src:
                clipped, _ = rmask(src, [zone_row.geometry], crop=True)
            values = clipped.astype(float).ravel()
            if nodata is not None:
                values = values[values != nodata]
            values = values[~np.isnan(values)]
        except Exception as exc:
            logger.debug("Zona '%s' sin datos en raster: %s", zone_id, exc)
            values = np.array([])

        for s in stats:
            stat_results[s].append(_stat_funcs[s](values) if len(values) > 0 else np.nan)

    import pandas as pd
    stats_df = pd.DataFrame({k: v for k, v in stat_results.items()})
    result = zones_gdf.merge(stats_df, on=zone_id_col, how="left")

    logger.info("zonal_statistics: %d zonas | stats=%s | raster='%s'",
                len(zones_gdf), stats, raster_path)
    return result
