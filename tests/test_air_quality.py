"""Tests para preprocessing/air_quality.py — categorize_ica, flag_spatial_episodes, correct_seasonal_bias."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.preprocessing.air_quality import (
    categorize_ica,
    correct_seasonal_bias,
    flag_spatial_episodes,
)

# ---------------------------------------------------------------------------
# Fixtures comunes
# ---------------------------------------------------------------------------

def _make_two_station_df(
    n_per_station: int = 200,
    spike_value: float = 500.0,
    spike_count: int = 6,
    rng_seed: int = 0,
) -> pd.DataFrame:
    """DataFrame mínimo con 2 estaciones cercanas para flag_spatial_episodes."""
    rng = np.random.default_rng(rng_seed)
    dates = pd.date_range("2023-01-01", periods=n_per_station, freq="h")

    base_vals = rng.normal(25.0, 5.0, n_per_station)
    spike_vals = base_vals.copy()
    spike_vals[:spike_count] = spike_value  # primeras horas con pico

    rows = []
    for station, lat, lon, vals in [
        ("A", 4.60, -74.10, spike_vals),
        ("B", 4.65, -74.15, spike_vals),  # vecina cercana (< 10 km)
    ]:
        for ts, v in zip(dates, vals):
            rows.append({"fecha": ts, "estacion": station, "pm25": v,
                         "lat": lat, "lon": lon})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# categorize_ica
# ---------------------------------------------------------------------------

class TestCategorizeIca:
    """Tests unitarios para categorize_ica()."""

    def test_pm25_all_categories(self):
        # Valores representativos de cada una de las 6 categorías
        s = pd.Series([5.0, 20.0, 45.0, 60.0, 200.0, 300.0])
        result = categorize_ica(s, pollutant="pm25")
        expected = [
            "Buena", "Aceptable", "Dañina sensibles",
            "Dañina", "Muy dañina", "Peligrosa",
        ]
        assert list(result) == expected

    def test_pm10_uses_different_breakpoints(self):
        # PM10 "Buena" llega a 54 µg/m³; PM2.5 a ese nivel ya es "Dañina sensibles" (37-55)
        s = pd.Series([50.0])
        cat_pm10 = categorize_ica(s, pollutant="pm10")
        cat_pm25 = categorize_ica(s, pollutant="pm25")
        assert str(cat_pm10.iloc[0]) == "Buena"
        assert str(cat_pm25.iloc[0]) == "Dañina sensibles"

    def test_nan_preserved(self):
        s = pd.Series([10.0, np.nan, 50.0])
        result = categorize_ica(s, pollutant="pm25")
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[0])
        assert not pd.isna(result.iloc[2])

    def test_all_nan_series(self):
        s = pd.Series([np.nan, np.nan])
        result = categorize_ica(s, pollutant="pm25")
        assert result.isna().all()

    def test_unknown_pollutant_falls_back_to_pm25(self):
        # Contaminante desconocido → fallback a PM2.5 con warning (no crash)
        s = pd.Series([10.0])
        result = categorize_ica(s, pollutant="ch4")  # no implementado
        assert str(result.iloc[0]) == "Buena"

    def test_invalid_standard_raises(self):
        s = pd.Series([10.0])
        with pytest.raises(ValueError, match="no implementada"):
            categorize_ica(s, standard="epa_2024")

    def test_result_is_categorical(self):
        s = pd.Series([10.0, 20.0])
        result = categorize_ica(s)
        assert hasattr(result, "cat"), "Resultado debe ser pd.Categorical"

    def test_o3_categories(self):
        # O3 Buena: ≤ 100 µg/m³; Aceptable: 101-160
        s = pd.Series([80.0, 130.0])
        result = categorize_ica(s, pollutant="o3")
        assert str(result.iloc[0]) == "Buena"
        assert str(result.iloc[1]) == "Aceptable"

    def test_boundary_value_pm25_37(self):
        # 37 µg/m³ es el límite de Aceptable (inclusive derecho)
        s = pd.Series([37.0])
        result = categorize_ica(s, pollutant="pm25")
        assert str(result.iloc[0]) == "Aceptable"

    def test_boundary_value_pm25_just_above_37(self):
        s = pd.Series([37.01])
        result = categorize_ica(s, pollutant="pm25")
        assert str(result.iloc[0]) == "Dañina sensibles"


# ---------------------------------------------------------------------------
# flag_spatial_episodes
# ---------------------------------------------------------------------------

class TestFlagSpatialEpisodes:
    """Tests para flag_spatial_episodes()."""

    def test_output_has_flag_column(self):
        df = _make_two_station_df()
        result = flag_spatial_episodes(
            df, "pm25", "estacion", "fecha", "lat", "lon",
            min_consecutive_hours=4,
        )
        assert "flag_episode" in result.columns

    def test_original_flag_default(self):
        # Sin valores extremos no debe haber episodios_criticos (picos sostenidos confirmados por vecinas)
        rng = np.random.default_rng(1)
        dates = pd.date_range("2023-01-01", periods=200, freq="h")
        df = pd.DataFrame({
            "fecha": list(dates) * 2,
            "estacion": ["A"] * 200 + ["B"] * 200,
            "pm25": rng.normal(20.0, 2.0, 400),
            "lat": [4.60] * 200 + [4.65] * 200,
            "lon": [-74.10] * 200 + [-74.15] * 200,
        })
        result = flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        # cap_absoluto puede aparecer por la cola de una distribución normal (percentil 99.9)
        # pero episodio_critico requiere ≥4h consecutivas confirmadas por vecinas → no ocurre
        assert "episodio_critico" not in result["flag_episode"].values

    def test_cap_absoluto_tagged_for_extreme_spike(self):
        # Valores estrictamente por encima del percentil 99.9 → cap_absoluto.
        # Con 3 spikes a valores escalonados (50k, 60k, 70k) en una sola estación,
        # quantile(0.999) queda entre 50k y 70k → el de 70k es > cap_value.
        rng = np.random.default_rng(7)
        n = 200
        dates = pd.date_range("2023-01-01", periods=n, freq="h")
        vals_a = rng.normal(25.0, 5.0, n)
        vals_a[0] = 50_000.0
        vals_a[1] = 60_000.0
        vals_a[2] = 70_000.0  # estrictamente > quantile(0.999)
        vals_b = rng.normal(25.0, 5.0, n)
        rows = (
            [{"fecha": ts, "estacion": "A", "pm25": v, "lat": 4.60, "lon": -74.10}
             for ts, v in zip(dates, vals_a)]
            + [{"fecha": ts, "estacion": "B", "pm25": v, "lat": 4.65, "lon": -74.15}
               for ts, v in zip(dates, vals_b)]
        )
        df = pd.DataFrame(rows)
        result = flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        assert "cap_absoluto" in result["flag_episode"].values

    def test_episodio_critico_preserved_value_col(self):
        # Los valores marcados como episodio_critico NO deben ser reemplazados
        df = _make_two_station_df(spike_value=500.0, spike_count=6)
        result = flag_spatial_episodes(
            df, "pm25", "estacion", "fecha", "lat", "lon",
            min_consecutive_hours=4,
        )
        episodios = result[result["flag_episode"] == "episodio_critico"]
        if len(episodios) > 0:
            # Valor debe seguir siendo ~500, no mediana local
            assert episodios["pm25"].mean() > 100.0

    def test_missing_column_raises_key_error(self):
        df = _make_two_station_df()
        df = df.drop(columns=["lat"])
        with pytest.raises(KeyError):
            flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")

    def test_output_has_same_row_count(self):
        df = _make_two_station_df()
        result = flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        assert len(result) == len(df)

    def test_no_month_column_leaked(self):
        df = _make_two_station_df()
        result = flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        assert "_month" not in result.columns

    def test_only_valid_flags(self):
        df = _make_two_station_df(spike_value=500.0, spike_count=8)
        result = flag_spatial_episodes(df, "pm25", "estacion", "fecha", "lat", "lon")
        valid_flags = {"original", "cap_absoluto", "episodio_critico", "iqr_hard", "iqr_soft"}
        assert set(result["flag_episode"].unique()).issubset(valid_flags)

    def test_iqr_soft_values_replaced_by_median(self):
        # Outliers suaves (iqr_soft) deben tener valor imputado < spike original
        df = _make_two_station_df(spike_value=120.0, spike_count=2)
        result = flag_spatial_episodes(
            df, "pm25", "estacion", "fecha", "lat", "lon",
            min_consecutive_hours=4,
        )
        soft = result[result["flag_episode"] == "iqr_soft"]
        if len(soft) > 0:
            assert soft["pm25"].max() < 120.0


# ---------------------------------------------------------------------------
# correct_seasonal_bias
# ---------------------------------------------------------------------------

class TestCorrectSeasonalBias:
    """Tests para correct_seasonal_bias()."""

    @pytest.fixture
    def uniform_bias_data(self):
        """Predicciones con sesgo constante de +10 en todos los meses."""
        dates = pd.date_range("2022-01-01", periods=365, freq="D")
        actuals = pd.Series(np.full(365, 30.0))
        predictions = pd.Series(np.full(365, 40.0))  # +10 constante
        time_col = pd.Series(dates)
        return predictions, actuals, time_col

    def test_corrected_reduces_bias(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        corrected, bias_table = correct_seasonal_bias(preds, actuals, time_col)
        # Después de corregir +10, predicción debe ser ~30
        assert abs(corrected.mean() - 30.0) < 0.5

    def test_bias_table_columns(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        _, bias_table = correct_seasonal_bias(preds, actuals, time_col)
        assert set(["periodo", "sesgo", "n_obs", "sesgo_std"]).issubset(bias_table.columns)

    def test_bias_table_has_12_months(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        _, bias_table = correct_seasonal_bias(preds, actuals, time_col, by="month")
        assert len(bias_table) == 12

    def test_bias_table_positive_sesgo_for_overestimate(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        _, bias_table = correct_seasonal_bias(preds, actuals, time_col)
        # Todas las predicciones sobreestiman → sesgo > 0
        assert (bias_table["sesgo"] > 0).all()

    def test_quarter_granularity(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        _, bias_table = correct_seasonal_bias(preds, actuals, time_col, by="quarter")
        assert len(bias_table) == 4

    def test_invalid_by_raises_value_error(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        with pytest.raises(ValueError, match="'by' debe ser"):
            correct_seasonal_bias(preds, actuals, time_col, by="decade")

    def test_length_mismatch_raises_value_error(self):
        preds = pd.Series([1.0, 2.0])
        actuals = pd.Series([1.0])
        time_col = pd.Series(pd.date_range("2022-01-01", periods=2))
        with pytest.raises(ValueError, match="misma longitud"):
            correct_seasonal_bias(preds, actuals, time_col)

    def test_corrected_preserves_index(self, uniform_bias_data):
        preds, actuals, time_col = uniform_bias_data
        corrected, _ = correct_seasonal_bias(preds, actuals, time_col)
        assert len(corrected) == len(preds)

    def test_zero_bias_unchanged(self):
        # Si pred == actual, corrección debe ser cero
        dates = pd.date_range("2022-01-01", periods=365, freq="D")
        vals = pd.Series(np.random.default_rng(42).normal(30.0, 5.0, 365))
        corrected, bias_table = correct_seasonal_bias(
            vals.copy(), vals.copy(), pd.Series(dates)
        )
        assert (bias_table["sesgo"].abs() < 1e-10).all()
        pd.testing.assert_series_equal(corrected, vals, check_names=False)

    def test_by_week_has_many_periods(self):
        dates = pd.date_range("2022-01-01", periods=365, freq="D")
        vals = pd.Series(np.full(365, 30.0))
        preds = pd.Series(np.full(365, 35.0))
        _, bias_table = correct_seasonal_bias(preds, vals, pd.Series(dates), by="week")
        assert len(bias_table) >= 52
