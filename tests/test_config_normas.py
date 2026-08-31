"""Tests de trazabilidad normativa: ver ADR-020 en docs/adr/.

Valida que NORMA_FUENTES documente la procedencia legal de cada constante
normativa y que ninguna verificación esté vencida (>12 meses).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import pytest

from estadistica_ambiental import config
from estadistica_ambiental.config import ICA_BREAKPOINTS, NORMA_FUENTES

CAMPOS_REQUERIDOS = ("codigo", "articulo", "url_oficial", "fecha_verificacion")
ESTADOS_VALIDOS = {"vigente", "guia_no_vinculante", "derogado_sin_reemplazo_fijo"}

# Constantes de umbral normativo colombiano en config.py, con nombre en
# mayúsculas (convención del módulo). Se descubren por introspección para que
# una constante nueva no quede invisible a este test por olvido.
_CONSTANTES_NORMA_EN_CONFIG = {
    nombre
    for nombre in dir(config)
    if (nombre.startswith("NORMA_") or nombre == "ICA_BREAKPOINTS") and nombre != "NORMA_FUENTES"
}


class TestNormaFuentesCompletitud:
    def test_todas_las_normas_de_config_tienen_entrada(self):
        faltantes = _CONSTANTES_NORMA_EN_CONFIG - set(NORMA_FUENTES)
        assert not faltantes, f"Faltan en NORMA_FUENTES: {sorted(faltantes)}"

    def test_keys_en_mayusculas_corresponden_a_constantes_reales(self):
        """Si se renombra o elimina una constante, su entrada no debe quedar huérfana.

        Las keys en minúsculas (ej. "agua_potable_od_dbo5") son entradas de
        sub-campo, no constantes de config.py, y se validan aparte en
        test_campos_excluidos_existen_y_estan_cubiertos.
        """
        for clave in NORMA_FUENTES:
            if not clave.isupper():
                continue
            assert hasattr(config, clave), (
                f"NORMA_FUENTES['{clave}'] no corresponde a ninguna constante en config.py"
            )

    def test_campos_requeridos_no_vacios(self):
        for clave, fuente in NORMA_FUENTES.items():
            for campo in CAMPOS_REQUERIDOS:
                assert campo in fuente, f"NORMA_FUENTES['{clave}'] no tiene '{campo}'"
                assert fuente[campo], f"NORMA_FUENTES['{clave}']['{campo}'] está vacío"

    def test_url_oficial_es_https(self):
        url_pattern = re.compile(r"^https://[^\s]+\.[a-z]{2,}(/[^\s]*)?$", re.IGNORECASE)
        for clave, fuente in NORMA_FUENTES.items():
            assert url_pattern.match(fuente["url_oficial"]), (
                f"NORMA_FUENTES['{clave}']['url_oficial'] no parece una URL https válida: "
                f"{fuente['url_oficial']!r}"
            )

    def test_estado_si_esta_presente_es_valido(self):
        for clave, fuente in NORMA_FUENTES.items():
            estado = fuente.get("estado")
            if estado is not None:
                # El campo trae una nota legible ("derogado_sin_reemplazo_fijo: ...");
                # solo se valida el prefijo estructurado antes del separador ": ".
                codigo_estado = estado.split(": ")[0]
                assert codigo_estado in ESTADOS_VALIDOS, (
                    f"NORMA_FUENTES['{clave}']['estado'] tiene un valor no reconocido: "
                    f"{codigo_estado!r} (validos: {sorted(ESTADOS_VALIDOS)})"
                )

    def test_campos_excluidos_existen_y_estan_cubiertos(self):
        """Si NORMA_FUENTES['X']['excluye'] = ['campo'], 'campo' debe existir en
        config.X, y alguna otra entrada debe declararlo en su 'cubre' — no basta con
        que exista *alguna* entrada de sub-campo, tiene que ser la que documenta
        justo ese campo excluido."""
        cubiertos = {c for f in NORMA_FUENTES.values() for c in f.get("cubre", ())}
        for clave, fuente in NORMA_FUENTES.items():
            for campo in fuente.get("excluye", ()):
                assert hasattr(config, clave) and hasattr(getattr(config, clave), "__contains__"), (
                    f"NORMA_FUENTES['{clave}'] no corresponde a una constante indexable en config.py"
                )
                assert campo in getattr(config, clave), (
                    f"NORMA_FUENTES['{clave}'] excluye '{campo}', que no existe en config.{clave}"
                )
                assert f"{clave}.{campo}" in cubiertos, (
                    f"{clave}.{campo} está excluido pero ninguna entrada de NORMA_FUENTES "
                    f"lo declara en su campo 'cubre'"
                )


class TestIcaBreakpointsConsistencia:
    def test_co_breakpoints_conversion_consistente(self):
        """Los cortes de CO son la tabla EPA (ppm) convertida a mg/m³: el factor
        implícito debe ser el mismo en los 5, o hay un dígito mal transcrito
        (ver ADR-020, corrección 2026-07-25 de 10.189 a 10.789)."""
        ppm = [4.4, 9.4, 12.4, 15.4, 30.4]
        mg = ICA_BREAKPOINTS["co"][1:-1]
        factores = [m / p for p, m in zip(ppm, mg)]
        assert max(factores) - min(factores) < 0.02, (
            f"Factor ppm→mg/m³ inconsistente entre cortes de CO: {factores} "
            "(sugiere un dígito mal transcrito)"
        )


@pytest.mark.normativa_vigencia
class TestNormaFuentesVigencia:
    """Excluida de la suite por defecto (ver pyproject.toml addopts) porque expira
    con el calendario, no con cambios de código; solo debe correr en el job
    programado `normativa-audit` de scheduled.yml."""

    def test_ninguna_verificacion_supera_12_meses(self):
        hoy = date.today()
        limite = hoy - timedelta(days=366)  # 366 para no penalizar años bisiestos
        for clave, fuente in NORMA_FUENTES.items():
            try:
                fecha = date.fromisoformat(fuente["fecha_verificacion"])
            except ValueError as exc:
                pytest.fail(
                    f"NORMA_FUENTES['{clave}']['fecha_verificacion'] no es una fecha "
                    f"ISO válida: {fuente['fecha_verificacion']!r} ({exc})"
                )
            assert fecha <= hoy, (
                f"NORMA_FUENTES['{clave}']['fecha_verificacion'] ({fecha}) está en el futuro"
            )
            assert fecha >= limite, (
                f"NORMA_FUENTES['{clave}']['fecha_verificacion'] ({fecha}) "
                f"supera 12 meses de antigüedad; reverificar contra la fuente oficial"
            )
