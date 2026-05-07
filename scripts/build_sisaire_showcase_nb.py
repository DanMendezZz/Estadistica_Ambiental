"""Genera el notebook showcase end-to-end con SISAIRE/CAR real (load_sisaire_local).

Si SISAIRE_LOCAL_DIR no está configurada, el notebook genera datos sintéticos
para que pueda ejecutarse de forma reproducible sin tocar nada externo.
"""

import json
from pathlib import Path

OUT = Path(
    "D:/Dan/98. IA/Estadistica_Ambiental/notebooks/showcases/calidad_aire_sisaire_real.ipynb"
)


def md(src: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": src,
        "id": f"m{abs(hash(src[:20])):08x}",
    }


def code(src: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": src,
        "outputs": [],
        "execution_count": None,
        "id": f"c{abs(hash(src[:20])):08x}",
    }


cells = [
    md(
        "# Showcase — Calidad del aire con datos SISAIRE/CAR reales\n"
        "\n"
        "**Objetivo:** demostrar el ciclo estadístico completo (carga → calidad → "
        "descriptiva → cumplimiento → tendencia → pronóstico → reporte) "
        "consumiendo datos reales de la **Red de Monitoreo de Calidad del Aire** de la CAR "
        "vía `load_sisaire_local()`, sin duplicar archivos al repo.\n"
        "\n"
        "**Datos:** archivos `CAR_<año>.csv` descargados manualmente del portal SISAIRE/IDEAM, "
        "almacenados en una carpeta externa apuntada por la variable de entorno "
        "`SISAIRE_LOCAL_DIR`. Si la variable no está configurada, el notebook cae a un "
        "dataset sintético equivalente (mismo esquema) para que sea reproducible.\n"
        "\n"
        "**Contexto de dominio:** ver `docs/fuentes/calidad_aire.md` (ICA, normas, "
        "buenas prácticas metodológicas, RF/XGBoost como modelo de producción real)."
    ),
    md("## 0. Setup"),
    code(
        "import warnings; warnings.filterwarnings('ignore')\n"
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "\n"
        "from estadistica_ambiental.io.connectors import load_sisaire_local\n"
        "from estadistica_ambiental.io.validators import validate\n"
        "from estadistica_ambiental.eda.quality import assess_quality\n"
        "from estadistica_ambiental.descriptive.univariate import summarize\n"
        "from estadistica_ambiental.inference.intervals import exceedance_report\n"
        "from estadistica_ambiental.inference.trend import mann_kendall\n"
        "from estadistica_ambiental.reporting.compliance_report import compliance_report\n"
        "\n"
        "OUT_DIR = Path('data/output/showcase_sisaire')\n"
        "OUT_DIR.mkdir(parents=True, exist_ok=True)\n"
        "print('Setup OK ->', OUT_DIR)"
    ),
    md(
        "## 1. Carga — datos reales con fallback sintético\n"
        "\n"
        "`load_sisaire_local(anios=, parametro=)` lee los `CAR_<año>.csv` de la carpeta "
        "indicada por `SISAIRE_LOCAL_DIR`. Si no está configurada, lanza `FileNotFoundError`; "
        "en ese caso generamos PM2.5 horario sintético con estacionalidad diaria + ruido."
    ),
    code(
        "try:\n"
        "    df = load_sisaire_local(anios=2024, parametro='pm25')\n"
        "    fuente = 'SISAIRE/CAR real'\n"
        "except FileNotFoundError as e:\n"
        "    print(f'[fallback] {e}')\n"
        "    rng = np.random.default_rng(42)\n"
        "    n = 24 * 366\n"
        "    fechas = pd.date_range('2024-01-01', periods=n, freq='h')\n"
        "    diurno = 8 * np.sin(2 * np.pi * np.arange(n) / 24)\n"
        "    estacional = 5 * np.sin(2 * np.pi * np.arange(n) / (24 * 365))\n"
        "    pm25 = np.clip(22 + diurno + estacional + rng.normal(0, 6, n), 0, None)\n"
        "    df = pd.DataFrame({'fecha': fechas, 'estacion': 'sintetica', 'pm25': pm25})\n"
        "    fuente = 'sintetico (fallback)'\n"
        "\n"
        "print(f'Fuente: {fuente}')\n"
        "print(f'Registros: {len(df):,} | Estaciones: {df.estacion.nunique()} | '\n"
        "      f'Periodo: {df.fecha.min()} -> {df.fecha.max()}')\n"
        "df.head()"
    ),
    md(
        "## 2. Calidad y validación\n"
        "\n"
        "- `validate(df, linea_tematica='calidad_aire')` aplica los rangos físicos del "
        "dominio (ADR-006). NO elimina valores fuera de rango (ADR-002): los picos "
        "ambientales son señal real.\n"
        "- `assess_quality(df, date_col='fecha')` reporta faltantes, gaps temporales, "
        "outliers estadísticos y congelamiento de sensor."
    ),
    code(
        "val = validate(df, date_col='fecha', linea_tematica='calidad_aire')\n"
        "print(f'Issues detectados: {val.has_issues()}')\n"
        "print(f'Violaciones de rango (cols): {list(val.range_violations.keys())}')\n"
        "print(f'Faltantes (>0): {val.missing}')\n"
    ),
    code(
        "calidad = assess_quality(df, date_col='fecha')\n"
        "print(calidad.summary())"
    ),
    md(
        "## 3. Resampling a diario\n"
        "\n"
        "La normativa colombiana (Res. 2254/2017) y las guías OMS 2021 evalúan promedios "
        "**diarios** y **anuales**. Pasamos de horario a diario por estación."
    ),
    code(
        "daily = (\n"
        "    df.assign(dia=df['fecha'].dt.floor('D'))\n"
        "      .groupby(['estacion', 'dia'], as_index=False)['pm25']\n"
        "      .mean()\n"
        "      .rename(columns={'dia': 'fecha'})\n"
        ")\n"
        "print(f'Promedios diarios: {len(daily):,} filas')\n"
        "daily.head()"
    ),
    md("## 4. Descriptiva univariada"),
    code(
        "desc = summarize(daily[['pm25']])\n"
        "desc.round(2)"
    ),
    code(
        "fig, ax = plt.subplots(figsize=(11, 3.5))\n"
        "for est, sub in daily.groupby('estacion'):\n"
        "    ax.plot(sub['fecha'], sub['pm25'], lw=0.8, alpha=0.7, label=str(est))\n"
        "ax.axhline(25, ls='--', c='orange', label='Norma CO anual (25 ug/m3)')\n"
        "ax.axhline(15, ls='--', c='red', label='OMS 24h (15 ug/m3)')\n"
        "ax.set_title('PM2.5 diario por estacion')\n"
        "ax.set_ylabel('ug/m3'); ax.legend(loc='upper right', ncol=2, fontsize=8)\n"
        "plt.tight_layout()\n"
        "fig.savefig(OUT_DIR / 'pm25_diario.png', dpi=120)\n"
        "plt.show()"
    ),
    md(
        "## 5. Excedencias normativas\n"
        "\n"
        "`exceedance_report(serie, variable='pm25')` cruza la serie contra:\n"
        "- **Res. 2254/2017** (Colombia): 37 µg/m³ (24h), 25 µg/m³ (anual).\n"
        "- **Guías OMS 2021**: 15 µg/m³ (24h), 5 µg/m³ (anual)."
    ),
    code(
        "rep = exceedance_report(daily['pm25'], variable='pm25')\n"
        "rep"
    ),
    md(
        "## 6. Tendencia — Mann-Kendall + Sen slope\n"
        "\n"
        "Test no paramétrico, robusto a estacionalidad y distribuciones no normales. "
        "Estándar en hidrología y calidad del aire para series largas."
    ),
    code(
        "serie_global = daily.groupby('fecha')['pm25'].mean()\n"
        "mk = mann_kendall(serie_global)\n"
        "for k in ('trend', 'pval', 'tau', 'slope'):\n"
        "    print(f'{k:>6} = {mk[k]}')\n"
        "sig = mk['pval'] < mk['alpha']\n"
        "print(f\"\\n=> Tendencia {'SIGNIFICATIVA' if sig else 'no significativa'}: {mk['trend']}\")"
    ),
    md(
        "## 7. Pronóstico estacional ingenuo\n"
        "\n"
        "Para no introducir aquí dependencias pesadas (statsmodels SARIMA), comparamos "
        "una predicción **naive estacional (lag-7 días)** contra los últimos 30 días observados. "
        "Para SARIMA/XGBoost real ver el notebook `notebooks/lineas_tematicas/.../calidad_aire.ipynb`."
    ),
    code(
        "from estadistica_ambiental.evaluation.metrics import evaluate\n"
        "\n"
        "serie = serie_global.dropna()\n"
        "h = 30\n"
        "y_true = serie.iloc[-h:].values\n"
        "y_pred = serie.shift(7).iloc[-h:].values  # naive lag-7\n"
        "\n"
        "metrics = evaluate(y_true, y_pred, domain='air_quality', pollutant='pm25')\n"
        "for k, v in metrics.items():\n"
        "    print(f'{k:>14} = {v:.3f}')"
    ),
    md(
        "## 8. Reporte HTML de cumplimiento\n"
        "\n"
        "`compliance_report` genera un HTML autoexplicativo con la tabla de excedencias "
        "y los gráficos clave — útil para entregar a un decisor sin necesidad de abrir "
        "el notebook."
    ),
    code(
        "html_path = OUT_DIR / 'cumplimiento_pm25.html'\n"
        "compliance_report(\n"
        "    daily,\n"
        "    variables=['pm25'],\n"
        "    linea_tematica='calidad_aire',\n"
        "    output=str(html_path),\n"
        ")\n"
        "print(f'Reporte: {html_path}')"
    ),
    md(
        "---\n"
        "## Cierre\n"
        "\n"
        "Este notebook se puede ejecutar de extremo a extremo con dos modos:\n"
        "\n"
        "- **Modo real:** `setx SISAIRE_LOCAL_DIR \"<carpeta con CAR_*.csv>\"` y reejecutar.\n"
        "- **Modo demo:** sin variable de entorno, usa datos sintéticos equivalentes.\n"
        "\n"
        "Las salidas (PNG, HTML) quedan en `data/output/showcase_sisaire/`. Para producir "
        "un dashboard real consumiendo estos resultados, crear un repo satélite que importe "
        "`estadistica_ambiental` como dependencia (ver README, sección *Consumir desde otro proyecto*)."
    ),
]


def main() -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Notebook generado: {OUT}")


if __name__ == "__main__":
    main()
