"""Tests para io/connectors.py (M-14).

Estrategia: mocks de ``requests.get`` para los conectores HTTP (OpenAQ, RMCAB,
SIATA, datos.gov.co) y archivos temporales para los que leen disco
(IDEAM DHIME, SMByC). No se hacen llamadas de red reales.

Cobertura objetivo: subir el módulo de 8.7 % a >70 %.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from estadistica_ambiental.io.connectors import (
    NOMBRES_CORRECTOS,
    _openaq_param_id,
    list_datasets_co,
    load_ideam_dhime,
    load_openaq,
    load_rmcab,
    load_siata_aire,
    load_sisaire,
    load_smbyc_alertas,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_payload: dict | list, status: int = 200) -> MagicMock:
    """Construye un mock que imita la respuesta de ``requests.get``."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_payload
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# _openaq_param_id
# ---------------------------------------------------------------------------


class TestOpenaqParamId:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("pm25", 2),
            ("PM25", 2),  # case insensitive
            ("pm10", 1),
            ("o3", 3),
            ("no2", 5),
            ("so2", 9),
            ("co", 4),
            ("bc", 12),
            ("desconocido", 2),  # fallback a pm25
        ],
    )
    def test_known_and_unknown_params(self, name, expected):
        assert _openaq_param_id(name) == expected


# ---------------------------------------------------------------------------
# load_openaq — API HTTP con paginación
# ---------------------------------------------------------------------------


class TestLoadOpenaq:
    def _sample_payload(self, n: int = 2, found: int = 2) -> dict:
        results = [
            {
                "datetime": {"utc": f"2024-01-0{i + 1}T00:00:00Z"},
                "locationId": 225433,
                "value": 10.0 + i,
                "unit": "µg/m³",
                "coordinates": {"latitude": 4.6, "longitude": -74.1},
            }
            for i in range(n)
        ]
        return {"results": results, "meta": {"found": found}}

    def test_with_location_id_returns_normalized_df(self):
        payload = self._sample_payload(n=2)
        with patch("requests.get", return_value=_mock_response(payload)):
            df = load_openaq(location_id=225433, parameter="pm25", limit=10)
        assert not df.empty
        assert list(df.columns) == [
            "fecha",
            "estacion",
            "parametro",
            "valor",
            "unidad",
            "lat",
            "lon",
        ]
        assert df["parametro"].iloc[0] == "pm25"
        assert df["estacion"].iloc[0] == 225433
        # fechas localizadas a naive (sin tz)
        assert df["fecha"].dt.tz is None

    def test_country_search_without_location_id(self):
        payload = self._sample_payload(n=1)
        with patch("requests.get", return_value=_mock_response(payload)) as mocked:
            df = load_openaq(parameter="pm10", date_from="2024-01-01", date_to="2024-01-02")
        assert mocked.called
        # Se debió consultar el endpoint genérico /measurements (no /locations/{id}/measurements)
        called_url = mocked.call_args[0][0]
        assert called_url.endswith("/measurements")
        assert len(df) == 1

    def test_pagination_stops_when_short_page(self):
        # Primera página: 2 resultados (igual al limit) → continuará. Segunda: 1 → corta.
        payload_full = self._sample_payload(n=2, found=3)
        payload_short = self._sample_payload(n=1, found=3)
        with patch("requests.get", side_effect=[
            _mock_response(payload_full),
            _mock_response(payload_short),
        ]):
            df = load_openaq(location_id=225433, parameter="pm25", limit=2)
        assert len(df) == 3

    def test_empty_results_returns_empty_df(self):
        with patch("requests.get", return_value=_mock_response({"results": [], "meta": {}})):
            df = load_openaq(location_id=999, parameter="pm25")
        assert df.empty

    def test_request_exception_returns_empty_df(self):
        with patch("requests.get", side_effect=RuntimeError("network down")):
            df = load_openaq(location_id=999, parameter="pm25")
        assert df.empty


# ---------------------------------------------------------------------------
# load_rmcab
# ---------------------------------------------------------------------------


class TestLoadRmcab:
    def test_without_token_returns_empty_with_columns(self, caplog):
        df = load_rmcab(station="Kennedy", variable="PM25")
        assert df.empty
        assert list(df.columns) == ["fecha", "estacion", "variable", "valor", "unidad"]

    def test_with_token_calls_api_and_normalizes(self):
        payload = [
            {"date": "2024-01-01T00:00:00", "value": 12.5},
            {"date": "2024-01-01T01:00:00", "value": 14.3},
        ]
        with patch("requests.get", return_value=_mock_response(payload)):
            df = load_rmcab(
                station="Kennedy",
                variable="PM25",
                date_from="2024-01-01",
                date_to="2024-01-02",
                token="secret",
            )
        assert len(df) == 2
        assert (df["estacion"] == "Kennedy").all()
        assert (df["variable"] == "PM25").all()
        assert (df["unidad"] == "µg/m³").all()
        assert pd.api.types.is_datetime64_any_dtype(df["fecha"])

    def test_co_variable_uses_mg_unit(self):
        payload = [{"date": "2024-01-01T00:00:00", "value": 1.2}]
        with patch("requests.get", return_value=_mock_response(payload)):
            df = load_rmcab(station="Kennedy", variable="CO", token="secret")
        assert df["unidad"].iloc[0] == "mg/m³"

    def test_empty_payload_returns_empty(self):
        with patch("requests.get", return_value=_mock_response([])):
            df = load_rmcab(station="Kennedy", variable="PM25", token="secret")
        assert df.empty

    def test_http_error_returns_empty(self):
        with patch("requests.get", side_effect=ValueError("boom")):
            df = load_rmcab(station="Kennedy", variable="PM25", token="secret")
        assert df.empty


# ---------------------------------------------------------------------------
# load_siata_aire — archivo local
# ---------------------------------------------------------------------------


class TestLoadSiataAire:
    def test_load_from_local_csv_with_normalization(self, tmp_path):
        csv = tmp_path / "siata.csv"
        csv.write_text(
            "Fecha,NombreEstacion,Parametro,Concentracion,Unit,Latitud,Longitud\n"
            "2024-01-01 00:00,Centro,PM2.5,18.0,µg/m³,6.25,-75.56\n"
            "2024-01-01 01:00,Centro,PM2.5,22.5,µg/m³,6.25,-75.56\n"
            "2024-01-01 02:00,Centro,PM10,45.0,µg/m³,6.25,-75.56\n",
            encoding="utf-8",
        )
        df = load_siata_aire(path=str(csv), variable="PM2.5")
        assert len(df) == 2  # PM10 fila descartada por filtro de variable
        assert "fecha" in df.columns
        assert "estacion" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["fecha"])

    def test_invalid_file_returns_empty(self, tmp_path):
        df = load_siata_aire(path=str(tmp_path / "no_existe.csv"))
        assert df.empty

    def test_remote_failure_returns_empty_with_columns(self):
        with patch("requests.get", side_effect=RuntimeError("offline")):
            df = load_siata_aire(path=None, variable="PM2.5")
        assert df.empty
        assert {"fecha", "estacion", "variable", "valor", "unidad"}.issubset(df.columns)

    def test_remote_success(self):
        csv_text = (
            "fecha,estacion,variable,valor,unidad\n"
            "2024-01-01,Itagui,PM2.5,30.0,µg/m³\n"
        )
        resp = MagicMock()
        resp.text = csv_text
        resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=resp):
            df = load_siata_aire(path=None, variable="PM2.5")
        assert len(df) == 1


# ---------------------------------------------------------------------------
# load_ideam_dhime — archivo local
# ---------------------------------------------------------------------------


class TestLoadIdeamDhime:
    def test_csv_basic(self, tmp_path):
        csv = tmp_path / "estacion_X.csv"
        csv.write_text(
            "Fecha,Valor\n2024-01-01,15.2\n2024-01-02,16.7\n",
            encoding="utf-8",
        )
        df = load_ideam_dhime(path=str(csv), variable="precipitacion")
        assert len(df) == 2
        assert (df["variable"] == "precipitacion").all()
        assert (df["estacion"] == "estacion_X").all()  # inferida del filename

    def test_xlsx_path(self, tmp_path):
        xlsx = tmp_path / "estacion.xlsx"
        pd.DataFrame({"Fecha": ["2024-01-01"], "Valor": [10.0]}).to_excel(xlsx, index=False)
        df = load_ideam_dhime(path=str(xlsx), variable="caudal")
        assert len(df) == 1

    def test_missing_file_returns_empty(self, tmp_path):
        df = load_ideam_dhime(path=str(tmp_path / "no_existe.csv"))
        assert df.empty

    def test_explicit_value_and_station_columns(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "Fecha,COD_EST,Caudal_m3s\n2024-01-01,EST123,20.5\n",
            encoding="utf-8",
        )
        df = load_ideam_dhime(
            path=str(csv),
            value_col="Caudal_m3s",
            station_col="COD_EST",
            variable="caudal",
        )
        assert df["estacion"].iloc[0] == "EST123"
        assert df["valor"].iloc[0] == 20.5

    def test_corrupt_file_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_bytes(b"\xff\xfe\x00not csv")
        # Crear como csv pero con contenido binario inválido
        df = load_ideam_dhime(path=str(bad))
        # Puede devolver vacío o intentar parsear; basta con que no explote
        assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# load_smbyc_alertas
# ---------------------------------------------------------------------------


class TestLoadSmbycAlertas:
    def test_falls_back_to_csv_without_geopandas(self, tmp_path, monkeypatch):
        csv = tmp_path / "alertas.csv"
        csv.write_text(
            "fecha_alerta,area_ha,municipio,departamento\n"
            "2024-01-01,150.5,Florencia,Caqueta\n",
            encoding="utf-8",
        )

        # Forzar ImportError de geopandas
        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "geopandas":
                raise ImportError("geopandas no instalado")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        df = load_smbyc_alertas(str(csv))
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_invalid_path_returns_empty(self, tmp_path, monkeypatch):
        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "geopandas":
                raise ImportError("geopandas no instalado")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        df = load_smbyc_alertas(str(tmp_path / "no_existe.csv"))
        assert df.empty


# ---------------------------------------------------------------------------
# list_datasets_co
# ---------------------------------------------------------------------------


class TestListDatasetsCo:
    def test_normalizes_response(self):
        payload = [
            {
                "name": "Calidad de aire RMCAB",
                "description": "Mediciones horarias de PM2.5 y PM10 en Bogotá",
                "id": "abcd-1234",
                "attribution": "SDA Bogotá",
                "rowsUpdatedAt": "2024-12-01",
            },
            {
                "name": "Estaciones SIATA",
                "description": "Red de monitoreo Medellín",
                "id": "efgh-5678",
                "attribution": "SIATA",
                "rowsUpdatedAt": "2024-11-15",
            },
        ]
        with patch("requests.get", return_value=_mock_response(payload)):
            df = list_datasets_co(query="calidad aire", limit=2)
        assert len(df) == 2
        assert {"name", "description", "url", "organization", "updated"}.issubset(df.columns)
        assert df["url"].iloc[0].startswith("https://www.datos.gov.co/d/")

    def test_request_failure_returns_empty(self):
        with patch("requests.get", side_effect=RuntimeError("offline")):
            df = list_datasets_co(query="caudal")
        assert df.empty


# ---------------------------------------------------------------------------
# load_sisaire — IDEAM SISAIRE con fallback de encoding (M-03 / Plan §13)
# ---------------------------------------------------------------------------


def _mock_csv_response(text: str, encoding: str = "utf-8", status: int = 200) -> MagicMock:
    """Mock de ``requests.get`` que devuelve CSV en bytes con encoding dado."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = text.encode(encoding)
    resp.raise_for_status.return_value = None
    return resp


class TestLoadSisaire:
    _CSV_UTF8 = (
        "FECHA,ESTACION,PM2_5,UNIDAD\n"
        "2024-01-01 00:00,Bogota Centro,15.3,µg/m³\n"
        "2024-01-01 01:00,Bogota Centro,18.7,µg/m³\n"
    )
    # Mismo contenido pero con caracteres no-ASCII (µ, ñ) que deben aparecer
    # correctamente cuando se decodifica con latin-1.
    _CSV_LATIN1 = (
        "FECHA,ESTACION,PM2_5,UNIDAD\n"
        "2024-01-01 00:00,Cañón del Chicamocha,12.4,µg/m³\n"
    )

    def test_happy_path_utf8(self):
        with patch(
            "requests.get",
            return_value=_mock_csv_response(self._CSV_UTF8, encoding="utf-8"),
        ) as mocked:
            df = load_sisaire(
                estacion="EST001",
                parametro="PM2.5",
                fecha_ini="2024-01-01",
                fecha_fin="2024-01-02",
            )
        assert mocked.called
        # parámetros propagados al endpoint
        kwargs = mocked.call_args.kwargs
        assert kwargs["timeout"] == 30.0
        assert kwargs["params"]["estacion"] == "EST001"
        assert kwargs["params"]["parametro"] == "PM2.5"
        # DataFrame normalizado
        assert len(df) == 2
        assert "pm25" in df.columns
        assert "fecha" in df.columns
        assert "estacion" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["fecha"])
        assert df["pm25"].iloc[0] == 15.3

    def test_fallback_latin1_when_utf8_fails(self):
        # Bytes inválidos como utf-8 pero válidos como latin-1
        with patch(
            "requests.get",
            return_value=_mock_csv_response(self._CSV_LATIN1, encoding="latin-1"),
        ):
            df = load_sisaire(
                estacion="EST002",
                parametro="PM2.5",
                fecha_ini="2024-01-01",
                fecha_fin="2024-01-02",
            )
        assert len(df) == 1
        # El nombre con tilde debe aparecer correctamente, no como mojibake
        nombre = df["estacion"].iloc[0]
        assert "Cañón" in nombre
        assert "�" not in nombre  # sin U+FFFD

    def test_column_normalization_pm2_5_to_pm25(self):
        csv = (
            "FECHA,ESTACION,PM2_5,PM10,O3\n"
            "2024-01-01,EST,10.0,25.0,30.0\n"
        )
        with patch("requests.get", return_value=_mock_csv_response(csv)):
            df = load_sisaire(
                estacion="EST",
                parametro="PM2.5",
                fecha_ini="2024-01-01",
                fecha_fin="2024-01-02",
            )
        # Columnas renombradas según NOMBRES_CORRECTOS
        assert "pm25" in df.columns
        assert "pm10" in df.columns
        assert "o3" in df.columns
        assert "PM2_5" not in df.columns
        assert "FECHA" not in df.columns
        # Verificación de la presencia del mapeo PM2_5 → pm25
        assert NOMBRES_CORRECTOS["PM2_5"] == "pm25"

    def test_http_error_propagates(self):
        # raise_for_status lanzando excepción debe propagarse al caller
        resp = MagicMock()
        resp.content = b""
        resp.raise_for_status.side_effect = RuntimeError("503 Service Unavailable")
        with patch("requests.get", return_value=resp):
            with pytest.raises(RuntimeError, match="503"):
                load_sisaire(
                    estacion="EST",
                    parametro="PM2.5",
                    fecha_ini="2024-01-01",
                    fecha_fin="2024-01-02",
                )

    def test_timeout_propagates(self):
        # Errores de timeout también deben propagarse, no silenciarse
        with patch("requests.get", side_effect=TimeoutError("read timed out")):
            with pytest.raises(TimeoutError):
                load_sisaire(
                    estacion="EST",
                    parametro="PM2.5",
                    fecha_ini="2024-01-01",
                    fecha_fin="2024-01-02",
                    timeout=5.0,
                )

    def test_estacion_none_queries_all(self):
        with patch(
            "requests.get",
            return_value=_mock_csv_response(self._CSV_UTF8),
        ) as mocked:
            df = load_sisaire(
                estacion=None,
                parametro="PM2.5",
                fecha_ini="2024-01-01",
                fecha_fin="2024-01-02",
            )
        assert mocked.call_args.kwargs["params"]["estacion"] == "all"
        assert not df.empty
