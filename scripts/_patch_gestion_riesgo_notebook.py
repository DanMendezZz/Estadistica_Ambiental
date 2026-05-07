# DEPRECATED — lógica integrada a build_notebooks.py 2026-05-07
# La fuente activa ahora es scripts/_patches/gestion_riesgo.py.
# Este archivo se conserva como referencia histórica del enriquecimiento.
"""Patch gestion_riesgo.ipynb: agrega AVR, IVET, SPI, vulnerabilidad, LSTM."""
import json, pathlib, uuid

def new_id(): return uuid.uuid4().hex[:16]
def md(src): return {"cell_type":"markdown","id":new_id(),"metadata":{},"source":src}
def code(src): return {"cell_type":"code","id":new_id(),"metadata":{},"execution_count":None,"outputs":[],"source":src}

NB = pathlib.Path("notebooks/lineas_tematicas/bloque_a_gestion/gestion_riesgo.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
cells = nb["cells"]

# -- Seccion 1b: Amenaza-Vulnerabilidad-Riesgo + IVET + SPI ------------------
avr_md = md(
    "## 1b. Componentes AVR — Amenaza, Vulnerabilidad y Riesgo\n\n"
    "La **Ley 1523/2012** define el riesgo como la combinacion de amenaza y vulnerabilidad:\n\n"
    "```\n"
    "Riesgo = Amenaza x Vulnerabilidad x Exposicion\n"
    "Escala: Muy Baja (1) | Baja (2) | Media (3) | Alta (4) | Muy Alta (5)\n"
    "```\n\n"
    "| Fenomeno | Indicador clave | Detonante | Fuente |\n"
    "|---|---|---|---|\n"
    "| Inundacion | Profundidad agua (m), caudal | Lluvia extrema | IDEAM/HEC-RAS |\n"
    "| Movimiento masa | Pendiente, litologia | Lluvia/sismo | SGC |\n"
    "| Avenida torrencial | IVET (0-1) | Lluvia intensa | SGC/IDEAM |\n"
    "| Sequia | SPI < -1.5 | Deficit lluvia | IDEAM |\n\n"
    "**IVET (Indice de Vulnerabilidad a Eventos Torrenciales):** combina pendiente, "
    "cobertura, morfometria de cuenca e indice de Melton. IVET > 0.6 = alta susceptibilidad.\n\n"
    "**SPI (Standardized Precipitation Index):** SPI < -1.5 = sequia severa; SPI > 1.5 = lluvia extrema."
)

avr_code = code(
    "# AVR sintetico por municipio + SPI de precipitacion\n"
    "np.random.seed(123)\n"
    "n = len(df)\n"
    "\n"
    "# -- SPI (Indice de Precipitacion Estandarizado) -------------------------\n"
    "precip = df['precipitacion'].values\n"
    "mu_p, std_p = precip.mean(), precip.std()\n"
    "spi = (precip - mu_p) / std_p  # SPI-1 mensual\n"
    "df['spi'] = spi.round(3)\n"
    "\n"
    "# -- IVET por subcuenca (valor anual, escala 0-1) -------------------------\n"
    "n_subcuencas = 8\n"
    "subcuencas = [f'SC-{i+1:02d}' for i in range(n_subcuencas)]\n"
    "ivet = np.random.beta(2, 3, n_subcuencas)  # distribucion tipica IVET\n"
    "\n"
    "# -- Indice de Amenaza (IA) + Vulnerabilidad (IV) + Riesgo (IR) ----------\n"
    "# Escala 1-5, simulando evaluacion AVR por municipio\n"
    "n_municipios = 15\n"
    "municipios = [f'Mpio-{i+1:02d}' for i in range(n_municipios)]\n"
    "ia = np.random.randint(1, 6, n_municipios)\n"
    "iv = np.random.randint(1, 6, n_municipios)\n"
    "ir = np.clip((ia * iv / 5).astype(int), 1, 5)\n"
    "\n"
    "df_avr = pd.DataFrame({'municipio': municipios, 'amenaza': ia,\n"
    "                        'vulnerabilidad': iv, 'riesgo': ir})\n"
    "df_avr['categoria_riesgo'] = pd.cut(df_avr['riesgo'],\n"
    "    bins=[0,1,2,3,4,5], labels=['Muy Baja','Baja','Media','Alta','Muy Alta'])\n"
    "\n"
    "print(f'SPI | min={spi.min():.2f} max={spi.max():.2f}')\n"
    "print(f'Meses SPI < -1.5 (sequia severa): {(spi < -1.5).sum()}')\n"
    "print(f'Meses SPI > 1.5 (lluvia extrema): {(spi > 1.5).sum()}')\n"
    "print(f'\\nIVET subcuencas | max={ivet.max():.3f} (alta susceptibilidad torrent si >0.6)')\n"
    "print(f'Subcuencas IVET > 0.6: {(ivet > 0.6).sum()}/{n_subcuencas}')\n"
    "df_avr"
)

# -- Seccion 3c: Dashboard AVR + SPI + IVET ----------------------------------
avr_viz_md = md(
    "## 3c. Dashboard AVR — Visualizacion de riesgo compuesto\n\n"
    "Los cuatro paneles responden preguntas clave del ciclo GRD (Ley 1523/2012):\n\n"
    "- **SPI:** deteccion de sequias extremas (detonante hidrologico)\n"
    "- **IVET:** susceptibilidad a avenidas torrenciales por subcuenca\n"
    "- **Matriz AVR:** distribucion amenaza vs. vulnerabilidad por municipio\n"
    "- **Riesgo compuesto:** clasificacion final para POT y POMCA\n\n"
    "> **InSAR / DInSAR** (Interferometric SAR): complementa el AVR midiendo deformacion del terreno "
    "en milimetros, fundamental para monitorear movimientos en masa activos y zonas de subsidencia. "
    "Fuentes: ESA Sentinel-1 (C-SAR) o ALOS-2 PALSAR-2."
)

avr_viz_code = code(
    "RISK_COLORS = {'Muy Baja':'#27ae60','Baja':'#82e0aa','Media':'#f1c40f',\n"
    "               'Alta':'#e67e22','Muy Alta':'#e74c3c'}\n"
    "\n"
    "fig, axes = plt.subplots(2, 2, figsize=(14, 8))\n"
    "\n"
    "# Panel A: SPI mensual\n"
    "ax = axes[0, 0]\n"
    "colors_spi = ['#e74c3c' if s < -1.5 else '#e67e22' if s < 0\n"
    "              else '#27ae60' if s > 1.5 else '#82e0aa' for s in df['spi']]\n"
    "ax.bar(df['fecha'], df['spi'], color=colors_spi, width=20)\n"
    "ax.axhline(-1.5, color='red', ls='--', lw=1.5, label='Sequia severa SPI<-1.5')\n"
    "ax.axhline(1.5, color='blue', ls='--', lw=1.5, label='Lluvia extrema SPI>1.5')\n"
    "ax.set_title('SPI — Indice de Precipitacion Estandarizado', fontweight='bold')\n"
    "ax.set_ylabel('SPI'); ax.legend(fontsize=7); ax.grid(alpha=0.3)\n"
    "\n"
    "# Panel B: IVET por subcuenca\n"
    "ax = axes[0, 1]\n"
    "colors_ivet = ['#e74c3c' if v > 0.6 else '#e67e22' if v > 0.4 else '#27ae60'\n"
    "               for v in ivet]\n"
    "ax.barh(subcuencas, ivet, color=colors_ivet, alpha=0.85)\n"
    "ax.axvline(0.6, color='red', ls='--', lw=1.5, label='Alta susceptibilidad IVET>0.6')\n"
    "ax.set_title('IVET — Susceptibilidad a Avenidas Torrenciales', fontweight='bold')\n"
    "ax.set_xlabel('IVET (0-1)'); ax.legend(fontsize=7); ax.grid(axis='x', alpha=0.3)\n"
    "\n"
    "# Panel C: Scatter Amenaza vs Vulnerabilidad\n"
    "ax = axes[1, 0]\n"
    "scatter_colors = df_avr['categoria_riesgo'].map(RISK_COLORS)\n"
    "sc = ax.scatter(df_avr['amenaza'], df_avr['vulnerabilidad'],\n"
    "                c=scatter_colors, s=80, alpha=0.8, edgecolors='gray', lw=0.5)\n"
    "ax.set_xlabel('Amenaza (1-5)'); ax.set_ylabel('Vulnerabilidad (1-5)')\n"
    "ax.set_title('Matriz Amenaza vs. Vulnerabilidad por Municipio', fontweight='bold')\n"
    "for _, r in df_avr.iterrows():\n"
    "    ax.annotate(r['municipio'], (r['amenaza'], r['vulnerabilidad']),\n"
    "                fontsize=6, ha='center', va='bottom')\n"
    "ax.grid(alpha=0.3)\n"
    "\n"
    "# Panel D: Distribucion riesgo compuesto\n"
    "ax = axes[1, 1]\n"
    "riesgo_counts = df_avr['categoria_riesgo'].value_counts().reindex(\n"
    "    ['Muy Baja','Baja','Media','Alta','Muy Alta'], fill_value=0)\n"
    "ax.bar(riesgo_counts.index, riesgo_counts.values,\n"
    "       color=[RISK_COLORS[k] for k in riesgo_counts.index], alpha=0.85)\n"
    "ax.set_title('Distribucion Riesgo Compuesto AVR (Ley 1523/2012)', fontweight='bold')\n"
    "ax.set_ylabel('N municipios'); ax.grid(axis='y', alpha=0.3)\n"
    "\n"
    "plt.suptitle('Dashboard Gestion del Riesgo — AVR + SPI + IVET',\n"
    "             fontweight='bold', fontsize=12)\n"
    "plt.tight_layout(); plt.show()\n"
    "\n"
    "alto_riesgo = (df_avr['categoria_riesgo'].isin(['Alta','Muy Alta'])).sum()\n"
    "print(f'Municipios en riesgo Alto/Muy Alto: {alto_riesgo}/{n_municipios}')\n"
    "print(df_avr[df_avr['categoria_riesgo'].isin(['Alta','Muy Alta'])][['municipio','amenaza','vulnerabilidad','categoria_riesgo']])"
)

# -- Seccion 5c: LSTM conceptual para prediccion de caudales extremos ---------
lstm_md = md(
    "## 5c. LSTM para prediccion de caudales extremos — arquitectura y flujo\n\n"
    "Las **Redes Neuronales Recurrentes (LSTM — Long Short-Term Memory)** son el estado del arte "
    "para prediccion de series temporales hidrologicas porque capturan dependencias temporales "
    "largas (memoria de lluvia acumulada, saturacion del suelo).\n\n"
    "```\n"
    "Arquitectura tipica para GRD:\n"
    "  Input: [precipitacion_t-k, ..., t-1, SPI, pendiente, cobertura]\n"
    "  LSTM Layer 1: 64 unidades, dropout=0.2\n"
    "  LSTM Layer 2: 32 unidades, dropout=0.2\n"
    "  Dense: 1 salida (caudal_t o prob_deslizamiento)\n"
    "  Loss: MSE (caudal) o BCE (clasificacion amenaza)\n"
    "```\n\n"
    "Librerias: `keras` / `tensorflow` o `pytorch`. "
    "Referencia IDEAM: modelos LSTM calibrados con datos DHIME para cuencas andinas (RMSE ~15% del caudal medio).\n\n"
    "> **InSAR / DInSAR (Interferometric SAR):** complementa el LSTM midiendo deformacion del terreno "
    "en mm/ano. Sentinel-1 permite generar mapas de velocidad de subsidencia o desplazamiento. "
    "Critico para monitorear deslizamientos activos antes del colapso."
)

lstm_code = code(
    "# Simulacion LSTM-like: ventana deslizante para prediccion de caudal maximo\n"
    "# (numpy puro — sin dependencias de tensorflow/pytorch)\n"
    "WINDOW = 6   # meses de contexto\n"
    "HORIZON = 1  # meses a predecir\n"
    "\n"
    "ts_vals = df_clean['precipitacion'].values if 'precipitacion' in df_clean.columns else df_clean.iloc[:, 0].values\n"
    "\n"
    "# Construir matrices X, y con ventana deslizante (como LSTM)\n"
    "X_lstm, y_lstm = [], []\n"
    "for t in range(WINDOW, len(ts_vals) - HORIZON):\n"
    "    X_lstm.append(ts_vals[t-WINDOW:t])  # contexto\n"
    "    y_lstm.append(ts_vals[t:t+HORIZON]) # objetivo\n"
    "X_lstm = np.array(X_lstm)  # shape: (muestras, WINDOW)\n"
    "y_lstm = np.array(y_lstm).ravel()\n"
    "\n"
    "# Regresion lineal como proxy del LSTM (misma ventana deslizante)\n"
    "from sklearn.linear_model import Ridge\n"
    "from sklearn.model_selection import cross_val_score\n"
    "ridge = Ridge(alpha=1.0)\n"
    "cv_rmse = (-cross_val_score(ridge, X_lstm, y_lstm,\n"
    "                            cv=5, scoring='neg_root_mean_squared_error')).mean()\n"
    "ridge.fit(X_lstm, y_lstm)\n"
    "y_pred = ridge.predict(X_lstm)\n"
    "\n"
    "# Plot: prediccion vs real\n"
    "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))\n"
    "ax1.plot(y_lstm, lw=1.5, color='#2980b9', label='Real')\n"
    "ax1.plot(y_pred, lw=1.5, ls='--', color='#e74c3c', label='LSTM-proxy (Ridge, ventana=6m)')\n"
    "ax1.set_title(f'LSTM-proxy — Prediccion caudal | CV-RMSE={cv_rmse:.2f}', fontweight='bold')\n"
    "ax1.set_xlabel('Paso temporal'); ax1.set_ylabel('Precipitacion (mm)')\n"
    "ax1.legend(fontsize=8); ax1.grid(alpha=0.3)\n"
    "\n"
    "# SPI extremos\n"
    "ax2.hist(df['spi'], bins=30, color='#3498db', alpha=0.7, edgecolor='white')\n"
    "ax2.axvline(-1.5, color='red', ls='--', lw=2, label='Sequia severa')\n"
    "ax2.axvline(1.5, color='green', ls='--', lw=2, label='Lluvia extrema')\n"
    "ax2.set_title('Distribucion SPI — Deteccion de extremos hidrologicos', fontweight='bold')\n"
    "ax2.set_xlabel('SPI'); ax2.set_ylabel('Frecuencia')\n"
    "ax2.legend(fontsize=8); ax2.grid(alpha=0.3)\n"
    "\n"
    "plt.tight_layout(); plt.show()\n"
    "print(f'Ventana LSTM: {WINDOW} meses | CV-RMSE: {cv_rmse:.2f}')\n"
    "print('Nota: LSTM real (TF/PyTorch) captura dependencias no lineales y memoria larga')\n"
    "print('InSAR/DInSAR (Sentinel-1): monitoreo deformacion del terreno mm/ano complementa GRD')"
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
cells.insert(idx_data + 1, avr_md)
cells.insert(idx_data + 2, avr_code)

idx_seasonal = next(i for i, c in enumerate(cells)
                    if c["cell_type"] == "code"
                    and "plot_seasonal_means(" in "".join(c["source"])
                    and "import" not in "".join(c["source"]))
cells.insert(idx_seasonal + 1, avr_viz_md)
cells.insert(idx_seasonal + 2, avr_viz_code)

idx_mk = next(i for i, c in enumerate(cells)
              if c["cell_type"] == "code" and "mann_kendall(" in "".join(c["source"])
              and "import" not in "".join(c["source"]))
cells.insert(idx_mk + 1, lstm_md)
cells.insert(idx_mk + 2, lstm_code)

nb["cells"] = cells
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — {len(nb['cells'])} celdas totales")
