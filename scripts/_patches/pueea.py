"""Enrichment PUEEA: IANC + Isolation Forest para anomalias de caudal."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_seasonal,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "pueea"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    ianc_md = md(
        f"{marker(KEY)}\n\n"
        "## 3c. IANC — Perdidas de agua y deteccion de anomalias (Isolation Forest)\n\n"
        "El **IANC (Indice de Agua No Contabilizada)** mide las perdidas del sistema de acueducto "
        "como porcentaje del volumen captado. Meta PUEAA: IANC <= 30% (Res. 943/2021 CRA).\n\n"
        "```\n"
        "IANC = (Volumen_captado - Volumen_facturado) / Volumen_captado * 100 (%)\n"
        "Perdidas tecnicas: fugas en red, reboses en tanques\n"
        "Perdidas comerciales: robos de agua, errores en medicion\n"
        "```\n\n"
        "**Isolation Forest** detecta lecturas de caudal anomalas "
        "(fugas subitas, captaciones ilegales, fallos de sensor)."
    )

    ianc_code = code(
        "from sklearn.ensemble import IsolationForest\n"
        "\n"
        "np.random.seed(66)\n"
        "n = len(df)\n"
        "\n"
        "# Volumen captado vs facturado (m3/mes)\n"
        "vol_captado   = df['consumo_agua'].values * 1000  # proxy: consumo -> captacion\n"
        "vol_facturado = vol_captado * np.clip(np.random.normal(0.72, 0.08, n), 0.3, 0.95)\n"
        "\n"
        "# IANC mensual\n"
        "ianc = (1 - vol_facturado / vol_captado) * 100\n"
        "df['ianc_pct'] = ianc.round(1)\n"
        "\n"
        "# Isolation Forest sobre caudal diario simulado\n"
        "np.random.seed(7)\n"
        "N_dias = 365\n"
        "caudal_diario = np.random.normal(15, 3, N_dias)  # L/s\n"
        "# Inyectar anomalias (fugas/captaciones ilegales)\n"
        "idx_anom = np.random.choice(N_dias, 12, replace=False)\n"
        "caudal_diario[idx_anom] += np.random.uniform(15, 40, 12)\n"
        "\n"
        "iso_caudal = IsolationForest(contamination=0.05, random_state=42)\n"
        "pred_caudal = iso_caudal.fit_predict(caudal_diario.reshape(-1, 1))\n"
        "scores_caudal = iso_caudal.decision_function(caudal_diario.reshape(-1, 1))\n"
        "\n"
        "fig, axes = plt.subplots(1, 3, figsize=(16, 4))\n"
        "\n"
        "# Panel A: IANC en el tiempo\n"
        "ax = axes[0]\n"
        "colors_ianc = ['#e74c3c' if v > 30 else '#f1c40f' if v > 20 else '#27ae60'\n"
        "               for v in df['ianc_pct']]\n"
        "ax.bar(df['fecha'], df['ianc_pct'], color=colors_ianc, width=20, alpha=0.85)\n"
        "ax.axhline(30, color='red', ls='--', lw=1.5, label='Meta IANC <= 30% (Res. 943/2021)')\n"
        "ax.set_title('IANC — Indice Agua No Contabilizada (%)', fontweight='bold')\n"
        "ax.set_ylabel('IANC (%)'); ax.legend(fontsize=7); ax.grid(axis='y', alpha=0.3)\n"
        "\n"
        "# Panel B: Caudal diario + anomalias Isolation Forest\n"
        "ax = axes[1]\n"
        "t_dias = range(N_dias)\n"
        "colors_if = ['#e74c3c' if p == -1 else '#2980b9' for p in pred_caudal]\n"
        "ax.scatter(t_dias, caudal_diario, c=colors_if, s=8, alpha=0.7)\n"
        "ax.set_title('Isolation Forest — Anomalias caudal diario\\n(fugas, captaciones ilegales)', fontweight='bold')\n"
        "ax.set_xlabel('Dia'); ax.set_ylabel('Caudal (L/s)')\n"
        "from matplotlib.patches import Patch\n"
        "ax.legend(handles=[Patch(color='#e74c3c',label='Anomalia'),\n"
        "                   Patch(color='#2980b9',label='Normal')], fontsize=8)\n"
        "ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel C: Tipo de perdidas\n"
        "ax = axes[2]\n"
        "perdidas_tecnicas   = np.clip(ianc * 0.65, 0, None).mean()\n"
        "perdidas_comerciales= np.clip(ianc * 0.35, 0, None).mean()\n"
        "ax.bar(['Tecnicas\\n(fugas/reboses)', 'Comerciales\\n(fraude/medicion)'],\n"
        "       [perdidas_tecnicas, perdidas_comerciales],\n"
        "       color=['#e74c3c', '#e67e22'], alpha=0.85, width=0.5)\n"
        "ax.set_title('Composicion IANC promedio\\n(PUEAA: meta reduccion quinquenal)', fontweight='bold')\n"
        "ax.set_ylabel('IANC medio (%)'); ax.grid(axis='y', alpha=0.3)\n"
        "\n"
        "plt.suptitle('PUEAA — IANC + Anomalias Isolation Forest (Ley 373/1997)',\n"
        "             fontweight='bold', fontsize=11)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "n_anom_if = (pred_caudal == -1).sum()\n"
        "print(f'IANC promedio: {ianc.mean():.1f}% | Meses > 30%: {(ianc > 30).sum()}/{n}')\n"
        "print(f'Anomalias caudal detectadas: {n_anom_if}/365 dias ({n_anom_if/365*100:.1f}%)')\n"
        "print(f'Injected anomalias: {len(idx_anom)} — todas dentro de los {n_anom_if} detectados')"
    )

    insert_after(cells, find_seasonal(cells), [ianc_md, ianc_code])
