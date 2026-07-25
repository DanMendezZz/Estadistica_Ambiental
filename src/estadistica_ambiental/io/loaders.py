"""
Ingesta multiformato para datos ambientales.
Soporta: CSV, Excel, Parquet, NetCDF, Shapefile / GeoPackage / GeoJSON.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

_SUPPORTED = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".nc", ".shp", ".gpkg", ".geojson"}


def load(
    path: Union[str, Path],
    date_col: Optional[str] = None,
    **kwargs,
) -> pd.DataFrame:
    """Carga un archivo ambiental detectando el formato por extensión.

    Para Shapefile / GeoPackage / GeoJSON devuelve un GeoDataFrame
    (requiere geopandas).  Para el resto, un DataFrame de pandas.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    ext = path.suffix.lower()
    if ext not in _SUPPORTED:
        raise ValueError(f"Formato no soportado: '{ext}'. Soportados: {sorted(_SUPPORTED)}")

    dispatch = {
        ".csv": load_csv,
        ".tsv": lambda p, **kw: load_csv(p, sep="\t", **kw),
        ".xlsx": load_excel,
        ".xls": load_excel,
        ".parquet": load_parquet,
        ".nc": load_netcdf,
        ".shp": load_shapefile,
        ".gpkg": load_shapefile,
        ".geojson": load_shapefile,
    }

    return dispatch[ext](path, date_col=date_col, **kwargs)


def load_csv(
    path: Union[str, Path],
    date_col: Optional[str] = None,
    sep: str = ",",
    encoding: Optional[str] = None,
    **kwargs,
) -> pd.DataFrame:
    """Carga CSV con detección automática de encoding si no se especifica."""
    path = Path(path)

    if encoding is None:
        encoding = _detect_encoding(path)

    df = pd.read_csv(path, sep=sep, encoding=encoding, **kwargs)
    df = _parse_dates(df, date_col)
    _log_summary(path, df)
    return df


def load_excel(
    path: Union[str, Path],
    date_col: Optional[str] = None,
    sheet_name: Union[str, int] = 0,
    **kwargs,
) -> pd.DataFrame:
    """Carga archivo Excel (.xlsx / .xls)."""
    path = Path(path)
    df = pd.read_excel(path, sheet_name=sheet_name, **kwargs)
    df = _parse_dates(df, date_col)
    _log_summary(path, df)
    return df


def load_parquet(
    path: Union[str, Path],
    date_col: Optional[str] = None,
    **kwargs,
) -> pd.DataFrame:
    """Carga archivo Parquet."""
    path = Path(path)
    df = pd.read_parquet(path, **kwargs)
    df = _parse_dates(df, date_col)
    _log_summary(path, df)
    return df


def load_netcdf(
    path: Union[str, Path],
    variable: Optional[str] = None,
    date_col: str = "time",
    lat_col: str = "lat",
    lon_col: str = "lon",
    **kwargs,
) -> pd.DataFrame:
    """Carga NetCDF y aplana a DataFrame de pandas.

    Si `variable` es None, carga todas las variables del archivo.
    Requiere: netCDF4 o h5netcdf (instalar con pip install netcdf4).
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError("xarray es necesario para leer NetCDF: pip install xarray netcdf4")

    path = Path(path)
    ds = xr.open_dataset(path, **kwargs)

    if variable is not None:
        ds = ds[[variable]]

    df = ds.to_dataframe().reset_index()
    df = _parse_dates(df, date_col)
    _log_summary(path, df)
    return df


def load_shapefile(
    path: Union[str, Path],
    date_col: Optional[str] = None,
    **kwargs,
):
    """Carga Shapefile, GeoPackage o GeoJSON a GeoDataFrame.

    Requiere: geopandas (pip install geopandas).
    """
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError(
            "geopandas es necesario para leer archivos espaciales: pip install geopandas"
        )

    path = Path(path)
    gdf = gpd.read_file(path, **kwargs)

    if date_col and date_col in gdf.columns:
        gdf[date_col] = pd.to_datetime(gdf[date_col], errors="coerce")
        gdf = gdf.sort_values(date_col).reset_index(drop=True)

    _log_summary(path, gdf)
    return gdf


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _detect_encoding(path: Path) -> str:
    """Detecta encoding de un archivo de texto usando chardet si está disponible."""
    try:
        import chardet

        raw = path.read_bytes()
        result = chardet.detect(raw[:50_000])
        encoding = result.get("encoding") or "utf-8"
        logger.debug(
            "Encoding detectado para %s: %s (confianza %.0f%%)",
            path.name,
            encoding,
            (result.get("confidence") or 0) * 100,
        )
        return encoding
    except ImportError:
        return "utf-8"


def _parse_dates(df: pd.DataFrame, date_col: Optional[str]) -> pd.DataFrame:
    """Parsea la columna de fechas y ordena el DataFrame cronológicamente."""
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        n_invalid = df[date_col].isna().sum()
        if n_invalid:
            logger.warning("%d fechas no parseables en columna '%s'", n_invalid, date_col)
        df = df.sort_values(date_col).reset_index(drop=True)
    elif date_col:
        logger.warning("Columna de fecha '%s' no encontrada en el archivo", date_col)
    return df


def _log_summary(path: Path, df: pd.DataFrame) -> None:
    """Registra un resumen básico del archivo cargado."""
    n_rows, n_cols = df.shape
    missing_pct = df.isnull().mean().mean() * 100
    logger.info(
        "Cargado '%s': %d filas × %d columnas | %.1f%% faltantes",
        path.name,
        n_rows,
        n_cols,
        missing_pct,
    )
