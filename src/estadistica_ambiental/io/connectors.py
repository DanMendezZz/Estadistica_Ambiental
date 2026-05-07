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
            "date_to": f"{date_to}T23:59:59Z",
            "limit": limit,
        }
    else:
        url = f"{_OPENAQ_API}/measurements"
        params = {
            "countries_id": 170,  # Colombia
            "parameters_id": _openaq_param_id(parameter),
            "date_from": f"{date_from}T00:00:00Z",
            "date_to": f"{date_to}T23:59:59Z",
            "limit": limit,
        }

    try:
        all_data: list = []
        page = 1
        while True:
            params["page"] = page
            resp = requests.get(url, headers=_OPENAQ_HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            body = resp.json()
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
            rows.append(
                {
                    "fecha": pd.to_datetime(m.get("datetime", {}).get("utc"), utc=True),
                    "estacion": m.get("locationId"),
                    "parametro": parameter,
                    "valor": m.get("value"),
                    "unidad": m.get("unit", "µg/m³"),
                    "lat": m.get("coordinates", {}).get("latitude"),
                    "lon": m.get("coordinates", {}).get("longitude"),
                }
            )
        df = pd.DataFrame(rows)
        df["fecha"] = pd.to_datetime(df["fecha"], utc=True).dt.tz_localize(None)
        logger.info(
            "OpenAQ: %d registros descargados (%s, %s → %s)", len(df), parameter, date_from, date_to
        )
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
            station,
            variable,
            date_from,
            date_to,
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

_SIATA_DATOS_GOV = "https://www.datos.gov.co/api/views/ms2k-yccr/rows.csv?accessType=DOWNLOAD"


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
                "Descarga manual en: https://www.datos.gov.co/",
                e,
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
# SISAIRE — Subsistema de Información sobre Calidad del Aire (IDEAM)
# Portal: https://sisaire.ideam.gov.co/
# Publica datos horarios y diarios de PM2.5, PM10, O3, NO2, SO2, CO de las
# Autoridades Ambientales (CARs) que reportan al IDEAM. Las descargas en CSV
# suelen llegar con encoding latin-1 (mojibake U+FFFD si se asume utf-8).
# ---------------------------------------------------------------------------

_SISAIRE_API = "https://sisaire.ideam.gov.co/api"

# Mapeo de nombres SISAIRE → convenciones internas del repo (M-03 / Plan §13).
# Corrige también encabezados con caracteres unicode dañados en exports CSV.
NOMBRES_CORRECTOS: dict[str, str] = {
    "PM2_5": "pm25",
    "PM2.5": "pm25",
    "PM25": "pm25",
    "PM10": "pm10",
    "O3": "o3",
    "NO2": "no2",
    "SO2": "so2",
    "CO": "co",
    "FECHA": "fecha",
    "FECHA INICIAL": "fecha",
    "FECHA FINAL": "fecha_fin",
    "FECHA_HORA": "fecha",
    "DATETIME": "fecha",
    "ESTACION": "estacion",
    "NOMBRE_ESTACION": "estacion",
    "CODIGO_ESTACION": "codigo_estacion",
    "AUTORIDAD_AMBIENTAL": "autoridad",
    "DEPARTAMENTO": "departamento",
    "MUNICIPIO": "municipio",
    "LATITUD": "lat",
    "LONGITUD": "lon",
    "VALOR": "valor",
    "UNIDAD": "unidad",
    "PARAMETRO": "parametro",
}


def load_sisaire(
    estacion: Optional[str],
    parametro: str = "PM2.5",
    fecha_ini: str = "2024-01-01",
    fecha_fin: Optional[str] = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Descarga CSV de SISAIRE (IDEAM) con fallback de encoding utf-8 → latin-1.

    Args:
        estacion: Código o nombre de estación SISAIRE; ``None`` consulta todas.
        parametro: Variable a descargar (PM2.5, PM10, O3, NO2, SO2, CO).
        fecha_ini: Fecha inicio ``YYYY-MM-DD``.
        fecha_fin: Fecha fin ``YYYY-MM-DD`` (default: hoy).
        timeout: Timeout HTTP en segundos.

    Returns:
        DataFrame con columnas normalizadas según ``NOMBRES_CORRECTOS``
        (p. ej. ``PM2_5`` → ``pm25``, ``FECHA`` → ``fecha``).

    Notas:
        El portal SISAIRE entrega CSV usualmente codificados en latin-1; esta
        función intenta primero ``utf-8`` y, si falla con ``UnicodeDecodeError``,
        reintenta con ``latin-1`` para evitar mojibake (U+FFFD).
    """
    try:
        import requests
    except ImportError:
        logger.error("Instalar 'requests': pip install requests")
        return pd.DataFrame()

    if fecha_fin is None:
        fecha_fin = datetime.now().strftime("%Y-%m-%d")

    url = f"{_SISAIRE_API}/datos/descarga"
    params = {
        "estacion": estacion if estacion is not None else "all",
        "parametro": parametro,
        "fechaIni": fecha_ini,
        "fechaFin": fecha_fin,
        "formato": "csv",
    }

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()

    raw: bytes = resp.content
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.info("SISAIRE: utf-8 falló, reintentando con latin-1.")
        text = raw.decode("latin-1")

    import io

    df = pd.read_csv(io.StringIO(text), low_memory=False)
    if df.empty:
        logger.warning("SISAIRE: respuesta sin registros para %s/%s", estacion, parametro)
        return df

    # Normalización de columnas con NOMBRES_CORRECTOS (case-insensitive en clave)
    rename_map: dict[str, str] = {}
    upper_lookup = {k.upper(): v for k, v in NOMBRES_CORRECTOS.items()}
    for col in df.columns:
        key = str(col).strip().upper()
        if key in upper_lookup:
            rename_map[col] = upper_lookup[key]
    df = df.rename(columns=rename_map)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    if "estacion" not in df.columns and estacion is not None:
        df["estacion"] = estacion

    logger.info(
        "SISAIRE: %d registros (%s, %s, %s → %s)",
        len(df),
        estacion,
        parametro,
        fecha_ini,
        fecha_fin,
    )
    return df.reset_index(drop=True)


def load_sisaire_local(
    anios: int | list[int] | None = None,
    parametro: str = "pm25",
    estaciones: list[str] | None = None,
    path: "str | None" = None,
) -> pd.DataFrame:
    """Lee descargas SISAIRE locales (`CAR_<año>.csv`) sin duplicar archivos.

    Pensado para uso con datos descargados manualmente del portal SISAIRE / CAR
    (formato: ``"Estacion","Fecha inicial","Fecha final","PM2.5"``). La carpeta
    se referencia por ``config.SISAIRE_LOCAL_DIR`` (variable de entorno
    ``SISAIRE_LOCAL_DIR``); el repo nunca asume una ruta fija.

    Args:
        anios: Año (int), lista de años o ``None`` para leer todos los
            ``CAR_*.csv`` presentes.
        parametro: Variable normalizada esperada (``pm25``, ``pm10``, ...).
            Debe coincidir con la columna del CSV tras normalizar headers.
        estaciones: Si se pasa, filtra ``estacion in estaciones``.
        path: Carpeta explícita. Si es ``None`` usa ``config.SISAIRE_LOCAL_DIR``.

    Returns:
        DataFrame con columnas ``fecha`` (datetime), ``estacion`` (str) y
        la columna del parámetro como float (p. ej. ``pm25``).

    Raises:
        FileNotFoundError: Si no se configuró ``SISAIRE_LOCAL_DIR`` ni se pasó
            ``path``, o si la carpeta no contiene archivos coincidentes.
    """
    from pathlib import Path

    from estadistica_ambiental.config import SISAIRE_LOCAL_DIR

    base = Path(path) if path is not None else SISAIRE_LOCAL_DIR
    if base is None:
        raise FileNotFoundError(
            "SISAIRE_LOCAL_DIR no está configurada. Define la variable de entorno "
            "SISAIRE_LOCAL_DIR apuntando a la carpeta con los CSV CAR_<año>.csv, "
            "o pasa `path=...` explícitamente."
        )
    if not base.exists():
        raise FileNotFoundError(f"SISAIRE_LOCAL_DIR no existe: {base}")

    if anios is None:
        archivos = sorted(base.glob("CAR_*.csv"))
    else:
        lista = [anios] if isinstance(anios, int) else list(anios)
        archivos = [base / f"CAR_{a}.csv" for a in lista]

    archivos = [a for a in archivos if a.exists()]
    if not archivos:
        raise FileNotFoundError(f"Sin archivos CAR_<año>.csv en {base} para anios={anios}")

    upper_lookup = {k.upper(): v for k, v in NOMBRES_CORRECTOS.items()}

    frames: list[pd.DataFrame] = []
    for archivo in archivos:
        try:
            sub = pd.read_csv(archivo, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            sub = pd.read_csv(archivo, encoding="latin-1", low_memory=False)

        rename = {
            c: upper_lookup[str(c).strip().upper()]
            for c in sub.columns
            if str(c).strip().upper() in upper_lookup
        }
        sub = sub.rename(columns=rename)
        frames.append(sub)

    df = pd.concat(frames, ignore_index=True)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    if parametro in df.columns:
        df[parametro] = pd.to_numeric(df[parametro], errors="coerce")
    else:
        raise KeyError(
            f"Parámetro '{parametro}' no encontrado tras normalizar columnas. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    if estaciones and "estacion" in df.columns:
        df = df[df["estacion"].isin(estaciones)]

    keep = [c for c in ("fecha", "estacion", parametro) if c in df.columns]
    df = df[keep].dropna(subset=["fecha", parametro])

    logger.info(
        "SISAIRE local: %d registros desde %d archivo(s) en %s (parametro=%s)",
        len(df),
        len(archivos),
        base,
        parametro,
    )
    return df.sort_values("fecha").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Datos abiertos.gov.co — Portal general de datos ambientales Colombia
# ---------------------------------------------------------------------------

# Tamaño máximo por consulta del API SODA. SODA tiene un tope duro de 50000
# filas por llamada — se expone como constante de módulo para que los tests
# puedan reducirlo y así forzar paginación con datasets pequeños.
DATOS_GOV_CO_PAGE_SIZE = 50000


def load_datos_gov_co_dataset(
    dataset_id: str,
    where: Optional[str] = None,
    select: Optional[str] = None,
    limit: int = 50000,
    app_token: Optional[str] = None,
) -> pd.DataFrame:
    """Descarga filas de un dataset SODA en datos.gov.co.

    Cliente genérico de la Socrata Open Data API (SODA). A diferencia de
    ``list_datasets_co`` (que solo lista metadatos), esta función descarga las
    filas reales del dataset identificado por ``dataset_id`` (p. ej.
    ``"7g8z-fpvn"``). El endpoint usado es:
    ``https://www.datos.gov.co/resource/<dataset_id>.json``.

    Args:
        dataset_id: ID del dataset (parte después de ``/d/`` en la URL pública).
        where: Cláusula SoQL ``$where`` (p. ej. ``"departamento = 'Antioquia'"``).
        select: Cláusula SoQL ``$select`` con columnas separadas por coma.
        limit: Tope total de filas a descargar (paginación interna por 50000).
        app_token: Token opcional ``X-App-Token`` para evitar throttling de SODA.

    Returns:
        DataFrame con las columnas tal como las devuelve el dataset (sin
        normalización: los datasets son heterogéneos).

    Notas:
        El endpoint SODA pagina con ``$offset`` y un máximo de 50000 filas por
        consulta. Esta función itera hasta alcanzar ``limit`` o agotar resultados.
    """
    try:
        import requests
    except ImportError:
        logger.warning("Instalar 'requests': pip install requests")
        return pd.DataFrame()

    url = f"https://www.datos.gov.co/resource/{dataset_id}.json"
    headers = {"Accept": "application/json"}
    if app_token:
        headers["X-App-Token"] = app_token

    # SODA limita cada llamada a ``DATOS_GOV_CO_PAGE_SIZE`` filas. Iteramos
    # con $offset hasta que el servidor devuelva una página corta (señal de
    # fin) o se alcance el ``limit`` total solicitado por el usuario.
    page_size = max(1, DATOS_GOV_CO_PAGE_SIZE)
    all_rows: list = []
    offset = 0
    try:
        while len(all_rows) < limit:
            params: dict = {"$limit": page_size, "$offset": offset}
            if where:
                params["$where"] = where
            if select:
                params["$select"] = select

            resp = requests.get(url, headers=headers, params=params, timeout=60)
            resp.raise_for_status()
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            all_rows.extend(batch)
            logger.info(
                "datos.gov.co [%s]: pág. offset=%d trajo %d filas (acum=%d)",
                dataset_id,
                offset,
                len(batch),
                len(all_rows),
            )
            # Página corta del servidor → ya no hay más filas.
            if len(batch) < page_size:
                break
            offset += len(batch)

        # Recortar al límite total solicitado por el usuario.
        if len(all_rows) > limit:
            all_rows = all_rows[:limit]
        df = pd.DataFrame(all_rows)
        logger.info("datos.gov.co [%s]: %d filas descargadas en total", dataset_id, len(df))
        return df
    except Exception as e:
        logger.error("Error descargando dataset %s desde datos.gov.co: %s", dataset_id, e)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# IDEAM DHIME — variante robusta para CSV (encabezados con metadatos previos)
# ---------------------------------------------------------------------------


def load_ideam_dhime_csv(
    path: str,
    parametro: str,
    fecha_col_candidates: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Lee CSV de IDEAM DHIME con líneas de metadatos previas al encabezado.

    Variante robusta de ``load_ideam_dhime`` específica para los CSV exportados
    por DHIME, que típicamente traen varias filas de metadatos (estación,
    municipio, coordenadas, etc.) antes del encabezado real, y nombran la
    columna de valor de forma localizada (``VALOR``, ``Valor [mm]``,
    ``valor_observado``...).

    La función inspecciona las primeras líneas hasta detectar una fila que
    contenga alguno de los candidatos de fecha y, a partir de ahí, parsea el
    CSV. Luego identifica la columna de valor por: (a) coincidencia con el
    ``parametro`` solicitado en el nombre o (b) primera columna numérica.

    Args:
        path: Ruta al CSV exportado desde DHIME.
        parametro: Nombre descriptivo del parámetro (``"precipitacion"``,
            ``"temperatura"``, ``"caudal"``, ...). Se intentará usar como pista
            para localizar la columna de valor.
        fecha_col_candidates: Nombres alternativos para la columna de fecha.
            Default: ``["Fecha", "FECHA", "fecha"]``.

    Returns:
        DataFrame con columnas: ``fecha``, ``estacion``, ``parametro``, ``valor``.

    Raises:
        FileNotFoundError: Si ``path`` no existe.
    """
    from pathlib import Path

    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Archivo DHIME no encontrado: {path}")

    if fecha_col_candidates is None:
        fecha_col_candidates = ["Fecha", "FECHA", "fecha"]
    candidatos_upper = {c.upper() for c in fecha_col_candidates}

    # Buscar la línea de encabezado: la primera que contenga alguno de los
    # nombres de fecha candidatos como token separado por coma o punto y coma.
    max_skip = 30
    header_line = 0
    encoding_used = "utf-8"
    try:
        with open(path_obj, encoding="utf-8") as fh:
            lines = fh.readlines()
    except UnicodeDecodeError:
        encoding_used = "latin-1"
        with open(path_obj, encoding="latin-1") as fh:
            lines = fh.readlines()

    for i, line in enumerate(lines[:max_skip]):
        tokens = [t.strip().strip('"').upper() for t in line.replace(";", ",").split(",")]
        if any(tok in candidatos_upper for tok in tokens):
            header_line = i
            break

    try:
        df = pd.read_csv(
            path_obj,
            skiprows=header_line,
            encoding=encoding_used,
            sep=None,
            engine="python",
        )
    except Exception as e:
        logger.error("Error leyendo CSV DHIME '%s': %s", path_obj.name, e)
        return pd.DataFrame(columns=["fecha", "estacion", "parametro", "valor"])

    # Localizar columna de fecha
    fecha_col: Optional[str] = None
    for col in df.columns:
        if str(col).strip().upper() in candidatos_upper:
            fecha_col = col
            break
    if fecha_col is None:
        for col in df.columns:
            if "FECHA" in str(col).upper() or "DATE" in str(col).upper():
                fecha_col = col
                break
    if fecha_col is None:
        logger.warning("DHIME CSV: no se halló columna de fecha en %s", path_obj.name)
        return pd.DataFrame(columns=["fecha", "estacion", "parametro", "valor"])

    df = df.rename(columns={fecha_col: "fecha"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=False)

    # Localizar columna de estación si existe
    estacion_col: Optional[str] = None
    for col in df.columns:
        cu = str(col).upper()
        if "ESTACION" in cu or "ESTACIÓN" in cu or "COD_EST" in cu or "CODIGOESTACION" in cu:
            estacion_col = col
            break

    # Localizar columna de valor: por coincidencia con parametro o primera numérica
    parametro_upper = parametro.upper()
    valor_col: Optional[str] = None
    for col in df.columns:
        if col == "fecha" or col == estacion_col:
            continue
        if parametro_upper in str(col).upper():
            valor_col = col
            break
    if valor_col is None:
        for col in df.columns:
            if col == "fecha" or col == estacion_col:
                continue
            serie_num = pd.to_numeric(df[col], errors="coerce")
            if serie_num.notna().any():
                valor_col = col
                df[col] = serie_num
                break
        else:
            # Fallback explícito a "VALOR"
            for col in df.columns:
                if str(col).strip().upper() == "VALOR":
                    valor_col = col
                    break

    if valor_col is None:
        logger.warning("DHIME CSV: no se halló columna de valor en %s", path_obj.name)
        return pd.DataFrame(columns=["fecha", "estacion", "parametro", "valor"])

    df = df.rename(columns={valor_col: "valor"})
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    if estacion_col and estacion_col in df.columns:
        df = df.rename(columns={estacion_col: "estacion"})
    else:
        df["estacion"] = path_obj.stem

    df["parametro"] = parametro

    out = df[["fecha", "estacion", "parametro", "valor"]].dropna(subset=["fecha", "valor"])
    logger.info(
        "DHIME CSV: %d registros leídos desde '%s' (parametro=%s, header_line=%d)",
        len(out),
        path_obj.name,
        parametro,
        header_line,
    )
    return out.sort_values("fecha").reset_index(drop=True)


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
            rows.append(
                {
                    "name": item.get("name", ""),
                    "description": item.get("description", "")[:150],
                    "url": f"https://www.datos.gov.co/d/{item.get('id', '')}",
                    "organization": item.get("attribution", ""),
                    "updated": item.get("rowsUpdatedAt", ""),
                }
            )
        return pd.DataFrame(rows)
    except Exception as e:
        logger.warning("No se pudo consultar datos.gov.co: %s", e)
        return pd.DataFrame()
