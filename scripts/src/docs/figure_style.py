"""Shared styling for documentation and thesis figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import plotly.io as pio


LABCIN_BLUE = "#365cc1"
LABCIN_GREEN = "#60aa26"
LABCIN_LIGHT_GREEN = "#8ac530"
LABCIN_LIME = "#b1de39"
LABCIN_SILVER = "#cccccc"
LABCIN_DARK = "#17315f"
LABCIN_TEAL = "#00a6a6"
LABCIN_GOLD = "#f5b700"
LABCIN_CORAL = "#ef476f"

LABCIN_SEQUENCE = [
    LABCIN_BLUE,
    LABCIN_GREEN,
    LABCIN_GOLD,
    LABCIN_TEAL,
    LABCIN_CORAL,
    LABCIN_LIGHT_GREEN,
    LABCIN_LIME,
    LABCIN_DARK,
]


def configure_matplotlib() -> None:
    plt.rcParams.update({
        "axes.edgecolor": "#d7deea",
        "axes.facecolor": "#ffffff",
        "axes.grid": True,
        "axes.labelcolor": "#17315f",
        "axes.titlecolor": "#17315f",
        "figure.facecolor": "#ffffff",
        "font.family": "DejaVu Sans",
        "grid.color": "#e7ecf5",
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "savefig.bbox": "tight",
        "savefig.dpi": 220,
        "text.color": "#17315f",
        "xtick.color": "#43516c",
        "ytick.color": "#43516c",
    })


def configure_plotly() -> None:
    pio.templates["labcin"] = {
        "layout": {
            "colorway": LABCIN_SEQUENCE,
            "font": {"family": "Inter, Arial, sans-serif", "color": LABCIN_DARK},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "xaxis": {
                "gridcolor": "#e7ecf5",
                "linecolor": "#d7deea",
                "zerolinecolor": "#d7deea",
            },
            "yaxis": {
                "gridcolor": "#e7ecf5",
                "linecolor": "#d7deea",
                "zerolinecolor": "#d7deea",
            },
        }
    }
    pio.templates.default = "labcin"


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
