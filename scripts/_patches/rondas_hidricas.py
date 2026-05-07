"""Enrichment rondas_hidricas: HAND + analisis de frecuencia Gumbel."""

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

KEY = "rondas_hidricas"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    hand_md = md(
        f"{marker(KEY)}\n\n"
        "## 3c. HAND y analisis de frecuencia — Delimitacion de ronda hidrica\n\n"
        "El **HAND (Height Above Nearest Drainage)** es un indice geomorfometrico derivado del DEM "
        "que expresa la diferencia de elevacion entre cada celda y el drenaje mas cercano. "
        "Es la herramienta central para el acotamiento funcional de rondas hidricas (Res. 957/2018):\n\n"
        "```\n"
        "HAND(x,y) = elevacion(x,y) - elevacion(drenaje_mas_cercano)\n"
        "HAND = 0    : cauce permanente\n"
        "HAND < 1m   : zona inundacion banca llena (ordinaria)\n"
        "HAND < Tr100: zona de flujo preferente (inundacion 100 anos)\n"
        "```\n\n"
        "Herramientas: **WhiteboxTools** (algoritmo D8 para red drenaje + HAND) o TauDEM.\n\n"
        "**Analisis de frecuencia de caudales maximos (Gumbel):**\n"
        "```\n"
        "F(Q) = exp(-exp(-y))    y = (Q - alpha) / beta\n"
        "Caudal_Tr = alpha - beta * ln(-ln(1 - 1/Tr))\n"
        "```"
    )

    hand_code = code(
        "# HAND conceptual + analisis frecuencia Gumbel para caudales maximos\n"
        "from scipy import stats\n"
        "np.random.seed(9)\n"
        "\n"
        "# -- Simulacion HAND transecto de rio (perfil transversal) ----------------\n"
        "distancia_m = np.linspace(-200, 200, 400)   # m desde el cauce\n"
        "# Perfil topografico sintetico (valle en V con llanura)\n"
        "hand_perfil = np.where(\n"
        "    np.abs(distancia_m) < 30,\n"
        "    np.abs(distancia_m) * 0.05,             # cauce y zona banca llena\n"
        "    0.05 * 30 + (np.abs(distancia_m) - 30) * 0.04  # ladera\n"
        ") + np.random.normal(0, 0.1, 400)\n"
        "hand_perfil = np.clip(hand_perfil, 0, None)\n"
        "\n"
        "# Umbrales HAND para ronda hidrica\n"
        "HAND_BANCA_LLENA = 0.5  # m — inundacion ordinaria\n"
        "HAND_TR15 = 1.8         # m — periodo retorno 15 anos\n"
        "HAND_TR100 = 4.2        # m — periodo retorno 100 anos (zona flujo preferente)\n"
        "\n"
        "# -- Analisis frecuencia Gumbel sobre caudales maximos anuales ------------\n"
        "n_anos = 35\n"
        "q_max_anual = np.random.gumbel(loc=80, scale=25, size=n_anos).clip(20)  # m3/s\n"
        "\n"
        "# Ajuste Gumbel (metodo momentos)\n"
        "alpha_g = q_max_anual.std() * np.sqrt(6) / np.pi\n"
        "beta_g  = q_max_anual.mean() - 0.5772 * alpha_g\n"
        "\n"
        "Tr_periodos = [2, 5, 10, 25, 50, 100]\n"
        "q_tr = [beta_g - alpha_g * np.log(-np.log(1 - 1/tr)) for tr in Tr_periodos]\n"
        "df_gumbel = pd.DataFrame({'Tr_anos': Tr_periodos, 'Q_m3s': [round(q,2) for q in q_tr]})\n"
        "\n"
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
        "\n"
        "# Panel A: Perfil HAND transecto\n"
        "ax = axes[0]\n"
        "ax.fill_between(distancia_m, hand_perfil, alpha=0.3, color='#8B4513')\n"
        "ax.plot(distancia_m, hand_perfil, color='#8B4513', lw=1)\n"
        "ax.axhline(HAND_BANCA_LLENA, color='#3498db', ls='-', lw=2, label=f'Banca llena (HAND={HAND_BANCA_LLENA}m)')\n"
        "ax.axhline(HAND_TR15, color='orange', ls='--', lw=1.5, label=f'Tr=15 anos (HAND={HAND_TR15}m)')\n"
        "ax.axhline(HAND_TR100, color='red', ls='--', lw=1.5, label=f'Tr=100 anos/ronda hidrica (HAND={HAND_TR100}m)')\n"
        "ax.set_xlabel('Distancia al cauce (m)'); ax.set_ylabel('HAND (m)')\n"
        "ax.set_title('HAND — Perfil transversal ronda hidrica\\n(WhiteboxTools D8, Res. 957/2018)', fontweight='bold')\n"
        "ax.legend(fontsize=8); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel B: Curva de frecuencia Gumbel\n"
        "ax = axes[1]\n"
        "Tr_cont = np.linspace(1.1, 200, 500)\n"
        "q_cont = beta_g - alpha_g * np.log(-np.log(1 - 1/Tr_cont))\n"
        "ax.plot(Tr_cont, q_cont, lw=2, color='#2980b9', label='Ajuste Gumbel')\n"
        "ax.scatter([r['Tr_anos'] for _, r in df_gumbel.iterrows()],\n"
        "           [r['Q_m3s'] for _, r in df_gumbel.iterrows()],\n"
        "           color='red', zorder=5, s=60, label='Tr de diseno')\n"
        "ax.axvline(100, color='red', ls='--', lw=1.5, label='Tr=100 anos (ronda hidrica)')\n"
        "ax.axvline(15, color='orange', ls='--', lw=1, label='Tr=15 anos (Res. 957/2018)')\n"
        "ax.set_xscale('log')\n"
        "ax.set_xlabel('Periodo de retorno Tr (anos, log)'); ax.set_ylabel('Caudal maximo (m3/s)')\n"
        "ax.set_title('Analisis frecuencia Gumbel — Caudales maximos\\nRonda hidrica: zona de flujo preferente Tr=100', fontweight='bold')\n"
        "ax.legend(fontsize=7); ax.grid(alpha=0.3)\n"
        "\n"
        "plt.tight_layout(); plt.show()\n"
        "print('Caudales de diseno por periodo de retorno:')\n"
        "print(df_gumbel.to_string(index=False))"
    )

    insert_after(cells, find_seasonal(cells), [hand_md, hand_code])
