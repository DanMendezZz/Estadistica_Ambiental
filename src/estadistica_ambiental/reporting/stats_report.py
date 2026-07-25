"""Reporte HTML de estadística descriptiva e inferencial."""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from estadistica_ambiental.descriptive.univariate import summarize
from estadistica_ambiental.inference.stationarity import stationarity_report
from estadistica_ambiental.inference.trend import mann_kendall

logger = logging.getLogger(__name__)


def stats_report(
    df: pd.DataFrame,
    output: str = "reports/stats_report.html",
    title: str = "Reporte Estadístico",
    date_col: Optional[str] = None,
    value_cols: Optional[list] = None,
) -> Path:
    """Genera reporte HTML con estadística descriptiva + inferencial.

    Incluye: resumen univariado, estacionariedad y tendencia por columna numérica.
    """
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    num_cols = value_cols or df.select_dtypes(include="number").columns.tolist()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections = [_section_descriptive(df, num_cols)]

    if date_col and date_col in df.columns:
        sections.append(_section_stationarity(df, date_col, num_cols))
        sections.append(_section_trend(df, date_col, num_cols))

    body = "\n".join(sections)
    content = _TEMPLATE.format(title=html.escape(title), body=body, generated=now)
    out_path.write_text(content, encoding="utf-8")
    logger.info("Reporte estadístico guardado en: %s", out_path)
    return out_path


def _section_descriptive(df: pd.DataFrame, cols: list) -> str:
    stats = summarize(df, cols=cols)
    return f"<section><h2>Estadística descriptiva</h2>{_df_html(stats)}</section>"


def _section_stationarity(df: pd.DataFrame, date_col: str, cols: list) -> str:
    rows = []
    for col in cols:
        s = df.set_index(date_col)[col].dropna()
        if len(s) < 20:
            continue
        try:
            rep = stationarity_report(s)
            for _, row in rep.iterrows():
                rows.append({"variable": col, **row.to_dict()})
        except Exception:
            continue
    if not rows:
        return ""
    result_df = pd.DataFrame(rows)
    return f"<section><h2>Estacionariedad (ADF + KPSS)</h2>{_df_html(result_df)}</section>"


def _section_trend(df: pd.DataFrame, date_col: str, cols: list) -> str:
    rows = []
    for col in cols:
        s = df.set_index(date_col)[col].dropna()
        if len(s) < 10:
            continue
        try:
            mk = mann_kendall(s)
            rows.append(
                {
                    "variable": col,
                    "tendencia": mk["trend"],
                    "significativo": mk["h"],
                    "p-valor": mk["pval"],
                    "tau": mk["tau"],
                    "Sen slope": mk["slope"],
                }
            )
        except Exception:
            continue
    if not rows:
        return ""
    return f"<section><h2>Tendencia (Mann-Kendall + Sen's slope)</h2>{_df_html(pd.DataFrame(rows))}</section>"


def _df_html(df: pd.DataFrame) -> str:
    header = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
        for _, row in df.iterrows()
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"


_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><title>{title}</title>
<style>
  body  {{ font-family:-apple-system,sans-serif; margin:0; padding:24px 40px;
          background:#f8f9fa; color:#212529; }}
  h1    {{ color:#1a5276; border-bottom:3px solid #1a5276; padding-bottom:8px; }}
  h2    {{ color:#1a5276; margin-top:28px; font-size:1.05rem; }}
  section {{ background:white; border-radius:8px; padding:20px 24px;
            margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  table {{ border-collapse:collapse; width:100%; font-size:.86rem; }}
  th    {{ background:#1a5276; color:white; padding:6px 10px; text-align:left; }}
  td    {{ padding:5px 10px; border-bottom:1px solid #dee2e6; }}
  footer{{ text-align:center; color:#999; font-size:.8rem; margin-top:24px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<footer>estadistica-ambiental · {generated}</footer>
</body>
</html>"""
