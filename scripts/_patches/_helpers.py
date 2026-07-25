"""Helpers compartidos para los enrichments de notebooks por línea temática.

Cada enrichment usa los mismos patrones:
- factories `md(...)` y `code(...)` con id estable por hash
- detectores de celdas ancla (`find_data`, `find_seasonal`, `find_mk`, `find_rank`)
- detector de marker para idempotencia
- fix transversal `walk_forward(..., gap=12, ...)`
"""

from __future__ import annotations

import hashlib
from typing import Iterable

# ---- Marker ---------------------------------------------------------------
# Los enrichments insertan en la 1ra celda markdown un comentario HTML
# `<!-- ENRICHMENT: <key> -->`. Si ese marker ya está presente, no se duplica.

MARKER_PREFIX = "<!-- ENRICHMENT:"


def already_enriched(cells: list, key: str) -> bool:
    """True si alguna celda contiene el marker ENRICHMENT:<key>."""
    needle = f"{MARKER_PREFIX} {key} -->"
    for c in cells:
        if needle in "".join(c.get("source", "")):
            return True
    return False


def marker(key: str) -> str:
    """Retorna el comentario HTML de marker (oculto al renderizar)."""
    return f"<!-- {MARKER_PREFIX[5:].strip()} {key} -->"


# ---- Cell factories -------------------------------------------------------
# IDs deterministas (basados en hash del contenido) para que el notebook
# resultante sea estable entre corridas y diff-friendly.

def _stable_id(prefix: str, src: str) -> str:
    h = hashlib.md5(src.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{h}"


def md(src: str) -> dict:
    """Crea una celda markdown con id estable (md5 del contenido)."""
    return {
        "cell_type": "markdown",
        "id": _stable_id("m", src),
        "metadata": {},
        "source": src,
    }


def code(src: str) -> dict:
    """Crea una celda code con id estable (md5 del contenido)."""
    return {
        "cell_type": "code",
        "id": _stable_id("c", src),
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": src,
    }


# ---- Anchor finders -------------------------------------------------------

def _src(cell: dict) -> str:
    return "".join(cell.get("source", ""))


def find_data(cells: list) -> int:
    """Índice de la celda code con datos sintéticos de ejemplo."""
    return next(
        i for i, c in enumerate(cells)
        if c["cell_type"] == "code" and "sintéticos de ejemplo" in _src(c)
    )


def find_seasonal(cells: list) -> int:
    """Índice de la celda code que LLAMA a plot_seasonal_means (no la importa)."""
    return next(
        i for i, c in enumerate(cells)
        if c["cell_type"] == "code"
        and "plot_seasonal_means(" in _src(c)
        and "import" not in _src(c)
    )


def find_mk(cells: list) -> int:
    """Índice de la celda code que LLAMA a mann_kendall (no la importa)."""
    return next(
        i for i, c in enumerate(cells)
        if c["cell_type"] == "code"
        and "mann_kendall(" in _src(c)
        and "import" not in _src(c)
    )


def find_rank(cells: list) -> int:
    """Índice de la celda code que LLAMA a rank_models(results)."""
    return next(
        i for i, c in enumerate(cells)
        if c["cell_type"] == "code" and "rank_models(results)" in _src(c)
    )


def find_first(cells: list, needle: str) -> int:
    """Índice de la primera celda code que contiene `needle`."""
    return next(
        i for i, c in enumerate(cells)
        if c["cell_type"] == "code" and needle in _src(c)
    )


# ---- Fixes transversales --------------------------------------------------

def fix_walk_forward_gap(cells: list) -> None:
    """Reemplaza in-place `walk_forward(model, ts, horizon=...)` por
    `walk_forward(model, ts, gap=12, horizon=...)` (idempotente)."""
    for i, c in enumerate(cells):
        src = _src(c)
        if (c["cell_type"] == "code"
                and "walk_forward(model, ts" in src
                and "gap=" not in src):
            cells[i]["source"] = src.replace(
                "walk_forward(model, ts, horizon=",
                "walk_forward(model, ts, gap=12, horizon=",
            )


def insert_after(cells: list, idx: int, new_cells: Iterable[dict]) -> None:
    """Inserta `new_cells` justo después de `cells[idx]`."""
    for off, cell in enumerate(new_cells, start=1):
        cells.insert(idx + off, cell)


__all__ = [
    "already_enriched",
    "marker",
    "md",
    "code",
    "find_data",
    "find_seasonal",
    "find_mk",
    "find_rank",
    "find_first",
    "fix_walk_forward_gap",
    "insert_after",
]
