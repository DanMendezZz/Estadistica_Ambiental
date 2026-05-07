# DEPRECATED — lógica integrada a build_notebooks.py 2026-05-07
# La fuente activa ahora es scripts/_patches/sistemas_informacion_ambiental.py.
# Este archivo se conserva como referencia histórica del enriquecimiento.
"""Patch sistemas_informacion_ambiental.ipynb: agrega RETC, vertimientos, metales pesados."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/sistemas_informacion_ambiental.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

retc_md = md(
    "## 3c. RETC — Cargas de vertimientos y metales pesados en biosólidos\n\n"
    "El **RETC (Registro de Emisiones y Transferencia de Contaminantes)**, integrado al RUA "
    "(Res. 839/2023), cuantifica cargas contaminantes vertidas al agua por sector productivo:\n\n"
    "| Parametro | Referencia | Umbral reporte |\n"
    "|---|---|---|\n"
    "| DBO (vertimientos) | Res. 631/2015 | Segun tipo de actividad |\n"
    "| SST (vertimientos) | Res. 631/2015 | Segun tipo de actividad |\n"
    "| Cadmio en biosolidos | Decreto 1287/2014 | < 39 mg/kg MS |\n"
    "| Plomo en biosolidos | Decreto 1287/2014 | < 300 mg/kg MS |\n\n"
    "Colombia vertio ~1.39 M ton DBO y ~1.35 M ton SST en 2020 (IDEAM/SIRH).\n\n"
    "> **Tasa retributiva (Decreto 2667/2012):** cargo economico por kg DBO o SST vertido, "
    "incentivo economico para que los generadores reduzcan sus cargas."
)

retc_code = code(
    "# RETC sintetico: cargas de vertimientos por sector + metales en biosolidos\n"
    "np.random.seed(19)\n"
    "n_anos = 10\n"
    "anos = list(range(2014, 2014 + n_anos))\n"
    "sectores_vert = ['Municipal', 'Agroindustria', 'Mineria', 'Manufactura', 'Servicios']\n"
    "\n"
    "# Cargas DBO por sector (miles ton DBO/ano)\n"
    "dbo_kt = {\n"
    "    'Municipal':     [800 - i*5  + np.random.normal(0, 20) for i in range(n_anos)],\n"
    "    'Agroindustria': [300 + i*2  + np.random.normal(0, 10) for i in range(n_anos)],\n"
    "    'Mineria':       [120 - i*1  + np.random.normal(0, 5)  for i in range(n_anos)],\n"
    "    'Manufactura':   [180 - i*3  + np.random.normal(0, 8)  for i in range(n_anos)],\n"
    "    'Servicios':     [40  + i*0.5+ np.random.normal(0, 2)  for i in range(n_anos)],\n"
    "}\n"
    "df_retc = pd.DataFrame({'ano': anos,\n"
    "                         **{s: [round(v,1) for v in vals]\n"
    "                            for s, vals in dbo_kt.items()}})\n"
    "df_retc['total_dbo_kt'] = df_retc[sectores_vert].sum(axis=1).round(1)\n"
    "\n"
    "# Metales pesados en biosolidos PTAR (mg/kg MS) -- Decreto 1287/2014\n"
    "n_ptar = 15\n"
    "ptars = [f'PTAR-{i+1:02d}' for i in range(n_ptar)]\n"
    "cadmio = np.random.uniform(10, 95, n_ptar).round(1)   # umbral: 39 mg/kg\n"
    "plomo  = np.random.uniform(80, 950, n_ptar).round(1)  # umbral: 300 mg/kg\n"
    "df_biosolidos = pd.DataFrame({'PTAR': ptars, 'Cadmio_mgkg': cadmio, 'Plomo_mgkg': plomo})\n"
    "df_biosolidos['Cd_cumple'] = df_biosolidos['Cadmio_mgkg'] <= 39\n"
    "df_biosolidos['Pb_cumple'] = df_biosolidos['Plomo_mgkg'] <= 300\n"
    "\n"
    "fig, axes = plt.subplots(1, 3, figsize=(16, 4))\n"
    "\n"
    "# Panel A: Cargas DBO vertimientos por sector (stacked)\n"
    "ax = axes[0]\n"
    "bottom = np.zeros(n_anos)\n"
    "colors_vert = ['#e74c3c','#e67e22','#f1c40f','#3498db','#9b59b6']\n"
    "for s, color in zip(sectores_vert, colors_vert):\n"
    "    ax.bar(df_retc['ano'], df_retc[s], bottom=bottom, label=s, color=color, alpha=0.85, width=0.7)\n"
    "    bottom += df_retc[s].values\n"
    "ax.set_title('RETC — Carga DBO vertida al agua (kt/ano)', fontweight='bold')\n"
    "ax.set_ylabel('kt DBO/ano'); ax.legend(fontsize=7); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "# Panel B: Cadmio en biosolidos\n"
    "ax = axes[1]\n"
    "bar_cd = ['#27ae60' if v <= 39 else '#e74c3c' for v in cadmio]\n"
    "ax.barh(ptars, cadmio, color=bar_cd, alpha=0.85)\n"
    "ax.axvline(39, color='red', ls='--', lw=1.5, label='Umbral Cd: 39 mg/kg (Dto. 1287/2014)')\n"
    "ax.set_title('Cadmio en Biosolidos PTAR', fontweight='bold')\n"
    "ax.set_xlabel('Cadmio (mg/kg MS)'); ax.legend(fontsize=7); ax.grid(axis='x', alpha=0.3)\n"
    "\n"
    "# Panel C: Plomo en biosolidos\n"
    "ax = axes[2]\n"
    "bar_pb = ['#27ae60' if v <= 300 else '#e74c3c' for v in plomo]\n"
    "ax.barh(ptars, plomo, color=bar_pb, alpha=0.85)\n"
    "ax.axvline(300, color='red', ls='--', lw=1.5, label='Umbral Pb: 300 mg/kg (Dto. 1287/2014)')\n"
    "ax.set_title('Plomo en Biosolidos PTAR', fontweight='bold')\n"
    "ax.set_xlabel('Plomo (mg/kg MS)'); ax.legend(fontsize=7); ax.grid(axis='x', alpha=0.3)\n"
    "\n"
    "plt.suptitle('SIAC / RETC — Monitoreo de cargas contaminantes y biosolidos (Res. 839/2023)',\n"
    "             fontweight='bold', fontsize=11)\n"
    "plt.tight_layout(); plt.show()\n"
    "\n"
    "ptar_cd_incumple = (~df_biosolidos['Cd_cumple']).sum()\n"
    "ptar_pb_incumple = (~df_biosolidos['Pb_cumple']).sum()\n"
    "print(f'PTAR incumple Cadmio (>39 mg/kg): {ptar_cd_incumple}/{n_ptar}')\n"
    "print(f'PTAR incumple Plomo (>300 mg/kg): {ptar_pb_incumple}/{n_ptar}')\n"
    "print(f'Total vertimientos 2023 (estimado): {df_retc[\"total_dbo_kt\"].iloc[-1]:.0f} kt DBO')"
)

# -- Fix walk_forward gap --
for i, c in enumerate(cells):
    src = "".join(c["source"])
    if c["cell_type"] == "code" and "walk_forward(model, ts" in src and "gap=" not in src:
        cells[i]["source"] = src.replace(
            "walk_forward(model, ts, horizon=",
            "walk_forward(model, ts, gap=12, horizon="
        )

idx_seasonal = next(i for i, c in enumerate(cells)
                    if c["cell_type"] == "code"
                    and "plot_seasonal_means(" in "".join(c["source"])
                    and "import" not in "".join(c["source"]))
cells.insert(idx_seasonal + 1, retc_md)
cells.insert(idx_seasonal + 2, retc_code)

nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — {len(nb['cells'])} celdas totales")
