"""
Reporte automático de EDA para datasets ambientales.

Genera un HTML autocontenido que integra:
  - Catálogo de variables (variables.py)
  - Análisis de calidad (quality.py)
  - Validación de rangos físicos (validators.py)
  - Estadísticas descriptivas básicas

Integración opcional con ydata-profiling o sweetviz cuando están instalados.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from estadistica_ambiental.eda.quality import QualityReport, assess_quality
from estadistica_ambiental.eda.variables import VariableCatalog, classify
from estadistica_ambiental.io.validators import ValidationReport, validate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def run_eda(
    df: pd.DataFrame,
    output: str = "reports/eda_report.html",
    title: str = "EDA Ambiental",
    date_col: Optional[str] = None,
    use_ydata: bool = True,
    use_sweetviz: bool = False,
) -> Path:
    """Genera el reporte completo de EDA y lo guarda en disco.

    Siempre produce el reporte propio. Si use_ydata=True y ydata-profiling
    está instalado, genera también el reporte completo de ydata en un archivo
    separado (<output>_ydata.html).

    Args:
        df: DataFrame ambiental.
        output: Ruta del HTML de salida.
        title: Título del reporte.
        date_col: Columna de fechas para análisis temporal.
        use_ydata: Intentar generar reporte ydata-profiling si está disponible.
        use_sweetviz: Intentar generar reporte sweetviz si está disponible.

    Returns:
        Path al HTML generado.
    """
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    catalog = classify(df)
    quality = assess_quality(df, date_col=date_col)
    val_report = validate(df, date_col=date_col)

    html_content = _build_html(df, title, catalog, quality, val_report, date_col)
    out_path.write_text(html_content, encoding="utf-8")
    logger.info("Reporte EDA guardado en: %s", out_path)

    if use_ydata:
        _try_ydata(df, out_path)

    if use_sweetviz:
        _try_sweetviz(df, out_path)

    return out_path


# ---------------------------------------------------------------------------
# Construcción del HTML propio
# ---------------------------------------------------------------------------


def _build_html(
    df: pd.DataFrame,
    title: str,
    catalog: VariableCatalog,
    quality: QualityReport,
    val_report: ValidationReport,
    date_col: Optional[str],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections = [
        _section_overview(df, now, date_col),
        _section_catalog(catalog),
        _section_missing(quality),
        _section_temporal(quality),
        _section_outliers(quality),
        _section_freezes(quality),
        _section_range_violations(val_report),
        _section_cross_issues(quality, val_report),
        _section_descriptive(df),
    ]

    body = "\n".join(s for s in sections if s)
    return _HTML_TEMPLATE.format(title=html.escape(title), body=body, generated=now)


# ---------------------------------------------------------------------------
# Secciones del reporte
# ---------------------------------------------------------------------------


def _section_overview(df: pd.DataFrame, now: str, date_col: Optional[str]) -> str:
    rows_info = f"{len(df):,} filas × {len(df.columns)} columnas"
    size_kb = df.memory_usage(deep=True).sum() / 1024
    date_range = ""
    if date_col and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates):
            date_range = f"<br>Período: <b>{dates.min().date()}</b> → <b>{dates.max().date()}</b>"

    cards = f"""
    <div class="cards">
      <div class="card"><span class="num">{len(df):,}</span><br>Filas</div>
      <div class="card"><span class="num">{len(df.columns)}</span><br>Columnas</div>
      <div class="card"><span class="num">{df.isnull().mean().mean() * 100:.1f}%</span><br>Faltantes (prom.)</div>
      <div class="card"><span class="num">{size_kb:.1f} KB</span><br>Memoria</div>
    </div>
    <p>{rows_info}{date_range}</p>"""
    return _wrap_section("Resumen del dataset", cards)


def _section_catalog(catalog: VariableCatalog) -> str:
    cat_df = catalog.to_dataframe()
    return _wrap_section("Catálogo de variables", _df_to_html(cat_df))


def _section_missing(quality: QualityReport) -> str:
    rows = [(n, m) for n, m in quality.missing.items() if m.n_missing > 0]
    if not rows:
        return _wrap_section("Datos faltantes", "<p class='ok'>Sin faltantes.</p>")

    rows_sorted = sorted(rows, key=lambda x: -x[1].pct_missing)
    table_rows = "".join(
        f"<tr class='{'warn' if m.pct_missing > 20 else ''}'>"
        f"<td>{html.escape(n)}</td>"
        f"<td>{m.n_missing}</td>"
        f"<td>{m.pct_missing:.1f}%</td>"
        f"<td>{m.max_consecutive_gap}</td>"
        f"<td>{m.pattern.value}</td>"
        f"</tr>"
        for n, m in rows_sorted
    )
    table = (
        "<table><thead><tr>"
        "<th>Columna</th><th>N faltantes</th><th>%</th>"
        "<th>Gap máx. consec.</th><th>Patrón</th>"
        "</tr></thead><tbody>" + table_rows + "</tbody></table>"
    )
    return _wrap_section("Datos faltantes", table)


def _section_temporal(quality: QualityReport) -> str:
    tg = quality.temporal_gaps
    if not tg:
        return ""
    color = "ok" if tg.completeness_pct >= 99 else "warn"
    content = f"""
    <p>Frecuencia inferida: <b>{tg.inferred_freq or "no inferida"}</b></p>
    <p>Registros esperados: {tg.expected_n:,} | Presentes: {tg.actual_n:,} |
       <span class='{color}'>{tg.completeness_pct:.1f}% completo</span></p>
    <p>Gaps detectados: {tg.n_gaps} | Mayor gap: {tg.max_gap_periods} periodos</p>"""
    return _wrap_section("Completitud temporal", content)


def _section_outliers(quality: QualityReport) -> str:
    if not quality.outliers:
        return _wrap_section("Outliers estadísticos", "<p class='ok'>Sin outliers detectados.</p>")
    table_rows = "".join(
        f"<tr><td>{html.escape(col)}</td>"
        f"<td>{o.n_iqr} ({o.pct_iqr:.1f}%)</td>"
        f"<td>{o.n_zscore} ({o.pct_zscore:.1f}%)</td>"
        f"<td>{', '.join(f'{v:.2f}' for v in o.worst_values[:3])}</td></tr>"
        for col, o in quality.outliers.items()
        if o.n_iqr > 0 or o.n_zscore > 0
    )
    if not table_rows:
        return _wrap_section("Outliers estadísticos", "<p class='ok'>Sin outliers detectados.</p>")
    table = (
        "<table><thead><tr><th>Columna</th><th>IQR (1.5×)</th>"
        "<th>Z-score (|z|>3)</th><th>Peores valores</th></tr></thead>"
        "<tbody>" + table_rows + "</tbody></table>"
        "<p class='note'>Los outliers NO se eliminan automáticamente (ADR-002).</p>"
    )
    return _wrap_section("Outliers estadísticos", table)


def _section_freezes(quality: QualityReport) -> str:
    if not quality.freezes:
        return ""
    table_rows = "".join(
        f"<tr class='warn'><td>{html.escape(col)}</td>"
        f"<td>{f.n_sequences}</td><td>{f.max_length}</td><td>{f.total_frozen}</td></tr>"
        for col, f in quality.freezes.items()
    )
    table = (
        "<table><thead><tr><th>Columna</th><th>Episodios</th>"
        "<th>Máx. longitud</th><th>Total registros congelados</th></tr></thead>"
        "<tbody>" + table_rows + "</tbody></table>"
    )
    return _wrap_section("Congelamiento de sensor", table)


def _section_range_violations(val_report: ValidationReport) -> str:
    if not val_report.range_violations:
        return _wrap_section("Rangos físicos", "<p class='ok'>Sin violaciones de rango físico.</p>")
    table_rows = "".join(
        f"<tr class='warn'><td>{html.escape(col)}</td>"
        f"<td>{v['n']} ({v['pct']:.1f}%)</td>"
        f"<td>[{v['range'][0]}, {v['range'][1]}]</td>"
        f"<td>[{v['min_obs']:.2f}, {v['max_obs']:.2f}]</td></tr>"
        for col, v in val_report.range_violations.items()
    )
    table = (
        "<table><thead><tr><th>Columna</th><th>Violaciones</th>"
        "<th>Rango esperado</th><th>Rango observado</th></tr></thead>"
        "<tbody>" + table_rows + "</tbody></table>"
    )
    return _wrap_section("Rangos físicos", table)


def _section_cross_issues(quality: QualityReport, val_report: ValidationReport) -> str:
    issues = list(quality.cross_issues) + list(val_report.warnings)
    if not issues:
        return ""
    items = "".join(f"<li class='warn'>{html.escape(i)}</li>" for i in issues)
    return _wrap_section("Advertencias e inconsistencias", f"<ul>{items}</ul>")


def _section_descriptive(df: pd.DataFrame) -> str:
    num_df = df.select_dtypes(include="number")
    if num_df.empty:
        return ""
    desc = num_df.describe().round(3).reset_index()
    return _wrap_section("Estadísticas descriptivas", _df_to_html(desc))


# ---------------------------------------------------------------------------
# Integraciones opcionales
# ---------------------------------------------------------------------------


def _try_ydata(df: pd.DataFrame, base_path: Path) -> None:
    try:
        from ydata_profiling import ProfileReport

        out = base_path.with_name(base_path.stem + "_ydata.html")
        profile = ProfileReport(df, title="ydata-profiling", minimal=True)
        profile.to_file(out)
        logger.info("Reporte ydata-profiling guardado en: %s", out)
    except ImportError:
        logger.debug("ydata-profiling no disponible. pip install ydata-profiling")
    except Exception as e:
        logger.warning("ydata-profiling falló: %s", e)


def _try_sweetviz(df: pd.DataFrame, base_path: Path) -> None:
    try:
        import sweetviz as sv

        out = str(base_path.with_name(base_path.stem + "_sweetviz.html"))
        report = sv.analyze(df)
        report.show_html(out, open_browser=False)
        logger.info("Reporte sweetviz guardado en: %s", out)
    except ImportError:
        logger.debug("sweetviz no disponible. pip install sweetviz")
    except Exception as e:
        logger.warning("sweetviz falló: %s", e)


# ---------------------------------------------------------------------------
# Helpers HTML
# ---------------------------------------------------------------------------


def _df_to_html(df: pd.DataFrame) -> str:
    header = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body_rows = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _wrap_section(title: str, content: str) -> str:
    return f"<section><h2>{html.escape(title)}</h2>{content}</section>"


# ---------------------------------------------------------------------------
# Template HTML
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         margin: 0; padding: 24px 40px; background: #f8f9fa; color: #212529; }}
  h1   {{ color: #1a5276; border-bottom: 3px solid #1a5276; padding-bottom: 8px; }}
  h2   {{ color: #1a5276; margin-top: 32px; font-size: 1.1rem; }}
  section {{ background: white; border-radius: 8px; padding: 20px 24px;
             margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  table {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
  th    {{ background: #1a5276; color: white; padding: 7px 12px; text-align: left; }}
  td    {{ padding: 6px 12px; border-bottom: 1px solid #dee2e6; }}
  tr:hover td {{ background: #f1f8ff; }}
  tr.warn td   {{ background: #fff3cd; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }}
  .card  {{ background: #1a5276; color: white; border-radius: 8px;
            padding: 16px 24px; text-align: center; min-width: 120px; }}
  .num   {{ font-size: 1.6rem; font-weight: bold; }}
  .ok    {{ color: #1e8449; font-weight: bold; }}
  .warn  {{ color: #a04000; font-weight: bold; }}
  .note  {{ font-size: .82rem; color: #666; font-style: italic; }}
  footer {{ text-align: center; color: #999; font-size: .8rem; margin-top: 32px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<footer>Generado por estadistica-ambiental · {generated}</footer>
</body>
</html>"""
