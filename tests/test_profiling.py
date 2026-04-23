"""Tests para estadistica_ambiental.eda.profiling."""

import pandas as pd
import pytest

from estadistica_ambiental.eda.profiling import run_eda


@pytest.fixture
def env_df():
    return pd.DataFrame(
        {
            "fecha": pd.date_range("2023-01-01", periods=20, freq="D"),
            "estacion": ["Kennedy", "Usme"] * 10,
            "pm25": [
                10.0,
                None,
                12.0,
                15.0,
                None,
                18.0,
                9.0,
                11.0,
                13.0,
                14.0,
                10.5,
                12.5,
                11.5,
                16.0,
                None,
                13.5,
                14.5,
                10.0,
                12.0,
                15.5,
            ],
            "pm10": [20.0 + i for i in range(20)],
            "temperatura": [14.0 + (i % 5) * 0.5 for i in range(20)],
            "calidad": ["buena", "aceptable", "moderada", "buena", "dañina"] * 4,
        }
    )


class TestRunEda:
    def test_creates_html_file(self, env_df, tmp_path):
        out = tmp_path / "eda_test.html"
        result = run_eda(env_df, output=str(out), date_col="fecha", use_ydata=False)
        assert result.exists()
        assert result.suffix == ".html"

    def test_html_contains_title(self, env_df, tmp_path):
        out = tmp_path / "eda_test.html"
        run_eda(env_df, output=str(out), title="Prueba EDA", use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "Prueba EDA" in content

    def test_html_contains_variable_catalog(self, env_df, tmp_path):
        out = tmp_path / "eda_test.html"
        run_eda(env_df, output=str(out), use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "Catálogo de variables" in content
        assert "pm25" in content

    def test_html_contains_missing_section(self, env_df, tmp_path):
        out = tmp_path / "eda_test.html"
        run_eda(env_df, output=str(out), use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "Datos faltantes" in content

    def test_html_contains_descriptive_stats(self, env_df, tmp_path):
        out = tmp_path / "eda_test.html"
        run_eda(env_df, output=str(out), use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "Estadísticas descriptivas" in content

    def test_creates_parent_dirs(self, env_df, tmp_path):
        out = tmp_path / "subdir" / "nested" / "eda.html"
        run_eda(env_df, output=str(out), use_ydata=False)
        assert out.exists()

    def test_returns_path_object(self, env_df, tmp_path):
        from pathlib import Path

        out = tmp_path / "eda.html"
        result = run_eda(env_df, output=str(out), use_ydata=False)
        assert isinstance(result, Path)

    def test_html_is_valid_utf8(self, env_df, tmp_path):
        out = tmp_path / "eda.html"
        run_eda(env_df, output=str(out), use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_no_crash_all_missing_col(self, tmp_path):
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=5, freq="D"),
                "pm25": [None] * 5,
                "temp": [14.0] * 5,
            }
        )
        out = tmp_path / "eda.html"
        run_eda(df, output=str(out), date_col="fecha", use_ydata=False)
        assert out.exists()

    def test_no_crash_no_numeric_cols(self, tmp_path):
        df = pd.DataFrame(
            {
                "estacion": ["A", "B", "C"],
                "calidad": ["buena", "mala", "regular"],
            }
        )
        out = tmp_path / "eda.html"
        run_eda(df, output=str(out), use_ydata=False)
        assert out.exists()
