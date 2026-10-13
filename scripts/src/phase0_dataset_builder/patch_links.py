from __future__ import annotations

import argparse
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd

from src.phase0_dataset_builder.matching import (
    CONFIRMED_MIN_AGREEMENT, CONFIRMED_MIN_INSIDE, MatchStatus, PictureCache, match_patch, parse_homography, place_patch,
    read_bgr,
)
from src.phase0_dataset_builder.sources import (
    PATCH_PLACEMENTS, PICTURE_RELATIONS, POOL_MATCHES, add_source_arguments, load_patch_table, load_pictures,
)
from src.utils.logger import logger


COARSE_FACTOR = 4
COARSE_THRESHOLD = 0.01  # true matches scored at most 0.005 in a 60-patch trial; the patch table checks the result against the SAB file names
MIN_PATCH_STD = 3.0  # a nearly flat patch matches blank areas anywhere; it carries no evidence
POOL_COLUMNS = ["patch_id", "histopath_id", "status", "x", "y", "width", "height", "mean_abs_diff", "max_abs_diff", "coarse_score"]

_PATCH_IDS: list[str] = []
_PATCH_PATHS: list[str] = []
_PATCH_SMALL: np.ndarray | None = None
_THRESHOLD = COARSE_THRESHOLD
_FACTOR = COARSE_FACTOR


def _small(gray: np.ndarray, factor: int) -> np.ndarray:
    return cv.resize(gray, None, fx=1 / factor, fy=1 / factor, interpolation=cv.INTER_AREA)


def _init_worker(patch_ids, patch_paths, patch_small, threshold, factor) -> None:
    global _PATCH_IDS, _PATCH_PATHS, _PATCH_SMALL, _THRESHOLD, _FACTOR
    cv.setNumThreads(1)
    _PATCH_IDS, _PATCH_PATHS, _PATCH_SMALL, _THRESHOLD, _FACTOR = patch_ids, patch_paths, patch_small, threshold, factor


def _search_picture(task: tuple[str, str]) -> tuple[list[dict], int]:
    histopath_id, path = task
    picture_bgr = read_bgr(path)
    picture_gray = cv.cvtColor(picture_bgr, cv.COLOR_BGR2GRAY)
    picture_small = _small(picture_gray, _FACTOR)
    rows, candidates = [], 0
    for index, patch_id in enumerate(_PATCH_IDS):
        patch_small = _PATCH_SMALL[index]
        if patch_small is None:
            continue
        coarse = float(cv.matchTemplate(picture_small, patch_small, cv.TM_SQDIFF_NORMED).min())
        if not coarse <= _THRESHOLD:
            continue
        candidates += 1
        match = match_patch(read_bgr(_PATCH_PATHS[index]), picture_bgr, picture_gray)
        if match.status is MatchStatus.NONE:
            continue
        rows.append({"patch_id": patch_id, "histopath_id": histopath_id, **match.as_row(), "coarse_score": coarse})
    return rows, candidates


def run_search_patches_in_pictures(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patches = sorted(load_patch_table(args, with_names=False), key=lambda patch: patch.patch_id)
    if args.limit_patches:
        patches = patches[: args.limit_patches]
    pictures = sorted(load_pictures(args), key=lambda picture: picture.histopath_id)

    smalls, flat = [], []
    for patch in patches:
        gray = cv.cvtColor(read_bgr(patch.path), cv.COLOR_BGR2GRAY)
        if float(gray.std()) < MIN_PATCH_STD:
            smalls.append(None)
            flat.append(patch.patch_id)
        else:
            smalls.append(_small(gray, args.coarse_factor))
    logger.info(f"Searching {len(patches) - len(flat)} patches ({len(flat)} nearly flat, skipped) in {len(pictures)} pictures")

    tasks = [(picture.histopath_id, str(picture.files[0].path)) for picture in pictures]
    started = time.time()
    rows, candidates = [], 0
    with Pool(args.workers, initializer=_init_worker,
              initargs=([p.patch_id for p in patches], [str(p.path) for p in patches], smalls, args.coarse_threshold, args.coarse_factor)) as pool:
        for number, (found, n_candidates) in enumerate(pool.imap_unordered(_search_picture, tasks), start=1):
            rows += found
            candidates += n_candidates
            if number % 20 == 0:
                logger.info(f"Searched {number}/{len(tasks)} pictures in {time.time() - started:.0f}s, {len(rows)} matches so far")
    table = pd.DataFrame(rows, columns=POOL_COLUMNS).sort_values(["patch_id", "histopath_id"])
    table.to_csv(output_dir / POOL_MATCHES.name, index=False)

    summary = {
        "patches_searched": len(patches) - len(flat),
        "flat_patches_skipped": len(flat),
        "coarse_candidates": candidates,
        "candidates_rejected_at_full_resolution": candidates - int(len(table)),
        "matches": int(len(table)),
        "patches_found_somewhere": int(table["patch_id"].nunique()),
        "pictures_per_patch": table.groupby("patch_id").size().value_counts().sort_index().to_dict(),
    }
    logger.info(f"Summary: {summary}")
    logger.info(f"Outputs saved under {output_dir}")
    return summary


def search_patches_in_pictures_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search every patch in every picture by template matching.")
    add_source_arguments(parser)
    parser.add_argument("--output-dir", type=Path, default=POOL_MATCHES.parent)
    parser.add_argument("--coarse-factor", type=int, default=COARSE_FACTOR, help="Downscale factor of the first pass.")
    parser.add_argument("--coarse-threshold", type=float, default=COARSE_THRESHOLD)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit-patches", type=int, default=None, help="Trial run on the first N patches.")
    return parser


PLACEMENT_COLUMNS = ["patch_id", "from_picture", "to_picture", "scale", "inside_fraction", "agreement"]


def run_place_patches(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pictures = {picture.histopath_id: picture for picture in load_pictures(args)}
    matches = pd.read_csv(args.pool_matches)
    matches = matches[matches["status"] == "exact"]
    relations = pd.read_csv(args.relations)
    relations = relations[relations["strong"].astype(bool)]
    logger.info(f"Projecting patches through {len(relations)} strong picture relations")
    patches_in = defaultdict(list)
    for row in matches.itertuples():
        patches_in[row.histopath_id].append(row)

    cache = PictureCache(size=7)
    rows = []
    for relation in relations.itertuples():
        forward = parse_homography(relation.homography)
        for source, target, homography in (
            (relation.a, relation.b, forward),
            (relation.b, relation.a, np.linalg.inv(forward)),
        ):
            for match in patches_in.get(source, []):
                patch = cv.cvtColor(read_bgr(args.patch_image_dir / f"{match.patch_id}.png"), cv.COLOR_BGR2GRAY)
                _, target_gray = cache.get(pictures[target])
                placed = place_patch(patch, int(match.x), int(match.y), homography, target_gray)
                rows.append({
                    "patch_id": match.patch_id,
                    "from_picture": source,
                    "to_picture": target,
                    "scale": placed.scale,
                    "inside_fraction": placed.inside_fraction,
                    "agreement": placed.agreement,
                })
    table = pd.DataFrame(rows, columns=PLACEMENT_COLUMNS).sort_values(["patch_id", "to_picture"])
    table.to_csv(output_dir / PATCH_PLACEMENTS.name, index=False)
    logger.info(f"{len(table)} placements for {table['patch_id'].nunique()} patches")
    logger.info(f"Outputs saved under {output_dir}")

    confirmed = table[(table["inside_fraction"] >= CONFIRMED_MIN_INSIDE) & (table["agreement"] >= CONFIRMED_MIN_AGREEMENT)]
    return {
        "placements": int(len(table)),
        "patches_with_a_related_picture": int(table["patch_id"].nunique()),
        "confirmed_placements": int(len(confirmed)),
        "patches_with_a_confirmed_other_picture": int(confirmed["patch_id"].nunique()),
        "confirmed_pictures_per_patch": confirmed.groupby("patch_id").size().value_counts().sort_index().to_dict(),
    }


def place_patches_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project each patch into related pictures and check the content there.")
    add_source_arguments(parser)
    parser.add_argument("--pool-matches", type=Path, default=POOL_MATCHES)
    parser.add_argument("--relations", type=Path, default=PICTURE_RELATIONS)
    parser.add_argument("--output-dir", type=Path, default=PATCH_PLACEMENTS.parent)
    return parser
