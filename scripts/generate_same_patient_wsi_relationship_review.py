#!/usr/bin/env python3
"""Create the same-patient WSI image-relationship review notebook and PDF."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path("/Users/beamaia/thesis_organization/ndb_ufes_data_organizer")
NOTEBOOK = REPO / "notebooks/same_patient_wsi_image_relationships_review.ipynb"
PDF = REPO / "docs/assets/contamination/same_patient_wsi_image_relationships.pdf"


COMMON_IMPORTS = r'''
from __future__ import annotations

import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon
from IPython.display import display

REPO = Path("/Users/beamaia/thesis_organization/ndb_ufes_data_organizer")
AUDIT_PATH = REPO / "results/phase0/validated_linkage/same_patient_wsi_image_relationships.csv"
PDF_PATH = REPO / "docs/assets/contamination/same_patient_wsi_image_relationships.pdf"
IMAGE_ROOT = REPO

audit = pd.read_csv(AUDIT_PATH)
audit["candidate"] = audit["candidate"].astype(str).str.lower().eq("true")
candidates = (
    audit.loc[audit["candidate"]]
    .sort_values(["patient_id", "origin_a", "origin_b"])
    .reset_index(drop=True)
)

print(f"Compared image pairs in audit: {len(audit):,}")
print(f"Candidate pairs included in this PDF: {len(candidates):,}")
print(f"Patient/case groups represented: {candidates['patient_id'].nunique():,}")
display(candidates[[
    "patient_id", "origin_a", "origin_b", "diagnosis_a", "diagnosis_b",
    "scale_a_to_b_x", "scale_b_to_a_x", "geometric_inliers_a_to_b",
    "median_reprojection_error_px", "interpretation"
]])
'''


HELPERS = r'''
def load_rgb(relative_path: str) -> np.ndarray:
    path = IMAGE_ROOT / relative_path
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def parse_quad(value: str):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        points = np.asarray(json.loads(value), dtype=np.float32)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return points if points.shape == (4, 2) and np.isfinite(points).all() else None


def resize_for_display(image: np.ndarray, max_side: int = 900) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    if scale == 1.0:
        return image
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def crop_from_quad(image: np.ndarray, quad: np.ndarray, output_size=(900, 675)) -> np.ndarray:
    target = np.array([
        [0, 0],
        [output_size[0] - 1, 0],
        [output_size[0] - 1, output_size[1] - 1],
        [0, output_size[1] - 1],
    ], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(quad.astype(np.float32), target)
    return cv2.warpPerspective(image, matrix, output_size)


def choose_relationship(row: pd.Series):
    scale_a = float(row["scale_a_to_b_x"])
    scale_b = float(row["scale_b_to_a_x"])
    if scale_a >= scale_b:
        original_name, target_name = "a", "b"
        original_path, target_path = row["image_a"], row["image_b"]
        projected_target = parse_quad(row["source_b_corners_in_a"])
        scale = scale_a
    else:
        original_name, target_name = "b", "a"
        original_path, target_path = row["image_b"], row["image_a"]
        projected_target = parse_quad(row["source_a_corners_in_b"])
        scale = scale_b
    return original_name, target_name, original_path, target_path, projected_target, scale


def relation_label(scale: float) -> str:
    if scale >= 1.5:
        return "scaled/cropped relationship candidate"
    if scale <= 2 / 3:
        return "reverse scaled/cropped relationship candidate"
    return "near-scale alignment candidate"


def render_candidate(row: pd.Series, number: int, total: int):
    original_name, target_name, original_path, target_path, quad, scale = choose_relationship(row)
    original = load_rgb(original_path)
    target = load_rgb(target_path)
    original_display = resize_for_display(original)
    target_display = resize_for_display(target)
    rectified = crop_from_quad(original, quad) if quad is not None else None

    fig = plt.figure(figsize=(15, 10.3), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.08, wspace=0.04)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]),
            fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]

    axes[0].imshow(original_display)
    axes[0].set_title(f"Original view ({original_name.upper()}): {Path(original_path).name}")
    if quad is not None:
        h, w = original.shape[:2]
        sx, sy = original_display.shape[1] / w, original_display.shape[0] / h
        display_quad = quad * np.array([sx, sy])
        axes[0].add_patch(Polygon(display_quad, closed=True, fill=False, linewidth=2.2, edgecolor="#ffd43b"))
        for index, (x, y) in enumerate(display_quad, start=1):
            axes[0].text(x, y, str(index), color="black", fontsize=10, weight="bold",
                         bbox=dict(facecolor="#ffd43b", edgecolor="none", pad=1.5))
    axes[0].set_xlabel("Yellow quadrilateral: projected target region")

    axes[1].imshow(target_display)
    axes[1].set_title(f"Compared view ({target_name.upper()}): {Path(target_path).name}")
    axes[1].set_xlabel("Image used by the geometric comparison")

    if rectified is not None:
        axes[2].imshow(resize_for_display(rectified))
        axes[2].set_title("Perspective-rectified crop from original view")
    else:
        axes[2].text(0.5, 0.5, "Projected region unavailable", ha="center", va="center")
        axes[2].set_title("Candidate region")

    if rectified is not None:
        overlay_target = cv2.resize(target, (rectified.shape[1], rectified.shape[0]), interpolation=cv2.INTER_AREA)
        overlay = cv2.addWeighted(rectified, 0.5, overlay_target, 0.5, 0)
        axes[3].imshow(resize_for_display(overlay))
        axes[3].set_title("Rectified crop / compared image overlay")
    else:
        axes[3].imshow(target_display)
        axes[3].set_title("Compared image")

    for axis in axes:
        axis.axis("off")

    patient = row["patient_id"]
    fig.suptitle(
        f"Same-patient WSI image relationship review | candidate {number}/{total}\n"
        f"Patient/case group: {patient} | origins {row['origin_a']} and {row['origin_b']} | "
        f"{relation_label(scale)}",
        fontsize=14, weight="bold",
    )
    summary = (
        f"classes: {row['diagnosis_a']} / {row['diagnosis_b']}    "
        f"scale A→B: {row['scale_a_to_b_x']:.3f}    scale B→A: {row['scale_b_to_a_x']:.3f}    "
        f"geometric inliers: {int(row['geometric_inliers_a_to_b'])}    "
        f"median reprojection error: {row['median_reprojection_error_px']:.3f} px    "
        f"interpretation: {row['interpretation']}"
    )
    fig.text(0.5, 0.005, summary, ha="center", va="bottom", fontsize=8.5)
    return fig
'''


PDF_CELL = r'''
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def pil_panel(image: np.ndarray, title: str, quad=None, panel_size=(390, 230)) -> Image.Image:
    panel_width, panel_height = panel_size
    panel = Image.new("RGB", (panel_width, panel_height), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((8, 6), title, fill="black", font=font)
    image_area = (8, 25, panel_width - 8, panel_height - 8)
    image_pil = Image.fromarray(image)
    image_pil.thumbnail((image_area[2] - image_area[0], image_area[3] - image_area[1]), Image.Resampling.LANCZOS)
    x = image_area[0] + (image_area[2] - image_area[0] - image_pil.width) // 2
    y = image_area[1] + (image_area[3] - image_area[1] - image_pil.height) // 2
    panel.paste(image_pil, (x, y))
    if quad is not None:
        height, width = image.shape[:2]
        sx, sy = image_pil.width / width, image_pil.height / height
        points = [(x + float(px) * sx, y + float(py) * sy) for px, py in quad]
        draw.line(points + [points[0]], fill="#ffd43b", width=3)
        for index, (px, py) in enumerate(points, start=1):
            draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill="#ffd43b", outline="black")
            draw.text((px - 2, py - 5), str(index), fill="black", font=font)
    return panel


def page_panels(row: pd.Series, number: int, total: int):
    original_name, target_name, original_path, target_path, quad, scale = choose_relationship(row)
    original = load_rgb(original_path)
    target = load_rgb(target_path)
    rectified = crop_from_quad(original, quad) if quad is not None else np.zeros((675, 900, 3), dtype=np.uint8)
    target_for_overlay = cv2.resize(target, (rectified.shape[1], rectified.shape[0]), interpolation=cv2.INTER_AREA)
    overlay = cv2.addWeighted(rectified, 0.5, target_for_overlay, 0.5, 0)
    return [
        pil_panel(original, f"Original view ({original_name.upper()})", quad=quad),
        pil_panel(target, f"Compared view ({target_name.upper()})"),
        pil_panel(rectified, "Perspective-rectified crop"),
        pil_panel(overlay, "Rectified crop / compared image overlay"),
    ], original_name, target_name, scale, quad


def draw_text_block(pdf, lines, x, y, font="Helvetica", size=8, leading=10):
    text = pdf.beginText(x, y)
    text.setFont(font, size)
    text.setLeading(leading)
    for line in lines:
        text.textLine(line)
    pdf.drawText(text)


def write_review_pdf(frame: pd.DataFrame, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(output_path), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle("Same-patient WSI image relationship review")
    pdf.setAuthor("Beatriz Matias Santana Maia")
    pdf.setSubject("Exploratory geometric review of same-patient source images")

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(48, page_height - 58, "Same-patient WSI image relationship review")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(48, page_height - 82, "Exploratory visual review for the NDB-UFES data organizer wiki")
    draw_text_block(pdf, [
        f"Image pairs compared in the audit: {len(audit):,}",
        f"Pairs included in this review: {len(frame):,}",
        f"Patient/case groups represented: {frame['patient_id'].nunique():,}",
        "",
        "Selection rule: only rows marked candidate=True by the same-patient image audit are included.",
        "The audit used feature matches, homography registration, scale estimates, and reprojection error.",
        "",
        "The yellow quadrilateral marks the region projected from the original view into the compared image.",
        "The rectified crop and overlay make a possible scaled/cropped relationship easier to inspect.",
        "",
        "These pages are image-evidence screening only; they do not prove identity, duplication, or contamination.",
    ], 48, page_height - 130, size=11, leading=19)
    draw_text_block(pdf, [
        "Source audit: results/phase0/validated_linkage/same_patient_wsi_image_relationships.csv",
        "Generated from: notebooks/same_patient_wsi_image_relationships_review.ipynb",
    ], 48, 74, font="Courier", size=7, leading=10)
    pdf.showPage()

    for number, (_, row) in enumerate(frame.iterrows(), start=1):
        panels, original_name, target_name, scale, quad = page_panels(row, number, len(frame))
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(24, page_height - 22, f"Candidate {number}/{len(frame)} | patient/case group {row['patient_id']} | origins {row['origin_a']} and {row['origin_b']}")
        pdf.setFont("Helvetica", 8)
        pdf.drawString(24, page_height - 35, f"{relation_label(scale)} | classes: {row['diagnosis_a']} / {row['diagnosis_b']}")
        positions = [(22, 300), (430, 300), (22, 66), (430, 66)]
        for panel, (x, y) in zip(panels, positions):
            buffer = BytesIO()
            panel.save(buffer, format="JPEG", quality=88, optimize=True)
            buffer.seek(0)
            pdf.drawImage(ImageReader(buffer), x, y, width=390, height=230, preserveAspectRatio=True, mask="auto")
        coordinate_text = "projected target corners in original view: unavailable"
        if quad is not None:
            coordinate_text = "projected target corners in original view: " + json.dumps(np.round(quad, 2).tolist())
        draw_text_block(pdf, [
            f"scale A->B: {row['scale_a_to_b_x']:.3f} | scale B->A: {row['scale_b_to_a_x']:.3f} | "
            f"geometric inliers: {int(row['geometric_inliers_a_to_b'])} | "
            f"median reprojection error: {row['median_reprojection_error_px']:.3f} px",
            coordinate_text,
            f"image A: {Path(row['image_a']).name} | image B: {Path(row['image_b']).name}",
            "Interpretation is a screening label from image geometry, not a final contamination decision.",
        ], 24, 47, size=7, leading=9)
        pdf.showPage()
    pdf.save()


write_review_pdf(candidates, PDF_PATH)
print(f"Wrote {PDF_PATH} ({PDF_PATH.stat().st_size / 1024 / 1024:.1f} MiB)")
'''


DISPLAY_CELL = r'''
# Display a small sample in the notebook after generating the complete PDF.
sample = candidates.head(3)
for number, (_, row) in enumerate(sample.iterrows(), start=1):
    figure = render_candidate(row, number, len(candidates))
    display(figure)
    plt.close(figure)
'''


def markdown_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code_cell(code: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": code.splitlines(True)}


def build_notebook() -> dict:
    cells = [
        markdown_cell(
            "# Same-patient WSI image relationship review\n\n"
            "This notebook reviews the candidate image pairs produced by the explicit same-patient/case audit. "
            "It is intended to generate the PDF linked from the wiki. The review is exploratory visual evidence: "
            "it does not prove patient identity, image duplication, or experimental contamination.\n\n"
            "The notebook includes only candidate pairs from the audit. It does not search every image in the represented groups beyond the pairs already compared by the audit."
        ),
        markdown_cell(
            "## Scope and interpretation\n\n"
            "For each candidate, the PDF shows the two source images, the projected region, a perspective-rectified crop, "
            "and a blended overlay. A scale close to four means that one image is approximately a four-times magnified view "
            "of a region in the other image. The geometric measurements are used to prioritize human review, not to make a final disposition."
        ),
        code_cell(COMMON_IMPORTS),
        code_cell(HELPERS),
        code_cell(PDF_CELL),
        markdown_cell("## Notebook sample\n\nThe complete review is in the generated PDF. The first three candidate pages are displayed here for a quick notebook check."),
        code_cell(DISPLAY_CELL),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    PDF.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(json.dumps(build_notebook(), indent=1), encoding="utf-8")
    print(f"Wrote {NOTEBOOK}")


if __name__ == "__main__":
    main()
