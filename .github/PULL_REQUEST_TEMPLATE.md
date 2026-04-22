## Descripción

<!-- ¿Qué cambia y por qué? Enlazar al issue si aplica: Closes #XX -->

## Tipo de cambio

- [ ] `feat` — nueva funcionalidad
- [ ] `fix` — corrección de bug
- [ ] `refactor` — refactorización sin cambio funcional
- [ ] `test` — agregar o corregir tests
- [ ] `docs` — documentación
- [ ] `chore` — mantenimiento (dependencias, CI, etc.)

## Módulos afectados

<!-- Ej: io/loaders.py, eda/quality.py -->

## Checklist

- [ ] Los tests pasan localmente (`python -m pytest tests/ -q`)
- [ ] El linter pasa (`ruff check src/ tests/`)
- [ ] Se agregaron tests para la funcionalidad nueva
- [ ] Se actualizó `CHANGELOG.md` si es un cambio visible
- [ ] No se incluyen datos crudos ni credenciales
- [ ] Si hereda de `boa-sarima-forecaster`: docstring de atribución incluido

## Decisiones de diseño

<!-- Si tomaste una decisión no obvia, documentarla aquí o en docs/decisiones.md -->

## Notas para el revisor

<!-- Contexto adicional, áreas a revisar con cuidado, limitaciones conocidas -->
