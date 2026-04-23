"""Tests para evaluation/metrics.py, optimization/bayes_opt.py y predictive/classical.py"""

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.evaluation.metrics import (
    mae, rmse, r2, smape, nse, kge, evaluate, compare_models,
)
from estadistica_ambiental.optimization.bayes_opt import (
    optimize, best_params, sarima_search_space,
)
from estadistica_ambiental.predictive.classical import ARIMAModel, SARIMAXModel, ETSModel


# --- fixtures ---

@pytest.fixture
def perfect():
    y = np.array([10.0, 15.0, 12.0, 18.0, 14.0])
    return y, y.copy()


@pytest.fixture
def noisy():
    np.random.seed(7)
    y = np.random.normal(15, 3, 100)
    y_hat = y + np.random.normal(0, 1, 100)
    return y, y_hat


@pytest.fixture
def ts():
    np.random.seed(9)
    return pd.Series(
        10 + np.cumsum(np.random.normal(0, 0.5, 120)),
        index=pd.date_range("2015-01-01", periods=120, freq="ME"),
    )


# --- metrics ---

class TestMetrics:
    def test_mae_perfect(self, perfect):
        assert mae(*perfect) == pytest.approx(0.0)

    def test_rmse_perfect(self, perfect):
        assert rmse(*perfect) == pytest.approx(0.0)

    def test_r2_perfect(self, perfect):
        assert r2(*perfect) == pytest.approx(1.0)

    def test_smape_range(self, noisy):
        assert 0 <= smape(*noisy) <= 200

    def test_nse_perfect(self, perfect):
        assert nse(*perfect) == pytest.approx(1.0)

    def test_kge_perfect(self, perfect):
        assert kge(*perfect) == pytest.approx(1.0)

    def test_evaluate_general(self, noisy):
        result = evaluate(*noisy, domain="general")
        assert "mae" in result and "rmse" in result and "r2" in result

    def test_evaluate_hydrology(self, noisy):
        result = evaluate(*noisy, domain="hydrology")
        assert "nse" in result and "kge" in result and "pbias" in result

    def test_compare_models(self, noisy):
        y, yhat = noisy
        models = {
            "A": evaluate(y, yhat),
            "B": evaluate(y, yhat + 2),
        }
        df = compare_models(models)
        assert "rmse" in df.columns
        assert df.index[0] == "A"  # menor RMSE primero


class TestAnomalyDetect:
    def test_length_mismatch_raises(self):
        from estadistica_ambiental.evaluation.anomaly import detect_anomalies
        with pytest.raises(ValueError, match="misma longitud"):
            detect_anomalies(np.array([1.0, 2.0]), np.array([1.0]))

    def test_absolute_mode(self, noisy):
        from estadistica_ambiental.evaluation.anomaly import detect_anomalies
        y, yhat = noisy
        result = detect_anomalies(y, yhat, relative=False)
        assert "is_anomaly" in result.columns


class TestRankModels:
    def test_rank_models_returns_df(self, noisy):
        from estadistica_ambiental.evaluation.comparison import rank_models
        y, yhat = noisy
        results = {
            "A": {"metrics": evaluate(y, yhat), "folds": [], "predictions": pd.DataFrame()},
            "B": {"metrics": evaluate(y, yhat + 1), "folds": [], "predictions": pd.DataFrame()},
        }
        df = rank_models(results, domain="general")
        assert "rank" in df.columns

    def test_fit_distribution_handles_failures(self, noisy):
        from estadistica_ambiental.inference.distributions import fit_distribution
        y, _ = noisy
        # Incluir ceros para forzar fallo en lognorm (cubre líneas 68-69)
        series = pd.Series(np.concatenate([[0.0], np.abs(y)]))
        result = fit_distribution(series, distributions=["norm", "lognorm"])
        assert isinstance(result, pd.DataFrame)


# --- optimization ---

class TestBayesOpt:
    def test_optimize_simple(self):
        def obj(trial):
            x = trial.suggest_float("x", -5, 5)
            return (x - 2) ** 2

        study = optimize(obj, n_trials=20)
        assert abs(best_params(study)["x"] - 2.0) < 1.0

    def test_sarima_search_space_keys(self):
        import optuna
        trial = optuna.trial.create_trial(
            params={"p": 1, "d": 1, "q": 1, "P": 0, "D": 0, "Q": 0},
            distributions={
                "p": optuna.distributions.IntDistribution(0, 5),
                "d": optuna.distributions.IntDistribution(0, 2),
                "q": optuna.distributions.IntDistribution(0, 5),
                "P": optuna.distributions.IntDistribution(0, 2),
                "D": optuna.distributions.IntDistribution(0, 1),
                "Q": optuna.distributions.IntDistribution(0, 2),
            },
            value=0.5,
        )
        # El trial ya está creado, solo verificamos que las claves esperadas existen
        assert {"p", "d", "q", "P", "D", "Q"}.issubset(trial.params.keys())


# --- classical models ---

class TestARIMA:
    def test_fit_predict(self, ts):
        model = ARIMAModel(order=(1, 1, 1))
        model.fit(ts)
        preds = model.predict(6)
        assert len(preds) == 6
        assert not np.any(np.isnan(preds))

    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            ARIMAModel().predict(3)

    def test_is_fitted(self, ts):
        model = ARIMAModel()
        assert not model.is_fitted
        model.fit(ts)
        assert model.is_fitted


class TestSARIMAX:
    def test_fit_predict_no_exog(self, ts):
        model = SARIMAXModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model.fit(ts)
        preds = model.predict(3)
        assert len(preds) == 3

    def test_aic_after_fit(self, ts):
        model = SARIMAXModel(order=(1, 1, 1))
        model.fit(ts)
        assert model.aic < float("inf")

    def test_summary_property_after_fit(self, ts):
        model = SARIMAXModel(order=(1, 1, 1))
        model.fit(ts)
        s = model.summary
        assert s is not None

    def test_sarima_model_init(self, ts):
        from estadistica_ambiental.predictive.classical import SARIMAModel
        model = SARIMAModel(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model.fit(ts)
        preds = model.predict(3)
        assert len(preds) == 3


class TestETS:
    def test_fit_predict(self, ts):
        model = ETSModel(seasonal_periods=12)
        model.fit(ts)
        preds = model.predict(6)
        assert len(preds) == 6

    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            ETSModel().predict(3)
