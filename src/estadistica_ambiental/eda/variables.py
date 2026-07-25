"""
Tipificación automática de variables en datasets ambientales.

Clasifica cada columna en: numérica continua, numérica discreta,
categórica nominal, categórica ordinal, temporal, espacial o texto libre.
Permite sobreescrituras manuales para casos que la heurística no resuelve.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tipos de variable
# ---------------------------------------------------------------------------


class VariableType(str, Enum):
    NUMERIC_CONTINUOUS = "numerica_continua"
    NUMERIC_DISCRETE = "numerica_discreta"
    CATEGORICAL_NOMINAL = "categorica_nominal"
    CATEGORICAL_ORDINAL = "categorica_ordinal"
    TEMPORAL = "temporal"
    SPATIAL = "espacial"
    TEXT = "texto_libre"
    UNKNOWN = "desconocida"


# ---------------------------------------------------------------------------
# Patrones de nombre de columna para detección automática
# ---------------------------------------------------------------------------

_DATE_PATTERNS = re.compile(
    r"\b(fecha|date|time|hora|hora_utc|periodo|periodo_|año|mes|dia|"
    r"datetime|timestamp|year|month|day|week|semana)\b",
    re.IGNORECASE,
)

_SPATIAL_PATTERNS = re.compile(
    r"\b(lat|lon|lng|latitud|longitud|latitude|longitude|"
    r"coord|easting|northing|x_coord|y_coord|geom|geometry|"
    r"cod_dane|codigo_dane|cod_igac|municipio_cod|depto_cod)\b",
    re.IGNORECASE,
)

# Valores típicos de variables ordinales ambientales
_ORDINAL_VALUE_SETS = [
    {"buena", "aceptable", "moderada", "dañina", "muy dañina", "peligrosa"},
    {"bueno", "aceptable", "moderado", "dañino", "muy dañino", "peligroso"},
    {"bajo", "medio", "alto", "muy alto", "extremo"},
    {"baja", "media", "alta", "muy alta", "extrema"},
    {"leve", "moderado", "grave", "muy grave", "catastrófico"},
    {"excelente", "buena", "aceptable", "deficiente", "muy deficiente"},
    {"1", "2", "3", "4", "5"},
    {"i", "ii", "iii", "iv", "v"},
    {"low", "medium", "high", "very high", "extreme"},
    {"good", "moderate", "unhealthy for sensitive", "unhealthy", "very unhealthy", "hazardous"},
]

# Umbral: si n_unique / n_filas supera esto, se considera texto libre
_TEXT_CARDINALITY_THRESHOLD = 0.5
# Umbral: para numérica discreta, máximo de valores únicos
_DISCRETE_UNIQUE_THRESHOLD = 20
# Umbral: para numérica discreta, el rango no puede ser mayor que este
_DISCRETE_RANGE_THRESHOLD = 200


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------


@dataclass
class VariableInfo:
    name: str
    dtype: str
    var_type: VariableType
    n_unique: int
    n_missing: int
    missing_pct: float
    sample_values: List
    note: str = ""


@dataclass
class VariableCatalog:
    """Catálogo de variables tipificadas para un DataFrame ambiental."""

    variables: Dict[str, VariableInfo] = field(default_factory=dict)

    # --- Acceso por tipo ---

    def by_type(self, var_type: VariableType) -> List[str]:
        return [n for n, v in self.variables.items() if v.var_type == var_type]

    def numerics(self) -> List[str]:
        return self.by_type(VariableType.NUMERIC_CONTINUOUS) + self.by_type(
            VariableType.NUMERIC_DISCRETE
        )

    def continuous(self) -> List[str]:
        return self.by_type(VariableType.NUMERIC_CONTINUOUS)

    def discrete(self) -> List[str]:
        return self.by_type(VariableType.NUMERIC_DISCRETE)

    def categoricals(self) -> List[str]:
        return self.by_type(VariableType.CATEGORICAL_NOMINAL) + self.by_type(
            VariableType.CATEGORICAL_ORDINAL
        )

    def temporals(self) -> List[str]:
        return self.by_type(VariableType.TEMPORAL)

    def spatials(self) -> List[str]:
        return self.by_type(VariableType.SPATIAL)

    # --- Exportación ---

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for info in self.variables.values():
            rows.append(
                {
                    "variable": info.name,
                    "tipo": info.var_type.value,
                    "dtype_pandas": info.dtype,
                    "n_unicos": info.n_unique,
                    "faltantes_%": info.missing_pct,
                    "muestra_valores": str(info.sample_values[:5]),
                    "nota": info.note,
                }
            )
        return pd.DataFrame(rows)

    def summary(self) -> str:
        counts: Dict[str, int] = {}
        for info in self.variables.values():
            counts[info.var_type.value] = counts.get(info.var_type.value, 0) + 1

        lines = [f"=== Catálogo de variables ({len(self.variables)} columnas) ==="]
        for vtype, n in sorted(counts.items()):
            cols = [name for name, info in self.variables.items() if info.var_type.value == vtype]
            lines.append(f"\n{vtype} ({n}): {', '.join(cols)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------


def classify(
    df: pd.DataFrame,
    overrides: Optional[Dict[str, VariableType]] = None,
) -> VariableCatalog:
    """Clasifica automáticamente las columnas de un DataFrame ambiental.

    Args:
        df: DataFrame a tipificar.
        overrides: Mapa {columna: VariableType} para sobreescribir la heurística.
                   Ejemplo: {"calidad_agua": VariableType.CATEGORICAL_ORDINAL}
    """
    overrides = overrides or {}
    catalog = VariableCatalog()

    for col in df.columns:
        series = df[col]
        info = _classify_column(col, series)

        if col in overrides:
            original = info.var_type
            info.var_type = overrides[col]
            info.note = f"sobreescrita (auto: {original.value})"
            logger.debug("Columna '%s': %s → %s (manual)", col, original.value, info.var_type.value)

        catalog.variables[col] = info
        logger.debug("'%s' → %s", col, info.var_type.value)

    logger.info("Tipificación completada: %d columnas clasificadas", len(catalog.variables))
    return catalog


# ---------------------------------------------------------------------------
# Lógica de clasificación por columna
# ---------------------------------------------------------------------------


def _classify_column(col: str, series: pd.Series) -> VariableInfo:
    n_total = len(series)
    n_missing = int(series.isna().sum())
    valid = series.dropna()
    n_unique = int(valid.nunique())
    missing_pct = round(n_missing / n_total * 100, 2) if n_total else 0.0
    sample = valid.unique()[:5].tolist()

    var_type, note = _infer_type(col, series, valid, n_unique, n_total)

    return VariableInfo(
        name=col,
        dtype=str(series.dtype),
        var_type=var_type,
        n_unique=n_unique,
        n_missing=n_missing,
        missing_pct=missing_pct,
        sample_values=sample,
        note=note,
    )


def _infer_type(
    col: str,
    series: pd.Series,
    valid: pd.Series,
    n_unique: int,
    n_total: int,
) -> tuple[VariableType, str]:
    """Aplica la cascada de heurísticas y devuelve (tipo, nota)."""

    # 1. Dtype datetime ya parseado
    if pd.api.types.is_datetime64_any_dtype(series):
        return VariableType.TEMPORAL, ""

    # 2. Nombre sugiere fecha/tiempo
    if _DATE_PATTERNS.search(col):
        # Intentar parsear para confirmar
        try:
            pd.to_datetime(valid.head(10), errors="raise")
            return VariableType.TEMPORAL, "detectado por nombre de columna"
        except Exception:
            pass

    # 3. Nombre sugiere coordenada / código espacial
    if _SPATIAL_PATTERNS.search(col):
        return VariableType.SPATIAL, "detectado por nombre de columna"

    # 4. Bool → nominal
    if pd.api.types.is_bool_dtype(series):
        return VariableType.CATEGORICAL_NOMINAL, ""

    # 5. Columna numérica
    if pd.api.types.is_numeric_dtype(series):
        return _classify_numeric(valid, n_unique)

    # 6. Columna de objeto (string)
    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        return _classify_text(valid, n_unique, n_total)

    # 7. Categórica pandas nativa
    if hasattr(series, "cat"):
        return VariableType.CATEGORICAL_NOMINAL, "dtype category de pandas"

    return VariableType.UNKNOWN, "no se pudo determinar el tipo"


def _classify_numeric(valid: pd.Series, n_unique: int) -> tuple[VariableType, str]:
    """Distingue continua de discreta para columnas numéricas."""
    if n_unique == 0:
        return VariableType.NUMERIC_CONTINUOUS, "sin valores válidos"

    all_integer = (valid == valid.round(0)).all()
    value_range = float(valid.max() - valid.min())

    if (
        all_integer
        and n_unique <= _DISCRETE_UNIQUE_THRESHOLD
        and value_range <= _DISCRETE_RANGE_THRESHOLD
    ):
        return VariableType.NUMERIC_DISCRETE, f"{n_unique} valores únicos enteros"

    return VariableType.NUMERIC_CONTINUOUS, ""


def _classify_text(
    valid: pd.Series,
    n_unique: int,
    n_total: int,
) -> tuple[VariableType, str]:
    """Clasifica columnas de texto como nominal, ordinal o texto libre."""
    if n_total == 0 or n_unique == 0:
        return VariableType.CATEGORICAL_NOMINAL, "columna vacía"

    cardinality = n_unique / n_total

    # Alta cardinalidad → texto libre
    if cardinality >= _TEXT_CARDINALITY_THRESHOLD and n_unique > 10:
        return VariableType.TEXT, f"cardinalidad {cardinality:.0%}"

    # Verificar si los valores coinciden con escalas ordinales conocidas
    lower_values = {str(v).lower().strip() for v in valid.unique()}
    for ordinal_set in _ORDINAL_VALUE_SETS:
        if lower_values.issubset(ordinal_set) or ordinal_set.issubset(lower_values):
            return VariableType.CATEGORICAL_ORDINAL, "valores coinciden con escala ordinal conocida"
        if len(lower_values & ordinal_set) >= 3:
            return (
                VariableType.CATEGORICAL_ORDINAL,
                "valores parcialmente coinciden con escala ordinal",
            )

    return VariableType.CATEGORICAL_NOMINAL, f"{n_unique} categorías únicas"
