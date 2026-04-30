"""Patch humedales.ipynb: agrega OD, estado trofico, Vollenweider, macroinvertebrados, NDWI."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/humedales.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

# -- Seccion 1b: OD + estado trofico + Vollenweider ---------------------------
trofico_md = md(
    "## 1b. Calidad del agua y estado trofico del humedal\n\n"
    "El **estado trofico** clasifica el nivel de enriquecimiento por nutrientes. "
    "El modelo de **Vollenweider** predice la concentracion de fosforo total en equilibrio:\n\n"
    "```\n"
    "[P] = L / (qs * (1 + tau^0.5))     L = carga de fosforo (mg/m2/ano)\n"
    "qs = caudal especifico (m/ano)       tau = tiempo de residencia (anos)\n"
    "```\n\n"
    "| Estado trofico | [P] ug/L | Clorofila-a ug/L | OD (min, mg/L) |\n"
    "|---|---|---|---|\n"
    "| Oligotrofico | < 10 | < 2 | > 7 |\n"
    "| Mesotrofico | 10 - 30 | 2 - 8 | 5 - 7 |\n"
    "| Eutrofico | 30 - 100 | 8 - 25 | 3 - 5 |\n"
    "| Hipertrofico | > 100 | > 25 | < 3 |\n\n"
    "> **Norma:** Res. 196/2006 y Politica Nacional Humedales 2002. "
    "OD < 4 mg/L es umbral critico de deterioro (IDEAM).\n\n"
    "> **Nota NDWI:** Indice de Agua de Diferencia Normalizada "
    "NDWI = (Green - NIR)/(Green + NIR) — valores > 0 indican presencia de agua libre (Sentinel-2)."
)

trofico_code = code(
    "# Indicadores fisicoquimicos y estado trofico del humedal (simulados)\n"
    "np.random.seed(42)\n"
    "n = len(df)\n"
    "\n"
    "# Oxigeno Disuelto (OD) mg/L -- desciende con eutrofizacion\n"
    "od_trend = np.linspace(6.5, 4.2, n)  # deterioro gradual\n"
    "od_seasonal = 0.8 * np.sin(2*np.pi*np.arange(n)/12)  # mayor OD en sequia\n"
    "od = np.clip(od_trend + od_seasonal + np.random.normal(0, 0.3, n), 0.5, 12)\n"
    "\n"
    "# Fosforo total (ug/L) -- modelo Vollenweider simplificado\n"
    "L_carga = 500       # mg P/m2/ano (carga tipica humedal andino con presion agricola)\n"
    "qs = 3.0            # m/ano caudal especifico\n"
    "tau = 0.5           # anos tiempo de residencia\n"
    "P_eq = L_carga / (qs * (1 + tau**0.5))  # Vollenweider\n"
    "fosforo = np.clip(\n"
    "    P_eq + np.linspace(0, 20, n) + np.random.normal(0, 5, n), 5, 200)\n"
    "\n"
    "# Clorofila-a (ug/L) -- correlacionada con fosforo\n"
    "clorofila = np.clip(0.18 * fosforo**0.9 + np.random.normal(0, 1.5, n), 0.5, 80)\n"
    "\n"
    "# NDWI simulado (espejo de agua) -- varia con hidroperiodo\n"
    "nivel_agua = df['nivel_agua'].values\n"
    "ndwi = np.clip(-0.1 + 0.4*(nivel_agua - nivel_agua.min())/(nivel_agua.max()-nivel_agua.min())\n"
    "               + np.random.normal(0, 0.03, n), -0.3, 0.6)\n"
    "\n"
    "df['od_mgl'] = od.round(2)\n"
    "df['fosforo_ugl'] = fosforo.round(1)\n"
    "df['clorofila_ugl'] = clorofila.round(2)\n"
    "df['ndwi'] = ndwi.round(3)\n"
    "\n"
    "# Clasificacion estado trofico\n"
    "def estado_trofico(p):\n"
    "    if p < 10: return 'Oligotrofico'\n"
    "    if p < 30: return 'Mesotrofico'\n"
    "    if p < 100: return 'Eutrofico'\n"
    "    return 'Hipertrofico'\n"
    "\n"
    "df['estado_trofico'] = df['fosforo_ugl'].apply(estado_trofico)\n"
    "\n"
    "print(f'Vollenweider [P]eq = {P_eq:.1f} ug/L ({estado_trofico(P_eq)})')\n"
    "print(f'OD actual | min={od.min():.2f} max={od.max():.2f} media={od.mean():.2f} mg/L')\n"
    "print(f'Meses con OD < 4 mg/L (deterioro): {(od < 4).sum()}/{n}')\n"
    "print(df['estado_trofico'].value_counts())\n"
    "df[['fecha','nivel_agua','od_mgl','fosforo_ugl','clorofila_ugl','ndwi','estado_trofico']].head()"
)

# -- Seccion 3c: Dashboard calidad agua + macroinvertebrados + NDWI -----------
bio_md = md(
    "## 3c. Dashboard calidad del agua — OD, fosforo, NDWI y bioindicadores\n\n"
    "Los **macroinvertebrados bentonicos** son bioindicadores de calidad ecologica del agua. "
    "El indice **BMWP-Col** (Biological Monitoring Working Party adaptado a Colombia) "
    "asigna puntajes a familias de macroinvertebrados segun su sensibilidad:\n\n"
    "| BMWP-Col | Calidad | Color |\n"
    "|---|---|---|\n"
    "| > 150 | Muy buena | Azul |\n"
    "| 101 - 150 | Buena | Verde |\n"
    "| 61 - 100 | Regular | Amarillo |\n"
    "| 36 - 60 | Mala | Naranja |\n"
    "| < 35 | Muy mala | Rojo |\n\n"
    "> **NDWI** (Sentinel-2): valores > 0 = agua libre; -0.1 a 0 = agua con sedimentos; < -0.1 = vegetacion/suelo seco."
)

bio_code = code(
    "# Simulacion indice BMWP-Col (macroinvertebrados bentonicos)\n"
    "np.random.seed(7)\n"
    "# BMWP-Col desciende al deteriorarse la calidad del agua\n"
    "bmwp = np.clip(\n"
    "    np.linspace(95, 45, n) + np.random.normal(0, 8, n), 10, 200)\n"
    "df['bmwp_col'] = bmwp.round(0).astype(int)\n"
    "\n"
    "BMWP_COLORS = {\n"
    "    'Muy buena': '#1a73e8', 'Buena': '#27ae60',\n"
    "    'Regular': '#f1c40f', 'Mala': '#e67e22', 'Muy mala': '#e74c3c'}\n"
    "\n"
    "def bmwp_categoria(b):\n"
    "    if b > 150: return 'Muy buena'\n"
    "    if b > 100: return 'Buena'\n"
    "    if b > 60: return 'Regular'\n"
    "    if b > 35: return 'Mala'\n"
    "    return 'Muy mala'\n"
    "\n"
    "df['bmwp_cat'] = df['bmwp_col'].apply(bmwp_categoria)\n"
    "\n"
    "fig, axes = plt.subplots(2, 2, figsize=(14, 8))\n"
    "\n"
    "# Panel A: OD en el tiempo\n"
    "ax = axes[0, 0]\n"
    "ax.plot(df['fecha'], df['od_mgl'], lw=1.5, color='#2980b9')\n"
    "ax.axhline(4.0, color='red', ls='--', lw=1.5, label='Umbral critico OD=4 mg/L')\n"
    "ax.axhline(7.0, color='green', ls='--', lw=1, label='Optimo OD>7 mg/L')\n"
    "ax.set_title('Oxigeno Disuelto (OD)', fontweight='bold')\n"
    "ax.set_ylabel('OD (mg/L)'); ax.legend(fontsize=7); ax.grid(alpha=0.3)\n"
    "\n"
    "# Panel B: Fosforo total + estado trofico\n"
    "ax = axes[0, 1]\n"
    "trofico_colors = df['estado_trofico'].map(\n"
    "    {'Oligotrofico':'#1a73e8','Mesotrofico':'#27ae60',\n"
    "     'Eutrofico':'#f1c40f','Hipertrofico':'#e74c3c'})\n"
    "ax.scatter(df['fecha'], df['fosforo_ugl'], c=trofico_colors, s=15, alpha=0.7)\n"
    "ax.axhline(30, color='orange', ls='--', lw=1.5, label='Limite mesotrofico 30 ug/L')\n"
    "ax.set_title('Fosforo Total + Estado Trofico (Vollenweider)', fontweight='bold')\n"
    "ax.set_ylabel('Fosforo (ug/L)'); ax.legend(fontsize=7); ax.grid(alpha=0.3)\n"
    "\n"
    "# Panel C: BMWP-Col (macroinvertebrados)\n"
    "ax = axes[1, 0]\n"
    "bmwp_c = df['bmwp_cat'].map(BMWP_COLORS)\n"
    "ax.bar(df['fecha'], df['bmwp_col'], color=bmwp_c, width=20, alpha=0.85)\n"
    "for thresh, label in [(35,'Muy mala'),(60,'Mala'),(100,'Regular'),(150,'Buena')]:\n"
    "    ax.axhline(thresh, color='gray', ls='--', lw=0.8)\n"
    "ax.set_title('BMWP-Col (macroinvertebrados bentonicos)', fontweight='bold')\n"
    "ax.set_ylabel('Puntaje BMWP-Col'); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "# Panel D: NDWI espejo de agua\n"
    "ax = axes[1, 1]\n"
    "ax.plot(df['fecha'], df['ndwi'], lw=1.5, color='#3498db', label='NDWI')\n"
    "ax.axhline(0.0, color='green', ls='--', lw=1.5, label='Umbral agua libre NDWI=0')\n"
    "ax.fill_between(df['fecha'], df['ndwi'], 0,\n"
    "                where=(df['ndwi'] > 0), alpha=0.3, color='#3498db', label='Agua libre')\n"
    "ax.set_title('NDWI — Espejo de agua (Sentinel-2)', fontweight='bold')\n"
    "ax.set_ylabel('NDWI'); ax.legend(fontsize=7); ax.grid(alpha=0.3)\n"
    "\n"
    "plt.suptitle('Dashboard Calidad Ecologica — Humedal (Ley 357/1997 Ramsar)',\n"
    "             fontweight='bold', fontsize=12)\n"
    "plt.tight_layout(); plt.show()\n"
    "\n"
    "print('Estado trofico actual:', df['estado_trofico'].iloc[-1])\n"
    "print('BMWP-Col ultimo registro:', df['bmwp_col'].iloc[-1], '(', df['bmwp_cat'].iloc[-1], ')')\n"
    "print(f'Meses con NDWI>0 (agua libre): {(df[\"ndwi\"]>0).sum()}/{n}')"
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
cells.insert(idx_data + 1, trofico_md)
cells.insert(idx_data + 2, trofico_code)

idx_seasonal = next(i for i, c in enumerate(cells)
                    if c["cell_type"] == "code"
                    and "plot_seasonal_means(" in "".join(c["source"])
                    and "import" not in "".join(c["source"]))
cells.insert(idx_seasonal + 1, bio_md)
cells.insert(idx_seasonal + 2, bio_code)

nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — {len(nb['cells'])} celdas totales")
