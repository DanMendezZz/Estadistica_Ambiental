"""
Estadística Ambiental — API pública del paquete.

Uso rápido:
    from estadistica_ambiental import load, validate, run_eda, classify
    from estadistica_ambiental import impute, summarize, adf_test, mann_kendall
    from estadistica_ambiental import walk_forward, rank_models
"""

from estadistica_ambiental.descriptive.univariate import summarize
from estadistica_ambiental.eda.profiling import run_eda
from estadistica_ambiental.eda.quality import assess_quality
from estadistica_ambiental.eda.variables import classify
from estadistica_ambiental.evaluation.backtesting import compare_backtests, walk_forward
from estadistica_ambiental.evaluation.comparison import rank_models, select_best
from estadistica_ambiental.evaluation.metrics import evaluate
from estadistica_ambiental.inference.intervals import exceedance_probability
from estadistica_ambiental.inference.stationarity import adf_test, stationarity_report
from estadistica_ambiental.inference.trend import mann_kendall
from estadistica_ambiental.io.loaders import load
from estadistica_ambiental.io.validators import validate
from estadistica_ambiental.predictive.registry import get_model, list_models, register
from estadistica_ambiental.preprocessing.imputation import impute
from estadistica_ambiental.preprocessing.resampling import resample
from estadistica_ambiental.reporting.forecast_report import forecast_report
from estadistica_ambiental.reporting.stats_report import stats_report

__version__ = "1.0.0"
__all__ = [
    "load", "validate",
    "classify", "assess_quality", "run_eda",
    "impute", "resample",
    "summarize",
    "adf_test", "stationarity_report", "mann_kendall", "exceedance_probability",
    "get_model", "list_models", "register",
    "evaluate", "walk_forward", "compare_backtests", "rank_models", "select_best",
    "forecast_report", "stats_report",
]
