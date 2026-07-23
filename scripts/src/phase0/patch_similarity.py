import argparse
import json
import pickle
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd
from skimage.metrics import structural_similarity

from src.phase0.recovery_audit import (
    DEFAULT_ACCEPTED_METADATA,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_PATCH_DIR,
    accepted_patch_table,
    patch_number,
)


DEFAULT_EMBEDDINGS_PATH = Path("data/embeddings/embeddings_wsi_level_virchow_20260628_223154.pkl")
DEFAULT_SIMILARITY_OUTPUT_DIR = Path("results/phase0/similarity")


def l2_normalize_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return values / norms


def cosine_similarity_matrix(values: np.ndarray) -> np.ndarray:
    normalized = l2_normalize_rows(values)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        matrix = normalized @ normalized.T
    return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)


def off_diagonal_values(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix)
    if matrix.shape[0] <= 1:
        return np.asarray([], dtype=float)
    mask = ~np.eye(matrix.shape[0], dtype=bool)
    return matrix[mask]


def similarity_stats(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return {
            "mean_cosine_similarity": np.nan,
            "median_cosine_similarity": np.nan,
            "std_cosine_similarity": np.nan,
            "p10_cosine_similarity": np.nan,
            "p90_cosine_similarity": np.nan,
            "min_cosine_similarity": np.nan,
            "max_cosine_similarity": np.nan,
        }
    return {
        "mean_cosine_similarity": float(np.mean(values)),
        "median_cosine_similarity": float(np.median(values)),
        "std_cosine_similarity": float(np.std(values)),
        "p10_cosine_similarity": float(np.quantile(values, 0.10)),
        "p90_cosine_similarity": float(np.quantile(values, 0.90)),
        "min_cosine_similarity": float(np.min(values)),
        "max_cosine_similarity": float(np.max(values)),
    }


def load_embeddings(path: Path) -> dict:
    with Path(path).open("rb") as embeddings_file:
        embeddings = pickle.load(embeddings_file)
    if not isinstance(embeddings, dict) or not embeddings:
        raise ValueError(f"Expected non-empty embedding dictionary: {path}")
    return embeddings


def origin_patch_ids(metadata: pd.DataFrame) -> dict[int, list[str]]:
    result = {}
    for origin_id, group in metadata.groupby("origin"):
        ordered = group.copy()
        ordered["patch_number"] = ordered["patch"].map(patch_number)
        ordered = ordered.sort_values("patch_number")
        result[int(origin_id)] = ordered["patch"].tolist()
    return result


def intra_origin_embedding_similarity(embeddings: dict, metadata: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    patch_ids_by_origin = origin_patch_ids(metadata)
    rows = []
    top_pairs = []
    for origin_id, raw_features in sorted(embeddings.items(), key=lambda item: int(item[0])):
        features = np.asarray(raw_features)
        if features.ndim != 2 or features.shape[0] == 0:
            continue
        non_finite_embedding_values = int((~np.isfinite(np.asarray(features, dtype=np.float64))).sum())
        matrix = cosine_similarity_matrix(features)
        values = off_diagonal_values(matrix)
        patch_ids = patch_ids_by_origin.get(int(origin_id), [])
        row = {
            "origin_id": int(origin_id),
            "n_patches": int(features.shape[0]),
            "non_finite_embedding_values": non_finite_embedding_values,
            **similarity_stats(values),
        }
        rows.append(row)
        if len(patch_ids) == features.shape[0] and features.shape[0] > 1:
            upper_i, upper_j = np.triu_indices(features.shape[0], k=1)
            pair_values = matrix[upper_i, upper_j]
            for index in np.argsort(pair_values)[-10:][::-1]:
                top_pairs.append({
                    "origin_id": int(origin_id),
                    "patch_a": patch_ids[int(upper_i[index])],
                    "patch_b": patch_ids[int(upper_j[index])],
                    "cosine_similarity": float(pair_values[index]),
                })
    return pd.DataFrame(rows), pd.DataFrame(top_pairs).sort_values("cosine_similarity", ascending=False)


def registered_overlap_slices(shape_a: tuple[int, int], shape_b: tuple[int, int], dx: int, dy: int):
    height_a, width_a = shape_a
    height_b, width_b = shape_b
    x_a_start = max(0, dx)
    y_a_start = max(0, dy)
    x_b_start = max(0, -dx)
    y_b_start = max(0, -dy)
    overlap_width = min(width_a - x_a_start, width_b - x_b_start)
    overlap_height = min(height_a - y_a_start, height_b - y_b_start)
    if overlap_width <= 1 or overlap_height <= 1:
        return None
    return (
        slice(y_a_start, y_a_start + overlap_height),
        slice(x_a_start, x_a_start + overlap_width),
        slice(y_b_start, y_b_start + overlap_height),
        slice(x_b_start, x_b_start + overlap_width),
    )


def normalized_cross_correlation(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    a = a - np.mean(a)
    b = b - np.mean(b)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return np.nan
    return float(np.sum(a * b) / denominator)


def registered_image_similarity(path_a: Path, path_b: Path) -> dict:
    image_a = cv.imread(str(path_a), cv.IMREAD_GRAYSCALE)
    image_b = cv.imread(str(path_b), cv.IMREAD_GRAYSCALE)
    if image_a is None or image_b is None:
        raise ValueError(f"Could not read both images: {path_a}, {path_b}")
    shift, response = cv.phaseCorrelate(np.float32(image_a), np.float32(image_b))
    dx, dy = int(round(shift[0])), int(round(shift[1]))
    slices = registered_overlap_slices(image_a.shape, image_b.shape, dx, dy)
    if slices is None:
        return {
            "translation_x": dx,
            "translation_y": dy,
            "phase_response": float(response),
            "overlap_width": 0,
            "overlap_height": 0,
            "overlap_ncc": np.nan,
            "overlap_ssim": np.nan,
        }
    y_a, x_a, y_b, x_b = slices
    overlap_a = image_a[y_a, x_a]
    overlap_b = image_b[y_b, x_b]
    return {
        "translation_x": dx,
        "translation_y": dy,
        "phase_response": float(response),
        "overlap_width": int(overlap_a.shape[1]),
        "overlap_height": int(overlap_a.shape[0]),
        "overlap_ncc": normalized_cross_correlation(overlap_a, overlap_b),
        "overlap_ssim": float(structural_similarity(overlap_a, overlap_b)),
    }


def write_similarity_method_plan(output_dir: Path, embeddings_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy": "evidence_only_not_automatic_inclusion",
        "scalability_default": {
            "within_origin": "full pairwise similarity",
            "missing_patch_to_candidate_origins": "top-k nearest neighbors only",
            "global_all_pairs": "disabled",
        },
        "near_duplicate_similarity": [
            "phase correlation translation estimate",
            "normalized cross-correlation on registered overlap",
            "SSIM on registered overlap",
        ],
        "morphology_similarity": [
            "L2-normalized frozen embeddings",
            "cosine similarity within origin",
            "nearest-neighbor candidate retrieval for missing patches",
        ],
        "default_embeddings_path": str(embeddings_path),
    }
    (output_dir / "similarity_method_plan.json").write_text(json.dumps(payload, indent=2))


def run_similarity_plan(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_similarity_method_plan(output_dir, args.embeddings)

    summary = {
        "embedding_similarity_computed": False,
        "near_duplicate_similarity_computed": False,
        "method_plan_written": True,
    }
    if args.embeddings.exists() and args.compute_embeddings:
        metadata = accepted_patch_table(args.accepted_metadata)
        embeddings = load_embeddings(args.embeddings)
        intra_origin, top_pairs = intra_origin_embedding_similarity(embeddings, metadata)
        intra_origin.to_csv(output_dir / "intra_origin_similarity.csv", index=False)
        top_pairs.head(args.top_pairs).to_csv(output_dir / "top_near_duplicate_pairs.csv", index=False)
        origin_summary = {
            "origin_count": int(len(intra_origin)),
            "mean_origin_similarity": float(intra_origin["mean_cosine_similarity"].mean()),
            "median_origin_similarity": float(intra_origin["median_cosine_similarity"].median()),
        }
        (output_dir / "origin_similarity_summary.json").write_text(json.dumps(origin_summary, indent=2))
        summary["embedding_similarity_computed"] = True
        summary["origin_count"] = origin_summary["origin_count"]
    return summary


def similarity_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and optionally compute scalable patch similarity reports.")
    parser.add_argument("--accepted-metadata", type=Path, default=DEFAULT_ACCEPTED_METADATA)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SIMILARITY_OUTPUT_DIR)
    parser.add_argument("--compute-embeddings", action="store_true")
    parser.add_argument("--top-pairs", type=int, default=200)
    return parser
