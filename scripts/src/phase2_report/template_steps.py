"""Figures that explain how a patch is found in its picture (template matching), on one real public pair, for the private slides.

The score of a window is the normalized squared difference of the matching code (``cv.TM_SQDIFF_NORMED`` on gray pictures); here it is also written out with numpy and
checked against OpenCV. Three figures: the score of the patch against three windows of the picture, the score at every position, and the check of the pixels of the best
window, in the right picture and in another one.
"""

from __future__ import annotations

from pathlib import Path

import cv2 as cv
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.colors import PowerNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from src.phase0_dataset_builder.matching import MatchStatus, match_patch, read_bgr  # noqa: E402
from src.phase0_dataset_builder.patch_links import COARSE_FACTOR  # noqa: E402
from src.phase0_dataset_builder.sources import DEFAULT_NDB_ORIGIN_DIR, DEFAULT_PATCH_IMAGE_DIR  # noqa: E402
from src.utils.logger import logger  # noqa: E402

ORIGIN_PATCHES = Path("data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv")  # public: each picture and the patches cut from it
WINDOWS = {"A": "#e34948", "B": "#eda100", "C": "#1baf7a"}  # the three windows shown: far from the patch, close to it, and the best one
DARK = "#3a3a3a"  # titles in dark gray, as on the other slide figures


def score(patch: np.ndarray, window: np.ndarray) -> float:
    """The normalized squared difference of two gray crops of the same size: sum((T - I)^2) / sqrt(sum(T^2) * sum(I^2)); 0 for identical pixels."""
    t, i = patch.astype(np.float64), window.astype(np.float64)
    return float(((t - i) ** 2).sum() / np.sqrt((t**2).sum() * (i**2).sum()))


def _example() -> tuple[np.ndarray, np.ndarray, str, str, np.ndarray, str]:
    """The first patch (in the order of the table) found at its exact pixels in its own picture and not flat, with its picture and another picture it does not come from
    (the next picture of the table). Each is a BGR array and a name."""
    mapping = pd.read_csv(ORIGIN_PATCHES, dtype=str)
    for position, row in mapping.iterrows():
        picture = read_bgr(DEFAULT_NDB_ORIGIN_DIR / f"{int(row['origin_id']):04d}.png")
        for patch_id in row["patch_ids"].split(","):
            patch = read_bgr(DEFAULT_PATCH_IMAGE_DIR / f"{patch_id}.png")
            if patch.std() >= 20 and match_patch(patch, picture).status is MatchStatus.EXACT:
                other = mapping.iloc[position + 1]["origin_id"]
                return picture, patch, f"{int(row['origin_id']):04d}", patch_id, read_bgr(DEFAULT_NDB_ORIGIN_DIR / f"{int(other):04d}.png"), f"{int(other):04d}"
    raise ValueError("No patch of the table is found exactly in its picture")


def _rgb(bgr: np.ndarray) -> np.ndarray:
    return cv.cvtColor(bgr, cv.COLOR_BGR2RGB)


def _windows(best: tuple[int, int], picture_size: tuple[int, int], patch_size: tuple[int, int]) -> dict[str, tuple[int, int]]:
    """Window A far from the best one, B a few pixels off it, C the best."""
    (x, y), (width, height), (w, h) = best, picture_size, patch_size
    return {"A": ((x + (width - w) // 2) % (width - w), (y + (height - h) // 2) % (height - h)), "B": (min(x + 30, width - w), min(y + 20, height - h)), "C": (x, y)}


def _axes_off(axes) -> None:
    for axis in np.ravel(axes):
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)


def scores_figure(picture: np.ndarray, patch: np.ndarray, gray: np.ndarray, patch_gray: np.ndarray, positions: dict, response: np.ndarray, path: Path) -> None:
    """The picture with three windows, the patch, and each window with its score."""
    h, w = patch_gray.shape
    figure, axes = plt.subplots(1, 5, figsize=(17, 3.9), gridspec_kw={"width_ratios": [picture.shape[1] / picture.shape[0], 1, 1, 1, 1]})
    axes[0].imshow(_rgb(picture))
    axes[0].set_title("picture\n", fontsize=17, color=DARK)
    axes[1].imshow(_rgb(patch))
    axes[1].set_title("patch\n", fontsize=17, color=DARK)
    for axis, (name, (x, y)) in zip(axes[2:], positions.items()):
        value = score(patch_gray, gray[y : y + h, x : x + w])
        assert np.isclose(value, response[y, x], atol=1e-5), (name, value, response[y, x])  # the formula is what OpenCV computes
        axes[0].add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=WINDOWS[name], linewidth=3.5))
        axis.imshow(_rgb(picture[y : y + h, x : x + w]))
        axis.set_title(f"window {name}\nscore {value:.3f}", fontsize=17, color=WINDOWS[name], fontweight="bold")
    _axes_off(axes)
    figure.subplots_adjust(wspace=0.04)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def map_figure(picture: np.ndarray, patch_size: tuple[int, int], positions: dict, response: np.ndarray, path: Path) -> None:
    """The picture with the best window, the score at every position of the patch (one value for each top-left corner), and the scores close to the best position."""
    w, h = patch_size
    (bx, by), reach = positions["C"], 40
    left, top = max(bx - reach, 0), max(by - reach, 0)
    around = response[top : by + reach + 1, left : bx + reach + 1]
    figure, axes = plt.subplots(1, 3, figsize=(19, 4.6), gridspec_kw={"width_ratios": [picture.shape[1] / picture.shape[0], response.shape[1] / response.shape[0], 1.1]})
    axes[0].imshow(_rgb(picture))
    axes[0].add_patch(Rectangle((bx, by), w, h, fill=False, edgecolor=WINDOWS["C"], linewidth=3.5))
    axes[0].set_title("picture\n", fontsize=17, color=DARK)
    image = axes[1].imshow(response, cmap="viridis", vmax=0.1)
    for name, (x, y) in positions.items():
        axes[1].plot(x, y, "o", markersize=14, markerfacecolor=WINDOWS[name], markeredgecolor="white", markeredgewidth=2)
    axes[1].set_title("score at every position\n", fontsize=17, color=DARK)
    figure.colorbar(image, ax=axes[1], fraction=0.04, pad=0.02).ax.tick_params(labelsize=13)
    axes[2].imshow(around, cmap="viridis", vmax=0.1, extent=(left - 0.5, left + around.shape[1] - 0.5, top + around.shape[0] - 0.5, top - 0.5))
    axes[2].plot(bx, by, "o", markersize=14, markerfacecolor=WINDOWS["C"], markeredgecolor="white", markeredgewidth=2)
    axes[2].set_title(f"{2 * reach} pixels around the best\nlowest {response.min():.3f}", fontsize=17, color=DARK)
    _axes_off(axes)
    figure.subplots_adjust(wspace=0.06)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def pixels_figure(patch: np.ndarray, pictures: dict[str, np.ndarray], path: Path) -> None:
    """The patch, then for the right picture and for another one: the best window and its pixel difference with the patch. Only the first is identical."""
    figure, axes = plt.subplots(1, 5, figsize=(19, 4.4))
    axes[0].imshow(_rgb(patch))
    axes[0].set_title("patch\n", fontsize=17, color=DARK)
    small = lambda image: cv.resize(cv.cvtColor(image, cv.COLOR_BGR2GRAY), None, fx=1 / COARSE_FACTOR, fy=1 / COARSE_FACTOR, interpolation=cv.INTER_AREA)  # noqa: E731
    for number, (name, picture) in enumerate(pictures.items()):
        match = match_patch(patch, picture)
        window = picture[match.y : match.y + match.height, match.x : match.x + match.width]
        coarse = float(cv.matchTemplate(small(picture), small(patch), cv.TM_SQDIFF_NORMED).min())
        color = WINDOWS["C"] if match.status is MatchStatus.EXACT else WINDOWS["A"]
        axes[1 + 2 * number].imshow(_rgb(window))
        axes[1 + 2 * number].set_title(f"{name}\nscore at 1/{COARSE_FACTOR} size: {coarse:.3f}", fontsize=15, color=color, fontweight="bold")
        axes[2 + 2 * number].imshow(cv.absdiff(patch, window), vmin=0, vmax=255)
        axes[2 + 2 * number].set_title(f"pixel difference\nlargest {match.max_abs_diff}: {match.status.value}", fontsize=15, color=color)
        logger.info(f"template matching, {name}: {match.status.value}, coarse score {coarse:.4f}, largest pixel difference {match.max_abs_diff}")
    _axes_off(axes)
    figure.subplots_adjust(wspace=0.04)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def template_steps(out: Path) -> dict:
    picture, patch, picture_name, patch_id, other, other_name = _example()
    gray, patch_gray = cv.cvtColor(picture, cv.COLOR_BGR2GRAY), cv.cvtColor(patch, cv.COLOR_BGR2GRAY)
    response = cv.matchTemplate(gray, patch_gray, cv.TM_SQDIFF_NORMED)
    _, _, best, _ = cv.minMaxLoc(response)
    positions = _windows(best, (picture.shape[1], picture.shape[0]), (patch.shape[1], patch.shape[0]))
    scores_figure(picture, patch, gray, patch_gray, positions, response, out / "template_scores.png")
    map_figure(picture, (patch.shape[1], patch.shape[0]), positions, response, out / "template_map.png")
    pixels_figure(patch, {f"its own picture ({picture_name})": picture, f"another picture ({other_name})": other}, out / "template_pixels.png")
    return {"template_example": f"{picture_name} {patch_id} at {best}", "template_windows": str(positions)}
