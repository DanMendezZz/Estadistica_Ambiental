# ADR-018 — Patrón base↔satélite: separación entre librería y productos consumidores

**Fecha:** 2026-05-07
**Estado:** Aceptado — instanciado por primera vez con `Estadistica_Ambiental_Dashboard`

## Contexto

Durante la sesión 2026-05-07 emergió la pregunta concreta: dónde vive un
dashboard Streamlit que opera sobre datos de calidad del aire. Dos modelos
posibles:

1. **Todo dentro del repo base** — incluir un módulo `dashboard/` o `app/`
   con la app Streamlit, sus configs de deploy y posiblemente datos crudos.
2. **Repo satélite separado** — la app vive en su propio repositorio y consume
   `estadistica-ambiental` como dependencia desde PyPI.

Sin una decisión explícita, la primera opción es tentadora (todo en un solo
sitio) pero diluye la promesa del repo: ser una **base de conocimiento +
librería** estable, citable, reutilizable, instalable con `pip install
estadistica-ambiental` desde cualquier proyecto.

## Decisión

**Adoptar el patrón base↔satélite:**

- **`Estadistica_Ambiental` (este repo)** — librería + plantillas + fichas de
  dominio. Se publica en PyPI como `estadistica-ambiental`. Tiene su propio
  versionado SemVer y su propio CI. **No contiene** apps de cliente,
  dashboards específicos, pipelines ETL nocturnos, datos crudos ni
  configuraciones de deploy productivo.

- **Satélites** — repos separados que importan `estadistica-ambiental` como
  dependencia. Ejemplos materializados o previstos:
  - `Estadistica_Ambiental_Dashboard` (Streamlit, calidad del aire genérico) — ✅ activo.
  - `calidad-aire-CAR` (dashboard CAR-específico) — previsto.
  - `paramos-rabanal`, `pomca-magdalena`, etc. — previstos.

  Cada satélite tiene su propio versionado, deploy y CI. Pinea la versión
  exacta de la base en su `requirements.txt` (ej. `estadistica-ambiental==1.3.2`).

## Reglas operativas

**Lo que SÍ va en el repo base:**

- Módulos en `src/` (estadística, validación, conectores genéricos, reportes
  HTML reutilizables).
- Conectores oficiales a fuentes ambientales colombianas (OpenAQ, SISAIRE,
  RMCAB, IDEAM DHIME, SMByC).
- Notebooks plantilla por línea temática en `notebooks/lineas_tematicas/`.
- Fichas de dominio en `docs/fuentes/<linea>.md`.
- ADRs en `docs/decisiones.md` y `docs/adr/`.
- Tests genéricos.
- Empaquetado para PyPI / install-from-git.

**Lo que NO va en el repo base:**

- Apps Streamlit, Dash, Shiny, etc.
- Dashboards específicos de un cliente o entidad (CAR, Corpoboyacá, etc.).
- Pipelines ETL nocturnos / cron jobs operativos.
- Configuraciones de deploy productivo (Docker compose para producción,
  Helm charts, configuraciones de Streamlit Cloud específicas).
- Datos crudos del cliente (ya cubierto por `.gitignore`).

## Coupling y versionado

- Los satélites pinean la **versión exacta** de la base
  (`estadistica-ambiental==X.Y.Z`), no rangos abiertos. Razón: garantiza
  reproducibilidad y aísla a cada satélite de releases breaking de la base.
- Cuando el satélite necesita una función no expuesta en la base, se evalúa:
  - ¿Es genérica y útil para múltiples satélites? → PR a la base, release
    nueva, satélite bumpea pin.
  - ¿Es específica del satélite? → vive en el satélite, no contamina la base.
- La base **nunca** depende de un satélite. La dirección del coupling es
  unidireccional: satélite → base.

## Scaffolding del primer satélite (referencia)

`Estadistica_Ambiental_Dashboard` establece el patrón replicable:

```
Estadistica_Ambiental_Dashboard/
├── app.py                              # Streamlit entrypoint
├── src/dashboard/
│   ├── data.py                         # Carga datos (demo o real)
│   ├── plots.py                        # Wrappers Plotly específicos del producto
│   ├── pages.py                        # Una función por tab
│   └── __init__.py
├── requirements.txt                    # estadistica-ambiental==X.Y.Z + streamlit
├── pyproject.toml                      # ruff, version, etc.
├── .streamlit/config.toml              # Tema, page config
├── .github/workflows/deploy.yml        # smoke headless + ruff
├── .gitignore
└── README.md
```

Para un nuevo satélite, copiar esta estructura y reemplazar la lógica de
páginas. La base permanece intacta.

## Consecuencias

- **Trazabilidad clara** de qué es metodología (base) vs. producto (satélite).
- **Reutilización** — agregar una segunda corporación regional no requiere
  fork ni mantenimiento del repo base; se crea un satélite nuevo.
- **Versionado limpio** — la base versiona su API; los satélites versionan
  su producto. Sin acoplamiento de release schedules.
- **Memoria de Claude Code** ya refleja esta regla
  (`feedback_repo_es_base_de_conocimiento.md`): cuando emerge una idea de
  "agregar un dashboard al repo", redirigir a un satélite nuevo.
- **Reevaluar** si en algún momento el repo base requiere una app de
  referencia mínima para demostrar uso (ej. un quickstart Streamlit). En ese
  caso, vivir en `examples/` con una nota explícita "este es ejemplo, no
  producto" — y no en `src/`.

## Referencias

- Primer satélite: <https://github.com/DanMendezZz/Estadistica_Ambiental_Dashboard>.
- Memoria correlacionada: `feedback_repo_es_base_de_conocimiento.md`.
- Plan §13 entry "2026-05-07 — Release v1.3.2 + JupyterLite + Fase 10 + primer satélite".
- Commit: scaffolding del satélite (repo aparte), referencia desde la base.
