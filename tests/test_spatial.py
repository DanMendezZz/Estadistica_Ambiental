"""Tests para spatial/, features/ y reporting/stats_report.py"""

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
from estadistica_ambiental.spatial.interpolation import idw, universal_kriging
from estadistica_ambiental.spatial.projections import bounding_box_colombia, points_to_geodataframe
from estadistica_ambiental.spatial.autocorrelation import geary_c, getis_ord_g, morans_i
from estadistica_ambiental.spatial.analysis import intersection_area, zonal_statistics

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


# ---------------------------------------------------------------------------
# spatial/autocorrelation — geary_c y getis_ord_g
# ---------------------------------------------------------------------------


class TestGearyC:
    @pytest.fixture
    def spatial_gdf(self):
        gpd = pytest.importorskip("geopandas")
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


class TestGetisOrdG:
    @pytest.fixture
    def spatial_gdf(self):
        gpd = pytest.importorskip("geopandas")
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

    def test_import_error_without_pykrige(self, stations, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pykrige.uk":
                raise ImportError
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        grid_lat, grid_lon = np.meshgrid(np.linspace(4, 5, 3), np.linspace(-74, -73, 3), indexing="ij")
        with pytest.raises(ImportError):
            universal_kriging(stations, "lat", "lon", "temp", grid_lat, grid_lon)


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
