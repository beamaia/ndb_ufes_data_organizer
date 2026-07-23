import argparse
import json
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd


DEFAULT_PATCH_SOURCE_CONVERGENCE = Path("results/phase0/sab_consistency_validation/patch_source_convergence.csv")
DEFAULT_OUTPUT_DIR = Path("results/phase0/sab_coordinate_recovery")


def read_bgr(path: str | Path) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def match_patch_inside_origin(
    patch_bgr: np.ndarray,
    origin_bgr: np.ndarray,
    exact_mae_threshold: float = 0.0,
    near_mae_threshold: float = 1.0,
) -> dict:
    patch_height, patch_width = patch_bgr.shape[:2]
    origin_height, origin_width = origin_bgr.shape[:2]
    if origin_height < patch_height or origin_width < patch_width:
        return {
            "coordinate_recovery_status": "origin_smaller_than_patch",
            "recovered_x": np.nan,
            "recovered_y": np.nan,
            "recovered_width": patch_width,
            "recovered_height": patch_height,
            "template_sqdiff_normed": np.nan,
            "mae": np.nan,
            "max_abs_diff": np.nan,
        }

    if origin_height == patch_height and origin_width == patch_width:
        crop = origin_bgr
        diff = cv.absdiff(patch_bgr, crop)
        mae = float(np.mean(diff))
        max_abs_diff = int(np.max(diff))
        status = match_status(mae, max_abs_diff, exact_mae_threshold, near_mae_threshold)
        return {
            "coordinate_recovery_status": status,
            "recovered_x": 0,
            "recovered_y": 0,
            "recovered_width": patch_width,
            "recovered_height": patch_height,
            "template_sqdiff_normed": 0.0 if status != "no_reliable_pixel_match" else np.nan,
            "mae": mae,
            "max_abs_diff": max_abs_diff,
        }

    patch_gray = cv.cvtColor(patch_bgr, cv.COLOR_BGR2GRAY)
    origin_gray = cv.cvtColor(origin_bgr, cv.COLOR_BGR2GRAY)
    response = cv.matchTemplate(origin_gray, patch_gray, cv.TM_SQDIFF_NORMED)
    min_value, _, min_location, _ = cv.minMaxLoc(response)
    x, y = min_location
    crop = origin_bgr[y:y + patch_height, x:x + patch_width]
    diff = cv.absdiff(patch_bgr, crop)
    mae = float(np.mean(diff))
    max_abs_diff = int(np.max(diff))
    status = match_status(mae, max_abs_diff, exact_mae_threshold, near_mae_threshold)
    return {
        "coordinate_recovery_status": status,
        "recovered_x": int(x),
        "recovered_y": int(y),
        "recovered_width": int(patch_width),
        "recovered_height": int(patch_height),
        "template_sqdiff_normed": float(min_value),
        "mae": mae,
        "max_abs_diff": max_abs_diff,
    }


def match_status(mae: float, max_abs_diff: int, exact_mae_threshold: float, near_mae_threshold: float) -> str:
    if mae <= exact_mae_threshold and max_abs_diff == 0:
        return "exact_pixel_match"
    if mae <= near_mae_threshold and max_abs_diff <= 5:
        return "near_pixel_match"
    return "no_reliable_pixel_match"


def recover_sab_patch_coordinates(
    patch_source_convergence: Path,
    exact_mae_threshold: float = 0.0,
    near_mae_threshold: float = 1.0,
) -> pd.DataFrame:
    source = pd.read_csv(patch_source_convergence)
    source = source[source["patch_exact_match_found"] == True].copy()
    rows = []
    origin_cache: dict[str, np.ndarray] = {}
    for row in source.itertuples(index=False):
        result = {
            "ndb_patch": row.ndb_patch,
            "ndb_patch_path": row.ndb_patch_path,
            "sab_patch_path": row.sab_patch_path,
            "sab_origin_image_id": row.sab_origin_image_id,
            "sab_case_prefix": row.sab_case_prefix,
            "sab_origin_folder": row.sab_origin_folder,
            "sab_origin_path": row.sab_origin_path,
            "sab_split": row.sab_split,
            "sab_split_class": row.sab_split_class,
            "current_patch_label_normalized": row.current_patch_label_normalized,
            "sab_split_label_normalized": row.sab_split_label_normalized,
            "ndb_origin_id_from_patch_csv": row.ndb_origin_id_from_patch_csv,
        }
        try:
            if not isinstance(row.sab_origin_path, str) or not row.sab_origin_path:
                raise ValueError("missing_sab_origin_path")
            patch_bgr = read_bgr(row.ndb_patch_path)
            if row.sab_origin_path not in origin_cache:
                origin_cache[row.sab_origin_path] = read_bgr(row.sab_origin_path)
            origin_bgr = origin_cache[row.sab_origin_path]
            result.update(
                match_patch_inside_origin(
                    patch_bgr,
                    origin_bgr,
                    exact_mae_threshold=exact_mae_threshold,
                    near_mae_threshold=near_mae_threshold,
                )
            )
            result["sab_origin_width"] = int(origin_bgr.shape[1])
            result["sab_origin_height"] = int(origin_bgr.shape[0])
            result["recovered_x2"] = (
                result["recovered_x"] + result["recovered_width"]
                if not pd.isna(result["recovered_x"]) else np.nan
            )
            result["recovered_y2"] = (
                result["recovered_y"] + result["recovered_height"]
                if not pd.isna(result["recovered_y"]) else np.nan
            )
        except Exception as error:
            result.update({
                "coordinate_recovery_status": f"error:{error}",
                "recovered_x": np.nan,
                "recovered_y": np.nan,
                "recovered_width": np.nan,
                "recovered_height": np.nan,
                "recovered_x2": np.nan,
                "recovered_y2": np.nan,
                "template_sqdiff_normed": np.nan,
                "mae": np.nan,
                "max_abs_diff": np.nan,
                "sab_origin_width": np.nan,
                "sab_origin_height": np.nan,
            })
        rows.append(result)
    return pd.DataFrame(rows)


def run_sab_patch_coordinate_recovery(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    coordinates = recover_sab_patch_coordinates(
        args.patch_source_convergence,
        exact_mae_threshold=args.exact_mae_threshold,
        near_mae_threshold=args.near_mae_threshold,
    )
    coordinates.to_csv(output_dir / "sab_patch_recovered_coordinates.csv", index=False)
    status_counts = coordinates["coordinate_recovery_status"].value_counts().rename_axis("status").reset_index(name="count")
    status_counts["percent"] = status_counts["count"] / status_counts["count"].sum() * 100
    status_counts.to_csv(output_dir / "coordinate_recovery_status_counts.csv", index=False)
    summary = {
        "patches_processed": int(len(coordinates)),
        "unique_sab_origins": int(coordinates["sab_origin_image_id"].nunique()),
        "status_counts": status_counts.set_index("status")["count"].to_dict(),
        "output_coordinates": str(output_dir / "sab_patch_recovered_coordinates.csv"),
    }
    (output_dir / "sab_patch_coordinate_recovery_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def sab_patch_coordinate_recovery_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover patch coordinates by locating exact NDB/SAB patches inside SAB origin images.")
    parser.add_argument("--patch-source-convergence", type=Path, default=DEFAULT_PATCH_SOURCE_CONVERGENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--exact-mae-threshold", type=float, default=0.0)
    parser.add_argument("--near-mae-threshold", type=float, default=1.0)
    return parser
