"""Search for scaled or cropped source-image relationships within patients.

This validation uses explicit patient linkage from the SAB convergence table. It
does not infer patient identity from demographic metadata and never compares
images belonging to different patient IDs.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


DEFAULT_CONVERGENCE = Path("results/phase0/sab_consistency_validation/origin_source_convergence.csv")
DEFAULT_OUTPUT = Path("results/phase0/validated_linkage/same_patient_wsi_image_relationships.csv")


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="Search for scaled/cropped relationships only among WSI from the same explicitly linked patient."
    )
    argument_parser.add_argument("--convergence", type=Path, default=DEFAULT_CONVERGENCE)
    argument_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    argument_parser.add_argument("--patient-id", action="append", help="Restrict the validation to one or more patient IDs.")
    argument_parser.add_argument("--ratio-test", type=float, default=0.70)
    argument_parser.add_argument("--min-inliers", type=int, default=30)
    argument_parser.add_argument("--min-inlier-fraction", type=float, default=0.50)
    argument_parser.add_argument("--max-reprojection-error", type=float, default=5.0)
    argument_parser.add_argument("--max-features", type=int, default=5000)
    return argument_parser


def _as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _image_path(repo_root: Path, row: pd.Series) -> Path:
    relative_path = Path(_as_text(row["ndb_origin_path"]))
    path = relative_path if relative_path.is_absolute() else repo_root / relative_path
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _load_features(path: Path, max_features: int) -> dict:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_half = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

    detector_name = "SIFT"
    detector = cv2.SIFT_create(nfeatures=max_features)
    keypoints, descriptors = detector.detectAndCompute(gray_half, None)
    if descriptors is None or len(keypoints) < 4:
        detector_name = "ORB"
        detector = cv2.ORB_create(nfeatures=max_features)
        keypoints, descriptors = detector.detectAndCompute(gray_half, None)

    return {
        "path": path,
        "shape": image.shape[:2],
        "keypoints": keypoints or [],
        "descriptors": descriptors,
        "detector": detector_name,
    }


def _corners(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    return np.float32([[[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]])


def _json_points(points: np.ndarray | None) -> str:
    if points is None:
        return ""
    return json.dumps(np.round(points.reshape(-1, 2), 2).tolist())


def _interpretation(inliers: int, inlier_fraction: float, reprojection_error: float, args: argparse.Namespace) -> str:
    if inliers >= args.min_inliers and inlier_fraction >= args.min_inlier_fraction and reprojection_error <= args.max_reprojection_error:
        return "strong_geometric_support"
    if inliers >= max(10, args.min_inliers // 3) and inlier_fraction >= 0.25:
        return "partial_or_local_support"
    if inliers >= 10:
        return "visual_similarity_only"
    return "unsupported"


def compare_features(left: dict, right: dict, args: argparse.Namespace) -> dict:
    descriptors_left = left["descriptors"]
    descriptors_right = right["descriptors"]
    if descriptors_left is None or descriptors_right is None:
        return {
            "detector": f"{left['detector']}/{right['detector']}",
            "keypoints_left": len(left["keypoints"]),
            "keypoints_right": len(right["keypoints"]),
            "good_matches": 0,
            "inliers": 0,
            "inlier_fraction": 0.0,
            "scale_x": np.nan,
            "scale_y": np.nan,
            "reprojection_error_px": np.nan,
            "homography": None,
            "left_corners_in_right": None,
            "interpretation": "unsupported",
        }

    norm = cv2.NORM_L2 if left["detector"] == "SIFT" and right["detector"] == "SIFT" else cv2.NORM_HAMMING
    matches = cv2.BFMatcher(norm).knnMatch(descriptors_left, descriptors_right, k=2)
    good = [first for first, second in matches if first.distance < args.ratio_test * second.distance]
    homography = None
    inlier_mask = None
    if len(good) >= 4:
        source_points = np.float32([left["keypoints"][match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
        target_points = np.float32([right["keypoints"][match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
        homography_half, inlier_mask = cv2.findHomography(source_points, target_points, cv2.RANSAC, args.max_reprojection_error)
        if homography_half is not None:
            half_scale = np.diag([0.5, 0.5, 1.0])
            homography = np.linalg.inv(half_scale) @ homography_half @ half_scale

    inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
    inlier_fraction = inliers / len(good) if good else 0.0
    errors = []
    if homography is not None and inlier_mask is not None:
        source_points_full = np.float32([left["keypoints"][match.queryIdx].pt for match in good]).reshape(-1, 1, 2) * 2.0
        target_points_full = np.float32([right["keypoints"][match.trainIdx].pt for match in good]).reshape(-1, 1, 2) * 2.0
        projected = cv2.perspectiveTransform(source_points_full, homography)
        errors = np.linalg.norm(projected - target_points_full, axis=2).ravel()[inlier_mask.ravel() == 1]

    linear = homography[:2, :2] if homography is not None else None
    scale_x = float(np.linalg.norm(linear[:, 0])) if linear is not None else np.nan
    scale_y = float(np.linalg.norm(linear[:, 1])) if linear is not None else np.nan
    left_corners_in_right = cv2.perspectiveTransform(_corners(left["shape"]), homography)[0] if homography is not None else None
    reprojection_error = float(np.median(errors)) if len(errors) else np.nan
    interpretation = _interpretation(inliers, inlier_fraction, reprojection_error, args) if np.isfinite(reprojection_error) else "unsupported"

    return {
        "detector": f"{left['detector']}/{right['detector']}",
        "keypoints_left": len(left["keypoints"]),
        "keypoints_right": len(right["keypoints"]),
        "good_matches": len(good),
        "inliers": inliers,
        "inlier_fraction": round(inlier_fraction, 4),
        "scale_x": round(scale_x, 6),
        "scale_y": round(scale_y, 6),
        "reprojection_error_px": round(reprojection_error, 4),
        "homography": homography,
        "left_corners_in_right": left_corners_in_right,
        "interpretation": interpretation,
    }


def _pair_row(patient_id: str, left: dict, right: dict, comparison: dict, repo_root: Path) -> dict:
    reverse_corners = None
    if comparison["homography"] is not None:
        try:
            reverse_homography = np.linalg.inv(comparison["homography"])
            reverse_corners = cv2.perspectiveTransform(_corners(right["shape"]), reverse_homography)[0]
        except np.linalg.LinAlgError:
            reverse_corners = None
    left_path = left["path"]
    right_path = right["path"]
    return {
        "patient_id": patient_id,
        "origin_a": left["public_id"],
        "origin_b": right["public_id"],
        "source_a": left["source_id"],
        "source_b": right["source_id"],
        "diagnosis_a": left["diagnosis"],
        "diagnosis_b": right["diagnosis"],
        "image_a": str(left_path.relative_to(repo_root)),
        "image_b": str(right_path.relative_to(repo_root)),
        "image_a_size": f"{left['shape'][1]}x{left['shape'][0]}",
        "image_b_size": f"{right['shape'][1]}x{right['shape'][0]}",
        "detector": comparison["detector"],
        "keypoints_a": comparison["keypoints_left"],
        "keypoints_b": comparison["keypoints_right"],
        "good_matches_a_to_b": comparison["good_matches"],
        "geometric_inliers_a_to_b": comparison["inliers"],
        "inlier_fraction_a_to_b": comparison["inlier_fraction"],
        "scale_a_to_b_x": comparison["scale_x"],
        "scale_a_to_b_y": comparison["scale_y"],
        "scale_b_to_a_x": round(1.0 / comparison["scale_x"], 6) if comparison["scale_x"] > 0 else np.nan,
        "scale_b_to_a_y": round(1.0 / comparison["scale_y"], 6) if comparison["scale_y"] > 0 else np.nan,
        "median_reprojection_error_px": comparison["reprojection_error_px"],
        "source_a_corners_in_b": _json_points(comparison["left_corners_in_right"]),
        "source_b_corners_in_a": _json_points(reverse_corners),
        "interpretation": comparison["interpretation"],
        "candidate": comparison["interpretation"] == "strong_geometric_support",
    }


def run_same_patient_wsi_relationships(args: argparse.Namespace) -> dict:
    convergence_path = args.convergence.resolve()
    repo_root = convergence_path.parents[3]
    table = pd.read_csv(convergence_path, dtype=str)
    required = {"patient_id", "public_id", "sab_origin_image_id", "ndb_origin_path", "current_origin_diagnosis"}
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Missing required convergence columns: {sorted(missing)}")

    table = table.rename(columns={
        "sab_origin_image_id": "source_id",
        "current_origin_diagnosis": "diagnosis",
    })
    table = table[table["patient_id"].notna() & table["patient_id"].ne("")].copy()
    table = table.drop_duplicates(subset=["patient_id", "public_id", "source_id"])
    # Different source identifiers can converge on the same public origin image.
    # Compare each public image once within a patient, while retaining the
    # source identifiers as provenance context.
    table = (
        table.groupby(["patient_id", "public_id", "ndb_origin_path"], as_index=False)
        .agg(
            source_id=("source_id", lambda values: " | ".join(sorted({_as_text(value) for value in values if _as_text(value)}))),
            diagnosis=("diagnosis", lambda values: " | ".join(sorted({_as_text(value) for value in values if _as_text(value)}))),
        )
    )
    if args.patient_id:
        wanted = {str(value) for value in args.patient_id}
        table = table[table["patient_id"].isin(wanted)].copy()

    grouped = table.groupby("patient_id", sort=True)
    rows = []
    patients_with_pairs = 0
    for patient_id, patient_table in grouped:
        records = []
        for _, row in patient_table.sort_values(["public_id", "source_id"]).iterrows():
            path = _image_path(repo_root, row)
            features = _load_features(path, args.max_features)
            features.update({
                "public_id": _as_text(row["public_id"]).zfill(4),
                "source_id": _as_text(row["source_id"]),
                "diagnosis": _as_text(row["diagnosis"]),
            })
            records.append(features)
        if len(records) < 2:
            continue
        patients_with_pairs += 1
        for left, right in itertools.combinations(records, 2):
            comparison = compare_features(left, right, args)
            rows.append(_pair_row(str(patient_id), left, right, comparison, repo_root))
        print(f"patient_id={patient_id}: compared {len(records)} WSI, {len(records) * (len(records) - 1) // 2} pairs")

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["candidate", "patient_id", "origin_a", "origin_b"], ascending=[False, True, True, True])
    output_path = args.output if args.output.is_absolute() else repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    candidates = int(result["candidate"].sum()) if not result.empty else 0
    print(f"wrote: {output_path}")
    print(f"patients_with_pairs: {patients_with_pairs}")
    print(f"pairs_compared: {len(result)}")
    print(f"strong_candidates: {candidates}")
    return {"output": str(output_path), "patients_with_pairs": patients_with_pairs, "pairs_compared": len(result), "strong_candidates": candidates}


if __name__ == "__main__":
    raise SystemExit(run_same_patient_wsi_relationships(parser().parse_args()))
