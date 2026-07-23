import argparse
from pathlib import Path

import cv2 as cv
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.phase0.recovery_validation import DEFAULT_ORIGIN_IMAGE_DIR, DEFAULT_RAW_PATCH_DIR
from src.phase0.review_packets import DEFAULT_REVIEW_OUTPUT_DIR, candidate_origin_items, load_font, wrap_label


DEFAULT_REVIEW_QUEUE = DEFAULT_REVIEW_OUTPUT_DIR / "missing_patch_review_queue.csv"
DEFAULT_OUTPUT_DIR = DEFAULT_REVIEW_OUTPUT_DIR / "patch_origin_registration"


def read_gray(path: Path) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def read_bgr(path: Path) -> np.ndarray:
    image = cv.imread(str(path), cv.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def read_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def normalized_cross_correlation(patch: np.ndarray, crop: np.ndarray) -> float:
    patch = patch.astype(np.float64)
    crop = crop.astype(np.float64)
    patch = patch - patch.mean()
    crop = crop - crop.mean()
    denominator = np.linalg.norm(patch) * np.linalg.norm(crop)
    if denominator == 0:
        return np.nan
    return float(np.sum(patch * crop) / denominator)


def white_fraction_bgr(image: np.ndarray) -> float:
    hsv = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    white_mask = (hsv[:, :, 1] < 35) & (hsv[:, :, 2] > 210)
    return float(np.mean(white_mask))


def lab_mean_delta(patch_bgr: np.ndarray, crop_bgr: np.ndarray) -> float:
    patch_lab = cv.cvtColor(patch_bgr, cv.COLOR_BGR2LAB).astype(np.float64)
    crop_lab = cv.cvtColor(crop_bgr, cv.COLOR_BGR2LAB).astype(np.float64)
    return float(np.linalg.norm(patch_lab.mean(axis=(0, 1)) - crop_lab.mean(axis=(0, 1))))


def color_texture_metrics(patch_bgr: np.ndarray, crop_bgr: np.ndarray) -> dict:
    patch_white = white_fraction_bgr(patch_bgr)
    crop_white = white_fraction_bgr(crop_bgr)
    patch_tissue = 1.0 - patch_white
    crop_tissue = 1.0 - crop_white
    color_delta = lab_mean_delta(patch_bgr, crop_bgr)
    color_similarity = float(np.exp(-color_delta / 35.0))
    tissue_similarity = max(0.0, 1.0 - abs(patch_tissue - crop_tissue))
    return {
        "lab_mean_delta": color_delta,
        "color_similarity": color_similarity,
        "patch_white_fraction": patch_white,
        "crop_white_fraction": crop_white,
        "patch_tissue_fraction": patch_tissue,
        "crop_tissue_fraction": crop_tissue,
        "tissue_fraction_delta": abs(patch_tissue - crop_tissue),
        "tissue_similarity": tissue_similarity,
    }


def quality_score(template_score: float, color_similarity: float, tissue_similarity: float) -> float:
    return float(0.55 * template_score + 0.30 * color_similarity + 0.15 * tissue_similarity)


def match_verdict(row: dict) -> str:
    if (
        row["template_score"] >= 0.75
        and row["lab_mean_delta"] <= 15
        and row["tissue_fraction_delta"] <= 0.15
    ):
        return "strong"
    if (
        row["template_score"] >= 0.55
        and row["lab_mean_delta"] <= 25
        and row["tissue_fraction_delta"] <= 0.25
    ):
        return "possible"
    if row["template_score"] < 0.40 or row["lab_mean_delta"] > 40 or row["tissue_fraction_delta"] > 0.40:
        return "weak_reject"
    return "weak_review"


def match_patch_to_origin(
    patch_path: Path,
    origin_path: Path,
    scales: tuple[float, ...] = (1.0,),
) -> dict:
    patch = read_gray(patch_path)
    origin = read_gray(origin_path)
    patch_bgr = read_bgr(patch_path)
    origin_bgr = read_bgr(origin_path)
    best = None
    for scale in scales:
        if scale <= 0:
            continue
        scaled_origin = cv.resize(origin, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)
        scaled_origin_bgr = cv.resize(origin_bgr, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)
        if scaled_origin.shape[0] < patch.shape[0] or scaled_origin.shape[1] < patch.shape[1]:
            continue
        response = cv.matchTemplate(scaled_origin, patch, cv.TM_CCOEFF_NORMED)
        _, max_value, _, max_location = cv.minMaxLoc(response)
        x_scaled, y_scaled = max_location
        crop = scaled_origin[y_scaled:y_scaled + patch.shape[0], x_scaled:x_scaled + patch.shape[1]]
        crop_bgr = scaled_origin_bgr[y_scaled:y_scaled + patch.shape[0], x_scaled:x_scaled + patch.shape[1]]
        mae = float(np.mean(np.abs(crop.astype(np.float64) - patch.astype(np.float64))))
        mse = float(np.mean((crop.astype(np.float64) - patch.astype(np.float64)) ** 2))
        ncc = normalized_cross_correlation(patch, crop)
        color_metrics = color_texture_metrics(patch_bgr, crop_bgr)
        candidate = {
            "scale": float(scale),
            "template_score": float(max_value),
            "ncc": ncc,
            "mae": mae,
            "mse": mse,
            "origin_x": int(round(x_scaled / scale)),
            "origin_y": int(round(y_scaled / scale)),
            "origin_width": int(round(patch.shape[1] / scale)),
            "origin_height": int(round(patch.shape[0] / scale)),
            "scaled_x": int(x_scaled),
            "scaled_y": int(y_scaled),
            **color_metrics,
        }
        candidate["match_quality_score"] = quality_score(
            candidate["template_score"],
            candidate["color_similarity"],
            candidate["tissue_similarity"],
        )
        candidate["match_verdict"] = match_verdict(candidate)
        if best is None or candidate["match_quality_score"] > best["match_quality_score"]:
            best = candidate
    if best is None:
        raise ValueError(f"Origin image is smaller than patch at every scale: {origin_path}")
    return best


def crop_origin_region(origin_path: Path, match: dict) -> Image.Image:
    origin = read_rgb(origin_path)
    box = (
        match["origin_x"],
        match["origin_y"],
        match["origin_x"] + match["origin_width"],
        match["origin_y"] + match["origin_height"],
    )
    return origin.crop(box).resize(read_rgb(origin_path).crop(box).size)


def make_overlay(origin_path: Path, match: dict, size: tuple[int, int] = (300, 225)) -> Image.Image:
    origin = read_rgb(origin_path)
    draw = ImageDraw.Draw(origin)
    x0 = match["origin_x"]
    y0 = match["origin_y"]
    x1 = x0 + match["origin_width"]
    y1 = y0 + match["origin_height"]
    draw.rectangle([x0, y0, x1, y1], outline="lime", width=max(3, origin.width // 500))
    return ImageOps.contain(origin, size)


def make_difference_image(patch_path: Path, origin_path: Path, match: dict, size: tuple[int, int] = (180, 180)) -> Image.Image:
    patch = read_gray(patch_path)
    origin = read_gray(origin_path)
    scale = match["scale"]
    scaled_origin = cv.resize(origin, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)
    x = match["scaled_x"]
    y = match["scaled_y"]
    crop = scaled_origin[y:y + patch.shape[0], x:x + patch.shape[1]]
    diff = cv.absdiff(patch, crop)
    diff_rgb = Image.fromarray(diff).convert("RGB")
    return ImageOps.contain(diff_rgb, size)


def labeled_image(image: Image.Image, label: str, tile_size: tuple[int, int]) -> Image.Image:
    tile = Image.new("RGB", tile_size, "white")
    draw = ImageDraw.Draw(tile)
    font = load_font(12)
    contained = ImageOps.contain(image, (tile_size[0] - 16, tile_size[1] - 54))
    tile.paste(contained, ((tile_size[0] - contained.width) // 2, 8))
    y = tile_size[1] - 42
    for line in wrap_label(label, 30)[:3]:
        draw.text((8, y), line, fill="black", font=font)
        y += 13
    return tile


def registration_tile(row: dict, tile_size: tuple[int, int] = (900, 260)) -> Image.Image:
    tile = Image.new("RGB", tile_size, "white")
    draw = ImageDraw.Draw(tile)
    font = load_font(12)
    title = (
        f"{row['patch']} vs origin {row['candidate_origin_id']} | "
        f"q={row.get('match_quality_score', 0):.3f} verdict={row.get('match_verdict', '')} "
        f"ncc={row['ncc']:.3f} lab={row.get('lab_mean_delta', 0):.1f} "
        f"crop={row.get('origin_width', 0)}x{row.get('origin_height', 0)} scale={row.get('scale', 1):.2f}"
    )
    draw.text((8, 8), title[:130], fill="black", font=font)
    patch = read_rgb(Path(row["patch_path"]))
    crop = crop_origin_region(Path(row["origin_path"]), row)
    overlay = make_overlay(Path(row["origin_path"]), row)
    diff = make_difference_image(Path(row["patch_path"]), Path(row["origin_path"]), row)
    panels = [
        labeled_image(patch, "missing patch", (180, 220)),
        labeled_image(crop, "best origin crop", (180, 220)),
        labeled_image(diff, "pixel abs diff", (180, 220)),
        labeled_image(overlay, "origin location", (330, 220)),
    ]
    x = 8
    for panel in panels:
        tile.paste(panel, (x, 32))
        x += panel.width + 8
    return tile


def make_registration_sheet(rows: list[dict], output_path: Path) -> None:
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tile_height = 260
    sheet = Image.new("RGB", (900, tile_height * len(rows)), "white")
    for index, row in enumerate(rows):
        sheet.paste(registration_tile(row), (0, index * tile_height))
    sheet.save(output_path)


def candidate_origin_ids(row, origin_image_dir: Path) -> list[str]:
    items = candidate_origin_items(row, origin_image_dir)
    ids = []
    for item in items:
        stem = Path(item["image_path"]).stem
        if stem not in ids:
            ids.append(stem)
    return ids


def run_registration_validation(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    queue = pd.read_csv(args.review_queue).sort_values("patch_number").reset_index(drop=True)
    if args.limit:
        queue = queue.head(args.limit)

    rows = []
    for review_row in queue.itertuples(index=False):
        patch_path = Path(review_row.raw_patch_path)
        origin_ids = candidate_origin_ids(review_row, args.origin_image_dir)
        for origin_id in origin_ids:
            origin_path = Path(args.origin_image_dir) / f"{origin_id}.png"
            if not origin_path.exists():
                continue
            match = match_patch_to_origin(patch_path, origin_path, scales=tuple(args.scales))
            rows.append({
                "patch": review_row.patch,
                "patch_number": int(review_row.patch_number),
                "patch_path": str(patch_path),
                "candidate_origin_id": origin_id,
                "origin_path": str(origin_path),
                "folder_label": getattr(review_row, "folder_label", ""),
                "candidate_status": getattr(review_row, "candidate_status", ""),
                **match,
            })

    results = pd.DataFrame(rows)
    if results.empty:
        results.to_csv(output_dir / "patch_origin_registration_scores.csv", index=False)
        return {"registered_pairs": 0, "pages": 0}

    results = results.sort_values(["patch_number", "match_quality_score"], ascending=[True, False])
    results.to_csv(output_dir / "patch_origin_registration_scores.csv", index=False)
    best = results.groupby("patch", as_index=False).head(1)
    best.to_csv(output_dir / "patch_origin_registration_best.csv", index=False)

    all_rows = results.to_dict("records") if args.include_all_candidates else best.to_dict("records")
    pages = 0
    for start in range(0, len(all_rows), args.page_size):
        pages += 1
        make_registration_sheet(
            all_rows[start:start + args.page_size],
            output_dir / "sheets" / f"patch_origin_registration_page_{pages:03d}.png",
        )
    return {
        "registered_pairs": int(len(results)),
        "registered_patches": int(results["patch"].nunique()),
        "pages": pages,
        "scores_path": str(output_dir / "patch_origin_registration_scores.csv"),
    }


def registration_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pixel-register missing patches against candidate origin images.")
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--origin-image-dir", type=Path, default=DEFAULT_ORIGIN_IMAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--page-size", type=int, default=8)
    parser.add_argument("--scales", type=float, nargs="+", default=[1.0])
    parser.add_argument("--include-all-candidates", action="store_true")
    return parser
