"""
Análisis profundo de calidad de datos para series ambientales.

Complementa io/validators.py (plausibilidad física) con análisis estadístico:
patrones de faltantes, gaps temporales, congelamiento de sensor y outliers.
No elimina ni imputa datos — solo diagnostica para informar la estrategia.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos y enums
# ---------------------------------------------------------------------------

class MissingPattern(str, Enum):
    """Clasificación heurística del mecanismo de datos faltantes."""
    MCAR    = "MCAR"     # Missing Completely At Random — aleatorio, sin patrón
    MAR     = "MAR"      # Missing At Random — relacionado con otras variables
    MNAR    = "MNAR"     # Missing Not At Random — relacionado con el propio valor
    UNKNOWN = "desconocido"


@dataclass
class MissingInfo:
    col: str
    n_missing: int
    pct_missing: float
    max_consecutive_gap: int       # máx. registros consecutivos faltantes
    gap_lengths: List[int]         # lista de longitudes de todos los gaps
    pattern: MissingPattern
    pattern_note: str = ""


@dataclass
class OutlierInfo:
    col: str
    n_iqr: int                     # outliers por IQR (1.5×)
    n_zscore: int                  # outliers por z-score (|z|>3)
    pct_iqr: float
    pct_zscore: float
    worst_values: List[float]      # los 5 valores más extremos


@dataclass
class FreezeInfo:
    col: str
    n_sequences: int               # cuántos episodios de congelamiento
    max_length: int                # longitud del episodio más largo
    total_frozen: int              # total de registros en episodios


@dataclass
class TemporalGapInfo:
    inferred_freq: Optional[str]   # frecuencia inferida ('H', 'D', 'M', etc.)
    expected_n: int                # registros esperados según frecuencia
    actual_n: int                  # registros presentes
    completeness_pct: float        # actual / expected × 100
    n_gaps: int                    # número de saltos temporales
    max_gap_periods: int           # salto más largo en periodos
    gap_summary: Dict[str, int]    # {longitud_gap: n_veces}


@dataclass
class QualityReport:
    n_rows: int
    n_cols: int
    missing:       Dict[str, MissingInfo]  = field(default_factory=dict)
    outliers:      Dict[str, OutlierInfo]  = field(default_factory=dict)
    freezes:       Dict[str, FreezeInfo]   = field(default_factory=dict)
    temporal_gaps: Optional[TemporalGapInfo] = None
    cross_issues:  List[str]               = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"=== Reporte de calidad EDA ({self.n_rows} filas × {self.n_cols} cols) ==="]

        # Faltantes
        cols_with_missing = {c: v for c, v in self.missing.items() if v.n_missing > 0}
        if cols_with_missing:
            lines.append(f"\nFaltantes ({len(cols_with_missing)} columnas):")
            for col, m in sorted(cols_with_missing.items(), key=lambda x: -x[1].pct_missing):
                lines.append(
                    f"  {col}: {m.pct_missing:.1f}% | gap máx={m.max_consecutive_gap} | patrón={m.pattern.value}"
                )
        else:
            lines.append("\nFaltantes: ninguno detectado")

        # Gaps temporales
        if self.temporal_gaps:
            tg = self.temporal_gaps
            lines.append("\nCompletitud temporal:")
            lines.append(f"  Frecuencia inferida: {tg.inferred_freq or 'no inferida'}")
            lines.append(f"  Esperados: {tg.expected_n} | Presentes: {tg.actual_n} | {tg.completeness_pct:.1f}%")
            lines.append(f"  Gaps: {tg.n_gaps} | Mayor gap: {tg.max_gap_periods} periodos")

        # Outliers
        if self.outliers:
            lines.append(f"\nOutliers estadísticos ({len(self.outliers)} columnas):")
            for col, o in self.outliers.items():
                lines.append(
                    f"  {col}: IQR={o.n_iqr} ({o.pct_iqr:.1f}%) | z>3={o.n_zscore} ({o.pct_zscore:.1f}%)"
                )

        # Congelamiento de sensor
        if self.freezes:
            lines.append(f"\nCongelamiento de sensor ({len(self.freezes)} columnas):")
            for col, f in self.freezes.items():
                lines.append(
                    f"  {col}: {f.n_sequences} episodios | máx={f.max_length} registros consecutivos iguales"
                )

        # Inconsistencias cruzadas
        if self.cross_issues:
            lines.append("\nInconsistencias cruzadas:")
            for issue in self.cross_issues:
                lines.append(f"  ⚠ {issue}")

        return "\n".join(lines)

    def has_issues(self) -> bool:
        missing_issues = any(m.n_missing > 0 for m in self.missing.values())
        return bool(
            missing_issues
            or self.outliers
            or self.freezes
            or self.cross_issues
            or (self.temporal_gaps and self.temporal_gaps.completeness_pct < 100)
        )


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def assess_quality(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    numeric_cols: Optional[List[str]] = None,
    freeze_min_length: int = 5,
    cross_checks: bool = True,
) -> QualityReport:
    """Análisis profundo de calidad para un DataFrame ambiental.

    Args:
        df: DataFrame a analizar.
        date_col: Columna de fechas para análisis temporal.
        numeric_cols: Columnas numéricas a analizar (None = todas).
        freeze_min_length: Mínimo de registros iguales consecutivos para
                           considerar congelamiento de sensor.
        cross_checks: Si True, evalúa inconsistencias entre columnas
                      (e.g., PM2.5 > PM10).
    """
    num_cols = _get_numeric_cols(df, numeric_cols)
    report = QualityReport(n_rows=len(df), n_cols=len(df.columns))

    report.missing  = {c: _analyze_missing(df[c], c) for c in df.columns}
    report.outliers = {c: _analyze_outliers(df[c], c)
                       for c in num_cols if df[c].notna().sum() >= 4}
    report.freezes  = {c: info
                       for c in num_cols
                       if (info := _analyze_freeze(df[c], c, freeze_min_length)).n_sequences > 0}

    if date_col and date_col in df.columns:
        report.temporal_gaps = _analyze_temporal_gaps(df[date_col])

    if cross_checks:
        report.cross_issues = _cross_column_checks(df)

    logger.info(
        "Calidad EDA: %d cols con faltantes | %d con outliers | %d con freeze",
        sum(1 for m in report.missing.values() if m.n_missing > 0),
        len(report.outliers),
        len(report.freezes),
    )
    return report


# ---------------------------------------------------------------------------
# Análisis de faltantes
# ---------------------------------------------------------------------------

def _analyze_missing(series: pd.Series, col: str) -> MissingInfo:
    mask = series.isna()
    n_missing = int(mask.sum())
    pct = round(n_missing / len(series) * 100, 2) if len(series) else 0.0
    gap_lengths = _consecutive_gap_lengths(mask)
    max_gap = max(gap_lengths) if gap_lengths else 0
    pattern, note = _classify_missing_pattern(series, pct)

    return MissingInfo(
        col=col,
        n_missing=n_missing,
        pct_missing=pct,
        max_consecutive_gap=max_gap,
        gap_lengths=gap_lengths,
        pattern=pattern,
        pattern_note=note,
    )


def _consecutive_gap_lengths(missing_mask: pd.Series) -> List[int]:
    """Devuelve lista con la longitud de cada bloque de True consecutivos."""
    gaps = []
    count = 0
    for val in missing_mask:
        if val:
            count += 1
        elif count > 0:
            gaps.append(count)
            count = 0
    if count > 0:
        gaps.append(count)
    return gaps


def _classify_missing_pattern(series: pd.Series, pct_missing: float) -> Tuple[MissingPattern, str]:
    """Heurística ligera para clasificar el mecanismo de faltantes."""
    if pct_missing == 0:
        return MissingPattern.MCAR, "sin faltantes"

    mask = series.isna()

    # MNAR heurístico: los faltantes se concentran en extremos de la distribución
    if pd.api.types.is_numeric_dtype(series):
        valid = series.dropna()
        if len(valid) >= 10:
            q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
            # Faltantes predominantes donde hay valores extremos
            idx_extreme = (series < q1) | (series > q3)
            ratio = (mask & idx_extreme).sum() / max(mask.sum(), 1)
            if ratio > 0.6:
                return MissingPattern.MNAR, "faltantes concentrados en colas de la distribución"

    # MCAR heurístico: gaps distribuidos aleatoriamente (no hay clusters largos)
    gaps = _consecutive_gap_lengths(mask)
    if gaps:
        avg_gap = np.mean(gaps)
        max_gap = max(gaps)
        if max_gap <= 3 and avg_gap < 2:
            return MissingPattern.MCAR, "gaps cortos distribuidos aleatoriamente"
        if max_gap > 24 or pct_missing > 30:
            return MissingPattern.MAR, "gaps largos — posible falla de sensor o mantenimiento"

    return MissingPattern.UNKNOWN, "patrón no determinado con heurística simple"


# ---------------------------------------------------------------------------
# Análisis de outliers (solo estadístico — NO elimina)
# ---------------------------------------------------------------------------

def _analyze_outliers(series: pd.Series, col: str) -> OutlierInfo:
    valid = series.dropna()
    n = len(valid)

    # IQR
    q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask_iqr = (valid < lo) | (valid > hi)
    n_iqr = int(mask_iqr.sum())

    # Z-score
    mu, sigma = valid.mean(), valid.std()
    if sigma > 0:
        z = (valid - mu) / sigma
        n_zscore = int((z.abs() > 3).sum())
    else:
        n_zscore = 0

    # Peores valores (más alejados de la mediana)
    median = valid.median()
    worst = valid.reindex((valid - median).abs().nlargest(5).index).tolist()

    return OutlierInfo(
        col=col,
        n_iqr=n_iqr,
        pct_iqr=round(n_iqr / n * 100, 2) if n else 0.0,
        n_zscore=n_zscore,
        pct_zscore=round(n_zscore / n * 100, 2) if n else 0.0,
        worst_values=worst,
    )


# ---------------------------------------------------------------------------
# Detección de congelamiento de sensor
# ---------------------------------------------------------------------------

def _analyze_freeze(series: pd.Series, col: str, min_length: int) -> FreezeInfo:
    """Detecta secuencias de valores idénticos consecutivos (sensor bloqueado)."""
    valid = series.dropna()
    if len(valid) < min_length:
        return FreezeInfo(col=col, n_sequences=0, max_length=0, total_frozen=0)

    sequences = []
    count = 1
    prev = valid.iloc[0]

    for val in valid.iloc[1:]:
        if val == prev:
            count += 1
        else:
            if count >= min_length:
                sequences.append(count)
            count = 1
            prev = val
    if count >= min_length:
        sequences.append(count)

    return FreezeInfo(
        col=col,
        n_sequences=len(sequences),
        max_length=max(sequences) if sequences else 0,
        total_frozen=sum(sequences),
    )


# ---------------------------------------------------------------------------
# Análisis de completitud temporal
# ---------------------------------------------------------------------------

def _analyze_temporal_gaps(date_series: pd.Series) -> TemporalGapInfo:
    dates = pd.to_datetime(date_series, errors="coerce").dropna().sort_values()
    if len(dates) < 2:
        return TemporalGapInfo(
            inferred_freq=None, expected_n=len(dates), actual_n=len(dates),
            completeness_pct=100.0, n_gaps=0, max_gap_periods=0, gap_summary={},
        )

    freq = pd.infer_freq(dates)
    actual_n = len(dates)

    # Si infer_freq falla (serie con gaps), usar la diferencia modal como periodo base
    diffs = dates.diff().dropna()
    mode_diff = diffs.mode().iloc[0] if len(diffs) else None

    if freq:
        expected_idx = pd.date_range(dates.iloc[0], dates.iloc[-1], freq=freq)
        expected_n = len(expected_idx)
        missing_ts = expected_idx.difference(dates)
        n_gaps = len(missing_ts)
        completeness = round(actual_n / expected_n * 100, 2) if expected_n else 100.0
    elif mode_diff and mode_diff.total_seconds() > 0:
        span = dates.iloc[-1] - dates.iloc[0]
        expected_n = int(span / mode_diff) + 1
        n_gaps = max(0, expected_n - actual_n)
        completeness = round(actual_n / expected_n * 100, 2) if expected_n else 100.0
    else:
        expected_n = actual_n
        n_gaps = 0
        completeness = 100.0

    # Distribución de tamaños de gap en la serie real
    diffs = dates.diff().dropna()
    if len(diffs):
        mode_diff = diffs.mode().iloc[0]
        long_gaps = diffs[diffs > mode_diff]
        gap_periods = (long_gaps / mode_diff).round().astype(int) - 1
        gap_summary = gap_periods.value_counts().to_dict()
        max_gap = int(gap_periods.max()) if len(gap_periods) else 0
    else:
        gap_summary = {}
        max_gap = 0

    return TemporalGapInfo(
        inferred_freq=freq,
        expected_n=expected_n,
        actual_n=actual_n,
        completeness_pct=completeness,
        n_gaps=n_gaps,
        max_gap_periods=max_gap,
        gap_summary={str(k): int(v) for k, v in gap_summary.items()},
    )


# ---------------------------------------------------------------------------
# Inconsistencias cruzadas entre columnas
# ---------------------------------------------------------------------------

_CROSS_RULES: List[Tuple[str, str, str]] = [
    ("pm25", "pm10",  "PM2.5 > PM10 en {n} filas (PM2.5 es subconjunto de PM10)"),
    ("pm10", "pm25",  None),  # se maneja en la regla anterior
    ("dbo",  "dqo",   "DBO > DQO en {n} filas (DBO es subconjunto de DQO)"),
    ("od",   "od",    None),
]


def _cross_column_checks(df: pd.DataFrame) -> List[str]:
    issues = []
    cols_lower = {c.lower(): c for c in df.columns}

    # PM2.5 no puede superar PM10
    if "pm25" in cols_lower and "pm10" in cols_lower:
        c25, c10 = cols_lower["pm25"], cols_lower["pm10"]
        mask = df[c25].notna() & df[c10].notna() & (df[c25] > df[c10])
        n = int(mask.sum())
        if n:
            issues.append(f"PM2.5 > PM10 en {n} filas — revisar sensor o unidades")

    # DBO no puede superar DQO
    if "dbo" in cols_lower and "dqo" in cols_lower:
        cdbo, cdqo = cols_lower["dbo"], cols_lower["dqo"]
        mask = df[cdbo].notna() & df[cdqo].notna() & (df[cdbo] > df[cdqo])
        n = int(mask.sum())
        if n:
            issues.append(f"DBO > DQO en {n} filas — imposible físicamente")

    # Humedad fuera de rango (doble check cruzado con temperatura)
    for hr_name in ("humedad", "hr", "humedad_relativa"):
        if hr_name in cols_lower:
            col = cols_lower[hr_name]
            n = int(((df[col] < 0) | (df[col] > 100)).sum())
            if n:
                issues.append(f"'{col}': {n} valores fuera de [0, 100]%")

    return issues


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_numeric_cols(df: pd.DataFrame, cols: Optional[List[str]]) -> List[str]:
    if cols:
        return [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    return df.select_dtypes(include="number").columns.tolist()
