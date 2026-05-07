"""Cambio climático — tendencias en CO2 atmosférico (Mauna Loa-like).

Demuestra:
- Mann-Kendall + Sen slope (no paramétricos, robustos a estacionalidad).
- Clasificación de tendencia significativa según p<alpha.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.inference.trend import mann_kendall


def co2_sintetico(n_meses: int = 360, seed: int = 13) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("1995-01-01", periods=n_meses, freq="MS")
    tendencia = 360 + 0.18 * np.arange(n_meses)
    estacional = 3 * np.sin(2 * np.pi * np.arange(n_meses) / 12)
    ruido = rng.normal(0, 0.6, n_meses)
    return pd.DataFrame({"fecha": fechas, "co2_ppm": tendencia + estacional + ruido})


def main() -> None:
    df = co2_sintetico()
    print(
        f"[1/2] Serie CO2 mensual sintética: {df['fecha'].min().date()} -> {df['fecha'].max().date()}"
    )

    mk = mann_kendall(df["co2_ppm"])
    print("[2/2] Mann-Kendall:")
    for k in ("trend", "pval", "tau", "slope"):
        if k in mk:
            print(f"   {k:>6} = {mk[k]}")

    sig = mk.get("pval", 1.0) < mk.get("alpha", 0.05)
    print(
        f"\n=> Tendencia {'SIGNIFICATIVA' if sig else 'no significativa'} "
        f"(alpha={mk.get('alpha', 0.05)}), direccion: {mk.get('trend', '?')}"
    )
    print(f"   Sen slope ~ {mk['slope']:.3f} ppm/mes  ({mk['slope'] * 12:.2f} ppm/anio)")

    out = Path("data/output/examples") / "co2_mannkendall.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(mk).to_csv(out, header=["valor"])
    print(f"\nResultado en: {out}")


if __name__ == "__main__":
    main()
