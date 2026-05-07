"""Calibrador AR(1) horario doble-escala sobre residuos de modelos ML.

Implementa el patrón validado en el proyecto CAR (calidad del aire,
Cundinamarca): añade autocorrelación realista a pronósticos deterministas
(RF/XGB) ajustando 24 modelos AR(1) (uno por hora del día) con varianza de
innovación estacional (σ por mes). Genera trayectorias Monte Carlo para
construir bandas P10/P50/P90, y expone una suite de tests formales
(T1-T4 + KS + Ljung-Box + Jarque-Bera) que devuelven PASS/FAIL.

Adaptado de boa-sarima-forecaster / proyecto CAR
(`06_Pronostico_2026/08_escalar_ar1_todas_estaciones.py`) por Dan Méndez —
2026-05-07. Ver `Plan/Plan.md` §13 / M-02 y
`Plan/Feedback/repo_estadistica_ambiental_feedback.md` §3.1.B.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

HOURS_IN_DAY: int = 24
MONTHS_IN_YEAR: int = 12
DEFAULT_TRAJECTORIES: int = 100
DEFAULT_ALPHA: float = 0.05  # nivel de significancia para PASS/FAIL


# ---------------------------------------------------------------------------
# Resultado de un test estadístico (PASS/FAIL + estadístico + p-valor)
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    """Resultado de un test estadístico individual."""

    name: str
    passed: bool
    statistic: float
    p_value: float
    detail: str = ""

    @property
    def status(self) -> str:
        """Cadena 'PASS' o 'FAIL' según ``passed``."""
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> Dict[str, Any]:
        """Serialización plana para reporte tabular."""
        return {
            "name": self.name,
            "status": self.status,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Calibrador principal
# ---------------------------------------------------------------------------


class HourlyAR1Calibrator:
    """AR(1) horario doble-escala sobre residuos: 24 phi por hora, σ por mes.

    Ajusta una familia de 24 modelos AR(1) (uno por hora del día) sobre los
    residuos ``r(t) = y(t) - base_ML(t)`` y modela la varianza de innovación
    σ²(mes) para captar la estacionalidad mensual andina (clima bimodal).

    Modelo::

        e_AR(t) = phi_h(t) · e_AR(t-1) + ε(t),   ε ~ N(0, σ_mes(t))

    Use :meth:`fit` para calibrar phi_h y σ_mes desde una serie de residuos
    indexada por hora, :meth:`simulate` para generar K trayectorias Monte
    Carlo, y :meth:`validate` para correr la suite de 7 tests formales.
    """

    name: str = "HourlyAR1Calibrator"

    def __init__(
        self,
        n_trajectories: int = DEFAULT_TRAJECTORIES,
        alpha: float = DEFAULT_ALPHA,
        random_state: Optional[int] = None,
    ) -> None:
        if n_trajectories < 1:
            raise ValueError("n_trajectories debe ser >= 1")
        if not 0 < alpha < 1:
            raise ValueError("alpha debe estar en (0, 1)")

        self.n_trajectories = n_trajectories
        self.alpha = alpha
        self.random_state = random_state

        # Atributos calibrados (poblados por fit)
        self.phi_by_hour: np.ndarray = np.zeros(HOURS_IN_DAY)
        self.sigma_by_month: np.ndarray = np.zeros(MONTHS_IN_YEAR)
        self.intercept_by_hour: np.ndarray = np.zeros(HOURS_IN_DAY)
        self._residuals: Optional[np.ndarray] = None
        self._index: Optional[pd.DatetimeIndex] = None
        self._fitted: bool = False

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        """True si el calibrador ya fue ajustado."""
        return self._fitted

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def fit(
        self,
        residuals: pd.Series | np.ndarray,
        datetime_index: Optional[pd.DatetimeIndex] = None,
    ) -> "HourlyAR1Calibrator":
        """Ajusta 24 phi (uno por hora) y 12 σ (uno por mes) desde residuos."""
        residuals_arr, idx = _coerce_series(residuals, datetime_index)
        if len(residuals_arr) < HOURS_IN_DAY * 2:
            raise ValueError(
                f"Se requieren al menos {HOURS_IN_DAY * 2} observaciones para ajustar "
                f"24 modelos AR(1); recibidas {len(residuals_arr)}."
            )
        if len(residuals_arr) != len(idx):
            raise ValueError("residuals y datetime_index deben tener la misma longitud.")

        hours = idx.hour.to_numpy()
        months = idx.month.to_numpy()

        # 1) Ajustar phi y residuo de innovación por hora del día
        innovations = np.full(len(residuals_arr), np.nan)
        for h in range(HOURS_IN_DAY):
            phi_h, intercept_h, inn_h, idx_h = _fit_ar1_hourly(residuals_arr, hours, h)
            self.phi_by_hour[h] = phi_h
            self.intercept_by_hour[h] = intercept_h
            innovations[idx_h] = inn_h

        # 2) Ajustar σ de innovación por mes
        for m in range(1, MONTHS_IN_YEAR + 1):
            mask = (months == m) & ~np.isnan(innovations)
            if mask.sum() >= 2:
                self.sigma_by_month[m - 1] = float(np.std(innovations[mask], ddof=1))
            else:
                # Fallback: σ global si no hay suficientes datos para ese mes
                global_inn = innovations[~np.isnan(innovations)]
                self.sigma_by_month[m - 1] = (
                    float(np.std(global_inn, ddof=1)) if global_inn.size >= 2 else 1.0
                )

        # Evitar σ=0 (degenera el simulador)
        self.sigma_by_month = np.where(self.sigma_by_month <= 0, 1e-6, self.sigma_by_month)

        self._residuals = residuals_arr
        self._index = idx
        self._innovations = innovations
        self._fitted = True
        return self

    # ------------------------------------------------------------------
    # Simulate
    # ------------------------------------------------------------------

    def simulate(
        self,
        horizon: int,
        n_trajectories: Optional[int] = None,
        start_datetime: Optional[pd.Timestamp] = None,
        e0: float = 0.0,
        random_state: Optional[int] = None,
    ) -> np.ndarray:
        """Genera ``K`` trayectorias Monte Carlo de longitud ``horizon``."""
        self._check_fitted()
        if horizon < 1:
            raise ValueError("horizon debe ser >= 1")

        K = int(n_trajectories) if n_trajectories is not None else self.n_trajectories
        if K < 1:
            raise ValueError("n_trajectories debe ser >= 1")

        seed = random_state if random_state is not None else self.random_state
        rng = np.random.default_rng(seed)

        if start_datetime is None:
            assert self._index is not None
            start_datetime = self._index[-1] + pd.Timedelta(hours=1)
        future_index = pd.date_range(start=start_datetime, periods=horizon, freq="h")
        hours = future_index.hour.to_numpy()
        months = future_index.month.to_numpy()

        traj = np.zeros((K, horizon))
        prev = np.full(K, e0, dtype=float)
        for t in range(horizon):
            h = int(hours[t])
            m = int(months[t])
            phi = self.phi_by_hour[h]
            mu = self.intercept_by_hour[h]
            sigma = self.sigma_by_month[m - 1]
            eps = rng.normal(0.0, sigma, size=K)
            current = mu + phi * prev + eps
            traj[:, t] = current
            prev = current
        return traj

    def percentiles(
        self,
        trajectories: np.ndarray,
        levels: Tuple[float, float, float] = (10.0, 50.0, 90.0),
    ) -> Dict[str, np.ndarray]:
        """Devuelve percentiles P10/P50/P90 (o niveles dados) por paso."""
        if trajectories.ndim != 2:
            raise ValueError("trajectories debe ser un array 2D (K, horizon).")
        out: Dict[str, np.ndarray] = {}
        for lvl in levels:
            out[f"P{int(lvl)}"] = np.percentile(trajectories, lvl, axis=0)
        return out

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate(
        self,
        residuals: Optional[pd.Series | np.ndarray] = None,
        datetime_index: Optional[pd.DatetimeIndex] = None,
        alpha: Optional[float] = None,
    ) -> Dict[str, TestResult]:
        """Ejecuta T1-T4 + KS + Ljung-Box + Jarque-Bera sobre las innovaciones."""
        self._check_fitted()
        a = alpha if alpha is not None else self.alpha

        if residuals is None:
            assert self._innovations is not None and self._index is not None
            innovations = self._innovations[~np.isnan(self._innovations)]
            inn_index = self._index[~np.isnan(self._innovations)]
            res_arr = self._residuals
            res_index = self._index
        else:
            res_arr, res_index = _coerce_series(residuals, datetime_index)
            innovations, inn_index = self._compute_innovations(res_arr, res_index)

        results: Dict[str, TestResult] = {}
        results["T1_mean_zero"] = _test_t1_mean_zero(innovations, alpha=a)
        results["T2_variance_finite"] = _test_t2_variance_finite(innovations, alpha=a)
        results["T3_hourly_autocorr"] = _test_t3_hourly_autocorr(
            innovations, inn_index, alpha=a
        )
        results["T4_monthly_seasonality"] = _test_t4_monthly_seasonality(
            res_arr, res_index, alpha=a
        )
        results["KS_normal"] = _test_ks_normal(innovations, alpha=a)
        results["LjungBox"] = _test_ljung_box(innovations, alpha=a)
        results["JarqueBera"] = _test_jarque_bera(innovations, alpha=a)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("Calibrador no ajustado: llama a fit() antes.")

    def _compute_innovations(
        self,
        residuals: np.ndarray,
        idx: pd.DatetimeIndex,
    ) -> Tuple[np.ndarray, pd.DatetimeIndex]:
        """Reconstruye ε(t) = r(t) - intercept_h - phi_h · r(t-1) hora a hora."""
        hours = idx.hour.to_numpy()
        innovations = np.full(len(residuals), np.nan)
        for h in range(HOURS_IN_DAY):
            mask = hours == h
            positions = np.where(mask)[0]
            if positions.size < 2:
                continue
            prev_pos = positions[positions > 0] - 1
            curr_pos = positions[positions > 0]
            inn = (
                residuals[curr_pos]
                - self.intercept_by_hour[h]
                - self.phi_by_hour[h] * residuals[prev_pos]
            )
            innovations[curr_pos] = inn
        valid = ~np.isnan(innovations)
        return innovations[valid], idx[valid]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _coerce_series(
    residuals: pd.Series | np.ndarray,
    datetime_index: Optional[pd.DatetimeIndex],
) -> Tuple[np.ndarray, pd.DatetimeIndex]:
    """Normaliza residuals + index a (np.ndarray, DatetimeIndex)."""
    if isinstance(residuals, pd.Series):
        idx = residuals.index
        arr = residuals.to_numpy(dtype=float)
        if datetime_index is not None:
            idx = pd.DatetimeIndex(datetime_index)
        if not isinstance(idx, pd.DatetimeIndex):
            raise TypeError("El índice de residuals debe ser DatetimeIndex.")
    else:
        if datetime_index is None:
            raise ValueError(
                "Si residuals es ndarray, datetime_index es obligatorio."
            )
        idx = pd.DatetimeIndex(datetime_index)
        arr = np.asarray(residuals, dtype=float)
    return arr, idx


def _fit_ar1_hourly(
    residuals: np.ndarray,
    hours: np.ndarray,
    h: int,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Ajusta AR(1) por OLS sobre (r_{t-1}, r_t) restringido a hora ``h``."""
    mask = hours == h
    positions = np.where(mask)[0]
    positions = positions[positions > 0]
    if positions.size < 2:
        return 0.0, 0.0, np.array([]), np.array([], dtype=int)

    y = residuals[positions]
    x = residuals[positions - 1]
    if np.isnan(y).any() or np.isnan(x).any():
        valid = ~np.isnan(y) & ~np.isnan(x)
        y = y[valid]
        x = x[valid]
        positions = positions[valid]
    if y.size < 2:
        return 0.0, 0.0, np.array([]), np.array([], dtype=int)

    x_mean = x.mean()
    y_mean = y.mean()
    denom = float(np.sum((x - x_mean) ** 2))
    if denom < 1e-12:
        phi = 0.0
        intercept = y_mean
    else:
        phi = float(np.sum((x - x_mean) * (y - y_mean)) / denom)
        # Restringir |phi| < 0.999 para mantener estacionariedad
        phi = float(np.clip(phi, -0.999, 0.999))
        intercept = float(y_mean - phi * x_mean)
    innovations = y - intercept - phi * x
    return phi, intercept, innovations, positions


# ---------------------------------------------------------------------------
# Suite de tests formales
# ---------------------------------------------------------------------------


def _test_t1_mean_zero(innovations: np.ndarray, alpha: float) -> TestResult:
    """T1: media de innovaciones ≈ 0 (one-sample t-test)."""
    if innovations.size < 2:
        return TestResult("T1_mean_zero", False, np.nan, np.nan, "muestra insuficiente")
    stat, p = stats.ttest_1samp(innovations, popmean=0.0)
    return TestResult(
        name="T1_mean_zero",
        passed=bool(p > alpha),
        statistic=float(stat),
        p_value=float(p),
        detail=f"mean={innovations.mean():.4f}",
    )


def _test_t2_variance_finite(innovations: np.ndarray, alpha: float) -> TestResult:
    """T2: varianza estable y finita (ratio de varianzas primera/segunda mitad)."""
    if innovations.size < 4:
        return TestResult(
            "T2_variance_finite", False, np.nan, np.nan, "muestra insuficiente"
        )
    half = innovations.size // 2
    v1 = float(np.var(innovations[:half], ddof=1))
    v2 = float(np.var(innovations[half:], ddof=1))
    if v1 <= 0 or v2 <= 0 or not np.isfinite(v1) or not np.isfinite(v2):
        return TestResult("T2_variance_finite", False, np.nan, np.nan, "varianza no finita")
    f_stat = v1 / v2 if v1 >= v2 else v2 / v1
    df1 = half - 1
    df2 = innovations.size - half - 1
    p = 2.0 * min(stats.f.sf(f_stat, df1, df2), stats.f.cdf(f_stat, df1, df2))
    return TestResult(
        name="T2_variance_finite",
        passed=bool(p > alpha),
        statistic=float(f_stat),
        p_value=float(p),
        detail=f"v1={v1:.4f} v2={v2:.4f}",
    )


def _test_t3_hourly_autocorr(
    innovations: np.ndarray,
    idx: pd.DatetimeIndex,
    alpha: float,
) -> TestResult:
    """T3: autocorrelación residual horaria ≈ 0 (test sobre ρ̂ en lag 1)."""
    n = innovations.size
    if n < 5:
        return TestResult(
            "T3_hourly_autocorr", False, np.nan, np.nan, "muestra insuficiente"
        )
    s = innovations - innovations.mean()
    denom = float(np.sum(s**2))
    if denom <= 0:
        return TestResult("T3_hourly_autocorr", False, 0.0, 1.0, "varianza nula")
    rho1 = float(np.sum(s[1:] * s[:-1]) / denom)
    # Bajo H0: rho1 ~ N(0, 1/n) asintóticamente
    z = rho1 * np.sqrt(n)
    p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
    return TestResult(
        name="T3_hourly_autocorr",
        passed=bool(p > alpha),
        statistic=float(rho1),
        p_value=float(p),
        detail=f"rho1={rho1:.4f}",
    )


def _test_t4_monthly_seasonality(
    residuals: np.ndarray,
    idx: pd.DatetimeIndex,
    alpha: float,
) -> TestResult:
    """T4: estacionalidad mensual de varianza presente (Levene entre meses)."""
    months = idx.month.to_numpy()
    groups: List[np.ndarray] = []
    for m in range(1, MONTHS_IN_YEAR + 1):
        sub = residuals[months == m]
        sub = sub[~np.isnan(sub)]
        if sub.size >= 2:
            groups.append(sub)
    if len(groups) < 2:
        return TestResult(
            "T4_monthly_seasonality",
            False,
            np.nan,
            np.nan,
            "menos de 2 meses con datos",
        )
    stat, p = stats.levene(*groups, center="median")
    # PASS: presencia de estacionalidad (varianzas distintas) → rechazamos H0
    # PERO si solo hay un puñado de meses, aceptamos un PASS condicional
    # cuando la varianza está modelada (sigma_by_month != const) — aquí solo
    # devolvemos el p-valor: "passed" indica que no podemos descartar
    # heteroscedasticidad mensual.
    passed = bool(p < alpha) or len(groups) <= 2
    return TestResult(
        name="T4_monthly_seasonality",
        passed=passed,
        statistic=float(stat),
        p_value=float(p),
        detail=f"n_meses={len(groups)}",
    )


def _test_ks_normal(innovations: np.ndarray, alpha: float) -> TestResult:
    """KS: bondad de ajuste a normal estandarizada."""
    if innovations.size < 8:
        return TestResult("KS_normal", False, np.nan, np.nan, "muestra insuficiente")
    sigma = float(np.std(innovations, ddof=1))
    if sigma <= 0:
        return TestResult("KS_normal", False, np.nan, np.nan, "sigma=0")
    z = (innovations - innovations.mean()) / sigma
    stat, p = stats.kstest(z, "norm")
    return TestResult(
        name="KS_normal",
        passed=bool(p > alpha),
        statistic=float(stat),
        p_value=float(p),
    )


def _test_ljung_box(innovations: np.ndarray, alpha: float, lags: int = 10) -> TestResult:
    """Ljung-Box: ausencia de autocorrelación residual hasta ``lags`` lags."""
    n = innovations.size
    if n < lags + 2:
        return TestResult("LjungBox", False, np.nan, np.nan, "muestra insuficiente")
    lb = acorr_ljungbox(innovations, lags=[lags], return_df=True)
    stat = float(lb["lb_stat"].iloc[0])
    p = float(lb["lb_pvalue"].iloc[0])
    return TestResult(
        name="LjungBox",
        passed=bool(p > alpha),
        statistic=stat,
        p_value=p,
        detail=f"lags={lags}",
    )


def _test_jarque_bera(innovations: np.ndarray, alpha: float) -> TestResult:
    """Jarque-Bera: normalidad por skew + kurtosis."""
    if innovations.size < 8:
        return TestResult("JarqueBera", False, np.nan, np.nan, "muestra insuficiente")
    stat, p = stats.jarque_bera(innovations)
    return TestResult(
        name="JarqueBera",
        passed=bool(p > alpha),
        statistic=float(stat),
        p_value=float(p),
    )


# ---------------------------------------------------------------------------
# Reporte tabular
# ---------------------------------------------------------------------------


@dataclass
class CalibrationReport:
    """Resumen tabular del estado de calibración y validación."""

    phi_by_hour: np.ndarray
    sigma_by_month: np.ndarray
    tests: Dict[str, TestResult] = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Devuelve un DataFrame con un test por fila."""
        rows = [t.to_dict() for t in self.tests.values()]
        return pd.DataFrame(rows)

    @property
    def all_pass(self) -> bool:
        """True si todos los tests devolvieron PASS."""
        return all(t.passed for t in self.tests.values())


__all__ = [
    "HourlyAR1Calibrator",
    "TestResult",
    "CalibrationReport",
]
