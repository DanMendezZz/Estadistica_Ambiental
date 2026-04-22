"""
Validación de plausibilidad física y calidad de datos ambientales.

Detecta: duplicados, rangos físicos imposibles, fechas inconsistentes,
coordenadas fuera de área de estudio. No lanza excepciones — devuelve
un ValidationReport con todos los hallazgos para que el analista decida.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rangos de plausibilidad física para variables ambientales colombianas
# (min, max) — valores fuera de este rango se marcan como sospechosos,
# NO se eliminan automáticamente.
# ---------------------------------------------------------------------------

PHYSICAL_RANGES: Dict[str, Tuple[float, float]] = {
    # Calidad del aire
    "pm25":          (0.0,   500.0),   # µg/m³
    "pm10":          (0.0,   600.0),   # µg/m³
    "pm1":           (0.0,   300.0),   # µg/m³
    "o3":            (0.0,   600.0),   # µg/m³
    "no2":           (0.0,   400.0),   # µg/m³
    "no":            (0.0,   400.0),   # µg/m³
    "co":            (0.0,    50.0),   # mg/m³
    "so2":           (0.0,   500.0),   # µg/m³
    "aqi":           (0.0,   500.0),   # índice
    # Meteorología
    "temperatura":   (-10.0,  45.0),   # °C (rango Colombia)
    "temp":          (-10.0,  45.0),   # °C
    "humedad":       (0.0,   100.0),   # %
    "hr":            (0.0,   100.0),   # %
    "precipitacion": (0.0,   300.0),   # mm/día (eventos extremos Colombia)
    "lluvia":        (0.0,   300.0),   # mm
    "presion":       (500.0, 1100.0),  # hPa
    "viento":        (0.0,   100.0),   # m/s
    "velocidad_viento": (0.0, 100.0),  # m/s
    "radiacion":     (0.0,  1400.0),   # W/m²
    # Calidad del agua
    "ph":            (0.0,    14.0),
    "od":            (0.0,    20.0),   # mg/L oxígeno disuelto
    "dbo":           (0.0,  1000.0),   # mg/L demanda bioquímica
    "dqo":           (0.0,  2000.0),   # mg/L demanda química
    "turbidez":      (0.0, 10000.0),   # NTU
    "conductividad": (0.0,  5000.0),   # µS/cm
    "sst":           (0.0,  5000.0),   # mg/L sólidos suspendidos totales
    "nitratos":      (0.0,   100.0),   # mg/L
    "fosforo":       (0.0,    50.0),   # mg/L
    # Hidrología
    "caudal":        (0.0, 1e7),       # m³/s — no puede ser negativo
    "nivel":         (0.0, 1e4),       # m s.n.m.
    # Coordenadas Colombia
    "latitud":       (-4.5,  13.0),    # grados decimales
    "lat":           (-4.5,  13.0),
    "longitud":      (-82.0, -66.0),   # grados decimales
    "lon":           (-82.0, -66.0),
    "lng":           (-82.0, -66.0),
}


# ---------------------------------------------------------------------------
# Dataclass de resultados
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    n_rows: int
    n_cols: int
    missing: Dict[str, float] = field(default_factory=dict)       # col → % faltantes
    duplicates_exact: int = 0
    duplicates_by_key: int = 0
    range_violations: Dict[str, dict] = field(default_factory=dict)  # col → {n, pct, min_obs, max_obs}
    temporal_issues: Dict[str, object] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"=== Reporte de validación ({self.n_rows} filas × {self.n_cols} cols) ===",
        ]

        # Faltantes
        high_missing = {c: v for c, v in self.missing.items() if v > 0}
        if high_missing:
            lines.append(f"\nFaltantes ({len(high_missing)} columnas con datos ausentes):")
            for col, pct in sorted(high_missing.items(), key=lambda x: -x[1]):
                lines.append(f"  {col}: {pct:.1f}%")
        else:
            lines.append("\nFaltantes: ninguno")

        # Duplicados
        lines.append(f"\nDuplicados exactos: {self.duplicates_exact}")
        if self.duplicates_by_key:
            lines.append(f"Duplicados por llave (estacion+fecha): {self.duplicates_by_key}")

        # Rangos
        if self.range_violations:
            lines.append(f"\nViolaciones de rango físico ({len(self.range_violations)} columnas):")
            for col, info in self.range_violations.items():
                lines.append(
                    f"  {col}: {info['n']} filas ({info['pct']:.1f}%) "
                    f"| obs [{info['min_obs']:.2f}, {info['max_obs']:.2f}] "
                    f"| esperado [{info['range'][0]}, {info['range'][1]}]"
                )
        else:
            lines.append("\nRangos físicos: sin violaciones detectadas")

        # Temporales
        if self.temporal_issues:
            lines.append("\nProblemas temporales:")
            for k, v in self.temporal_issues.items():
                lines.append(f"  {k}: {v}")

        # Advertencias adicionales
        for w in self.warnings:
            lines.append(f"  ⚠ {w}")

        return "\n".join(lines)

    _TEMPORAL_PROBLEM_KEYS = {"fechas_invalidas", "fechas_futuras", "fechas_duplicadas"}

    def has_issues(self) -> bool:
        temporal_problems = any(
            k in self._TEMPORAL_PROBLEM_KEYS for k in self.temporal_issues
        )
        return bool(
            self.duplicates_exact
            or self.duplicates_by_key
            or self.range_violations
            or temporal_problems
            or self.warnings
        )


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def validate(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    key_cols: Optional[List[str]] = None,
    ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    colombia_coords: bool = True,
) -> ValidationReport:
    """Valida un DataFrame ambiental y devuelve un reporte con todos los hallazgos.

    Args:
        df: DataFrame a validar.
        date_col: Nombre de la columna de fechas.
        key_cols: Columnas que forman la llave lógica (e.g. ['estacion', 'fecha']).
        ranges: Rangos personalizados {col: (min, max)} que sobreescriben los defaults.
        colombia_coords: Si True, valida latitud/longitud en el bounding box de Colombia.
    """
    effective_ranges = {**PHYSICAL_RANGES}
    if not colombia_coords:
        effective_ranges.pop("latitud", None)
        effective_ranges.pop("lat", None)
        effective_ranges.pop("longitud", None)
        effective_ranges.pop("lon", None)
        effective_ranges.pop("lng", None)
    if ranges:
        effective_ranges.update(ranges)

    report = ValidationReport(n_rows=len(df), n_cols=len(df.columns))
    report.missing = _check_missing(df)
    report.duplicates_exact, report.duplicates_by_key = _check_duplicates(df, key_cols)
    report.range_violations = _check_ranges(df, effective_ranges)

    if date_col and date_col in df.columns:
        report.temporal_issues = _check_temporal(df, date_col)

    _emit_warnings(report)
    logger.info("Validación completada. Issues: %s", report.has_issues())
    return report


# ---------------------------------------------------------------------------
# Checks individuales
# ---------------------------------------------------------------------------

def _check_missing(df: pd.DataFrame) -> Dict[str, float]:
    pct = (df.isnull().mean() * 100).round(2)
    return pct[pct > 0].to_dict()


def _check_duplicates(
    df: pd.DataFrame,
    key_cols: Optional[List[str]],
) -> Tuple[int, int]:
    exact = int(df.duplicated().sum())
    key_dups = 0
    if key_cols:
        valid_keys = [c for c in key_cols if c in df.columns]
        if valid_keys:
            key_dups = int(df.duplicated(subset=valid_keys).sum())
    return exact, key_dups


def _check_ranges(
    df: pd.DataFrame,
    ranges: Dict[str, Tuple[float, float]],
) -> Dict[str, dict]:
    violations = {}
    numeric_cols = df.select_dtypes(include="number").columns

    for col in numeric_cols:
        col_key = col.lower().replace(" ", "_")
        if col_key not in ranges:
            continue

        lo, hi = ranges[col_key]
        series = df[col].dropna()
        mask = (series < lo) | (series > hi)
        n = int(mask.sum())

        if n > 0:
            violations[col] = {
                "n": n,
                "pct": round(n / len(series) * 100, 2),
                "min_obs": float(series.min()),
                "max_obs": float(series.max()),
                "range": (lo, hi),
            }

    return violations


def _check_temporal(df: pd.DataFrame, date_col: str) -> Dict[str, object]:
    issues: Dict[str, object] = {}
    dates = pd.to_datetime(df[date_col], errors="coerce")

    # Fechas no parseables
    n_invalid = int(dates.isna().sum())
    if n_invalid:
        issues["fechas_invalidas"] = n_invalid

    # Fechas futuras
    now = pd.Timestamp(datetime.now())
    n_future = int((dates > now).sum())
    if n_future:
        issues["fechas_futuras"] = n_future

    # Duplicados temporales
    n_dup_dates = int(dates.duplicated().sum())
    if n_dup_dates:
        issues["fechas_duplicadas"] = n_dup_dates

    # Rango temporal
    valid_dates = dates.dropna()
    if len(valid_dates) > 1:
        issues["fecha_inicio"] = str(valid_dates.min().date())
        issues["fecha_fin"] = str(valid_dates.max().date())
        issues["n_periodos"] = len(valid_dates)

    return issues


def _emit_warnings(report: ValidationReport) -> None:
    for col, pct in report.missing.items():
        if pct > 40:
            msg = f"'{col}' tiene {pct:.1f}% de faltantes — considerar imputación avanzada (MICE, BRITS)"
            report.warnings.append(msg)
            logger.warning(msg)
    for col, info in report.range_violations.items():
        msg = f"'{col}': {info['n']} valores fuera del rango físico [{info['range'][0]}, {info['range'][1]}]"
        logger.warning(msg)
    if report.duplicates_exact:
        logger.warning("%d filas duplicadas exactas", report.duplicates_exact)
