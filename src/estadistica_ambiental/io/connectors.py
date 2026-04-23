"""Conectores a fuentes de datos ambientales colombianas públicas.

Provee acceso estandarizado a APIs y portales de datos abiertos usados en las
16 líneas temáticas. Cada función devuelve un DataFrame con columnas normalizadas
compatibles con el pipeline del repositorio.

Fuentes incluidas:
- OpenAQ: calidad del aire (PM2.5, PM10, O3, NO2, SO2, CO)
- RMCAB: Red de Monitoreo de Calidad del Aire de Bogotá
- SIATA: Sistema de Alerta Temprana de Medellín/Antioquia
- IDEAM DHIME: datos hidrometeorológicos (instrucciones de acceso manual)
- SMByC: alertas de deforestación IDEAM (instrucciones de acceso)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAQ — Calidad del Aire (API v3, gratuita)
# Documentación: https://docs.openaq.org/
# Cubre estaciones RMCAB (Bogotá), SIATA (Medellín), IDEAM y otras CARs
# ---------------------------------------------------------------------------

_OPENAQ_API = "https://api.openaq.org/v3"
_OPENAQ_HEADERS = {"Accept": "application/json"}


def load_openaq(
    location_id: Optional[int] = None,
    location_name: Optional[str] = None,
    country: str = "CO",
    parameter: str = "pm25",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10000,
) -> pd.DataFrame:
    """Descarga mediciones de calidad del aire desde OpenAQ v3.

    Args:
        location_id: ID numérico de la estación en OpenAQ (preferido).
        location_name: Nombre de la estación (búsqueda aproximada si no hay ID).
        country: Código ISO de país (default 'CO').
        parameter: Variable a descargar ('pm25', 'pm10', 'o3', 'no2', 'so2', 'co').
        date_from: Fecha inicio 'YYYY-MM-DD' (default: últimos 30 días).
        date_to: Fecha fin 'YYYY-MM-DD' (default: hoy).
        limit: Máximo de registros por consulta.

    Returns:
        DataFrame con columnas: fecha, estacion, parametro, valor, unidad, lat, lon.

    Ejemplos de location_id para Colombia (OpenAQ):
        - 225433 → Estación Kennedy, RMCAB Bogotá
        - 64510  → Estación El Poblado, SIATA Medellín
        Buscar IDs en: https://explore.openaq.org/
    """
    try:
        import requests
    except ImportError:
        logger.error("Instalar 'requests': pip install requests")
        return pd.DataFrame()

    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    if location_id:
        url = f"{_OPENAQ_API}/locations/{location_id}/measurements"
        params = {
            "parameter_id": _openaq_param_id(parameter),
            "date_from": f"{date_from}T00:00:00Z",
            "date_to":   f"{date_to}T23:59:59Z",
            "limit": limit,
        }
    else:
        url = f"{_OPENAQ_API}/measurements"
        params = {
            "countries_id": 170,  # Colombia
            "parameters_id": _openaq_param_id(parameter),
            "date_from": f"{date_from}T00:00:00Z",
            "date_to":   f"{date_to}T23:59:59Z",
            "limit": limit,
        }

    try:
        all_data: list = []
        page = 1
        while True:
            params["page"] = page
            resp = requests.get(url, headers=_OPENAQ_HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            body    = resp.json()
            results = body.get("results", [])
            all_data.extend(results)
            total = body.get("meta", {}).get("found", len(all_data))
            logger.info("OpenAQ pág. %d: %d/%d registros descargados", page, len(all_data), total)
            if len(results) < limit:
                break
            page += 1
        data = all_data
        if not data:
            logger.warning("OpenAQ: sin datos para los parámetros solicitados.")
            return pd.DataFrame()
        rows = []
        for m in data:
            rows.append({
                "fecha":     pd.to_datetime(m.get("datetime", {}).get("utc"), utc=True),
                "estacion":  m.get("locationId"),
                "parametro": parameter,
                "valor":     m.get("value"),
                "unidad":    m.get("unit", "µg/m³"),
                "lat":       m.get("coordinates", {}).get("latitude"),
                "lon":       m.get("coordinates", {}).get("longitude"),
            })
        df = pd.DataFrame(rows)
        df["fecha"] = pd.to_datetime(df["fecha"], utc=True).dt.tz_localize(None)
        logger.info("OpenAQ: %d registros descargados (%s, %s → %s)", len(df), parameter, date_from, date_to)
        return df.sort_values("fecha").reset_index(drop=True)
    except Exception as e:
        logger.error("Error consultando OpenAQ: %s", e)
        return pd.DataFrame()


def _openaq_param_id(param: str) -> int:
    """Mapea nombre de parámetro a ID interno de OpenAQ v3."""
    ids = {"pm25": 2, "pm10": 1, "o3": 3, "no2": 5, "so2": 9, "co": 4, "bc": 12}
    return ids.get(param.lower(), 2)


# ---------------------------------------------------------------------------
# RMCAB — Red de Monitoreo de Calidad del Aire de Bogotá
# Portal: http://rmcab.ambientebogota.gov.co/
# API REST disponible (requiere token gratuito de la SDA)
# ---------------------------------------------------------------------------

def load_rmcab(
    station: str,
    variable: str = "PM25",
    date_from: str = "2024-01-01",
    date_to: Optional[str] = None,
    token: Optional[str] = None,
) -> pd.DataFrame:
    """Descarga datos de calidad del aire desde RMCAB Bogotá.

    Requiere token gratuito de la Secretaría Distrital de Ambiente (SDA).
    Solicitar en: http://rmcab.ambientebogota.gov.co/

    Args:
        station: Código de la estación (ej. 'Kennedy', 'Usme', 'Fontibon').
        variable: Variable ('PM25', 'PM10', 'O3', 'NO2', 'SO2', 'CO').
        date_from: Fecha inicio 'YYYY-MM-DD'.
        date_to: Fecha fin (default: hoy).
        token: Token de acceso SDA.

    Returns:
        DataFrame con columnas: fecha, estacion, variable, valor, unidad.

    Nota:
        Sin token, los datos pueden consultarse manualmente en:
        http://rmcab.ambientebogota.gov.co/Report/stationreport
    """
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

    if token is None:
        logger.warning(
            "RMCAB requiere token SDA. Descarga manual en: "
            "http://rmcab.ambientebogota.gov.co/Report/stationreport\n"
            "Estación: %s | Variable: %s | %s → %s",
            station, variable, date_from, date_to,
        )
        return pd.DataFrame(columns=["fecha", "estacion", "variable", "valor", "unidad"])

    try:
        import requests
    except ImportError:
        logger.error("Instalar 'requests': pip install requests")
        return pd.DataFrame()

    url = "http://rmcab.ambientebogota.gov.co/api/Consultation/data"
    params = {
        "station": station,
        "variable": variable,
        "dateIni": date_from,
        "dateEnd": date_to,
        "token": token,
    }
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df.rename(columns={"date": "fecha", "value": "valor"})
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["estacion"] = station
        df["variable"] = variable
        df["unidad"] = "µg/m³" if variable in ("PM25", "PM10", "O3", "NO2", "SO2") else "mg/m³"
        logger.info("RMCAB: %d registros descargados para %s/%s", len(df), station, variable)
        return df[["fecha", "estacion", "variable", "valor", "unidad"]].sort_values("fecha")
    except Exception as e:
        logger.error("Error consultando RMCAB: %s", e)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# SIATA — Sistema de Alerta Temprana de Medellín / Antioquia
# Portal: https://siata.gov.co/siata_nuevo/
# Datos abiertos disponibles en: https://www.datos.gov.co/ (descarga CSV)
# ---------------------------------------------------------------------------

_SIATA_DATOS_GOV = (
    "https://www.datos.gov.co/api/views/ms2k-yccr/rows.csv"
    "?accessType=DOWNLOAD"
)


def load_siata_aire(
    path: Optional[str] = None,
    variable: str = "PM2.5",
) -> pd.DataFrame:
    """Carga datos de calidad del aire de SIATA (Medellín/Antioquia).

    Puede cargar desde archivo local (descarga previa) o intentar descargar
    desde datos.gov.co. Dado que la URL puede cambiar, se recomienda descarga manual.

    Args:
        path: Ruta al CSV descargado desde datos.gov.co o portal SIATA.
        variable: Variable a filtrar en la columna 'variable' o 'parametro'.

    Portales de descarga:
        - https://www.datos.gov.co/ (buscar "SIATA calidad aire")
        - https://siata.gov.co/siata_nuevo/index.php/descargaData

    Returns:
        DataFrame con columnas: fecha, estacion, variable, valor, unidad, lat, lon.
    """
    import io

    if path:
        try:
            df = pd.read_csv(path, low_memory=False)
        except Exception as e:
            logger.error("Error leyendo archivo SIATA: %s", e)
            return pd.DataFrame()
    else:
        try:
            import requests
            logger.info("Intentando descarga SIATA desde datos.gov.co...")
            resp = requests.get(_SIATA_DATOS_GOV, timeout=60)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
        except Exception as e:
            logger.warning(
                "No se pudo descargar SIATA automáticamente: %s\n"
                "Descarga manual en: https://www.datos.gov.co/", e
            )
            return pd.DataFrame(columns=["fecha", "estacion", "variable", "valor", "unidad"])

    # Normalización de columnas — el formato puede variar entre versiones del portal
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if "fecha" in cl or "date" in cl or "time" in cl:
            col_map[c] = "fecha"
        elif "estacion" in cl or "station" in cl or "nombre" in cl:
            col_map[c] = "estacion"
        elif cl in ("valor", "value", "concentracion", "concentration"):
            col_map[c] = "valor"
        elif "variable" in cl or "parametro" in cl or "parameter" in cl:
            col_map[c] = "variable"
        elif "unidad" in cl or "unit" in cl:
            col_map[c] = "unidad"
        elif cl in ("lat", "latitud", "latitude"):
            col_map[c] = "lat"
        elif cl in ("lon", "lng", "longitud", "longitude"):
            col_map[c] = "lon"
    df = df.rename(columns=col_map)

    if "variable" in df.columns:
        df = df[df["variable"].str.upper().str.contains(variable.upper(), na=False)]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    expected = ["fecha", "estacion", "variable", "valor", "unidad"]
    for col in expected:
        if col not in df.columns:
            df[col] = None

    logger.info("SIATA: %d registros cargados para variable '%s'", len(df), variable)
    return df[expected].sort_values("fecha").reset_index(drop=True)


# ---------------------------------------------------------------------------
# IDEAM DHIME — Datos Hidrometeorológicos
# Portal: http://dhime.ideam.gov.co/
# Requiere registro gratuito; descarga manual de CSV/XLSX
# ---------------------------------------------------------------------------

def load_ideam_dhime(
    path: str,
    date_col: str = "Fecha",
    value_col: Optional[str] = None,
    station_col: Optional[str] = None,
    variable: Optional[str] = None,
) -> pd.DataFrame:
    """Carga datos de IDEAM DHIME desde archivo descargado manualmente.

    El portal DHIME no tiene API pública. Los datos deben descargarse en:
    http://dhime.ideam.gov.co/atencionciudadano/

    Pasos:
        1. Registrarse en el portal (gratuito).
        2. Buscar la estación por código, nombre o municipio.
        3. Seleccionar variable (precipitación, temperatura, caudal, etc.)
        4. Descargar en formato Excel o CSV.
        5. Cargar con esta función.

    Args:
        path: Ruta al archivo XLSX o CSV descargado.
        date_col: Nombre de la columna de fechas en el archivo DHIME.
        value_col: Nombre de la columna del valor. Si None, infiere automáticamente.
        station_col: Nombre de la columna de estación.
        variable: Nombre descriptivo de la variable (para documentar).

    Returns:
        DataFrame con columnas: fecha, estacion, variable, valor.
    """
    path_obj = __import__("pathlib").Path(path)
    if not path_obj.exists():
        logger.error("Archivo DHIME no encontrado: %s", path)
        return pd.DataFrame()

    try:
        if path_obj.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        logger.error("Error leyendo archivo DHIME: %s", e)
        return pd.DataFrame()

    # Renombrar columna de fecha
    if date_col in df.columns:
        df = df.rename(columns={date_col: "fecha"})
    else:
        # Intentar inferir la columna de fecha
        for c in df.columns:
            if "fecha" in c.lower() or "date" in c.lower() or "tiempo" in c.lower():
                df = df.rename(columns={c: "fecha"})
                break

    df["fecha"] = pd.to_datetime(df.get("fecha"), errors="coerce")

    if value_col and value_col in df.columns:
        df = df.rename(columns={value_col: "valor"})
    else:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            df = df.rename(columns={numeric_cols[0]: "valor"})

    if station_col and station_col in df.columns:
        df = df.rename(columns={station_col: "estacion"})
    elif "estacion" not in df.columns:
        df["estacion"] = path_obj.stem

    df["variable"] = variable or "desconocida"

    cols = [c for c in ["fecha", "estacion", "variable", "valor"] if c in df.columns]
    df = df[cols].dropna(subset=["fecha", "valor"])
    logger.info("DHIME: %d registros cargados desde '%s'", len(df), path_obj.name)
    return df.sort_values("fecha").reset_index(drop=True)


# ---------------------------------------------------------------------------
# SMByC — Sistema de Monitoreo de Bosques y Carbono (IDEAM)
# Datos de deforestación y alertas tempranas
# Portal: http://smbyc.ideam.gov.co/
# ---------------------------------------------------------------------------

def load_smbyc_alertas(path: str) -> pd.DataFrame:
    """Carga alertas tempranas de deforestación del SMByC desde archivo local.

    El SMByC publica alertas trimestrales como Shapefile o GeoJSON en:
    http://smbyc.ideam.gov.co/MonitoreoBC-WEB/reg/indexLogOn.jsp

    También disponibles en el portal SIAC:
    http://www.siac.gov.co/

    Args:
        path: Ruta al Shapefile (.shp) o GeoJSON descargado del SMByC.

    Returns:
        GeoDataFrame (si geopandas disponible) o DataFrame con columnas:
        fecha_alerta, area_ha, municipio, departamento, geometry (si aplica).
    """
    try:
        import geopandas as gpd
        gdf = gpd.read_file(path)
        logger.info("SMByC: %d alertas cargadas (geopandas)", len(gdf))
        return gdf
    except ImportError:
        logger.warning("geopandas no disponible. Cargando como CSV sin geometría.")
        try:
            df = pd.read_csv(path)
            logger.info("SMByC: %d registros cargados", len(df))
            return df
        except Exception as e:
            logger.error("Error cargando SMByC: %s", e)
            return pd.DataFrame()
    except Exception as e:
        logger.error("Error cargando archivo SMByC: %s", e)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Datos abiertos.gov.co — Portal general de datos ambientales Colombia
# ---------------------------------------------------------------------------

def list_datasets_co(
    query: str = "calidad aire",
    limit: int = 10,
) -> pd.DataFrame:
    """Busca datasets en datos.gov.co relacionados con el query ambiental.

    Args:
        query: Término de búsqueda (ej. 'calidad agua', 'deforestacion', 'caudal').
        limit: Número máximo de resultados.

    Returns:
        DataFrame con name, description, url, organization.
    """
    try:
        import requests
        resp = requests.get(
            "https://www.datos.gov.co/api/views.json",
            params={"q": query, "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data:
            rows.append({
                "name":         item.get("name", ""),
                "description":  item.get("description", "")[:150],
                "url":          f"https://www.datos.gov.co/d/{item.get('id', '')}",
                "organization": item.get("attribution", ""),
                "updated":      item.get("rowsUpdatedAt", ""),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        logger.warning("No se pudo consultar datos.gov.co: %s", e)
        return pd.DataFrame()
