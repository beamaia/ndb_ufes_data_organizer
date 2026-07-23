import argparse
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.phase0.recovery_validation import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_ORIGIN_IMAGE_DIR,
    DEFAULT_RAW_PATCH_DIR,
    patch_number,
)


DEFAULT_REVIEW_OUTPUT_DIR = Path("results/phase0/missing_patch_review")
DEFAULT_MISSING_CANDIDATES = DEFAULT_OUTPUT_DIR / "missing_patch_candidates.csv"
DEFAULT_PATCHLESS_ORIGINS = DEFAULT_OUTPUT_DIR / "patchless_origin_candidates.csv"


def load_font(size: int = 14):
    try:
        return ImageFont.truetype("Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


@lru_cache(maxsize=2048)
def cached_thumbnail(image_path: str, image_width: int, image_height: int) -> Image.Image | None:
    path = Path(image_path)
    if not path.exists():
        return None
    image = Image.open(path).convert("RGB")
    return ImageOps.contain(image, (image_width, image_height))


def thumbnail_with_label(
    image_path: Path,
    label: str,
    tile_size: tuple[int, int] = (180, 220),
    image_size: tuple[int, int] = (160, 160),
) -> Image.Image:
    tile = Image.new("RGB", tile_size, "white")
    draw = ImageDraw.Draw(tile)
    font = load_font(12)
    if image_path.exists():
        image = cached_thumbnail(str(image_path), image_size[0], image_size[1])
        x = (image_size[0] - image.width) // 2 + 10
        tile.paste(image, (x, 8))
    else:
        draw.rectangle([10, 8, 10 + image_size[0], 8 + image_size[1]], outline="red", width=2)
        draw.text((14, 70), "missing image", fill="red", font=font)

    label_lines = wrap_label(label, max_chars=24)
    y = image_size[1] + 16
    for line in label_lines[:4]:
        draw.text((8, y), line, fill="black", font=font)
        y += 14
    return tile


def wrap_label(label: str, max_chars: int) -> list[str]:
    words = str(label).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:max_chars]
    if current:
        lines.append(current)
    return lines or [""]


def make_contact_sheet(
    items: list[dict],
    output_path: Path,
    columns: int = 6,
    tile_size: tuple[int, int] = (180, 220),
) -> None:
    if not items:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * tile_size[0], rows * tile_size[1]), "white")
    for index, item in enumerate(items):
        tile = thumbnail_with_label(Path(item["image_path"]), item["label"], tile_size=tile_size)
        x = (index % columns) * tile_size[0]
        y = (index // columns) * tile_size[1]
        sheet.paste(tile, (x, y))
    sheet.save(output_path)


def patch_origin_comparison_tile(
    patch_path: Path,
    origin_items: list[dict],
    label: str,
    tile_size: tuple[int, int] = (720, 230),
    image_size: tuple[int, int] = (150, 150),
) -> Image.Image:
    tile = Image.new("RGB", tile_size, "white")
    draw = ImageDraw.Draw(tile)
    font = load_font(12)

    draw.text((8, 8), label[:95], fill="black", font=font)
    patch_tile = thumbnail_with_label(
        patch_path,
        "patch",
        tile_size=(170, 200),
        image_size=image_size,
    )
    tile.paste(patch_tile, (8, 28))

    x = 190
    for item in origin_items[:3]:
        origin_tile = thumbnail_with_label(
            Path(item["image_path"]),
            item["label"],
            tile_size=(170, 200),
            image_size=image_size,
        )
        tile.paste(origin_tile, (x, 28))
        x += 175
    return tile


def make_patch_origin_sheet(
    rows: list[dict],
    output_path: Path,
    columns: int = 1,
    tile_size: tuple[int, int] = (720, 230),
) -> None:
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (columns * tile_size[0], len(rows) * tile_size[1]), "white")
    for index, row in enumerate(rows):
        tile = patch_origin_comparison_tile(
            Path(row["patch_path"]),
            row["origin_items"],
            row["label"],
            tile_size=tile_size,
        )
        sheet.paste(tile, (0, index * tile_size[1]))
    sheet.save(output_path)


def contiguous_missing_blocks(candidates: pd.DataFrame) -> pd.DataFrame:
    table = candidates.copy().sort_values("patch_number").reset_index(drop=True)
    rows = []
    block_id = 0
    current = []
    previous_number = None
    for row in table.itertuples(index=False):
        number = int(row.patch_number)
        if previous_number is None or number == previous_number + 1:
            current.append(row._asdict())
        else:
            rows.append(summarize_block(block_id, current))
            block_id += 1
            current = [row._asdict()]
        previous_number = number
    if current:
        rows.append(summarize_block(block_id, current))
    return pd.DataFrame(rows)


def summarize_block(block_id: int, rows: list[dict]) -> dict:
    first = rows[0]
    last = rows[-1]
    labels = pd.Series([row.get("folder_label", "") for row in rows]).value_counts(dropna=False)
    return {
        "block_id": block_id,
        "start_patch": first["patch"],
        "end_patch": last["patch"],
        "start_patch_number": int(first["patch_number"]),
        "end_patch_number": int(last["patch_number"]),
        "n_missing_patches": len(rows),
        "dominant_folder_label": labels.index[0] if not labels.empty else "",
        "previous_accepted_patch": first.get("previous_accepted_patch", ""),
        "previous_accepted_origin_id": first.get("previous_accepted_origin_id", ""),
        "previous_accepted_diagnosis": first.get("previous_accepted_diagnosis", ""),
        "next_accepted_patch": last.get("next_accepted_patch", ""),
        "next_accepted_origin_id": last.get("next_accepted_origin_id", ""),
        "next_accepted_diagnosis": last.get("next_accepted_diagnosis", ""),
        "has_proposed_correct_origin": bool(any(row.get("has_proposed_correct_origin", False) for row in rows)),
    }


def build_review_queue(candidates: pd.DataFrame) -> pd.DataFrame:
    queue = candidates.copy().sort_values("patch_number").reset_index(drop=True)
    queue["review_decision"] = ""
    queue["verified_origin_id"] = ""
    queue["verified_diagnosis"] = ""
    queue["reviewer"] = ""
    queue["review_notes"] = ""
    preferred = [
        "patch",
        "patch_number",
        "raw_patch_path",
        "folder_label",
        "folder_label_number",
        "source_split_hint",
        "candidate_status",
        "proposed_correct_origin_id",
        "previous_accepted_patch",
        "previous_accepted_origin_id",
        "previous_accepted_diagnosis",
        "previous_accepted_distance",
        "next_accepted_patch",
        "next_accepted_origin_id",
        "next_accepted_diagnosis",
        "next_accepted_distance",
        "review_decision",
        "verified_origin_id",
        "verified_diagnosis",
        "reviewer",
        "review_notes",
    ]
    return queue[[column for column in preferred if column in queue.columns]]


def missing_items_from_rows(rows: pd.DataFrame) -> list[dict]:
    items = []
    for row in rows.itertuples(index=False):
        parts = [row.patch, str(getattr(row, "folder_label", ""))]
        previous_origin = getattr(row, "previous_accepted_origin_id", "")
        next_origin = getattr(row, "next_accepted_origin_id", "")
        if previous_origin or next_origin:
            parts.append(f"prev {previous_origin} / next {next_origin}")
        proposed_origin = getattr(row, "proposed_correct_origin_id", "")
        if proposed_origin:
            parts.append(f"proposed {proposed_origin}")
        items.append({"image_path": row.raw_patch_path, "label": " | ".join(parts)})
    return items


def context_items_for_block(block: pd.Series, candidates: pd.DataFrame, raw_patch_dir: Path) -> list[dict]:
    start = int(block["start_patch_number"])
    end = int(block["end_patch_number"])
    block_rows = candidates[(candidates["patch_number"] >= start) & (candidates["patch_number"] <= end)]
    items = []
    for prefix in ["previous", "next"]:
        patch = block.get(f"{prefix}_accepted_patch", "")
        origin = block.get(f"{prefix}_accepted_origin_id", "")
        diagnosis = block.get(f"{prefix}_accepted_diagnosis", "")
        if isinstance(patch, str) and patch:
            items.append({
                "image_path": str(Path(raw_patch_dir) / f"{patch}.png"),
                "label": f"{prefix}: {patch} | o{origin} | {diagnosis}",
            })
    return items[:1] + missing_items_from_rows(block_rows) + items[1:]


def candidate_origin_items(row, origin_image_dir: Path) -> list[dict]:
    candidates = []
    seen = set()
    for field, label in [
        ("proposed_correct_origin_id", "proposed"),
        ("previous_accepted_origin_id", "previous"),
        ("next_accepted_origin_id", "next"),
    ]:
        origin_id = getattr(row, field, "")
        if pd.isna(origin_id):
            origin_id = ""
        origin_id = str(origin_id).strip()
        if origin_id and origin_id not in seen:
            seen.add(origin_id)
            normalized_origin = f"{int(float(origin_id)):04d}"
            candidates.append({
                "image_path": str(Path(origin_image_dir) / f"{normalized_origin}.png"),
                "label": f"{label} origin {normalized_origin}",
            })
    return candidates


def patch_origin_comparison_rows(candidates: pd.DataFrame, origin_image_dir: Path) -> list[dict]:
    rows = []
    for row in candidates.sort_values("patch_number").itertuples(index=False):
        origin_items = candidate_origin_items(row, origin_image_dir)
        if not origin_items:
            continue
        label = (
            f"{row.patch} | folder={getattr(row, 'folder_label', '')} | "
            f"prev={getattr(row, 'previous_accepted_origin_id', '')} | "
            f"next={getattr(row, 'next_accepted_origin_id', '')}"
        )
        rows.append({
            "patch": row.patch,
            "patch_path": row.raw_patch_path,
            "origin_items": origin_items,
            "label": label,
        })
    return rows


def run_review_packet(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    sheets_dir = output_dir / "contact_sheets"
    block_dir = sheets_dir / "blocks"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(args.missing_candidates)
    patchless = pd.read_csv(args.patchless_origins) if Path(args.patchless_origins).exists() else pd.DataFrame()

    queue = build_review_queue(candidates)
    blocks = contiguous_missing_blocks(candidates)
    queue.to_csv(output_dir / "missing_patch_review_queue.csv", index=False)
    blocks.to_csv(output_dir / "missing_patch_blocks.csv", index=False)

    items = missing_items_from_rows(candidates)
    for page, start in enumerate(range(0, len(items), args.page_size), start=1):
        make_contact_sheet(
            items[start:start + args.page_size],
            sheets_dir / f"missing_patches_page_{page:03d}.png",
            columns=args.columns,
        )

    largest_blocks = blocks.sort_values("n_missing_patches", ascending=False).head(args.max_block_sheets)
    for block in largest_blocks.itertuples(index=False):
        block_series = pd.Series(block._asdict())
        block_items = context_items_for_block(block_series, candidates, args.raw_patch_dir)
        filename = (
            f"block_{int(block.block_id):03d}_"
            f"{block.start_patch}_{block.end_patch}_n{int(block.n_missing_patches)}.png"
        )
        make_contact_sheet(block_items, block_dir / filename, columns=args.columns)

    if not patchless.empty:
        patchless_items = [
            {
                "image_path": row.origin_image_path,
                "label": f"origin {row.origin_id} | {getattr(row, 'diagnosis', '')}",
            }
            for row in patchless.itertuples(index=False)
        ]
        make_contact_sheet(
            patchless_items,
            sheets_dir / "patchless_origin_images.png",
            columns=args.columns,
        )

    patch_vs_origin_dir = output_dir / "patch_vs_origin"
    comparison_rows = patch_origin_comparison_rows(candidates, args.origin_image_dir)
    for page, start in enumerate(range(0, len(comparison_rows), args.patch_origin_page_size), start=1):
        make_patch_origin_sheet(
            comparison_rows[start:start + args.patch_origin_page_size],
            patch_vs_origin_dir / f"patch_vs_origin_page_{page:03d}.png",
        )

    summary = {
        "missing_patch_rows": int(len(candidates)),
        "review_blocks": int(len(blocks)),
        "overview_contact_sheet_pages": int(math.ceil(len(items) / args.page_size)),
        "block_contact_sheets": int(len(largest_blocks)),
        "patch_vs_origin_pages": int(math.ceil(len(comparison_rows) / args.patch_origin_page_size)),
        "patchless_origin_sheet_written": bool(not patchless.empty),
        "review_policy": "candidate_only_manual_verified",
    }
    (output_dir / "review_packet_summary.json").write_text(pd.Series(summary).to_json(indent=2))
    return summary


def review_packet_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build manual review packets for missing/unassociated patch images.")
    parser.add_argument("--missing-candidates", type=Path, default=DEFAULT_MISSING_CANDIDATES)
    parser.add_argument("--patchless-origins", type=Path, default=DEFAULT_PATCHLESS_ORIGINS)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--origin-image-dir", type=Path, default=DEFAULT_ORIGIN_IMAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REVIEW_OUTPUT_DIR)
    parser.add_argument("--page-size", type=int, default=48)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--max-block-sheets", type=int, default=40)
    parser.add_argument("--patch-origin-page-size", type=int, default=12)
    return parser
