"""Quickstart: cargar → validar → describir → reportar.

Demuestra el ciclo mínimo viable de la librería con datos sintéticos para
que sea ejecutable sin dependencias externas. Reemplaza la generación
sintética por tu carga real (load_sisaire_local, load_openaq, etc.).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from estadistica_ambiental.descriptive.univariate import summarize
from estadistica_ambiental.eda.quality import assess_quality
from estadistica_ambiental.io.validators import validate


def datos_sinteticos(n: int = 720, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2024-01-01", periods=n, freq="h")
    base = 25 + 10 * np.sin(2 * np.pi * np.arange(n) / 24)
    ruido = rng.normal(0, 4, size=n)
    pm25 = np.clip(base + ruido, 0, None)
    return pd.DataFrame({"fecha": fechas, "estacion": "demo", "pm25": pm25})


def main() -> None:
    df = datos_sinteticos()
    print(f"[1/4] Cargados {len(df)} registros de PM2.5 sintético.")

    val = validate(df, date_col="fecha", linea_tematica="calidad_aire")
    n_viol = sum(v.get("n_violations", 0) for v in val.range_violations.values())
    print(
        f"[2/4] Validación: {len(val.range_violations)} columnas con violaciones de rango, "
        f"{n_viol} valores fuera de rango (no se eliminan; ADR-002)."
    )

    calidad = assess_quality(df, date_col="fecha")
    n_miss_cols = sum(1 for m in calidad.missing.values() if m.n_missing > 0)
    print(f"[3/4] Calidad: {n_miss_cols} cols con faltantes, {len(calidad.outliers)} con outliers.")

    desc = summarize(df[["pm25"]])
    print("[4/4] Resumen descriptivo:")
    print(desc.round(2).to_string(index=False))

    out = Path("data/output/examples") / "quickstart_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    desc.to_csv(out, index=False)
    print(f"\nSalida guardada en: {out}")


if __name__ == "__main__":
    main()
