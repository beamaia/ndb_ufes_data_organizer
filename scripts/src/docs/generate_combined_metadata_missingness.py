#!/usr/bin/env python3
"""Generate the combined origin- and patch-level metadata missingness figure."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


FIELDS = [
    "dysplasia_severity",
    "sun_exposure",
    "tobacco_use",
    "alcohol_consumption",
    "skin_color",
    "gender",
    "age_group_label",
    "localization",
    "larger_size",
]

ORIGIN_COUNTS = [131, 102, 98, 98, 96, 0, 0, 0, 0]
ORIGIN_PERCENT = [64.532020, 50.246305, 48.275862, 48.275862, 47.290640, 0, 0, 0, 0]

PATCH_COUNTS = [2156, 1465, 1425, 1425, 1393, 0, 0, 0, 0]
PATCH_PERCENT = [69.863901, 47.472456, 46.176280, 46.176280, 45.139339, 0, 0, 0, 0]


def draw_panel(ax, title, counts, percentages):
    positions = np.arange(len(FIELDS))
    bars = ax.barh(positions, percentages, color="#D9822B", height=0.72)
    ax.set_yticks(positions, FIELDS)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11, pad=10)
    ax.set_xlabel("Percent of records")
    ax.set_xlim(0, 80)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    for bar, count, percent in zip(bars, counts, percentages):
        x = percent + 0.7 if percent else 0.4
        ax.text(
            x,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({percent:.1f}%)",
            va="center",
            ha="left",
            fontsize=8.5,
            color="#333333",
        )


def main():
    output_dir = Path("docs/assets/thesis_section3")
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharex=True, sharey=True)
    draw_panel(axes[0], "(a) Origin level", ORIGIN_COUNTS, ORIGIN_PERCENT)
    draw_panel(axes[1], "(b) Patch level", PATCH_COUNTS, PATCH_PERCENT)
    fig.suptitle("Missing and Not informed metadata rates", fontsize=13, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96), w_pad=3.5)

    stem = output_dir / "fig_07_metadata_missingness_combined"
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
