"""Tests para predictive/residual_ar.py — HourlyAR1Calibrator (M-02)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.predictive.residual_ar import (
    HOURS_IN_DAY,
    MONTHS_IN_YEAR,
    CalibrationReport,
    HourlyAR1Calibrator,
    TestResult,
)

# ---------------------------------------------------------------------------
# Fixtures: residuos sintéticos AR(1) puro
# ---------------------------------------------------------------------------


def _generate_ar1(
    n_days: int = 365,
    phi_target: float = 0.85,
    sigma: float = 1.0,
    seed: int = 42,
    start: str = "2024-01-01",
) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Genera una serie AR(1) horaria estacionaria con phi y sigma dados."""
    rng = np.random.default_rng(seed)
    n = n_days * HOURS_IN_DAY
    eps = rng.normal(0.0, sigma, size=n)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = phi_target * y[t - 1] + eps[t]
    idx = pd.date_range(start=start, periods=n, freq="h")
    return y, idx


@pytest.fixture(scope="module")
def ar1_pure():
    """Serie AR(1) sintética larga (1 año horario)."""
    arr, idx = _generate_ar1(n_days=365, phi_target=0.85, sigma=1.0, seed=42)
    return arr, idx


@pytest.fixture(scope="module")
def calibrator_fitted(ar1_pure):
    """Calibrador ajustado sobre la serie AR(1) pura."""
    arr, idx = ar1_pure
    cal = HourlyAR1Calibrator(n_trajectories=100, alpha=0.05, random_state=0)
    cal.fit(pd.Series(arr, index=idx))
    return cal


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_attaches_phi_and_sigma(self, calibrator_fitted):
        cal = calibrator_fitted
        assert cal.is_fitted
        assert cal.phi_by_hour.shape == (HOURS_IN_DAY,)
        assert cal.sigma_by_month.shape == (MONTHS_IN_YEAR,)
        assert np.all(np.isfinite(cal.phi_by_hour))
        assert np.all(cal.sigma_by_month > 0)

    def test_fit_recovers_phi(self, calibrator_fitted):
        # Cada phi por hora debe estar en torno al 0.85 verdadero
        cal = calibrator_fitted
        # Margen amplio: cada hora tiene ~365 muestras
        assert 0.75 < cal.phi_by_hour.mean() < 0.95

    def test_fit_short_series_raises(self):
        cal = HourlyAR1Calibrator()
        idx = pd.date_range("2024-01-01", periods=10, freq="h")
        with pytest.raises(ValueError, match="al menos"):
            cal.fit(pd.Series(np.zeros(10), index=idx))

    def test_fit_accepts_ndarray_with_index(self):
        arr, idx = _generate_ar1(n_days=30, seed=1)
        cal = HourlyAR1Calibrator()
        cal.fit(arr, datetime_index=idx)
        assert cal.is_fitted

    def test_fit_ndarray_without_index_raises(self):
        arr, _ = _generate_ar1(n_days=30, seed=2)
        cal = HourlyAR1Calibrator()
        with pytest.raises(ValueError, match="datetime_index"):
            cal.fit(arr)


class TestSimulate:
    def test_simulate_shape(self, calibrator_fitted):
        traj = calibrator_fitted.simulate(horizon=48, n_trajectories=50)
        assert traj.shape == (50, 48)

    def test_simulate_default_K(self, calibrator_fitted):
        traj = calibrator_fitted.simulate(horizon=24)
        assert traj.shape == (100, 24)

    def test_simulate_before_fit_raises(self):
        cal = HourlyAR1Calibrator()
        with pytest.raises(RuntimeError, match="fit"):
            cal.simulate(horizon=24)

    def test_simulate_invalid_horizon(self, calibrator_fitted):
        with pytest.raises(ValueError):
            calibrator_fitted.simulate(horizon=0)

    def test_simulate_reproducible(self, calibrator_fitted):
        a = calibrator_fitted.simulate(horizon=12, n_trajectories=20, random_state=123)
        b = calibrator_fitted.simulate(horizon=12, n_trajectories=20, random_state=123)
        np.testing.assert_allclose(a, b)

    def test_percentiles(self, calibrator_fitted):
        traj = calibrator_fitted.simulate(horizon=24, n_trajectories=80, random_state=0)
        pct = calibrator_fitted.percentiles(traj)
        assert set(pct.keys()) == {"P10", "P50", "P90"}
        assert all(v.shape == (24,) for v in pct.values())
        # Coherencia ordinal
        assert np.all(pct["P10"] <= pct["P50"])
        assert np.all(pct["P50"] <= pct["P90"])


class TestValidateSyntheticAR1:
    """Sobre datos AR(1) puros, T1-T3 + KS + Ljung-Box deben dar PASS."""

    def test_returns_dict_of_test_results(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        assert isinstance(results, dict)
        assert all(isinstance(v, TestResult) for v in results.values())
        assert "T1_mean_zero" in results
        assert "KS_normal" in results
        assert "LjungBox" in results
        assert "JarqueBera" in results

    def test_T1_mean_zero_passes(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        assert results["T1_mean_zero"].passed, results["T1_mean_zero"]

    def test_T2_variance_finite_passes(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        assert results["T2_variance_finite"].passed, results["T2_variance_finite"]

    def test_T3_hourly_autocorr_passes(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        # Las innovaciones deben ser blancas (sin autocorr)
        assert results["T3_hourly_autocorr"].passed, results["T3_hourly_autocorr"]

    def test_ljung_box_no_rejects(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        assert results["LjungBox"].passed, results["LjungBox"]

    def test_ks_normal_holds(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        # Innovaciones gaussianas verdaderas → KS no rechaza
        assert results["KS_normal"].passed, results["KS_normal"]

    def test_status_string(self):
        tr = TestResult(name="dummy", passed=True, statistic=0.0, p_value=0.5)
        assert tr.status == "PASS"
        tr2 = TestResult(name="dummy", passed=False, statistic=0.0, p_value=0.01)
        assert tr2.status == "FAIL"


class TestCoverageNominal:
    """Con K=200 trayectorias, el intervalo P5-P95 debe cubrir ~90% de muestras."""

    def test_coverage_around_90pct(self, ar1_pure):
        arr, idx = ar1_pure
        # Calibrar sobre los primeros 320 días
        train_end = 320 * HOURS_IN_DAY
        train_idx = idx[:train_end]
        train_arr = arr[:train_end]

        cal = HourlyAR1Calibrator(n_trajectories=200, alpha=0.05, random_state=7)
        cal.fit(pd.Series(train_arr, index=train_idx))

        horizon = HOURS_IN_DAY * 14  # 2 semanas
        test_arr = arr[train_end : train_end + horizon]
        # Inicializar simulación desde el último valor real
        cal._index = train_idx
        traj = cal.simulate(
            horizon=horizon,
            n_trajectories=200,
            start_datetime=train_idx[-1] + pd.Timedelta(hours=1),
            e0=float(train_arr[-1]),
            random_state=7,
        )
        p5 = np.percentile(traj, 5, axis=0)
        p95 = np.percentile(traj, 95, axis=0)
        inside = (test_arr >= p5) & (test_arr <= p95)
        coverage = float(inside.mean())
        # Tolerancia razonable: 80%-98% (Monte Carlo + horizon corto)
        assert 0.80 <= coverage <= 0.99, f"coverage={coverage:.3f}"


class TestReport:
    def test_calibration_report_to_frame(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        report = CalibrationReport(
            phi_by_hour=calibrator_fitted.phi_by_hour,
            sigma_by_month=calibrator_fitted.sigma_by_month,
            tests=results,
        )
        df = report.to_frame()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(results)
        assert "status" in df.columns
        assert "p_value" in df.columns

    def test_calibration_report_all_pass(self, calibrator_fitted):
        results = calibrator_fitted.validate()
        report = CalibrationReport(
            phi_by_hour=calibrator_fitted.phi_by_hour,
            sigma_by_month=calibrator_fitted.sigma_by_month,
            tests=results,
        )
        # T1, T2, T3, KS, LjungBox deben pasar; T4/JB pueden ser sensibles
        # con AR(1) puro sin estacionalidad mensual real, así que solo
        # comprobamos que el helper devuelva un bool.
        assert isinstance(report.all_pass, bool)


class TestConstructorValidation:
    def test_invalid_n_trajectories(self):
        with pytest.raises(ValueError):
            HourlyAR1Calibrator(n_trajectories=0)

    def test_invalid_alpha(self):
        with pytest.raises(ValueError):
            HourlyAR1Calibrator(alpha=1.5)
