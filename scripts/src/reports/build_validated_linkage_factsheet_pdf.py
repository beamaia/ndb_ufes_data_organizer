#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
VALIDATED_DIR = ROOT / "results/phase0/validated_linkage"
ALIGNMENT_DIR = ROOT / "results/phase0/dataset_alignment_report"
PATCH_DIR = ROOT / "data/ndb_ufes/patch_level/images"
LOGO = ROOT / "docs/assets/branding/labcin-logo.png"
PRIVATE_DIR = VALIDATED_DIR / "private_lab_crosswalks"
IMAGE_CACHE = VALIDATED_DIR / "render_cache"
FIGURE_DIR = VALIDATED_DIR / "figures"

PAGE_W, PAGE_H = A4
LAND_W, LAND_H = landscape(A4)
MARGIN_X = 20 * mm
TOP = PAGE_H - 22 * mm
INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#666666")
BLUE = colors.HexColor("#24285F")
LIGHT_GRAY = colors.HexColor("#F2F2F2")
GRID = colors.HexColor("#D7D7D7")
RED = colors.HexColor("#D04A3A")
GOLD = colors.HexColor("#E2A23A")
STEEL = colors.HexColor("#3E78B2")
UNKNOWN = colors.HexColor("#777777")
PALE_RED = colors.HexColor("#FCE8E5")

LABEL_COLORS = {
    "oscc": RED,
    "with_dysplasia": GOLD,
    "without_dysplasia": STEEL,
    "unknown": UNKNOWN,
}

LABEL_DISPLAY = {
    "oscc": "OSCC",
    "with_dysplasia": "with dysplasia",
    "without_dysplasia": "without dysplasia",
    "broad_leukoplakia_unknown_dysplasia": "broad leukoplakia, dysplasia unknown",
    "unknown": "not available",
}

CONFLICT_ROWS_PER_PAGE = 25
SIMILARITY_ROWS_PER_PAGE = 28
LAB_CROSSWALK_ROWS_PER_PAGE = 11
SIMILARITY_METHOD_PAGES = 2

EVIDENCE_DISPLAY = {
    "validated_exact_public_wsi": "Exact patch-to-WSI link and public WSI match",
    "validated_exact_sab_only": "Exact patch-to-WSI link, SAB-only WSI",
    "validated_exact_with_metadata_conflict": "Exact patch-to-WSI link with WSI context review flag",
    "requires_manual_review": "Requires manual review",
}


def display_wsi_source(value):
    if value == "both":
        return "public NDB-UFES + SAB"
    return str(value)


def short_sab_path(path):
    path = str(path)
    parts = Path(path).parts
    if "SAB" in parts:
        idx = parts.index("SAB")
        short = "/" + "/".join(parts[idx:])
    else:
        short = path
    return short.replace("/", "/<br/>")


def style(name, size=9, leading=None, bold=False, color=INK, space_after=6):
    return ParagraphStyle(
        name=name,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size * 1.32,
        textColor=color,
        spaceAfter=space_after,
    )


STYLES = {
    "body": style("body", 9.6, 13.2),
    "small": style("small", 7.6, 9.5, color=MUTED, space_after=3),
    "h1": style("h1", 19, 24, bold=True, space_after=10),
    "h2": style("h2", 14, 18, bold=True, space_after=8),
    "table": style("table", 7.2, 8.8, space_after=0),
    "caption": style("caption", 7.8, 9.5, color=MUTED, space_after=8),
}


class Numbering:
    def __init__(self):
        self.table = 0
        self.figure = 0

    def table_caption(self, title, legend):
        self.table += 1
        return f"<b>Table {self.table}. {title}.</b> {legend}"

    def figure_caption(self, title, legend):
        self.figure += 1
        return f"<b>Figure {self.figure}. {title}.</b> {legend}"


def para(text, style_name="body"):
    return Paragraph(str(text), STYLES[style_name])


def draw_paragraph(c, text, x, y, width, style_name="body"):
    p = para(text, style_name)
    _w, h = p.wrap(width, 1000)
    p.drawOn(c, x, y - h)
    return y - h - STYLES[style_name].spaceAfter


def cached_preview(path, max_side=900, quality=82):
    path = Path(path)
    if not path.exists():
        return path
    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{path.resolve()}|{max_side}|{quality}".encode("utf-8")).hexdigest()[:24]
    out = IMAGE_CACHE / f"{key}.jpg"
    if out.exists():
        return out
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        img.save(out, "JPEG", quality=quality, optimize=True)
    return out


def draw_image_fit(c, path, x, y, w, h, max_side=900):
    path = Path(path)
    if not path.exists():
        c.setStrokeColor(GRID)
        c.rect(x, y, w, h, stroke=1, fill=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + w / 2, y + h / 2, "image not available")
        return
    preview = cached_preview(path, max_side=max_side)
    with Image.open(preview) as img:
        iw, ih = img.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    c.drawImage(str(preview), dx, dy, dw, dh, preserveAspectRatio=False, mask="auto")


def page_footer(c, page_number, page_width=PAGE_W):
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(page_width - MARGIN_X, 13 * mm, str(page_number))


def bookmark_page(c, name):
    c.bookmarkPage(name)
    c.addOutlineEntry(name.replace("_", " ").title(), name, level=0, closed=False)


def new_page(c, page_number, title=None, subtitle=None, landscape_page=False):
    c.showPage()
    if landscape_page:
        c.setPageSize(landscape(A4))
        width, height = LAND_W, LAND_H
    else:
        c.setPageSize(A4)
        width, height = PAGE_W, PAGE_H
    page_footer(c, page_number, width)
    y = height - 22 * mm
    if title:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 19)
        c.drawString(MARGIN_X, y, title)
        y -= 11 * mm
    if subtitle:
        y = draw_paragraph(c, subtitle, MARGIN_X, y, width - 2 * MARGIN_X, "body")
    return y, width, height


def draw_toc(c, page_number, entries):
    y, _, _ = new_page(c, page_number, "Table of contents", "Click a section name to jump to that part of the PDF.")
    c.setFont("Helvetica", 9.2)
    for title, destination, section_page in entries:
        row_top = y
        c.setFillColor(INK)
        c.drawString(MARGIN_X, y, title)
        c.setFillColor(MUTED)
        c.drawRightString(PAGE_W - MARGIN_X, y, str(section_page))
        c.setStrokeColor(GRID)
        c.line(MARGIN_X, y - 2.2 * mm, PAGE_W - MARGIN_X, y - 2.2 * mm)
        c.linkRect("", destination, (MARGIN_X, y - 3 * mm, PAGE_W - MARGIN_X, row_top + 4 * mm), relative=0, thickness=0)
        y -= 8.5 * mm
    return page_number + 1


def draw_table(c, rows, x, y, widths, font_size=7.2, header=True):
    table_rows = [[para(cell, "table") for cell in row] for row in rows]
    table = Table(table_rows, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY))
        commands.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    table.setStyle(TableStyle(commands))
    _w, h = table.wrap(sum(widths), 1000)
    table.drawOn(c, x, y - h)
    return y - h - 8


def draw_caption(c, numbering_text, x, y, width):
    return draw_paragraph(c, numbering_text, x, y, width, "caption")


def count_rows(series, display=None):
    counts = series.fillna("unknown").astype(str).value_counts()
    total = counts.sum()
    rows = [["Category", "Count", "Percent"]]
    for key, count in counts.items():
        label = display.get(key, key.replace("_", " ")) if display else key.replace("_", " ")
        rows.append([label, f"{int(count):,}", f"{count / total * 100:.1f}%"])
    return rows


def draw_cover(c, summary, privacy):
    bookmark_page(c, "cover")
    c.setFillColor(colors.white)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    if LOGO.exists():
        draw_image_fit(c, LOGO, PAGE_W - MARGIN_X - 25 * mm, TOP - 16 * mm, 25 * mm, 18 * mm, max_side=500)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(MARGIN_X, TOP - 62 * mm, "Validated dataset factsheet")
    c.setFont("Helvetica-Bold", 33)
    c.drawString(MARGIN_X, TOP - 91 * mm, "NDB-UFES and SAB")
    c.drawString(MARGIN_X, TOP - 116 * mm, "patch-to-WSI linkage")
    c.setFont("Helvetica", 21)
    c.drawString(MARGIN_X, TOP - 150 * mm, "2026")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN_X, 30 * mm, f"{summary['patches']:,} patches | {summary['validated_wsi_count']:,} validated WSI units | {privacy} version")
    c.setFillColor(BLUE)
    c.rect(0, 0, PAGE_W, 25 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(PAGE_W / 2, 9 * mm, "Pixel containment, label agreement, WSI inventory, and patch similarity")


def draw_intro(c, page, numbering, summary):
    y, _, _ = new_page(c, page, "Validated linkage summary", "The patch-to-WSI link is built from exact pixel containment inside SAB WSI images.")
    bookmark_page(c, "validated_linkage_summary")
    rows = [
        ["Measure", "Value"],
        ["Patch images linked to validated WSI IDs", f"{summary['patches_with_final_wsi_id']:,} / {summary['patches']:,}"],
        ["Patch images with recovered coordinates", f"{summary['patches_with_coordinates']:,} / {summary['patches']:,}"],
        ["Validated WSI units", f"{summary['validated_wsi_count']:,}"],
        ["Validated WSI units with public NDB-UFES exact WSI match", f"{summary['validated_wsi_with_public_ndb_match']:,}"],
        ["SAB-only recovered WSI units", f"{summary['validated_wsi_sab_only']:,}"],
    ]
    y = draw_caption(c, numbering.table_caption("Validated linkage overview", "All values are computed from validated_patch_wsi_linkage.csv."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    draw_table(c, rows, MARGIN_X, y, [100 * mm, 54 * mm])


def draw_sources(c, page, numbering, privacy):
    y, _, _ = new_page(c, page, "Dataset sources", "NDB-UFES is the public Mendeley dataset. SAB is the private laboratory dataset used as patch provenance evidence.")
    bookmark_page(c, "dataset_sources")
    rows = [
        ["Source", "Description", "Role in this document"],
        ["NDB-UFES", "Public dataset distributed through Mendeley.", "Provides public WSI images, available patch metadata, and previous reconstructed origin IDs."],
        ["SAB", "Private laboratory dataset with WSI folders named benigno, leucoplasia and carcinoma. Patch folders are divided by train/test and carcinoma, dysplasia and no dysplasia labels.", "Provides WSI hash names and the image files used to recover exact patch containment."],
        ["Validated WSI ID", "A public pseudonym assigned to each final WSI unit.", "Canonical WSI identity used for public tables and figures."],
        ["Private crosswalk", "Laboratory-only table linking validated WSI IDs to real SAB names and paths.", "Available only in the lab document version for lab-only review."],
    ]
    y = draw_caption(c, numbering.table_caption("Dataset sources and their role", f"This is the {privacy} version of the document."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, rows, MARGIN_X, y, [30 * mm, 60 * mm, 64 * mm])
    y -= 4
    draw_paragraph(c, "The SAB WSI class folders have September 10, 2021 creation/modification times on disk. The SAB patch folder is dated August 23, 2022.", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "small")


def draw_evidence_and_labels(c, page, numbering, linkage, summary):
    y, _, _ = new_page(c, page, "Linkage evidence and patch labels", "Tables 3, 4, and 5 summarize the validated patch-to-WSI linkage and the patch-label sources.")
    bookmark_page(c, "linkage_evidence_and_patch_labels")
    y = draw_caption(c, numbering.table_caption("Linkage evidence levels", "Rows count patch images according to the evidence used to assign the final WSI ID."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, count_rows(linkage["linkage_evidence_level"], EVIDENCE_DISPLAY), MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])
    y -= 4
    label_display = {
        "agrees": "NDB-UFES patch label and SAB patch label agree",
        "disagrees": "NDB-UFES patch label and SAB patch label differ",
        "patch_label_not_available": "Patch label not available",
    }
    y = draw_caption(c, numbering.table_caption("NDB-UFES patch label versus SAB patch label", "This table answers whether the two patch-level label sources agree."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, count_rows(linkage["patch_label_agreement_status"], label_display), MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])
    y -= 4
    plausibility_display = {
        "plausible": "Patch label is plausible in the validated WSI context",
        "plausible_but_origin_patch_disagreement": "Patch label differs from WSI folder label but remains biologically plausible",
        "impossible_or_high_conflict": "Patch label is not plausible for the WSI folder label and requires expert review",
        "broad_origin_requires_review": "Broad leukoplakia WSI context requires review",
        "unknown_origin_metadata": "WSI context is not available",
    }
    y = draw_caption(c, numbering.table_caption("Patch label versus validated WSI context", "This table answers whether the patch diagnosis is plausible given the validated WSI source label."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, count_rows(linkage["patch_vs_origin_plausibility_status"], plausibility_display), MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])
    y -= 4
    draw_paragraph(c, "The standalone patch labels are not the unresolved issue in this version: NDB-UFES and SAB patch labels agree for all 3,763 patches. The repaired artifact links those standalone patches to validated WSI units and records whether the patch label is plausible in the WSI context.", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "small")


def draw_inventory_summary(c, page, numbering, inventory):
    y, _, _ = new_page(c, page, "Validated WSI inventory", "This page summarizes the final WSI groups created by the pixel-based patch-to-WSI linkage.")
    bookmark_page(c, "validated_wsi_inventory")
    source_rows = [["WSI source", "Number of WSI units"]]
    for source, count in inventory["wsi_source"].value_counts().sort_index().items():
        source_rows.append([display_wsi_source(source), str(int(count))])
    y = draw_caption(c, numbering.table_caption("Validated WSI source summary", "Each row counts final validated WSI IDs, not patches."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, source_rows, MARGIN_X, y, [90 * mm, 34 * mm])
    y -= 7 * mm

    summary_rows = [["Patch count group", "Number of WSI units"]]
    bins = [
        ("1 patch", inventory["n_patches"].eq(1)),
        ("2 to 5 patches", inventory["n_patches"].between(2, 5)),
        ("6 to 10 patches", inventory["n_patches"].between(6, 10)),
        ("11 to 15 patches", inventory["n_patches"].between(11, 15)),
        ("16 to 20 patches", inventory["n_patches"].between(16, 20)),
    ]
    for label, mask in bins:
        summary_rows.append([label, str(int(mask.sum()))])
    y = draw_caption(c, numbering.table_caption("Number of patches per validated WSI", "The complete WSI-level inventory is available in validated_wsi_inventory.csv."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y = draw_table(c, summary_rows, MARGIN_X, y, [90 * mm, 34 * mm])
    y -= 7 * mm
    top = inventory.sort_values("n_patches", ascending=False).head(5)
    examples = ", ".join(f"{row.final_validated_wsi_id} ({int(row.n_patches)} patches)" for row in top.itertuples())
    draw_paragraph(c, f"Largest WSI groups in this version: {examples}. The CSV contains the full list with patch-label counts for every validated WSI.", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "small")


def draw_reconstruction_correction_log(c, page, numbering, linkage):
    conflicts = linkage[linkage["current_metadata_vs_complete_patch_label_status"].eq("disagrees")].copy()
    if conflicts.empty:
        y, width, _ = new_page(c, page, "Superseded reconstruction correction log", "No superseded reconstructed metadata rows required correction.")
        bookmark_page(c, "superseded_reconstruction_correction_log")
        draw_paragraph(c, "The validated linkage artifact does not contain rows where a previous reconstructed metadata label differs from the validated NDB-UFES/SAB patch label.", MARGIN_X, y, width - 2 * MARGIN_X, "body")
        return page + 1
    rows_per_page = CONFLICT_ROWS_PER_PAGE
    for start in range(0, len(conflicts), rows_per_page):
        subtitle = "Rows corrected by the validated linkage artifact. These are not current NDB-UFES-versus-SAB patch-label conflicts."
        if start > 0:
            subtitle = "Continued."
        y, width, _ = new_page(c, page, "Superseded reconstruction correction log", subtitle)
        if start == 0:
            bookmark_page(c, "superseded_reconstruction_correction_log")
        chunk = conflicts.sort_values(["final_validated_wsi_id", "ndb_patch"]).iloc[start:start + rows_per_page]
        rows = [["Patch", "Validated WSI", "Superseded reconstructed label", "Validated NDB/SAB patch label", "Status"]]
        for _, row in chunk.iterrows():
            current_label = LABEL_DISPLAY.get(row.get("current_reconstructed_patch_label", "unknown"), row.get("current_reconstructed_patch_label", "unknown"))
            complete_label = LABEL_DISPLAY.get(row["sab_patch_label"], row["sab_patch_label"])
            rows.append([
                row["ndb_patch"],
                row["final_validated_wsi_id"],
                current_label,
                complete_label,
                "corrected",
            ])
        y = draw_caption(c, numbering.table_caption("Superseded reconstruction corrections", "These rows document where the validated NDB-UFES/SAB patch label replaces a previous reconstructed metadata value."), MARGIN_X, y, width - 2 * MARGIN_X)
        draw_table(c, rows, MARGIN_X, y, [19 * mm, 35 * mm, 40 * mm, 45 * mm, 27 * mm], font_size=6.5)
        page += 1
    c.setPageSize(A4)
    return page


def draw_atlas_intro(c, page, numbering):
    y, _, _ = new_page(c, page, "Validated WSI atlas", "Each atlas page shows one validated WSI, the recovered patch boxes, and patch thumbnails with label status.")
    bookmark_page(c, "validated_wsi_atlas")
    rows = [
        ["Atlas item", "How to read it"],
        ["Patch boxes", "Box color follows the SAB patch label because the SAB parsed patch files cover all 3,763 patches."],
        ["Thumbnail label", "Black text means the NDB-UFES patch label and SAB patch label agree. Red text means those two patch-label sources diverge and both labels are shown."],
        ["Correction log", "Superseded reconstruction corrections are listed only in the appendix. They do not mean the NDB-UFES and SAB patch labels disagree."],
        ["Validated WSI ID", "Public pseudonym used as the canonical WSI identity."],
        ["Previous NDB origin ID", "Historical reconstructed metadata retained for comparison only."],
    ]
    y = draw_caption(c, numbering.table_caption("Atlas reading guide", "The atlas is generated from validated_patch_wsi_linkage.csv and the private crosswalk for image rendering."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    draw_table(c, rows, MARGIN_X, y, [45 * mm, 109 * mm])


def draw_atlas_section(c, page, title, subtitle, bookmark):
    y, _, _ = new_page(c, page, title, subtitle)
    bookmark_page(c, bookmark)
    draw_paragraph(c, "The WSI pages that follow use the same visual template: WSI metadata at the top, patch boxes in the WSI context, and patch thumbnails below.", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "body")


def draw_wsi_page(c, page, numbering, group, privacy):
    page_footer(c, page)
    y = TOP
    wsi_id = group["final_validated_wsi_id"].iloc[0]
    sab_label = group["sab_origin_folder_label_normalized"].iloc[0]
    ndb_origins = "|".join(sorted(set(str(int(float(v))) for v in group["previous_reconstructed_ndb_origin_id"].dropna())))
    public_match = "|".join(sorted(set(str(int(float(v))) for v in group["previous_public_ndb_wsi_match"].dropna())))
    wsi_source = "public NDB-UFES + SAB" if public_match else "SAB-only recovered WSI"
    ndb_origin_labels = sorted(set(str(v) for v in group["current_origin_label_from_sab_origin_exact_match"].dropna() if str(v) != "nan"))
    ndb_origin_label = ", ".join(LABEL_DISPLAY.get(label, label) for label in ndb_origin_labels) if ndb_origin_labels else "not available"
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN_X, y, wsi_id)
    y -= 6 * mm
    c.setFont("Helvetica", 7.6)
    meta_lines = [
        f"Number of patches: {len(group)}",
        f"WSI source: {wsi_source}",
        f"SAB WSI label: {LABEL_DISPLAY.get(sab_label, sab_label)}",
        f"NDB-UFES WSI label: {ndb_origin_label}",
        f"Previous NDB origin ID(s): {ndb_origins or 'not available'}",
    ]
    if public_match:
        meta_lines.append(f"Matched NDB-UFES WSI ID: {public_match}")
    if privacy == "lab":
        meta_lines.append(f"SAB hash: {group['sab_origin_image_id'].iloc[0]}")
    for line in meta_lines:
        c.drawString(MARGIN_X, y, line[:125])
        y -= 3.6 * mm
    y -= 2 * mm
    origin_path = group["sab_origin_path"].dropna().astype(str).iloc[0] if "sab_origin_path" in group and group["sab_origin_path"].notna().any() else ""
    wsi_x, wsi_y, wsi_w, wsi_h = MARGIN_X, y - 73 * mm, PAGE_W - 2 * MARGIN_X, 73 * mm
    draw_image_fit(c, origin_path, wsi_x, wsi_y, wsi_w, wsi_h, max_side=1100)
    if origin_path and Path(origin_path).exists():
        with Image.open(origin_path) as img:
            iw, ih = img.size
        scale = min(wsi_w / iw, wsi_h / ih)
        dw, dh = iw * scale, ih * scale
        dx, dy = wsi_x + (wsi_w - dw) / 2, wsi_y + (wsi_h - dh) / 2
        for _, row in group.iterrows():
            label = row["sab_patch_label"]
            c.setStrokeColor(LABEL_COLORS.get(label, UNKNOWN))
            c.setLineWidth(0.65)
            x1 = dx + float(row["x"]) * scale
            y1 = dy + (ih - (float(row["y"]) + float(row["height"]))) * scale
            c.rect(x1, y1, float(row["width"]) * scale, float(row["height"]) * scale, stroke=1, fill=0)
    y = wsi_y - 6 * mm
    y = draw_caption(c, numbering.figure_caption(f"{wsi_id} WSI context", "Recovered patch boxes are drawn at exact SAB pixel-containment coordinates."), MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    x = MARGIN_X
    for label in ["oscc", "with_dysplasia", "without_dysplasia", "unknown"]:
        c.setFillColor(LABEL_COLORS[label])
        c.rect(x, y, 4 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 5 * mm, y, LABEL_DISPLAY[label])
        x += 37 * mm
    y -= 9 * mm
    cols, rows = 5, 4
    gap = 3 * mm
    cell_w = (PAGE_W - 2 * MARGIN_X - gap * (cols - 1)) / cols
    cell_h = 20 * mm
    label_h = 10 * mm
    row_gap = 3 * mm
    for idx, (_, row) in enumerate(group.sort_values("ndb_patch").head(cols * rows).iterrows()):
        col = idx % cols
        line = idx // cols
        x = MARGIN_X + col * (cell_w + gap)
        label_y = y - line * (cell_h + label_h + row_gap)
        has_patch_label_conflict = row.get("patch_label_agreement_status", "") == "disagrees"
        c.setFillColor(RED if has_patch_label_conflict else INK)
        c.setFont("Helvetica-Bold", 5.8)
        ndb = LABEL_DISPLAY.get(row["ndb_ufes_patch_label"], row["ndb_ufes_patch_label"])
        sab = LABEL_DISPLAY.get(row["sab_patch_label"], row["sab_patch_label"])
        if row["patch_label_agreement_status"] == "agrees":
            c.drawString(x, label_y, f"{row['ndb_patch']} | agree")
            c.setFont("Helvetica", 5.5)
            c.drawString(x, label_y - 3.0 * mm, sab[:34])
        elif row["patch_label_agreement_status"] == "disagrees":
            c.drawString(x, label_y, f"{row['ndb_patch']} | divergent")
            c.setFont("Helvetica", 5.3)
            c.drawString(x, label_y - 3.0 * mm, f"NDB patch: {ndb}"[:34])
            c.drawString(x, label_y - 6.0 * mm, f"SAB patch: {sab}"[:34])
        else:
            c.drawString(x, label_y, f"{row['ndb_patch']} | label unavailable")
            c.setFont("Helvetica", 5.3)
            c.drawString(x, label_y - 3.0 * mm, f"SAB patch: {sab}"[:34])
        yy = label_y - label_h - cell_h
        draw_image_fit(c, PATCH_DIR / f"{row['ndb_patch']}.png", x, yy, cell_w, cell_h, max_side=240)


def save_histogram(data, column, title, xlabel, path, bins=30):
    values = pd.to_numeric(data[column], errors="coerce").dropna()
    plt.figure(figsize=(6.2, 3.4))
    plt.hist(values, bins=bins, color="#3E78B2", edgecolor="white")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Number of same-WSI patch pairs")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_pair_relation_chart(data, path):
    counts = data["pair_relation"].fillna("unknown").astype(str).value_counts().sort_values()
    labels = [label.replace("_", " ") for label in counts.index]
    plt.figure(figsize=(6.2, 3.4))
    plt.barh(labels, counts.values, color="#E2A23A")
    plt.xlabel("Number of same-WSI patch pairs")
    plt.title("Patch-pair interpretation categories")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def similarity_figure_paths(similarity):
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "iou": FIGURE_DIR / "same_wsi_iou_distribution.png",
        "visual": FIGURE_DIR / "same_wsi_visual_similarity_distribution.png",
        "lab": FIGURE_DIR / "same_wsi_lab_delta_distribution.png",
        "relation": FIGURE_DIR / "same_wsi_pair_relation_counts.png",
    }
    save_histogram(similarity, "iou", "Spatial overlap between same-WSI patches", "Intersection over union", paths["iou"])
    save_histogram(similarity, "visual_fingerprint_similarity", "Visual fingerprint similarity", "Cosine similarity", paths["visual"])
    save_histogram(similarity, "lab_mean_delta", "Mean LAB color difference", "LAB mean delta", paths["lab"])
    save_pair_relation_chart(similarity, paths["relation"])
    return paths


def draw_similarity_methods(c, page, numbering, similarity):
    paths = similarity_figure_paths(similarity)
    y, width, _ = new_page(c, page, "Similarity methods and distributions", "This section defines the same-WSI patch-pair measurements used in the appendix.")
    bookmark_page(c, "similarity_methods_and_distributions")
    rows = [
        ["Measure", "Definition", "How to read it"],
        ["IoU", "Intersection over union between two recovered coordinate boxes in the same validated WSI.", "Higher values mean the two patch boxes spatially overlap more."],
        ["Visual fingerprint similarity", "Each patch is resized to 32 x 32 pixels. RGB and LAB color vectors are concatenated, mean-centered, L2-normalized, and compared using cosine similarity.", "Higher values mean the patches have more similar color and texture fingerprints. It is not a diagnosis score."],
        ["LAB mean delta", "Euclidean distance between the mean LAB color values of the two patch images.", "Lower values mean the two patches have more similar average stain/color appearance."],
        ["Pair relation", "A readable category derived from spatial overlap, visual fingerprint similarity, and LAB color difference.", "Used to separate overlapping patches from visually similar but spatially separate patches."],
    ]
    y = draw_caption(c, numbering.table_caption("Same-WSI patch similarity measures", "The methods compare patches inside the same validated WSI only."), MARGIN_X, y, width - 2 * MARGIN_X)
    y = draw_table(c, rows, MARGIN_X, y, [33 * mm, 79 * mm, 54 * mm], font_size=6.7)
    y -= 2 * mm
    draw_image_fit(c, paths["iou"], MARGIN_X, y - 58 * mm, 79 * mm, 48 * mm, max_side=900)
    draw_image_fit(c, paths["visual"], MARGIN_X + 87 * mm, y - 58 * mm, 79 * mm, 48 * mm, max_side=900)
    y -= 62 * mm
    y = draw_caption(c, numbering.figure_caption("Same-WSI spatial and visual similarity distributions", "The histograms summarize all patch pairs assigned to the same validated WSI."), MARGIN_X, y, width - 2 * MARGIN_X)

    page += 1
    y, width, _ = new_page(c, page, "Similarity methods and distributions", "Continued.")
    draw_image_fit(c, paths["lab"], MARGIN_X, y - 74 * mm, 79 * mm, 55 * mm, max_side=900)
    draw_image_fit(c, paths["relation"], MARGIN_X + 87 * mm, y - 74 * mm, 79 * mm, 55 * mm, max_side=900)
    y -= 78 * mm
    y = draw_caption(c, numbering.figure_caption("Same-WSI color and interpretation distributions", "LAB delta describes color difference. Pair-relation counts summarize the final readable categories."), MARGIN_X, y, width - 2 * MARGIN_X)
    draw_paragraph(c, "These figures are descriptive. They help identify whether same-WSI patches are overlapping, visually similar but spatially separate, or visually different enough to add distinct information to the dataset.", MARGIN_X, y, width - 2 * MARGIN_X, "small")
    return page + 1


def draw_similarity_appendix(c, page, numbering, similarity):
    rows_per_page = SIMILARITY_ROWS_PER_PAGE
    data = similarity.sort_values(["final_validated_wsi_id", "patch_a", "patch_b"]).reset_index(drop=True)
    for start in range(0, len(data), rows_per_page):
        y, width, _height = new_page(c, page, "Same-WSI patch-pair similarity", "Full pairwise table for patches inside the same validated WSI.")
        if start == 0:
            bookmark_page(c, "same_wsi_patch_pair_similarity")
        chunk = data.iloc[start:start + rows_per_page]
        rows = [["WSI", "Patch A", "Patch B", "IoU", "Visual sim.", "LAB delta", "Interpretation"]]
        for _, row in chunk.iterrows():
            rows.append([
                row["final_validated_wsi_id"],
                row["patch_a"],
                row["patch_b"],
                f"{row['iou']:.3f}" if pd.notna(row["iou"]) else "",
                f"{row['visual_fingerprint_similarity']:.3f}" if pd.notna(row["visual_fingerprint_similarity"]) else "",
                f"{row['lab_mean_delta']:.1f}" if pd.notna(row["lab_mean_delta"]) else "",
                str(row["pair_relation"]).replace("_", " "),
            ])
        y = draw_caption(c, numbering.table_caption("Same-WSI patch-pair similarity", "IoU measures spatial overlap. Visual similarity and LAB delta describe patch appearance."), MARGIN_X, y, width - 2 * MARGIN_X)
        draw_table(c, rows, MARGIN_X, y, [31 * mm, 18 * mm, 18 * mm, 14 * mm, 18 * mm, 17 * mm, 50 * mm], font_size=6.4)
        page += 1
    c.setPageSize(A4)
    return page


def draw_lab_crosswalk(c, page, numbering, crosswalk):
    y, width, _ = new_page(c, page, "Laboratory crosswalk", "This lab-only appendix contains original SAB identifiers and must not be included in the public version.")
    bookmark_page(c, "laboratory_crosswalk")
    rows_per_page = LAB_CROSSWALK_ROWS_PER_PAGE
    data = crosswalk.sort_values("public_wsi_pseudonym").reset_index(drop=True)
    for start in range(0, len(data), rows_per_page):
        if start > 0:
            y, width, _ = new_page(c, page, "Laboratory crosswalk", "Continued.")
        rows = [["Public WSI pseudonym", "SAB hash name", "SAB folder", "SAB file path"]]
        for _, row in data.iloc[start:start + rows_per_page].iterrows():
            rows.append([
                row["public_wsi_pseudonym"],
                row["sab_origin_image_id"],
                row["sab_origin_folder"],
                short_sab_path(row["sab_origin_path"]),
            ])
        y = draw_caption(c, numbering.table_caption("Private WSI crosswalk", "Original SAB names are available only in the laboratory document version for lab-only review."), MARGIN_X, y, width - 2 * MARGIN_X)
        draw_table(c, rows, MARGIN_X, y, [31 * mm, 53 * mm, 25 * mm, 57 * mm], font_size=5.8)
        page += 1
    c.setPageSize(A4)
    return page


def build_pdf(privacy):
    linkage = pd.read_csv(VALIDATED_DIR / "validated_patch_wsi_linkage.csv")
    private_linkage = pd.read_csv(PRIVATE_DIR / "private_validated_patch_wsi_linkage.csv")
    inventory = pd.read_csv(VALIDATED_DIR / "validated_wsi_inventory.csv")
    similarity = pd.read_csv(VALIDATED_DIR / "validated_wsi_patch_similarity.csv")
    crosswalk = pd.read_csv(PRIVATE_DIR / "private_validated_wsi_crosswalk.csv")
    summary = json.loads((VALIDATED_DIR / "validated_linkage_summary.json").read_text())
    out = VALIDATED_DIR / f"validated_patch_wsi_linkage_factsheet_{privacy}.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    numbering = Numbering()
    correction_pages = max(1, (int(linkage["current_metadata_vs_complete_patch_label_status"].eq("disagrees").sum()) + CONFLICT_ROWS_PER_PAGE - 1) // CONFLICT_ROWS_PER_PAGE)
    public_wsi_ids = set(inventory[inventory["wsi_source"].eq("both")]["final_validated_wsi_id"])
    both_groups = [(wsi_id, group) for wsi_id, group in private_linkage.groupby("final_validated_wsi_id", sort=True) if wsi_id in public_wsi_ids]
    sab_only_groups = [(wsi_id, group) for wsi_id, group in private_linkage.groupby("final_validated_wsi_id", sort=True) if wsi_id not in public_wsi_ids]
    similarity_pages = max(1, (len(similarity) + SIMILARITY_ROWS_PER_PAGE - 1) // SIMILARITY_ROWS_PER_PAGE)
    similarity_methods_page = 10 + len(both_groups) + len(sab_only_groups)
    similarity_appendix_page = similarity_methods_page + SIMILARITY_METHOD_PAGES
    correction_log_page = similarity_appendix_page + similarity_pages
    toc_entries = [
        ("Validated linkage summary", "validated_linkage_summary", 3),
        ("Dataset sources", "dataset_sources", 4),
        ("Linkage evidence and patch labels", "linkage_evidence_and_patch_labels", 5),
        ("Validated WSI inventory", "validated_wsi_inventory", 6),
        ("Validated WSI atlas", "validated_wsi_atlas", 7),
        ("Atlas: public NDB-UFES + SAB WSI", "atlas_public_ndb_ufes_sab", 8),
        ("Atlas: SAB-only recovered WSI", "atlas_sab_only_recovered", 9 + len(both_groups)),
        ("Similarity methods and distributions", "similarity_methods_and_distributions", similarity_methods_page),
        ("Same-WSI patch-pair similarity", "same_wsi_patch_pair_similarity", similarity_appendix_page),
        ("Superseded reconstruction correction log", "superseded_reconstruction_correction_log", correction_log_page),
    ]
    if privacy == "lab":
        toc_entries.append(("Laboratory crosswalk", "laboratory_crosswalk", correction_log_page + correction_pages))
    draw_cover(c, summary, privacy)
    page = draw_toc(c, 2, toc_entries)
    draw_intro(c, page, numbering, summary); page += 1
    draw_sources(c, page, numbering, privacy); page += 1
    draw_evidence_and_labels(c, page, numbering, linkage, summary); page += 1
    draw_inventory_summary(c, page, numbering, inventory); page += 1
    draw_atlas_intro(c, page, numbering); page += 1
    draw_atlas_section(c, page, "Atlas: public NDB-UFES + SAB WSI", "These WSI groups have an exact SAB WSI image and an exact public NDB-UFES WSI image match.", "atlas_public_ndb_ufes_sab"); page += 1
    for _wsi_id, group in both_groups:
        c.showPage()
        c.setPageSize(A4)
        draw_wsi_page(c, page, numbering, group, privacy)
        page += 1
    draw_atlas_section(c, page, "Atlas: SAB-only recovered WSI", "These WSI groups have exact SAB patch containment but no exact public NDB-UFES WSI file match.", "atlas_sab_only_recovered"); page += 1
    for _wsi_id, group in sab_only_groups:
        c.showPage()
        c.setPageSize(A4)
        draw_wsi_page(c, page, numbering, group, privacy)
        page += 1
    page = draw_similarity_methods(c, page, numbering, similarity)
    page = draw_similarity_appendix(c, page, numbering, similarity)
    page = draw_reconstruction_correction_log(c, page, numbering, linkage)
    if privacy == "lab":
        page = draw_lab_crosswalk(c, page, numbering, crosswalk)
    c.save()
    return out


def main():
    parser = argparse.ArgumentParser(description="Build validated patch-to-WSI linkage factsheet PDFs.")
    parser.add_argument("--privacy", choices=["public", "lab", "both"], default="both")
    args = parser.parse_args()
    outputs = []
    for privacy in (["public", "lab"] if args.privacy == "both" else [args.privacy]):
        outputs.append(build_pdf(privacy))
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
