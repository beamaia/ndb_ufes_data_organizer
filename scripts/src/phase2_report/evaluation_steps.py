"""Figures that explain the evaluation metrics, for the slides and the thesis. They are diagrams, not results.

Three figures, written to the folder given to the slides command:
- ``confusion_binary.png``: the binary confusion matrix, with its true positives, false negatives, false positives and true negatives.
- ``confusion_multiclass.png``: the confusion matrix of the three classes, once for each class taken as the positive one, with the other two as negative.
- ``roc.png``: the ROC curves of a perfect model, a made-up good model and random guessing, with the area under the good one.

Rows are the true class and columns the predicted class, as in scikit-learn's ``confusion_matrix``, which the training pipeline uses.
"""

from __future__ import annotations

from pathlib import Path
from statistics import NormalDist

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from src.phase2_report.cluster_steps import DARK, STYLE  # noqa: E402
from src.utils.logger import logger  # noqa: E402

CELL = {"TP": "#e1d5e7", "FN": "#f8cecc", "FP": "#d5e8d4", "TN": "#dae8fc"}  # the colors of the old draw.io figures
CLASSES = ["without\ndysplasia", "with\ndysplasia", "OSCC"]
GOOD, PERFECT, RANDOM = "#1baf7a", "#2a78d6", "#8a8f98"
SEPARATION = 1.47  # the made-up good model: the probabilities of the class and of the others are two normal curves this many deviations apart


def outcome(true: int, predicted: int, positive: int) -> str:
    """The name of a cell when class ``positive`` is the positive one and all others are negative."""
    if true == positive:
        return "TP" if predicted == positive else "FN"
    return "FP" if predicted == positive else "TN"


def confusion_panel(axis, names: list[str], positive: int, title: str) -> None:
    """A confusion matrix of ``names``, rows the true class and columns the predicted class, each cell named and colored for the class ``positive``."""
    n = len(names)
    for i in range(n):
        for j in range(n):
            name = outcome(i, j, positive)
            axis.add_patch(Rectangle((j, n - 1 - i), 1, 1, fc=CELL[name], ec=DARK, lw=1))
            axis.text(j + 0.5, n - 0.5 - i, name, ha="center", va="center", fontsize=14, color=DARK)
    for k, name in enumerate(names):
        axis.text(k + 0.5, n + 0.08, name, ha="center", va="bottom", fontsize=11, color=DARK)
        axis.text(-0.1, n - 0.5 - k, name, ha="right", va="center", fontsize=11, color=DARK)
    axis.text(n / 2, n + 0.6, "predicted class", ha="center", va="bottom", fontsize=12, color=DARK)
    axis.text(-1.15, n / 2, "true class", ha="center", va="center", rotation=90, fontsize=12, color=DARK)
    axis.set_xlim(-1.5, n + 0.1)
    axis.set_ylim(-0.1, n + 1.1)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.set_title(title, fontsize=12, pad=4)


def binary_figure(path: Path) -> None:
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(4.6, 4.2))
        confusion_panel(axis, ["positive", "negative"], 0, "")
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"binary confusion matrix, written to {path}")


def multiclass_figure(path: Path) -> None:
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, len(CLASSES), figsize=(16, 5))
        for positive, (axis, name) in enumerate(zip(axes, CLASSES)):
            confusion_panel(axis, CLASSES, positive, f"({'abc'[positive]}) Positive class: {name.replace(chr(10), ' ')}")
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"multiclass confusion matrix, one panel per positive class, written to {path}")


def roc_figure(path: Path) -> dict:
    """The ROC curves of a perfect model, a good model and random guessing, with the area under the good one and the direction of a lower threshold. The
    good model is the textbook case of two normal curves of probabilities, ``SEPARATION`` deviations apart: its true positive rate at a false positive rate
    f is Phi(SEPARATION + Phi^-1(f))."""
    normal = NormalDist()
    fpr = np.linspace(1e-6, 1 - 1e-6, 400)
    tpr = np.array([normal.cdf(SEPARATION + normal.inv_cdf(f)) for f in fpr])
    fpr, tpr = np.concatenate([[0], fpr, [1]]), np.concatenate([[0], tpr, [1]])
    area = float(np.trapezoid(tpr, fpr))
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(6.4, 6.0))
        axis.fill_between(fpr, tpr, color=GOOD, alpha=0.12)
        axis.plot([0, 0, 1], [0, 1, 1], color=PERFECT, lw=2, label="perfect model (AUC 1)")
        axis.plot(fpr, tpr, color=GOOD, lw=2.2, label=f"good model (AUC {area:.2f})")
        axis.plot([0, 1], [0, 1], color=RANDOM, lw=1.6, ls="--", label="random guessing (AUC 0.5)")
        axis.annotate("", xy=(0.42, 0.93), xytext=(0.08, 0.52), arrowprops={"arrowstyle": "-|>", "color": DARK, "lw": 1.2,
                                                                           "connectionstyle": "arc3,rad=-0.25"})
        axis.text(0.27, 0.62, "lower\nthreshold", fontsize=11, color=DARK, ha="left")
        axis.scatter([0, 1], [0, 1], s=40, color=DARK, zorder=3)
        axis.annotate("no object predicted\nas the class", (0, 0), xytext=(0.06, 0.04), fontsize=10, color=DARK)
        axis.annotate("all objects predicted\nas the class", (1, 1), xytext=(0.62, 0.86), fontsize=10, color=DARK)
        axis.text(0.6, 0.3, "AUC: area under\nthe curve", fontsize=11, color=GOOD)
        axis.set_xlim(-0.02, 1.02)
        axis.set_ylim(-0.02, 1.05)
        axis.set_aspect("equal")
        axis.set_xlabel("false positive rate (1 - specificity)")
        axis.set_ylabel("true positive rate (recall)")
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(loc="lower right", bbox_to_anchor=(1.0, 0.02), frameon=False, fontsize=10)
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"roc: good model with separation {SEPARATION}, AUC {area:.3f}, written to {path}")
    return {"roc_good_auc": round(area, 3)}


def evaluation_steps(out: Path) -> dict:
    binary_figure(out / "confusion_binary.png")
    multiclass_figure(out / "confusion_multiclass.png")
    return roc_figure(out / "roc.png")
