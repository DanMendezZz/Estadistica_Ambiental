"""Oferta hídrica — caudal mensual: NSE/KGE contra una predicción ingenua,
descomposición y prueba de estacionariedad.

NSE y KGE son las métricas primarias en hidrología (ADR — métricas).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.evaluation.metrics import evaluate
from estadistica_ambiental.inference.stationarity import adf_test


def caudal_sintetico(n_meses: int = 240, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2005-01-01", periods=n_meses, freq="MS")
    estacional = 60 + 30 * np.sin(2 * np.pi * np.arange(n_meses) / 12)
    enso = 15 * np.sin(2 * np.pi * np.arange(n_meses) / 60)
    ruido = rng.normal(0, 8, n_meses)
    caudal = np.clip(estacional + enso + ruido, 1, None)
    return pd.DataFrame({"fecha": fechas, "caudal": caudal})


def main() -> None:
    df = caudal_sintetico()
    print(f"[1/3] Caudal mensual sintético: {len(df)} meses.")

    res_adf = adf_test(df["caudal"])
    pval = res_adf.get("pval", res_adf.get("p_value", 1.0))
    veredicto = "estacionaria" if pval < 0.05 else "no estacionaria"
    print(f"[2/3] ADF p={pval:.4f} -> {veredicto}")

    pred = df["caudal"].shift(12).bfill()
    metrics = evaluate(df["caudal"].values, pred.values, domain="hydrology")
    print("[3/3] Métricas vs. naive estacional (lag-12):")
    for k, v in metrics.items():
        print(f"   {k:>6} = {v:.3f}")

    out = Path("data/output/examples") / "caudal_metrics.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(metrics).to_csv(out, header=["valor"])
    print(f"\nMétricas guardadas en: {out}")


if __name__ == "__main__":
    main()
