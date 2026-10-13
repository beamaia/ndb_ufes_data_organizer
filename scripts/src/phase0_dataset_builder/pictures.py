from __future__ import annotations

import argparse
import itertools
import pickle
import time
from multiprocessing import Pool
from pathlib import Path

import cv2 as cv
import pandas as pd

from src.phase0_dataset_builder.matching import PictureFeatures, extract_features_from_file, find_relation, group_pictures
from src.phase0_dataset_builder.sources import (
    PICTURE_FEATURES, PICTURE_RELATIONS, add_source_arguments, load_pictures,
)
from src.utils.logger import logger


PROGRESS_EVERY = 2000
RELATION_COLUMNS = ["a", "b", "good_matches", "inliers", "inlier_fraction", "median_error_px",
                    "scale_x", "scale_y", "strong", "homography"]


def run_extract_picture_features(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pictures = sorted(load_pictures(args), key=lambda picture: picture.histopath_id)
    if args.limit_pictures:
        pictures = pictures[: args.limit_pictures]
    logger.info(f"Extracting SIFT features for {len(pictures)} pictures")
    features = {}
    for number, picture in enumerate(pictures, start=1):
        found = extract_features_from_file(picture.files[0].path)
        features[picture.histopath_id] = (found.points, found.descriptors)  # plain arrays: the cache survives code moves
        if number % 50 == 0:
            logger.info(f"Extracted {number}/{len(pictures)} pictures")
    with (output_dir / PICTURE_FEATURES.name).open("wb") as handle:
        pickle.dump(features, handle)

    keypoints = sorted(len(points) for points, _ in features.values())
    logger.info(f"Outputs saved under {output_dir}")
    return {
        "pictures": len(features),
        "keypoints_min": keypoints[0],
        "keypoints_median": keypoints[len(keypoints) // 2],
        "keypoints_max": keypoints[-1],
    }


def extract_picture_features_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract SIFT features for every picture and cache them.")
    add_source_arguments(parser)
    parser.add_argument("--output-dir", type=Path, default=PICTURE_FEATURES.parent)
    parser.add_argument("--limit-pictures", type=int, default=None, help="Trial run on the first N pictures.")
    return parser


_FEATURES: dict | None = None


def _load_features(path: Path) -> None:
    global _FEATURES
    cv.setNumThreads(1)  # one process per core; OpenCV's own threads would oversubscribe the machine
    with Path(path).open("rb") as handle:
        _FEATURES = {picture_id: PictureFeatures(*arrays) for picture_id, arrays in pickle.load(handle).items()}


def _relate(pair: tuple[str, str]) -> dict | None:
    a, b = pair
    relation = find_relation(_FEATURES[a], _FEATURES[b])
    if relation is None:
        return None
    return {
        "a": a,
        "b": b,
        "good_matches": relation.good_matches,
        "inliers": relation.inliers,
        "inlier_fraction": relation.inlier_fraction,
        "median_error_px": relation.median_error_px,
        "scale_x": relation.scale_x,
        "scale_y": relation.scale_y,
        "strong": relation.is_strong,
        "homography": " ".join(f"{value:.10g}" for value in relation.homography),
    }


def run_relate_pictures(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Path(args.features).open("rb") as handle:
        picture_ids = sorted(pickle.load(handle))
    pairs = list(itertools.combinations(picture_ids, 2))
    logger.info(f"Comparing {len(pairs)} picture pairs with {args.workers} workers")
    started = time.time()
    found = []
    with Pool(args.workers, initializer=_load_features, initargs=(args.features,)) as pool:
        for number, row in enumerate(pool.imap_unordered(_relate, pairs, chunksize=200), start=1):
            if row is not None:
                found.append(row)
            if number % PROGRESS_EVERY == 0:
                logger.info(f"Compared {number}/{len(pairs)} pairs in {time.time() - started:.0f}s, {len(found)} relations so far")

    relations = pd.DataFrame(found, columns=RELATION_COLUMNS).sort_values(["a", "b"])
    relations["strong"] = relations["strong"].astype(bool)  # stays boolean when no relation is found
    relations.to_csv(output_dir / PICTURE_RELATIONS.name, index=False)

    strong = relations[relations["strong"]]
    logger.info(f"Relations: {len(relations)} found, {len(strong)} strong")
    group_of = group_pictures(picture_ids, list(zip(strong["a"], strong["b"])))
    sizes = pd.Series(group_of).value_counts().value_counts().sort_index()
    logger.info(f"{len(picture_ids)} pictures form {len(set(group_of.values()))} groups; sizes {sizes.to_dict()}")
    logger.info(f"Outputs saved under {output_dir}")
    return {
        "pictures": len(picture_ids),
        "pairs_compared": len(pairs),
        "relations": int(len(relations)),
        "strong_relations": int(len(strong)),
        "groups": len(set(group_of.values())),
        "group_size_counts": sizes.to_dict(),
    }


def relate_pictures_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match SIFT features between every pair of pictures and group related ones.")
    parser.add_argument("--features", type=Path, default=PICTURE_FEATURES)
    parser.add_argument("--output-dir", type=Path, default=PICTURE_RELATIONS.parent)
    parser.add_argument("--workers", type=int, default=6)
    return parser
