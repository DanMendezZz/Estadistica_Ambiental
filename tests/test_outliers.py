"""Tests para preprocessing/outliers.py.

Cobertura:
  - flag_outliers (smoke + happy path; cobertura más extensa en otros tests).
  - detect_regional_episodes (M-01, feedback CAR §3.1.A): episodios sostenidos
    con confirmación espacial entre estaciones vecinas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from estadistica_ambiental.preprocessing.outliers import (
    detect_regional_episodes,
    flag_outliers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_two_station_df(
    n: int = 200,
    spike_value: float = 200.0,
    spike_start: int = 50,
    spike_count: int = 6,
    in_both: bool = True,
    rng_seed: int = 0,
) -> pd.DataFrame:
    """Genera un DataFrame con dos estaciones cercanas (~7 km) y un pico
    sostenido en la primera; opcionalmente en la segunda también.
    """
    rng = np.random.default_rng(rng_seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="h")

    base_a = rng.normal(25.0, 5.0, n)
    base_b = rng.normal(25.0, 5.0, n)

    base_a[spike_start : spike_start + spike_count] = spike_value
    if in_both:
        base_b[spike_start : spike_start + spike_count] = spike_value

    rows = []
    for ts, va, vb in zip(dates, base_a, base_b):
        rows.append({"fecha": ts, "estacion": "A", "lat": 4.60, "lon": -74.10, "pm25": va})
        rows.append({"fecha": ts, "estacion": "B", "lat": 4.65, "lon": -74.15, "pm25": vb})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# flag_outliers — smoke
# ---------------------------------------------------------------------------


class TestFlagOutliers:
    def test_iqr_marks_extremes(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
        out = flag_outliers(df, cols=["x"], method="iqr")
        assert out["x_outlier"].iloc[-1]
        assert not out["x_outlier"].iloc[0]

    def test_treat_clip_caps_values(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
        out = flag_outliers(df, cols=["x"], method="iqr", treat=True, treatment="clip")
        assert out["x"].iloc[-1] < 100.0

    def test_invalid_method_raises(self):
        df = pd.DataFrame({"x": [1.0, 2.0]})
        with pytest.raises(ValueError, match="method debe ser"):
            flag_outliers(df, cols=["x"], method="nope")


# ---------------------------------------------------------------------------
# detect_regional_episodes — M-01
# ---------------------------------------------------------------------------


class TestDetectRegionalEpisodes:
    """Verifica el algoritmo de episodios regionales con confirmación espacial."""

    def test_episode_in_both_stations_is_regional(self):
        """Pico sostenido ≥4 h presente en ambas estaciones cercanas → 'regional'."""
        df = _make_two_station_df(in_both=True, spike_count=6)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
            iqr_hard_mult=3.0,
            iqr_soft_mult=1.5,
            min_duration_hours=4,
            neighbor_radius_km=50.0,
        )
        flags_a = out.loc[out["estacion"] == "A", "flag_episode"]
        assert (flags_a == "regional").sum() >= 4, flags_a.value_counts().to_dict()
        # No debe quedar ninguno marcado 'puntual' en este caso
        assert (flags_a == "puntual").sum() == 0

    def test_episode_only_in_one_station_is_puntual(self):
        """Pico sostenido sólo en A (B se mantiene normal) → 'puntual' en A."""
        df = _make_two_station_df(in_both=False, spike_count=6)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
            min_duration_hours=4,
            neighbor_radius_km=50.0,
        )
        flags_a = out.loc[out["estacion"] == "A", "flag_episode"]
        # Al menos 4 horas marcadas como puntual (no confirmadas por B)
        assert (flags_a == "puntual").sum() >= 4
        assert (flags_a == "regional").sum() == 0

    def test_short_spike_is_ignored(self):
        """Pico de 2 h < min_duration_hours=4 → permanece 'original'."""
        df = _make_two_station_df(in_both=True, spike_count=2)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
            min_duration_hours=4,
        )
        flagged = out["flag_episode"].value_counts().to_dict()
        assert flagged.get("regional", 0) == 0
        assert flagged.get("puntual", 0) == 0

    def test_isolated_station_no_neighbor_within_radius(self):
        """Si no hay vecinos en el radio → criterio temporal basta (regional)."""
        df = _make_two_station_df(in_both=False, spike_count=6)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
            min_duration_hours=4,
            neighbor_radius_km=1.0,  # B queda fuera del radio → A está aislada
        )
        flags_a = out.loc[out["estacion"] == "A", "flag_episode"]
        assert (flags_a == "regional").sum() >= 4

    def test_min_neighbors_zero_disables_confirmation(self):
        """min_neighbors_confirmed=0 marca todo episodio sostenido como regional."""
        df = _make_two_station_df(in_both=False, spike_count=6)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
            min_duration_hours=4,
            min_neighbors_confirmed=0,
        )
        flags_a = out.loc[out["estacion"] == "A", "flag_episode"]
        assert (flags_a == "regional").sum() >= 4

    def test_missing_column_raises(self):
        df = _make_two_station_df()
        with pytest.raises(KeyError, match="Columnas requeridas"):
            detect_regional_episodes(
                df,
                value_col="caudal",  # no existe
                station_col="estacion",
                datetime_col="fecha",
                lat_col="lat",
                lon_col="lon",
            )

    def test_does_not_mutate_input(self):
        df = _make_two_station_df(in_both=True, spike_count=6)
        df_before = df.copy()
        _ = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
        )
        pd.testing.assert_frame_equal(df, df_before)

    def test_does_not_modify_values(self):
        """A diferencia de flag_spatial_episodes, no debe modificar la columna value_col."""
        df = _make_two_station_df(in_both=True, spike_count=6)
        out = detect_regional_episodes(
            df,
            value_col="pm25",
            station_col="estacion",
            datetime_col="fecha",
            lat_col="lat",
            lon_col="lon",
        )
        # Los valores originales se preservan exactamente
        np.testing.assert_array_equal(out["pm25"].to_numpy(), df["pm25"].to_numpy())

    def test_export_path(self):
        """Verifica que la función esté exportada desde el package."""
        from estadistica_ambiental.preprocessing import detect_regional_episodes as fn

        assert callable(fn)
