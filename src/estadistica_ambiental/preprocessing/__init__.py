"""Submódulo de preprocesamiento para series ambientales."""

from .air_quality import (
    ICA_COLORS,
    categorize_ica,
    correct_seasonal_bias,
    flag_spatial_episodes,
)
from .imputation import impute
from .outliers import flag_outliers

__all__ = [
    # imputación
    "impute",
    # outliers genéricos
    "flag_outliers",
    # calidad del aire
    "ICA_COLORS",
    "categorize_ica",
    "correct_seasonal_bias",
    "flag_spatial_episodes",
]
