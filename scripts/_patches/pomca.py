"""Enrichment POMCA: OHDS, IUA, IRH, IVH (balance hidrico de la cuenca)."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_data,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "pomca"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    ohds_md = md(
        f"{marker(KEY)}\n\n"
        "## 1b. OHDS, IVH e indices POMCA — Balance hidrico de la cuenca\n\n"
        "El POMCA articula seis indices hidrologicos para el diagnostico y la zonificacion:\n\n"
        "| Indice | Formula simplificada | Umbral critico |\n"
        "|---|---|---|\n"
        "| **IUA** | Demanda_total / OHDS | IUA > 50% = alto estres hidrico |\n"
        "| **IRH** | Caudal_base / Caudal_total | IRH < 0.5 = baja regulacion |\n"
        "| **IVH** | f(IUA, IRH) | IVH > 3 = vulnerabilidad alta |\n"
        "| **ICA** | Agregado fisicoquimico | < 0.5 = calidad deficiente |\n"
        "| **IACAL** | Cargas_vertidas / OHDS | > 2 = alta presion contaminacion |\n"
        "| **OHDS** | Oferta_total - Caudal_ambiental | -- |\n\n"
        "**OHDS (Oferta Hidrica Disponible Superficial):** fraccion del caudal total que puede "
        "extraerse respetando el caudal ambiental (Estudio Nacional del Agua, IDEAM)."
    )

    ohds_code = code(
        "# Indices POMCA sinteticos: IUA, IRH, IVH, OHDS por subcuenca\n"
        "import numpy as np, pandas as pd\n"
        "np.random.seed(11)\n"
        "n_sub = 10\n"
        "subcuencas = [f'SC-{i+1:02d}' for i in range(n_sub)]\n"
        "\n"
        "oferta_total  = np.random.uniform(10, 200, n_sub)   # hm3/ano\n"
        "q_ambiental   = oferta_total * np.random.uniform(0.15, 0.30, n_sub)  # 15-30%\n"
        "ohds          = oferta_total - q_ambiental           # oferta disponible\n"
        "demanda_total = np.random.uniform(5, 180, n_sub)     # hm3/ano\n"
        "\n"
        "iua = np.clip(demanda_total / ohds * 100, 0, 200)    # %\n"
        "irh = np.random.uniform(0.3, 0.85, n_sub)            # indice regulacion\n"
        "\n"
        "# IVH: vulnerabilidad desabastecimiento (IDEAM: cruza IUA e IRH)\n"
        "def ivh_score(iua_v, irh_v):\n"
        "    iua_cat = 3 if iua_v > 50 else 2 if iua_v > 20 else 1\n"
        "    irh_cat = 3 if irh_v < 0.4 else 2 if irh_v < 0.6 else 1\n"
        "    return iua_cat + irh_cat  # 2=bajo, 3-4=medio, 5-6=alto\n"
        "\n"
        "ivh = np.array([ivh_score(iua[i], irh[i]) for i in range(n_sub)])\n"
        "ivh_cat = pd.cut(ivh, bins=[1,2,4,6], labels=['Bajo','Medio','Alto'])\n"
        "\n"
        "df_pomca_indices = pd.DataFrame({\n"
        "    'subcuenca': subcuencas, 'oferta_hm3': oferta_total.round(1),\n"
        "    'ohds_hm3': ohds.round(1), 'demanda_hm3': demanda_total.round(1),\n"
        "    'iua_pct': iua.round(1), 'irh': irh.round(3), 'ivh': ivh, 'ivh_cat': ivh_cat\n"
        "})\n"
        "\n"
        "print('Indices POMCA por subcuenca:')\n"
        "print(df_pomca_indices[['subcuenca','ohds_hm3','iua_pct','irh','ivh_cat']])\n"
        "print(f'\\nSubcuencas IUA > 50% (estres hidrico): {(iua > 50).sum()}/{n_sub}')\n"
        "print(f'Subcuencas IVH Alto (vulnerabilidad desabastecimiento): {(ivh >= 5).sum()}/{n_sub}')"
    )

    insert_after(cells, find_data(cells), [ohds_md, ohds_code])
