# Plantilla — Bloque hijo reutilizable (R Markdown / Jupyter)

> **Propósito.** Patrón canónico para escribir sub-secciones reutilizables (estilo *child Rmd* o *parametrized notebook block*) que se puedan insertar en cualquier notebook temático del repo `Estadistica_Ambiental`.
>
> **Uso.** Copiar este archivo a `docs/templates/childs/<nombre>.md` (o a un `.Rmd` / celda Markdown del notebook padre) y rellenar las secciones marcadas con `<...>`. El bloque debe correr **sin modificaciones** siempre que el notebook padre exponga las variables listadas en *Parámetros esperados*.
>
> **Origen.** Item M-06 del `Plan.md §13`. Inspirado en el patrón "plantilla madre + N hijos parametrizables" descrito en `Plan/Feedback/repo_estadistica_ambiental_feedback.md §3.1.C`.

---

## 1. Frontmatter

Cabecera YAML mínima al inicio del archivo hijo. Sirve tanto para `knitr::knit_child()` (R Markdown) como metadato para scripts generadores en Python.

```yaml
---
title: "<Nombre del bloque — ej. Panel de cumplimiento normativo>"
slug: "<panel_cumplimiento>"            # identificador único (snake_case)
linea_tematica: "<calidad_aire>"        # key de docs/fuentes/ (o "transversal")
audiencia: ["analista", "tomador_decisiones"]   # target del bloque
dependencies:
  python: ">=3.10"
  packages:
    - "estadistica_ambiental>=0.x"
    - "pandas>=2.0"
    - "matplotlib>=3.7"
  modulos_repo:
    - "estadistica_ambiental.inference.intervals.exceedance_report"
    - "estadistica_ambiental.config.NORMA_CO"
inputs:                                 # ver §3 para detalle
  - df: "DataFrame con columna fecha y la(s) variable(s) objetivo"
  - variable: "str — nombre de la columna a evaluar (ej. 'pm25')"
outputs:                                # ver §4 para detalle
  - "tabla_excedencias: pd.DataFrame"
  - "fig_panel: matplotlib.figure.Figure"
  - "data/output/figures/<linea>_<slug>.png"
adr_referenciados: ["ADR-005", "ADR-008"]
ultima_revision: "YYYY-MM-DD"
autor: "<nombre>"
---
```

---

## 2. Descripción breve

Una a tres frases que respondan: ¿qué hace el bloque? ¿en qué notebooks se usa típicamente? ¿qué pregunta de negocio responde?

> Ejemplo. *Genera un panel visual + tabla con excedencias de la norma colombiana (Res. 2254/2017) y guías OMS 2021 para una variable de calidad del aire. Pensado para insertarse en la sección "Cumplimiento" de cualquier notebook del bloque A.*

---

## 3. Parámetros esperados

Variables que el **notebook padre** debe tener definidas en su `globals()` antes de invocar el child. Usar exactamente estos nombres para que el bloque sea drop-in.

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|---|
| `df` | `pd.DataFrame` | Sí | Dataset limpio (post-validación + imputación) | `df_clean` |
| `DATE_COL` | `str` | Sí | Columna de fecha | `"fecha"` |
| `VARIABLE` | `str` | Sí | Variable objetivo a analizar | `"pm25"` |
| `UNIDAD` | `str` | Sí | Unidad de medida (sólo display) | `"µg/m³"` |
| `LINEA` | `str` | Sí | Línea temática para rutas y contexto de dominio | `"calidad_aire"` |
| `<extra>` | `<tipo>` | No | <descripción> | <ejemplo> |

**Pre-condiciones.** Indicar qué validaciones debe haber pasado el dataset antes de este bloque (ej. *"`ea.validate(df, linea_tematica=LINEA)` ya ejecutada y sin errores físicos"*).

---

## 4. Salidas producidas

Objetos que el child deja en el namespace del padre (para reutilización aguas abajo) y artefactos persistidos a disco.

**En memoria.**

| Nombre | Tipo | Contenido |
|---|---|---|
| `tabla_excedencias` | `pd.DataFrame` | columnas: `norma`, `umbral`, `n_excedencias`, `pct_excedencia` |
| `fig_panel` | `matplotlib.figure.Figure` | panel 2×2: serie + histograma + box estacional + barras norma |

**En disco.**

| Ruta | Formato | Cuándo |
|---|---|---|
| `data/output/figures/<LINEA>_<slug>.png` | PNG 300 dpi | siempre |
| `data/output/tables/<LINEA>_<slug>.csv` | CSV UTF-8 | siempre |
| `data/output/reports/<LINEA>_<slug>.html` | HTML | si `EXPORT_HTML = True` |

> **Convención de rutas.** Toda salida persistida bajo `data/output/{figures,tables,reports}/` y prefijada con `<LINEA>_<slug>` para evitar colisiones entre notebooks.

---

## 5. Bloque de código (ejemplo)

```python
# === CHILD: <slug> =========================================================
# Requiere en el padre: df, DATE_COL, VARIABLE, UNIDAD, LINEA
# Produce: tabla_excedencias, fig_panel + artefactos en data/output/

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from estadistica_ambiental.inference.intervals import exceedance_report

# --- 0. Validación de pre-condiciones --------------------------------------
_REQ = ["df", "DATE_COL", "VARIABLE", "UNIDAD", "LINEA"]
_missing = [v for v in _REQ if v not in globals()]
if _missing:
    raise NameError(f"Child '<slug>' requiere variables del padre: {_missing}")

# --- 1. Cómputo principal --------------------------------------------------
serie = df.set_index(DATE_COL)[VARIABLE].dropna()
tabla_excedencias = exceedance_report(serie, variable=VARIABLE)

# --- 2. Visualización ------------------------------------------------------
fig_panel, axes = plt.subplots(2, 2, figsize=(12, 7))
axes[0, 0].plot(serie.index, serie.values, lw=0.8)
axes[0, 0].set_title(f"Serie — {VARIABLE} ({UNIDAD})")
axes[0, 1].hist(serie.values, bins=40)
axes[0, 1].set_title("Distribución")
serie.groupby(serie.index.month).mean().plot.bar(ax=axes[1, 0])
axes[1, 0].set_title("Media mensual")
tabla_excedencias.plot.bar(x="norma", y="pct_excedencia", ax=axes[1, 1], legend=False)
axes[1, 1].set_title("% excedencia por norma")
fig_panel.suptitle(f"Panel <slug> — {LINEA}", fontweight="bold")
fig_panel.tight_layout()

# --- 3. Persistencia -------------------------------------------------------
_slug = "<slug>"
_outdir_fig = Path("data/output/figures"); _outdir_fig.mkdir(parents=True, exist_ok=True)
_outdir_tab = Path("data/output/tables");  _outdir_tab.mkdir(parents=True, exist_ok=True)
fig_panel.savefig(_outdir_fig / f"{LINEA}_{_slug}.png", dpi=300, bbox_inches="tight")
tabla_excedencias.to_csv(_outdir_tab / f"{LINEA}_{_slug}.csv", index=False)

print(f"[child:{_slug}] OK — {len(tabla_excedencias)} normas evaluadas")
# === FIN CHILD =============================================================
```

> **Convención de marcadores.** Abrir y cerrar siempre con `# === CHILD: <slug> ===` / `# === FIN CHILD ===` para que sea trivial localizar y refactorizar bloques entre notebooks.

---

## 6. Cómo invocar este child

**Desde Jupyter (vía `%run` o `nbformat`).**

```python
# En el notebook padre, después de definir df, DATE_COL, VARIABLE, UNIDAD, LINEA:
%run docs/templates/childs/<slug>.py    # versión .py exportada
# o pegar el bloque directamente como celda
```

**Desde R Markdown.**

```rmd
```{r, child = "docs/templates/childs/<slug>.Rmd"}
```
```

**Desde script generador (patrón "plantilla madre + N hijos").**

```python
# scripts/build_child_<slug>.py
from jinja2 import Template
plantilla = Template(Path("docs/templates/rmd_child_template.md").read_text())
for estacion in estaciones:
    Path(f"reports/{estacion}.md").write_text(plantilla.render(estacion=estacion))
```

---

## 7. Notas de reproducibilidad

- **Aleatoriedad.** Si el bloque usa muestreo o modelos estocásticos, fijar `np.random.seed(42)` al inicio y dejarlo explícito en *Parámetros esperados*.
- **Versionado.** El campo `dependencies.packages` debe pinear versiones mínimas; correr `pip freeze | grep <pkg>` al cerrar el bloque y registrar cambios mayores.
- **Rutas.** Usar siempre rutas relativas a la raíz del repo (`data/output/...`), nunca rutas absolutas locales — esto rompe portabilidad y CI.
- **Datos.** No incrustar datos en el child. Si el bloque necesita un fixture, cargarlo desde `data/raw/` o `data/processed/` con un loader oficial (`ea.load(...)`, `load_openaq`, `load_rmcab`, etc.).
- **Idempotencia.** El bloque debe poder ejecutarse N veces sin acumular efectos secundarios (sobreescribe artefactos, no concatena).
- **Side-effects controlados.** Evitar `plt.show()` dentro del child si se usa en pipelines headless (CI, JupyterLite); preferir `fig_panel` como salida y dejar al padre decidir el render.
- **Tests.** Si el child es de uso frecuente, agregar un smoke test en `tests/test_childs/test_<slug>.py` que sólo verifique que corre con un mini-fixture y produce las salidas declaradas.
- **ADRs.** Cuando el child encapsula una decisión metodológica (ej. lag ENSO, umbrales OMS), referenciar el ADR correspondiente en el frontmatter (`adr_referenciados`) y citar `docs/decisiones.md` en la descripción.

---

## 8. Checklist antes de promover un child a `docs/templates/childs/`

- [ ] Frontmatter completo y `slug` único en el repo.
- [ ] Parámetros esperados validados explícitamente al inicio (ver §5, paso 0).
- [ ] Salidas documentadas y persistidas con la convención `<LINEA>_<slug>.<ext>`.
- [ ] Sin rutas absolutas, sin credenciales, sin datos embebidos.
- [ ] Probado en al menos dos notebooks de líneas distintas.
- [ ] Smoke test agregado si el child es reutilizado >2 veces.
- [ ] Entrada nueva en `Plan.md §11` (seguimiento) si es la primera vez que se publica.
