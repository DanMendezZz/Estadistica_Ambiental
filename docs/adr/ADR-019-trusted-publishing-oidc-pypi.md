# ADR-019 — Trusted Publishing (OIDC) en PyPI sin tokens de larga vida

**Fecha:** 2026-05-07
**Estado:** Aceptado — activo desde release v1.3.2

## Contexto

Antes de v1.3.2 el repo publicaba en TestPyPI usando un API token de larga
vida almacenado como GitHub Actions secret (`TEST_PYPI_API_TOKEN`). Para
activar publicación a PyPI real había dos caminos:

1. **API token de PyPI real** — registrar otro token, almacenarlo como secret,
   replicar el flujo de TestPyPI. Riesgo: el token vive indefinidamente en
   GitHub. Si se filtra (logs, fork compromiso, leak de secret) un atacante
   puede publicar paquetes maliciosos hasta que se revoque manualmente.
2. **Trusted Publishing (OIDC)** — PyPI confía en GitHub Actions vía OpenID
   Connect. El workflow recibe un token efímero (~10 min) por job, scoped al
   repo + workflow + environment específicos. No hay secret persistente que
   robar.

PyPI lanzó Trusted Publishing como GA en 2023. La tecnología está madura,
soportada por `pypa/gh-action-pypi-publish@release/v1` y documentada en
<https://docs.pypi.org/trusted-publishers/>.

## Decisión

**Adoptar Trusted Publishing vía OIDC** para publicación a PyPI real. Razones:

- **Ningún token persistente** que pueda filtrarse o requerir rotación
  manual. El riesgo de credential leak se elimina por construcción.
- **Scope mínimo** — el publisher está restringido a `DanMendezZz/Estadistica_Ambiental`,
  workflow `release.yml`, sin necesidad de configurar environment.
- **Auditoría natural** — cada release queda trazado en GitHub Actions logs +
  PyPI history sin necesidad de monitorear uso de un token compartido.
- **Recovery codes** — los recovery codes de PyPI siguen siendo necesarios
  para acceso a la cuenta (account-level), pero ya no son la línea de defensa
  para publicación.

## Implementación

`.github/workflows/release.yml`, JOB 6 `publish-pypi`:

```yaml
publish-pypi:
  needs: [build-and-publish-testpypi]
  runs-on: ubuntu-latest
  permissions:
    id-token: write   # OIDC token para PyPI Trusted Publishing
  steps:
    - uses: actions/download-artifact@v4
      with:
        name: dist
    - uses: pypa/gh-action-pypi-publish@release/v1
      # sin password ni token — OIDC se negocia automáticamente
```

**Configuración en PyPI:** registrado como Trusted Publisher en
`pypi.org/manage/account/publishing/` con:
- Owner: `DanMendezZz`
- Repository: `Estadistica_Ambiental`
- Workflow: `release.yml`
- Environment: (no requerido para este repo)

**Flujo completo:**
1. `git tag vX.Y.Z`
2. `git push --tags`
3. `release.yml` se dispara: build → publish-testpypi → publish-pypi.
4. PyPI valida el OIDC token, confirma que viene del workflow autorizado, y
   acepta la publicación.

## Decisiones colaterales

- **TestPyPI** sigue usando API token (`TEST_PYPI_API_TOKEN`). Trusted
  Publishing también es soportado por TestPyPI, pero migrar TestPyPI no es
  prioritario porque su superficie de riesgo es menor (paquetes de prueba,
  no consumidos por usuarios finales). **Reevaluar** en 12 meses o cuando
  rotemos el token de TestPyPI por cualquier otra razón.
- **Recovery codes** — Dan regeneró los recovery codes de TestPyPI durante
  esta sesión por higiene general (no relacionado con la decisión OIDC).

## Consecuencias

- **Cero secrets de PyPI real en el repo.** El único secret de publicación
  es el token de TestPyPI (cuyo blast radius es mínimo).
- **Releases automatizados** — cualquier `git tag vX.Y.Z && git push --tags`
  publica a PyPI real. No requiere intervención manual ni acceso a la cuenta
  PyPI. Esto es deseable y peligroso a la vez: cualquier persona con permiso
  de `git push --tags` puede publicar. Mitigación: el repo sigue siendo
  unipersonal; si crece el equipo, configurar branch protection + tag
  protection en GitHub.
- **Si Dan pierde acceso a la cuenta GitHub o el repo cambia de owner**, el
  Trusted Publisher hay que reconfigurar en PyPI manualmente. Documentado.
- **Los runners self-hosted no están autorizados** — el OIDC issuer es
  `https://token.actions.githubusercontent.com`, válido solo para runners
  hosted de GitHub. Si en algún momento se migra a self-hosted, este flujo
  rompe. Reevaluar entonces.

## Referencias

- PyPA docs: <https://docs.pypi.org/trusted-publishers/>.
- Workflow: `.github/workflows/release.yml` (job `publish-pypi`).
- PyPI URL: <https://pypi.org/project/estadistica-ambiental/>.
- Plan §13 entry "2026-05-07 — Release v1.3.2 + JupyterLite + Fase 10 + primer satélite".
- Commit que activó OIDC: `ef276c5`.
