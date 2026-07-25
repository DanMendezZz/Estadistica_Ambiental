"""Enrichment recurso_hidrico: capacidad de asimilacion + Streeter-Phelps/QUAL2K."""

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

KEY = "recurso_hidrico"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    qual_md = md(
        f"{marker(KEY)}\n\n"
        "## 3c. Capacidad de asimilacion y modelo de calidad QUAL2K\n\n"
        "La **capacidad de asimilacion** es la cantidad de carga contaminante que un rio "
        "puede recibir sin superar los objetivos de calidad del PORH (Res. 0751/2018).\n\n"
        "El modelo **Streeter-Phelps** (base de QUAL2K/QUAL2Kw) describe el deficit de OD:\n\n"
        "```\n"
        "DBO(x) = DBO0 * exp(-Kd * x/U)            Kd = tasa descomposicion (1/dia)\n"
        "OD_deficit(x) = Dc * exp(-Ka * x/U)       Ka = tasa reaireacion (1/dia)\n"
        "               - (Kd*DBO0)/(Ka-Kd) * [exp(-Kd*x/U) - exp(-Ka*x/U)]\n"
        "Donde U = velocidad media del rio (m/s), x = distancia aguas abajo (km)\n"
        "```\n\n"
        "**QUAL2K** extiende este modelo con temperatura, nitrificacion, algas y sedimentos. "
        "Implementacion Python: `qual2kpy` o manual con ODE de scipy.\n\n"
        "> **BMWP-Col (macroinvertebrados):** bioindicador biologico obligatorio en el diagnostico "
        "del PORH, complementa el ICA fisicoquimico con informacion de la calidad ecologica del agua."
    )

    qual_code = code(
        "# Modelo Streeter-Phelps simplificado — perfil DBO y deficit de OD aguas abajo\n"
        "# Simula la capacidad de asimilacion de un rio receptor de vertimiento\n"
        "\n"
        "# Parametros del cuerpo de agua (rio andino tipico)\n"
        "Q_rio = 5.0       # m3/s caudal receptor\n"
        "U_vel = 0.4       # m/s velocidad media\n"
        "OD_sat = 8.5      # mg/L saturacion OD (a ~1500 msnm)\n"
        "OD_ini = 6.2      # mg/L OD aguas arriba del vertimiento\n"
        "Kd = 0.25         # 1/dia tasa descomposicion DBO\n"
        "Ka = 0.80         # 1/dia tasa reaireacion (K2)\n"
        "\n"
        "# Vertimiento (punto de descarga PTAR municipal)\n"
        "Q_vert = 0.15     # m3/s caudal vertido\n"
        "DBO_vert = 180    # mg/L DBO5 del vertimiento\n"
        "OD_vert = 1.0     # mg/L OD del vertimiento\n"
        "\n"
        "# Mezcla inmediata aguas abajo del punto de descarga\n"
        "DBO_mix = (Q_rio * 2.0 + Q_vert * DBO_vert) / (Q_rio + Q_vert)  # 2.0 mg/L DBO rio\n"
        "OD_mix  = (Q_rio * OD_ini + Q_vert * OD_vert) / (Q_rio + Q_vert)\n"
        "Dc_ini  = OD_sat - OD_mix  # deficit inicial\n"
        "\n"
        "# Perfil a lo largo del rio (0 a 80 km)\n"
        "x_km = np.linspace(0, 80, 200)\n"
        "t = x_km * 1000 / (U_vel * 86400)  # dias de viaje\n"
        "\n"
        "DBO_x = DBO_mix * np.exp(-Kd * t)\n"
        "def_od = (Dc_ini * np.exp(-Ka * t)\n"
        "          - (Kd * DBO_mix) / (Ka - Kd) * (np.exp(-Kd * t) - np.exp(-Ka * t)))\n"
        "OD_x = np.clip(OD_sat - def_od, 0, OD_sat)\n"
        "\n"
        "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))\n"
        "\n"
        "ax1.plot(x_km, DBO_x, lw=2, color='#e74c3c', label='DBO5 (mg/L)')\n"
        "ax1.axhline(5, color='orange', ls='--', lw=1.5, label='Objetivo calidad PORH DBO=5')\n"
        "x_meta_dbo = x_km[DBO_x < 5][0] if (DBO_x < 5).any() else 80\n"
        "ax1.axvline(x_meta_dbo, color='gray', ls=':', lw=1)\n"
        "ax1.set_xlabel('Distancia aguas abajo (km)'); ax1.set_ylabel('DBO5 (mg/L)')\n"
        "ax1.set_title('Perfil DBO — Streeter-Phelps (base QUAL2K)', fontweight='bold')\n"
        "ax1.legend(fontsize=8); ax1.grid(alpha=0.3)\n"
        "\n"
        "ax2.plot(x_km, OD_x, lw=2, color='#2980b9', label='OD (mg/L)')\n"
        "ax2.axhline(4.0, color='red', ls='--', lw=1.5, label='Minimo OD uso piscicola=4 mg/L')\n"
        "ax2.axhline(OD_sat, color='green', ls=':', lw=1, label=f'OD saturacion={OD_sat}')\n"
        "od_min_km = x_km[OD_x.argmin()]\n"
        "ax2.axvline(od_min_km, color='gray', ls=':', lw=1, label=f'Minimo OD en {od_min_km:.1f} km')\n"
        "ax2.set_xlabel('Distancia aguas abajo (km)'); ax2.set_ylabel('OD (mg/L)')\n"
        "ax2.set_title('Deficit de OD — Curva de sagging (capacidad asimilacion)', fontweight='bold')\n"
        "ax2.legend(fontsize=7); ax2.grid(alpha=0.3)\n"
        "\n"
        "plt.suptitle('Modelo QUAL2K simplificado — PORH (Res. 0751/2018 MADS)',\n"
        "             fontweight='bold', fontsize=11)\n"
        "plt.tight_layout(); plt.show()\n"
        "\n"
        "od_min = OD_x.min()\n"
        "print(f'OD minimo: {od_min:.2f} mg/L a {od_min_km:.1f} km del vertimiento')\n"
        "print(f'DBO5 cumple objetivo (< 5 mg/L) a partir de: {x_meta_dbo:.1f} km')\n"
        "print(f'Capacidad asimilacion: Q_rio={Q_rio} m3/s puede asimilar ~{Q_vert*DBO_vert:.0f} g/s DBO')\n"
        "print('BMWP-Col recomendado en km 0, 10, 30 y 60 para validar el modelo')"
    )

    insert_after(cells, find_seasonal(cells), [qual_md, qual_code])
