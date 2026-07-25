"""Enrichment oferta_hidrica: piezometria, Theis/Cooper-Jacob, Kriging, MODFLOW."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_data,
    find_seasonal,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "oferta_hidrica"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    piezo_md = md(
        f"{marker(KEY)}\n\n"
        "## 1b. Hidrogeologia: Piezometria, transmisividad y curva de abatimiento\n\n"
        "El inventario FUNIAS levanta los parametros clave del acuifero por pozo:\n\n"
        "| Parametro | Simbolo | Unidad | Rango tipico |\n"
        "|---|---|---|---|\n"
        "| Nivel estatico | Ne | m | 3 - 30 m |\n"
        "| Nivel dinamico | Nd | m | > Ne |\n"
        "| Transmisividad | T | m2/dia | 10 - 5000 m2/dia |\n"
        "| Caudal extraccion | Q | L/s | 1 - 50+ L/s |\n\n"
        "**Ecuacion de Theis** (bombeo a largo plazo, sin recarga):\n"
        "```\n"
        "s(r,t) = Q/(4*pi*T) * W(u)       u = r^2*S/(4*T*t)\n"
        "```\n"
        "Donde W(u) = funcion de pozo (well function), r = distancia al pozo (m), "
        "S = coeficiente de almacenamiento (adim), t = tiempo (dias).\n\n"
        "**Kriging Empirico Bayesiano (EBK):** mejor opcion para mapas de isopiezas "
        "porque estima la varianza del modelo variografico en lugar de asumirla fija.\n\n"
        "**MODFLOW** (USGS): modelo de diferencias finitas para simular el acuifero en 3D; "
        "se conecta a Python mediante `flopy`."
    )

    piezo_code = code(
        "# Inventario FUNIAS sintetico + curva de abatimiento (Theis) + Kriging\n"
        "np.random.seed(33)\n"
        "n_pozos = 25\n"
        "\n"
        "# Inventario FUNIAS (pozos del acuifero)\n"
        "df_pozos = pd.DataFrame({\n"
        "    'pozo_id': [f'PZ-{i+1:03d}' for i in range(n_pozos)],\n"
        "    'ne_m': np.random.uniform(3, 25, n_pozos).round(1),        # nivel estatico\n"
        "    'q_ls': np.random.uniform(1, 40, n_pozos).round(1),         # caudal extraccion\n"
        "    'transmisiv': np.random.lognormal(4, 1, n_pozos).round(1),  # m2/dia\n"
        "    'lat': np.random.uniform(4.5, 6.5, n_pozos),                # lat Colombia\n"
        "    'lon': np.random.uniform(-75.5, -73.5, n_pozos),            # lon Colombia\n"
        "})\n"
        "df_pozos['nivel_piezom'] = df_pozos['ne_m'] + np.random.uniform(50, 200, n_pozos)  # cota\n"
        "\n"
        "# Curva de abatimiento Theis para pozo representativo\n"
        "Q_bomba = 10.0    # L/s = 0.01 m3/s\n"
        "T_trans = 150.0   # m2/dia (transmisividad tipica)\n"
        "S_almac = 0.001   # coeficiente almacenamiento (acuifero confinado)\n"
        "r_obs = 50.0      # m distancia pozo de observacion\n"
        "t_dias = np.logspace(-2, 2, 200)  # 0.01 a 100 dias\n"
        "\n"
        "# Aproximacion Cooper-Jacob (valida para u < 0.05)\n"
        "u = r_obs**2 * S_almac / (4 * T_trans * t_dias)\n"
        "abatim = np.where(u < 0.05,\n"
        "    (Q_bomba * 86.4) / (4 * np.pi * T_trans) * (-0.5772 - np.log(u)),\n"
        "    np.nan)\n"
        "\n"
        "print(f'Inventario FUNIAS: {n_pozos} pozos')\n"
        "print(f'Transmisividad | mediana={df_pozos[\"transmisiv\"].median():.1f} m2/dia')\n"
        "print(f'Caudal medio extraccion: {df_pozos[\"q_ls\"].mean():.1f} L/s')\n"
        "print(f'Abatimiento maximo en r={r_obs}m despues de 100 dias: {np.nanmax(abatim):.2f} m')\n"
        "print()\n"
        "print('Para mapa de isopiezas: usar pykrige.OrdinaryKriging o EmpiricalBayesianKriging')\n"
        "print('Para modelo MODFLOW 3D: flopy.modflow (USGS) con Python/FloPy')\n"
        "df_pozos[['pozo_id','ne_m','q_ls','transmisiv','nivel_piezom']].head(10)"
    )

    piezo_viz_md = md(
        "## 3c. Mapa de isopiezas y curva de abatimiento — Kriging + Theis\n\n"
        "El mapa de isopiezas (lineas de igual carga hidraulica) muestra la direccion del flujo "
        "subterraneo y permite identificar zonas de recarga (valores altos) y descarga (valores bajos). "
        "Se genera con **Kriging Ordinario** o **EBK** sobre los niveles piezometricos de los pozos FUNIAS."
    )

    piezo_viz_code = code(
        "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))\n"
        "\n"
        "# Panel A: Dispersion de pozos FUNIAS + nivel piezometrico (proxy mapa isopiezas)\n"
        "sc = ax1.scatter(df_pozos['lon'], df_pozos['lat'],\n"
        "                 c=df_pozos['nivel_piezom'], cmap='Blues_r', s=60, alpha=0.85, edgecolors='gray')\n"
        "plt.colorbar(sc, ax=ax1, label='Nivel piezometrico (m.s.n.m.)')\n"
        "ax1.set_xlabel('Longitud'); ax1.set_ylabel('Latitud')\n"
        "ax1.set_title('Pozos FUNIAS — Mapa de isopiezas\\n(Kriging EBK con pykrige)', fontweight='bold')\n"
        "ax1.grid(alpha=0.3)\n"
        "# Anotar pozos con mayor transmisividad\n"
        "top3 = df_pozos.nlargest(3, 'transmisiv')\n"
        "for _, row in top3.iterrows():\n"
        "    ax1.annotate(f\"{row['pozo_id']}\\nT={row['transmisiv']:.0f}\",\n"
        "                 (row['lon'], row['lat']), fontsize=6, color='darkblue')\n"
        "\n"
        "# Panel B: Curva de abatimiento Theis / Cooper-Jacob\n"
        "ax2.semilogx(t_dias, abatim, lw=2, color='#e74c3c', label=f'Abatimiento r={r_obs}m')\n"
        "ax2.axhline(5.0, color='orange', ls='--', lw=1.5, label='Umbral abatim. 5m (alerta)')\n"
        "ax2.axhline(10.0, color='red', ls='--', lw=1.5, label='Umbral abatim. 10m (critico)')\n"
        "ax2.set_xlabel('Tiempo de bombeo (dias, escala log)')\n"
        "ax2.set_ylabel('Abatimiento (m)')\n"
        "ax2.set_title(f'Curva abatimiento Theis/Cooper-Jacob\\nQ={Q_bomba} L/s, T={T_trans} m2/dia', fontweight='bold')\n"
        "ax2.legend(fontsize=8); ax2.grid(alpha=0.3)\n"
        "\n"
        "plt.suptitle('Hidrogeologia — FUNIAS + Theis + Kriging (MODFLOW/FloPy para modelo 3D)',\n"
        "             fontweight='bold', fontsize=11)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "t_alerta = t_dias[np.nanargmax(abatim >= 5.0)] if (abatim >= 5.0).any() else None\n"
        "if t_alerta:\n"
        "    print(f'Abatimiento supera 5m despues de {t_alerta:.1f} dias de bombeo')"
    )

    insert_after(cells, find_data(cells), [piezo_md, piezo_code])
    insert_after(cells, find_seasonal(cells), [piezo_viz_md, piezo_viz_code])
