"""
Fase 8 — Análisis descriptivo: Dirección Directiva.

Línea temática: Dirección Directiva (gestión institucional)
Variable: cumplimiento de indicadores de gestión (%), reporte anual.
Síntesis: 16 indicadores × 10 años (2015-2024), valores entre 55%-95%.
          Refleja el desempeño de la entidad en metas del Plan de Acción
          Institucional (PAI) y cumplimiento MIPG / SIPLANCOL.

Análisis:
  - Solo análisis descriptivo (no es serie temporal predictiva):
    media, percentiles, tendencia global, variabilidad entre indicadores.
  - Mann-Kendall sobre el indicador compuesto agregado (promedio anual).
  - Tabla resumen por indicador (media 10 años, tendencia).
  - Semáforo de desempeño (verde ≥80%, amarillo 60-80%, rojo <60%).
  - Sin SARIMA ni walk-forward (propósito: seguimiento gerencial, no predicción).

Uso:
    python scripts/fase8_direccion_directiva.py

Salidas en data/output/fase8/:
    - direccion_directiva_datos.csv
    - direccion_directiva_descriptiva.csv
    - direccion_directiva_semaforo.csv
    - direccion_directiva_inferencial.json
    - direccion_directiva_reporte.html
"""
from __future__ import annotations

import html as html_lib
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fase8_direccion_directiva")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).parent.parent
DATA   = ROOT / "data"
OUTPUT = DATA / "output" / "fase8"
OUTPUT.mkdir(parents=True, exist_ok=True)

LINEA    = "direccion_directiva"
VARIABLE = "cumplimiento_pct"
INICIO   = 2015
FIN      = 2024

# 16 indicadores del PAI / MIPG (nombres ficticios pero representativos)
INDICADORES = [
    "Metas_PAI",
    "Ejecucion_Presupuestal",
    "Contratos_Suscritos",
    "Tramites_Licencias",
    "PQRS_Resueltas",
    "Informes_SIAC",
    "Capacitaciones_Personal",
    "Visitas_Control",
    "Proyectos_Ejecutados",
    "Acuerdos_Interinstitucionales",
    "Estaciones_Activas",
    "Planes_Manejo_Aprobados",
    "Recuperacion_Ecosistemas",
    "Quejas_Ambientales_Atendidas",
    "Cumplimiento_MIPG",
    "Transparencia_Activa",
]

# Perfiles de cumplimiento: alta o moderada variabilidad, con tendencia
PERFILES = {
    "Metas_PAI":                      {"base": 70, "trend": 1.2,  "std": 5.0},
    "Ejecucion_Presupuestal":         {"base": 80, "trend": 0.5,  "std": 3.5},
    "Contratos_Suscritos":            {"base": 75, "trend": 0.8,  "std": 6.0},
    "Tramites_Licencias":             {"base": 65, "trend": 1.5,  "std": 8.0},
    "PQRS_Resueltas":                 {"base": 85, "trend": 0.3,  "std": 4.0},
    "Informes_SIAC":                  {"base": 72, "trend": 2.0,  "std": 5.5},
    "Capacitaciones_Personal":        {"base": 60, "trend": 1.8,  "std": 7.0},
    "Visitas_Control":                {"base": 55, "trend": 2.5,  "std": 9.0},
    "Proyectos_Ejecutados":           {"base": 78, "trend": 0.6,  "std": 4.5},
    "Acuerdos_Interinstitucionales":  {"base": 68, "trend": 1.0,  "std": 6.5},
    "Estaciones_Activas":             {"base": 73, "trend": 1.5,  "std": 4.0},
    "Planes_Manejo_Aprobados":        {"base": 62, "trend": 2.2,  "std": 7.5},
    "Recuperacion_Ecosistemas":       {"base": 58, "trend": 2.8,  "std": 8.5},
    "Quejas_Ambientales_Atendidas":   {"base": 88, "trend": 0.2,  "std": 3.0},
    "Cumplimiento_MIPG":              {"base": 76, "trend": 1.0,  "std": 4.0},
    "Transparencia_Activa":           {"base": 82, "trend": 0.4,  "std": 3.5},
}


# ===========================================================================
# 1. GENERACIÓN DE DATOS SINTÉTICOS
# ===========================================================================

def generar_datos() -> pd.DataFrame:
    """Genera 16 indicadores × 10 años de cumplimiento (%).

    Cada indicador tiene una base, tendencia positiva leve y ruido gaussiano.
    Rango forzado entre 55% y 95% para reflejar el rango real de PAIs.
    """
    logger.info("--- Generando datos sintéticos de dirección directiva ---")
    rng = np.random.default_rng(42)

    anios = np.arange(INICIO, FIN + 1)
    n     = len(anios)  # 10 años

    registros = []
    for indicador in INDICADORES:
        perfil = PERFILES.get(indicador, {"base": 70, "trend": 1.0, "std": 5.0})
        t      = np.arange(n)
        valores = (
            perfil["base"]
            + perfil["trend"] * t
            + rng.normal(0, perfil["std"], n)
        )
        valores = np.clip(valores, 55.0, 95.0)

        for i, anio in enumerate(anios):
            registros.append({
                "anio":             anio,
                "indicador":        indicador,
                "cumplimiento_pct": round(float(valores[i]), 2),
            })

    df = pd.DataFrame(registros)
    logger.info("Datos generados: %d registros (%d indicadores × %d años)",
                len(df), len(INDICADORES), n)
    logger.info("Cumplimiento medio global: %.2f%% | std=%.2f%%",
                df["cumplimiento_pct"].mean(), df["cumplimiento_pct"].std())

    out_path = OUTPUT / "direccion_directiva_datos.csv"
    df.to_csv(out_path, index=False)
    logger.info("CSV guardado: %s", out_path.name)
    return df


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar(df: pd.DataFrame) -> dict:
    """validate(df, linea_tematica='direccion_directiva')."""
    logger.info("--- Validación de dominio ---")
    df_val = df.copy()
    df_val["fecha"] = pd.to_datetime(df_val["anio"].astype(str) + "-01-01")
    resultados: dict = {}
    try:
        from estadistica_ambiental.io.validators import validate
        report = validate(df_val, date_col="fecha", linea_tematica=LINEA)
        logger.info(report.summary())
        resultados = {
            "n_rows":    report.n_rows,
            "n_cols":    report.n_cols,
            "missing":   report.missing,
            "has_issues": report.has_issues(),
        }
        logger.info("Validación OK: issues=%s", report.has_issues())
    except Exception as exc:
        logger.warning("Validación skipped: %s", exc)
    return resultados


# ===========================================================================
# 3. EDA + DESCRIPTIVA
# ===========================================================================

def eda_descriptiva(df: pd.DataFrame) -> pd.DataFrame:
    """Estadísticas por indicador (media 10 años, std, min, max, p25, p75)."""
    logger.info("--- EDA + Descriptiva por indicador ---")

    resumen_rows = []
    for ind in INDICADORES:
        sub = df[df["indicador"] == ind]["cumplimiento_pct"].dropna()
        resumen_rows.append({
            "indicador": ind,
            "n":         len(sub),
            "media":     round(float(sub.mean()), 2),
            "mediana":   round(float(sub.median()), 2),
            "std":       round(float(sub.std()), 2),
            "p25":       round(float(sub.quantile(0.25)), 2),
            "p75":       round(float(sub.quantile(0.75)), 2),
            "min":       round(float(sub.min()), 2),
            "max":       round(float(sub.max()), 2),
        })
        logger.info("  %-40s media=%.1f%% | std=%.1f%% | [%.1f, %.1f]",
                    ind, resumen_rows[-1]["media"], resumen_rows[-1]["std"],
                    resumen_rows[-1]["min"], resumen_rows[-1]["max"])

    # Resumen global anual (compuesto: promedio de todos los indicadores por año)
    anual = df.groupby("anio")["cumplimiento_pct"].agg(
        n="count", media="mean", mediana="median", std="std",
        min="min", max="max",
        p25=lambda x: x.quantile(0.25),
        p75=lambda x: x.quantile(0.75),
    ).round(2)
    logger.info("Resumen anual compuesto:")
    for anio, row in anual.iterrows():
        logger.info("  %d: media=%.1f%% | std=%.1f%% | [%.1f, %.1f]",
                    anio, row["media"], row["std"], row["min"], row["max"])

    resumen = pd.DataFrame(resumen_rows).set_index("indicador")
    out_path = OUTPUT / "direccion_directiva_descriptiva.csv"
    resumen.to_csv(out_path)
    logger.info("Descriptiva por indicador guardada: %s", out_path.name)
    return resumen


# ===========================================================================
# 4. SEMÁFORO DE DESEMPEÑO
# ===========================================================================

def semaforo(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica cada indicador en verde/amarillo/rojo según media histórica.

    Umbrales:
    - Verde:    media ≥ 80%
    - Amarillo: 60% ≤ media < 80%
    - Rojo:     media < 60%
    """
    logger.info("--- Semáforo de desempeño ---")

    medias = (
        df.groupby("indicador")["cumplimiento_pct"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"cumplimiento_pct": "media_historica_pct"})
    )

    def _categoria(val: float) -> str:
        if val >= 80.0:
            return "verde"
        if val >= 60.0:
            return "amarillo"
        return "rojo"

    medias["semaforo"] = medias["media_historica_pct"].apply(_categoria)

    conteo = medias["semaforo"].value_counts()
    logger.info("Distribución semáforo: %s", conteo.to_dict())
    for _, row in medias.sort_values("media_historica_pct").iterrows():
        emoji = {"verde": "[OK]", "amarillo": "[!!]", "rojo": "[XX]"}
        logger.info("  %s %-40s %.1f%%",
                    emoji.get(row["semaforo"], "   "),
                    row["indicador"],
                    row["media_historica_pct"])

    out_path = OUTPUT / "direccion_directiva_semaforo.csv"
    medias.to_csv(out_path, index=False)
    logger.info("Semáforo guardado: %s", out_path.name)
    return medias


# ===========================================================================
# 5. INFERENCIAL — MANN-KENDALL COMPUESTO
# ===========================================================================

def inferencial(df: pd.DataFrame) -> dict:
    """Mann-Kendall sobre el indicador compuesto (promedio anual de todos los indicadores)."""
    logger.info("--- Inferencial (Mann-Kendall compuesto) ---")
    resultados: dict = {}

    compuesto = (
        df.groupby("anio")["cumplimiento_pct"]
        .mean()
        .reset_index()
        .rename(columns={"cumplimiento_pct": "compuesto_pct"})
    )
    serie_compuesta = pd.Series(
        compuesto["compuesto_pct"].values,
        index=pd.to_datetime(compuesto["anio"].astype(str) + "-01-01"),
        name="compuesto_pct",
    )

    try:
        from estadistica_ambiental.inference.trend import mann_kendall, sens_slope
        mk = mann_kendall(serie_compuesta)
        ss = sens_slope(serie_compuesta)
        slope_anual = float(ss.get("slope", 0.0))
        resultados["mann_kendall_compuesto"] = {
            "n":                    len(serie_compuesta),
            "tendencia":            mk.get("trend", "unknown"),
            "p_value":              round(float(mk.get("pval", 1.0)), 6),
            "significativo":        mk.get("pval", 1.0) < 0.05,
            "tau":                  round(float(mk.get("tau", 0.0)), 4),
            "sen_slope_anual_pp":   round(float(slope_anual), 4),
        }
        r = resultados["mann_kendall_compuesto"]
        logger.info("MK compuesto: %s | p=%.6f | slope=%.4f pp/año%s",
                    r["tendencia"], r["p_value"], r["sen_slope_anual_pp"],
                    " [SIGNIFICATIVO]" if r["significativo"] else "")
    except Exception as exc:
        logger.warning("Mann-Kendall skipped: %s", exc)

    # Percentiles por año del indicador compuesto
    resultados["compuesto_por_anio"] = {
        str(row["anio"]): round(float(row["compuesto_pct"]), 2)
        for _, row in compuesto.iterrows()
    }

    out_path = OUTPUT / "direccion_directiva_inferencial.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Inferencial guardado: %s", out_path.name)
    return resultados


# ===========================================================================
# 6. REPORTE HTML DESCRIPTIVO (sin SARIMA)
# ===========================================================================

def _semaforo_color(val: float) -> str:
    """Retorna color CSS para el semáforo."""
    if val >= 80.0:
        return "#27ae60"
    if val >= 60.0:
        return "#f39c12"
    return "#e74c3c"


def generar_reporte_html(
    df: pd.DataFrame,
    resumen: pd.DataFrame,
    semaforo_df: pd.DataFrame,
    inf: dict,
) -> Path:
    """Genera reporte HTML descriptivo para Dirección Directiva."""
    logger.info("--- Generando reporte HTML ---")
    out_path = OUTPUT / "direccion_directiva_reporte.html"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Tabla de semáforo por indicador
    rows_sem = ""
    for _, row in semaforo_df.sort_values("media_historica_pct", ascending=False).iterrows():
        color = _semaforo_color(row["media_historica_pct"])
        rows_sem += (
            f"<tr>"
            f"<td>{html_lib.escape(row['indicador'])}</td>"
            f"<td style='text-align:right'>{row['media_historica_pct']:.1f}%</td>"
            f"<td><span style='background:{color};color:white;padding:2px 10px;"
            f"border-radius:12px;font-size:.8rem'>{row['semaforo'].upper()}</span></td>"
            f"</tr>"
        )

    # Compuesto por año
    compuesto_anio = inf.get("compuesto_por_anio", {})
    rows_anual = ""
    for anio, val in compuesto_anio.items():
        color = _semaforo_color(val)
        rows_anual += (
            f"<tr>"
            f"<td>{anio}</td>"
            f"<td style='text-align:right'>{val:.1f}%</td>"
            f"<td><span style='background:{color};color:white;padding:2px 8px;"
            f"border-radius:10px;font-size:.8rem'>"
            f"{'OK' if val >= 80 else ('!' if val >= 60 else 'ALERTA')}"
            f"</span></td>"
            f"</tr>"
        )

    # Tendencia Mann-Kendall
    mk_r = inf.get("mann_kendall_compuesto", {})
    mk_html = ""
    if mk_r:
        signif = "Sí" if mk_r.get("significativo") else "No"
        mk_html = (
            f"<p>Tendencia Mann-Kendall (compuesto anual): "
            f"<strong>{html_lib.escape(mk_r.get('tendencia','?'))}</strong> | "
            f"p = {mk_r.get('p_value', 1.0):.6f} | Significativo: {signif} | "
            f"Sen slope: {mk_r.get('sen_slope_anual_pp', 0.0):.3f} pp/año</p>"
        )

    # Datos para gráfico de líneas (compuesto anual)
    anios_js  = list(compuesto_anio.keys())
    vals_js   = list(compuesto_anio.values())

    content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Dirección Directiva — Cumplimiento de Indicadores PAI</title>
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
  footer {{ text-align: center; color: #999; font-size: .8rem; margin-top: 24px; }}
</style>
</head>
<body>
<h1>Dirección Directiva — Cumplimiento de Indicadores PAI</h1>
<p>Entidad: Corporación Autónoma Regional (ficticia) | Período: {INICIO}–{FIN} |
   {len(INDICADORES)} indicadores PAI/MIPG | Datos: <em>sintéticos</em></p>

<section>
  <h2>Tendencia del indicador compuesto</h2>
  {mk_html}
  <canvas id="lineChart" style="max-height:300px"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <script>
  new Chart(document.getElementById('lineChart'), {{
    type: 'line',
    data: {{
      labels: {anios_js},
      datasets: [{{
        label: 'Compuesto (promedio 16 indicadores)',
        data: {vals_js},
        borderColor: '#1a5276', backgroundColor: 'rgba(26,82,118,0.08)',
        borderWidth: 2, pointRadius: 4, fill: true
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'top' }} }},
      scales: {{
        y: {{
          min: 50, max: 100,
          title: {{ display: true, text: 'Cumplimiento (%)' }}
        }}
      }}
    }}
  }});
  </script>
</section>

<section>
  <h2>Compuesto anual</h2>
  <table>
    <thead><tr><th>Año</th><th>Cumplimiento medio (%)</th><th>Estado</th></tr></thead>
    <tbody>{rows_anual}</tbody>
  </table>
</section>

<section>
  <h2>Semáforo por indicador (media histórica {INICIO}-{FIN})</h2>
  <p><span style="background:#27ae60;color:white;padding:1px 8px;border-radius:10px">
     VERDE</span> ≥ 80% &nbsp;
     <span style="background:#f39c12;color:white;padding:1px 8px;border-radius:10px">
     AMARILLO</span> 60-80% &nbsp;
     <span style="background:#e74c3c;color:white;padding:1px 8px;border-radius:10px">
     ROJO</span> &lt; 60%</p>
  <table>
    <thead><tr><th>Indicador</th><th>Media histórica (%)</th><th>Semáforo</th></tr></thead>
    <tbody>{rows_sem}</tbody>
  </table>
</section>

<footer>estadistica-ambiental · generado {now}</footer>
</body>
</html>"""

    out_path.write_text(content, encoding="utf-8")
    logger.info("Reporte HTML guardado: %s", out_path.name)
    return out_path


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    logger.info("=" * 65)
    logger.info("FASE 8 — DIRECCIÓN DIRECTIVA | Cumplimiento indicadores PAI")
    logger.info("%d indicadores × %d años (%d-%d) | sintéticos",
                len(INDICADORES), FIN - INICIO + 1, INICIO, FIN)
    logger.info("=" * 65)

    # 1. Datos
    try:
        df = generar_datos()
    except Exception as exc:
        logger.error("Generación de datos falló: %s", exc)
        return

    # 2. Validación
    try:
        validar(df)
    except Exception as exc:
        logger.warning("Validación falló: %s", exc)

    # 3. EDA + Descriptiva
    try:
        resumen = eda_descriptiva(df)
    except Exception as exc:
        logger.warning("EDA/Descriptiva falló: %s", exc)
        resumen = pd.DataFrame()

    # 4. Semáforo
    try:
        sem = semaforo(df)
    except Exception as exc:
        logger.warning("Semáforo falló: %s", exc)
        sem = pd.DataFrame()

    # 5. Inferencial
    try:
        inf = inferencial(df)
    except Exception as exc:
        logger.warning("Inferencial falló: %s", exc)
        inf = {}

    # 6. Reporte HTML
    try:
        generar_reporte_html(df, resumen, sem, inf)
    except Exception as exc:
        logger.error("Reporte HTML falló: %s", exc)
        import traceback
        traceback.print_exc()

    # Resumen ejecutivo
    logger.info("=" * 65)
    logger.info("RESUMEN EJECUTIVO — Dirección Directiva")
    logger.info("  Período: %d-%d | %d indicadores", INICIO, FIN, len(INDICADORES))
    logger.info("  Cumplimiento medio global: %.2f%%", df["cumplimiento_pct"].mean())
    if not sem.empty:
        conteo = sem["semaforo"].value_counts().to_dict()
        logger.info("  Semáforo: verde=%d | amarillo=%d | rojo=%d",
                    conteo.get("verde", 0),
                    conteo.get("amarillo", 0),
                    conteo.get("rojo", 0))
        peor = sem.sort_values("media_historica_pct").iloc[0]
        mejor = sem.sort_values("media_historica_pct").iloc[-1]
        logger.info("  Mejor indicador: %-40s %.1f%%",
                    mejor["indicador"], mejor["media_historica_pct"])
        logger.info("  Peor indicador:  %-40s %.1f%%",
                    peor["indicador"], peor["media_historica_pct"])
    mk_r = inf.get("mann_kendall_compuesto", {})
    if mk_r:
        logger.info("  MK compuesto: %s | p=%.6f | %.4f pp/año%s",
                    mk_r.get("tendencia", "?"),
                    mk_r.get("p_value", 1.0),
                    mk_r.get("sen_slope_anual_pp", 0.0),
                    " [SIGNIF.]" if mk_r.get("significativo") else "")
    logger.info("  Salidas en: %s", OUTPUT)
    logger.info("=" * 65)
    logger.info("Fase 8 Dirección Directiva completada.")


if __name__ == "__main__":
    main()
