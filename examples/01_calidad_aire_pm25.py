"""Calidad del aire — PM2.5: carga real (SISAIRE) o fallback sintético,
luego reporta excedencias contra Res. 2254/2017 y guías OMS 2021.

Si tienes datos SISAIRE/CAR locales:
    setx SISAIRE_LOCAL_DIR "<carpeta con CAR_<año>.csv>"
y reejecutá. Si no, corre con datos sintéticos.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.inference.intervals import exceedance_report
from estadistica_ambiental.io.connectors import load_sisaire_local


def cargar_pm25() -> pd.DataFrame:
    try:
        df = load_sisaire_local(anios=2024, parametro="pm25")
        print(f"[real] {len(df):,} registros SISAIRE 2024.")
        return df
    except FileNotFoundError as e:
        print(f"[fallback] {e}\nGenerando PM2.5 sintético horario.")
        rng = np.random.default_rng(42)
        n = 24 * 365
        fechas = pd.date_range("2024-01-01", periods=n, freq="h")
        diurno = 8 * np.sin(2 * np.pi * np.arange(n) / 24)
        estacional = 5 * np.sin(2 * np.pi * np.arange(n) / (24 * 365))
        pm25 = np.clip(22 + diurno + estacional + rng.normal(0, 6, n), 0, None)
        return pd.DataFrame({"fecha": fechas, "estacion": "sintetica", "pm25": pm25})


def main() -> None:
    df = cargar_pm25()

    daily = (
        df.assign(dia=df["fecha"].dt.floor("D"))
        .groupby("dia", as_index=False)["pm25"]
        .mean()
        .rename(columns={"dia": "fecha"})
    )
    print(f"\nPromedio diario: {len(daily)} días | media={daily['pm25'].mean():.1f} µg/m³")

    rep = exceedance_report(daily["pm25"], variable="pm25")
    print("\n=== Excedencias PM2.5 (diarias) ===")
    print(rep.to_string(index=False))

    out = Path("data/output/examples") / "pm25_exceedances.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rep.to_csv(out, index=False)
    print(f"\nReporte guardado en: {out}")


if __name__ == "__main__":
    main()
