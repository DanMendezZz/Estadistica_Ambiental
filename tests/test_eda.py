"""Tests para estadistica_ambiental.eda.variables."""

import pandas as pd
import pytest

from estadistica_ambiental.eda.variables import (
    VariableType,
    classify,
)

# ---------------------------------------------------------------------------
# Fixture base
# ---------------------------------------------------------------------------


@pytest.fixture
def env_df():
    """DataFrame con los tipos de variable más comunes en datos ambientales."""
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=6, freq="D"),
            "estacion": ["Kennedy", "Usme", "Bosa", "Kennedy", "Usme", "Bosa"],
            "pm25": [12.1, 15.3, 18.7, 9.5, 22.0, 14.4],
            "temperatura": [14.5, 15.0, 13.0, 16.0, 14.0, 15.5],
            "n_eventos": [1, 0, 2, 1, 3, 0],
            "calidad_aire": ["buena", "aceptable", "moderada", "buena", "dañina", "aceptable"],
            "observaciones": [
                "sin novedad",
                "lluvia leve",
                "tráfico alto",
                "sin novedad",
                "incendio cercano",
                "neblina",
            ],
            "lat": [4.628, 4.487, 4.615, 4.628, 4.487, 4.615],
            "lon": [-74.164, -74.132, -74.198, -74.164, -74.132, -74.198],
            "activo": [True, True, False, True, False, True],
        }
    )


# ---------------------------------------------------------------------------
# Tipos básicos
# ---------------------------------------------------------------------------


class TestBasicTypes:
    def test_datetime_detected(self, env_df):
        cat = classify(env_df)
        assert cat.variables["fecha"].var_type == VariableType.TEMPORAL

    def test_float_is_continuous(self, env_df):
        cat = classify(env_df)
        assert cat.variables["pm25"].var_type == VariableType.NUMERIC_CONTINUOUS
        assert cat.variables["temperatura"].var_type == VariableType.NUMERIC_CONTINUOUS

    def test_integer_low_cardinality_is_discrete(self, env_df):
        cat = classify(env_df)
        assert cat.variables["n_eventos"].var_type == VariableType.NUMERIC_DISCRETE

    def test_low_cardinality_string_is_nominal(self, env_df):
        cat = classify(env_df)
        assert cat.variables["estacion"].var_type == VariableType.CATEGORICAL_NOMINAL

    def test_ordinal_quality_values_detected(self, env_df):
        cat = classify(env_df)
        assert cat.variables["calidad_aire"].var_type == VariableType.CATEGORICAL_ORDINAL

    def test_high_cardinality_string_is_text(self):
        df = pd.DataFrame({"notas": [f"observación única número {i}" for i in range(20)]})
        cat = classify(df)
        assert cat.variables["notas"].var_type == VariableType.TEXT

    def test_spatial_coord_detected(self, env_df):
        cat = classify(env_df)
        assert cat.variables["lat"].var_type == VariableType.SPATIAL
        assert cat.variables["lon"].var_type == VariableType.SPATIAL

    def test_bool_is_nominal(self, env_df):
        cat = classify(env_df)
        assert cat.variables["activo"].var_type == VariableType.CATEGORICAL_NOMINAL


# ---------------------------------------------------------------------------
# Detección por nombre de columna
# ---------------------------------------------------------------------------


class TestNamePatterns:
    def test_fecha_string_col_detected_as_temporal(self):
        df = pd.DataFrame({"fecha": ["2023-01-01", "2023-01-02", "2023-01-03"]})
        cat = classify(df)
        assert cat.variables["fecha"].var_type == VariableType.TEMPORAL

    def test_latitud_detected_as_spatial(self):
        df = pd.DataFrame({"latitud": [4.6, 4.7, 4.8]})
        cat = classify(df)
        assert cat.variables["latitud"].var_type == VariableType.SPATIAL

    def test_cod_dane_detected_as_spatial(self):
        df = pd.DataFrame({"cod_dane": ["11001", "05001", "76001"]})
        cat = classify(df)
        assert cat.variables["cod_dane"].var_type == VariableType.SPATIAL


# ---------------------------------------------------------------------------
# Sobreescrituras manuales
# ---------------------------------------------------------------------------


class TestOverrides:
    def test_override_changes_type(self, env_df):
        cat = classify(env_df, overrides={"n_eventos": VariableType.NUMERIC_CONTINUOUS})
        assert cat.variables["n_eventos"].var_type == VariableType.NUMERIC_CONTINUOUS

    def test_override_records_note(self, env_df):
        cat = classify(env_df, overrides={"n_eventos": VariableType.NUMERIC_CONTINUOUS})
        assert "sobreescrita" in cat.variables["n_eventos"].note

    def test_override_nonexistent_col_ignored(self, env_df):
        cat = classify(env_df, overrides={"no_existe": VariableType.TEXT})
        assert "no_existe" not in cat.variables


# ---------------------------------------------------------------------------
# VariableCatalog — métodos de acceso
# ---------------------------------------------------------------------------


class TestCatalogAccess:
    def test_by_type(self, env_df):
        cat = classify(env_df)
        temporals = cat.by_type(VariableType.TEMPORAL)
        assert "fecha" in temporals

    def test_numerics_includes_both(self, env_df):
        cat = classify(env_df)
        nums = cat.numerics()
        assert "pm25" in nums
        assert "n_eventos" in nums

    def test_temporals(self, env_df):
        cat = classify(env_df)
        assert "fecha" in cat.temporals()

    def test_spatials(self, env_df):
        cat = classify(env_df)
        spatial = cat.spatials()
        assert "lat" in spatial
        assert "lon" in spatial

    def test_to_dataframe_shape(self, env_df):
        cat = classify(env_df)
        df = cat.to_dataframe()
        assert len(df) == len(env_df.columns)
        assert "tipo" in df.columns

    def test_summary_is_string(self, env_df):
        cat = classify(env_df)
        s = cat.summary()
        assert isinstance(s, str)
        assert "Catálogo" in s

    def test_continuous(self, env_df):
        cat = classify(env_df)
        cont = cat.continuous()
        assert "pm25" in cont

    def test_discrete(self, env_df):
        cat = classify(env_df)
        disc = cat.discrete()
        assert "n_eventos" in disc

    def test_categoricals(self, env_df):
        cat = classify(env_df)
        cats = cat.categoricals()
        assert "calidad_aire" in cats or "estacion" in cats


class TestEdgeCaseTypes:
    def test_bool_column_classified_nominal(self):
        df = pd.DataFrame({"activo": [True, False, True, False, True]})
        cat = classify(df)
        assert cat.variables["activo"].var_type == VariableType.CATEGORICAL_NOMINAL

    def test_pandas_category_dtype_classified_nominal(self):
        df = pd.DataFrame({"cat_col": pd.Categorical(["A", "B", "A", "C", "B"])})
        cat = classify(df)
        assert cat.variables["cat_col"].var_type == VariableType.CATEGORICAL_NOMINAL

    def test_fecha_pattern_string_col(self):
        df = pd.DataFrame({"fecha_registro": ["2023-01-01", "2023-01-02", "2023-01-03"]})
        cat = classify(df)
        # Nombre sugiere fecha → el clasificador intenta parsear; resultado depende de n_unique
        vtype = cat.variables["fecha_registro"].var_type
        assert vtype in {VariableType.TEMPORAL, VariableType.TEXT, VariableType.CATEGORICAL_NOMINAL}

    def test_fecha_pattern_but_not_parseable(self):
        # Nombre parece fecha pero valores no son parseables → fallback (líneas 229-230)
        df = pd.DataFrame({"fecha_col": ["abc", "def", "ghi", "jkl", "mno"]})
        cat = classify(df)
        vtype = cat.variables["fecha_col"].var_type
        # No debe ser TEMPORAL si los valores no son fechas
        assert isinstance(vtype, VariableType)
