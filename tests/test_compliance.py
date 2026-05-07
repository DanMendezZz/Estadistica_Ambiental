"""Tests para exceedance_report, enso_lagged y compliance_report."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.config import ENSO_LAG_MESES, ENSO_THRESHOLDS
from estadistica_ambiental.features.climate import _classify_enso_intensity, enso_lagged
from estadistica_ambiental.inference.intervals import exceedance_report

# ===========================================================================
# exceedance_report
# ===========================================================================


class TestExceedanceReport:
    def test_pm25_returns_4_rows(self):
        """PM2.5 tiene 4 normas registradas (CO 24h, CO anual, OMS 24h, OMS anual)."""
        s = pd.Series([10.0, 40.0, 60.0, 8.0, 20.0])
        rep = exceedance_report(s, variable="pm25")
        assert len(rep) == 4

    def test_pm25_columns_present(self):
        s = pd.Series([20.0] * 10)
        rep = exceedance_report(s, variable="pm25")
        for col in ["norma", "umbral", "tipo", "n_exceedances", "pct_exceed", "cumple"]:
            assert col in rep.columns

    def test_all_below_threshold_cumple(self):
        """Serie con todos los valores muy bajos → todas las normas se cumplen."""
        s = pd.Series([1.0, 2.0, 1.5, 0.5])
        rep = exceedance_report(s, variable="pm25")
        assert rep["cumple"].all()

    def test_all_above_strictest_threshold_no_cumple(self):
        """Serie con valores muy altos → ninguna norma se cumple."""
        s = pd.Series([200.0] * 50)
        rep = exceedance_report(s, variable="pm25")
        assert not rep["cumple"].any()

    def test_unknown_variable_returns_empty(self):
        """Variable sin normas registradas → DataFrame vacío."""
        s = pd.Series([1.0, 2.0, 3.0])
        rep = exceedance_report(s, variable="variable_inexistente_xyz")
        assert rep.empty

    def test_dbo5_returns_rows(self):
        """DBO5 tiene normas tanto de agua potable como de vertimientos."""
        s = pd.Series([5.0, 50.0, 200.0])
        rep = exceedance_report(s, variable="dbo5")
        assert len(rep) >= 2

    def test_od_min_threshold(self):
        """OD tiene umbral mínimo (excedencia = estar por debajo)."""
        s = pd.Series([6.0, 2.0, 8.0, 1.5])  # 2.0 y 1.5 < 4.0 mg/L
        rep = exceedance_report(s, variable="od")
        assert not rep.empty
        row = rep[rep["tipo"] == "mínimo"].iloc[0]
        assert row["n_exceedances"] == 2

    def test_pct_exceed_calculation(self):
        """100 valores, 10 superan el umbral → pct_exceed ≈ 10%."""
        vals = [50.0] * 10 + [5.0] * 90  # 10 > 37 µg/m³ (Res 2254 24h)
        s = pd.Series(vals)
        rep = exceedance_report(s, variable="pm25")
        norma_24h = rep[rep["norma"].str.contains("24h") & rep["norma"].str.contains("2254")]
        assert len(norma_24h) == 1
        assert norma_24h.iloc[0]["pct_exceed"] == pytest.approx(10.0, rel=0.01)

    def test_return_period_none_when_no_exceedances(self):
        s = pd.Series([1.0] * 30)
        rep = exceedance_report(s, variable="pm25")
        rows_no_exceed = rep[rep["n_exceedances"] == 0]
        assert (rows_no_exceed["return_period_days"].isna()).all()


# ===========================================================================
# enso_lagged
# ===========================================================================


class TestEnsoLagged:
    @pytest.fixture
    def mock_oni(self):
        """ONI ficticio con 5 años de datos mensuales."""
        fechas = pd.date_range("2020-01-01", periods=60, freq="MS")
        oni_vals = np.sin(np.linspace(0, 4 * np.pi, 60)) * 1.5
        return pd.DataFrame(
            {
                "fecha": fechas,
                "oni": oni_vals,
                "fase": [_classify_enso_intensity(v) for v in oni_vals],
                "intensidad": [_classify_enso_intensity(v) for v in oni_vals],
            }
        )

    @pytest.fixture
    def sample_df(self):
        fechas = pd.date_range("2020-07-01", periods=30, freq="MS")
        return pd.DataFrame(
            {
                "fecha": fechas,
                "caudal": np.random.gamma(3, 10, 30),
            }
        )

    def test_adds_oni_lag_column(self, sample_df, mock_oni):
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", lag_meses=3)
        assert "oni_lag3" in result.columns

    def test_adds_fase_and_intensidad_columns(self, sample_df, mock_oni):
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", lag_meses=2)
        assert "fase_lag2" in result.columns
        assert "intensidad_lag2" in result.columns

    def test_adds_enso_dummies(self, sample_df, mock_oni):
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", lag_meses=3)
        dummy_cols = [c for c in result.columns if c.startswith("enso_lag")]
        assert len(dummy_cols) > 0

    def test_linea_tematica_applies_correct_lag(self, sample_df, mock_oni):
        """oferta_hidrica usa lag=4 según config.ENSO_LAG_MESES."""
        expected_lag = ENSO_LAG_MESES["oferta_hidrica"]
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", linea_tematica="oferta_hidrica")
        assert f"oni_lag{expected_lag}" in result.columns

    def test_lag_meses_overrides_linea_tematica(self, sample_df, mock_oni):
        """lag_meses explícito tiene precedencia sobre linea_tematica."""
        result = enso_lagged(
            sample_df, mock_oni, date_col="fecha", linea_tematica="oferta_hidrica", lag_meses=1
        )
        assert "oni_lag1" in result.columns

    def test_original_columns_preserved(self, sample_df, mock_oni):
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", lag_meses=2)
        assert "fecha" in result.columns
        assert "caudal" in result.columns

    def test_row_count_preserved(self, sample_df, mock_oni):
        result = enso_lagged(sample_df, mock_oni, date_col="fecha", lag_meses=3)
        assert len(result) == len(sample_df)


class TestEnsoClassification:
    @pytest.mark.parametrize(
        "oni,expected_fase",
        [
            (2.0, "niño"),
            (0.8, "niño"),
            (0.3, "neutro"),
            (-0.3, "neutro"),
            (-0.8, "niña"),
            (-2.0, "niña"),
        ],
    )
    def test_fase_classification(self, oni, expected_fase):
        from estadistica_ambiental.features.climate import _classify_enso

        assert _classify_enso(oni) == expected_fase

    @pytest.mark.parametrize(
        "oni,expected_intensity",
        [
            (2.0, "fuerte"),
            (0.8, "moderado"),
            (0.3, "neutro"),
            (-0.8, "moderado"),
            (-2.0, "fuerte"),
        ],
    )
    def test_intensity_classification(self, oni, expected_intensity):
        assert _classify_enso_intensity(oni) == expected_intensity

    def test_thresholds_from_config(self):
        """Los umbrales de clasificación vienen de config.ENSO_THRESHOLDS."""
        assert ENSO_THRESHOLDS["nino"] == 0.5
        assert ENSO_THRESHOLDS["nina"] == -0.5
        assert ENSO_THRESHOLDS["nino_fuerte"] == 1.5


# ===========================================================================
# compliance_report (integración)
# ===========================================================================


class TestComplianceReport:
    @pytest.fixture
    def air_quality_df(self):
        np.random.seed(42)
        n = 60
        return pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=n, freq="D"),
                "pm25": np.random.gamma(4, 8, n),  # algunos superarán norma 37
                "pm10": np.random.gamma(5, 10, n),
                "estacion": ["Kennedy"] * n,
            }
        )

    def test_creates_html_file(self, air_quality_df, tmp_path):
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        out = tmp_path / "test_compliance.html"
        result = compliance_report(
            air_quality_df,
            variables=["pm25", "pm10"],
            date_col="fecha",
            linea_tematica="calidad_aire",
            output=str(out),
        )
        assert result.exists()
        assert result.stat().st_size > 1000  # el HTML tiene contenido real

    def test_html_contains_variable_names(self, air_quality_df, tmp_path):
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        out = tmp_path / "test_compliance2.html"
        compliance_report(
            air_quality_df,
            variables=["pm25"],
            date_col="fecha",
            output=str(out),
        )
        content = out.read_text(encoding="utf-8")
        assert "PM25" in content
        assert "2254" in content  # menciona Res. 2254

    def test_html_contains_semaforo(self, air_quality_df, tmp_path):
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        out = tmp_path / "test_compliance3.html"
        compliance_report(
            air_quality_df,
            variables=["pm25"],
            date_col="fecha",
            output=str(out),
        )
        content = out.read_text(encoding="utf-8")
        assert "semaforo" in content

    def test_custom_threshold_included(self, air_quality_df, tmp_path):
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        out = tmp_path / "test_compliance4.html"
        compliance_report(
            air_quality_df,
            variables=["pm25"],
            date_col="fecha",
            output=str(out),
            custom_thresholds={"pm25": 20.0},
        )
        content = out.read_text(encoding="utf-8")
        assert "personalizado" in content

    def test_water_quality_variables(self, tmp_path):
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=30, freq="D"),
                "od": np.random.uniform(2, 10, 30),
                "dbo5": np.random.uniform(5, 150, 30),
                "ph": np.random.uniform(6, 9.5, 30),
            }
        )
        out = tmp_path / "test_water.html"
        result = compliance_report(
            df,
            variables=["od", "dbo5", "ph"],
            date_col="fecha",
            linea_tematica="recurso_hidrico",
            output=str(out),
        )
        assert result.exists()
        assert result.stat().st_size > 1000
        content = result.read_text(encoding="utf-8")
        # Las tres variables hídricas deben aparecer en el reporte
        assert "OD" in content
        assert "DBO5" in content
        assert "PH" in content

    def test_missing_variable_skipped(self, air_quality_df, tmp_path):
        """Variable que no existe en el df no rompe el reporte."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        out = tmp_path / "test_skip.html"
        result = compliance_report(
            air_quality_df,
            variables=["pm25", "variable_inexistente"],
            date_col="fecha",
            output=str(out),
        )
        assert result.exists()
        assert result.stat().st_size > 1000
        content = result.read_text(encoding="utf-8")
        # PM25 sí debe aparecer; variable_inexistente debe ser ignorada limpiamente
        assert "PM25" in content
        assert "variable_inexistente" not in content


class TestComplianceReportCoverage:
    """Tests de cobertura para ramas no ejercidas en TestComplianceReport."""

    def test_all_vars_not_in_df_empty_sections(self, tmp_path):
        """_section_semaforo({}) y _section_tabla_exceedances({}) cuando all_dfs vacío (lines 154, 188)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame({"temperatura": [14.0, 15.0, 16.0]})
        out = tmp_path / "empty.html"
        result = compliance_report(df, variables=["pm25"], date_col="fecha", output=str(out))
        assert result.exists()
        content = out.read_text(encoding="utf-8")
        assert "Sin variables con normas colombianas" in content

    def test_variable_no_norms_gray_and_table_empty_rep(self, tmp_path):
        """temperatura sin normas → tarjeta gris (line 159) y fila 'Sin norma' en tabla (lines 193-197)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
                "pm25": [50.0] * 10,
                "temperatura": [14.0] * 10,
            }
        )
        out = tmp_path / "gray.html"
        result = compliance_report(
            df,
            variables=["pm25", "temperatura"],
            date_col="fecha",
            output=str(out),
        )
        assert result.exists()
        content = out.read_text(encoding="utf-8")
        assert "Sin norma" in content or "Sin norma colombiana" in content

    def test_all_values_comply_green_card(self, tmp_path):
        """Valores pm25 muy bajos → max_exc == 0 → tarjeta verde CUMPLE (line 163)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
                "pm25": [1.0] * 10,
            }
        )
        out = tmp_path / "green.html"
        result = compliance_report(df, variables=["pm25"], date_col="fecha", output=str(out))
        assert result.exists()
        content = out.read_text(encoding="utf-8")
        assert "CUMPLE" in content

    def test_small_exceedance_yellow_card(self, tmp_path):
        """~5% excedencia OMS annual → 0 < max_exc <= 10 → tarjeta amarilla ALERTA (line 165)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        # 5 valores ligeramente sobre OMS annual (5 µg/m³), 95 por debajo
        vals = [6.0] * 5 + [4.0] * 95
        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=100, freq="D"),
                "pm25": vals,
            }
        )
        out = tmp_path / "yellow.html"
        result = compliance_report(df, variables=["pm25"], date_col="fecha", output=str(out))
        assert result.exists()
        content = out.read_text(encoding="utf-8")
        assert "ALERTA" in content

    def test_no_date_col_in_df_series_skipped(self, tmp_path):
        """date_col ausente en df → _section_series retorna "" (line 235)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame({"pm25": [50.0] * 10})
        out = tmp_path / "no_date.html"
        result = compliance_report(
            df, variables=["pm25"], date_col="fecha_inexistente", output=str(out)
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        # PM25 sigue siendo evaluado; las series temporales se omiten en silencio
        assert "PM25" in content

    def test_linea_tematica_without_ficha_file(self, tmp_path):
        """linea_tematica sin archivo md → _section_ficha_dominio retorna "" (line 321)."""
        from estadistica_ambiental.reporting.compliance_report import compliance_report

        df = pd.DataFrame(
            {
                "fecha": pd.date_range("2023-01-01", periods=5, freq="D"),
                "pm25": [10.0] * 5,
            }
        )
        out = tmp_path / "no_ficha.html"
        result = compliance_report(
            df,
            variables=["pm25"],
            date_col="fecha",
            linea_tematica="linea_inexistente_xyz_abc",
            output=str(out),
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<html" in content.lower()
        # La sección de ficha de dominio debe estar ausente (sin linea válida)
        assert "linea_inexistente_xyz_abc" not in content

    def test_ficha_exists_but_no_resumen_returns_empty(self, tmp_path, monkeypatch):
        """_section_ficha_dominio: ficha sin sección ## Resumen → retorna "" (line 336)."""
        import importlib

        cr_module = importlib.import_module("estadistica_ambiental.reporting.compliance_report")
        monkeypatch.setattr(cr_module, "DOCS_FUENTES", tmp_path)
        ficha = tmp_path / "test_linea.md"
        ficha.write_text("# Test\n\n## Otra Sección\nAlgún texto.\n", encoding="utf-8")

        result = cr_module._section_ficha_dominio("test_linea")
        assert result == ""
