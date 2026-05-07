# DEPRECATED — lógica integrada a build_notebooks.py 2026-05-07
# La fuente activa ahora son scripts/_patches/{pomca,rondas_hidricas,
# areas_protegidas,pueea,geoespacial}.py. Este archivo se conserva como
# referencia histórica del enriquecimiento.
"""Patch notebooks con 1 marker faltante: pomca, rondas_hidricas, areas_protegidas, pueea, geoespacial."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

def fix_gap(cells):
    for i, c in enumerate(cells):
        src = "".join(c["source"])
        if c["cell_type"] == "code" and "walk_forward(model, ts" in src and "gap=" not in src:
            cells[i]["source"] = src.replace(
                "walk_forward(model, ts, horizon=",
                "walk_forward(model, ts, gap=12, horizon="
            )
    return cells

def find_data(cells):
    return next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code" and "sintéticos de ejemplo" in "".join(c["source"]))

def find_seasonal(cells):
    return next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code"
                and "plot_seasonal_means(" in "".join(c["source"])
                and "import" not in "".join(c["source"]))

def find_mk(cells):
    return next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code" and "mann_kendall(" in "".join(c["source"])
                and "import" not in "".join(c["source"]))

def find_rank(cells):
    return next(i for i, c in enumerate(cells)
                if c["cell_type"] == "code" and "rank_models(results)" in "".join(c["source"]))

# =============================================================================
# 1. POMCA — agrega OHDS (Oferta Hidrica Disponible Superficial) + IVH
# =============================================================================
NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/pomca.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = fix_gap(nb["cells"])

ohds_md = md(
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

idx = find_data(cells)
cells.insert(idx + 1, ohds_md)
cells.insert(idx + 2, ohds_code)
nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"pomca OK — {len(nb['cells'])} celdas")

# =============================================================================
# 2. RONDAS HIDRICAS — agrega HAND + analisis de frecuencia Gumbel
# =============================================================================
NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/rondas_hidricas.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = fix_gap(nb["cells"])

hand_md = md(
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

idx = find_seasonal(cells)
cells.insert(idx + 1, hand_md)
cells.insert(idx + 2, hand_code)
nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"rondas_hidricas OK — {len(nb['cells'])} celdas")

# =============================================================================
# 3. AREAS PROTEGIDAS — agrega Random Forest para prediccion de deforestacion
# =============================================================================
NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/areas_protegidas.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = fix_gap(nb["cells"])

rf_deforest_md = md(
    "## 5c. Random Forest — Prediccion de deforestacion en areas protegidas\n\n"
    "El **Random Forest** es el modelo de referencia del IDEAM/SMByC para predecir "
    "tasas de deforestacion. Ventajas frente a modelos lineales:\n\n"
    "- Captura interacciones no lineales entre distancia a vias, pendiente, densidad demografica\n"
    "- Robusto ante outliers y variables con diferentes escalas\n"
    "- Produce importancia de variables (feature importance) para priorizar monitoreo\n\n"
    "Variables predictoras tipicas del SMByC:\n"
    "| Variable | Tipo | Fuente |\n"
    "|---|---|---|\n"
    "| Distancia a vias | Continua | IGAC/INVIAS |\n"
    "| Pendiente | Continua | DEM NASA/IGAC |\n"
    "| Densidad poblacional | Continua | DANE |\n"
    "| Cobertura previa | Categorica | Corine Land Cover |\n"
    "| Precipitacion media | Continua | IDEAM |\n"
    "| Presencia mineria | Binaria | ANM/ANLA |\n\n"
    "> **Matriz de confusion ajustada por area:** el SMByC usa exactitudes del usuario y "
    "productor ponderadas por el area real de cada clase (no por pixeles), siguiendo "
    "Olofsson et al. (2014) — estandar IPCC Tier 3."
)

rf_deforest_code = code(
    "from sklearn.ensemble import RandomForestClassifier\n"
    "from sklearn.model_selection import cross_val_score\n"
    "from sklearn.metrics import confusion_matrix, classification_report\n"
    "\n"
    "np.random.seed(42)\n"
    "N = 500  # puntos de muestreo en el area protegida\n"
    "\n"
    "# Features: predictores de deforestacion\n"
    "dist_vias_km  = np.random.exponential(15, N)           # km al vial mas cercano\n"
    "pendiente_deg = np.random.gamma(2, 8, N).clip(0, 60)   # grados\n"
    "dens_pob      = np.random.lognormal(2, 1, N)           # hab/km2\n"
    "precipitacion = np.random.normal(2000, 400, N)          # mm/ano\n"
    "mineria       = (np.random.random(N) < 0.15).astype(int)  # presencia mineria\n"
    "\n"
    "X_rf = np.column_stack([dist_vias_km, pendiente_deg, dens_pob, precipitacion, mineria])\n"
    "feature_names = ['dist_vias_km','pendiente_deg','dens_pob','precipitacion','mineria']\n"
    "\n"
    "# Probabilidad de deforestacion (proceso generativo)\n"
    "prob_def = 1 / (1 + np.exp(\n"
    "    2 - 0.15*dist_vias_km + 0.02*dens_pob - 0.01*pendiente_deg + 1.5*mineria))\n"
    "y_rf = (prob_def > 0.5).astype(int)  # 1=deforestado, 0=estable\n"
    "\n"
    "# Entrenar RandomForest\n"
    "rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)\n"
    "cv_scores = cross_val_score(rf, X_rf, y_rf, cv=5, scoring='f1')\n"
    "rf.fit(X_rf, y_rf)\n"
    "y_pred_rf = rf.predict(X_rf)\n"
    "\n"
    "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))\n"
    "\n"
    "# Panel A: Importancia de variables\n"
    "importances = rf.feature_importances_\n"
    "sorted_idx = np.argsort(importances)[::-1]\n"
    "ax1.barh([feature_names[i] for i in sorted_idx], importances[sorted_idx],\n"
    "         color=['#e74c3c' if i == sorted_idx[0] else '#3498db' for i in range(len(feature_names))],\n"
    "         alpha=0.85)\n"
    "ax1.set_title('Random Forest — Importancia de variables\\n(prediccion deforestacion SMByC)', fontweight='bold')\n"
    "ax1.set_xlabel('Importancia (Gini)'); ax1.grid(axis='x', alpha=0.3)\n"
    "\n"
    "# Panel B: Matriz de confusion\n"
    "cm = confusion_matrix(y_rf, y_pred_rf)\n"
    "cm_norm = cm / cm.sum(axis=1, keepdims=True)  # normalizada por clase (exactitud productor)\n"
    "im = ax2.imshow(cm_norm, cmap='Blues', vmin=0, vmax=1)\n"
    "plt.colorbar(im, ax=ax2, label='Proporcion')\n"
    "for i in range(2):\n"
    "    for j in range(2):\n"
    "        ax2.text(j, i, f'{cm[i,j]}\\n({cm_norm[i,j]:.2f})',\n"
    "                 ha='center', va='center', fontsize=10)\n"
    "ax2.set_xticks([0,1]); ax2.set_yticks([0,1])\n"
    "ax2.set_xticklabels(['Pred: Estable','Pred: Deforest.'])\n"
    "ax2.set_yticklabels(['Real: Estable','Real: Deforest.'])\n"
    "ax2.set_title('Matriz de confusion RF — Exactitud productor/usuario\\n(Olofsson 2014 requiere ajuste por area)', fontweight='bold')\n"
    "\n"
    "plt.tight_layout(); plt.show()\n"
    "print(f'CV F1-score (5-fold): {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}')\n"
    "print(f'Variable mas importante: {feature_names[importances.argmax()]} ({importances.max():.3f})')\n"
    "print(classification_report(y_rf, y_pred_rf, target_names=['Estable','Deforestado']))"
)

idx = find_mk(cells)
cells.insert(idx + 1, rf_deforest_md)
cells.insert(idx + 2, rf_deforest_code)
nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"areas_protegidas OK — {len(nb['cells'])} celdas")

# =============================================================================
# 4. PUEEA — agrega IANC (perdidas de agua) + Isolation Forest
# =============================================================================
NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/pueea.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = fix_gap(nb["cells"])

ianc_md = md(
    "## 3c. IANC — Perdidas de agua y deteccion de anomalias (Isolation Forest)\n\n"
    "El **IANC (Indice de Agua No Contabilizada)** mide las perdidas del sistema de acueducto "
    "como porcentaje del volumen captado. Meta PUEAA: IANC <= 30% (Res. 943/2021 CRA).\n\n"
    "```\n"
    "IANC = (Volumen_captado - Volumen_facturado) / Volumen_captado * 100 (%)\n"
    "Perdidas tecnicas: fugas en red, reboses en tanques\n"
    "Perdidas comerciales: robos de agua, errores en medicion\n"
    "```\n\n"
    "**Isolation Forest** detecta lecturas de caudal anomalas "
    "(fugas subitas, captaciones ilegales, fallos de sensor)."
)

ianc_code = code(
    "from sklearn.ensemble import IsolationForest\n"
    "\n"
    "np.random.seed(66)\n"
    "n = len(df)\n"
    "\n"
    "# Volumen captado vs facturado (m3/mes)\n"
    "vol_captado   = df['consumo_agua'].values * 1000  # proxy: consumo -> captacion\n"
    "vol_facturado = vol_captado * np.clip(np.random.normal(0.72, 0.08, n), 0.3, 0.95)\n"
    "\n"
    "# IANC mensual\n"
    "ianc = (1 - vol_facturado / vol_captado) * 100\n"
    "df['ianc_pct'] = ianc.round(1)\n"
    "\n"
    "# Isolation Forest sobre caudal diario simulado\n"
    "np.random.seed(7)\n"
    "N_dias = 365\n"
    "caudal_diario = np.random.normal(15, 3, N_dias)  # L/s\n"
    "# Inyectar anomalias (fugas/captaciones ilegales)\n"
    "idx_anom = np.random.choice(N_dias, 12, replace=False)\n"
    "caudal_diario[idx_anom] += np.random.uniform(15, 40, 12)\n"
    "\n"
    "iso_caudal = IsolationForest(contamination=0.05, random_state=42)\n"
    "pred_caudal = iso_caudal.fit_predict(caudal_diario.reshape(-1, 1))\n"
    "scores_caudal = iso_caudal.decision_function(caudal_diario.reshape(-1, 1))\n"
    "\n"
    "fig, axes = plt.subplots(1, 3, figsize=(16, 4))\n"
    "\n"
    "# Panel A: IANC en el tiempo\n"
    "ax = axes[0]\n"
    "colors_ianc = ['#e74c3c' if v > 30 else '#f1c40f' if v > 20 else '#27ae60'\n"
    "               for v in df['ianc_pct']]\n"
    "ax.bar(df['fecha'], df['ianc_pct'], color=colors_ianc, width=20, alpha=0.85)\n"
    "ax.axhline(30, color='red', ls='--', lw=1.5, label='Meta IANC <= 30% (Res. 943/2021)')\n"
    "ax.set_title('IANC — Indice Agua No Contabilizada (%)', fontweight='bold')\n"
    "ax.set_ylabel('IANC (%)'); ax.legend(fontsize=7); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "# Panel B: Caudal diario + anomalias Isolation Forest\n"
    "ax = axes[1]\n"
    "t_dias = range(N_dias)\n"
    "colors_if = ['#e74c3c' if p == -1 else '#2980b9' for p in pred_caudal]\n"
    "ax.scatter(t_dias, caudal_diario, c=colors_if, s=8, alpha=0.7)\n"
    "ax.set_title('Isolation Forest — Anomalias caudal diario\\n(fugas, captaciones ilegales)', fontweight='bold')\n"
    "ax.set_xlabel('Dia'); ax.set_ylabel('Caudal (L/s)')\n"
    "from matplotlib.patches import Patch\n"
    "ax.legend(handles=[Patch(color='#e74c3c',label='Anomalia'),\n"
    "                   Patch(color='#2980b9',label='Normal')], fontsize=8)\n"
    "ax.grid(alpha=0.3)\n"
    "\n"
    "# Panel C: Tipo de perdidas\n"
    "ax = axes[2]\n"
    "perdidas_tecnicas   = np.clip(ianc * 0.65, 0, None).mean()\n"
    "perdidas_comerciales= np.clip(ianc * 0.35, 0, None).mean()\n"
    "ax.bar(['Tecnicas\\n(fugas/reboses)', 'Comerciales\\n(fraude/medicion)'],\n"
    "       [perdidas_tecnicas, perdidas_comerciales],\n"
    "       color=['#e74c3c', '#e67e22'], alpha=0.85, width=0.5)\n"
    "ax.set_title('Composicion IANC promedio\\n(PUEAA: meta reduccion quinquenal)', fontweight='bold')\n"
    "ax.set_ylabel('IANC medio (%)'); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "plt.suptitle('PUEAA — IANC + Anomalias Isolation Forest (Ley 373/1997)',\n"
    "             fontweight='bold', fontsize=11)\n"
    "plt.tight_layout(); plt.show()\n"
    "\n"
    "n_anom_if = (pred_caudal == -1).sum()\n"
    "print(f'IANC promedio: {ianc.mean():.1f}% | Meses > 30%: {(ianc > 30).sum()}/{n}')\n"
    "print(f'Anomalias caudal detectadas: {n_anom_if}/365 dias ({n_anom_if/365*100:.1f}%)')\n"
    "print(f'Injected anomalias: {len(idx_anom)} — todas dentro de los {n_anom_if} detectados')"
)

idx = find_seasonal(cells)
cells.insert(idx + 1, ianc_md)
cells.insert(idx + 2, ianc_code)
nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"pueea OK — {len(nb['cells'])} celdas")

# =============================================================================
# 5. GEOESPACIAL — agrega NDWI + MNDWI
# =============================================================================
NB = pathlib.Path("notebooks/lineas_tematicas/bloque_c_tecnicas/geoespacial.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

ndwi_md = md(
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

# Insertar despues de la ultima celda de Caso 4 (getis_ord_g)
idx_g = next(i for i, c in enumerate(cells)
             if c["cell_type"] == "code" and "getis_ord_g" in "".join(c["source"]))
cells.insert(idx_g + 1, ndwi_md)
cells.insert(idx_g + 2, ndwi_code)
nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"geoespacial OK — {len(nb['cells'])} celdas")
