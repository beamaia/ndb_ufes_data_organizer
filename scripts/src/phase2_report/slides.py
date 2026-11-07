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

from src.phase0_dataset_builder.matching import FEATURE_SCALE, MAX_FEATURES, RANSAC_REPROJECTION_PX, RATIO_TEST, overlap_fractions, parse_homography  # noqa: E402
from src.phase0_dataset_builder.sources import DEFAULT_NDB_ORIGIN_DIR, NDB_METADATA, PATCH_TABLE_LAB, PICTURE_RELATIONS, PICTURE_TABLE_LAB  # noqa: E402
from src.phase2_report.atlas import _footprint, _picture_path, _scale_and_rotation  # noqa: E402
from src.utils.logger import logger  # noqa: E402


PUBLISHED_FOLDS = Path("results/phase1/folds/fold_assignments_published.csv")
TEST_FOLD = 5  # the sixth published fold is the test fold of Experiment 1
PATCH = 512
CLASS_COLOR = {"Leukoplakia without dysplasia": "#2a78d6", "Leukoplakia with dysplasia": "#eb6834", "OSCC": "#1baf7a"}  # the colours of the slides
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


def draw_picture(image: Image.Image, patches: pd.DataFrame, colour_by: str, colours: dict, labels: dict, title: str, path: Path, highlight=()) -> None:
    """The picture with a box for each patch, coloured by ``colour_by``; the boxes of ``highlight`` are drawn thicker."""
    figure, axis = plt.subplots(figsize=(10, 7.5 * image.height / image.width + 0.6))
    axis.imshow(image)
    for patch_id, row in patches.iterrows():
        thick = patch_id in highlight
        axis.add_patch(Rectangle((row["x"], row["y"]), row["x2"] - row["x"], row["y2"] - row["y"], fill=False, edgecolor=colours[row[colour_by]],
                                 linewidth=4 if thick else 1.6, linestyle="-" if thick else "--", alpha=1 if thick else 0.9))
    handles = [Rectangle((0, 0), 1, 1, fill=False, edgecolor=colours[key], linewidth=2.5, label=f"{labels.get(key, key)} ({(patches[colour_by] == key).sum()})")
               for key in colours if (patches[colour_by] == key).any()]
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
    """The ``n`` pictures with the most patches labelled more severely than the NDB-UFES diagnosis of the picture: each with every patch coloured by
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
            axes[0].set_title(f"{picture}: picture labelled {SHORT[first['ndb_diagnosis']]}\n{len(severe)} of its {len(of_picture)} patches labelled more severe", fontsize=14, color=DARK)
            axes[1].imshow(image.crop((first["x"], first["y"], first["x2"], first["y2"])))
            axes[1].set_title(f"{first.name}\nlabelled {SHORT[first['patch_diagnosis']]}", fontsize=14, color=CLASS_COLOR[first["patch_diagnosis"]])
            for axis in axes:
                axis.axis("off")
            figure.subplots_adjust(wspace=0.04)
            figure.savefig(out / f"more_severe_{number}.png", dpi=120, bbox_inches="tight", pad_inches=0.05)
            plt.close(figure)
    return {"more_severe_examples": " ".join(chosen)}


OUTLINE = "#eda100"
DARK = "#3a3a3a"  # titles in dark grey on the slides


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
    """The two steps of SIFT on one pair, with the settings of the matching code: the key points found on a half-size grey copy of a picture, and the
    matches (ratio test) that agree on one geometry between the two pictures (RANSAC)."""
    images = [np.asarray(_picture(pictures, pid)) for pid in (a_id, b_id)]
    small = [cv.resize(cv.cvtColor(image, cv.COLOR_RGB2GRAY), None, fx=FEATURE_SCALE, fy=FEATURE_SCALE, interpolation=cv.INTER_AREA) for image in images]
    sift = cv.SIFT_create(nfeatures=MAX_FEATURES)
    (keys_a, desc_a), (keys_b, desc_b) = [sift.detectAndCompute(image, None) for image in small]
    pairs = cv.BFMatcher(cv.NORM_L2).knnMatch(desc_a, desc_b, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < RATIO_TEST * pair[1].distance]
    source = np.float32([keys_a[m.queryIdx].pt for m in good]) / FEATURE_SCALE
    target = np.float32([keys_b[m.trainIdx].pt for m in good]) / FEATURE_SCALE
    _, mask = cv.findHomography(source, target, cv.RANSAC, RANSAC_REPROJECTION_PX)
    agreeing = [m for m, keep in zip(good, mask.ravel()) if keep]
    shown = agreeing[:: max(1, len(agreeing) // 60)]  # about 60 lines, so that they can be told apart
    figure, axes = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1, 2.05]})
    keypoints_image = cv.drawKeypoints(cv.cvtColor(small[0], cv.COLOR_GRAY2RGB), keys_a, None, color=(42, 120, 214))
    axes[0].imshow(keypoints_image)
    axes[0].set_title(f"1. Key points\non a half-size grey copy: {len(keys_a):,}", fontsize=14, color=DARK)
    matches_image = cv.drawMatches(cv.cvtColor(small[0], cv.COLOR_GRAY2RGB), keys_a, cv.cvtColor(small[1], cv.COLOR_GRAY2RGB), keys_b, shown, None,
                                   matchColor=(235, 104, 52), singlePointColor=None, flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    axes[1].imshow(matches_image)
    axes[1].set_title(f"2. Matches that agree on one geometry\n{len(agreeing):,} of {len(good):,} matches (60 drawn)", fontsize=14, color=DARK)
    for axis in axes:
        axis.axis("off")
    figure.subplots_adjust(wspace=0.03)
    figure.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)


def parent_examples(relations_path: Path, picture_table: Path, out: Path) -> dict:
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
        draw_picture(image, of_picture, "patch_diagnosis", CLASS_COLOR, SHORT, f"{picture}: each patch is a 512 x 512 crop of the picture, labelled one by one",
                     out / "picture_with_patches.png")
    example = more_severe_examples(patches, out) | parent_examples(PICTURE_RELATIONS, PICTURE_TABLE_LAB, out)
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
