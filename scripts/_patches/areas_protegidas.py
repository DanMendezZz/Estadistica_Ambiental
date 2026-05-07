"""Enrichment areas_protegidas: Random Forest para prediccion de deforestacion."""

from __future__ import annotations

from ._helpers import (
    already_enriched,
    code,
    find_mk,
    fix_walk_forward_gap,
    insert_after,
    marker,
    md,
)

KEY = "areas_protegidas"


def apply(nb: dict) -> None:
    cells = nb["cells"]
    if already_enriched(cells, KEY):
        return

    fix_walk_forward_gap(cells)

    rf_md = md(
        f"{marker(KEY)}\n\n"
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

    rf_code = code(
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

    insert_after(cells, find_mk(cells), [rf_md, rf_code])
