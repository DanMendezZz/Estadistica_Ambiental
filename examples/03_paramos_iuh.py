"""Páramos — Índice de Retención Hídrica (IRH) y gradiente Caldas-Lang.

Demuestra:
- Validación con rangos de dominio para línea 'paramos'.
- Cálculo de IRH (categorización IDEAM/ENA usando IRH_THRESHOLDS).
- Gradiente Caldas-Lang (P/ETP) como proxy de zona de vida.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.config import IRH_THRESHOLDS
from estadistica_ambiental.io.validators import validate


def datos_paramos_sinteticos(n: int = 36, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2022-01-01", periods=n, freq="MS")
    altitud = rng.uniform(3200, 4200, n)
    precip = 1500 + 0.4 * (altitud - 3200) + rng.normal(0, 120, n)
    et_pot = 600 - 0.05 * (altitud - 3200) + rng.normal(0, 30, n)
    return pd.DataFrame(
        {
            "fecha": fechas,
            "estacion": [f"P{i % 5}" for i in range(n)],
            "altitud_m": altitud,
            "precipitacion": np.clip(precip, 0, None),
            "et_pot_mm": np.clip(et_pot, 1, None),
        }
    )


def categorizar_irh(irh: pd.Series) -> pd.Series:
    cortes = sorted(IRH_THRESHOLDS.values())
    bins = [-0.001] + cortes + [1.001]
    labels = ["muy_baja", "baja", "moderada", "alta", "muy_alta"][: len(bins) - 1]
    return pd.cut(irh, bins=bins, labels=labels, include_lowest=True)


def main() -> None:
    df = datos_paramos_sinteticos()
    val = validate(df, date_col="fecha", linea_tematica="paramos")
    print(
        f"[1/3] Validación paramos: issues={val.has_issues()}, "
        f"violaciones de rango en {len(val.range_violations)} columnas."
    )

    df["irh"] = (df["precipitacion"] / (df["precipitacion"] + df["et_pot_mm"])).clip(0, 1)
    df["categoria_irh"] = categorizar_irh(df["irh"])
    print("[2/3] Distribución IRH:")
    print(df["categoria_irh"].value_counts().to_string())

    df["gradiente_caldas_lang"] = df["precipitacion"] / df["et_pot_mm"]
    print(
        f"[3/3] Caldas-Lang medio: {df['gradiente_caldas_lang'].mean():.2f} "
        f"(>2 = superhúmedo, 1-2 = húmedo, <1 = semiárido)"
    )

    out = Path("data/output/examples") / "paramos_irh.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nResultados en: {out}")


if __name__ == "__main__":
    main()
