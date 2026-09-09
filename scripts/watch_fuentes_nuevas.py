"""Watcher semanal de fuentes ambientales nuevas en datos.gov.co (issue #15).

Nunca commitea nada: solo imprime un resumen. El workflow que lo invoca
(`.github/workflows/scheduled.yml`, job `fuentes-watcher`) abre un Issue si
este script sale con código 1 (encontró datasets dados de alta recientemente).

Se filtra por `created` (fecha de alta del dataset en el portal), no por
`updated`: varios datasets de calidad del aire/caudal se refrescan a diario,
así que filtrar por "última actualización" dispararía todas las semanas con
los mismos datasets de siempre en vez de detectar fuentes genuinamente nuevas.

IDEAM DHIME y SMByC no tienen API pública utilizable desde este repo (acceso
manual, ver bitácora de la sesión 1) — no se intentan automatizar aquí; el
resultado solo deja un recordatorio para revisarlos a mano.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from estadistica_ambiental.io.connectors import list_datasets_co

# Una query representativa por línea temática con mayor probabilidad de tener
# datasets propios en datos.gov.co (donde IDEAM y varias CAR publican).
QUERIES: dict[str, str] = {
    "Calidad del aire": "calidad aire",
    "Oferta hídrica": "caudal",
    "Recurso hídrico": "calidad agua",
    "Páramos": "paramos",
    "Humedales": "humedales",
    "Cambio climático": "cambio climatico",
    "Gestión de riesgo": "gestion riesgo",
    "Sistemas de información (deforestación/GEI)": "deforestacion",
}

VENTANA_DIAS = 9  # cron semanal (7 días) + margen de 2 días
# views.json ordena por relevancia al término de búsqueda, no por fecha — un
# dataset recién creado puede no ser aún "relevante"; un límite bajo lo deja
# fuera del top-N y nunca se detecta.
LIMITE_POR_QUERY = 20


def _parse_epoch(value: object) -> datetime | None:
    """Convierte un epoch en segundos (puede venir como str/int/float/None/NaN) a datetime UTC.

    Devuelve None ante cualquier valor faltante o fuera de rango en vez de
    propagar — un dataset con metadata rara no debe tumbar el watcher entero.
    """
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)  # type: ignore[arg-type]
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def main() -> int:
    limite = datetime.now(timezone.utc) - timedelta(days=VENTANA_DIAS)
    hallazgos: list[str] = []

    for linea, query in QUERIES.items():
        # list_datasets_co ya atrapa sus propios errores de red/parseo y
        # devuelve un DataFrame vacío — si datos.gov.co está caído, todas las
        # queries vuelven vacías y el script sale 0 (sin Issue falso).
        df = list_datasets_co(query=query, limit=LIMITE_POR_QUERY)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            creado = _parse_epoch(row.get("created"))
            if creado is None or creado < limite:
                continue
            hallazgos.append(
                f"- **{linea}**: [{row['name']}]({row['url']}) "
                f"({row['organization']}, dado de alta {creado:%Y-%m-%d})"
            )

    if hallazgos:
        print(f"## Posibles fuentes nuevas en datos.gov.co (últimos {VENTANA_DIAS} días)\n")
        print("\n".join(hallazgos))
        print(
            "\n## Recordatorio manual\n\n"
            "IDEAM DHIME y SMByC son de acceso manual (sin API pública utilizable "
            "desde este repo) — revisarlos aparte si aplica a alguna línea temática."
        )
        return 1  # señal para que el workflow abra un Issue
    print("Sin fuentes nuevas detectadas en datos.gov.co esta semana.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
