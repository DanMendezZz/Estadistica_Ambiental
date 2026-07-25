"""EDA genérico — perfilado, calidad y reporte HTML para cualquier dataset.

Pensado como punto de partida cuando recibes un dataset ambiental nuevo y
quieres una primera mirada antes de modelar.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.eda.profiling import run_eda
from estadistica_ambiental.eda.quality import assess_quality
from estadistica_ambiental.eda.variables import classify
from estadistica_ambiental.reporting.stats_report import stats_report


def dataset_sintetico(n: int = 1000, seed: int = 21) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "fecha": fechas,
            "estacion": rng.choice(["A", "B", "C"], size=n),
            "temperatura": 22 + 5 * np.sin(2 * np.pi * np.arange(n) / 365) + rng.normal(0, 1.5, n),
            "humedad": np.clip(70 + rng.normal(0, 12, n), 0, 100),
            "precipitacion": np.where(rng.random(n) < 0.3, rng.exponential(8, n), 0.0),
            "tipo_evento": rng.choice(["seco", "lluvia", "tormenta"], size=n, p=[0.6, 0.3, 0.1]),
        }
    )


def main() -> None:
    df = dataset_sintetico()
    print(f"[1/4] Dataset sintético: {df.shape[0]} filas x {df.shape[1]} columnas.")

    catalog = classify(df)
    print("[2/4] Clasificación de variables:")
    print(catalog.summary())

    calidad = assess_quality(df, date_col="fecha")
    print(f"\n[3/4] {calidad.summary()[:600]}\n   ...")

    out_dir = Path("data/output/examples")
    out_dir.mkdir(parents=True, exist_ok=True)

    eda_path = run_eda(
        df, output=str(out_dir / "eda_profile.html"), date_col="fecha", use_ydata=False
    )
    stats_path = stats_report(df, output=str(out_dir / "eda_stats.html"), title="EDA — sintético")
    print(f"\n[4/4] HTMLs generados:\n   {eda_path}\n   {stats_path}")


if __name__ == "__main__":
    main()
