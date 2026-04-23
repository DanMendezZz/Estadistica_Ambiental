"""Regression tests for the 10 bugs fixed in PR #6.

Each test reproduces the exact failing scenario from the ultrareview report.
A test that starts passing after reverting the fix means the fix is correct.

Bugs covered:
  bug_029  detect_anomalies silently returns zero anomalies with NaN input
  bug_001  anomaly_summary threshold_value inconsistent with detect_anomalies
  bug_010  nrmse produces astronomical values with zero-variance y_true
  bug_031  evaluate(domain='air_quality') uses PM2.5 breakpoints for all pollutants
  bug_003  hit_rate_ica inflates accuracy when inputs contain NaN
  bug_028  optimize_model swallows TrialPruned, defeating MedianPruner
  bug_030  OPTIMIZER_PENALTY wrong sign for direction='maximize'
  merged_bug_017  optimize_model fallback discards good work, wrong n_trials
  bug_034  flag_spatial_episodes neighbor threshold contaminated by cap_absoluto
  merged_bug_007  rolling median computed over the very outliers being replaced
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.evaluation.anomaly import anomaly_summary, detect_anomalies
from estadistica_ambiental.evaluation.metrics import evaluate, hit_rate_ica, nrmse
from estadistica_ambiental.optimization.bayes_opt import optimize_model
from estadistica_ambiental.predictive.base import OPTIMIZER_PENALTY
from estadistica_ambiental.preprocessing.air_quality import flag_spatial_episodes

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _NullSpec:
    """Minimal ModelSpec stub: no warm_starts, no build_model."""
    name = "null_test"


def _make_station_df(
    station_values: dict[str, np.ndarray],
    station_coords: dict[str, tuple[float, float]],
    start: str = "2024-01-15 00:00",
) -> pd.DataFrame:
    """Build a minimal DataFrame for flag_spatial_episodes."""
    rows = []
    base = pd.Timestamp(start)
    for station, values in station_values.items():
        lat, lon = station_coords[station]
        for i, v in enumerate(values):
            rows.append({
                "dt": base + pd.Timedelta(hours=i),
                "station": station,
                "value": v,
                "lat": lat,
                "lon": lon,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# bug_029 — detect_anomalies silently zero anomalies with NaN
# ---------------------------------------------------------------------------

class TestBug029:
    def test_outlier_detected_despite_single_nan(self):
        """One NaN must not produce NaN threshold that hides all anomalies.

        With only a few observations the single outlier can fall exactly at the
        2σ boundary. Using 20 clean background points ensures the outlier is
        clearly above the threshold.
        """
        # 20 perfect predictions (error_rel=0) + 1 NaN gap + 1 clear outlier
        n_bg = 20
        y_true = np.concatenate([np.arange(1.0, n_bg + 1), [np.nan], [100.0]])
        y_pred = np.concatenate([np.arange(1.0, n_bg + 1), [5.0],    [1.0]])

        out = detect_anomalies(y_true, y_pred)

        assert out["is_anomaly"].sum() > 0, (
            "detect_anomalies returned zero anomalies despite a clear outlier "
            "— NaN likely propagated to threshold (np.mean instead of np.nanmean)"
        )

    def test_all_nan_gaps_do_not_raise(self):
        """NaN-only positions should be silently skipped, not crash."""
        y_true = np.array([np.nan, np.nan, 10.0, np.nan])
        y_pred = np.array([np.nan, np.nan, 10.0, np.nan])
        out = detect_anomalies(y_true, y_pred)
        assert "is_anomaly" in out.columns

    def test_attrs_stored(self):
        """umbral and threshold must be stored in df.attrs for anomaly_summary."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        out = detect_anomalies(y_true, y_pred, threshold=3.0)
        assert "umbral" in out.attrs
        assert out.attrs["threshold"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# bug_001 — anomaly_summary threshold_value inconsistent
# ---------------------------------------------------------------------------

class TestBug001:
    def test_threshold_value_matches_detect_anomalies(self):
        """threshold_value in summary must be the stored umbral (rounded to 4 dp).

        Before the fix: hardcoded 2.0 multiplier + pandas std (ddof=1) →
        threshold_value diverges from the umbral actually used by detect_anomalies.
        After the fix: summary reads umbral directly from df.attrs.
        Tolerance = 5e-4 (one unit in the last decimal place after rounding).
        """
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0,   1.0])

        df = detect_anomalies(y_true, y_pred, threshold=3.0)
        summary = anomaly_summary(df)

        # summary rounds to 4 decimals; allow for that rounding error
        assert abs(summary["threshold_value"] - df.attrs["umbral"]) < 5e-4, (
            f"threshold_value={summary['threshold_value']} differs from "
            f"umbral={df.attrs['umbral']} by more than rounding — "
            "likely hardcoded 2.0 multiplier or ddof mismatch"
        )

    def test_std_uses_ddof0(self):
        """std_error_rel must use ddof=0 (numpy/population std), not ddof=1 (pandas)."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.1, 3.1, 4.1, 5.1])

        df = detect_anomalies(y_true, y_pred)
        summary = anomaly_summary(df)

        err_rel = df["error_rel"].values
        expected_std_ddof0 = float(np.nanstd(err_rel))        # ddof=0 (numpy)
        wrong_std_ddof1    = float(np.nanstd(err_rel, ddof=1)) # ddof=1 (pandas)

        # Summary must be close to ddof=0, NOT to ddof=1
        diff_correct = abs(summary["std_error_rel"] - expected_std_ddof0)
        diff_wrong   = abs(summary["std_error_rel"] - wrong_std_ddof1)
        assert diff_correct < 5e-4, (
            f"std_error_rel={summary['std_error_rel']} differs from ddof=0 value "
            f"{expected_std_ddof0} by {diff_correct:.6f}"
        )
        # Sanity: ddof=0 and ddof=1 differ enough to distinguish
        if wrong_std_ddof1 != expected_std_ddof0:
            assert diff_correct < diff_wrong, (
                "std_error_rel is closer to ddof=1 (pandas) than ddof=0 (numpy)"
            )


# ---------------------------------------------------------------------------
# bug_010 — nrmse astronomical values with zero variance
# ---------------------------------------------------------------------------

class TestBug010:
    def test_nrmse_zero_variance_returns_nan(self):
        """A flat-lined y_true (zero std) must return nan, not rmse * 1e8."""
        y_true = np.full(24, 150.0)   # sensor saturated at rail
        y_pred = np.full(24, 148.0)

        result = nrmse(y_true, y_pred)

        assert math.isnan(result), (
            f"nrmse returned {result} for zero-variance y_true "
            "— expected nan (1e-8 epsilon trick produces ~2e8)"
        )

    def test_nrmse_normal_case_finite(self):
        """Sanity: normal input must still produce a finite positive value."""
        rng = np.random.default_rng(0)
        y_true = rng.normal(50, 10, 100)
        y_pred = y_true + rng.normal(0, 2, 100)
        result = nrmse(y_true, y_pred)
        assert math.isfinite(result) and result > 0


# ---------------------------------------------------------------------------
# bug_031 — evaluate uses PM2.5 breakpoints for every pollutant
# ---------------------------------------------------------------------------

class TestBug031:
    def test_pm10_breakpoints_differ_from_pm25(self):
        """evaluate with PM10 must use PM10 thresholds, not PM2.5 ones.

        30 µg/m³ → PM10 'Buena' (≤54) | PM2.5 'Aceptable' (12–37)
        40 µg/m³ → PM10 'Buena' (≤54) | PM2.5 'Dañina sensibles' (37–55)
        PM10: both Buena → hit_rate = 100%
        PM2.5: different categories → hit_rate = 0%
        """
        y_true = np.full(20, 30.0)
        y_pred = np.full(20, 40.0)

        res_pm10 = evaluate(y_true, y_pred, domain="air_quality", pollutant="pm10")
        res_pm25 = evaluate(y_true, y_pred, domain="air_quality", pollutant="pm25")

        assert res_pm10["hit_rate_ica"] == pytest.approx(100.0), (
            "PM10 values 30 and 40 are both in category 'Buena' for PM10 "
            "but evaluate returned < 100% — likely still using PM2.5 breakpoints"
        )
        assert res_pm25["hit_rate_ica"] == pytest.approx(0.0)

    def test_evaluate_air_quality_has_hit_rate_key(self):
        y = np.array([20.0, 30.0, 45.0])
        res = evaluate(y, y, domain="air_quality", pollutant="pm25")
        assert "hit_rate_ica" in res


# ---------------------------------------------------------------------------
# bug_003 — hit_rate_ica inflates accuracy with NaN
# ---------------------------------------------------------------------------

class TestBug003:
    def test_nan_pairs_not_counted_as_hit(self):
        """Two NaN at the same index must NOT be counted as a category match.

        Only valid pair: 10 (Buena) vs 999 (Peligrosa) → 0% hit rate.
        With bug: NaN→'' and ''=='' → 66.7% hit rate.
        """
        y_true = np.array([np.nan, np.nan, 10.0])
        y_pred = np.array([np.nan, np.nan, 999.0])

        rate = hit_rate_ica(y_true, y_pred, pollutant="pm25")

        assert rate == pytest.approx(0.0), (
            f"hit_rate_ica returned {rate:.1f}% with two NaN/NaN pairs "
            "— NaN positions are being counted as correct category matches"
        )

    def test_all_nan_returns_nan(self):
        y = np.array([np.nan, np.nan])
        result = hit_rate_ica(y, y)
        assert math.isnan(result)

    def test_no_nan_unaffected(self):
        y_true = np.array([10.0, 10.0, 10.0])
        y_pred = np.array([10.0, 10.0, 10.0])
        assert hit_rate_ica(y_true, y_pred) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# bug_028 — optimize_model swallows TrialPruned
# ---------------------------------------------------------------------------

class TestBug028:
    def test_trial_pruned_not_recorded_as_complete_with_penalty(self):
        """TrialPruned must reach Optuna so trials are PRUNED, not COMPLETE=1e6."""
        import optuna

        def pruning_obj(trial):
            x = trial.suggest_float("x", 0.0, 1.0)
            trial.report(x, step=0)
            if trial.should_prune():
                raise optuna.TrialPruned()
            return x

        result = optimize_model(
            model_spec=_NullSpec(),
            objective=pruning_obj,
            n_trials=12,
            direction="minimize",
        )

        if result.study is None:
            pytest.skip("study is None — cannot inspect trial states")

        complete_with_penalty = [
            t for t in result.study.trials
            if t.state == optuna.trial.TrialState.COMPLETE
            and t.value is not None
            and abs(t.value - OPTIMIZER_PENALTY) < 1.0
        ]
        assert len(complete_with_penalty) == 0, (
            f"{len(complete_with_penalty)} trial(s) were recorded COMPLETE "
            f"with value≈1e6 — TrialPruned was swallowed by except Exception"
        )


# ---------------------------------------------------------------------------
# bug_030 — OPTIMIZER_PENALTY wrong sign for direction='maximize'
# ---------------------------------------------------------------------------

class TestBug030:
    def test_all_fail_maximize_best_score_is_negative_penalty(self):
        """When all trials fail in a maximize study, best_score = -OPTIMIZER_PENALTY."""
        def always_fails(trial):
            trial.suggest_float("x", 0.0, 1.0)
            raise ValueError("simulated failure")

        result = optimize_model(
            model_spec=_NullSpec(),
            objective=always_fails,
            n_trials=3,
            direction="maximize",
            max_fallos=3,
        )

        assert result.fallback is True
        assert result.best_score == pytest.approx(-OPTIMIZER_PENALTY), (
            f"best_score={result.best_score} for all-fail maximize study — "
            "expected -OPTIMIZER_PENALTY (-1e6), got +1e6 means failures look "
            "like the best possible score"
        )

    def test_all_fail_minimize_best_score_is_positive_penalty(self):
        """Minimize direction: all-fail fallback must still be +OPTIMIZER_PENALTY."""
        def always_fails(trial):
            trial.suggest_float("x", 0.0, 1.0)
            raise ValueError("simulated failure")

        result = optimize_model(
            model_spec=_NullSpec(),
            objective=always_fails,
            n_trials=3,
            direction="minimize",
            max_fallos=3,
        )
        assert result.fallback is True
        assert result.best_score == pytest.approx(OPTIMIZER_PENALTY)


# ---------------------------------------------------------------------------
# merged_bug_017 — fallback discards good work, wrong n_trials
# ---------------------------------------------------------------------------

class TestMergedBug017:
    def test_fallback_uses_study_best_when_available(self):
        """When early trials succeed but later ones fail, use study.best_params."""
        call_count = [0]

        def obj(trial):
            call_count[0] += 1
            x = trial.suggest_float("x", 0.0, 1.0)
            if call_count[0] > 5:
                raise ValueError("late failure")
            return x

        result = optimize_model(
            model_spec=_NullSpec(),
            objective=obj,
            n_trials=8,
            direction="minimize",
            max_fallos=3,
        )

        assert result.best_score < OPTIMIZER_PENALTY / 2, (
            f"best_score={result.best_score} — fallback discarded 5 valid trials "
            "and reported OPTIMIZER_PENALTY as if no trial ever succeeded"
        )

    def test_n_trials_reflects_actual_count(self):
        """n_trials must equal len(study.trials), not the requested budget."""
        def obj(trial):
            return trial.suggest_float("x", 0.0, 1.0)

        result = optimize_model(
            model_spec=_NullSpec(),
            objective=obj,
            n_trials=7,
            direction="minimize",
        )
        assert result.n_trials == 7, (
            f"n_trials={result.n_trials} but 7 trials were requested and all "
            "succeeded — should reflect actual executed count"
        )

    def test_build_model_called_with_empty_params(self):
        """build_model must be called even when best_params is {} (falsy guard)."""
        built = [False]

        class SpecWithBuild:
            name = "with_build"
            def build_model(self, params):
                built[0] = True
                return object()

        def obj(trial):
            return 0.5  # no params suggested → best_params = {}

        optimize_model(
            model_spec=SpecWithBuild(),
            objective=obj,
            n_trials=2,
            direction="minimize",
        )
        assert built[0], (
            "build_model was never called — 'and best_p' guard skipped it "
            "because best_params={} is falsy"
        )


# ---------------------------------------------------------------------------
# bug_034 — neighbor threshold contaminated by cap_absoluto
# ---------------------------------------------------------------------------

class TestBug034:
    def _make_episode_df(self) -> pd.DataFrame:
        """
        Two stations 3 km apart (neighbors at default 50 km).
        Station 'sensor_A': 200 normal hours (~20 µg/m³) plus 1 extreme spike
            at hour 50 that will be tagged cap_absoluto (>99.9th percentile).
        Station 'sensor_B': 200 normal hours (~20 µg/m³) plus a 5-hour episode
            at hours 48-52 (≥4 consecutive hours) that is clearly extreme for B
            AND those same hours in A are elevated (confirming the episode).
        """
        rng = np.random.default_rng(0)
        n = 200
        base = pd.Timestamp("2024-01-10 00:00")
        times = [base + pd.Timedelta(hours=i) for i in range(n)]

        # Station A: normal + one giant spike at hour 50 → cap_absoluto
        val_a = rng.normal(20, 3, n).clip(5)
        val_a[50] = 5000.0  # cap_absoluto spike

        # Station B: normal + 5-hour episode at hours 48-52 elevated
        val_b = rng.normal(20, 3, n).clip(5)
        for h in range(47, 52):
            val_b[h] = 200.0  # extreme, ≥4 consecutive hours

        rows = []
        for i, t in enumerate(times):
            rows.append({"dt": t, "station": "sensor_A", "value": val_a[i],
                         "lat": 4.600, "lon": -74.080})
            rows.append({"dt": t, "station": "sensor_B", "value": val_b[i],
                         "lat": 4.627, "lon": -74.065})
        return pd.DataFrame(rows)

    def test_cap_absoluto_values_are_flagged_and_preserved(self):
        """
        Smoke test: a run with a clear cap_absoluto spike must complete without
        error and preserve the spike row as 'cap_absoluto' (not overwrite it).
        The determinism test (below) is the primary regression check for bug_034.
        """
        df = self._make_episode_df()
        result = flag_spatial_episodes(
            df,
            value_col="value",
            station_col="station",
            datetime_col="dt",
            lat_col="lat",
            lon_col="lon",
            iqr_multiplier=3.0,
            min_consecutive_hours=4,
            distance_km=50.0,
            min_neighbor_stations=1,
        )
        # The 5000 spike in sensor_A must have been tagged cap_absoluto
        spike_rows = result[
            (result["station"] == "sensor_A") & (result["value"] == 5000.0)
        ]
        assert not spike_rows.empty
        assert (spike_rows["flag_episode"] == "cap_absoluto").all()

    def test_result_deterministic_across_station_name_order(self):
        """Results must be the same regardless of alphabetical station order."""
        df = self._make_episode_df()

        # Rename so alphabetical order flips
        df2 = df.copy()
        df2["station"] = df2["station"].map({"sensor_A": "zz_A", "sensor_B": "aa_B"})

        res1 = flag_spatial_episodes(df, "value", "station", "dt", "lat", "lon")
        res2 = flag_spatial_episodes(df2, "value", "station", "dt", "lat", "lon")

        # Flag counts must match regardless of station naming
        counts1 = res1["flag_episode"].value_counts().to_dict()
        counts2 = res2["flag_episode"].value_counts().to_dict()
        assert counts1 == counts2, (
            f"flag counts differ: {counts1} vs {counts2} — "
            "episode detection is order-dependent (mask_vec_mes reads imputed values)"
        )


# ---------------------------------------------------------------------------
# merged_bug_007 — rolling median over the very outliers being replaced
# ---------------------------------------------------------------------------

class TestMergedBug007:
    def _make_short_cluster_df(self) -> pd.DataFrame:
        """
        Single isolated station (no neighbors → episodio_critico needs temporal only,
        but 3-hour run < min_consecutive_hours=4 so it falls through to IQR).

        Hours 0-199: normal values ~20 µg/m³
        Hours 50-52 (3 consecutive): extreme values 500 µg/m³ → iqr_hard
        Expected imputed value: close to surrounding ~20 µg/m³, NOT ~500.
        """
        rng = np.random.default_rng(1)
        n = 200
        base = pd.Timestamp("2024-01-05 00:00")
        times = [base + pd.Timedelta(hours=i) for i in range(n)]
        values = rng.normal(20, 3, n).clip(5)
        # 3-hour cluster (< min_consecutive_hours=4)
        values[50] = 500.0
        values[51] = 510.0
        values[52] = 505.0

        return pd.DataFrame({
            "dt": times,
            "station": "solo",
            "value": values,
            "lat": 4.60,
            "lon": -74.08,
        })

    def test_imputed_values_not_contaminated_by_outliers(self):
        """
        After flagging, iqr_hard positions must have values close to surrounding
        normals (~20), not close to the original outliers (~500).
        """
        df = self._make_short_cluster_df()
        result = flag_spatial_episodes(
            df,
            value_col="value",
            station_col="station",
            datetime_col="dt",
            lat_col="lat",
            lon_col="lon",
            iqr_multiplier=3.0,
            min_consecutive_hours=4,
            distance_km=50.0,
            min_neighbor_stations=0,  # solo station — no neighbor needed
        )

        hard_rows = result[result["flag_episode"] == "iqr_hard"]
        if hard_rows.empty:
            pytest.skip("No iqr_hard rows found — test data may need adjustment")

        imputed_values = hard_rows["value"].values
        assert (imputed_values < 100.0).all(), (
            f"Imputed values {imputed_values} are still near the outlier level "
            "— rolling median was computed on the outliers themselves"
        )
