"""Reporte HTML automático de pronósticos con comparación de modelos."""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def forecast_report(
    y_true: pd.Series,
    predictions: Dict[str, np.ndarray],
    metrics: Dict[str, dict],
    output: str = "reports/forecast_report.html",
    title: str = "Reporte de Pronóstico",
    variable_name: str = "variable",
    unit: str = "",
) -> Path:
    """Genera reporte HTML con series reales vs. pronósticos y tabla de métricas.

    Args:
        y_true: Serie real (valores observados en el período de test).
        predictions: {model_name: array_de_predicciones}.
        metrics: {model_name: metrics_dict} — salida de evaluate().
        output: Ruta del HTML de salida.
        title: Título del reporte.
        variable_name: Nombre de la variable pronosticada.
        unit: Unidad de medida (e.g. 'µg/m³').
    """
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = _build_body(y_true, predictions, metrics, variable_name, unit)
    content = _TEMPLATE.format(title=html.escape(title), body=body, generated=now)
    out_path.write_text(content, encoding="utf-8")
    logger.info("Reporte de pronóstico guardado en: %s", out_path)
    return out_path


def _build_body(y_true, predictions, metrics, variable_name, unit):
    sections = [
        _section_summary(metrics),
        _section_metrics_table(metrics),
        _section_series(y_true, predictions, variable_name, unit),
    ]
    return "\n".join(sections)


def _section_summary(metrics: Dict[str, dict]) -> str:
    if not metrics:
        return ""
    best_model = min(metrics, key=lambda m: metrics[m].get("rmse", float("inf")))
    best_rmse  = metrics[best_model].get("rmse", "N/A")
    return f"""<section>
    <h2>Resumen</h2>
    <p>Mejor modelo según RMSE: <strong>{html.escape(best_model)}</strong>
       (RMSE = {best_rmse})</p>
    <p>Modelos comparados: {len(metrics)}</p>
    </section>"""


def _section_metrics_table(metrics: Dict[str, dict]) -> str:
    if not metrics:
        return ""
    all_keys = sorted({k for m in metrics.values() for k in m})
    header = "<th>Modelo</th>" + "".join(f"<th>{k}</th>" for k in all_keys)
    best_rmse = min(m.get("rmse", float("inf")) for m in metrics.values())

    rows = ""
    for name, m in sorted(metrics.items(), key=lambda x: x[1].get("rmse", float("inf"))):
        is_best = m.get("rmse") == best_rmse
        cls = " class='best'" if is_best else ""
        cells = "".join(f"<td>{m.get(k, '—')}</td>" for k in all_keys)
        rows += f"<tr{cls}><td><strong>{html.escape(name)}</strong></td>{cells}</tr>"

    return f"""<section>
    <h2>Métricas por modelo</h2>
    <table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>
    </section>"""


def _section_series(y_true, predictions, variable_name, unit):
    labels = [str(i) for i in range(len(y_true))]
    actual_vals = [round(float(v), 3) for v in y_true.values]

    series_js = f"labels: {labels},\ndatasets: [\n"
    series_js += (
        f"{{label: 'Real', data: {actual_vals}, "
        "borderColor: '#1a5276', backgroundColor: 'transparent', "
        "borderWidth: 2, pointRadius: 2}},\n"
    )
    colors = ["#e74c3c", "#27ae60", "#f39c12", "#8e44ad", "#16a085"]
    for i, (name, preds) in enumerate(predictions.items()):
        vals = [round(float(v), 3) for v in preds]
        color = colors[i % len(colors)]
        series_js += (
            f"{{label: '{html.escape(name)}', data: {vals}, "
            f"borderColor: '{color}', backgroundColor: 'transparent', "
            "borderWidth: 1.5, borderDash: [4,2], pointRadius: 1}},\n"
        )
    series_js += "]"

    y_label = f"{variable_name} ({unit})" if unit else variable_name
    return f"""<section>
    <h2>Serie real vs. pronósticos</h2>
    <canvas id="forecastChart" style="max-height:350px"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
    <script>
    new Chart(document.getElementById('forecastChart'), {{
      type: 'line',
      data: {{ {series_js} }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'top' }} }},
        scales: {{ y: {{ title: {{ display: true, text: '{html.escape(y_label)}' }} }} }}
      }}
    }});
    </script>
    </section>"""


_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body  {{ font-family: -apple-system, sans-serif; margin: 0; padding: 24px 40px;
          background: #f8f9fa; color: #212529; }}
  h1    {{ color: #1a5276; border-bottom: 3px solid #1a5276; padding-bottom: 8px; }}
  h2    {{ color: #1a5276; margin-top: 28px; font-size: 1.05rem; }}
  section {{ background: white; border-radius: 8px; padding: 20px 24px;
            margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  table {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
  th    {{ background: #1a5276; color: white; padding: 7px 12px; text-align: left; }}
  td    {{ padding: 6px 12px; border-bottom: 1px solid #dee2e6; }}
  tr.best td {{ background: #d5f5e3; }}
  footer {{ text-align: center; color: #999; font-size: .8rem; margin-top: 24px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<footer>estadistica-ambiental · {generated}</footer>
</body>
</html>"""
