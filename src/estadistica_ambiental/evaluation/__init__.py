"""Módulo de evaluación — métricas, comparación y detección de anomalías."""

from estadistica_ambiental.evaluation.anomaly import (
    anomaly_summary,
    detect_anomalies,
)
from estadistica_ambiental.evaluation.comparison import (
    rank_models,
    select_best,
)
from estadistica_ambiental.evaluation.metrics import (
    compare_models,
    evaluate,
    hit_rate_ica,
    kge,
    mae,
    mape,
    mase,
    mse,
    nrmse,
    nse,
    pbias,
    r2,
    rmse,
    smape,
)

__all__ = [
    # métricas básicas
    "mae",
    "rmse",
    "mse",
    "r2",
    "smape",
    "mape",
    "mase",
    # métricas hidrológicas
    "nse",
    "kge",
    "pbias",
    # métricas escala-invariante y calidad del aire
    "nrmse",
    "hit_rate_ica",
    # suite completa
    "evaluate",
    "compare_models",
    # comparación multi-criterio
    "rank_models",
    "select_best",
    # detección de anomalías
    "detect_anomalies",
    "anomaly_summary",
]
