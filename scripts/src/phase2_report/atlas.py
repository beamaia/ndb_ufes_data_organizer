from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2 as cv
import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import PathPatch, Polygon, Rectangle  # noqa: E402
from matplotlib.path import Path as DrawPath  # noqa: E402

from src.phase0_dataset_builder.matching import overlap_fractions, parse_homography, read_bgr  # noqa: E402
from src.phase0_dataset_builder.sources import (  # noqa: E402
    DEFAULT_NDB_ORIGIN_DIR, DIAGNOSIS_COLOR, PATCH_TABLE_LAB, PICTURE_RELATIONS, PICTURE_TABLE_LAB, SHORT_LABEL,
)
from src.utils.logger import logger  # noqa: E402


SHORT = SHORT_LABEL
PATIENT_ATLAS = Path("atlases/patient_atlas.pdf")  # published in git and linked from the wiki
ALIGNED_ATLAS = Path("atlases/aligned_atlas.pdf")
JPEG_SETTING = "<< /ColorImageDict << /QFactor 0.3 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >> >> setdistillerparams"  # JPEG at about quality 85


def shrink_pdf(path: Path) -> None:
    """Recompress the images of a PDF as JPEG with Ghostscript; the text and the outlines stay vector.

    Matplotlib stores images without loss, which makes an atlas of tissue images several times larger than it needs to be.
    Without Ghostscript the file is kept as it was written.
    """
    ghostscript = shutil.which("gs")
    if ghostscript is None:
        logger.warning(f"Ghostscript (gs) is not installed; {path} keeps its lossless images and may be too large for git")
        return
    smaller = path.with_suffix(".small.pdf")
    subprocess.run(
        [ghostscript, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", "-dDownsampleColorImages=false",
         "-dAutoFilterColorImages=false", "-dColorImageFilter=/DCTEncode", f"-sOutputFile={smaller}", "-c", JPEG_SETTING, "-f", str(path)],
        check=True,
    )
    before, after = path.stat().st_size / 1e6, smaller.stat().st_size / 1e6
    smaller.replace(path)
    logger.info(f"Recompressed the images of {path.name}: {before:.1f} MB to {after:.1f} MB")

# patient-atlas: one PDF, a page per case group. Each picture shows its patches as boxes; under it every patch is drawn
# on its own next to the crop of the picture at its coordinates, so the position can be checked by eye. Related pictures
# (same tissue, from SIFT) sit next to each other, so a page shows the pictures of one possible patient.
UNASSIGNED = "no_case"
DIAGNOSIS_COLORS = DIAGNOSIS_COLOR
CARD_WIDTH_IN = 5.0
CARDS_PER_ROW = 3
GAP_IN = 0.25
TITLE_IN = 0.7
CARD_HEADER_IN = 0.3
MAX_PAGE_HEIGHT_IN = 40.0
CELLS_PER_ROW = 4  # each cell: the patch, the crop of the picture at its coordinates, two lines of text
CELL_GAP_PX = 8
TILE_GAP_PX = 4
TEXT_BAND_PX = 30


@dataclass
class _Box:
    label: str
    x: int
    y: int
    x2: int
    y2: int
    diagnosis: str


@dataclass
class _Card:
    header: str
    pixels: np.ndarray
    width: int
    height: int
    boxes: list[_Box]
    mosaic: np.ndarray | None
    mosaic_texts: list[tuple[int, int, str]]

    @property
    def image_height_in(self) -> float:
        return CARD_WIDTH_IN * self.height / self.width

    @property
    def mosaic_height_in(self) -> float:
        return 0.0 if self.mosaic is None else CARD_WIDTH_IN * self.mosaic.shape[0] / self.mosaic.shape[1]

    @property
    def height_in(self) -> float:
        return CARD_HEADER_IN + self.image_height_in + self.mosaic_height_in + 0.1 + GAP_IN


def _picture_path(picture: pd.Series, ndb_origin_dir: Path) -> Path:
    sab_files = [path for path in picture["sab_files"].split(" | ") if path]
    return Path(sab_files[0]) if sab_files else Path(ndb_origin_dir) / f"{picture['ndb_origin_id']}.png"


def _tiles(image: Image.Image, patches: pd.DataFrame, tile_px: int) -> tuple[np.ndarray, list[tuple[int, int, str]]]:
    """A mosaic with one cell per patch: the patch image, the picture's crop at its coordinates, and its coordinates as text."""
    cell_w = 2 * tile_px + TILE_GAP_PX
    cell_h = tile_px + TEXT_BAND_PX
    rows = math.ceil(len(patches) / CELLS_PER_ROW)
    canvas = np.full((rows * (cell_h + CELL_GAP_PX), CELLS_PER_ROW * (cell_w + CELL_GAP_PX), 3), 255, np.uint8)
    texts = []
    for index, patch in enumerate(patches.itertuples()):
        row, column = divmod(index, CELLS_PER_ROW)
        left, top = column * (cell_w + CELL_GAP_PX), row * (cell_h + CELL_GAP_PX)
        with Image.open(patch.patch_path) as patch_image:
            alone = np.asarray(patch_image.convert("RGB").resize((tile_px, tile_px), Image.LANCZOS))
        crop = np.asarray(image.crop((int(patch.x), int(patch.y), int(patch.x2), int(patch.y2))).resize((tile_px, tile_px), Image.LANCZOS))
        canvas[top : top + tile_px, left : left + tile_px] = alone
        canvas[top : top + tile_px, left + tile_px + TILE_GAP_PX : left + cell_w] = crop
        text = f"{patch.patch_id.removeprefix('p')} {SHORT[patch.patch_diagnosis]}\n({patch.x},{patch.y})-({patch.x2},{patch.y2})"
        texts.append((left, top + tile_px + 3, text))
    return canvas, texts


def _card(picture: pd.Series, patches: pd.DataFrame, group_size: int, ndb_origin_dir: Path, thumb_width: int, tile_px: int) -> _Card:
    patches = patches.sort_values(["y", "x"], key=lambda column: column.astype(int))
    with Image.open(_picture_path(picture, ndb_origin_dir)) as image:
        image = image.convert("RGB")
        width, height = image.size
        pixels = np.asarray(image.resize((thumb_width, round(thumb_width * height / width)), Image.LANCZOS))
        mosaic, texts = _tiles(image, patches, tile_px) if len(patches) else (None, [])
    boxes = [_Box(row.patch_id.removeprefix("p"), int(row.x), int(row.y), int(row.x2), int(row.y2), row.patch_diagnosis) for row in patches.itertuples()]
    origin = f"NDB {picture['ndb_origin_id']}" if picture["ndb_origin_id"] else "SAB only"
    related = f" | related views: {group_size}" if group_size > 1 else ""
    header = f"{picture['histopath_id']} | {origin} | {width}x{height} | {len(boxes)} patches{related}"
    return _Card(header, pixels, width, height, boxes, mosaic, texts)


def _draw_card(fig, card: _Card, left: float, top: float, page_width: float, page_height: float) -> None:
    def axes(x: float, y: float, w: float, h: float):
        return fig.add_axes([x / page_width, 1 - (y + h) / page_height, w / page_width, h / page_height])

    fig.text(left / page_width, 1 - (top + CARD_HEADER_IN / 2) / page_height, card.header, fontsize=7, va="center")
    image_top = top + CARD_HEADER_IN
    ax = axes(left, image_top, CARD_WIDTH_IN, card.image_height_in)
    ax.imshow(card.pixels, extent=(0, card.width, card.height, 0), aspect="auto")
    for box in card.boxes:
        color = DIAGNOSIS_COLORS[box.diagnosis]
        ax.add_patch(Rectangle((box.x, box.y), box.x2 - box.x, box.y2 - box.y, fill=False, edgecolor=color, linewidth=0.6))
        ax.text(box.x + 4, box.y + 4, box.label, fontsize=3.5, color=color, va="top", ha="left")
    ax.axis("off")
    if card.mosaic is not None:
        mosaic_ax = axes(left, image_top + card.image_height_in + 0.05, CARD_WIDTH_IN, card.mosaic_height_in)
        mosaic_ax.imshow(card.mosaic, extent=(0, card.mosaic.shape[1], card.mosaic.shape[0], 0), aspect="auto")
        for x, y, text in card.mosaic_texts:
            mosaic_ax.text(x, y, text, fontsize=3.8, family="monospace", va="top", ha="left")
        mosaic_ax.axis("off")


def _pages(rows: list[list[_Card]]) -> list[list[list[_Card]]]:
    """Fill each page with rows of pictures until it would pass the maximum height."""
    pages, current, height = [], [], TITLE_IN + GAP_IN
    for row in rows:
        row_height = max(card.height_in for card in row)
        if current and height + row_height > MAX_PAGE_HEIGHT_IN:
            pages.append(current)
            current, height = [], TITLE_IN + GAP_IN
        current.append(row)
        height += row_height
    return pages + [current]


def run_render_patient_atlas(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patches = pd.read_csv(args.patch_table, dtype=str, keep_default_na=False)
    pictures = pd.read_csv(args.picture_table, dtype=str, keep_default_na=False)
    pictures["case_group"] = pictures["case_group"].replace("", UNASSIGNED)
    pseudonyms_of_group = pictures.groupby("case_group")["case_pseudonym"].apply(lambda cells: sorted({name for cell in cells for name in cell.split()})).to_dict()
    group_sizes = pictures.groupby("picture_group").size().to_dict()
    patches_of = {picture_id: group for picture_id, group in patches.groupby("histopath_id")}

    case_group_ids = sorted(pictures["case_group"].unique(), key=lambda name: (name == UNASSIGNED, name))
    if args.limit_groups:
        case_group_ids = case_group_ids[: args.limit_groups]
    page_width = CARDS_PER_ROW * CARD_WIDTH_IN + (CARDS_PER_ROW + 1) * GAP_IN
    legend = [(name, DIAGNOSIS_COLORS[name]) for name in DIAGNOSIS_COLORS]
    pages = drawn_pictures = drawn_patches = 0
    with PdfPages(output_dir / PATIENT_ATLAS.name) as pdf:
        for case_group in case_group_ids:
            members = pictures[pictures["case_group"] == case_group].sort_values(["picture_group", "histopath_id"])
            cards = [
                _card(picture, patches_of.get(picture["histopath_id"], patches.iloc[0:0]), group_sizes[picture["picture_group"]],
                      args.ndb_origin_dir, args.thumb_width, args.tile_pixels)
                for _, picture in members.iterrows()
            ]
            rows = [cards[start : start + CARDS_PER_ROW] for start in range(0, len(cards), CARDS_PER_ROW)]
            chunks = _pages(rows)
            cases = ", ".join(pseudonyms_of_group.get(case_group, [])) or "pictures not tied to a case (NDB-UFES only)"
            for number, chunk in enumerate(chunks, start=1):
                row_heights = [max(card.height_in for card in row) for row in chunk]
                page_height = TITLE_IN + sum(row_heights) + GAP_IN
                fig = plt.figure(figsize=(page_width, page_height))
                part = f"  (page {number}/{len(chunks)})" if len(chunks) > 1 else ""
                fig.text(GAP_IN / page_width, 1 - 0.28 / page_height, f"{case_group} | {cases} | {len(members)} pictures{part}", fontsize=11, va="center", weight="bold")
                fig.text(GAP_IN / page_width, 1 - 0.52 / page_height, "boxes: patch position in the picture. Under each picture: the patch (left) beside the picture's crop at its coordinates (right), with patch id, label and (x,y)-(x2,y2) in pixels of the full-size picture", fontsize=6, va="center")
                for index, (name, color) in enumerate(legend):
                    fig.text((page_width - 3.4 + index * 1.1) / page_width, 1 - 0.28 / page_height, f"■ {SHORT[name]}", color=color, fontsize=9, va="center")
                top = TITLE_IN
                for row, row_height in zip(chunk, row_heights):
                    for column, card in enumerate(row):
                        _draw_card(fig, card, GAP_IN + column * (CARD_WIDTH_IN + GAP_IN), top, page_width, page_height)
                    top += row_height
                pdf.savefig(fig)
                plt.close(fig)
                pages += 1
            drawn_pictures += len(cards)
            drawn_patches += sum(len(card.boxes) for card in cards)
            logger.info(f"{case_group}: {len(cards)} pictures, {len(chunks)} page(s)")
    shrink_pdf(output_dir / PATIENT_ATLAS.name)
    size_mb = (output_dir / PATIENT_ATLAS.name).stat().st_size / 1e6
    logger.info(f"Outputs saved under {output_dir}")
    return {"case_groups": len(case_group_ids), "pages": pages, "pictures_drawn": drawn_pictures, "patches_drawn": drawn_patches, "pdf_megabytes": round(size_mb, 1)}


def render_patient_atlas_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PDF with a page per case group: pictures with patch boxes, each patch beside the crop of the picture at its coordinates.")
    parser.add_argument("--patch-table", type=Path, default=PATCH_TABLE_LAB)
    parser.add_argument("--picture-table", type=Path, default=PICTURE_TABLE_LAB)
    parser.add_argument("--ndb-origin-dir", type=Path, default=DEFAULT_NDB_ORIGIN_DIR)
    parser.add_argument("--output-dir", type=Path, default=PATIENT_ATLAS.parent)
    parser.add_argument("--thumb-width", type=int, default=480, help="Pixel width of each picture in the PDF; larger means a bigger file.")
    parser.add_argument("--tile-pixels", type=int, default=64, help="Pixel size of each patch tile and crop tile; larger means a bigger file.")
    parser.add_argument("--limit-groups", type=int, default=None, help="Trial run on the first N case groups.")
    return parser


# aligned-atlas: one row per strong SIFT relation between two pictures, laid out like an equation.
# Same zoom: picture A + picture B (rotated to match A) = the two joined into one picture.
# Different zoom: the wide picture with a rectangle where the close-up lies, "=", and the close-up rotated to the wide picture's direction.
# No patches are drawn.
SAME_ZOOM_RATIO = 1.25  # a relation is "same zoom" when the scale between the pictures is within this factor of 1
DISPLAY_PX = 1000  # longest side of each picture in the PDF
RECTANGLE_COLOR = "#2ca02c"
SECOND_COLOR = "#ff7f0e"
PICTURE_EDGE_COLOR = "#888888"
SHADE_ALPHA = 0.55
COLUMN_WIDTH_IN = 5.5
PANEL_HEADER_IN = 0.3
BLOCK_HEADER_IN = 0.3
EQUALS_WIDTH_IN = 0.6
SAME_ZOOM_PANEL_IN = 3.6  # three panels and two signs fit on the page


def _corners(width: int, height: int) -> np.ndarray:
    return np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)


def _footprint(matrix: np.ndarray, width: int, height: int) -> np.ndarray:
    return cv.perspectiveTransform(_corners(width, height), matrix).reshape(-1, 2)


def _scale_and_rotation(matrix: np.ndarray) -> tuple[float, np.ndarray]:
    """Scale (pixels of the target per pixel of the source) and the pure rotation inside a homography's linear part."""
    linear = matrix[:2, :2] / matrix[2, 2]
    u, _, vt = np.linalg.svd(linear)
    if np.linalg.det(u @ vt) < 0:
        u[:, -1] *= -1
    return math.sqrt(abs(np.linalg.det(linear))), u @ vt


def _angle(rotation: np.ndarray) -> float:
    return math.degrees(math.atan2(rotation[1, 0], rotation[0, 0]))


@dataclass
class _Panel:
    title: str
    pixels: np.ndarray
    size: tuple[int, int]  # width, height of the coordinate system the outlines are in
    outlines: list[tuple[np.ndarray, str]]  # polygon, colour
    width_in: float = COLUMN_WIDTH_IN
    view: tuple[float, float, float, float] | None = None  # x min, x max, y min, y max shown; the picture's own area by default
    lit: np.ndarray | None = None  # when set, everything outside this polygon is shaded

    def __post_init__(self) -> None:
        if self.view is None:
            self.view = (0.0, float(self.size[0]), 0.0, float(self.size[1]))

    @property
    def height_in(self) -> float:
        return PANEL_HEADER_IN + self.width_in * (self.view[3] - self.view[2]) / (self.view[1] - self.view[0])


@dataclass
class _Block:
    header: str
    panels: list[_Panel]
    signs: list[str]  # between neighbouring panels: "=" for a close-up, "+" and "=" for two pictures joined

    @property
    def height_in(self) -> float:
        return BLOCK_HEADER_IN + max(panel.height_in for panel in self.panels) + GAP_IN


def _thumbnail(rgb: np.ndarray) -> np.ndarray:
    scale = min(1.0, DISPLAY_PX / max(rgb.shape[:2]))
    return rgb if scale == 1.0 else cv.resize(rgb, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)


def _label(picture: pd.Series) -> str:
    return f"{picture['histopath_id']} | " + (f"NDB {picture['ndb_origin_id']}" if picture["ndb_origin_id"] else "SAB only")


def _rotated(rgb: np.ndarray, rotation: np.ndarray) -> tuple[np.ndarray, tuple[int, int], np.ndarray, np.ndarray]:
    """The picture turned by the rotation, on white, shrunk to the display size: pixels, size, the outline of the picture in them, and the matrix into them."""
    size = (rgb.shape[1], rgb.shape[0])
    centre = np.array(size, np.float32) / 2
    corners = (_footprint(np.eye(3), *size) - centre) @ rotation.T
    low, high = corners.min(axis=0), corners.max(axis=0)
    shrink = min(1.0, DISPLAY_PX / max(high - low))
    out_size = (int(math.ceil((high[0] - low[0]) * shrink)), int(math.ceil((high[1] - low[1]) * shrink)))
    affine = shrink * np.hstack([rotation, (-rotation @ centre - low)[:, None]])
    pixels = cv.warpAffine(rgb, affine, out_size, flags=cv.INTER_AREA if shrink < 1 else cv.INTER_LINEAR, borderValue=(255, 255, 255))
    return pixels, out_size, (corners - low) * shrink, np.vstack([affine, [0, 0, 1]])


def _joined(a_rgb: np.ndarray, b_rgb: np.ndarray, b_to_a: np.ndarray) -> tuple[np.ndarray, tuple[int, int], np.ndarray, np.ndarray]:
    """A and B in the frame of A, blended into one picture (feathered where they overlap): pixels, size, outline of A, outline of B."""
    a_size, b_size = (a_rgb.shape[1], a_rgb.shape[0]), (b_rgb.shape[1], b_rgb.shape[0])
    a_outline, b_outline = _footprint(np.eye(3), *a_size), _footprint(b_to_a, *b_size)
    low, high = np.vstack([a_outline, b_outline]).min(axis=0), np.vstack([a_outline, b_outline]).max(axis=0)
    scale = DISPLAY_PX / max(high - low)
    canvas = (int(round((high[0] - low[0]) * scale)), int(round((high[1] - low[1]) * scale)))
    frame = np.array([[scale, 0, -low[0] * scale], [0, scale, -low[1] * scale], [0, 0, 1]])

    def place(rgb: np.ndarray, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        pixels = cv.warpPerspective(rgb, frame @ matrix, canvas, flags=cv.INTER_LINEAR).astype(np.float32)
        covered = cv.warpPerspective(np.ones(rgb.shape[:2], np.uint8), frame @ matrix, canvas, flags=cv.INTER_NEAREST)
        return pixels, cv.distanceTransform(covered, cv.DIST_L2, 3)  # weight grows with the distance from the picture's edge

    (a_pixels, a_weight), (b_pixels, b_weight) = place(a_rgb, np.eye(3)), place(b_rgb, b_to_a)
    total = a_weight + b_weight
    blended = (a_pixels * a_weight[..., None] + b_pixels * b_weight[..., None]) / np.maximum(total, 1e-6)[..., None]
    pixels = np.where(total[..., None] > 0, blended, 255).astype(np.uint8)
    to_canvas = lambda polygon: cv.perspectiveTransform(polygon.reshape(-1, 1, 2).astype(np.float32), frame).reshape(-1, 2)
    return pixels, canvas, to_canvas(a_outline), to_canvas(b_outline)


def _same_zoom_block(a: pd.Series, b: pd.Series, a_rgb: np.ndarray, b_rgb: np.ndarray, b_to_a: np.ndarray, header: str) -> _Block:
    """Picture A + picture B (turned to A's direction) = the two joined into one picture."""
    _, rotation = _scale_and_rotation(b_to_a)
    b_pixels, b_size, b_border, _ = _rotated(b_rgb, rotation)
    a_size = (a_rgb.shape[1], a_rgb.shape[0])
    joined, canvas, a_outline, b_outline = _joined(a_rgb, b_rgb, b_to_a)
    width = SAME_ZOOM_PANEL_IN
    panels = [
        _Panel(_label(a), _thumbnail(a_rgb), a_size, [(_footprint(np.eye(3), *a_size), RECTANGLE_COLOR)], width),
        _Panel(f"{_label(b)} | rotated {_angle(rotation):+.1f} deg to match", b_pixels, b_size, [(b_border, SECOND_COLOR)], width),
        _Panel(f"joined (green: {a['histopath_id']}, orange: {b['histopath_id']})", joined, canvas, [(a_outline, RECTANGLE_COLOR), (b_outline, SECOND_COLOR)], width),
    ]
    return _Block(header, panels, signs=["+", "="])


def _zoom_block(wide: pd.Series, close: pd.Series, wide_rgb: np.ndarray, close_rgb: np.ndarray, close_to_wide: np.ndarray, header: str) -> _Block:
    """The wide picture with a rectangle where the close-up lies, and the close-up rotated to the wide picture's direction.

    The close-up can reach past the edge of the wide picture: the wide panel then shows the whole rectangle, and the close-up
    marks where the wide picture ends and shades what lies outside it.
    """
    scale, rotation = _scale_and_rotation(close_to_wide)
    wide_size, close_size = (wide_rgb.shape[1], wide_rgb.shape[0]), (close_rgb.shape[1], close_rgb.shape[0])
    rectangle = _footprint(close_to_wide, *close_size)
    rotated, size, border, display = _rotated(close_rgb, rotation)
    wide_in_close = cv.perspectiveTransform(_footprint(np.eye(3), *wide_size).reshape(-1, 1, 2).astype(np.float32), display @ np.linalg.inv(close_to_wide)).reshape(-1, 2)
    inside, _ = overlap_fractions(close_to_wide, close_size, wide_size)

    low, high = np.minimum(rectangle.min(axis=0), 0), np.maximum(rectangle.max(axis=0), wide_size)
    panels = [
        _Panel(f"{_label(wide)} | wide view; green: where the close-up lies, grey: edge of the wide picture", _thumbnail(wide_rgb), wide_size,
               [(_footprint(np.eye(3), *wide_size), PICTURE_EDGE_COLOR), (rectangle, RECTANGLE_COLOR)], view=(low[0], high[0], low[1], high[1])),
        _Panel(f"{_label(close)} | close-up, x{1 / scale:.1f} magnified, rotated {_angle(rotation):+.1f} deg to match",
               rotated, size, [(border, RECTANGLE_COLOR), (wide_in_close, SECOND_COLOR)], lit=wide_in_close),
    ]
    return _Block(f"{header} | {inside:.0%} of the close-up lies in the wide picture (orange line: its edge; shaded: outside it)", panels, signs=["="])


def _relation_block(relation, pictures: dict[str, pd.Series], images: dict[str, np.ndarray]) -> _Block:
    a, b = pictures[relation.a], pictures[relation.b]
    a_to_b = parse_homography(relation.homography)
    scale, rotation = _scale_and_rotation(a_to_b)
    matched = f"{relation.inliers} matched features"
    if scale < 1 / SAME_ZOOM_RATIO:  # A fills only a small part of B: A is the close-up
        header = f"{b['histopath_id']} contains {a['histopath_id']} | close-up x{1 / scale:.1f} | {matched}"
        return _zoom_block(b, a, images[relation.b], images[relation.a], a_to_b, header)
    if scale > SAME_ZOOM_RATIO:  # B is the close-up of A
        header = f"{a['histopath_id']} contains {b['histopath_id']} | close-up x{scale:.1f} | {matched}"
        return _zoom_block(a, b, images[relation.a], images[relation.b], np.linalg.inv(a_to_b), header)
    header = f"{a['histopath_id']} and {b['histopath_id']} | same zoom (x{scale:.2f}), rotated {_angle(rotation):+.1f} deg | {matched}"
    return _same_zoom_block(a, b, images[relation.a], images[relation.b], np.linalg.inv(a_to_b), header)


def _signed_area(polygon: np.ndarray) -> float:
    x, y = polygon[:, 0], polygon[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _draw_panel(fig, panel: _Panel, left: float, top: float, page_width: float, page_height: float) -> None:
    fig.text(left / page_width, 1 - (top + PANEL_HEADER_IN / 2) / page_height, panel.title, fontsize=6.5, va="center")
    ax = fig.add_axes([left / page_width, 1 - (top + panel.height_in) / page_height, panel.width_in / page_width, (panel.height_in - PANEL_HEADER_IN) / page_height])
    ax.imshow(panel.pixels, extent=(0, panel.size[0], panel.size[1], 0), aspect="auto")
    if panel.lit is not None:  # shade everything in the picture that is outside the lit polygon
        outer = np.array([[0, 0], [panel.size[0], 0], [panel.size[0], panel.size[1]], [0, panel.size[1]]], float)
        inner = panel.lit if _signed_area(panel.lit) * _signed_area(outer) < 0 else panel.lit[::-1]
        vertices = np.vstack([outer, outer[:1], inner, inner[:1]])
        codes = [DrawPath.MOVETO] + [DrawPath.LINETO] * 3 + [DrawPath.CLOSEPOLY] + [DrawPath.MOVETO] + [DrawPath.LINETO] * (len(inner) - 1) + [DrawPath.CLOSEPOLY]
        ax.add_patch(PathPatch(DrawPath(vertices, codes), facecolor="white", edgecolor="none", alpha=SHADE_ALPHA))
    for outline, color in panel.outlines:
        ax.add_patch(Polygon(outline, closed=True, fill=False, edgecolor=color, linewidth=1.2))
    ax.set_xlim(panel.view[0], panel.view[1])
    ax.set_ylim(panel.view[3], panel.view[2])
    ax.axis("off")


def _draw_block(fig, block: _Block, top: float, page_width: float, page_height: float) -> None:
    fig.text(GAP_IN / page_width, 1 - (top + BLOCK_HEADER_IN / 2) / page_height, block.header, fontsize=8, va="center", weight="bold")
    top += BLOCK_HEADER_IN
    total = sum(panel.width_in for panel in block.panels) + EQUALS_WIDTH_IN * len(block.signs)
    left = (page_width - total) / 2
    height = max(panel.height_in for panel in block.panels)
    for index, panel in enumerate(block.panels):
        _draw_panel(fig, panel, left, top, page_width, page_height)
        left += panel.width_in
        if index < len(block.signs):
            fig.text((left + EQUALS_WIDTH_IN / 2) / page_width, 1 - (top + PANEL_HEADER_IN + (height - PANEL_HEADER_IN) / 2) / page_height, block.signs[index], fontsize=28, ha="center", va="center")
            left += EQUALS_WIDTH_IN


def run_render_aligned_atlas(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pictures = pd.read_csv(args.picture_table, dtype=str, keep_default_na=False)
    relations = pd.read_csv(args.relations)
    strong = relations[relations["strong"].astype(bool)]
    picture_rows = {row["histopath_id"]: row for _, row in pictures.iterrows()}
    group_of = dict(zip(pictures["histopath_id"], pictures["picture_group"]))

    related_groups = sorted({group_of[a] for a in strong["a"]}, key=lambda group: (pictures.loc[pictures["picture_group"] == group, "case_group"].iloc[0] or "~", group))
    if args.limit_groups:
        related_groups = related_groups[: args.limit_groups]
    page_width = 2 * COLUMN_WIDTH_IN + EQUALS_WIDTH_IN + 2 * GAP_IN
    pages = blocks_drawn = 0
    with PdfPages(output_dir / ALIGNED_ATLAS.name) as pdf:
        for group in related_groups:
            members = pictures[pictures["picture_group"] == group]
            ids = set(members["histopath_id"])
            images = {i: cv.cvtColor(read_bgr(_picture_path(picture_rows[i], args.ndb_origin_dir)), cv.COLOR_BGR2RGB) for i in ids}
            blocks = [_relation_block(relation, picture_rows, images) for relation in strong[strong["a"].isin(ids) & strong["b"].isin(ids)].itertuples()]

            case_group = members["case_group"].iloc[0] or UNASSIGNED
            cases = ", ".join(sorted({name for cell in members["case_pseudonym"] for name in cell.split()})) or "no case"
            chunks, current, height = [], [], TITLE_IN + GAP_IN
            for block in blocks:
                if current and height + block.height_in > MAX_PAGE_HEIGHT_IN:
                    chunks.append(current)
                    current, height = [], TITLE_IN + GAP_IN
                current.append(block)
                height += block.height_in
            chunks.append(current)
            for number, chunk in enumerate(chunks, start=1):
                page_height = TITLE_IN + sum(block.height_in for block in chunk) + GAP_IN
                fig = plt.figure(figsize=(page_width, page_height))
                part = f"  (page {number}/{len(chunks)})" if len(chunks) > 1 else ""
                fig.text(GAP_IN / page_width, 1 - 0.28 / page_height, f"{group} | {case_group} ({cases}) | {len(members)} related pictures{part}", fontsize=11, va="center", weight="bold")
                fig.text(GAP_IN / page_width, 1 - 0.52 / page_height, "each row is one relation found by SIFT; green outlines show where one picture lies in the other; pictures are rotated to the same direction", fontsize=6, va="center")
                top = TITLE_IN
                for block in chunk:
                    _draw_block(fig, block, top, page_width, page_height)
                    top += block.height_in
                pdf.savefig(fig)
                plt.close(fig)
                pages += 1
            blocks_drawn += len(blocks)
            logger.info(f"{group}: {len(blocks)} relations, {len(chunks)} page(s)")
    shrink_pdf(output_dir / ALIGNED_ATLAS.name)
    size_mb = (output_dir / ALIGNED_ATLAS.name).stat().st_size / 1e6
    logger.info(f"Outputs saved under {output_dir}")
    return {"groups": len(related_groups), "relations_drawn": blocks_drawn, "pages": pages, "pdf_megabytes": round(size_mb, 1)}


def render_aligned_atlas_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PDF with a row per relation between two pictures: stacked at the same zoom, or wide picture = rotated close-up.")
    parser.add_argument("--picture-table", type=Path, default=PICTURE_TABLE_LAB)
    parser.add_argument("--relations", type=Path, default=PICTURE_RELATIONS)
    parser.add_argument("--ndb-origin-dir", type=Path, default=DEFAULT_NDB_ORIGIN_DIR)
    parser.add_argument("--output-dir", type=Path, default=ALIGNED_ATLAS.parent)
    parser.add_argument("--limit-groups", type=int, default=None, help="Trial run on the first N groups.")
    return parser
