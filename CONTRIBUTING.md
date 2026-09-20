# Guía de contribución

Gracias por interesarte en `estadistica-ambiental`. Este es un proyecto de un solo mantenedor,
así que el flujo es corto: abre un issue, trabaja en una rama y envía un PR.

## Preparar el entorno

Requiere Python >= 3.10.

```bash
git clone https://github.com/DanMendezZz/Estadistica_Ambiental.git
cd Estadistica_Ambiental
pip install -e ".[dev,docs]"
pre-commit install
```

El extra `docs` es necesario porque el hook `mkdocs-build-strict` de pre-commit ejecuta
`mkdocs build --strict`. Los módulos pesados son *extras* opcionales (`ml`, `bayes`, `spatial`,
`deep`, `prophet`, `netcdf`, `profile`, `fast`): instala solo los que necesites, por ejemplo
`pip install -e ".[dev,docs,ml,spatial]"`. Los tests que dependen de un extra se saltan solos si
no está instalado.

## Flujo de trabajo

1. Abre un issue describiendo el bug o la mejora (hay plantillas).
2. Crea una rama desde `main`. El hook `no-commit-to-branch` impide commitear directo a `main`.
3. Haz cambios pequeños y enfocados, con tests.
4. Antes de enviar el PR, corre lo mismo que corre el CI:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest
mkdocs build --strict   # si tocaste docs/, src/ o mkdocs.yml (lo corre el hook)
```

5. Abre el PR usando la plantilla y enlaza el issue (`Closes #N`).

## Decisiones metodológicas (ADRs)

Si tu cambio toma una decisión metodológica (un umbral, una norma, un supuesto estadístico),
documéntala como ADR en [`docs/adr/`](docs/adr/) y enlázala desde
[`docs/decisiones.md`](docs/decisiones.md). Las normas colombianas viven centralizadas en el
código, no hardcodeadas por script.

## Reportar un problema de seguridad

No abras un issue público: sigue [`SECURITY.md`](SECURITY.md).

## Conducta

Al participar aceptas el [Código de Conducta](CODE_OF_CONDUCT.md).
