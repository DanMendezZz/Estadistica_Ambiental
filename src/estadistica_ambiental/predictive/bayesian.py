"""Modelos bayesianos para series y panel ambiental con PyMC.

Requiere: ``pip install estadistica-ambiental[bayes]`` (pymc + arviz).

Implementaciones:

- :class:`BayesianARIMA`: ARIMA(p, d, q) bayesiano con priors ``Normal(0, 1)`` sobre
  coeficientes AR/MA y ``HalfNormal(1)`` sobre la innovación. Pronóstico vía
  simulación recursiva del posterior (q=0 usa la matriz de lags AR; q>0 simula
  los errores MA junto con los lags).
- :class:`HierarchicalModel`: modelo normal jerárquico (partial pooling) sobre
  un panel ``[group_col, value_col]`` con hiperprior global y media por grupo.

Si PyMC no está instalado el módulo se carga igual y la instanciación de las
clases lanza ``ImportError`` con instrucciones claras (mismo patrón que
``predictive/deep.py``). El registro central solo expone estos modelos cuando
PyMC está disponible.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from estadistica_ambiental.predictive.base import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PyMC import (graceful)
# ---------------------------------------------------------------------------


def _try_import_pymc():
    """Importa pymc y arviz; devuelve ``(pm, az)`` o ``(None, None)`` si falla."""
    try:
        import arviz as az  # type: ignore
        import pymc as pm  # type: ignore

        return pm, az
    except ImportError:
        return None, None


def _check_pymc():
    """Lanza ``ImportError`` claro si PyMC/ArviZ no están instalados."""
    pm, az = _try_import_pymc()
    if pm is None or az is None:
        raise ImportError(
            "PyMC y ArviZ son necesarios para modelos bayesianos.\n"
            "Instalar: pip install estadistica-ambiental[bayes]"
        )
    return pm, az


# ---------------------------------------------------------------------------
# Diferenciación
# ---------------------------------------------------------------------------


def _difference(y: np.ndarray, d: int) -> np.ndarray:
    """Aplica diferenciación d veces a un array 1D."""
    out = np.asarray(y, dtype=float).copy()
    for _ in range(int(d)):
        out = np.diff(out)
    return out


def _undifference(forecast_diff: np.ndarray, y_orig: np.ndarray, d: int) -> np.ndarray:
    """Reconstruye la serie original a partir de pronósticos diferenciados d veces."""
    if d <= 0:
        return np.asarray(forecast_diff, dtype=float)
    series = np.asarray(forecast_diff, dtype=float)
    for k in range(d - 1, -1, -1):
        anchor_series = _difference(y_orig, k)
        anchor = float(anchor_series[-1])
        series = np.concatenate([[anchor], series]).cumsum()[1:]
    return series


# ---------------------------------------------------------------------------
# BayesianARIMA
# ---------------------------------------------------------------------------


class BayesianARIMA(BaseModel):
    """ARIMA(p, d, q) bayesiano con PyMC.

    Priors:
        - ``intercept ~ Normal(0, 1)``
        - ``phi[i] ~ Normal(0, 1)`` (coeficientes AR)
        - ``theta[j] ~ Normal(0, 1)`` (coeficientes MA, solo si q > 0)
        - ``sigma ~ HalfNormal(1)`` (innovación)

    El modelo se ajusta sobre la serie diferenciada ``d`` veces. La verosimilitud
    es ``Normal(mu, sigma)`` con ``mu`` igual a la suma autoregresiva (más MA si
    procede) sobre los lags observados.

    Parameters
    ----------
    p, d, q : int, opcional
        Órdenes del proceso ARIMA. Pueden pasarse posicionalmente o vía
        ``order=(p, d, q)``.
    samples : int
        Número de draws por cadena (alias: ``draws``).
    tune : int
        Pasos de tuneo de NUTS por cadena.
    chains : int
        Número de cadenas MCMC.
    seed : int
        Semilla aleatoria (alias: ``random_seed``).
    """

    name = "BayesianARIMA"

    def __init__(
        self,
        p: int = 1,
        d: int = 0,
        q: int = 0,
        samples: int = 1000,
        tune: int = 500,
        chains: int = 2,
        seed: int = 42,
        *,
        order: Optional[Tuple[int, int, int]] = None,
        draws: Optional[int] = None,
        random_seed: Optional[int] = None,
    ):
        # Soporta tanto la API nueva ``(p, d, q, samples, ..., seed)`` como la
        # heredada ``(order=(p,d,q), draws=, random_seed=)``.
        if order is not None:
            p, d, q = order
        if draws is not None:
            samples = int(draws)
        if random_seed is not None:
            seed = int(random_seed)

        super().__init__(order=(p, d, q), samples=samples, tune=tune, chains=chains, seed=seed)
        self.p, self.d, self.q = int(p), int(d), int(q)
        self.order: Tuple[int, int, int] = (self.p, self.d, self.q)
        self.samples = int(samples)
        self.tune = int(tune)
        self.chains = int(chains)
        self.seed = int(seed)

        # Aliases retro-compatibles (usados en tests existentes).
        self.draws = self.samples
        self.random_seed = self.seed

        self._trace: Any = None
        self._model: Any = None
        self._y_orig: Optional[np.ndarray] = None
        self._y_diff: Optional[np.ndarray] = None
        self._last_index: Optional[pd.Index] = None
        self._freq: Optional[str] = None
        self.last_obs_: Optional[np.ndarray] = None
        self.diff_d_: int = self.d

    # ------------------------------------------------------------------ fit

    def fit(
        self,
        y: pd.Series,
        X: Optional[pd.DataFrame] = None,
        samples: Optional[int] = None,
    ) -> "BayesianARIMA":
        """Ajusta ARIMA(p, d, q) bayesiano a la serie ``y``.

        ``X`` se acepta por compatibilidad con la interfaz :class:`BaseModel`
        pero se ignora en esta versión. Aplica diferenciación ``d`` antes de
        ajustar y guarda los anclajes necesarios para invertirla en
        :meth:`predict`.
        """
        pm, _az = _check_pymc()

        if samples is not None:
            self.samples = int(samples)
            self.draws = self.samples

        y_series = pd.Series(y).dropna()
        y_arr = np.asarray(y_series.values, dtype=float)
        self._y_orig = y_arr
        if isinstance(y_series.index, pd.DatetimeIndex):
            self._last_index = y_series.index
            self._freq = pd.infer_freq(y_series.index) or getattr(
                y_series.index, "freqstr", None
            )

        y_diff = _difference(y_arr, self.d)
        self._y_diff = y_diff
        self.last_obs_ = y_arr[-self.d :].copy() if self.d > 0 else np.array([], dtype=float)

        p_eff = max(self.p, 1)
        q_eff = max(self.q, 0)
        n_lags = max(p_eff, q_eff if q_eff > 0 else 1)
        if len(y_diff) <= n_lags:
            raise ValueError(
                f"Serie demasiado corta tras diferenciar (n={len(y_diff)}) "
                f"para ARIMA(p={self.p}, d={self.d}, q={self.q})."
            )

        # Matriz de lags AR (siempre).
        Y = y_diff[n_lags:]
        Xlag = np.column_stack(
            [y_diff[n_lags - i - 1 : len(y_diff) - i - 1] for i in range(p_eff)]
        )

        # Para MA pre-calculamos residuos del fit OLS-like sobre AR (proxy de epsilons).
        eps_lags = None
        if q_eff > 0:
            # Estimación rápida via mínimos cuadrados de phi inicial para residuos.
            try:
                phi_ols, *_ = np.linalg.lstsq(
                    np.column_stack([np.ones_like(Y), Xlag]), Y, rcond=None
                )
                resid = Y - (np.ones_like(Y) * phi_ols[0] + Xlag @ phi_ols[1:])
                # Construimos lags de residuos
                resid_full = np.concatenate([np.zeros(n_lags), resid])
                eps_lags = np.column_stack(
                    [resid_full[n_lags - j - 1 : len(resid_full) - j - 1] for j in range(q_eff)]
                )
            except Exception:
                eps_lags = np.zeros((len(Y), q_eff))

        with pm.Model() as model:
            intercept = pm.Normal("intercept", mu=0.0, sigma=1.0)
            if self.p > 0:
                phi = pm.Normal("phi", mu=0.0, sigma=1.0, shape=p_eff)
            else:
                phi = None
            if q_eff > 0:
                theta = pm.Normal("theta", mu=0.0, sigma=1.0, shape=q_eff)
            else:
                theta = None
            sigma = pm.HalfNormal("sigma", sigma=1.0)

            mu = intercept
            if phi is not None:
                mu = mu + pm.math.dot(Xlag, phi)
            if theta is not None and eps_lags is not None:
                mu = mu + pm.math.dot(eps_lags, theta)

            pm.Normal("y_obs", mu=mu, sigma=sigma, observed=Y)
            self._trace = pm.sample(
                draws=self.samples,
                tune=self.tune,
                chains=self.chains,
                random_seed=self.seed,
                progressbar=False,
                return_inferencedata=True,
            )

        self._model = model
        self._fitted = True
        # Atributo público requerido por la spec.
        self.trace_ = self._trace
        logger.info(
            "BayesianARIMA(p=%d, d=%d, q=%d) ajustado.", self.p, self.d, self.q
        )
        return self

    # ------------------------------------------------------------------ predict

    def _simulate_paths(self, horizon: int, n_samples: int) -> np.ndarray:
        """Simula trayectorias del posterior predictivo. Devuelve (n_samples, horizon)."""
        if not self._fitted or self._trace is None or self._y_diff is None:
            raise RuntimeError("Llama fit() primero.")

        rng = np.random.default_rng(self.seed)
        post = self._trace.posterior  # type: ignore[attr-defined]

        intercepts = post["intercept"].values.reshape(-1)
        n_total = intercepts.shape[0]

        if self.p > 0:
            phis = post["phi"].values.reshape(-1, post["phi"].values.shape[-1])
        else:
            phis = np.zeros((n_total, 0))
        if self.q > 0:
            thetas = post["theta"].values.reshape(-1, post["theta"].values.shape[-1])
        else:
            thetas = np.zeros((n_total, 0))
        sigmas = post["sigma"].values.reshape(-1)

        n_draw = min(int(n_samples), n_total)
        idx = rng.choice(n_total, size=n_draw, replace=(n_draw > n_total))

        p_eff = max(self.p, 1) if self.p > 0 else 0
        q_eff = self.q
        history = np.asarray(self._y_diff, dtype=float)
        sims_diff = np.zeros((n_draw, int(horizon)), dtype=float)

        for s, k in enumerate(idx):
            phi_k = phis[k] if self.p > 0 else None
            theta_k = thetas[k] if q_eff > 0 else None
            a_k = float(intercepts[k])
            sig_k = float(sigmas[k])
            buf = list(history[-max(p_eff, 1) :])
            eps_buf: List[float] = [0.0] * max(q_eff, 1)
            for h in range(int(horizon)):
                mu_h = a_k
                if phi_k is not None:
                    lags = np.array(buf[-p_eff:][::-1])
                    mu_h += float(np.dot(phi_k, lags))
                if theta_k is not None:
                    eps_lags = np.array(eps_buf[-q_eff:][::-1])
                    mu_h += float(np.dot(theta_k, eps_lags))
                eps = float(rng.normal(0.0, sig_k))
                val = mu_h + eps
                sims_diff[s, h] = val
                buf.append(val)
                eps_buf.append(eps)

        if self.d > 0 and self._y_orig is not None:
            out = np.zeros_like(sims_diff)
            for s in range(n_draw):
                out[s, :] = _undifference(sims_diff[s, :], self._y_orig, self.d)
            return out
        return sims_diff

    def _future_index(self, horizon: int) -> Optional[pd.DatetimeIndex]:
        """Construye un índice futuro si la serie original era datetime."""
        if self._last_index is None or len(self._last_index) == 0:
            return None
        try:
            freq = self._freq or pd.infer_freq(self._last_index)
            if freq is None:
                return None
            start = self._last_index[-1]
            return pd.date_range(start=start, periods=int(horizon) + 1, freq=freq)[1:]
        except Exception:
            return None

    def predict(
        self,
        horizon: int,
        X_future: Optional[pd.DataFrame] = None,
        n_samples: Optional[int] = None,
        return_samples: bool = False,
    ) -> Union[pd.Series, np.ndarray]:
        """Pronóstico posterior predictivo a ``horizon`` pasos.

        Por defecto devuelve una :class:`pandas.Series` con la **media** del
        posterior predictivo (indexada por fechas futuras si la serie original
        era datetime).

        Si ``return_samples=True`` o si se pasa ``n_samples`` explícito,
        devuelve un ``np.ndarray`` de forma ``(n_samples, horizon)`` con las
        trayectorias muestreadas (compatible con la API histórica).
        """
        if return_samples or n_samples is not None:
            n = int(n_samples) if n_samples is not None else 500
            return self._simulate_paths(int(horizon), n)

        sims = self._simulate_paths(int(horizon), 500)
        mean = sims.mean(axis=0)
        idx = self._future_index(int(horizon))
        if idx is not None:
            return pd.Series(mean, index=idx, name="forecast")
        return pd.Series(mean, name="forecast")

    # ------------------------------------------------------------------ summary / plots

    def summary(self) -> pd.DataFrame:
        """Resumen del posterior con mean, sd, HDI, r_hat y ess."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _check_pymc()
        return az.summary(self._trace, hdi_prob=0.94)

    def plot_trace(self, **kwargs: Any) -> Any:
        """Wrapper sobre ``arviz.plot_trace`` del posterior ajustado."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _check_pymc()
        return az.plot_trace(self._trace, **kwargs)

    def predict_interval(
        self,
        horizon: int,
        credible_interval: float = 0.94,
    ) -> pd.DataFrame:
        """Intervalo de credibilidad por horizonte (``mean``, ``lower``, ``upper``)."""
        sims = self._simulate_paths(int(horizon), 500)
        alpha = (1.0 - float(credible_interval)) / 2.0
        lower = np.quantile(sims, alpha, axis=0)
        upper = np.quantile(sims, 1.0 - alpha, axis=0)
        mean = sims.mean(axis=0)
        idx = self._future_index(int(horizon))
        df = pd.DataFrame({"mean": mean, "lower": lower, "upper": upper})
        if idx is not None:
            df.index = idx
        return df

    def posterior_predictive_interval(
        self,
        horizon: int,
        hdi_prob: float = 0.95,
    ) -> pd.DataFrame:
        """Intervalo HDI del posterior predictivo (``mean``, ``lower``, ``upper``)."""
        return self.predict_interval(horizon=horizon, credible_interval=float(hdi_prob))


# ---------------------------------------------------------------------------
# HierarchicalModel
# ---------------------------------------------------------------------------


class HierarchicalModel(BaseModel):
    """Modelo normal jerárquico con partial pooling por grupo.

    Estructura del modelo::

        mu_global   ~ Normal(0, 10)
        sigma_global ~ HalfNormal(5)
        mu_group[i] ~ Normal(mu_global, sigma_global)
        sigma       ~ HalfNormal(5)
        y[i]        ~ Normal(mu_group[group[i]], sigma)

    Acepta entrada en formato largo (``DataFrame`` con columnas
    ``[group_col, value_col]``) o, retro-compatiblemente, una serie ``y`` y un
    array de grupos vía ``groups=`` o ``X['estacion']``.
    """

    name = "HierarchicalModel"

    def __init__(
        self,
        group_col: str = "estacion",
        samples: int = 1000,
        tune: int = 500,
        chains: int = 2,
        seed: int = 42,
        *,
        draws: Optional[int] = None,
        random_seed: Optional[int] = None,
    ):
        if draws is not None:
            samples = int(draws)
        if random_seed is not None:
            seed = int(random_seed)

        super().__init__(group_col=group_col, samples=samples, tune=tune, chains=chains, seed=seed)
        self.group_col = group_col
        self.samples = int(samples)
        self.tune = int(tune)
        self.chains = int(chains)
        self.seed = int(seed)

        # Aliases retro-compat.
        self.draws = self.samples
        self.random_seed = self.seed

        self._trace: Any = None
        self._model: Any = None
        self._stations: Optional[List[Any]] = None
        self._station_means: Optional[np.ndarray] = None

    # ------------------------------------------------------------------ fit

    def fit(  # type: ignore[override]
        self,
        y: Union[pd.Series, pd.DataFrame],
        X: Optional[pd.DataFrame] = None,
        groups: Optional[Sequence] = None,
        value_col: Optional[str] = None,
        samples: Optional[int] = None,
    ) -> "HierarchicalModel":
        """Ajusta el modelo jerárquico.

        Dos formas de uso:

        1. Formato largo: ``fit(df, value_col="y")`` con ``df`` que tiene
           la columna ``self.group_col`` y la columna ``value_col``.
        2. Compatibilidad: ``fit(y_series, groups=array)`` o
           ``fit(y_series, X=df_con_columna_estacion)``.
        """
        pm, _az = _check_pymc()
        if samples is not None:
            self.samples = int(samples)
            self.draws = self.samples

        # Resolver y / groups según la forma de invocación.
        if isinstance(y, pd.DataFrame):
            df = y
            vc = value_col
            if vc is None:
                # Heurística: primera columna numérica distinta de group_col.
                for col in df.columns:
                    if col == self.group_col:
                        continue
                    if pd.api.types.is_numeric_dtype(df[col]):
                        vc = col
                        break
            if vc is None:
                raise ValueError(
                    "value_col no especificado y no se pudo inferir una columna numérica."
                )
            if self.group_col not in df.columns:
                raise ValueError(
                    f"DataFrame no tiene la columna de grupo '{self.group_col}'."
                )
            y_arr = np.asarray(df[vc].values, dtype=float)
            g = df[self.group_col].values
        else:
            y_series = pd.Series(y)
            y_arr = np.asarray(y_series.values, dtype=float)
            g = groups
            if g is None and X is not None and self.group_col in X.columns:
                g = X[self.group_col].values
            if (
                g is None
                and isinstance(y_series.index, pd.MultiIndex)
                and self.group_col in y_series.index.names
            ):
                g = y_series.index.get_level_values(self.group_col).values
            if g is None:
                raise ValueError(
                    "HierarchicalModel.fit requiere `groups` o un DataFrame con la columna "
                    f"'{self.group_col}'."
                )

        g_cat = pd.Series(g).astype("category")
        stations = list(g_cat.cat.categories)
        idx = g_cat.cat.codes.values
        n_groups = len(stations)
        self._stations = stations

        with pm.Model() as model:
            mu_global = pm.Normal("mu_global", mu=0.0, sigma=10.0)
            sigma_global = pm.HalfNormal("sigma_global", sigma=5.0)
            mu_group = pm.Normal(
                "mu_group", mu=mu_global, sigma=sigma_global, shape=n_groups
            )
            sigma = pm.HalfNormal("sigma", sigma=5.0)
            pm.Normal("y_obs", mu=mu_group[idx], sigma=sigma, observed=y_arr)
            self._trace = pm.sample(
                draws=self.samples,
                tune=self.tune,
                chains=self.chains,
                random_seed=self.seed,
                progressbar=False,
                return_inferencedata=True,
            )

        self._model = model
        self._fitted = True
        self.trace_ = self._trace

        post = self._trace.posterior  # type: ignore[attr-defined]
        self._station_means = post["mu_group"].values.mean(axis=(0, 1))
        logger.info("HierarchicalModel ajustado con %d grupos.", n_groups)
        return self

    # ------------------------------------------------------------------ predict

    def predict(
        self,
        horizon: int,
        X_future: Optional[pd.DataFrame] = None,
        n_samples: int = 500,
    ) -> np.ndarray:
        """Trayectorias por grupo: array ``(n_samples, horizon, n_groups)``.

        El modelo no es temporal: cada paso muestrea independientemente del
        posterior conjunto sobre ``(mu_group, sigma)``.
        """
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")

        rng = np.random.default_rng(self.seed)
        post = self._trace.posterior  # type: ignore[attr-defined]
        mu_group_flat = post["mu_group"].values.reshape(-1, post["mu_group"].values.shape[-1])
        sigma_flat = post["sigma"].values.reshape(-1)

        n_total = mu_group_flat.shape[0]
        n_draw = min(int(n_samples), n_total)
        idx = rng.choice(n_total, size=n_draw, replace=(n_draw > n_total))
        n_groups = mu_group_flat.shape[1]
        horizon = int(horizon)

        sims = np.zeros((n_draw, horizon, n_groups), dtype=float)
        for s, k in enumerate(idx):
            mean_k = mu_group_flat[k]
            sig_k = float(sigma_flat[k])
            sims[s, :, :] = rng.normal(loc=mean_k, scale=sig_k, size=(horizon, n_groups))
        return sims

    # ------------------------------------------------------------------ summary

    def summary(self) -> pd.DataFrame:
        """Resumen ArviZ del posterior con mean, sd, HDI, r_hat, ess."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _check_pymc()
        return az.summary(self._trace, hdi_prob=0.94)

    def group_estimates(self) -> pd.DataFrame:
        """Tabla por grupo con media posterior y HDI 95% de ``mu_group[i]``."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _check_pymc()
        post = self._trace.posterior  # type: ignore[attr-defined]
        mg = post["mu_group"].values  # (chain, draw, n_groups)
        flat = mg.reshape(-1, mg.shape[-1])
        means = flat.mean(axis=0)

        # HDI 95% por grupo
        try:
            hdi = az.hdi(self._trace, var_names=["mu_group"], hdi_prob=0.95)
            mu_hdi = hdi["mu_group"].values  # (n_groups, 2)
            lower = mu_hdi[:, 0]
            upper = mu_hdi[:, 1]
        except Exception:
            lower = np.quantile(flat, 0.025, axis=0)
            upper = np.quantile(flat, 0.975, axis=0)

        return pd.DataFrame(
            {
                self.group_col: self._stations,
                "mean": means,
                "hdi_lower": lower,
                "hdi_upper": upper,
            }
        )

    def plot_forest(self, **kwargs: Any) -> Any:
        """Wrapper sobre ``arviz.plot_forest`` para los efectos por grupo."""
        if not self._fitted or self._trace is None:
            raise RuntimeError("Llama fit() primero.")
        _pm, az = _check_pymc()
        kwargs.setdefault("var_names", ["mu_group"])
        return az.plot_forest(self._trace, **kwargs)


# ---------------------------------------------------------------------------
# Disponibilidad para el registro central
# ---------------------------------------------------------------------------

PYMC_AVAILABLE: bool = _try_import_pymc()[0] is not None
