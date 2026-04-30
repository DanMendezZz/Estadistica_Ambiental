"""Patch ordenamiento_territorial.ipynb: agrega EEP, IACAL, SARAR."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/ordenamiento_territorial.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

# -- Seccion 1b: EEP + TCCN + IACAL ------------------------------------------
eep_md = md(
    "## 1b. Estructura Ecologica Principal (EEP) e indicadores de presion territorial\n\n"
    "La **EEP** es el conjunto de areas y ecosistemas estrategicos que sostienen los procesos "
    "ecologicos del territorio. Es la base para la zonificacion ambiental en el POT (Ley 388/1997).\n\n"
    "| Componente EEP | Norma | Funcion |\n"
    "|---|---|---|\n"
    "| Paramos | Ley 1930/2018 | Regulacion hidrica, provision agua |\n"
    "| Humedales | Ley 357/1997 (Ramsar) | Regulacion hidrica, biodiversidad |\n"
    "| Rondas hidricas | Res. 957/2018 | Proteccion cauces, zonas de inundacion |\n"
    "| Areas Protegidas | Decreto 1076/2015 | Conservacion biodiversidad |\n\n"
    "**Indicadores de presion:**\n"
    "- **TCCN (Tasa de Cambio de Coberturas Naturales):** perdida anual en % de ecosistemas estrategicos\n"
    "- **IACAL (Indice de Alteracion Potencial de la Calidad del Agua):** presion por vertimientos\n"
    "- **IACAL formula:** Cargas_contaminantes_vertidas / Oferta_hidrica_disponible"
)

eep_code = code(
    "# EEP sintetica + TCCN + IACAL por municipio\n"
    "np.random.seed(55)\n"
    "n = len(df)\n"
    "\n"
    "# Coberturas EEP (ha) -- tendencia decreciente por expansion urbana/agricola\n"
    "componentes_eep = ['Paramo', 'Humedal', 'Bosque_Andino', 'Ronda_Hidrica']\n"
    "n_muni = 12\n"
    "municipios = [f'Mpio-{i+1:02d}' for i in range(n_muni)]\n"
    "ha_eep = {\n"
    "    comp: np.random.uniform(100, 5000, n_muni)\n"
    "    for comp in componentes_eep\n"
    "}\n"
    "df_eep = pd.DataFrame({'municipio': municipios, **ha_eep})\n"
    "df_eep['total_eep_ha'] = df_eep[componentes_eep].sum(axis=1)\n"
    "\n"
    "# TCCN: tasa de cambio de coberturas naturales (%/ano)\n"
    "df_eep['tccn_pct'] = np.random.uniform(-3.5, -0.2, n_muni).round(2)  # negativo = perdida\n"
    "\n"
    "# IACAL: cargas vertimientos / oferta hidrica (0-1 bajo; >2 critico)\n"
    "carga_dbo_ton = np.random.uniform(50, 800, n_muni)  # ton DBO/ano\n"
    "oferta_hm3 = np.random.uniform(5, 200, n_muni)     # hm3/ano\n"
    "df_eep['iacal'] = (carga_dbo_ton / oferta_hm3).round(3)\n"
    "\n"
    "def iacal_cat(v):\n"
    "    if v < 0.1: return 'Muy bajo'\n"
    "    if v < 1.0: return 'Bajo'\n"
    "    if v < 2.0: return 'Medio'\n"
    "    if v < 5.0: return 'Alto'\n"
    "    return 'Muy alto'\n"
    "\n"
    "df_eep['iacal_cat'] = df_eep['iacal'].apply(iacal_cat)\n"
    "\n"
    "from estadistica_ambiental.config import IUA_THRESHOLDS\n"
    "print('IUA_THRESHOLDS (referencia para IACAL):', IUA_THRESHOLDS)\n"
    "print(f'\\nIACAL | min={df_eep[\"iacal\"].min():.3f} max={df_eep[\"iacal\"].max():.3f}')\n"
    "print(f'Municipios IACAL Alto/Muy Alto: {(df_eep[\"iacal\"] >= 2).sum()}/{n_muni}')\n"
    "print(f'TCCN promedio: {df_eep[\"tccn_pct\"].mean():.2f}%/ano (negativo = perdida coberturas)')\n"
    "df_eep[['municipio','total_eep_ha','tccn_pct','iacal','iacal_cat']]"
)

# -- Seccion 3c: IACAL dashboard + SARAR conceptual ---------------------------
iacal_md = md(
    "## 3c. IACAL y Estructura Ecologica Principal — Dashboard territorial\n\n"
    "La econometria espacial con **modelos SARAR** (Spatial AutoRegressive with AutoRegressive "
    "disturbances) permite modelar como la presion territorial en un municipio afecta a sus vecinos:\n\n"
    "```\n"
    "y = rho * W * y + X * beta + u      (SAR: autocorrelacion en y)\n"
    "u = lambda * W * u + e              (AR: autocorrelacion en errores)\n"
    "```\n\n"
    "Donde W = matriz de contigüedad espacial (reina/torre). "
    "Implementacion en Python: `spreg.GM_Combo` de `pysal/spreg`.\n\n"
    "> Un IACAL alto en un municipio genera externalidades hidricas negativas aguas abajo "
    "(efecto autocorrelacion espacial positiva). Esto justifica el enfoque cuencal del POMCA."
)

iacal_code = code(
    "IACAL_COLORS = {'Muy bajo':'#27ae60','Bajo':'#82e0aa','Medio':'#f1c40f',\n"
    "                'Alto':'#e67e22','Muy alto':'#e74c3c'}\n"
    "\n"
    "fig, axes = plt.subplots(1, 3, figsize=(16, 5))\n"
    "\n"
    "# Panel A: IACAL por municipio\n"
    "ax = axes[0]\n"
    "bar_colors = df_eep['iacal_cat'].map(IACAL_COLORS)\n"
    "ax.barh(df_eep['municipio'], df_eep['iacal'], color=bar_colors, alpha=0.85)\n"
    "ax.axvline(2.0, color='red', ls='--', lw=1.5, label='Umbral alto IACAL=2')\n"
    "ax.set_title('IACAL — Alteracion Potencial Calidad Agua', fontweight='bold')\n"
    "ax.set_xlabel('IACAL (carga/oferta)'); ax.legend(fontsize=7); ax.grid(axis='x', alpha=0.3)\n"
    "\n"
    "# Panel B: Composicion EEP por municipio\n"
    "ax = axes[1]\n"
    "bottom = np.zeros(n_muni)\n"
    "colors_eep = ['#1a73e8','#27ae60','#82e0aa','#f1c40f']\n"
    "for comp, color in zip(componentes_eep, colors_eep):\n"
    "    ax.bar(range(n_muni), df_eep[comp], bottom=bottom, color=color, alpha=0.85, label=comp)\n"
    "    bottom += df_eep[comp].values\n"
    "ax.set_xticks(range(n_muni)); ax.set_xticklabels(df_eep['municipio'], rotation=45, ha='right', fontsize=7)\n"
    "ax.set_title('Composicion EEP por Municipio (ha)', fontweight='bold')\n"
    "ax.set_ylabel('Hectareas'); ax.legend(fontsize=7); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "# Panel C: TCCN vs IACAL\n"
    "ax = axes[2]\n"
    "sc = ax.scatter(df_eep['tccn_pct'], df_eep['iacal'],\n"
    "                c=df_eep['iacal_cat'].map(IACAL_COLORS), s=80, alpha=0.8, edgecolors='gray')\n"
    "ax.axhline(2.0, color='red', ls='--', lw=1)\n"
    "ax.axvline(-2.0, color='orange', ls='--', lw=1)\n"
    "ax.set_xlabel('TCCN (%/ano)'); ax.set_ylabel('IACAL')\n"
    "ax.set_title('Presion territorial: TCCN vs IACAL\\n(SARAR: efecto espacial sobre cuenca)', fontweight='bold')\n"
    "for _, r in df_eep.iterrows():\n"
    "    ax.annotate(r['municipio'], (r['tccn_pct'], r['iacal']), fontsize=6)\n"
    "ax.grid(alpha=0.3)\n"
    "\n"
    "plt.suptitle('EEP + IACAL + TCCN — Determinantes ambientales POT (Ley 388/1997)',\n"
    "             fontweight='bold', fontsize=11)\n"
    "plt.tight_layout(); plt.show()\n"
    "\n"
    "print('Modelo SARAR (spreg.GM_Combo) requiere: pip install spreg')\n"
    "print(f'Municipios EEP < 500 ha total: {(df_eep[\"total_eep_ha\"] < 500).sum()} — prioridad restauracion')"
)

# -- Fix walk_forward gap --
for i, c in enumerate(cells):
    src = "".join(c["source"])
    if c["cell_type"] == "code" and "walk_forward(model, ts" in src and "gap=" not in src:
        cells[i]["source"] = src.replace(
            "walk_forward(model, ts, horizon=",
            "walk_forward(model, ts, gap=12, horizon="
        )

# -- Insertar celdas --
idx_data = next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code" and "sintéticos de ejemplo" in "".join(c["source"]))
cells.insert(idx_data + 1, eep_md)
cells.insert(idx_data + 2, eep_code)

idx_seasonal = next(i for i, c in enumerate(cells)
                    if c["cell_type"] == "code"
                    and "plot_seasonal_means(" in "".join(c["source"])
                    and "import" not in "".join(c["source"]))
cells.insert(idx_seasonal + 1, iacal_md)
cells.insert(idx_seasonal + 2, iacal_code)

nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — {len(nb['cells'])} celdas totales")
