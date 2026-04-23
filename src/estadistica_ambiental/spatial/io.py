"""I/O espacial: lectura de SHP, GeoPackage, GeoJSON, NetCDF y raster.

Complementa io/loaders.py para formatos con componente geométrico.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    import geopandas
    import xarray

logger = logging.getLogger(__name__)

_VECTOR_EXTS  = {".shp", ".gpkg", ".geojson", ".json"}
_RASTER_EXTS  = {".tif", ".tiff", ".nc", ".nc4"}


def load_vector(
    path: Union[str, Path],
    layer: Optional[str] = None,
    to_epsg: Optional[int] = None,
) -> "geopandas.GeoDataFrame":
    """Carga un archivo vectorial (SHP, GeoPackage, GeoJSON) a GeoDataFrame.

    Args:
        path: Ruta al archivo.
        layer: Capa específica (para GeoPackage con múltiples capas).
        to_epsg: Reprojecta al EPSG indicado tras la carga.
    """
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("pip install geopandas  (o [spatial])")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    kwargs = {"filename": path}
    if layer:
        kwargs["layer"] = layer

    gdf = gpd.read_file(**kwargs)
    logger.info("Cargado '%s': %d features | CRS=%s", path.name, len(gdf), gdf.crs)

    if to_epsg and gdf.crs and gdf.crs.to_epsg() != to_epsg:
        gdf = gdf.to_crs(epsg=to_epsg)
        logger.info("Reproyectado a EPSG:%d", to_epsg)

    return gdf


def load_raster(
    path: Union[str, Path],
    band: int = 1,
) -> dict:
    """Carga un raster GeoTIFF/NetCDF y devuelve datos + metadatos.

    Returns dict con: data (np.ndarray), transform, crs, shape, nodata.
    Requiere: rasterio.
    """
    try:
        import rasterio
    except ImportError:
        raise ImportError("pip install rasterio  (o [spatial])")

    path = Path(path)
    with rasterio.open(path) as src:
        data = src.read(band)
        result = {
            "data":      data,
            "transform": src.transform,
            "crs":       src.crs,
            "shape":     src.shape,
            "nodata":    src.nodata,
            "bounds":    src.bounds,
            "res":       src.res,
        }
    logger.info("Raster '%s': shape=%s | CRS=%s | nodata=%s",
                path.name, result["shape"], result["crs"], result["nodata"])
    return result


def load_netcdf_spatial(
    path: Union[str, Path],
    variable: Optional[str] = None,
    time_slice: Optional[slice] = None,
) -> "xarray.Dataset":
    """Carga un NetCDF como xarray Dataset (datos espacio-temporales).

    Útil para datos Copernicus, IDEAM o modelos climáticos.
    Requiere: xarray + netcdf4.
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError("pip install xarray netcdf4")

    path = Path(path)
    ds = xr.open_dataset(path)

    if variable:
        ds = ds[[variable]]

    if time_slice and "time" in ds.dims:
        ds = ds.sel(time=time_slice)

    logger.info("NetCDF '%s': variables=%s | dims=%s",
                path.name, list(ds.data_vars), dict(ds.dims))
    return ds


def list_gpkg_layers(path: Union[str, Path]) -> List[str]:
    """Lista las capas disponibles en un GeoPackage."""
    try:
        import fiona
    except ImportError:
        raise ImportError("pip install fiona")
    return fiona.listlayers(str(path))


def vector_to_parquet(
    gdf,
    output: Union[str, Path],
) -> Path:
    """Guarda un GeoDataFrame como GeoParquet (formato eficiente para SIG)."""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out)
    logger.info("GeoDataFrame guardado en: %s", out)
    return out
