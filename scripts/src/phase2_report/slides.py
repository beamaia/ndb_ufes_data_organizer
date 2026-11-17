"""Figures for the private slides: a picture with its patches, and how the published folds put overlapping patches of one picture on both sides of the
split. The pictures are SAB images, which are private, so the figures are written only to the folder given by --out, never to the wiki."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2 as cv
import matplotlib
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402

from src.phase0_dataset_builder.matching import RANSAC_REPROJECTION_PX, overlap_fractions, parse_homography  # noqa: E402
from src.phase0_dataset_builder.sources import DEFAULT_NDB_ORIGIN_DIR, DEFAULT_PATCH_IMAGE_DIR, NDB_METADATA, PATCH_TABLE_LAB, PICTURE_RELATIONS, PICTURE_TABLE_LAB  # noqa: E402
from src.phase2_report.atlas import _footprint, _picture_path, _scale_and_rotation  # noqa: E402
from src.phase2_report.cluster_steps import cluster_steps  # noqa: E402
from src.phase2_report.evaluation_steps import evaluation_steps  # noqa: E402
from src.phase2_report.network_steps import network_steps  # noqa: E402
from src.phase2_report.sift_steps import opencv_matches, sift_steps  # noqa: E402
from src.phase2_report.template_steps import template_steps  # noqa: E402
from src.utils.logger import logger  # noqa: E402


PUBLISHED_FOLDS = Path("results/phase1/folds/fold_assignments_published.csv")
TEST_FOLD = 5  # the sixth published fold is the test fold of Experiment 1
PATCH_LABELS = Path("data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv")  # public: patch name and class
EXAMPLE_SEED = 0  # the example of each class is drawn at random with this seed, so the figure can be redrawn
PATCH = 512
MOST_SHARED = 0.9  # the patient example is the pair with the most area in common up to this share: above it the two pictures are almost the same crop
CLASS_COLOR = {"Leukoplakia without dysplasia": "#2a78d6", "Leukoplakia with dysplasia": "#eb6834", "OSCC": "#1baf7a"}  # the colors of the slides
ROLE_COLOR = {"test fold": "#e34948", "training folds": "#2a78d6"}
SHORT = {"Leukoplakia without dysplasia": "without dysplasia", "Leukoplakia with dysplasia": "with dysplasia", "OSCC": "OSCC"}


def patches_with_published_folds(lab_table: Path, folds: Path) -> pd.DataFrame:
    """Every patch with its picture file, its box in the picture, its label, and its published fold and role (test or training)."""
    lab = pd.read_csv(lab_table, dtype=str, keep_default_na=False).set_index("patch_id")
    published = pd.read_csv(folds, dtype=str, keep_default_na=False).set_index("patch_id")["fold"]
    published = published[published != ""].astype(int)  # a patch with no fold is a duplicate the published folds leave out
    table = lab[["histopath_id", "sab_picture_path", "patch_diagnosis", "ndb_diagnosis", "x", "y", "x2", "y2"]].join(published.rename("published_fold"), how="inner")
    table[["x", "y", "x2", "y2"]] = table[["x", "y", "x2", "y2"]].astype(int)
    table["role"] = (table["published_fold"] == TEST_FOLD).map({True: "test fold", False: "training folds"})
    return table


def shared_area(a: pd.Series, b: pd.Series) -> float:
    width = max(0, min(a["x2"], b["x2"]) - max(a["x"], b["x"]))
    height = max(0, min(a["y2"], b["y2"]) - max(a["y"], b["y"]))
    return width * height / PATCH**2


def split_pairs(patches: pd.DataFrame, min_shared: float) -> pd.DataFrame:
    """The pairs of patches of one picture, one in the test fold and one in a training fold, that share at least ``min_shared`` of their area."""
    rows = []
    for picture, group in patches.groupby("histopath_id"):
        test, training = group[group["role"] == "test fold"], group[group["role"] == "training folds"]
        for test_id, a in test.iterrows():
            for train_id, b in training.iterrows():
                share = shared_area(a, b)
                if share >= min_shared:
                    rows.append({"histopath_id": picture, "test_patch": test_id, "training_patch": train_id, "shared": share})
    return pd.DataFrame(rows, columns=["histopath_id", "test_patch", "training_patch", "shared"])


def draw_picture(image: Image.Image, patches: pd.DataFrame, color_by: str, colors: dict, labels: dict, title: str, path: Path, highlight=()) -> None:
    """The picture with a box for each patch, colored by ``color_by``; the boxes of ``highlight`` are drawn thicker."""
    figure, axis = plt.subplots(figsize=(10, 7.5 * image.height / image.width + 0.6))
    axis.imshow(image)
    for patch_id, row in patches.iterrows():
        thick = patch_id in highlight
        axis.add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=colors[row[color_by]],
                                 linewidth=4 if thick else 1.6, linestyle="-" if thick else "--", alpha=1 if thick else 0.9))
    handles = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=colors[key], linewidth=2.5, label=f"{labels.get(key, key)} ({(patches[color_by] == key).sum()})")
               for key in colors if (patches[color_by] == key).any()]
    axis.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=len(handles), frameon=False, fontsize=12, labelcolor=DARK)
    axis.set_title(title, fontsize=13, color=DARK)
    axis.axis("off")
    figure.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(figure)


def draw_pair(image: Image.Image, test: pd.Series, training: pd.Series, share: float, path: Path) -> None:
    """The two patches side by side, and the part of the picture they come from with both boxes: the same tissue on both sides of the split."""
    x0, y0 = min(test["x"], training["x"]), min(test["y"], training["y"])
    x1, y1 = max(test["x2"], training["x2"]), max(test["y2"], training["y2"])
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.4), gridspec_kw={"width_ratios": [1, 1, (x1 - x0) / (y1 - y0)]})
    for axis, row, role in ((axes[0], test, "test fold"), (axes[1], training, "training folds")):
        axis.imshow(image.crop((row["x"], row["y"], row["x2"], row["y2"])))
        axis.set_title(f"{row.name} in the {role} (fold {row['published_fold']})\nlabel: {SHORT[row['patch_diagnosis']]}", fontsize=13, color=ROLE_COLOR[role])
        for side in axis.spines.values():
            side.set_edgecolor(ROLE_COLOR[role])
            side.set_linewidth(4)
        axis.set_xticks([])
        axis.set_yticks([])
    axes[2].imshow(image.crop((x0, y0, x1, y1)))
    for row, role in ((test, "test fold"), (training, "training folds")):
        axes[2].add_patch(Rectangle((row["x"] - x0, row["y"] - y0), PATCH, PATCH, fill=False, edgecolor=ROLE_COLOR[role], linewidth=3))
    axes[2].set_title(f"in the picture: they share {share:.0%} of their area", fontsize=13, color=DARK)
    axes[2].axis("off")
    figure.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(figure)


SEVERITY = ["Leukoplakia without dysplasia", "Leukoplakia with dysplasia", "OSCC"]


SEVERITY = ["Leukoplakia without dysplasia", "Leukoplakia with dysplasia", "OSCC"]


def more_severe_examples(patches: pd.DataFrame, out: Path, n: int = 5) -> dict:
    """The ``n`` pictures with the most patches labeled more severely than the NDB-UFES diagnosis of the picture: each with every patch colored by
    label (the more severe ones thick) next to its most severe patch."""
    rank = {label: i for i, label in enumerate(SEVERITY)}
    known = patches[patches["ndb_diagnosis"].isin(SEVERITY)]
    worse = known[known["patch_diagnosis"].map(rank) > known["ndb_diagnosis"].map(rank)]
    by_kind = [worse[worse["ndb_diagnosis"] == diagnosis]["histopath_id"].value_counts().index.tolist() for diagnosis in SEVERITY[:2]]
    chosen = [picture for pair in zip(*by_kind) for picture in pair][:n]  # alternate the two kinds: without dysplasia with worse patches, with dysplasia with OSCC
    for number, picture in enumerate(chosen, 1):
        of_picture = patches[patches["histopath_id"] == picture]
        severe = worse[worse["histopath_id"] == picture].sort_values("patch_diagnosis", key=lambda s: s.map(rank), ascending=False)
        first = severe.iloc[0]
        with Image.open(of_picture["sab_picture_path"].iloc[0]) as image:
            image = image.convert("RGB")
            figure, axes = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [image.width / image.height, 1]})
            axes[0].imshow(image)
            for patch_id, row in of_picture.iterrows():
                thick = patch_id in severe.index
                axes[0].add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=CLASS_COLOR[row["patch_diagnosis"]],
                                            linewidth=3.5 if thick else 1.4, linestyle="-" if thick else "--"))
            handles = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=CLASS_COLOR[label], linewidth=2.5, label=f"{SHORT[label]} ({(of_picture['patch_diagnosis'] == label).sum()})")
                       for label in SEVERITY if (of_picture["patch_diagnosis"] == label).any()]
            axes[0].legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=len(handles), frameon=False, fontsize=13, labelcolor=DARK)
            axes[0].set_title(f"{picture}: picture labeled {SHORT[first['ndb_diagnosis']]}\n{len(severe)} of its {len(of_picture)} patches labeled more severe", fontsize=14, color=DARK)
            axes[1].imshow(image.crop((first["x"], first["y"], first["x2"], first["y2"])))
            axes[1].set_title(f"{first.name}\nlabeled {SHORT[first['patch_diagnosis']]}", fontsize=14, color=CLASS_COLOR[first["patch_diagnosis"]])
            for axis in axes:
                axis.axis("off")
            figure.subplots_adjust(wspace=0.04)
            figure.savefig(out / f"more_severe_{number}.png", dpi=120, bbox_inches="tight", pad_inches=0.05)
            plt.close(figure)
    return {"more_severe_examples": " ".join(chosen)}


def class_examples(out: Path) -> dict:
    """One NDB-UFES picture and one P-NDB-UFES patch of each class (public data), drawn at random with ``EXAMPLE_SEED``: a figure of the three pictures
    and one of the three patches, each as large as a slide allows."""
    rng = np.random.default_rng(EXAMPLE_SEED)
    pictures = pd.read_csv(NDB_METADATA, dtype=str, keep_default_na=False)
    patches = pd.read_csv(PATCH_LABELS, dtype=str, keep_default_na=False)
    shapes = {"pictures": (12.6, 3.7), "patches": (10.5, 4.2)}  # the figure size of each, in inches
    figures = {name: plt.subplots(1, len(SEVERITY), figsize=size) for name, size in shapes.items()}
    chosen = {}
    for column, label in enumerate(SEVERITY):
        picture = pictures[pictures["diagnosis"] == label].iloc[rng.integers((pictures["diagnosis"] == label).sum())]
        patch = patches[patches["class"] == label].iloc[rng.integers((patches["class"] == label).sum())]
        with Image.open(DEFAULT_NDB_ORIGIN_DIR / picture["path"]) as image, Image.open(DEFAULT_PATCH_IMAGE_DIR / f"{patch['image_name']}.png") as crop:
            figures["pictures"][1][column].imshow(image.convert("RGB"))
            figures["patches"][1][column].imshow(crop.convert("RGB"))
        chosen[label] = f"{picture['path']} {patch['image_name']}"
    for name, (figure, axes) in figures.items():
        for axis, label in zip(axes, SEVERITY):
            axis.set_title(SHORT[label], fontsize=20, color=CLASS_COLOR[label], fontweight="bold")
            axis.axis("off")
        figure.subplots_adjust(wspace=0.03)
        figure.savefig(out / f"class_examples_{name}.png", dpi=120, bbox_inches="tight", pad_inches=0.05)
        plt.close(figure)
    return {"class_examples": chosen}


OUTLINE = "#eda100"
BLUE = "#2a78d6"
DARK = "#3a3a3a"  # titles in dark gray on the slides


def _picture(pictures: pd.DataFrame, picture_id: str) -> Image.Image:
    with Image.open(_picture_path(pictures.loc[picture_id], DEFAULT_NDB_ORIGIN_DIR)) as image:
        return image.convert("RGB")


def _side_by_side(images, titles, outlines, suptitle: str, path: Path) -> None:
    """Pictures next to each other; ``outlines`` gives, for each, the polygons drawn on it (in its own pixels)."""
    figure, axes = plt.subplots(1, len(images), figsize=(6 * len(images), 4.6))
    for axis, image, title, polygons in zip(axes, images, titles, outlines):
        axis.imshow(image)
        for polygon in polygons:
            axis.add_patch(Polygon(polygon, closed=True, fill=False, edgecolor=OUTLINE, linewidth=3))
        axis.set_xlim(0, image.width)
        axis.set_ylim(image.height, 0)
        axis.set_title(title, fontsize=15, color=DARK)
        axis.axis("off")
    figure.subplots_adjust(wspace=0.04)
    figure.savefig(path, dpi=130, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def sift_example(pictures: pd.DataFrame, a_id: str, b_id: str, path: Path) -> None:
    """The two steps of SIFT on one pair, with the settings of the matching code: the key points found on a half-size gray copy of a picture, and the
    matches (ratio test) that agree on one geometry between the two pictures (RANSAC)."""
    images = [np.asarray(_picture(pictures, pid)) for pid in (a_id, b_id)]
    small, keys_a, keys_b, good, source, target = opencv_matches(images)
    _, mask = cv.findHomography(source, target, cv.RANSAC, RANSAC_REPROJECTION_PX)
    agreeing = [m for m, keep in zip(good, mask.ravel()) if keep]
    shown = agreeing[:: max(1, len(agreeing) // 60)]  # about 60 lines, so that they can be told apart
    figure, axes = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1, 2.05]})
    keypoints_image = cv.drawKeypoints(cv.cvtColor(small[0], cv.COLOR_GRAY2RGB), keys_a, None, color=(42, 120, 214))
    axes[0].imshow(keypoints_image)
    axes[0].set_title(f"1. Key points\non a half-size gray copy: {len(keys_a):,}", fontsize=14, color=DARK)
    matches_image = cv.drawMatches(cv.cvtColor(small[0], cv.COLOR_GRAY2RGB), keys_a, cv.cvtColor(small[1], cv.COLOR_GRAY2RGB), keys_b, shown, None,
                                   matchColor=(235, 104, 52), singlePointColor=None, flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    axes[1].imshow(matches_image)
    axes[1].set_title(f"2. Matches that agree on one geometry\n{len(agreeing):,} of {len(good):,} matches (60 drawn)", fontsize=14, color=DARK)
    for axis in axes:
        axis.axis("off")
    figure.subplots_adjust(wspace=0.03)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def _convex(points) -> np.ndarray:
    """A convex polygon as float32 points that all have the same orientation (what ``cv.intersectConvexConvex`` expects)."""
    points = np.asarray(points, np.float32).reshape(-1, 2)
    return points if cv.contourArea(points, oriented=True) >= 0 else points[::-1].copy()


def _common(first, second) -> tuple[float, np.ndarray | None]:
    """The area that two convex polygons have in common and the polygon of it (None when they do not meet)."""
    area, polygon = cv.intersectConvexConvex(_convex(first), _convex(second))
    return (float(area), polygon.reshape(-1, 2)) if area > 0 else (0.0, None)


def _box(row: pd.Series) -> np.ndarray:
    return np.array([[row["x"], row["y"]], [row["x2"], row["y"]], [row["x2"], row["y2"]], [row["x"], row["y2"]]], np.float32)


INK = "#222222"  # the text of the figures made for the thesis (print: dark on white)


def _frame(axis, color: str = "#999999") -> None:
    """No ticks and a thin frame, so that each picture is a clear panel."""
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_edgecolor(color)
        spine.set_linewidth(0.8)


def shift_intersection(a: Image.Image, b: Image.Image, a_id: str, b_id: str, a_to_b: np.ndarray, patches: pd.DataFrame, out: Path) -> None:
    """For print: two related pictures cut down to the tissue that both show, with the patches that lie inside it (shift_intersection.png); and the patches of A put in the frame
    of B, with the pairs of patches that overlap and the three with the largest area in common side by side (shift_patch_pairs.png)."""
    corners = lambda image: np.array([[0, 0], [image.width, 0], [image.width, image.height], [0, image.height]], np.float32)  # noqa: E731
    inside = {a_id: _common(corners(a), _footprint(np.linalg.inv(a_to_b), b.width, b.height))[1], b_id: _common(corners(b), _footprint(a_to_b, a.width, a.height))[1]}
    plt.rcParams.update({"font.size": 12, "text.color": INK, "axes.labelcolor": INK, "legend.labelcolor": INK})
    figure, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for axis, image, pid, letter, name in zip(axes, (a, b), (a_id, b_id), "ab", "AB"):
        polygon = inside[pid]
        (x0, y0), (x1, y1) = np.floor(polygon.min(axis=0)).astype(int), np.ceil(polygon.max(axis=0)).astype(int)
        mask = np.zeros((image.height, image.width), np.uint8)
        cv.fillPoly(mask, [polygon.astype(np.int32)], 1)
        array = np.asarray(image).copy()
        array[mask == 0] = 255  # only the tissue that the other picture shows too
        axis.imshow(array[y0:y1, x0:x1], extent=(x0, x1, y1, y0))
        shown = 0
        for _, row in patches[patches["histopath_id"] == pid].iterrows():
            if _common(_box(row), polygon)[0] > 0:
                axis.add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=CLASS_COLOR[row["patch_diagnosis"]], linewidth=1.5, alpha=0.95))
                shown += 1
        axis.set_xlim(x0, x1)
        axis.set_ylim(y1, y0)
        axis.set_title(f"({letter}) Picture {name}: {shown} patches in the shared tissue", fontsize=13, loc="left")
        _frame(axis)
    handles = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=color, linewidth=2.2, label=f"patch labeled {SHORT[label]}") for label, color in CLASS_COLOR.items()]
    figure.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=12)
    figure.subplots_adjust(bottom=0.17, wspace=0.05)
    figure.savefig(out / "shift_intersection.png", dpi=300, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(figure)

    # every patch of A in the frame of B against every patch of B
    pairs = []
    for patch_a, row_a in patches[patches["histopath_id"] == a_id].iterrows():
        footprint = cv.perspectiveTransform(_box(row_a).reshape(-1, 1, 2), a_to_b).reshape(-1, 2)
        for patch_b, row_b in patches[patches["histopath_id"] == b_id].iterrows():
            area, polygon = _common(footprint, _box(row_b))
            if area > 0:
                pairs.append({"share": area / PATCH**2, "a": patch_a, "b": patch_b, "footprint": footprint, "common": polygon})
    pairs.sort(key=lambda pair: -pair["share"])
    best, used_a, used_b = [], set(), set()
    for pair in pairs:  # the best pairs, each patch once
        if pair["a"] not in used_a and pair["b"] not in used_b and len(best) < 3:
            best.append(pair)
            used_a.add(pair["a"])
            used_b.add(pair["b"])
    logger.info(f"{len(pairs)} pairs of patches of {a_id} and {b_id} overlap in the frame of {b_id}; best shares " + ", ".join(f"{pair['share']:.0%}" for pair in best))

    figure = plt.figure(figsize=(16, 7.6))
    grid = figure.add_gridspec(len(best), 4, width_ratios=[2.7, 1, 1, 1], hspace=0.12, wspace=0.1)
    overview = figure.add_subplot(grid[:, 0])
    overview.set_anchor("N")
    polygon = inside[b_id]
    (x0, y0), (x1, y1) = np.floor(polygon.min(axis=0)).astype(int), np.ceil(polygon.max(axis=0)).astype(int)
    overview.imshow(np.asarray(b)[y0:y1, x0:x1], extent=(x0, x1, y1, y0))
    for _, row in patches[patches["histopath_id"] == b_id].iterrows():
        overview.add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=BLUE, linewidth=1.2, alpha=0.9))
    for pair in pairs:
        overview.add_patch(Polygon(pair["footprint"], closed=True, fill=False, edgecolor=OUTLINE, linewidth=1.0, linestyle="--"))
        overview.add_patch(Polygon(pair["common"], closed=True, facecolor="#ffe45c", alpha=0.16, edgecolor="none"))
    for rank, pair in enumerate(best, 1):
        overview.add_patch(Polygon(pair["common"], closed=True, facecolor="#ffe45c", alpha=0.55, edgecolor="#b58900", linewidth=1.8))
        overview.annotate(str(rank), pair["common"].mean(axis=0), color=INK, fontsize=16, fontweight="bold", ha="center", va="center")
    overview.set_xlim(x0, x1)
    overview.set_ylim(y1, y0)
    overview.set_title("(a) Picture B, with the patches of both pictures in its frame", fontsize=13, loc="left")
    _frame(overview)
    key = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=BLUE, linewidth=2, label="patches of picture B"),
           Rectangle((0, 0), 1, 1, fill=False, edgecolor=OUTLINE, linewidth=2, linestyle="--", label="patches of picture A, moved into the frame of B"),
           Rectangle((0, 0), 1, 1, facecolor="#ffe45c", alpha=0.6, edgecolor="#b58900", label="area in common (the best three pairs are numbered)")]
    overview.legend(handles=key, loc="upper left", bbox_to_anchor=(0, -0.04), frameon=False, fontsize=12)
    for rank, pair in enumerate(best, 1):
        row_a, row_b = patches.loc[pair["a"]], patches.loc[pair["b"]]
        views = [(a.crop((row_a["x"], row_a["y"], row_a["x2"], row_a["y2"])), f"{rank}. {pair['a']}"), (b.crop((row_b["x"], row_b["y"], row_b["x2"], row_b["y2"])), pair["b"])]
        for column, (image, title) in enumerate(views, 1):
            axis = figure.add_subplot(grid[rank - 1, column])
            axis.imshow(image)
            axis.set_title(("(b) Patch of A\n" if rank == 1 and column == 1 else "Patch of B\n" if rank == 1 else "") + title, fontsize=12)
            _frame(axis)
        axis = figure.add_subplot(grid[rank - 1, 3])
        low, high = np.minimum(pair["footprint"].min(axis=0), _box(row_b).min(axis=0)).astype(int), np.maximum(pair["footprint"].max(axis=0), _box(row_b).max(axis=0)).astype(int)
        axis.imshow(np.asarray(b)[low[1]:high[1], low[0]:high[0]], extent=(low[0], high[0], high[1], low[1]))
        axis.add_patch(Polygon(pair["footprint"], closed=True, fill=False, edgecolor=OUTLINE, linewidth=2.2))
        axis.add_patch(Rectangle((row_b["x"], row_b["y"]), row_b["x2"] - row_b["x"], row_b["y2"] - row_b["y"], fill=False, edgecolor=BLUE, linewidth=2.2))
        axis.add_patch(Polygon(pair["common"], closed=True, facecolor="#ffe45c", alpha=0.45, edgecolor="none"))
        axis.set_xlim(low[0], high[0])
        axis.set_ylim(high[1], low[1])
        axis.set_title(("Both in the frame of B\n" if rank == 1 else "") + f"{pair['share']:.0%} of the area in common", fontsize=12)
        _frame(axis)
    figure.savefig(out / "shift_patch_pairs.png", dpi=300, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(figure)


def parent_examples(relations_path: Path, picture_table: Path, out: Path, patches: pd.DataFrame) -> dict:
    """Three cases at the level of the parent pictures: one picture that is a close-up of another, two pictures of the same field shifted, and two
    pictures of the same patient code that show different tissue (SIFT finds no relation between them)."""
    pictures = pd.read_csv(picture_table, dtype=str, keep_default_na=False).set_index("histopath_id")
    relations = pd.read_csv(relations_path, dtype={"a": str, "b": str})
    strong = relations[relations["strong"].astype(str) == "True"].copy()
    strong["scale"] = [_scale_and_rotation(parse_homography(h))[0] for h in strong["homography"]]
    strong["ratio"] = np.maximum(strong["scale"], 1 / strong["scale"])

    zoom = strong[strong["ratio"] > 2].sort_values("inliers", ascending=False).iloc[0]
    a, b = _picture(pictures, zoom["a"]), _picture(pictures, zoom["b"])
    a_to_b = parse_homography(zoom["homography"])
    if zoom["scale"] < 1:  # A is the close-up, inside B
        wide, close, wide_id, close_id, inside = b, a, zoom["b"], zoom["a"], _footprint(a_to_b, a.width, a.height)
    else:
        wide, close, wide_id, close_id, inside = a, b, zoom["a"], zoom["b"], _footprint(np.linalg.inv(a_to_b), b.width, b.height)
    sift_example(pictures, wide_id, close_id, out / "sift_example.png")
    sift_steps(np.asarray(wide), np.asarray(close), out)  # the figures of the slides that explain SIFT step by step
    _side_by_side([wide, close], [f"{wide_id}: wide field", f"{close_id}: close-up, × {zoom['ratio']:.1f}"], [[inside], []],
                  f"One picture is a zoomed part of the other ({int(zoom['inliers'])} matched SIFT points)", out / "parent_zoom.png")

    same_zoom = strong[strong["ratio"] < 1.25].copy()
    sizes = {pid: Image.open(_picture_path(pictures.loc[pid], DEFAULT_NDB_ORIGIN_DIR)).size for pid in set(same_zoom["a"]) | set(same_zoom["b"])}
    same_zoom["shared"] = [min(overlap_fractions(parse_homography(r["homography"]), sizes[r["a"]], sizes[r["b"]])) for _, r in same_zoom.iterrows()]
    shift = same_zoom[(same_zoom["shared"] > 0.3) & (same_zoom["shared"] < 0.85)].sort_values("inliers", ascending=False).iloc[0]
    a, b = _picture(pictures, shift["a"]), _picture(pictures, shift["b"])
    a_to_b = parse_homography(shift["homography"])
    _side_by_side([a, b], [shift["a"], shift["b"]], [[_footprint(np.linalg.inv(a_to_b), b.width, b.height)], [_footprint(a_to_b, a.width, a.height)]],
                  f"The same field, shifted: about {shift['shared']:.0%} of the tissue is in both ({int(shift['inliers'])} matched SIFT points)", out / "parent_shift.png")
    shift_intersection(a, b, shift["a"], shift["b"], a_to_b, patches, out)

    related = set(zip(relations["a"], relations["b"])) | set(zip(relations["b"], relations["a"]))
    meta = pd.read_csv(NDB_METADATA, dtype=str, keep_default_na=False)
    meta = meta.assign(ndb_origin_id=meta["path"].str.removesuffix(".png")).set_index("ndb_origin_id")
    in_ndb = pictures[(pictures["case_pseudonym"] != "") & pictures["ndb_origin_id"].isin(meta.index)]
    candidates = []  # pairs of one patient code, both in NDB-UFES, that SIFT does not relate; the same area of the mouth first
    for case, group in in_ndb.groupby("case_pseudonym"):
        ids = sorted(group.index)
        for i, first in enumerate(ids):
            for second in ids[i + 1:]:
                if (first, second) in related:
                    continue
                m1, m2 = meta.loc[pictures.loc[first, "ndb_origin_id"]], meta.loc[pictures.loc[second, "ndb_origin_id"]]
                candidates.append((m1["localization"] != m2["localization"], case, first, second, m1, m2))
    _, case, first, second, m1, m2 = sorted(candidates, key=lambda c: (c[0], c[1], c[2], c[3]))[0]
    describe = lambda pid, m: f"{pid}\n{m['localization']}, lesion {m['lesion_id']}, {SHORT[m['diagnosis']]}"
    area = f"same area of the mouth ({m1['localization'].lower()})" if m1["localization"] == m2["localization"] else "different areas of the mouth"
    _side_by_side([_picture(pictures, first), _picture(pictures, second)], [describe(first, m1), describe(second, m2)], [[], []],
                  f"The same patient code ({case}), {area}, different tissue: SIFT finds no relation", out / "parent_same_patient.png")
    same_area = sum(1 for c in candidates if not c[0])
    same_lesion = sum(1 for c in candidates if c[4]["lesion_id"] == c[5]["lesion_id"])
    logger.info(f"same patient, unrelated pictures in NDB-UFES: {len(candidates)} pairs, {same_area} in the same area of the mouth, {same_lesion} of the same lesion")
    return {"zoom_pair": f"{zoom['a']} {zoom['b']}", "shift_pair": f"{shift['a']} {shift['b']}", "same_patient_pair": f"{first} {second}"}


def contamination_patient(patches: pd.DataFrame, relations_path: Path, picture_table: Path, case_groups: Path, out: Path) -> dict:
    """The contamination at the level of the patient (contamination_patient.png and contamination_patient_pair.png): two pictures of one patient that show the same
    field, with the patches colored by the published fold role, and the two patches (one in the test fold, one in a training fold, from different pictures) that
    share the most tissue once the test patch is moved into the frame of the training picture. Only NDB-UFES pictures, and pictures at the same zoom."""
    pictures = pd.read_csv(picture_table, dtype=str, keep_default_na=False).set_index("histopath_id")
    patches = patches.join(pd.read_csv(case_groups, dtype=str).set_index("patch_id")["case_group"])
    relations = pd.read_csv(relations_path, dtype={"a": str, "b": str})
    strong = relations[relations["strong"].astype(str) == "True"]
    public = set(pictures.index[pictures["ndb_origin_id"] != ""])
    best = None
    for _, relation in strong.iterrows():
        a, b = relation["a"], relation["b"]
        scale = _scale_and_rotation(parse_homography(relation["homography"]))[0]
        if a not in public or b not in public or max(scale, 1 / scale) > 1.25:
            continue
        a_to_b = parse_homography(relation["homography"])
        in_a, in_b = patches[patches["histopath_id"] == a], patches[patches["histopath_id"] == b]
        for patch_a, row_a in in_a.iterrows():
            footprint = cv.perspectiveTransform(_box(row_a).reshape(-1, 1, 2), a_to_b).reshape(-1, 2)
            for patch_b, row_b in in_b.iterrows():
                if row_a["role"] == row_b["role"]:
                    continue
                area, polygon = _common(footprint, _box(row_b))
                if area / PATCH**2 <= MOST_SHARED and (best is None or area > best["area"]):
                    best = {"area": area, "a": a, "b": b, "patch_a": patch_a, "patch_b": patch_b, "footprint": footprint, "common": polygon, "a_to_b": a_to_b}
    share = best["area"] / PATCH**2
    case = patches.loc[best["patch_a"], "case_group"]
    patient = patches[patches["case_group"] == case]
    n_test = int((patient["role"] == "test fold").sum())
    images = {pid: _picture(pictures, pid) for pid in (best["a"], best["b"])}
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    for axis, pid, letter in zip(axes, (best["a"], best["b"]), "ab"):
        shown = patient[patient["histopath_id"] == pid]
        axis.imshow(images[pid])
        for patch_id, row in shown.iterrows():
            thick = patch_id in (best["patch_a"], best["patch_b"])
            axis.add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=ROLE_COLOR[row["role"]],
                                     linewidth=4 if thick else 1.4, linestyle="-" if thick else "--", alpha=1 if thick else 0.9))
        axis.set_title(f"({letter}) {pid}: {len(shown)} patches, {int((shown['role'] == 'test fold').sum())} in the test fold", fontsize=13, loc="left", color=INK)
        axis.axis("off")
    handles = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=color, linewidth=2.5, label=role) for role, color in ROLE_COLOR.items()]
    figure.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=12, labelcolor=INK)
    figure.suptitle(f"One patient: {patient['histopath_id'].nunique()} pictures and {len(patient)} patches, {n_test} in the published test fold and {len(patient) - n_test} in the training folds",
                    fontsize=13, color=INK)
    figure.subplots_adjust(bottom=0.1, wspace=0.03)
    figure.savefig(out / "contamination_patient.png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    # the two patches, and the training picture with both boxes (the test patch moved into its frame)
    test_is_a = patches.loc[best["patch_a"], "role"] == "test fold"
    test_id, train_id = (best["patch_a"], best["patch_b"]) if test_is_a else (best["patch_b"], best["patch_a"])
    test, train = patches.loc[test_id], patches.loc[train_id]
    frame_id = best["b"] if test_is_a else best["a"]  # the picture of the training patch
    test_pid = best["a"] if test_is_a else best["b"]
    footprint = best["footprint"] if test_is_a else cv.perspectiveTransform(_box(patches.loc[best["patch_b"]]).reshape(-1, 1, 2), np.linalg.inv(best["a_to_b"])).reshape(-1, 2)
    frame = images[frame_id]
    low, high = np.minimum(footprint.min(axis=0), _box(train).min(axis=0)).astype(int), np.maximum(footprint.max(axis=0), _box(train).max(axis=0)).astype(int)
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.4), gridspec_kw={"width_ratios": [1, 1, (high[0] - low[0]) / (high[1] - low[1])]})
    for axis, row, pid, role in ((axes[0], test, test_pid, "test fold"), (axes[1], train, frame_id, "training folds")):
        axis.imshow(images[pid].crop((row["x"], row["y"], row["x2"], row["y2"])))
        axis.set_title(f"{row.name} in the {role} (fold {row['published_fold']})\n{pid}, label: {SHORT[row['patch_diagnosis']]}", fontsize=11, color=ROLE_COLOR[role])
        for side in axis.spines.values():
            side.set_edgecolor(ROLE_COLOR[role])
            side.set_linewidth(4)
        axis.set_xticks([])
        axis.set_yticks([])
    axes[2].imshow(np.asarray(frame)[low[1]:high[1], low[0]:high[0]], extent=(low[0], high[0], high[1], low[1]))
    axes[2].add_patch(Polygon(footprint, closed=True, fill=False, edgecolor=ROLE_COLOR["test fold"], linewidth=3))
    axes[2].add_patch(Rectangle((train["x"], train["y"]), train["x2"] - train["x"], train["y2"] - train["y"], fill=False, edgecolor=ROLE_COLOR["training folds"], linewidth=3))
    axes[2].set_xlim(low[0], high[0])
    axes[2].set_ylim(high[1], low[1])
    axes[2].set_title(f"in {frame_id}: they share {share:.0%} of their area", fontsize=11, color=INK)
    axes[2].axis("off")
    figure.savefig(out / "contamination_patient_pair.png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    logger.info(f"patient example: pictures {best['a']} and {best['b']}, patches {test_id} (test) and {train_id} (training) share {share:.0%}; the patient has {len(patient)} patches in {patient['published_fold'].nunique()} folds")
    return {"patient_pair": f"{best['a']} {best['b']}", "patient_patches": f"{test_id} {train_id}", "patient_share": round(float(share), 3)}


def run_slides(args: argparse.Namespace) -> dict:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    patches = patches_with_published_folds(Path(args.lab_table), Path(args.published_folds))
    pairs = split_pairs(patches, args.min_shared)
    picture = pairs["histopath_id"].value_counts().idxmax()  # the picture with the most overlapping pairs split between test and training
    best = pairs[pairs["histopath_id"] == picture].sort_values("shared", ascending=False).iloc[0]
    of_picture = patches[patches["histopath_id"] == picture]
    with Image.open(of_picture["sab_picture_path"].iloc[0]) as image:
        image = image.convert("RGB")
        n_test = (of_picture["role"] == "test fold").sum()
        draw_picture(image, of_picture, "role", ROLE_COLOR, {}, f"{picture}: {len(of_picture)} patches, {n_test} in the published test fold, "
                     f"{len(of_picture) - n_test} in its training folds", out / "contamination_picture.png", highlight=(best["test_patch"], best["training_patch"]))
        draw_pair(image, patches.loc[best["test_patch"]], patches.loc[best["training_patch"]], best["shared"], out / "contamination_pair.png")
        draw_picture(image, of_picture, "patch_diagnosis", CLASS_COLOR, SHORT, f"{picture}: each patch is a 512 x 512 crop of the picture, labeled one by one",
                     out / "picture_with_patches.png")
    example = more_severe_examples(patches, out) | parent_examples(PICTURE_RELATIONS, PICTURE_TABLE_LAB, out, patches) | class_examples(out) | template_steps(out) | cluster_steps(out) | network_steps(out) | evaluation_steps(out) | contamination_patient(patches, PICTURE_RELATIONS, PICTURE_TABLE_LAB, Path("results/phase1/folds/fold_assignments.csv"), out)
    logger.info(f"{len(pairs)} overlapping test/training pairs (shared area >= {args.min_shared:.0%}) in {pairs['histopath_id'].nunique()} pictures")
    return {"picture": picture, "pairs_in_picture": int((pairs["histopath_id"] == picture).sum()), "best_pair_shared": round(float(best["shared"]), 3),
            "split_pairs": len(pairs), "pictures_with_split_pairs": int(pairs["histopath_id"].nunique()), "out": str(out)} | example


def slides_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="A private folder for the figures (they show SAB pictures), for example ../presentation/web/figures.")
    parser.add_argument("--lab-table", default=str(PATCH_TABLE_LAB))
    parser.add_argument("--published-folds", default=str(PUBLISHED_FOLDS))
    parser.add_argument("--min-shared", type=float, default=0.5, help="The least share of their area two patches must have in common to count as a pair.")
    return parser
