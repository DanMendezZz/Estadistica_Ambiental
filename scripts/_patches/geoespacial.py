"""Enrichment geoespacial: NDWI / MNDWI deteccion espejo de agua Sentinel-2.

Notable: este enrichment NO sigue el patrón estándar (find_data, find_seasonal, etc.).
El notebook de geoespacial está estructurado por casos de uso y la celda ancla
es la que llama a `getis_ord_g`. Tampoco se aplica fix_walk_forward_gap porque
el notebook geoespacial no usa walk_forward."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_first,
    insert_after,
    marker,
    md,
)

KEY = "geoespacial"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    ndwi_md = md(
        f"{marker(KEY)}\n\n"
        "---\n\n"
        "## Caso 5 — NDWI y MNDWI: Deteccion de espejo de agua con Sentinel-2\n\n"
        "Los indices de agua permiten extraer cuerpos de agua de imagenes multiespectrales "
        "sin clasificacion supervisada:\n\n"
        "| Indice | Formula | Bandas Sentinel-2 | Umbral agua |\n"
        "|---|---|---|---|\n"
        "| **NDWI** (McFeeters) | (Green - NIR) / (Green + NIR) | B3 / B8 | > 0 |\n"
        "| **MNDWI** (Xu 2006) | (Green - SWIR) / (Green + SWIR) | B3 / B11 | > 0 |\n"
        "| **AWEI** | 4*(Green-SWIR1) - (0.25*NIR+2.75*SWIR2) | B3/B11/B8/B12 | > 0 |\n\n"
        "**NDWI** es sensible a la turbidez; **MNDWI** es mas robusto en zonas urbanas "
        "y humedales someros porque suprime mejor la respuesta de suelo desnudo y edificios.\n\n"
        "> En humedales colombianos: usar MNDWI sobre Sentinel-2 L2A (correccion atmosferica), "
        "mascara de nubes SCL (escena de clasificacion de escena) y combinacion con Sentinel-1 SAR "
        "para periodos nublados (Amazonia/Pacifico)."
    )

    ndwi_code = code(
        "# NDWI y MNDWI simulados: comparacion de indices de agua\n"
        "np.random.seed(42)\n"
        "\n"
        "# Simular una imagen de 100x100 pixeles con distintas coberturas\n"
        "n_pix = 10000\n"
        "# Reflectancias Sentinel-2 L2A por cobertura (valores tipicos 0-1)\n"
        "coberturas = {\n"
        "    'Agua profunda':   {'green': 0.03, 'nir': 0.01, 'swir1': 0.005},\n"
        "    'Agua turbia':     {'green': 0.06, 'nir': 0.04, 'swir1': 0.03},\n"
        "    'Vegetacion':      {'green': 0.10, 'nir': 0.35, 'swir1': 0.15},\n"
        "    'Suelo desnudo':   {'green': 0.15, 'nir': 0.22, 'swir1': 0.20},\n"
        "    'Area urbana':     {'green': 0.18, 'nir': 0.20, 'swir1': 0.18},\n"
        "    'Nieve/hielo':     {'green': 0.45, 'nir': 0.40, 'swir1': 0.10},\n"
        "}\n"
        "\n"
        "n_por_cob = n_pix // len(coberturas)\n"
        "all_green, all_nir, all_swir1, all_labels = [], [], [], []\n"
        "for nombre, vals in coberturas.items():\n"
        "    noise = np.random.normal(0, 0.005, n_por_cob)\n"
        "    all_green.append(np.clip(vals['green'] + noise, 0, 1))\n"
        "    all_nir.append(np.clip(vals['nir'] + noise, 0, 1))\n"
        "    all_swir1.append(np.clip(vals['swir1'] + noise, 0, 1))\n"
        "    all_labels.extend([nombre] * n_por_cob)\n"
        "\n"
        "green = np.concatenate(all_green)\n"
        "nir   = np.concatenate(all_nir)\n"
        "swir1 = np.concatenate(all_swir1)\n"
        "\n"
        "ndwi  = (green - nir)   / (green + nir  + 1e-8)   # NDWI McFeeters\n"
        "mndwi = (green - swir1) / (green + swir1 + 1e-8)  # MNDWI Xu\n"
        "\n"
        "df_indices = pd.DataFrame({\n"
        "    'cobertura': all_labels, 'green': green, 'nir': nir,\n"
        "    'swir1': swir1, 'ndwi': ndwi, 'mndwi': mndwi\n"
        "})\n"
        "\n"
        "fig, axes = plt.subplots(1, 3, figsize=(16, 4))\n"
        "\n"
        "# Panel A: Distribucion NDWI por cobertura\n"
        "ax = axes[0]\n"
        "for cob in coberturas.keys():\n"
        "    sub = df_indices[df_indices['cobertura'] == cob]['ndwi']\n"
        "    ax.boxplot(sub, positions=[list(coberturas).index(cob)],\n"
        "              widths=0.6, patch_artist=True,\n"
        "              boxprops=dict(facecolor='#3498db', alpha=0.6))\n"
        "ax.axhline(0, color='red', ls='--', lw=1.5, label='Umbral agua NDWI=0')\n"
        "ax.set_xticks(range(len(coberturas)))\n"
        "ax.set_xticklabels(coberturas.keys(), rotation=30, ha='right', fontsize=8)\n"
        "ax.set_title('NDWI (McFeeters) por cobertura', fontweight='bold')\n"
        "ax.set_ylabel('NDWI'); ax.legend(fontsize=8); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel B: Comparacion NDWI vs MNDWI\n"
        "ax = axes[1]\n"
        "colors_cob = ['#1a73e8','#27ae60','#e67e22','#e74c3c','#9b59b6','#f1c40f']\n"
        "for cob, color in zip(coberturas.keys(), colors_cob):\n"
        "    sub = df_indices[df_indices['cobertura'] == cob]\n"
        "    ax.scatter(sub['ndwi'].sample(100, random_state=1), sub['mndwi'].sample(100, random_state=1),\n"
        "               c=color, alpha=0.5, s=15, label=cob)\n"
        "ax.axhline(0, color='gray', ls='--', lw=1); ax.axvline(0, color='gray', ls='--', lw=1)\n"
        "ax.set_xlabel('NDWI'); ax.set_ylabel('MNDWI')\n"
        "ax.set_title('NDWI vs MNDWI — separacion coberturas\\n(Sentinel-2, CTM12 EPSG:9377)', fontweight='bold')\n"
        "ax.legend(fontsize=6, ncol=2); ax.grid(alpha=0.3)\n"
        "\n"
        "# Panel C: Precision deteccion agua (NDWI vs MNDWI)\n"
        "ax = axes[2]\n"
        "es_agua = df_indices['cobertura'].str.contains('Agua').astype(int)\n"
        "ndwi_agua = (ndwi > 0).astype(int)\n"
        "mndwi_agua = (mndwi > 0).astype(int)\n"
        "prec_ndwi  = (ndwi_agua == es_agua).mean()\n"
        "prec_mndwi = (mndwi_agua == es_agua).mean()\n"
        "ax.bar(['NDWI\\n(McFeeters)','MNDWI\\n(Xu 2006)'], [prec_ndwi, prec_mndwi],\n"
        "       color=['#3498db','#27ae60'], alpha=0.85, width=0.5)\n"
        "ax.set_ylim(0, 1); ax.set_ylabel('Exactitud global')\n"
        "ax.set_title('Precision deteccion agua\\nNDWI vs MNDWI (umbral=0)', fontweight='bold')\n"
        "for i, v in enumerate([prec_ndwi, prec_mndwi]):\n"
        "    ax.text(i, v + 0.01, f'{v:.3f}', ha='center', fontweight='bold')\n"
        "ax.grid(axis='y', alpha=0.3)\n"
        "\n"
        "plt.suptitle('NDWI/MNDWI — Extraccion espejo de agua Sentinel-2 (EPSG:9377 para areas)',\n"
        "             fontweight='bold', fontsize=11)\n"
        "plt.tight_layout(); plt.show()\n"
        "print(f'Exactitud NDWI: {prec_ndwi:.3f} | MNDWI: {prec_mndwi:.3f}')\n"
        "print('MNDWI recomendado en humedales urbanos y turbios (menor confusion suelo/agua)')"
    )

    # Si no encuentra getis_ord_g, no aplicar (evitar StopIteration en notebooks
    # generados de cero por build_notebooks.py — esos no tienen el caso 4).
    try:
        anchor_idx = find_first(cells, "getis_ord_g")
    except StopIteration:
        return

    insert_after(cells, anchor_idx, [ndwi_md, ndwi_code])
