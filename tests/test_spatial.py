"""Tests para spatial/, features/ y reporting/stats_report.py"""

import logging

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.evaluation.comparison import rank_models, select_best
from estadistica_ambiental.features.calendar import add_calendar_features
from estadistica_ambiental.features.exogenous import meteorological_features
from estadistica_ambiental.features.lags import add_diff_features, add_lags, add_rolling_features
from estadistica_ambiental.preprocessing.imputation import impute
from estadistica_ambiental.preprocessing.outliers import flag_outliers
from estadistica_ambiental.preprocessing.resampling import fill_missing_timestamps, resample
from estadistica_ambiental.reporting.stats_report import stats_report
from estadistica_ambiental.spatial.analysis import intersection_area, zonal_statistics
from estadistica_ambiental.spatial.autocorrelation import (
    geary_c,
    getis_ord_g,
    local_morans_i,
    morans_i,
)
from estadistica_ambiental.spatial.interpolation import (
    _clip_variance,
    idw,
    ordinary_kriging,
    universal_kriging,
)
from estadistica_ambiental.spatial.projections import (
    bounding_box_colombia,
    clip_to_colombia,
    points_to_geodataframe,
    reproject,
)

# ---------------------------------------------------------------------------
# spatial/analysis — intersection_area y zonal_statistics
# ---------------------------------------------------------------------------


class TestIntersectionArea:
    @pytest.fixture
    def two_overlapping_gdfs(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        gdf1 = gpd.GeoDataFrame(
            {"id_ini": ["A", "B"], "geometry": [box(0, 0, 2, 2), box(3, 3, 5, 5)]},
            crs="EPSG:4326",
        )
        gdf2 = gpd.GeoDataFrame(
            {"id_ap": ["X", "Y"], "geometry": [box(1, 1, 3, 3), box(0, 0, 1, 1)]},
            crs="EPSG:4326",
        )
        return gdf1, gdf2

    def test_returns_geodataframe(self, two_overlapping_gdfs):
        gdf1, gdf2 = two_overlapping_gdfs
        result = intersection_area(gdf1, gdf2, "id_ini", "id_ap")
        gpd = pytest.importorskip("geopandas")
        assert isinstance(result, gpd.GeoDataFrame)

    def test_columns_present(self, two_overlapping_gdfs):
        gdf1, gdf2 = two_overlapping_gdfs
        result = intersection_area(gdf1, gdf2, "id_ini", "id_ap")
        assert "intersection_area_m2" in result.columns
        assert "pct_of_id_ini" in result.columns
        assert "pct_of_id_ap" in result.columns

    def test_area_positive(self, two_overlapping_gdfs):
        gdf1, gdf2 = two_overlapping_gdfs
        result = intersection_area(gdf1, gdf2, "id_ini", "id_ap")
        if len(result) > 0:
            assert (result["intersection_area_m2"] >= 0).all()

    def test_no_overlap_returns_empty(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        gdf1 = gpd.GeoDataFrame({"id_a": ["A"], "geometry": [box(0, 0, 1, 1)]}, crs="EPSG:4326")
        gdf2 = gpd.GeoDataFrame({"id_b": ["B"], "geometry": [box(10, 10, 11, 11)]}, crs="EPSG:4326")
        result = intersection_area(gdf1, gdf2, "id_a", "id_b")
        assert len(result) == 0

    def test_different_crs_aligned(self, two_overlapping_gdfs):
        gdf1, gdf2 = two_overlapping_gdfs
        gdf2_reproj = gdf2.to_crs(epsg=3857)
        result = intersection_area(gdf1, gdf2_reproj, "id_ini", "id_ap")
        gpd = pytest.importorskip("geopandas")
        assert isinstance(result, gpd.GeoDataFrame)


class TestZonalStatistics:
    @pytest.fixture
    def raster_4x4(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from rasterio.transform import from_origin

        path = tmp_path / "raster.tif"
        # origen (0,4), pixel 1x1 -> fila 0 es y=[3,4], fila 3 es y=[0,1];
        # columna 0 es x=[0,1], columna 3 es x=[3,4].
        data = np.array(
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]], dtype="float32"
        )
        transform = from_origin(0, 4, 1, 1)
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=4,
            width=4,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999,
        ) as dst:
            dst.write(data, 1)
        return path

    def test_computes_stats_for_zone_covering_left_half(self, raster_4x4):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        # Columnas 0-1 (x en [0,2]), todas las filas -> valores 1,2,5,6,9,10,13,14
        # (verificado a mano contra el layout de `raster_4x4` antes de escribir el assert).
        zone = gpd.GeoDataFrame({"zid": ["izquierda"]}, geometry=[box(0, 0, 2, 4)], crs="EPSG:4326")

        result = zonal_statistics(
            raster_4x4, zone, "zid", stats=["mean", "sum", "count", "min", "max"]
        )

        row = result.iloc[0]
        assert row["sum"] == 60.0
        assert row["count"] == 8.0
        assert row["mean"] == 7.5
        assert row["min"] == 1.0
        assert row["max"] == 14.0

    def test_zone_without_overlap_returns_nan(self, raster_4x4):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        zone = gpd.GeoDataFrame(
            {"zid": ["fuera"]}, geometry=[box(100, 100, 101, 101)], crs="EPSG:4326"
        )
        result = zonal_statistics(raster_4x4, zone, "zid", stats=["mean"])
        assert pd.isna(result.iloc[0]["mean"])

    def test_unsupported_stat_raises_valueerror(self, raster_4x4, tmp_path):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        zone = gpd.GeoDataFrame({"zid": ["x"]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")
        with pytest.raises(ValueError, match="no soportadas"):
            zonal_statistics(raster_4x4, zone, "zid", stats=["percentil_90"])

    def test_reprojects_zones_to_raster_crs(self, raster_4x4):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import box

        # Zona en Web Mercator (3857) sobre un raster en WGS84 (4326): debe
        # reproyectar antes de recortar, no fallar ni devolver todo NaN.
        zone_4326 = gpd.GeoDataFrame(
            {"zid": ["izquierda"]}, geometry=[box(0, 0, 2, 4)], crs="EPSG:4326"
        )
        zone_3857 = zone_4326.to_crs(epsg=3857)
        result = zonal_statistics(raster_4x4, zone_3857, "zid", stats=["count"])
        assert result.iloc[0]["count"] == 8.0


# ---------------------------------------------------------------------------
# spatial/autocorrelation — geary_c y getis_ord_g
# ---------------------------------------------------------------------------


class TestGearyC:
    @pytest.fixture
    def spatial_gdf(self):
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [float(i * 4 + j) for i in range(4) for j in range(4)]
        return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

    def test_returns_dict(self, spatial_gdf):
        result = geary_c(spatial_gdf, "value")
        assert isinstance(result, dict)

    def test_required_keys(self, spatial_gdf):
        result = geary_c(spatial_gdf, "value")
        assert "C" in result
        assert "p_sim" in result
        assert "significant" in result
        assert "interpretation" in result

    def test_c_positive(self, spatial_gdf):
        result = geary_c(spatial_gdf, "value")
        assert result["C"] >= 0

    def test_not_significant_interpretation(self, spatial_gdf):
        # significance=-1 garantiza p_sim >= significance siempre (p_sim
        # nunca es negativo), forzando la rama "aleatoria" sin depender del
        # resultado estocástico de las permutaciones.
        result = geary_c(spatial_gdf, "value", significance=-1)
        assert result["significant"] is False
        assert "aleatoria" in result["interpretation"]

    def test_dispersion_interpretation_on_checkerboard_rook(self):
        # Tablero de ajedrez con pesos rook: C > 1 (dispersión) verificado
        # empíricamente (C=1.875). significance=1.1 evita caer en la rama
        # "aleatoria" (p_sim <= 1 siempre < 1.1).
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [float((i + j) % 2) for i in range(4) for j in range(4)]
        gdf = gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

        result = geary_c(gdf, "value", weight_type="rook", significance=1.1)
        assert result["C"] > 1
        assert "dispersión" in result["interpretation"]


class TestGetisOrdG:
    @pytest.fixture
    def spatial_gdf(self):
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [float(i * 4 + j) for i in range(4) for j in range(4)]
        return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

    def test_adds_columns(self, spatial_gdf):
        result = getis_ord_g(spatial_gdf, "value")
        assert "g_z" in result.columns
        assert "g_p" in result.columns
        assert "hotspot" in result.columns

    def test_hotspot_values(self, spatial_gdf):
        result = getis_ord_g(spatial_gdf, "value")
        assert set(result["hotspot"].unique()).issubset({"hot", "cold", "ns"})

    def test_preserves_length(self, spatial_gdf):
        result = getis_ord_g(spatial_gdf, "value")
        assert len(result) == len(spatial_gdf)

    def test_hot_cluster_classified_as_hot_not_cold(self):
        # Grilla 8x8 con un cluster 3x3 muy por encima del resto -- valores
        # verificados empíricamente antes de escribir el assert: la esquina
        # (7,7) da g_z=2.47, p_sim<=0.003, clasificada "hot". Con n=16 (otros
        # fixtures del módulo) el contraste no alcanza el umbral |z|>1.96;
        # de ahí la grilla más grande solo para este test.
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        n = 8
        geoms = [box(i, j, i + 1, j + 1) for i in range(n) for j in range(n)]
        values = [
            1000.0 if (i >= n - 3 and j >= n - 3) else 1.0 for i in range(n) for j in range(n)
        ]
        gdf = gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

        result = getis_ord_g(gdf, "value")
        corner_idx = (n - 1) * n + (n - 1)
        assert result.iloc[corner_idx]["hotspot"] == "hot"


class TestMoransI:
    @pytest.fixture
    def gradient_gdf(self):
        """Gradiente monótono 4x4 -> autocorrelación positiva fuerte con
        cualquier esquema de pesos (queen/knn)."""
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [float(i * 4 + j) for i in range(4) for j in range(4)]
        return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

    @pytest.fixture
    def checkerboard_gdf(self):
        """Tablero de ajedrez 4x4 -> con pesos rook (solo ortogonales), cada
        celda tiene únicamente vecinos del valor opuesto: dispersión perfecta."""
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [float((i + j) % 2) for i in range(4) for j in range(4)]
        return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

    def test_returns_expected_keys(self, gradient_gdf):
        result = morans_i(gradient_gdf, "value")
        assert set(result) == {
            "I",
            "EI",
            "p_norm",
            "p_sim",
            "z_norm",
            "significant",
            "interpretation",
        }

    def test_positive_clustering_on_gradient(self, gradient_gdf):
        # n=16 -> EI = -1/(n-1) es exacto sin importar los pesos (verificado
        # empíricamente contra el mismo valor con weight_type="k3").
        result = morans_i(gradient_gdf, "value")
        assert result["I"] > 0.5
        assert result["EI"] == pytest.approx(-1 / 15, abs=1e-4)
        assert result["significant"] is True
        assert "positivo" in result["interpretation"]

    @pytest.mark.parametrize(
        "weight_type,expected_i",
        [("queen", -0.1833), ("rook", -1.0), ("k3", -0.8333), ("k5", -0.2)],
    )
    def test_weight_type_selects_the_right_scheme(self, checkerboard_gdf, weight_type, expected_i):
        # A diferencia del gradiente (donde los 4 esquemas dan I > 0.5 y el
        # mismo EI, sin distinguir entre ellos), el tablero de ajedrez separa
        # los 4 valores de I -- esto sí fija cada rama de _build_weights en
        # vez de solo cubrir la línea (valores verificados empíricamente).
        result = morans_i(checkerboard_gdf, "value", weight_type=weight_type)
        assert result["I"] == pytest.approx(expected_i, abs=1e-3)

    def test_dispersion_interpretation_on_checkerboard_rook(self, checkerboard_gdf):
        result = morans_i(checkerboard_gdf, "value", weight_type="rook")
        assert "dispersión" in result["interpretation"]

    def test_significant_flag_matches_p_sim_threshold(self, gradient_gdf):
        # Umbral que garantiza True (p_sim <= 1 siempre) y uno que garantiza
        # False (p_sim >= 0 siempre) -- no depende del resultado estocástico
        # de las permutaciones de esda.
        assert morans_i(gradient_gdf, "value", significance=1.1)["significant"] is True
        assert morans_i(gradient_gdf, "value", significance=-1.0)["significant"] is False

    def test_large_gdf_logs_warning(self, gradient_gdf, caplog, monkeypatch):
        import estadistica_ambiental.spatial.autocorrelation as autocorr

        # `len` no es un atributo real del módulo (viene de builtins) --
        # raising=False evita el AttributeError de monkeypatch al no
        # encontrarlo antes de crearlo.
        monkeypatch.setattr(autocorr, "len", lambda x: 5001, raising=False)
        with caplog.at_level(logging.WARNING):
            morans_i(gradient_gdf, "value")
        assert "puede ser lento" in caplog.text

    def test_import_error_when_libpysal_missing(self, monkeypatch):
        # Ancla el mensaje propio de morans_i, no solo "algún ImportError en
        # la cadena de imports" -- con sys.modules["libpysal"]=None, esda
        # también lanza su propio ImportError que matchea "pysal|libpysal";
        # sin este regex más estricto el test pasa aunque se borre el
        # try/except entero de morans_i.
        import sys

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(
            ImportError, match=r"pip install pysal esda libpysal  \(o \[spatial\]\)"
        ):
            morans_i(None, "value")


class TestLocalMoransI:
    @pytest.fixture
    def two_cluster_gdf(self):
        """Mitad izquierda (i<2) en 0.0, mitad derecha (i>=2) en 10.0 --
        cada celda de cada mitad solo tiene vecinos de su propio valor
        (verificado empíricamente: lisa_q es 3 (LL) o 1 (HH) en todas las
        filas, nunca 2/4, sin excepción)."""
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("libpysal")
        pytest.importorskip("esda")
        from shapely.geometry import box

        geoms = [box(i, j, i + 1, j + 1) for i in range(4) for j in range(4)]
        values = [10.0 if i >= 2 else 0.0 for i in range(4) for j in range(4)]
        return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs="EPSG:4326")

    def test_adds_expected_columns(self, two_cluster_gdf):
        result = local_morans_i(two_cluster_gdf, "value")
        assert {"lisa_q", "lisa_p", "lisa_sig"} <= set(result.columns)

    def test_preserves_length(self, two_cluster_gdf):
        result = local_morans_i(two_cluster_gdf, "value")
        assert len(result) == len(two_cluster_gdf)

    def test_low_cluster_is_ll_high_cluster_is_hh(self, two_cluster_gdf):
        result = local_morans_i(two_cluster_gdf, "value")
        assert (result.loc[result["value"] == 0.0, "lisa_q"] == 3).all()
        assert (result.loc[result["value"] == 10.0, "lisa_q"] == 1).all()

    def test_lisa_sig_matches_p_threshold(self, two_cluster_gdf):
        result = local_morans_i(two_cluster_gdf, "value")
        assert (result["lisa_sig"] == (result["lisa_p"] < 0.05)).all()

    def test_import_error_when_libpysal_missing(self, monkeypatch):
        # Mismo motivo que en TestMoransI: ancla el mensaje propio de
        # local_morans_i ("pip install pysal esda libpysal", sin el sufijo
        # "(o [spatial])" que sí tienen las otras 3 funciones del módulo).
        import sys

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(ImportError, match=r"^pip install pysal esda libpysal$"):
            local_morans_i(None, "value")


# ---------------------------------------------------------------------------
# spatial/interpolation — Universal Kriging
# ---------------------------------------------------------------------------


class TestUniversalKriging:
    @pytest.fixture
    def stations(self):
        return pd.DataFrame(
            {
                "lat": [4.0, 4.5, 5.0, 4.2, 4.8],
                "lon": [-74.0, -74.5, -73.5, -73.8, -74.2],
                "temp": [18.0, 15.0, 20.0, 17.0, 16.0],
            }
        )

    def test_returns_two_arrays(self, stations):
        pytest.importorskip("pykrige")
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 4), np.linspace(-74.5, -73.5, 4), indexing="ij"
        )
        z, ss = universal_kriging(stations, "lat", "lon", "temp", grid_lat, grid_lon)
        assert z.shape == grid_lat.shape
        assert ss.shape == grid_lat.shape

    def test_variance_non_negative(self, stations):
        pytest.importorskip("pykrige")
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 4), np.linspace(-74.5, -73.5, 4), indexing="ij"
        )
        _, ss = universal_kriging(stations, "lat", "lon", "temp", grid_lat, grid_lon)
        assert np.all(ss >= 0)
        assert np.all(np.isfinite(ss))  # el clip de #16 no debe tapar NaN/inf real
        assert np.any(ss > 0)  # no degeneró a todo-cero

    def test_import_error_without_pykrige(self, stations, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pykrige.uk":
                raise ImportError
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4, 5, 3), np.linspace(-74, -73, 3), indexing="ij"
        )
        with pytest.raises(ImportError):
            universal_kriging(stations, "lat", "lon", "temp", grid_lat, grid_lon)


class TestClipVariance:
    """No depende de pykrige -- ejercita _clip_variance() directo, sin
    importorskip, para que el chequeo de negativos reales corra siempre
    en CI aunque el extra [spatial] no esté instalado."""

    def test_clips_float_noise(self):
        out = _clip_variance(np.array([1.0, -5.90e-14, 0.5]))
        assert np.all(out >= 0)

    def test_warns_on_significant_negative(self, caplog):
        with caplog.at_level(logging.WARNING):
            _clip_variance(np.array([1.0, -3.2, 0.5]))
        assert any("negativa no despreciable" in r.message for r in caplog.records)

    def test_no_warning_for_noise_only(self, caplog):
        with caplog.at_level(logging.WARNING):
            _clip_variance(np.array([1.0, -5.90e-14, 0.5]))
        assert not any("negativa no despreciable" in r.message for r in caplog.records)

    def test_preserves_nan(self):
        out = _clip_variance(np.array([1.0, np.nan, 0.5]))
        assert np.isnan(out[1])

    def test_scale_ignores_infinite_values(self, caplog):
        # Un +inf legitimo en ss no debe desactivar el aviso sobre un negativo real.
        with caplog.at_level(logging.WARNING):
            _clip_variance(np.array([np.inf, -3.2, 0.5]))
        assert any("negativa no despreciable" in r.message for r in caplog.records)

    def test_small_magnitude_field_no_artificial_floor(self, caplog):
        # Campo con valores ~1e-3 (ej. mg/L): un negativo real de -5e-4 no debe
        # esconderse detrás de un piso de escala artificial de 1.0.
        with caplog.at_level(logging.WARNING):
            _clip_variance(np.array([1e-3, -5e-4, 5e-4]))
        assert any("negativa no despreciable" in r.message for r in caplog.records)


class TestOrdinaryKriging:
    @pytest.fixture
    def stations(self):
        return pd.DataFrame(
            {
                "lat": [4.0, 4.5, 5.0, 4.2, 4.8],
                "lon": [-74.0, -74.5, -73.5, -73.8, -74.2],
                "temp": [18.0, 15.0, 20.0, 17.0, 16.0],
            }
        )

    def test_variance_non_negative(self, stations):
        pytest.importorskip("pykrige")
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 4), np.linspace(-74.5, -73.5, 4), indexing="ij"
        )
        _, ss = ordinary_kriging(stations, "lat", "lon", "temp", grid_lat, grid_lon)
        assert np.all(ss >= 0)  # mismo clip de #16 (issue solo probaba universal_kriging)
        assert np.all(np.isfinite(ss))
        assert np.any(ss > 0)


# ---------------------------------------------------------------------------
# spatial/interpolation — IDW (no requiere dependencias opcionales)
# ---------------------------------------------------------------------------


class TestIDW:
    @pytest.fixture
    def stations(self):
        return pd.DataFrame(
            {
                "lat": [4.0, 4.5, 5.0, 4.2],
                "lon": [-74.0, -74.5, -73.5, -73.8],
                "pm25": [15.0, 20.0, 18.0, 12.0],
            }
        )

    def test_returns_array(self, stations):
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 5), np.linspace(-74.5, -73.5, 5), indexing="ij"
        )
        result = idw(stations, "lat", "lon", "pm25", grid_lat, grid_lon)
        assert result.shape == grid_lat.shape

    def test_interpolated_values_in_range(self, stations):
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(4.0, 5.0, 4), np.linspace(-74.5, -73.5, 4), indexing="ij"
        )
        result = idw(stations, "lat", "lon", "pm25", grid_lat, grid_lon)
        assert result.min() >= stations["pm25"].min() - 1
        assert result.max() <= stations["pm25"].max() + 1

    def test_exact_hit_returns_station_value_without_division(self, stations):
        # Un punto de grilla exactamente sobre una estación: dist==0 evitaría
        # una división por cero si se calculara 1/dist**power; debe devolver
        # el valor de la estación tal cual, no NaN/inf.
        grid_lat = np.array([[4.0]])
        grid_lon = np.array([[-74.0]])  # coincide exacto con la 1ra estación
        result = idw(stations, "lat", "lon", "pm25", grid_lat, grid_lon)
        assert result[0, 0] == stations["pm25"].iloc[0]
        assert np.isfinite(result).all()


# ---------------------------------------------------------------------------
# spatial/projections
# ---------------------------------------------------------------------------


class TestProjections:
    def test_bounding_box_colombia(self):
        bbox = bounding_box_colombia()
        lon_min, lat_min, lon_max, lat_max = bbox
        assert lon_min < lon_max
        assert lat_min < lat_max
        assert -83 < lon_min < -81
        assert 12 < lat_max <= 13

    def test_points_to_geodataframe_requires_geopandas(self):
        df = pd.DataFrame({"lat": [4.6], "lon": [-74.1], "value": [10]})
        try:
            gdf = points_to_geodataframe(df)
            assert len(gdf) == 1
        except ImportError:
            pytest.skip("geopandas no instalado")

    def test_points_to_geodataframe_lon_lat_order(self):
        # Point(lon, lat), no Point(lat, lon) -- swap clásico. Bogotá real:
        # lon negativo grande (~-74), lat positivo chico (~4.6); si el orden
        # estuviera invertido, x/y quedarían intercambiados.
        pytest.importorskip("geopandas")
        df = pd.DataFrame({"lat": [4.6], "lon": [-74.1]})
        gdf = points_to_geodataframe(df)
        point = gdf.geometry.iloc[0]
        assert point.x == -74.1
        assert point.y == 4.6

    def test_reproject_sets_crs_when_missing(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(geometry=[Point(-74.1, 4.6)])  # sin CRS
        assert gdf.crs is None
        result = reproject(gdf, from_epsg=4326, to_epsg=3857)
        assert result.crs.to_epsg() == 3857

    def test_reproject_existing_crs(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(geometry=[Point(-74.1, 4.6)], crs="EPSG:4326")
        result = reproject(gdf, from_epsg=4326, to_epsg=3857)
        assert result.crs.to_epsg() == 3857

    def test_clip_to_colombia_drops_points_outside(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"nombre": ["bogota", "origen_atlantico"]},
            geometry=[Point(-74.1, 4.6), Point(0.0, 0.0)],
            crs="EPSG:4326",
        )
        result = clip_to_colombia(gdf)
        assert list(result["nombre"]) == ["bogota"]

    def test_clip_to_colombia_reprojects_before_clipping(self):
        gpd = pytest.importorskip("geopandas")
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"nombre": ["bogota"]}, geometry=[Point(-74.1, 4.6)], crs="EPSG:4326"
        ).to_crs(epsg=3857)
        result = clip_to_colombia(gdf)
        assert len(result) == 1
        assert result.crs.to_epsg() == 4326


# ---------------------------------------------------------------------------
# features/lags
# ---------------------------------------------------------------------------


class TestLags:
    @pytest.fixture
    def df(self):
        return pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=20, freq="D"),
                "pm25": np.random.default_rng(0).normal(15, 3, 20),
            }
        )

    def test_add_lags_creates_columns(self, df):
        result = add_lags(df, "pm25", lags=[1, 3, 7])
        assert "pm25_lag1" in result.columns
        assert "pm25_lag7" in result.columns

    def test_add_rolling_features(self, df):
        result = add_rolling_features(df, "pm25", windows=[3, 7], stats=["mean", "std"])
        assert "pm25_roll3_mean" in result.columns
        assert "pm25_roll7_std" in result.columns

    def test_add_diff_features(self, df):
        result = add_diff_features(df, "pm25", orders=[1, 2])
        assert "pm25_diff1" in result.columns
        assert "pm25_diff2" in result.columns

    def test_drop_na_option(self, df):
        result = add_lags(df, "pm25", lags=[7], drop_na=True)
        assert result["pm25_lag7"].isna().sum() == 0


# ---------------------------------------------------------------------------
# features/calendar
# ---------------------------------------------------------------------------


class TestCalendar:
    @pytest.fixture
    def df(self):
        return pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=30, freq="D"),
                "pm25": range(30),
            }
        )

    def test_cyclical_encoding(self, df):
        result = add_calendar_features(df, "fecha", features=("month",), cyclical=True)
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns

    def test_non_cyclical(self, df):
        result = add_calendar_features(df, "fecha", features=("month",), cyclical=False)
        assert "month" in result.columns

    def test_sin_cos_in_range(self, df):
        result = add_calendar_features(df, "fecha", features=("hour",), cyclical=True)
        assert result["hour_sin"].between(-1, 1).all()


# ---------------------------------------------------------------------------
# features/exogenous
# ---------------------------------------------------------------------------


class TestExogenous:
    def test_heat_index_created(self):
        df = pd.DataFrame({"temp": [25.0, 30.0], "hr": [60.0, 80.0]})
        result = meteorological_features(df, temp_col="temp", humidity_col="hr")
        assert "heat_index" in result.columns

    def test_wind_squared(self):
        df = pd.DataFrame({"viento": [2.0, 4.0]})
        result = meteorological_features(df, wind_col="viento")
        assert "viento_sq" in result.columns
        assert result["viento_sq"].iloc[0] == pytest.approx(4.0)

    def test_rain_binary(self):
        df = pd.DataFrame({"lluvia": [0.0, 5.0, 0.05]})
        result = meteorological_features(df, rain_col="lluvia")
        assert result["lluvia_bin"].tolist() == [0, 1, 0]


# ---------------------------------------------------------------------------
# evaluation/comparison
# ---------------------------------------------------------------------------


class TestComparison:
    @pytest.fixture
    def mock_results(self):
        return {
            "ModelA": {"metrics": {"rmse": 2.0, "mae": 1.5, "r2": 0.85, "smape": 10.0}},
            "ModelB": {"metrics": {"rmse": 3.0, "mae": 2.0, "r2": 0.75, "smape": 15.0}},
            "ModelC": {"metrics": {"rmse": 1.5, "mae": 1.2, "r2": 0.90, "smape": 8.0}},
        }

    def test_rank_models_returns_dataframe(self, mock_results):
        result = rank_models(mock_results, domain="air_quality")
        assert isinstance(result, pd.DataFrame)
        assert "rank" in result.columns

    def test_best_model_has_rank_1(self, mock_results):
        result = rank_models(mock_results, domain="air_quality")
        assert result["rank"].min() == 1

    def test_select_best(self, mock_results):
        best = select_best(mock_results, domain="air_quality")
        assert best == "ModelC"

    def test_custom_weights(self, mock_results):
        result = rank_models(mock_results, weights={"rmse": 1.0})
        assert result.index[0] == "ModelC"


# ---------------------------------------------------------------------------
# preprocessing/imputation
# ---------------------------------------------------------------------------


class TestImputation:
    @pytest.fixture
    def df_missing(self):
        s = pd.Series([1.0, None, None, 4.0, 5.0, None, 7.0])
        return pd.DataFrame({"val": s})

    def test_linear_fills_all(self, df_missing):
        result = impute(df_missing, method="linear")
        assert result["val"].isna().sum() == 0

    def test_ffill(self, df_missing):
        result = impute(df_missing, method="ffill")
        assert result["val"].isna().sum() == 0

    def test_mean_imputation(self, df_missing):
        result = impute(df_missing, method="mean")
        assert result["val"].isna().sum() == 0

    def test_invalid_method_raises(self, df_missing):
        with pytest.raises(ValueError, match="no soportado"):
            impute(df_missing, method="magic")


# ---------------------------------------------------------------------------
# preprocessing/outliers
# ---------------------------------------------------------------------------


class TestOutliers:
    @pytest.fixture
    def df_outlier(self):
        vals = [10.0] * 18 + [1000.0, -500.0]
        return pd.DataFrame({"pm25": vals})

    def test_flag_column_created(self, df_outlier):
        result = flag_outliers(df_outlier, method="iqr")
        assert "pm25_outlier" in result.columns

    def test_outliers_detected(self, df_outlier):
        result = flag_outliers(df_outlier, method="iqr")
        assert result["pm25_outlier"].sum() >= 2

    def test_no_clip_by_default(self, df_outlier):
        result = flag_outliers(df_outlier, method="iqr")
        assert result["pm25"].max() == 1000.0

    def test_clip_when_treat_true(self, df_outlier):
        result = flag_outliers(df_outlier, method="iqr", treat=True, treatment="clip")
        assert result["pm25"].max() < 1000.0

    def test_nan_treatment(self, df_outlier):
        result = flag_outliers(df_outlier, method="iqr", treat=True, treatment="nan")
        assert result["pm25"].isna().sum() >= 2

    def test_invalid_method_raises(self, df_outlier):
        with pytest.raises(ValueError):
            flag_outliers(df_outlier, method="invalid")


# ---------------------------------------------------------------------------
# preprocessing/resampling
# ---------------------------------------------------------------------------


class TestResampling:
    @pytest.fixture
    def daily_df(self):
        return pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=90, freq="D"),
                "pm25": np.random.default_rng(1).normal(15, 3, 90),
            }
        )

    def test_resample_to_monthly(self, daily_df):
        result = resample(daily_df, "fecha", freq="ME")
        assert len(result) < len(daily_df)

    def test_resample_sum(self, daily_df):
        result = resample(daily_df, "fecha", freq="ME", agg="sum")
        assert result["pm25"].iloc[0] > daily_df["pm25"].mean()

    def test_fill_missing_timestamps(self):
        df = pd.DataFrame(
            {
                "fecha": ["2023-01-01", "2023-01-03", "2023-01-05"],
                "val": [1.0, 3.0, 5.0],
            }
        )
        result = fill_missing_timestamps(df, "fecha", freq="D")
        assert len(result) == 5


# ---------------------------------------------------------------------------
# reporting/stats_report
# ---------------------------------------------------------------------------


class TestStatsReport:
    def test_creates_html(self, tmp_path):
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2020-01-01", periods=60, freq="ME"),
                "pm25": np.random.default_rng(5).normal(15, 3, 60),
                "temp": np.random.default_rng(6).normal(14, 2, 60),
            }
        )
        out = tmp_path / "stats.html"
        path = stats_report(df, output=str(out), date_col="fecha")
        assert path.exists()
        content = out.read_text(encoding="utf-8")
        assert "Mann-Kendall" in content
        assert "descriptiva" in content.lower()


# ---------------------------------------------------------------------------
# spatial/projections — ImportError coverage (geopandas no instalado)
# ---------------------------------------------------------------------------


class TestKrigingImportError:
    def test_ordinary_kriging_no_pykrige(self, monkeypatch):
        """ordinary_kriging: ImportError cuando pykrige no está instalado (lines 72-75)."""
        import sys

        import numpy as np
        import pandas as pd

        monkeypatch.setitem(sys.modules, "pykrige", None)
        monkeypatch.setitem(sys.modules, "pykrige.ok", None)
        from estadistica_ambiental.spatial.interpolation import ordinary_kriging

        df = pd.DataFrame(
            {"lat": [4.5, 5.0, 5.5], "lon": [-74.0, -73.5, -73.0], "pm25": [10.0, 15.0, 12.0]}
        )
        lat_g, lon_g = np.meshgrid(np.linspace(4.5, 5.5, 3), np.linspace(-74.0, -73.0, 3))
        with pytest.raises(ImportError, match="pykrige"):
            ordinary_kriging(df, "lat", "lon", "pm25", lat_g, lon_g)


class TestProjectionsImportError:
    def test_reproject_no_geopandas_raises(self, monkeypatch):
        """reproject: ImportError cuando geopandas no está instalado."""
        import sys

        monkeypatch.setitem(sys.modules, "geopandas", None)
        from estadistica_ambiental.spatial.projections import reproject

        with pytest.raises(ImportError, match="geopandas"):
            reproject(None, 4326, 9377)

    def test_clip_to_colombia_no_geopandas_raises(self, monkeypatch):
        """clip_to_colombia: ImportError cuando geopandas no está instalado."""
        import sys

        monkeypatch.setitem(sys.modules, "geopandas", None)
        from estadistica_ambiental.spatial.projections import clip_to_colombia

        with pytest.raises(ImportError, match="geopandas"):
            clip_to_colombia(None)

    def test_bounding_box_colombia_no_deps(self):
        """bounding_box_colombia: no requiere geopandas."""
        from estadistica_ambiental.spatial.projections import bounding_box_colombia

        bbox = bounding_box_colombia(buffer_deg=1.0)
        assert len(bbox) == 4
        assert bbox[0] < bbox[2]  # lon_min < lon_max
        assert bbox[1] < bbox[3]  # lat_min < lat_max


# ---------------------------------------------------------------------------
# spatial/autocorrelation — _interpret_moran (puro) e ImportError paths
# ---------------------------------------------------------------------------


class TestInterpretMoran:
    """Función pura: no requiere libpysal/esda."""

    def test_clustering_positivo(self):
        from estadistica_ambiental.spatial.autocorrelation import _interpret_moran

        result = _interpret_moran(0.5, p=0.01, alpha=0.05)
        assert "clustering" in result
        assert "positivo" in result

    def test_dispersion(self):
        from estadistica_ambiental.spatial.autocorrelation import _interpret_moran

        result = _interpret_moran(-0.4, p=0.01, alpha=0.05)
        assert "dispersión" in result

    def test_no_significativo(self):
        from estadistica_ambiental.spatial.autocorrelation import _interpret_moran

        result = _interpret_moran(0.5, p=0.20, alpha=0.05)
        assert "aleatoria" in result
        assert "no significativo" in result


class TestAutocorrelationImportErrors:
    """Cubre las ramas `except ImportError` cuando libpysal/esda faltan."""

    def test_morans_i_import_error(self, monkeypatch):
        import sys

        from estadistica_ambiental.spatial.autocorrelation import morans_i

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(ImportError, match="pysal|libpysal"):
            morans_i(None, "value")

    def test_geary_c_import_error(self, monkeypatch):
        import sys

        from estadistica_ambiental.spatial.autocorrelation import geary_c

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(ImportError, match="pysal|libpysal"):
            geary_c(None, "value")

    def test_getis_ord_g_import_error(self, monkeypatch):
        import sys

        from estadistica_ambiental.spatial.autocorrelation import getis_ord_g

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(ImportError, match="pysal|libpysal"):
            getis_ord_g(None, "value")

    def test_local_morans_i_import_error(self, monkeypatch):
        import sys

        from estadistica_ambiental.spatial.autocorrelation import local_morans_i

        monkeypatch.setitem(sys.modules, "libpysal", None)
        with pytest.raises(ImportError, match="pysal|libpysal"):
            local_morans_i(None, "value")


# ---------------------------------------------------------------------------
# evaluation/comparison — edge cases en _normalize y rank_models
# ---------------------------------------------------------------------------


class TestComparisonEdgeCases:
    def test_hydrology_domain_inverts_nse_kge(self):
        """En hidrología NSE/KGE son higher-is-better → mayor NSE = menor score."""
        results = {
            "ModelGood": {"metrics": {"nse": 0.85, "kge": 0.80, "rmse": 1.0, "pbias": 5.0}},
            "ModelBad": {"metrics": {"nse": 0.20, "kge": 0.25, "rmse": 3.0, "pbias": 30.0}},
        }
        ranking = rank_models(results, domain="hydrology")
        assert ranking.index[0] == "ModelGood"

    def test_constant_metric_ignored_in_score(self):
        """Métrica con varianza cero (lo == hi) no aporta al ranking."""
        # rmse idéntico en ambos modelos; mae los diferencia
        results = {
            "A": {"metrics": {"rmse": 2.0, "mae": 1.0, "r2": 0.9, "mase": 1.0}},
            "B": {"metrics": {"rmse": 2.0, "mae": 3.0, "r2": 0.9, "mase": 1.0}},
        }
        ranking = rank_models(results, domain="general")
        # A debe ganar gracias a menor MAE; rmse/r2/mase constantes no penalizan
        assert ranking.index[0] == "A"

    def test_missing_metric_does_not_crash(self):
        """Modelo con métrica faltante: fillna(0) lo deja sin penalización en esa métrica."""
        results = {
            "ModelComplete": {"metrics": {"rmse": 2.0, "mae": 1.5, "r2": 0.85, "mase": 1.0}},
            "ModelPartial": {"metrics": {"rmse": 1.5, "mae": 1.0}},  # faltan r2 y mase
        }
        ranking = rank_models(results, domain="general")
        assert "rank" in ranking.columns
        assert len(ranking) == 2

    def test_normalize_all_nan_column(self):
        """_normalize: columna toda NaN → resultado NaN sin crash."""
        from estadistica_ambiental.evaluation.comparison import _normalize

        df = pd.DataFrame({"rmse": [1.0, 2.0, 3.0], "kge": [np.nan, np.nan, np.nan]})
        result = _normalize(df, ["rmse", "kge"])
        assert result["kge"].isna().all()

    def test_normalize_skips_missing_column(self):
        """_normalize: columna que no existe en df se omite limpiamente."""
        from estadistica_ambiental.evaluation.comparison import _normalize

        df = pd.DataFrame({"rmse": [1.0, 2.0]})
        result = _normalize(df, ["rmse", "nse"])
        assert "rmse" in result.columns
        assert "nse" not in result.columns

    def test_select_best_returns_string(self):
        """select_best: tipo de retorno es str (cubre str(...) cast)."""
        results = {
            "X": {"metrics": {"rmse": 2.0, "mae": 1.5, "r2": 0.85, "mase": 1.0}},
            "Y": {"metrics": {"rmse": 5.0, "mae": 4.0, "r2": 0.50, "mase": 2.0}},
        }
        best = select_best(results)
        assert isinstance(best, str)
        assert best == "X"
