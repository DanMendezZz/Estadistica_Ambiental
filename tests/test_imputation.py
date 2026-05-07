"""Tests para preprocessing/imputation.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.preprocessing.imputation import impute

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def df_with_gaps():
    np.random.seed(0)
    n = 60
    vals = np.random.normal(20, 5, n)
    idx_na = [5, 10, 20, 21, 22, 40]
    vals[idx_na] = np.nan
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=n, freq="D"),
            "pm25": vals,
            "temperatura": np.random.normal(15, 3, n),
        }
    )


# ---------------------------------------------------------------------------
# Métodos básicos
# ---------------------------------------------------------------------------


class TestImpute:
    def test_linear_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="linear")
        assert result["pm25"].isna().sum() == 0

    def test_ffill_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="ffill")
        assert result["pm25"].isna().sum() == 0

    def test_bfill_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="bfill")
        assert result["pm25"].isna().sum() == 0

    def test_mean_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="mean")
        assert result["pm25"].isna().sum() == 0

    def test_median_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="median")
        assert result["pm25"].isna().sum() == 0

    def test_rolling_mean_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="rolling_mean", window=7)
        assert result["pm25"].isna().sum() == 0

    def test_mice_removes_nans(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="mice")
        assert result["pm25"].isna().sum() == 0

    def test_kalman_fallback_to_linear(self, df_with_gaps):
        # pykalman no instalado → fallback lineal, no debe levantar excepción
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="kalman")
        assert result["pm25"].isna().sum() == 0

    def test_unknown_method_raises(self, df_with_gaps):
        with pytest.raises(ValueError, match="no soportado"):
            impute(df_with_gaps.copy(), cols=["pm25"], method="brits")

    def test_auto_detects_numeric_cols(self, df_with_gaps):
        result = impute(df_with_gaps.copy(), method="mean")
        assert result["pm25"].isna().sum() == 0

    def test_preserves_non_target_cols(self, df_with_gaps):
        original_fecha = df_with_gaps["fecha"].copy()
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="linear")
        pd.testing.assert_series_equal(result["fecha"], original_fecha)

    def test_kalman_real_imputation_recovers_sine(self):
        """_kalman: imputación numérica real sobre seno con NaNs cada 5 muestras.

        Valida que el filtro de Kalman (vía pykalman) reconstruye una señal
        determinista con error razonable (RMSE < 2× std de la señal).
        """
        pytest.importorskip("pykalman")

        n = 100
        t = np.arange(n)
        ground_truth = np.sin(2 * np.pi * t / 20.0) * 5.0 + 10.0
        values = ground_truth.copy()
        nan_idx = np.arange(0, n, 5)  # NaN cada 5 muestras
        values[nan_idx] = np.nan

        df = pd.DataFrame({"pm25": values})
        result = impute(df, cols=["pm25"], method="kalman")

        # Sin NaN restantes
        assert result["pm25"].isna().sum() == 0
        # Valores plausibles dentro del rango original (con margen)
        signal_std = ground_truth.std()
        rng_min, rng_max = ground_truth.min() - signal_std, ground_truth.max() + signal_std
        assert result["pm25"].between(rng_min, rng_max).all()
        # RMSE solo sobre los puntos imputados, tolerancia generosa
        rmse = np.sqrt(np.mean((result["pm25"].values[nan_idx] - ground_truth[nan_idx]) ** 2))
        assert rmse < 2 * signal_std, f"RMSE {rmse:.3f} excede 2× std ({2 * signal_std:.3f})"

    def test_mice_real_imputation_plausible_values(self):
        """_mice: imputación numérica real con IterativeImputer.

        Valida que la imputación múltiple devuelve valores en el rango de los
        datos originales y reduce el error vs. imputación trivial (constante=0).
        """
        pytest.importorskip("sklearn")

        rng = np.random.default_rng(42)
        n = 80
        ground_truth = rng.normal(loc=20.0, scale=4.0, size=n)
        values = ground_truth.copy()
        nan_idx = np.array([7, 15, 23, 31, 47, 55, 63, 71])
        values[nan_idx] = np.nan

        df = pd.DataFrame({"pm25": values})
        result = impute(df, cols=["pm25"], method="mice")

        # Sin NaN restantes
        assert result["pm25"].isna().sum() == 0
        # Valores plausibles: dentro de min/max ± std del ground truth
        signal_std = ground_truth.std()
        rng_min = ground_truth.min() - signal_std
        rng_max = ground_truth.max() + signal_std
        assert result["pm25"].between(rng_min, rng_max).all()
        # RMSE razonable sobre puntos imputados (< 2× std de la señal)
        rmse = np.sqrt(np.mean((result["pm25"].values[nan_idx] - ground_truth[nan_idx]) ** 2))
        assert rmse < 2 * signal_std, f"RMSE {rmse:.3f} excede 2× std ({2 * signal_std:.3f})"

    def test_mean_imputed_value_is_column_mean(self):
        s = pd.DataFrame({"v": [10.0, np.nan, 20.0]})
        result = impute(s, cols=["v"], method="mean")
        assert result["v"].iloc[1] == pytest.approx(15.0)

    def test_median_imputed_value_is_column_median(self):
        s = pd.DataFrame({"v": [10.0, np.nan, 30.0, 30.0]})
        result = impute(s, cols=["v"], method="median")
        assert result["v"].iloc[1] == pytest.approx(30.0)

    def test_rolling_mean_custom_window(self, df_with_gaps):
        # window=7 cubre los gaps consecutivos de 3 en el fixture
        result = impute(df_with_gaps.copy(), cols=["pm25"], method="rolling_mean", window=7)
        assert result["pm25"].isna().sum() == 0

    def test_no_nans_unchanged_by_mean(self):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0]})
        result = impute(df.copy(), cols=["v"], method="mean")
        pd.testing.assert_series_equal(result["v"], df["v"])
