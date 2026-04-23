"""
Visualizaciones estándar de EDA para datos ambientales.

Todas las funciones devuelven matplotlib Figure para que el caller
decida si mostrar, guardar o incrustar en un notebook/reporte.
No llaman plt.show() — control queda en el usuario.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Paleta ambiental consistente
_PALETTE = [
    "#1a5276",
    "#1e8449",
    "#a04000",
    "#7d3c98",
    "#17a589",
    "#b7950b",
    "#2e86c1",
    "#cb4335",
    "#117a65",
    "#6e2f8e",
]


# ---------------------------------------------------------------------------
# Series temporales
# ---------------------------------------------------------------------------


def plot_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_col: Optional[str] = None,
    title: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: tuple = (12, 4),
) -> plt.Figure:
    """Serie temporal simple o por grupo (una línea por categoría)."""
    fig, ax = plt.subplots(figsize=figsize)

    if group_col and group_col in df.columns:
        groups = df[group_col].dropna().unique()
        for i, grp in enumerate(groups):
            sub = df[df[group_col] == grp].sort_values(date_col)
            ax.plot(
                sub[date_col],
                sub[value_col],
                label=str(grp),
                color=_PALETTE[i % len(_PALETTE)],
                linewidth=1.2,
            )
        ax.legend(fontsize=8, ncol=min(4, len(groups)))
    else:
        data = df.sort_values(date_col)
        ax.plot(data[date_col], data[value_col], color=_PALETTE[0], linewidth=1.2)

    ax.set_title(title or f"{value_col} en el tiempo", fontweight="bold")
    ax.set_xlabel(date_col)
    ax.set_ylabel(ylabel or value_col)
    _format_date_axis(ax, df[date_col])
    fig.tight_layout()
    return fig


def plot_missing_heatmap(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    figsize: tuple = (12, 5),
) -> plt.Figure:
    """Mapa de calor de datos faltantes: filas=tiempo, columnas=variables."""
    num_df = df.select_dtypes(include="number")
    if num_df.empty:
        num_df = df

    missing = num_df.isnull().astype(int)

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(missing.T, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1, interpolation="none")

    ax.set_yticks(range(len(missing.columns)))
    ax.set_yticklabels(missing.columns, fontsize=8)
    ax.set_xlabel("Índice de fila" if not date_col else date_col)
    ax.set_title("Mapa de faltantes (rojo = ausente)", fontweight="bold")

    # Porcentaje al lado derecho
    for i, col in enumerate(missing.columns):
        pct = missing[col].mean() * 100
        ax.text(len(missing) + 1, i, f"{pct:.0f}%", va="center", fontsize=7, color="#555")

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Distribuciones
# ---------------------------------------------------------------------------


def plot_histogram(
    df: pd.DataFrame,
    col: str,
    bins: int = 30,
    group_col: Optional[str] = None,
    title: Optional[str] = None,
    figsize: tuple = (7, 4),
) -> plt.Figure:
    """Histograma con KDE superpuesta, opcional por grupo."""
    try:
        from scipy.stats import gaussian_kde

        has_scipy = True
    except ImportError:
        has_scipy = False

    fig, ax = plt.subplots(figsize=figsize)
    series = df[col].dropna()

    if group_col and group_col in df.columns:
        groups = df[group_col].dropna().unique()
        for i, grp in enumerate(groups):
            vals = df.loc[df[group_col] == grp, col].dropna()
            ax.hist(
                vals,
                bins=bins,
                alpha=0.45,
                color=_PALETTE[i % len(_PALETTE)],
                label=str(grp),
                density=True,
            )
            if has_scipy and len(vals) > 5:
                xs = np.linspace(vals.min(), vals.max(), 200)
                ax.plot(xs, gaussian_kde(vals)(xs), color=_PALETTE[i % len(_PALETTE)], lw=1.5)
        ax.legend(fontsize=8)
    else:
        ax.hist(series, bins=bins, color=_PALETTE[0], alpha=0.7, density=True, label="datos")
        if has_scipy and len(series) > 5:
            xs = np.linspace(series.min(), series.max(), 200)
            ax.plot(xs, gaussian_kde(series)(xs), color=_PALETTE[1], lw=2, label="KDE")
            ax.legend(fontsize=8)

    ax.set_title(title or f"Distribución de {col}", fontweight="bold")
    ax.set_xlabel(col)
    ax.set_ylabel("Densidad")
    fig.tight_layout()
    return fig


def plot_boxplot(
    df: pd.DataFrame,
    value_col: str,
    group_col: Optional[str] = None,
    title: Optional[str] = None,
    figsize: tuple = (8, 4),
) -> plt.Figure:
    """Boxplot por grupo o global."""
    fig, ax = plt.subplots(figsize=figsize)

    if group_col and group_col in df.columns:
        groups = sorted(df[group_col].dropna().unique())
        data = [df.loc[df[group_col] == g, value_col].dropna().values for g in groups]
        bp = ax.boxplot(data, patch_artist=True, tick_labels=[str(g) for g in groups])
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(_PALETTE[i % len(_PALETTE)])
            patch.set_alpha(0.7)
        ax.tick_params(axis="x", rotation=30)
    else:
        ax.boxplot(
            df[value_col].dropna(),
            patch_artist=True,
            boxprops={"facecolor": _PALETTE[0], "alpha": 0.7},
        )

    ax.set_title(title or f"Boxplot de {value_col}", fontweight="bold")
    ax.set_ylabel(value_col)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Correlaciones
# ---------------------------------------------------------------------------


def plot_correlation_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    cols: Optional[List[str]] = None,
    figsize: tuple = (8, 7),
) -> plt.Figure:
    """Heatmap de correlaciones con anotaciones numéricas."""
    num_df = (
        df[cols].select_dtypes(include="number") if cols else df.select_dtypes(include="number")
    )
    if num_df.shape[1] < 2:
        logger.warning("Se necesitan al menos 2 columnas numéricas para correlación")
        fig, ax = plt.subplots()
        ax.text(
            0.5,
            0.5,
            "Insuficientes columnas numéricas",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        return fig

    corr = num_df.corr(method=method)
    n = len(corr)
    figsize = (max(figsize[0], n * 0.8), max(figsize[1], n * 0.7))

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    fig.colorbar(im, ax=ax, fraction=0.04)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)

    for i in range(n):
        for j in range(n):
            val = corr.iloc[i, j]
            color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7, color=color)

    ax.set_title(f"Correlación {method.capitalize()}", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Estacionalidad y descomposición
# ---------------------------------------------------------------------------


def plot_seasonal_means(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    period: str = "month",
    figsize: tuple = (10, 4),
) -> plt.Figure:
    """Promedio mensual o por día de semana para detectar estacionalidad."""
    data = df[[date_col, value_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna()

    if period == "month":
        data["period"] = data[date_col].dt.month
        labels = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic",
        ]
        xlabel = "Mes"
    elif period == "weekday":
        data["period"] = data[date_col].dt.dayofweek
        labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        xlabel = "Día de la semana"
    elif period == "hour":
        data["period"] = data[date_col].dt.hour
        labels = [str(h) for h in range(24)]
        xlabel = "Hora del día"
    else:
        raise ValueError(f"period debe ser 'month', 'weekday' u 'hour'. Recibido: '{period}'")

    grouped = data.groupby("period")[value_col].agg(["mean", "std"]).reset_index()

    fig, ax = plt.subplots(figsize=figsize)
    periods = grouped["period"].values
    tick_labels = [labels[p] for p in periods] if len(labels) > max(periods) else periods

    ax.bar(
        range(len(periods)),
        grouped["mean"],
        color=_PALETTE[0],
        alpha=0.75,
        width=0.65,
        label="Media",
    )
    ax.errorbar(
        range(len(periods)),
        grouped["mean"],
        yerr=grouped["std"],
        fmt="none",
        color="#555",
        capsize=4,
        linewidth=1,
    )

    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels(tick_labels, fontsize=9)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(value_col)
    ax.set_title(f"Media estacional de {value_col} por {xlabel.lower()}", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Múltiples variables
# ---------------------------------------------------------------------------


def plot_multi_series(
    df: pd.DataFrame,
    date_col: str,
    value_cols: Sequence[str],
    title: Optional[str] = None,
    figsize: tuple = (12, 3),
) -> plt.Figure:
    """Subplots independientes, uno por variable, compartiendo eje X."""
    n = len(value_cols)
    fig, axes = plt.subplots(n, 1, figsize=(figsize[0], figsize[1] * n), sharex=True)
    if n == 1:
        axes = [axes]

    data = df.sort_values(date_col)
    for ax, col, color in zip(axes, value_cols, _PALETTE):
        ax.plot(data[date_col], data[col], color=color, linewidth=1.1)
        ax.set_ylabel(col, fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    axes[-1].set_xlabel(date_col)
    if title:
        fig.suptitle(title, fontweight="bold", y=1.01)
    _format_date_axis(axes[-1], df[date_col])
    fig.tight_layout()
    return fig


def plot_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    title: Optional[str] = None,
    figsize: tuple = (6, 5),
) -> plt.Figure:
    """Scatter plot con línea de regresión y coloreado opcional por categoría."""
    fig, ax = plt.subplots(figsize=figsize)
    data = df[[x_col, y_col]].dropna()

    if color_col and color_col in df.columns:
        cats = df[color_col].dropna().unique()
        for i, cat in enumerate(cats):
            mask = df[color_col] == cat
            sub = df.loc[mask, [x_col, y_col]].dropna()
            ax.scatter(
                sub[x_col],
                sub[y_col],
                label=str(cat),
                color=_PALETTE[i % len(_PALETTE)],
                alpha=0.6,
                s=25,
            )
        ax.legend(fontsize=8)
    else:
        ax.scatter(data[x_col], data[y_col], color=_PALETTE[0], alpha=0.5, s=25)

    # Línea de regresión sobre datos completos
    if len(data) >= 3:
        m, b = np.polyfit(data[x_col], data[y_col], 1)
        xs = np.linspace(data[x_col].min(), data[x_col].max(), 100)
        ax.plot(xs, m * xs + b, color="#e74c3c", linewidth=1.5, linestyle="--", label="Regresión")

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{x_col} vs {y_col}", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------


def _format_date_axis(ax: plt.Axes, dates: pd.Series) -> None:
    """Auto-formato del eje de fechas según el rango temporal."""
    try:
        dates_parsed = pd.to_datetime(dates, errors="coerce").dropna()
        if len(dates_parsed) < 2:
            return
        span_days = (dates_parsed.max() - dates_parsed.min()).days
        if span_days > 365 * 2:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax.xaxis.set_major_locator(mdates.YearLocator())
        elif span_days > 90:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
    except Exception:
        pass
