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
        assert out.parent.is_dir()
        assert out.stat().st_size > 500

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
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        # Datos faltantes 100% en pm25 deben aparecer en la sección de missing
        assert "Datos faltantes" in content

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
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        # Las columnas categóricas deben aparecer en el catálogo
        assert "estacion" in content


class TestProfilingCoverage:
    """Tests de cobertura para rutas no ejercidas en TestRunEda."""

    def test_use_ydata_import_error_handled(self, tmp_path):
        """_try_ydata: ImportError capturado sin crash (ydata-profiling no instalado)."""
        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0], "temp": [14.0, 15.0, 16.0]})
        out = tmp_path / "eda.html"
        result = run_eda(df, output=str(out), use_ydata=True, use_sweetviz=False)
        assert result.exists()
        # El reporte fallback debe haberse generado igual con HTML válido
        content = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert result.stat().st_size > 500

    def test_use_ydata_with_mock(self, tmp_path, monkeypatch):
        """_try_ydata: ruta de éxito cuando ydata-profiling está disponible (mock)."""
        import sys
        import types
        from unittest.mock import MagicMock

        mock_profile = MagicMock()
        mock_profile.to_file = MagicMock()
        MockProfileReport = MagicMock(return_value=mock_profile)

        fake_ydata = types.ModuleType("ydata_profiling")
        fake_ydata.ProfileReport = MockProfileReport
        monkeypatch.setitem(sys.modules, "ydata_profiling", fake_ydata)

        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0]})
        out = tmp_path / "eda.html"
        run_eda(df, output=str(out), use_ydata=True, use_sweetviz=False)
        assert out.exists()
        # Verifica que el path de éxito de _try_ydata invocó ProfileReport y to_file
        MockProfileReport.assert_called_once()
        mock_profile.to_file.assert_called_once()

    def test_use_sweetviz_import_error_handled(self, tmp_path):
        """_try_sweetviz: ImportError capturado sin crash (sweetviz no instalado)."""
        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0]})
        out = tmp_path / "eda.html"
        result = run_eda(df, output=str(out), use_ydata=False, use_sweetviz=True)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert result.stat().st_size > 500

    def test_use_sweetviz_with_mock(self, tmp_path, monkeypatch):
        """_try_sweetviz: ruta de éxito con sweetviz disponible (mock)."""
        import sys
        import types
        from unittest.mock import MagicMock

        mock_report = MagicMock()
        mock_report.show_html = MagicMock()
        mock_sv = types.ModuleType("sweetviz")
        mock_sv.analyze = MagicMock(return_value=mock_report)
        monkeypatch.setitem(sys.modules, "sweetviz", mock_sv)

        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0]})
        out = tmp_path / "eda.html"
        run_eda(df, output=str(out), use_ydata=False, use_sweetviz=True)
        assert out.exists()
        # Verifica que el path de éxito de _try_sweetviz invocó analyze y show_html
        mock_sv.analyze.assert_called_once()
        mock_report.show_html.assert_called_once()

    def test_outliers_table_section_with_extreme_values(self, tmp_path):
        """_section_outliers: genera tabla cuando hay outliers reales (z-score > 3)."""
        df = pd.DataFrame({"pm25": [10.0] * 20 + [500.0, 800.0]})
        out = tmp_path / "eda_outliers.html"
        run_eda(df, output=str(out), use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "ADR-002" in content

    def test_range_violations_table_generated(self, tmp_path):
        """_section_range_violations: genera tabla cuando pm25 tiene valores negativos."""
        df = pd.DataFrame(
            {
                "pm25": [-50.0, 5.0, 10.0],
                "fecha": pd.date_range("2023-01-01", periods=3, freq="D"),
            }
        )
        out = tmp_path / "eda_ranges.html"
        run_eda(df, output=str(out), date_col="fecha", use_ydata=False)
        content = out.read_text(encoding="utf-8")
        assert "Rangos físicos" in content


class TestProfilingPrivateFunctions:
    """Tests directos sobre _try_ydata y _try_sweetviz para cubrir ramas de excepción."""

    def test_try_ydata_import_error_path(self, tmp_path):
        """_try_ydata: cuando ydata-profiling no está instalado (lines 277-278 equiv)."""
        from estadistica_ambiental.eda.profiling import _try_ydata

        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0]})
        # sweetviz no instalado → ImportError silenciosa
        _try_ydata(df, tmp_path / "eda.html")

    def test_try_ydata_exception_path(self, tmp_path, monkeypatch):
        """_try_ydata: cuando ProfileReport lanza excepción (lines 265-266)."""
        import sys
        import types

        mock_profile = types.ModuleType("ydata_profiling")

        def bad_profile(df, **kwargs):
            raise RuntimeError("forced ydata error")

        mock_profile.ProfileReport = bad_profile
        monkeypatch.setitem(sys.modules, "ydata_profiling", mock_profile)

        from estadistica_ambiental.eda.profiling import _try_ydata

        df = pd.DataFrame({"pm25": [10.0, 12.0]})
        _try_ydata(df, tmp_path / "eda.html")

    def test_try_sweetviz_import_error_path(self, tmp_path):
        """_try_sweetviz: cuando sweetviz no está instalado (lines 277-278)."""
        from estadistica_ambiental.eda.profiling import _try_sweetviz

        df = pd.DataFrame({"pm25": [10.0, 12.0, 15.0]})
        _try_sweetviz(df, tmp_path / "eda.html")

    def test_try_sweetviz_exception_path(self, tmp_path, monkeypatch):
        """_try_sweetviz: cuando sv.analyze lanza excepción (lines 279-280)."""
        import sys
        import types

        mock_sv = types.ModuleType("sweetviz")

        def bad_analyze(df, **kwargs):
            raise RuntimeError("forced sweetviz error")

        mock_sv.analyze = bad_analyze
        monkeypatch.setitem(sys.modules, "sweetviz", mock_sv)

        from estadistica_ambiental.eda.profiling import _try_sweetviz

        df = pd.DataFrame({"pm25": [10.0, 12.0]})
        _try_sweetviz(df, tmp_path / "eda.html")
