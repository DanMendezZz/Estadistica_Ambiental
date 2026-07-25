"""Enrichment predios_conservacion: AHP + costo de oportunidad + RBC."""

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

KEY = "predios_conservacion"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    ahp_md = md(
        f"{marker(KEY)}\n\n"
        "## 3c. AHP para priorizacion de predios PSA — Costo de oportunidad\n\n"
        "El **AHP (Analytic Hierarchy Process)** sopesa criterios ambientales y socioeconomicos "
        "para priorizar donde invertir recursos del 1% (Ley 99/1993 Art.111 y Ley 2320/2023):\n\n"
        "| Criterio | Peso AHP | Por que |\n"
        "|---|---|---|\n"
        "| NDVI (vigor vegetal) | 35% | Mayor cobertura = menor intervencion requerida |\n"
        "| TWI (indice topografico humedad) | 25% | Alta TWI = zona de recarga prioritaria |\n"
        "| Costo de oportunidad ($/ha) | 20% | Menor costo = mayor eficiencia del PSA |\n"
        "| Pendiente del terreno | 10% | Alta pendiente = riesgo erosion sin cobertura |\n"
        "| Acceso a fuente de agua | 10% | Abastece acueducto municipal |\n\n"
        "**Costo de oportunidad:** beneficio economico sacrificado al dejar la ganaderia/agricultura "
        "por conservacion. PSA eficiente: compensacion >= costo oportunidad.\n\n"
        "**RBC (Relacion Beneficio-Costo):** RBC > 1 = el valor del servicio hidrico supera el costo del incentivo."
    )

    ahp_code = code(
        "# AHP para priorizacion de predios PSA\n"
        "np.random.seed(17)\n"
        "n_predios = 20\n"
        "\n"
        "# Variables por predio (simuladas, normalizadas 0-1)\n"
        "predios_df = pd.DataFrame({\n"
        "    'predio_id': [f'PRD-{i+1:03d}' for i in range(n_predios)],\n"
        "    'ndvi':           np.clip(np.random.normal(0.55, 0.18, n_predios), 0, 1),\n"
        "    'twi':            np.clip(np.random.normal(0.5, 0.2, n_predios), 0, 1),\n"
        "    'pendiente':      np.clip(np.random.normal(0.4, 0.2, n_predios), 0, 1),\n"
        "    'acceso_agua':    np.random.uniform(0, 1, n_predios),\n"
        "    'costo_oport_ha': np.random.uniform(300_000, 2_500_000, n_predios).round(-3),  # $/ha/ano\n"
        "})\n"
        "\n"
        "# Normalizar costo de oportunidad (inverso: menor costo = mayor puntaje)\n"
        "co_min, co_max = predios_df['costo_oport_ha'].min(), predios_df['costo_oport_ha'].max()\n"
        "predios_df['costo_norm'] = 1 - (predios_df['costo_oport_ha'] - co_min) / (co_max - co_min)\n"
        "\n"
        "# Pesos AHP\n"
        "pesos = {'ndvi': 0.35, 'twi': 0.25, 'costo_norm': 0.20, 'pendiente': 0.10, 'acceso_agua': 0.10}\n"
        "\n"
        "# Puntaje AHP ponderado\n"
        "predios_df['puntaje_ahp'] = sum(\n"
        "    predios_df[col] * peso for col, peso in pesos.items())\n"
        "predios_df['puntaje_ahp'] = predios_df['puntaje_ahp'].round(4)\n"
        "predios_df['rango_ahp'] = predios_df['puntaje_ahp'].rank(ascending=False).astype(int)\n"
        "\n"
        "# RBC simplificado: valor servicio hidrico / costo PSA\n"
        "VALOR_AGUA_HA = 1_500_000  # $/ha/ano valor agua para acueducto\n"
        "INCENTIVO_PSA = 600_000    # $/ha/ano incentivo tipico PSA (Decreto 1007/2018)\n"
        "predios_df['rbc'] = (VALOR_AGUA_HA * predios_df['ndvi']) / predios_df['costo_oport_ha']\n"
        "\n"
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
        "\n"
        "# Panel A: Puntaje AHP por predio\n"
        "top10 = predios_df.nlargest(10, 'puntaje_ahp')\n"
        "ax = axes[0]\n"
        "bars = ax.barh(top10['predio_id'], top10['puntaje_ahp'],\n"
        "               color=['#27ae60' if r <= 5 else '#f1c40f' for r in top10['rango_ahp']], alpha=0.85)\n"
        "ax.set_xlabel('Puntaje AHP (0-1)')\n"
        "ax.set_title('Top 10 Predios Priorizados — AHP\\n(NDVI 35%, TWI 25%, Costo 20%...)', fontweight='bold')\n"
        "ax.grid(axis='x', alpha=0.3)\n"
        "\n"
        "# Panel B: Scatter NDVI vs Costo de oportunidad coloreado por RBC\n"
        "ax = axes[1]\n"
        "sc = ax.scatter(predios_df['costo_oport_ha']/1e6,\n"
        "                predios_df['ndvi'],\n"
        "                c=predios_df['rbc'], cmap='RdYlGn', s=60, alpha=0.8)\n"
        "plt.colorbar(sc, ax=ax, label='RBC (valor/costo)')\n"
        "ax.axhline(0.5, color='green', ls='--', lw=1)\n"
        "ax.set_xlabel('Costo de oportunidad (M$/ha/ano)')\n"
        "ax.set_ylabel('NDVI (vigor vegetal)')\n"
        "ax.set_title('NDVI vs Costo oportunidad (color=RBC)\\n(PSA eficiente: RBC > 1)', fontweight='bold')\n"
        "ax.grid(alpha=0.3)\n"
        "\n"
        "plt.suptitle('Priorizacion PSA — Ley 99/1993 Art.111 + Ley 2320/2023 + Decreto 1007/2018',\n"
        "             fontweight='bold', fontsize=11)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "n_rbc_positivo = (predios_df['rbc'] >= 1.0).sum()\n"
        "print(f'Predios con RBC >= 1 (PSA eficiente): {n_rbc_positivo}/{n_predios}')\n"
        "print(f'Costo oportunidad promedio: ${predios_df[\"costo_oport_ha\"].mean()/1e6:.2f} M/ha/ano')\n"
        "print('Top 3 predios priorizados:')\n"
        "print(predios_df.nsmallest(3, 'rango_ahp')[['predio_id','puntaje_ahp','costo_oport_ha','rbc']])"
    )

    insert_after(cells, find_seasonal(cells), [ahp_md, ahp_code])
