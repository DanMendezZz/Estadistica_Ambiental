"""Modelos bayesianos jerárquicos para series ambientales.

Requiere: pip install estadistica-ambiental[bayes]  (pymc + arviz)

Implementación funcional mínima (M-05):
- BayesianARIMA: AR(p) con priors normales sobre coeficientes y half-cauchy
  sobre sigma. Soporta diferenciación d>=0 vía np.diff/recomposición.
- HierarchicalModel: efecto fijo + efecto aleatorio por estación.

Si PyMC no está instalado, los métodos lanzan NotImplementedError documentando
el camino de implementación. Los tests usan ``pytest.importorskip``.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _try_import_pymc():
    """Importa pymc y arviz; devuelve (pm, az) o (None, None) si no están."""
    try:
        import arviz as az  # type: ignore
        import pymc as pm  # type: ignore

        return pm, az
    except ImportError:
        return None, None


def _require_pymc():
    pm, az = _try_import_pymc()
    if pm is None:
        raise NotImplementedError(
            "PyMC/ArviZ no están instalados. Instalar:\n"
            "    pip install estadistica-ambiental[bayes]\n"
            "Camino de implementación: ver src/estadistica_ambiental/predictive/bayesian.py"
        )
    return pm, az


def _difference(y: np.ndarray, d: int) -> np.ndarray:
    """Aplica diferenciación d veces a un array 1D."""
    out = np.asarray(y, dtype=float).copy()
    for _ in range(int(d)):
        out = np.diff(out)
    return out


def _undifference(forecast_diff: np.ndarray, y_orig: np.ndarray, d: int) -> np.ndarray:
    """Reconstruye la serie original a partir de pronósticos en escala diferenciada d veces.

    ``y_orig`` debe ser la serie original completa (necesaria para anclar cada nivel
    de integración con los últimos valores de la serie diferenciada apropiada).
    """
    if d <= 0:
        return np.asarray(forecast_diff, dtype=float)
    series = np.asarray(forecast_diff, dtype=float)
    # Construimos los anclajes a partir de la serie original en cada nivel de diferenciación.
    # level k (k=d-1..0) usa la serie diferenciada k veces para tomar su último valor.
    for k in range(d - 1, -1, -1):
        anchor_series = _difference(y_orig, k)
        anchor = float(anchor_series[-1])
        series = np.concatenate([[anchor], series]).cumsum()[1:]
    return series


# ---------------------------------------------------------------------------
# BayesianARIMA
# ---------------------------------------------------------------------------


class BayesianARIMA(BaseModel):
    """ARIMA(p, d, q) bayesiano con PyMC (q se ignora; soporta solo AR(p))."""

    name = "BayesianARIMA"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 0, 0),
        draws: int = 1000,
        tune: int = 500,
        chains: int = 2,
        random_seed: int = 42,
    ):
        super().__init__(order=order, draws=draws, tune=tune, chains=chains)
        self.order = order
        self.p, self.d, self.q = order
        if self.q != 0:
            logger.warning(
                "BayesianARIMA implementa solo AR(p) por ahora; q=%d se ignorará.", self.q
            )
        self.draws = draws
        self.tune = tune
        self.chains = chains
        self.random_seed = random_seed
        self._trace = None
        self._model = None
        self._y_orig: Optional[np.ndarray] = None
        self._y_diff: Optional[np.ndarray] = None

    # -------------------- fit --------------------

    def fit(
        self,
        y: pd.Series,
        X: Optional[pd.DataFrame] = None,
        samples: Optional[int] = None,
    ) -> "BayesianARIMA":
        """Ajusta AR(p) bayesiano con priors Normal(0, 1) sobre phi y HalfCauchy sobre sigma."""
        pm, _az = _require_pymc()

        if samples is not None:
            self.draws = int(samples)

        y_arr = np.asarray(y, dtype=float)
        self._y_orig = y_arr
        y_diff = _difference(y_arr, self.d)
        self._y_diff = y_diff

        p = max(self.p, 1)
        if len(y_diff) <= p:
            raise ValueError(
                f"Serie demasiado corta tras diferenciar (n={len(y_diff)}) para AR(p={p})."
            )

        # Construye matriz de lags
        Y = y_diff[p:]
        Xlag = np.column_stack([y_diff[p - i - 1 : -i - 1] for i in range(p)])

        with pm.Model() as model:
            intercept = pm.Normal("intercept", mu=0.0, sigma=1.0)
            phi = pm.Normal("phi", mu=0.0, sigma=1.0, shape=p)
            sigma = pm.HalfCauchy("sigma", beta=1.0)
            mu = intercept + pm.math.dot(Xlag, phi)
            pm.Normal("y_obs", mu=mu, sigma=sigma, observed=Y)
            self._trace = pm.sample(
                draws=self.draws,
                tune=self.tune,
                chains=self.chains,
                random_seed=self.random_seed,
                progressbar=False,
                return_inferencedata=True,
            )

        self._model = model
        self._fitted = True
        logger.info("BayesianARIMA(p=%d,d=%d) ajustado.", p, self.d)
        return self

    # -------------------- predict --------------------

    def predict(
        self,
        horizon: int,
        X_future: Optional[pd.DataFrame] = None,
        n_samples: int = 500,
    ) -> np.ndarray:
        """Devuelve una matriz (n_samples x horizon) con trayectorias del posterior predictivo."""
        if not self._fitted or self._trace is None or self._y_diff is None:
            raise RuntimeError("Llama fit() primero.")

        rng = np.random.default_rng(self.random_seed)
        # Aplana muestras de cadenas
        post = self._trace.posterior  # type: ignore[attr-defined]
        intercepts = post["intercept"].values.reshape(-1)
        phis = post["phi"].values.reshape(-1, post["phi"].values.shape[-1])
        sigmas = post["sigma"].values.reshape(-1)

        n_total = intercepts.shape[0]
        n_draw = min(int(n_samples), n_total)
        idx = rng.choice(n_total, size=n_draw, replace=False)

        p = phis.shape[1]
        history = self._y_diff
        horizon = int(horizon)
        sims_diff = np.zeros((n_draw, horizon), dtype=float)

        for s, k in enumerate(idx):
            phi_k = phis[k]
            a_k = intercepts[k]
            sig_k = sigmas[k]
            buf = list(history[-p:])
            for h in range(horizon):
                lags = np.array(buf[-p:][::-1])  # más reciente primero
                mu_h = a_k + float(np.dot(phi_k, lags))
                eps = rng.normal(0.0, sig_k)
                val = mu_h + eps
                sims_diff[s, h] = val
                buf.append(val)

        # Reconstruye a la escala original si d > 0
        if self.d > 0 and self._y_orig is not None:
            out = np.zeros_like(sims_diff)
            for s in range(n_draw):
                out[s, :] = _undifference(sims_diff[s, :], self._y_orig, self.d)
            return out
        return sims_diff

    # -------------------- summary --------------------

    def summary(self) -> pd.DataFrame:
        """Resumen ArviZ del posterior con mean, sd y HDI 3%/97%."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _require_pymc()
        df = az.summary(self._trace, hdi_prob=0.94)
        return df

    def predict_interval(
        self,
        horizon: int,
        credible_interval: float = 0.94,
    ) -> pd.DataFrame:
        """Intervalo de credibilidad por horizonte con columnas mean, lower, upper."""
        sims = self.predict(horizon)
        alpha = (1.0 - credible_interval) / 2.0
        lower = np.quantile(sims, alpha, axis=0)
        upper = np.quantile(sims, 1.0 - alpha, axis=0)
        mean = sims.mean(axis=0)
        return pd.DataFrame({"mean": mean, "lower": lower, "upper": upper})


# ---------------------------------------------------------------------------
# HierarchicalModel
# ---------------------------------------------------------------------------


class HierarchicalModel(BaseModel):
    """Regresión jerárquica con intercepto fijo + efecto aleatorio por estación."""

    name = "HierarchicalModel"

    def __init__(
        self,
        draws: int = 1000,
        tune: int = 500,
        chains: int = 2,
        random_seed: int = 42,
    ):
        super().__init__(draws=draws, tune=tune, chains=chains)
        self.draws = draws
        self.tune = tune
        self.chains = chains
        self.random_seed = random_seed
        self._trace = None
        self._model = None
        self._stations: Optional[List[str]] = None
        self._station_means: Optional[np.ndarray] = None

    # -------------------- fit --------------------

    def fit(
        self,
        y: pd.Series,
        X: Optional[pd.DataFrame] = None,
        groups: Optional[Sequence] = None,
        samples: Optional[int] = None,
    ) -> "HierarchicalModel":
        """Ajusta y_ij ~ Normal(mu + alpha_j, sigma) con alpha_j ~ Normal(0, tau).

        Si ``groups`` no se pasa, se intenta tomar de ``X['estacion']`` o
        de un MultiIndex con nivel ``estacion``.
        """
        pm, _az = _require_pymc()
        if samples is not None:
            self.draws = int(samples)

        y_arr = np.asarray(y, dtype=float)

        # Resolver groups
        g = groups
        if g is None and X is not None and "estacion" in X.columns:
            g = X["estacion"].values
        if g is None and isinstance(y.index, pd.MultiIndex) and "estacion" in y.index.names:
            g = y.index.get_level_values("estacion").values
        if g is None:
            raise ValueError(
                "HierarchicalModel.fit requiere `groups` (array de estación por observación)"
                " o una columna 'estacion' en X."
            )

        g_arr = pd.Series(g).astype("category")
        stations = list(g_arr.cat.categories)
        idx = g_arr.cat.codes.values
        n_groups = len(stations)
        self._stations = stations

        with pm.Model() as model:
            mu = pm.Normal("mu", mu=float(np.mean(y_arr)), sigma=10.0)
            tau = pm.HalfCauchy("tau", beta=1.0)
            alpha = pm.Normal("alpha", mu=0.0, sigma=tau, shape=n_groups)
            sigma = pm.HalfCauchy("sigma", beta=1.0)
            y_hat = mu + alpha[idx]
            pm.Normal("y_obs", mu=y_hat, sigma=sigma, observed=y_arr)
            self._trace = pm.sample(
                draws=self.draws,
                tune=self.tune,
                chains=self.chains,
                random_seed=self.random_seed,
                progressbar=False,
                return_inferencedata=True,
            )

        self._model = model
        self._fitted = True

        # Cache de medias posteriores por estación para predict()
        post = self._trace.posterior  # type: ignore[attr-defined]
        mu_mean = float(post["mu"].values.mean())
        alpha_mean = post["alpha"].values.mean(axis=(0, 1))
        self._station_means = mu_mean + alpha_mean
        logger.info("HierarchicalModel ajustado con %d estaciones.", n_groups)
        return self

    # -------------------- predict --------------------

    def predict(
        self,
        horizon: int,
        X_future: Optional[pd.DataFrame] = None,
        n_samples: int = 500,
    ) -> np.ndarray:
        """Trayectorias por estación: array (n_samples x horizon x n_groups).

        Como el modelo es no-temporal (efecto aleatorio puro), cada paso
        de horizonte muestrea independientemente de los posteriors.
        """
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")

        rng = np.random.default_rng(self.random_seed)
        post = self._trace.posterior  # type: ignore[attr-defined]
        mu_flat = post["mu"].values.reshape(-1)
        alpha_flat = post["alpha"].values.reshape(-1, post["alpha"].values.shape[-1])
        sigma_flat = post["sigma"].values.reshape(-1)

        n_total = mu_flat.shape[0]
        n_draw = min(int(n_samples), n_total)
        idx = rng.choice(n_total, size=n_draw, replace=False)
        n_groups = alpha_flat.shape[1]
        horizon = int(horizon)

        sims = np.zeros((n_draw, horizon, n_groups), dtype=float)
        for s, k in enumerate(idx):
            mean_k = mu_flat[k] + alpha_flat[k]
            sig_k = sigma_flat[k]
            sims[s, :, :] = rng.normal(loc=mean_k, scale=sig_k, size=(horizon, n_groups))
        return sims

    # -------------------- summary --------------------

    def summary(self) -> pd.DataFrame:
        """Resumen ArviZ del posterior con mean, sd y HDI 3%/97%."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _require_pymc()
        df = az.summary(self._trace, hdi_prob=0.94)
        return df
