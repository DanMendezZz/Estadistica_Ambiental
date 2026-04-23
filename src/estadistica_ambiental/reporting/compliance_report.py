"""Reporte HTML de cumplimiento normativo ambiental colombiano.

Genera un documento HTML que muestra, por variable, el porcentaje de
excedencias respecto a las normas colombianas relevantes (Res. 2254/2017,
Res. 2115/2007, Res. 631/2015, IUA, ICA, etc.).

Uso típico:
    from estadistica_ambiental.reporting.compliance_report import compliance_report

    compliance_report(
        df,
        variables=["pm25", "od", "dbo5"],
        date_col="fecha",
        linea_tematica="calidad_aire",
        output="data/output/reports/cumplimiento_aire.html",
    )
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from estadistica_ambiental.config import (
    DOCS_FUENTES,
)
from estadistica_ambiental.inference.intervals import exceedance_probability, exceedance_report

logger = logging.getLogger(__name__)


def compliance_report(
    df: pd.DataFrame,
    variables: List[str],
    date_col: str = "fecha",
    linea_tematica: Optional[str] = None,
    estacion_col: Optional[str] = None,
    output: str = "data/output/reports/compliance_report.html",
    title: Optional[str] = None,
    custom_thresholds: Optional[Dict[str, float]] = None,
) -> Path:
    """Genera reporte HTML de cumplimiento normativo ambiental colombiano.

    Compara cada variable del DataFrame contra todas las normas colombianas
    registradas para esa variable y produce un HTML con:
    - Semáforo de cumplimiento global
    - Tabla de excedencias por variable y norma
    - Serie temporal con excedencias resaltadas por variable
    - Contexto de la línea temática (ficha de dominio)

    Args:
        df: DataFrame con series temporales ambientales.
        variables: Lista de columnas a evaluar (ej. ['pm25', 'od', 'dbo5']).
        date_col: Columna de fechas.
        linea_tematica: Nombre de la línea temática para agregar contexto
            ('calidad_aire', 'recurso_hidrico', 'oferta_hidrica', etc.).
        estacion_col: Columna de estación para reportar en el encabezado.
        output: Ruta del HTML de salida.
        title: Título del reporte (default: auto-generado).
        custom_thresholds: Umbrales adicionales {variable: umbral} no incluidos
            en las normas estándar.

    Returns:
        Path al archivo HTML generado.
    """
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        linea_str = linea_tematica or "General"
        title = f"Cumplimiento Normativo — {linea_str.replace('_', ' ').title()}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_registros = len(df)
    fecha_ini = str(pd.to_datetime(df[date_col], errors="coerce").min().date()) if date_col in df.columns else "—"
    fecha_fin = str(pd.to_datetime(df[date_col], errors="coerce").max().date()) if date_col in df.columns else "—"
    estacion_info = df[estacion_col].iloc[0] if estacion_col and estacion_col in df.columns else "—"

    # ---- Construir secciones ----
    all_exceedance_dfs: Dict[str, pd.DataFrame] = {}
    for var in variables:
        if var not in df.columns:
            logger.warning("Variable '%s' no encontrada en el DataFrame.", var)
            continue
        rep = exceedance_report(df[var], variable=var)
        # Agregar umbrales personalizados si los hay
        if custom_thresholds and var in custom_thresholds:
            umbral = custom_thresholds[var]
            exc = exceedance_probability(df[var], threshold=umbral)
            custom_row = pd.DataFrame([{
                "norma": "Umbral personalizado",
                "umbral": umbral,
                "tipo": "máximo",
                "n_exceedances": exc["n_exceedances"],
                "pct_exceed": exc["pct_exceed"],
                "cumple": exc["n_exceedances"] == 0,
                "return_period_days": exc["return_period_days"],
            }])
            rep = pd.concat([rep, custom_row], ignore_index=True)
        all_exceedance_dfs[var] = rep

    body = "\n".join([
        _section_meta(n_registros, fecha_ini, fecha_fin, estacion_info, linea_tematica),
        _section_semaforo(all_exceedance_dfs),
        _section_tabla_exceedances(all_exceedance_dfs),
        _section_series(df, variables, date_col, all_exceedance_dfs),
        _section_ficha_dominio(linea_tematica),
    ])

    content = _TEMPLATE.format(title=html.escape(title), body=body, generated=now)
    out_path.write_text(content, encoding="utf-8")
    logger.info("Reporte de cumplimiento guardado en: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Secciones del reporte
# ---------------------------------------------------------------------------

def _section_meta(n_registros, fecha_ini, fecha_fin, estacion, linea):
    linea_str = linea.replace("_", " ").title() if linea else "General"
    return f"""<section class="meta">
    <div class="meta-grid">
      <div><span class="label">Línea temática</span><span class="value">{html.escape(linea_str)}</span></div>
      <div><span class="label">Estación</span><span class="value">{html.escape(str(estacion))}</span></div>
      <div><span class="label">Período</span><span class="value">{fecha_ini} → {fecha_fin}</span></div>
      <div><span class="label">N registros</span><span class="value">{n_registros:,}</span></div>
    </div>
    </section>"""


def _section_semaforo(all_dfs: Dict[str, pd.DataFrame]) -> str:
    if not all_dfs:
        return "<section><p>Sin variables con normas colombianas registradas.</p></section>"

    cards = ""
    for var, rep in all_dfs.items():
        if rep.empty:
            color, estado, pct = "gray", "Sin norma", "—"
        else:
            max_exc = rep["pct_exceed"].max()
            if max_exc == 0:
                color, estado = "green", "CUMPLE"
            elif max_exc <= 10:
                color, estado = "yellow", "ALERTA"
            else:
                color, estado = "red", "INCUMPLE"
            pct = f"{max_exc:.1f}%"

        normas_count = len(rep)
        cumple_count = int(rep["cumple"].sum()) if not rep.empty else 0
        cards += f"""
        <div class="semaforo-card {color}">
          <div class="var-name">{html.escape(var.upper())}</div>
          <div class="estado">{estado}</div>
          <div class="detalle">Máx. excedencia: {pct}</div>
          <div class="detalle">{cumple_count}/{normas_count} normas OK</div>
        </div>"""

    return f"""<section>
    <h2>Semáforo de cumplimiento</h2>
    <div class="semaforo-grid">{cards}</div>
    </section>"""


def _section_tabla_exceedances(all_dfs: Dict[str, pd.DataFrame]) -> str:
    if not all_dfs or all(rep.empty for rep in all_dfs.values()):
        return ""

    rows = ""
    for var, rep in all_dfs.items():
        if rep.empty:
            rows += f"<tr><td><strong>{html.escape(var)}</strong></td>" \
                    f"<td colspan='5'>Sin norma colombiana registrada</td></tr>"
            continue
        for _, row in rep.iterrows():
            cumple_icon = "✅" if row["cumple"] else "❌"
            ret = str(row["return_period_days"]) if row["return_period_days"] else "—"
            bg = "" if row["cumple"] else " class='exceed'"
            rows += (
                f"<tr{bg}>"
                f"<td><strong>{html.escape(var)}</strong></td>"
                f"<td>{html.escape(str(row['norma']))}</td>"
                f"<td>{row['tipo']}</td>"
                f"<td>{row['umbral']}</td>"
                f"<td>{row['n_exceedances']} ({row['pct_exceed']:.1f}%)</td>"
                f"<td>{cumple_icon}</td>"
                f"<td>{ret}</td>"
                f"</tr>"
            )

    return f"""<section>
    <h2>Detalle de excedencias por norma</h2>
    <table>
      <thead>
        <tr>
          <th>Variable</th><th>Norma</th><th>Tipo</th><th>Umbral</th>
          <th>Excedencias (n / %)</th><th>Cumple</th><th>Período retorno (días)</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    </section>"""


def _section_series(
    df: pd.DataFrame,
    variables: List[str],
    date_col: str,
    all_dfs: Dict[str, pd.DataFrame],
) -> str:
    if date_col not in df.columns:
        return ""

    charts = ""
    for var in variables:
        if var not in df.columns:
            continue
        rep = all_dfs.get(var, pd.DataFrame())

        # Primer umbral máximo disponible (para resaltar en el gráfico)
        threshold_line = ""
        threshold_label = ""
        if not rep.empty:
            max_rows = rep[rep["tipo"] == "máximo"].sort_values("umbral")
            if not max_rows.empty:
                row0 = max_rows.iloc[0]
                threshold_line = str(row0["umbral"])
                threshold_label = str(row0["norma"])

        series = df[[date_col, var]].dropna()
        labels = series[date_col].astype(str).tolist()
        values = [round(float(v), 3) for v in series[var]]

        canvas_id = f"chart_{var}"
        annotation_js = ""
        if threshold_line:
            annotation_js = f"""
            annotation: {{
              annotations: {{
                norma: {{
                  type: 'line', yMin: {threshold_line}, yMax: {threshold_line},
                  borderColor: '#e74c3c', borderWidth: 2, borderDash: [6,3],
                  label: {{ content: '{html.escape(threshold_label)}',
                            display: true, position: 'start' }}
                }}
              }}
            }},"""

        charts += f"""
        <div class="chart-wrap">
          <h3>{html.escape(var.upper())}</h3>
          <canvas id="{canvas_id}" style="max-height:220px"></canvas>
          <script>
          (function(){{
            var labels = {labels};
            var data   = {values};
            new Chart(document.getElementById('{canvas_id}'), {{
              type: 'line',
              data: {{
                labels: labels,
                datasets: [{{
                  label: '{html.escape(var)}',
                  data: data,
                  borderColor: '#1a5276',
                  backgroundColor: 'rgba(26,82,118,0.08)',
                  borderWidth: 1.5,
                  pointRadius: 1,
                  fill: true
                }}]
              }},
              options: {{
                responsive: true,
                plugins: {{
                  legend: {{ display: false }},
                  {annotation_js}
                }},
                scales: {{ y: {{ beginAtZero: false }} }}
              }}
            }});
          }})();
          </script>
        </div>"""

    return f"""<section>
    <h2>Series temporales con umbrales normativos</h2>
    <p style="color:#666;font-size:.85rem">
      Línea roja punteada = norma colombiana más estricta aplicable.
    </p>
    {charts}
    </section>"""


def _section_ficha_dominio(linea_tematica: Optional[str]) -> str:
    if not linea_tematica:
        return ""
    ficha = DOCS_FUENTES / f"{linea_tematica}.md"
    if not ficha.exists():
        return ""
    # Extraer solo el resumen ejecutivo (hasta la primera sección ##)
    text = ficha.read_text(encoding="utf-8")
    resumen = ""
    in_resumen = False
    for line in text.splitlines():
        if line.startswith("## Resumen"):
            in_resumen = True
            continue
        if in_resumen:
            if line.startswith("##"):
                break
            resumen += html.escape(line) + "<br>"

    if not resumen.strip():
        return ""
    return f"""<section>
    <h2>Contexto de dominio — {html.escape(linea_tematica.replace('_', ' ').title())}</h2>
    <p style="font-size:.88rem;color:#444;line-height:1.6">{resumen}</p>
    <p style="font-size:.8rem;color:#888">
      Fuente: <code>docs/fuentes/{linea_tematica}.md</code>
    </p>
    </section>"""


# ---------------------------------------------------------------------------
# Template HTML
# ---------------------------------------------------------------------------

_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js"></script>
<style>
  body  {{ font-family: -apple-system, sans-serif; margin: 0; padding: 24px 40px;
          background: #f0f2f5; color: #212529; }}
  h1    {{ color: #1a5276; border-bottom: 3px solid #1a5276; padding-bottom: 8px; }}
  h2    {{ color: #1a5276; margin-top: 0; font-size: 1.05rem; }}
  h3    {{ color: #555; font-size: .95rem; margin: 12px 0 4px; }}
  section {{ background: white; border-radius: 8px; padding: 20px 24px;
            margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}

  /* Meta */
  .meta-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .label {{ display: block; font-size: .75rem; color: #888; text-transform: uppercase;
           letter-spacing: .05em; }}
  .value {{ font-size: 1rem; font-weight: 600; color: #212529; }}

  /* Semáforo */
  .semaforo-grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
  .semaforo-card {{ border-radius: 8px; padding: 14px 20px; min-width: 140px;
                   text-align: center; color: white; }}
  .semaforo-card.green  {{ background: #1e8449; }}
  .semaforo-card.yellow {{ background: #d68910; }}
  .semaforo-card.red    {{ background: #c0392b; }}
  .semaforo-card.gray   {{ background: #7f8c8d; }}
  .var-name {{ font-size: 1.1rem; font-weight: 700; }}
  .estado   {{ font-size: .85rem; font-weight: 600; margin: 4px 0; }}
  .detalle  {{ font-size: .75rem; opacity: .9; }}

  /* Tabla */
  table {{ border-collapse: collapse; width: 100%; font-size: .85rem; margin-top: 8px; }}
  th    {{ background: #1a5276; color: white; padding: 8px 12px; text-align: left; }}
  td    {{ padding: 6px 12px; border-bottom: 1px solid #dee2e6; }}
  tr.exceed td {{ background: #fdecea; }}
  tr:hover td  {{ background: #eaf4fb; }}

  /* Charts */
  .chart-wrap {{ margin-top: 16px; padding-top: 16px;
                border-top: 1px solid #eee; }}
  .chart-wrap:first-child {{ border-top: none; margin-top: 0; padding-top: 0; }}

  footer {{ text-align: center; color: #999; font-size: .8rem; margin-top: 24px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<footer>estadistica-ambiental · Cumplimiento Normativo Ambiental Colombia · {generated}</footer>
</body>
</html>"""
