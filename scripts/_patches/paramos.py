"""Enrichment paramos: IRH, cobertura vegetal y gradiente Caldas-Lang."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_data,
    find_mk,
    find_seasonal,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "paramos"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    irh_md = md(
        f"{marker(KEY)}\n\n"
        "## 1b. Indicadores de paramo como fabrica de agua — IRH, caudal y cobertura\n\n"
        "La temperatura es la variable de monitoreo climatico, pero los **indicadores de salud**\n"
        "del paramo son hidrologicos y de cobertura vegetal:\n\n"
        "| Indicador | Escala | Umbral critico | Fuente |\n"
        "|---|---|---|---|\n"
        "| **IRH** (Retencion Hidrica) | 0 a 1 | < 0.6 = deterioro | IDEAM / ENA |\n"
        "| **Cobertura natural** | 0-100% | < 70% = alerta | Landsat/Sentinel |\n"
        "| **Caudal base** | m3/s | Tendencia decreciente = alarma | IDEAM limnimetria |\n\n"
        "> **Ley 1930/2018:** Los complejos de paramo delimitados deben mantener IRH >= 0.6\n"
        "> para garantizar el suministro de agua a las cuencas abastecedoras.\n\n"
        "> **IRH_THRESHOLDS en config.py:** muy_baja=0.2, baja=0.4, moderada=0.6, alta=0.8"
    )

    irh_code = code(
        "# Indicadores sinteticos de ecosistema paramo (complementan la temperatura)\n"
        "np.random.seed(77)\n"
        "n = len(df)\n"
        "\n"
        "# IRH: Indice de Retencion Hidrica (0-1)\n"
        "# Tendencia decreciente por presion agricola, recuperacion parcial en anos lluviosos\n"
        "irh_trend = np.linspace(0.75, 0.58, n)  # deterioro gradual\n"
        "irh_seasonal = 0.08 * np.sin(2 * np.pi * np.arange(n) / 12)  # ciclo lluvia-sequia\n"
        "irh = np.clip(irh_trend + irh_seasonal + np.random.normal(0, 0.03, n), 0.1, 1.0)\n"
        "\n"
        "# Caudal base (m3/s) — correlacionado con IRH y precipitacion\n"
        "caudal = 2.5 * irh + 0.5 * np.random.normal(0, 0.2, n)\n"
        "caudal = np.clip(caudal, 0.1, None)\n"
        "\n"
        "# Cobertura natural (%) — decrece por ganaderia y papa\n"
        "cobertura = np.clip(np.linspace(82, 68, n) + np.random.normal(0, 2, n), 40, 100)\n"
        "\n"
        "df['irh'] = irh.round(3)\n"
        "df['caudal_m3s'] = caudal.round(3)\n"
        "df['cobertura_pct'] = cobertura.round(1)\n"
        "\n"
        "from estadistica_ambiental.config import IRH_THRESHOLDS\n"
        "\n"
        "print('IRH_THRESHOLDS (config.py):', IRH_THRESHOLDS)\n"
        "print(f'\\nIRH actual | min={irh.min():.2f} max={irh.max():.2f} media={irh.mean():.2f}')\n"
        "print(f'Meses con IRH < 0.6 (deterioro): {(irh < 0.6).sum()} de {n}')\n"
        "df[['fecha', 'temperatura', 'irh', 'caudal_m3s', 'cobertura_pct']].head()"
    )

    irh_viz_md = md(
        "## 3c. Dashboard IRH — Salud hidrologica del paramo\n\n"
        "El **IRH** (Indice de Retencion y Regulacion Hidrica) es el indicador operativo\n"
        "para clasificar el estado del paramo como regulador hidrico. Las categorias provienen\n"
        "de `config.IRH_THRESHOLDS` y son las mismas que usa el IDEAM en el ENA (Estudio Nacional del Agua):\n\n"
        "| IRH | Categoria | Significado para gestion |\n"
        "|---|---|---|\n"
        "| > 0.8 | Muy alta | Ecosistema pristino — preservar |\n"
        "| 0.6 – 0.8 | Alta / moderada | Funcionamiento aceptable |\n"
        "| 0.4 – 0.6 | Baja | Deterioro — iniciar restauracion |\n"
        "| < 0.4 | Muy baja | Crisis hidrica — intervencion urgente |"
    )

    irh_viz_code = code(
        "fig, axes = plt.subplots(2, 2, figsize=(14, 8))\n"
        "\n"
        "# Panel A: IRH en el tiempo con bandas de umbral\n"
        "ax = axes[0, 0]\n"
        "ax.plot(df['fecha'], df['irh'], lw=1.5, color='#2980b9', label='IRH mensual')\n"
        "ax.axhspan(0.8, 1.0, alpha=0.12, color='#27ae60', label='Muy alta (>0.8)')\n"
        "ax.axhspan(0.6, 0.8, alpha=0.10, color='#f1c40f', label='Alta/Moderada (0.6-0.8)')\n"
        "ax.axhspan(0.4, 0.6, alpha=0.10, color='#e67e22', label='Baja (0.4-0.6)')\n"
        "ax.axhspan(0.0, 0.4, alpha=0.12, color='#e74c3c', label='Muy baja (<0.4)')\n"
        "ax.axhline(0.6, color='#e67e22', ls='--', lw=1.5, label='Umbral critico 0.6')\n"
        "ax.set_title('IRH — Retencion Hidrica del Paramo', fontweight='bold')\n"
        "ax.set_ylabel('IRH (0-1)'); ax.set_ylim(0, 1)\n"
        "ax.legend(fontsize=7, loc='lower left'); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel B: Cobertura natural (%)\n"
        "ax = axes[0, 1]\n"
        "ax.fill_between(df['fecha'], df['cobertura_pct'], alpha=0.6, color='#27ae60')\n"
        "ax.axhline(70, color='red', ls='--', lw=1.5, label='Umbral critico 70%')\n"
        "ax.set_title('Cobertura Natural (%)', fontweight='bold')\n"
        "ax.set_ylabel('%'); ax.set_ylim(50, 100)\n"
        "ax.legend(fontsize=8); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel C: Caudal base (m3/s)\n"
        "ax = axes[1, 0]\n"
        "ax.plot(df['fecha'], df['caudal_m3s'], lw=1, color='#3498db')\n"
        "ax.fill_between(df['fecha'], df['caudal_m3s'], alpha=0.3, color='#3498db')\n"
        "ax.set_title('Caudal Base (m3/s)', fontweight='bold')\n"
        "ax.set_ylabel('m3/s'); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel D: IRH vs Cobertura (scatter)\n"
        "ax = axes[1, 1]\n"
        "sc = ax.scatter(df['cobertura_pct'], df['irh'], c=df['temperatura'],\n"
        "                cmap='RdYlGn_r', alpha=0.6, s=20)\n"
        "plt.colorbar(sc, ax=ax, label='Temp (C)')\n"
        "ax.axhline(0.6, color='orange', ls='--', lw=1)\n"
        "ax.axvline(70, color='red', ls='--', lw=1)\n"
        "ax.set_xlabel('Cobertura Natural (%)'); ax.set_ylabel('IRH')\n"
        "ax.set_title('IRH vs Cobertura (color=temperatura)', fontweight='bold')\n"
        "ax.grid(alpha=0.3)\n"
        "\n"
        "plt.suptitle('Dashboard de Salud Hidrologica — Paramo (Ley 1930/2018)',\n"
        "             fontweight='bold', fontsize=12)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "# Resumen de alertas\n"
        "n_alerta = (df['irh'] < 0.6).sum()\n"
        "n_cob = (df['cobertura_pct'] < 70).sum()\n"
        "print(f'Meses con IRH < 0.6 (restauracion necesaria): {n_alerta}/{len(df)} ({n_alerta/len(df)*100:.0f}%)')\n"
        "print(f'Meses con cobertura < 70% (alerta): {n_cob}/{len(df)} ({n_cob/len(df)*100:.0f}%)')"
    )

    caldas_md = md(
        "## 5c. Gradiente altitudinal Caldas-Lang — temperatura vs. altitud\n\n"
        "La **relacion Caldas-Lang** describe la variacion de temperatura con la altitud en Colombia.\n"
        "El gradiente termico vertical es ~0.6C/100m en paramos andinos (lapse rate):\n\n"
        "```\n"
        "T(altitud) = T_referencia - lapse_rate * (altitud - altitud_ref) / 100\n"
        "lapse_rate tipico en paramos: 0.55 - 0.65 C/100m\n"
        "Rango altitudinal paramo: 3.000 - 4.700 m.s.n.m.\n"
        "```\n\n"
        "Esta relacion es util para:\n"
        "- Extrapolar temperatura a zonas sin estaciones de alta montana\n"
        "- Delimitar la franja de transicion bosque andino - paramo (~3.000 m)\n"
        "- Proyectar la franja de paramo bajo escenarios de calentamiento"
    )

    caldas_code = code(
        "# Gradiente Caldas-Lang: temperatura ~ altitud en paramo andino colombiano\n"
        "ALTITUDES = np.arange(2500, 4800, 100)  # m.s.n.m.\n"
        "LAPSE_RATE = 0.60  # C/100m — gradiente tipico paramo andino\n"
        "ALT_REF = 3000     # m.s.n.m. referencia\n"
        "T_REF = 12.5       # C en 3000 m (limite inferior paramo)\n"
        "\n"
        "T_teorico = T_REF - LAPSE_RATE * (ALTITUDES - ALT_REF) / 100\n"
        "\n"
        "# Simular estaciones reales con variabilidad\n"
        "np.random.seed(55)\n"
        "n_estaciones = 20\n"
        "alt_est = np.random.choice(ALTITUDES, n_estaciones)\n"
        "T_est   = T_REF - LAPSE_RATE * (alt_est - ALT_REF)/100 + np.random.normal(0, 0.8, n_estaciones)\n"
        "\n"
        "# Regresion lineal altitud-temperatura\n"
        "from numpy.polynomial import polynomial as P\n"
        "coef = np.polyfit(alt_est, T_est, 1)\n"
        "lapse_estimado = -coef[0] * 100  # C/100m\n"
        "\n"
        "fig, ax = plt.subplots(figsize=(9, 5))\n"
        "ax.plot(T_teorico, ALTITUDES, lw=2, color='#2980b9', label=f'Gradiente teorico ({LAPSE_RATE} C/100m)')\n"
        "ax.scatter(T_est, alt_est, color='#e74c3c', s=60, zorder=5, label='Estaciones IDEAM (simuladas)')\n"
        "T_fit = np.polyval(coef, ALTITUDES)\n"
        "ax.plot(T_fit, ALTITUDES, ls='--', color='#e74c3c', lw=1.5,\n"
        "        label=f'Ajuste empirico ({lapse_estimado:.2f} C/100m)')\n"
        "\n"
        "# Bandas altitudinales\n"
        "ax.axhspan(3000, 3500, alpha=0.08, color='#27ae60', label='Subparamo (3.000-3.500 m)')\n"
        "ax.axhspan(3500, 4200, alpha=0.08, color='#f1c40f', label='Paramo abierto (3.500-4.200 m)')\n"
        "ax.axhspan(4200, 4800, alpha=0.08, color='#3498db', label='Superparamo (>4.200 m)')\n"
        "\n"
        "ax.set_xlabel('Temperatura media (C)'); ax.set_ylabel('Altitud (m.s.n.m.)')\n"
        "ax.set_title('Relacion Caldas-Lang — Gradiente termico altitudinal en paramo andino',\n"
        "             fontweight='bold')\n"
        "ax.legend(fontsize=8, loc='upper right'); ax.grid(alpha=0.3)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "print(f'Gradiente empirico estimado: {lapse_estimado:.3f} C/100m')\n"
        "T_3500 = T_REF - LAPSE_RATE * (3500 - ALT_REF)/100\n"
        "T_4200 = T_REF - LAPSE_RATE * (4200 - ALT_REF)/100\n"
        "print(f'T estimada a 3.500 m: {T_3500:.1f} C | a 4.200 m: {T_4200:.1f} C')\n"
        "print(f'Con calentamiento +1.5C (escenario SSP2-4.5): franja paramo sube ~250 m')"
    )

    insert_after(cells, find_data(cells), [irh_md, irh_code])
    insert_after(cells, find_seasonal(cells), [irh_viz_md, irh_viz_code])
    insert_after(cells, find_mk(cells), [caldas_md, caldas_code])
