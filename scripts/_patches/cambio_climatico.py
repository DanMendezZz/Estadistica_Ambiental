"""Enrichment cambio_climatico: contabilidad de carbono, NDC, Monte Carlo Tier 1/2."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_data,
    find_rank,
    find_seasonal,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "cambio_climatico"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    gei_md = md(
        f"{marker(KEY)}\n\n"
        "## 1b. Contabilidad de Carbono — Inventario GEI por sector\n\n"
        "Mientras el ONI captura el forzante climático externo, la **contabilidad de carbono** cuantifica\n"
        "las emisiones de GEI internas del país. En Colombia el sector **AFOLU** representa ~60% de las\n"
        "emisiones brutas — principalmente por deforestación en la Amazonia y los Andes.\n\n"
        "| Registro | Gestiona | Referencia legal |\n"
        "|---|---|---|\n"
        "| **RENARE** | Reducciones de GEI (REDD+, MDL, NAMAs) | Ley 1753/2015, Res. 1447/2018 |\n"
        "| **INGEI** | Inventario Nacional de GEI | IDEAM / Directrices IPCC |\n"
        "| **SMByC** | Monitoreo de Bosques y Carbono | IDEAM — Satelital (Landsat/Sentinel) |\n\n"
        "> **Meta NDC Colombia:** reducir 51% de emisiones netas para 2030 (tope: 169.440 kt CO2eq).\n\n"
        "**Formula IPCC (Tier 1):**\n"
        "```\n"
        "Emisiones (tCO2e) = Datos_Actividad (AD) x Factor_Emision (EF) x PCG\n"
        "Ej: ha_deforestadas x EF_biomasa_tC_ha x (44/12)  ->  tCO2e liberadas\n"
        "```"
    )

    gei_code = code(
        "# Inventario GEI sintetico por sector (kt CO2e/ano)\n"
        "# Estructura basada en INGEI Colombia 2015-2024\n"
        "sectores = ['AFOLU', 'Energia', 'Transporte', 'Industria', 'Residuos']\n"
        "n_anos = 10\n"
        "anos = list(range(2015, 2015 + n_anos))\n"
        "\n"
        "np.random.seed(99)\n"
        "emisiones_kt = {\n"
        "    'AFOLU':      [210 - i*2   + np.random.normal(0, 5)   for i in range(n_anos)],\n"
        "    'Energia':    [65  + i*0.5 + np.random.normal(0, 2)   for i in range(n_anos)],\n"
        "    'Transporte': [40  + i*0.8 + np.random.normal(0, 1.5) for i in range(n_anos)],\n"
        "    'Industria':  [20  - i*0.1 + np.random.normal(0, 1)   for i in range(n_anos)],\n"
        "    'Residuos':   [8   + i*0.2 + np.random.normal(0, 0.5) for i in range(n_anos)],\n"
        "}\n"
        "df_gei = pd.DataFrame({'ano': anos,\n"
        "                        **{s: [round(v, 1) for v in vals]\n"
        "                           for s, vals in emisiones_kt.items()}})\n"
        "df_gei['total_kt'] = df_gei[sectores].sum(axis=1).round(1)\n"
        "\n"
        "NDC_META_KT   = 169.4\n"
        "NDC_BASE_2015 = float(df_gei.loc[df_gei['ano']==2015, 'total_kt'].values[0])\n"
        "\n"
        "print(f'Linea base 2015: {NDC_BASE_2015:.1f} kt CO2e')\n"
        "print(f'Meta NDC 2030:   {NDC_META_KT:.1f} kt CO2e (reduccion {(1-NDC_META_KT/NDC_BASE_2015)*100:.0f}%)')\n"
        "df_gei"
    )

    ndc_md = md(
        "## 3c. Visualizacion NDC — Progreso y emisiones por sector\n\n"
        "Los dos paneles responden las preguntas clave del ciclo MRV:\n"
        "- **Izquierda:** evolucion de emisiones por sector — que sector lidera la reduccion?\n"
        "- **Derecha:** a que distancia esta Colombia de la meta NDC del 51% para 2030?\n\n"
        "> AFOLU (deforestacion) es la palanca principal: una reduccion del 30% en deforestacion\n"
        "> equivale a ~60 kt CO2e menos — mas que todos los demas sectores combinados."
    )

    ndc_code = code(
        "colors_sect = ['#27ae60','#e74c3c','#3498db','#f39c12','#9b59b6']\n"
        "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))\n"
        "\n"
        "# Panel A: emisiones stacked por sector\n"
        "bottom = np.zeros(n_anos)\n"
        "for sector, color in zip(sectores, colors_sect):\n"
        "    ax1.bar(df_gei['ano'], df_gei[sector], bottom=bottom,\n"
        "            label=sector, color=color, alpha=0.85, width=0.7)\n"
        "    bottom += df_gei[sector].values\n"
        "ax1.axhline(NDC_META_KT, color='black', ls='--', lw=2,\n"
        "            label=f'Meta NDC 2030 ({NDC_META_KT} kt CO2e)')\n"
        "ax1.set_title('Emisiones GEI por sector (kt CO2e/ano)', fontweight='bold')\n"
        "ax1.set_ylabel('kt CO2e')\n"
        "ax1.legend(fontsize=7, loc='upper right'); ax1.grid(axis='y', alpha=0.3)\n"
        "\n"
        "# Panel B: progreso NDC (%)\n"
        "pct_red = ((NDC_BASE_2015 - df_gei['total_kt']) / NDC_BASE_2015 * 100).clip(lower=0)\n"
        "ax2.plot(df_gei['ano'], pct_red, marker='o', color='#27ae60', lw=2, label='Reduccion observada')\n"
        "ax2.axhline(51, color='red', ls='--', lw=1.5, label='Meta NDC 51%')\n"
        "ax2.fill_between(df_gei['ano'], pct_red, 51,\n"
        "                 where=(pct_red < 51), alpha=0.15, color='red', label='Brecha pendiente')\n"
        "ax2.set_title('Progreso NDC — % reduccion vs. linea base 2015', fontweight='bold')\n"
        "ax2.set_ylabel('% reduccion'); ax2.set_ylim(0, 60)\n"
        "ax2.legend(fontsize=8); ax2.grid(alpha=0.3)\n"
        "\n"
        "plt.tight_layout(); plt.show()\n"
        "print(f'Reduccion {anos[-1]}: {pct_red.iloc[-1]:.1f}% | Brecha meta 51%: {51 - pct_red.iloc[-1]:.1f}pp')"
    )

    mc_md = md(
        "## 7b. Incertidumbre en factores de emision — Monte Carlo (Tier 1 vs. Tier 2)\n\n"
        "Una de las principales criticas a los creditos REDD+ es el **over-crediting**: usar factores de\n"
        "emision genericos (Tier 1, IPCC por defecto) en lugar de factores nacionales calibrados (Tier 2).\n"
        "Monte Carlo cuantifica esa diferencia en MtCO2e con distribucion de probabilidad completa:\n\n"
        "```\n"
        "Emisiones = Area_deforestada x EF ~ Normal(mu, sigma)\n"
        "n = 10.000 simulaciones\n"
        "```\n\n"
        "**Resultado clave:** Tier 2 reduce la incertidumbre porque usa datos del IFN\n"
        "(Inventario Forestal Nacional) y parcelas del SMByC en lugar de promedios globales tropicales.\n"
        "La diferencia de medias es el **over-crediting potencial** evitable con datos colombianos."
    )

    mc_code = code(
        "np.random.seed(42)\n"
        "N_SIM = 10_000\n"
        "\n"
        "# Factor de emision AFOLU: biomasa aerea + subterranea (tCO2e/ha)\n"
        "# Tier 1 (IPCC Tabla 4.7, bosque humedo tropical): mayor incertidumbre\n"
        "# Tier 2 (SMByC/IFN Colombia): mas preciso, parcelas nacionales\n"
        "EF_T1 = np.random.normal(120, 30, N_SIM)   # tCO2e/ha  +-25%\n"
        "EF_T2 = np.random.normal(95,  12, N_SIM)   # tCO2e/ha  +-12%\n"
        "\n"
        "AREA_HA = 50_000  # ha/ano de deforestacion\n"
        "em_T1 = (AREA_HA * EF_T1 / 1e6).clip(min=0)  # MtCO2e\n"
        "em_T2 = (AREA_HA * EF_T2 / 1e6).clip(min=0)\n"
        "\n"
        "fig, ax = plt.subplots(figsize=(10, 4))\n"
        "ax.hist(em_T1, bins=80, alpha=0.6, color='#e74c3c',\n"
        "        label=f'Tier 1 (IPCC defecto) | media={em_T1.mean():.2f}, sigma={em_T1.std():.2f} MtCO2e')\n"
        "ax.hist(em_T2, bins=80, alpha=0.6, color='#27ae60',\n"
        "        label=f'Tier 2 (Colombia IFN) | media={em_T2.mean():.2f}, sigma={em_T2.std():.2f} MtCO2e')\n"
        "ax.axvline(em_T1.mean(), color='#e74c3c', lw=2, ls='--')\n"
        "ax.axvline(em_T2.mean(), color='#27ae60', lw=2, ls='--')\n"
        "ax.set_title(f'Monte Carlo — Incertidumbre AFOLU (n={N_SIM:,} sim, area={AREA_HA:,} ha)',\n"
        "             fontweight='bold')\n"
        "ax.set_xlabel('MtCO2e/ano'); ax.legend(fontsize=9)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "ci95_T1 = np.percentile(em_T1, [2.5, 97.5])\n"
        "ci95_T2 = np.percentile(em_T2, [2.5, 97.5])\n"
        "print(f'Tier 1 IC95%: [{ci95_T1[0]:.2f}, {ci95_T1[1]:.2f}] — rango={ci95_T1[1]-ci95_T1[0]:.2f} MtCO2e')\n"
        "print(f'Tier 2 IC95%: [{ci95_T2[0]:.2f}, {ci95_T2[1]:.2f}] — rango={ci95_T2[1]-ci95_T2[0]:.2f} MtCO2e')\n"
        "print(f'Reduccion de incertidumbre con Tier 2: {(1 - em_T2.std()/em_T1.std())*100:.0f}%')\n"
        "print(f'Over-crediting potencial (Tier1-Tier2): {(em_T1.mean()-em_T2.mean()):.2f} MtCO2e')"
    )

    insert_after(cells, find_data(cells), [gei_md, gei_code])
    insert_after(cells, find_seasonal(cells), [ndc_md, ndc_code])
    insert_after(cells, find_rank(cells), [mc_md, mc_code])
