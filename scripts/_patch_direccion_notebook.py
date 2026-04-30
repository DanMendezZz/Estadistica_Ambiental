"""Patch direccion_directiva.ipynb: agrega DPSIR, ICAU, Isolation Forest."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/direccion_directiva.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

# -- Seccion 1b: Marco DPSIR + ICAU + IEDI ------------------------------------
dpsir_md = md(
    "## 1b. Marco DPSIR y dashboard ICAU — Analitica institucional\n\n"
    "El marco **DPSIR** (Fuerzas Motrices - Presion - Estado - Impacto - Respuesta), "
    "promovido por la OCDE y adoptado por el IDEAM, estructura la causalidad ambiental:\n\n"
    "| Componente | Ejemplo ambiental | Indicador |\n"
    "|---|---|---|\n"
    "| **D** Fuerzas motrices | Crecimiento urbano, industria | Densidad poblacional, PIB |\n"
    "| **P** Presion | Vertimientos, emisiones, deforestacion | IACAL, RETC, TCCN |\n"
    "| **S** Estado | Calidad aire/agua, cobertura bosque | ICA, IVH, IRH |\n"
    "| **I** Impacto | Salud publica, perdida biodiversidad | Morbilidad, BMWP-Col |\n"
    "| **R** Respuesta | Normas, inversiones, PUEAA | % POT actualizados, IEDI |\n\n"
    "**ICAU (Indice de Calidad Ambiental Urbana):** agrega 6 componentes con pesos iguales:\n"
    "aire (PM2.5/PM10), agua (ICA), espacio publico, residuos, arbolado y ruido.\n\n"
    "**IEDI (Indice de Evaluacion del Desempeño Institucional):** mide la gestion de las CAR "
    "en 3 ejes: misional (eficacia/eficiencia), financiero y administrativo. Res. 667/2016."
)

dpsir_code = code(
    "# Marco DPSIR sintetico + ICAU por ciudad + IEDI por CAR\n"
    "np.random.seed(88)\n"
    "n = len(df)\n"
    "\n"
    "# -- DPSIR: variables por componente (indices normalizados 0-1) -----------\n"
    "dpsir_data = {\n"
    "    'Fuerzas_Motrices': 0.72,  # densidad pob + PIB industrial\n"
    "    'Presion':          0.65,  # IACAL + emisiones + deforest\n"
    "    'Estado':           0.41,  # ICA + IRH + cobertura bosque\n"
    "    'Impacto':          0.55,  # morbilidad + biodiversidad\n"
    "    'Respuesta':        0.38,  # % POT actualizados + IEDI promedio\n"
    "}\n"
    "\n"
    "# -- ICAU por ciudad (6 componentes) ------------------------------------\n"
    "ciudades = ['Bogota','Medellin','Cali','Barranquilla','Bucaramanga','Manizales']\n"
    "componentes_icau = ['Aire','Agua','Espacio_publico','Residuos','Arbolado','Ruido']\n"
    "icau_matrix = np.random.uniform(0.3, 0.9, (len(ciudades), len(componentes_icau)))\n"
    "icau_total = icau_matrix.mean(axis=1)  # promedio simple\n"
    "df_icau = pd.DataFrame(icau_matrix, columns=componentes_icau, index=ciudades)\n"
    "df_icau['ICAU_total'] = icau_total.round(3)\n"
    "\n"
    "# -- IEDI por CAR (escala 0-100) ----------------------------------------\n"
    "cars = ['CAR','CORPOAMAZONIA','CORNARE','CVC','CORANTIOQUIA','CORPOCESAR']\n"
    "iedi_misional  = np.random.uniform(50, 90, len(cars))\n"
    "iedi_financiero= np.random.uniform(40, 85, len(cars))\n"
    "iedi_admin     = np.random.uniform(45, 88, len(cars))\n"
    "iedi_total     = (iedi_misional * 0.5 + iedi_financiero * 0.3 + iedi_admin * 0.2)\n"
    "df_iedi = pd.DataFrame({'CAR': cars, 'Misional': iedi_misional.round(1),\n"
    "                         'Financiero': iedi_financiero.round(1),\n"
    "                         'Administrativo': iedi_admin.round(1),\n"
    "                         'IEDI_total': iedi_total.round(1)})\n"
    "\n"
    "print('Marco DPSIR (escala 0-1, mayor = mayor presion/impacto):')\n"
    "for k, v in dpsir_data.items():\n"
    "    bar = '|' * int(v * 20)\n"
    "    print(f'  {k:20s}: {bar} {v:.2f}')\n"
    "print(f'\\nICAU promedio ciudades: {icau_total.mean():.3f}')\n"
    "print(f'Ciudad mejor ICAU: {ciudades[icau_total.argmax()]} ({icau_total.max():.3f})')\n"
    "print(f'IEDI promedio CARs: {iedi_total.mean():.1f}/100')\n"
    "df_iedi"
)

# -- Seccion 3c: ICAU dashboard -----------------------------------------------
icau_md = md(
    "## 3c. Dashboard ICAU — Calidad Ambiental Urbana por ciudad y componente\n\n"
    "El ICAU permite a los directivos comparar el desempeño ambiental de ciudades y "
    "priorizar inversiones en el componente mas deficitario. "
    "La Resolucion 667/2016 (MADS) establece los **Indicadores Minimos de Gestion (IMG)** "
    "que las CAR deben reportar anualmente."
)

icau_code = code(
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
    "\n"
    "# Panel A: ICAU por componente y ciudad (heatmap)\n"
    "ax = axes[0]\n"
    "im = ax.imshow(df_icau[componentes_icau].values, cmap='RdYlGn',\n"
    "               aspect='auto', vmin=0, vmax=1)\n"
    "ax.set_xticks(range(len(componentes_icau)))\n"
    "ax.set_xticklabels(componentes_icau, rotation=30, ha='right', fontsize=8)\n"
    "ax.set_yticks(range(len(ciudades)))\n"
    "ax.set_yticklabels(ciudades, fontsize=9)\n"
    "for i in range(len(ciudades)):\n"
    "    for j in range(len(componentes_icau)):\n"
    "        ax.text(j, i, f'{df_icau[componentes_icau].values[i,j]:.2f}',\n"
    "                ha='center', va='center', fontsize=7)\n"
    "plt.colorbar(im, ax=ax, label='ICAU componente')\n"
    "ax.set_title('ICAU por Componente y Ciudad\\n(Res. 667/2016 — IMG MADS)', fontweight='bold')\n"
    "\n"
    "# Panel B: IEDI por CAR\n"
    "ax = axes[1]\n"
    "x = range(len(cars))\n"
    "width = 0.25\n"
    "ax.bar([i - width for i in x], df_iedi['Misional'], width, label='Misional (50%)', color='#27ae60', alpha=0.85)\n"
    "ax.bar(x, df_iedi['Financiero'], width, label='Financiero (30%)', color='#3498db', alpha=0.85)\n"
    "ax.bar([i + width for i in x], df_iedi['Administrativo'], width, label='Administrativo (20%)', color='#e67e22', alpha=0.85)\n"
    "ax.plot(x, df_iedi['IEDI_total'], 'ko-', ms=6, lw=2, label='IEDI total')\n"
    "ax.set_xticks(x); ax.set_xticklabels(cars, rotation=20, ha='right', fontsize=8)\n"
    "ax.set_title('IEDI por CAR — Evaluacion Desempeño Institucional', fontweight='bold')\n"
    "ax.set_ylabel('Puntaje (0-100)'); ax.legend(fontsize=7); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "plt.tight_layout(); plt.show()\n"
    "print(f'CAR mejor IEDI: {df_iedi.loc[df_iedi[\"IEDI_total\"].idxmax(), \"CAR\"]} '\n"
    "      f'({df_iedi[\"IEDI_total\"].max():.1f}/100)')"
)

# -- Seccion 7b: Isolation Forest anomalias presupuestales --------------------
if_md = md(
    "## 7b. Isolation Forest — Deteccion de anomalias en ejecucion presupuestal\n\n"
    "El **Isolation Forest** es un algoritmo no supervisado que detecta outliers "
    "aislando puntos atipicos en pocas particiones del arbol. "
    "En gestion publica ambiental se usa para:\n\n"
    "- Detectar contratos con valores atipicos (posibles irregularidades en contratacion)\n"
    "- Identificar CARs con ejecucion presupuestal anormalmente baja o alta\n"
    "- Anomalias en reportes de indicadores (posible subregistro o error de digitacion)\n\n"
    "```python\n"
    "from sklearn.ensemble import IsolationForest\n"
    "iso = IsolationForest(contamination=0.1, random_state=42)\n"
    "anomalias = iso.fit_predict(X)   # -1 = anomalia, +1 = normal\n"
    "scores = iso.decision_function(X)  # scores mas negativos = mas anomalo\n"
    "```"
)

if_code = code(
    "from sklearn.ensemble import IsolationForest\n"
    "\n"
    "np.random.seed(42)\n"
    "N = 120  # contratos/proyectos simulados\n"
    "\n"
    "# Features: valor contrato (M$), duracion (meses), ejecucion (%)\n"
    "valor = np.random.lognormal(mean=3.5, sigma=0.8, size=N)     # M pesos\n"
    "duracion = np.random.randint(3, 36, N)                         # meses\n"
    "ejecucion = np.clip(np.random.normal(75, 15, N), 0, 100)      # %\n"
    "\n"
    "# Inyectar anomalias (5 contratos irregulares)\n"
    "idx_anoms = np.random.choice(N, 5, replace=False)\n"
    "valor[idx_anoms] = np.random.uniform(500, 2000, 5)  # valores extremos\n"
    "ejecucion[idx_anoms] = np.random.uniform(0, 10, 5)  # ejecucion casi cero\n"
    "\n"
    "X_if = np.column_stack([valor, duracion, ejecucion])\n"
    "\n"
    "iso = IsolationForest(contamination=0.08, random_state=42, n_estimators=100)\n"
    "pred_if = iso.fit_predict(X_if)   # -1=anomalia\n"
    "scores_if = iso.decision_function(X_if)\n"
    "\n"
    "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))\n"
    "\n"
    "# Panel A: Valor vs Ejecucion coloreado por anomalia\n"
    "colors_if = ['#e74c3c' if p == -1 else '#2980b9' for p in pred_if]\n"
    "ax1.scatter(valor, ejecucion, c=colors_if, alpha=0.7, s=30)\n"
    "ax1.set_xlabel('Valor contrato (M pesos)')\n"
    "ax1.set_ylabel('Ejecucion presupuestal (%)')\n"
    "ax1.set_title('Isolation Forest — Anomalias presupuestales CAR', fontweight='bold')\n"
    "from matplotlib.patches import Patch\n"
    "ax1.legend(handles=[Patch(color='#e74c3c',label='Anomalia'),\n"
    "                     Patch(color='#2980b9',label='Normal')], fontsize=8)\n"
    "ax1.grid(alpha=0.3)\n"
    "\n"
    "# Panel B: Scores de anomalia\n"
    "sorted_idx = np.argsort(scores_if)\n"
    "ax2.barh(range(15), scores_if[sorted_idx[:15]], color=[\n"
    "    '#e74c3c' if pred_if[i]==-1 else '#2980b9' for i in sorted_idx[:15]])\n"
    "ax2.axvline(0, color='black', lw=1, ls='--')\n"
    "ax2.set_title('Top 15 scores Isolation Forest\\n(negativo = mas anomalo)', fontweight='bold')\n"
    "ax2.set_xlabel('Anomaly score'); ax2.grid(axis='x', alpha=0.3)\n"
    "\n"
    "plt.tight_layout(); plt.show()\n"
    "n_anom = (pred_if == -1).sum()\n"
    "print(f'Contratos anomalos detectados: {n_anom}/{N} ({n_anom/N*100:.1f}%)')\n"
    "print(f'Contratos inyectados como irregulares: {len(idx_anoms)}')\n"
    "print('Usar en produccion con datos SECOP II o SUI para auditoria presupuestal')"
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
cells.insert(idx_data + 1, dpsir_md)
cells.insert(idx_data + 2, dpsir_code)

idx_seasonal = next(i for i, c in enumerate(cells)
                    if c["cell_type"] == "code"
                    and "plot_seasonal_means(" in "".join(c["source"])
                    and "import" not in "".join(c["source"]))
cells.insert(idx_seasonal + 1, icau_md)
cells.insert(idx_seasonal + 2, icau_code)

idx_rank = next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code"
                and "rank_models(results)" in "".join(c["source"]))
cells.insert(idx_rank + 1, if_md)
cells.insert(idx_rank + 2, if_code)

nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — {len(nb['cells'])} celdas totales")
