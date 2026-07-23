import json
import math
import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase.pdfmetrics import stringWidth


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/phase0/dataset_alignment_report"
MASTER = OUT / "source_alignment_master.csv"
COORDS = OUT / "patch_coordinate_status.csv"
ORIGINS = OUT / "origin_patch_composition.csv"
PAIRS = OUT / "patch_spatial_feature_similarity.csv"
SUMMARY = OUT / "dataset_alignment_report_summary.json"
PRIVATE_CROSSWALK = OUT / "private_lab_crosswalks/origin_validation_private_crosswalk.csv"
ORIGIN_INVENTORY = ROOT / "results/phase0/recovery_validation/origin_image_inventory.csv"
LOGO = ROOT / "docs/assets/branding/labcin-logo.png"
RAW_PATCH_DIR = ROOT / "data/ndb_ufes/patch_level/images"
OUTPUT_PDF = OUT / "ndb_ufes_sab_dataset_factsheet_full.pdf"
IMAGE_CACHE = OUT / "private_lab_crosswalks/render_cache"

PAGE_W, PAGE_H = A4
MARGIN_X = 22 * mm
TOP = PAGE_H - 24 * mm
BOTTOM = 22 * mm
INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#666666")
BLUE = colors.HexColor("#24285F")
LIGHT_BLUE = colors.HexColor("#DFF5FA")
LIGHT_GRAY = colors.HexColor("#F2F2F2")
GRID = colors.HexColor("#D7D7D7")
RED = colors.HexColor("#D04A3A")
GOLD = colors.HexColor("#E2A23A")
STEEL = colors.HexColor("#3E78B2")
UNKNOWN = colors.HexColor("#777777")

LABEL_COLORS = {
    "oscc": RED,
    "with_dysplasia": GOLD,
    "without_dysplasia": STEEL,
    "unknown": UNKNOWN,
    "missing_from_accepted_metadata": UNKNOWN,
}

LABEL_DISPLAY = {
    "oscc": "OSCC",
    "with_dysplasia": "with dysplasia",
    "without_dysplasia": "without dysplasia",
    "unknown": "unknown",
    "missing_from_accepted_metadata": "missing from accepted metadata",
}

STATUS_DISPLAY = {
    "source_convergent": "Sources converge",
    "source_disagreement": "Source labels differ",
    "requires_manual_review": "Needs manual review",
    "biologically_implausible_or_high_conflict": "High biological/source conflict",
    "metadata_insufficient": "Metadata incomplete",
}

PAIR_DISPLAY = {
    "feature_similar_and_spatially_overlapping": "visually similar and spatially overlapping",
    "feature_similar_without_spatial_overlap": "visually similar but spatially separate",
    "spatially_overlapping": "spatially overlapping",
    "spatially_distinct": "spatially separate",
}


def pstyle(name, size=10, leading=None, bold=False, italic=False, color=INK, space_after=7):
    return ParagraphStyle(
        name=name,
        fontName=("Helvetica-BoldOblique" if bold and italic else "Helvetica-Bold" if bold else "Helvetica-Oblique" if italic else "Helvetica"),
        fontSize=size,
        leading=leading or size * 1.35,
        textColor=color,
        spaceAfter=space_after,
    )


STYLES = {
    "body": pstyle("body", 10.2, 14.2),
    "small": pstyle("small", 8, 10.5, color=MUTED, space_after=4),
    "h1": pstyle("h1", 20, 25, bold=True, space_after=12),
    "h2": pstyle("h2", 16, 20, bold=True, space_after=9),
    "h3": pstyle("h3", 12, 15, bold=True, space_after=6),
    "table": pstyle("table", 8.2, 10.2, space_after=0),
    "table_small": pstyle("table_small", 7.2, 8.6, space_after=0),
    "footer": pstyle("footer", 7.2, 8.8, italic=True, color=MUTED, space_after=0),
}


def para(text, style="body"):
    return Paragraph(str(text), STYLES[style])


def draw_paragraph(c, text, x, y, width, style="body"):
    p = para(text, style)
    _w, h = p.wrap(width, 1000)
    p.drawOn(c, x, y - h)
    return y - h - STYLES[style].spaceAfter


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


def draw_image_fit(c, path, x, y, w, h, preserve=True, max_side=900):
    path = Path(path)
    if not path.exists():
        c.setFillColor(MUTED)
        c.rect(x, y, w, h, stroke=1, fill=0)
        c.drawCentredString(x + w / 2, y + h / 2, "image not available")
        return
    preview = cached_preview(path, max_side=max_side)
    with Image.open(preview) as img:
        iw, ih = img.size
    if preserve:
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    else:
        dx, dy, dw, dh = x, y, w, h
    c.drawImage(str(preview), dx, dy, dw, dh, preserveAspectRatio=False, mask="auto")


def draw_page_frame(c, page_label):
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawRightString(PAGE_W - MARGIN_X, 14 * mm, page_label)


def new_page(c, title=None, subtitle=None, page_label="", advance=True):
    if advance:
        c.showPage()
    draw_page_frame(c, page_label)
    y = TOP
    if title:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(MARGIN_X, y, title)
        y -= 12 * mm
    if subtitle:
        y = draw_paragraph(c, subtitle, MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "body")
    return y


def make_table(data, widths, header=True, font_size=8.2, row_fill=None):
    rows = []
    for row in data:
        rows.append([para(cell, "table" if font_size >= 8 else "table_small") for cell in row])
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    if row_fill:
        for idx, fill in row_fill.items():
            style.append(("BACKGROUND", (0, idx), (-1, idx), fill))
    t.setStyle(TableStyle(style))
    return t


def draw_table(c, data, x, y, widths, available_height=500, header=True, font_size=8.2):
    t = make_table(data, widths, header=header, font_size=font_size)
    _w, h = t.wrap(sum(widths), available_height)
    t.drawOn(c, x, y - h)
    return y - h - 10


def counts_rows(series, display=None):
    counts = series.fillna("unknown").astype(str).value_counts()
    total = counts.sum()
    rows = [["Category", "Count", "Percent"]]
    for key, value in counts.items():
        label = display.get(key, key.replace("_", " ")) if display else key.replace("_", " ")
        rows.append([label, f"{int(value):,}", f"{value / total * 100:.1f}%"])
    return rows


def draw_cover(c, summary, origins):
    c.setFillColor(colors.white)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    if LOGO.exists():
        draw_image_fit(c, LOGO, PAGE_W - MARGIN_X - 25 * mm, TOP - 16 * mm, 25 * mm, 18 * mm, max_side=500)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(MARGIN_X, TOP - 66 * mm, "Data factsheet")
    c.setFont("Helvetica-Bold", 34)
    c.drawString(MARGIN_X, TOP - 94 * mm, "NDB-UFES and SAB")
    c.drawString(MARGIN_X, TOP - 119 * mm, "dataset alignment")
    c.setFont("Helvetica", 22)
    c.drawString(MARGIN_X, TOP - 154 * mm, "2026")
    c.setFillColor(BLUE)
    c.rect(0, 0, PAGE_W, 25 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 9 * mm, "Patch provenance, label convergence, and recovered WSI coordinates")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN_X, 29 * mm, f"{summary.get('source_alignment_rows', 3763):,} patches | {origins['origin_validation_id'].nunique()} SAB origin groups | Public-private source alignment")
    c.showPage()


def draw_intro(c, summary, origins):
    draw_page_frame(c, "Data factsheet: NDB-UFES/SAB alignment Page 2")
    y = TOP
    y = draw_paragraph(c, "Introduction", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "h1")
    for text in [
        "This factsheet compares the public NDB-UFES dataset distributed through Mendeley with the private SAB laboratory dataset stored in laboratory computers and university cloud folders. The SAB files are treated as trusted provenance evidence for this validation because they were used in previous training pipelines and contain the origin-image hash names from which the patch files were generated.",
        "The goal is to validate whether patch images, labels, and origin-image relationships align across dataset versions, and to identify patches or origin images that require manual review before leakage-safe experiments.",
        "For privacy, real SAB origin filenames are not printed in the public-facing tables. This PDF uses origin_validation_id pseudonyms. The private crosswalk remains available for lab-only review.",
    ]:
        y = draw_paragraph(c, text, MARGIN_X, y, PAGE_W - 2 * MARGIN_X)
    y -= 6
    rows = [
        ["Validation item", "Result"],
        ["NDB-UFES public WSI images validated", "242"],
        ["NDB-UFES patch images validated", "3,763"],
        ["SAB WSI groups represented by the patch split", f"{origins['origin_validation_id'].nunique():,}"],
        ["Patch images exact-matched between NDB-UFES and SAB", "3,763 / 3,763"],
        ["NDB-UFES WSI images exact-matched to SAB WSI images", "222 / 242"],
    ]
    draw_table(c, rows, MARGIN_X, y, [112 * mm, 42 * mm])


def draw_source_definitions(c):
    y = new_page(c, "Dataset sources", "Definitions used throughout this validation.", "Data factsheet: NDB-UFES/SAB alignment Page 3")
    rows = [
        ["Term", "Meaning", "Role in this validation"],
        ["NDB-UFES", "Public dataset distributed through Mendeley.", "Public WSI images, patch images, accepted metadata, patient/lesion fields, and task labels used in the current organized dataset."],
        ["SAB", "Private laboratory dataset stored in laboratory computers and university cloud folders.", "WSI folders named benigno, leucoplasia, and carcinoma; patch train/test folders; origin hash names that link images to the local SAB system."],
        ["Accepted NDB-UFES metadata", "The current CSV treated as the organized public metadata table.", "Used when available, but not assumed to contain every patch-origin relationship found in SAB."],
        ["Origin validation ID", "Privacy-preserving pseudonym generated for each SAB origin image.", "Used in this PDF instead of the SAB hash filename; private crosswalk links it back to SAB for lab-only review."],
    ]
    y = draw_table(c, rows, MARGIN_X, y, [37 * mm, 49 * mm, 68 * mm], font_size=7.2)
    y -= 8
    draw_paragraph(c, "Observed file provenance: SAB WSI class folders have September 10, 2021 modification times on this disk. The SAB patch split contains 3,763 PNG files. These timestamps describe file provenance, not annotation date.", MARGIN_X, y, PAGE_W - 2 * MARGIN_X, "small")


def draw_key_findings(c, master, origins, pairs, origin_inventory):
    y = new_page(c, "Key validation findings", "Counts are validation evidence, not clinical truth claims.", "Data factsheet: NDB-UFES/SAB alignment Page 4")
    patchless = int((origin_inventory["accepted_patch_count"] == 0).sum()) if origin_inventory is not None else 34
    rows = [
        ["Question", "Result", "Interpretation"],
        ["Patch identity", "3,763 / 3,763 NDB-UFES patch files exact-match SAB split patch files.", "The patch image set is shared between the sources."],
        ["WSI identity", "222 / 242 NDB-UFES WSI images exact-match a SAB WSI image.", "The WSI/origin set diverges across sources."],
        ["SAB WSI groups with patches", f"{origins['origin_validation_id'].nunique()} origin_validation_id groups.", "The SAB split links patches to more origin groups than the public WSI set exact-matches."],
        ["NDB-UFES public WSI without accepted patches", str(patchless), "These public origin images currently do not contribute accepted patch rows."],
        ["Origins with >1 best available patch label", str(int(origins["has_multiple_best_available_patch_labels"].sum())), "Uses accepted NDB-UFES labels when present, otherwise SAB split labels."],
        ["Patch pairs spatially compared", f"{len(pairs):,}", "Comparisons are within the same SAB origin only."],
    ]
    draw_table(c, rows, MARGIN_X, y, [43 * mm, 50 * mm, 61 * mm], font_size=7.2)


def draw_flags(c):
    y = new_page(c, "How to read the validation flags", "The validation separates source convergence from biological or logical plausibility.", "Data factsheet: NDB-UFES/SAB alignment Page 5")
    rows = [
        ["Reader-facing flag", "Meaning", "Suggested action"],
        ["Sources converge", "Available labels from NDB-UFES and SAB do not show a relevant disagreement.", "Usually low priority."],
        ["Source labels differ", "The accepted NDB-UFES label and the SAB split/folder label differ at patch or origin level.", "Review before using for model training."],
        ["Needs manual review", "A broad SAB folder, missing current metadata, or ambiguous source context prevents a clean decision.", "Candidate-only until reviewed."],
        ["High biological/source conflict", "A non-OSCC origin context is linked to an OSCC/carcinoma patch label.", "Do not silently include without manual adjudication."],
        ["Metadata incomplete", "The exact image exists, but the accepted public metadata does not fully describe it.", "Recoverable evidence, but not final metadata."],
    ]
    y = draw_table(c, rows, MARGIN_X, y, [44 * mm, 65 * mm, 45 * mm], font_size=7.2)
    y -= 10
    rows2 = [
        ["Label term", "Definition"],
        ["NDB-UFES accepted metadata label", "Patch diagnosis found in the current public organized metadata CSV."],
        ["SAB patch split label", "Patch class inferred from the SAB train/test class folder after exact image matching."],
        ["Best available patch label", "NDB-UFES accepted metadata label when present; otherwise SAB patch split label."],
        ["SAB origin folder label", "Origin-level context from the private SAB WSI folder name; leucoplasia is broad and does not specify dysplasia."],
    ]
    draw_table(c, rows2, MARGIN_X, y, [58 * mm, 96 * mm], font_size=7.2)


def draw_counts(c, master):
    y = new_page(c, "Source convergence counts", "Tables are used instead of unlabeled charts so the categories can be read directly.", "Data factsheet: NDB-UFES/SAB alignment Page 6")
    rows = counts_rows(master["dataset_use_status"], STATUS_DISPLAY)
    y = draw_table(c, rows, MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])
    y -= 12
    rows = counts_rows(master["patch_csv_vs_sab_split_status"], {
        "agrees": "accepted NDB-UFES and SAB split agree",
        "disagrees": "accepted NDB-UFES and SAB split differ",
        "missing_current_patch_metadata": "missing from accepted NDB-UFES metadata",
    })
    draw_table(c, rows, MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])


def draw_label_agreement(c, master):
    y = new_page(c, "Patch label agreement", "Rows are labels from accepted NDB-UFES metadata. Columns are labels from the SAB patch split.", "Data factsheet: NDB-UFES/SAB alignment Page 7")
    crosstab = pd.crosstab(master["ndb_ufes_accepted_patch_label"], master["sab_patch_split_label"])
    rows = [["NDB-UFES accepted metadata", "SAB without dysplasia", "SAB with dysplasia", "SAB OSCC"]]
    for index in ["missing_from_accepted_metadata", "oscc", "with_dysplasia", "without_dysplasia"]:
        row = crosstab.loc[index] if index in crosstab.index else pd.Series(dtype=int)
        rows.append([
            LABEL_DISPLAY.get(index, index),
            str(int(row.get("without_dysplasia", 0))),
            str(int(row.get("with_dysplasia", 0))),
            str(int(row.get("oscc", 0))),
        ])
    y = draw_table(c, rows, MARGIN_X, y, [58 * mm, 32 * mm, 32 * mm, 32 * mm])
    y -= 10
    for text in [
        "Cells away from the diagonal indicate that the same patch image carries different class information depending on which source is used.",
        "The row 'missing from accepted metadata' means the patch is absent from the accepted NDB-UFES metadata table but still has a SAB split label.",
        "This table should not be read as a pathologist disagreement matrix. It is a source-alignment matrix between dataset versions.",
    ]:
        y = draw_paragraph(c, text, MARGIN_X, y, PAGE_W - 2 * MARGIN_X)


def draw_spatial(c, pairs):
    y = new_page(c, "Patch spatial and visual relationships", "Pairwise comparisons are computed only within the same SAB origin image.", "Data factsheet: NDB-UFES/SAB alignment Page 8")
    rows = counts_rows(pairs["pair_relation"], PAIR_DISPLAY)
    y = draw_table(c, rows, MARGIN_X, y, [90 * mm, 32 * mm, 32 * mm])
    y -= 10
    for text in [
        "Spatial relationship comes from recovered pixel coordinates: two 512 x 512 patches either overlap on the same SAB origin image or they do not.",
        "Visual relationship uses a conservative patch fingerprint. Patches are called visually similar only when their downsampled color/structure fingerprint is high and their mean LAB color difference is low.",
        "The category 'visually similar but spatially separate' indicates repeated or similar morphology within the same WSI, not duplicated tissue. 'Visually similar and spatially overlapping' indicates near-duplicate or shared-tissue evidence.",
    ]:
        y = draw_paragraph(c, text, MARGIN_X, y, PAGE_W - 2 * MARGIN_X)


def draw_limitations(c):
    y = new_page(c, "Use and limitations", "This validation prepares evidence for manual review and leakage-safe experiments.", "Data factsheet: NDB-UFES/SAB alignment Page 9")
    rows = [
        ["Rule", "Meaning"],
        ["Do not publish private linkage keys", "Use origin_validation_id publicly. Keep the private crosswalk inside the lab."],
        ["Do not treat flags as final clinical judgment", "Flags identify source inconsistencies and plausibility concerns; they do not replace blind pathology review."],
        ["Recovered coordinates are evidence", "Coordinates were recovered by exact pixel matching between patches and SAB WSI images."],
        ["Suspicious patches are candidates for exclusion or adjudication", "Experiments can compare all linked data versus stricter reviewed subsets."],
        ["Patch labels can be patch-specific", "A patch label may differ from a broad origin context, especially for leukoplakia; OSCC under non-OSCC origin context is treated as high conflict."],
    ]
    draw_table(c, rows, MARGIN_X, y, [55 * mm, 99 * mm], font_size=7.5)


def draw_atlas_intro(c, start_page):
    y = new_page(c, "Origin atlas", "The following pages show one SAB origin per page. Each page includes the SAB WSI with recovered patch boxes and the linked patch thumbnails.", f"Data factsheet: NDB-UFES/SAB alignment Page {start_page}")
    for text in [
        "Every page is fixed A4 portrait so the PDF has consistent page boundaries. Origin identifiers are pseudonymous origin_validation_id values.",
        "Patch box color follows the best available patch label: red = OSCC, gold = with dysplasia, blue = without dysplasia, gray = unknown or missing.",
        "The atlas is part of the final PDF product because it documents where patches exist in the WSI context and which patch labels are attached to each WSI group.",
    ]:
        y = draw_paragraph(c, text, MARGIN_X, y, PAGE_W - 2 * MARGIN_X)


def draw_origin_page(c, origin_id, group, page_number):
    draw_page_frame(c, f"Data factsheet: NDB-UFES/SAB alignment Page {page_number}")
    y = TOP
    folder = group["sab_origin_folder"].iloc[0]
    folder_label = LABEL_DISPLAY.get(str(group["sab_origin_folder_label_normalized"].iloc[0]), str(group["sab_origin_folder_label_normalized"].iloc[0]))
    match = group["ndb_origin_id_from_sab_origin_exact_match"].iloc[0]
    match = "not matched" if pd.isna(match) else str(match)
    best_counts = group["best_available_patch_label"].value_counts().to_dict()
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(MARGIN_X, y, str(origin_id))
    y -= 8 * mm
    c.setFont("Helvetica", 8.3)
    c.drawString(MARGIN_X, y, f"SAB WSI folder: {folder} ({folder_label}) | NDB-UFES exact WSI match: {match} | patches: {len(group)}")
    y -= 5 * mm
    label_text = ", ".join(f"{LABEL_DISPLAY.get(k, k)}: {v}" for k, v in best_counts.items())
    c.drawString(MARGIN_X, y, f"Best available patch labels: {label_text}")
    y -= 8 * mm
    origin_path = group["sab_origin_path"].dropna().astype(str).iloc[0] if group["sab_origin_path"].notna().any() else ""
    wsi_x, wsi_y, wsi_w, wsi_h = MARGIN_X, y - 88 * mm, PAGE_W - 2 * MARGIN_X, 88 * mm
    c.setStrokeColor(GRID)
    c.rect(wsi_x, wsi_y, wsi_w, wsi_h, stroke=1, fill=0)
    draw_image_fit(c, origin_path, wsi_x, wsi_y, wsi_w, wsi_h, max_side=1100)
    if Path(origin_path).exists():
        with Image.open(origin_path) as img:
            iw, ih = img.size
        scale = min(wsi_w / iw, wsi_h / ih)
        dw, dh = iw * scale, ih * scale
        dx, dy = wsi_x + (wsi_w - dw) / 2, wsi_y + (wsi_h - dh) / 2
        for _, row in group.iterrows():
            if row["coordinate_status"] != "recovered_from_sab_exact_or_near_pixel_match":
                continue
            label = str(row["best_available_patch_label"])
            c.setStrokeColor(LABEL_COLORS.get(label, UNKNOWN))
            c.setLineWidth(0.7)
            x1 = dx + float(row["recovered_x"]) * scale
            y1 = dy + (ih - float(row["recovered_y2"])) * scale
            bw = float(row["recovered_width"]) * scale
            bh = float(row["recovered_height"]) * scale
            c.rect(x1, y1, bw, bh, stroke=1, fill=0)
            c.setFillColor(INK)
            c.setFont("Helvetica", 4.8)
            c.drawString(x1, y1 + bh + 1, row["ndb_patch"])
    legend_y = wsi_y - 6 * mm
    x = MARGIN_X
    for label in ["oscc", "with_dysplasia", "without_dysplasia", "unknown"]:
        c.setFillColor(LABEL_COLORS[label])
        c.rect(x, legend_y, 4 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 7)
        c.drawString(x + 5 * mm, legend_y, LABEL_DISPLAY[label])
        x += 38 * mm
    patch_y_top = legend_y - 9 * mm
    cols, rows = 5, 4
    gap = 3 * mm
    cell_w = (PAGE_W - 2 * MARGIN_X - gap * (cols - 1)) / cols
    cell_h = 28 * mm
    for idx, (_, row) in enumerate(group.head(cols * rows).iterrows()):
        col = idx % cols
        line = idx // cols
        x = MARGIN_X + col * (cell_w + gap)
        y = patch_y_top - line * (cell_h + 7 * mm) - cell_h
        patch_path = RAW_PATCH_DIR / f"{row['ndb_patch']}.png"
        draw_image_fit(c, patch_path, x, y, cell_w, cell_h, max_side=240)
        c.setFillColor(INK)
        c.setFont("Helvetica", 5.8)
        label = LABEL_DISPLAY.get(str(row["best_available_patch_label"]), str(row["best_available_patch_label"]))
        c.drawString(x, y - 4 * mm, f"{row['ndb_patch']} | {label}")


def draw_patchless_pages(c, origin_inventory, start_page):
    if origin_inventory is None:
        return 0
    patchless = origin_inventory[origin_inventory["accepted_patch_count"] == 0].copy()
    if patchless.empty:
        return 0
    pages = 0
    per_page = 9
    for start in range(0, len(patchless), per_page):
        page_num = start_page + pages
        y = new_page(
            c,
            "NDB-UFES WSI images without accepted patches",
            "These public NDB-UFES origin images currently have zero accepted patch rows in the organized patch metadata.",
            f"Data factsheet: NDB-UFES/SAB alignment Page {page_num}",
            advance=pages > 0,
        )
        chunk = patchless.iloc[start:start + per_page]
        cols, rows = 3, 3
        gap = 5 * mm
        cell_w = (PAGE_W - 2 * MARGIN_X - gap * (cols - 1)) / cols
        cell_h = 48 * mm
        top = y - 5 * mm
        for idx, (_, row) in enumerate(chunk.iterrows()):
            col = idx % cols
            line = idx // cols
            x = MARGIN_X + col * (cell_w + gap)
            yy = top - line * (cell_h + 18 * mm) - cell_h
            draw_image_fit(c, ROOT / str(row["origin_image_path"]), x, yy, cell_w, cell_h, max_side=520)
            c.setFont("Helvetica", 7)
            c.setFillColor(INK)
            c.drawString(x, yy - 4 * mm, f"NDB WSI {row['origin_id']}")
            c.drawString(x, yy - 8 * mm, str(row["diagnosis"])[:34])
        pages += 1
    return pages


def build():
    master = pd.read_csv(MASTER)
    coords = pd.read_csv(COORDS)
    origins = pd.read_csv(ORIGINS)
    pairs = pd.read_csv(PAIRS)
    summary = json.loads(SUMMARY.read_text())
    crosswalk = pd.read_csv(PRIVATE_CROSSWALK)
    origin_inventory = pd.read_csv(ORIGIN_INVENTORY) if ORIGIN_INVENTORY.exists() else None
    full = coords.merge(crosswalk, on="origin_validation_id", how="left", suffixes=("", "_private"))
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A4)
    draw_cover(c, summary, origins)
    draw_intro(c, summary, origins)
    draw_source_definitions(c)
    draw_key_findings(c, master, origins, pairs, origin_inventory)
    draw_flags(c)
    draw_counts(c, master)
    draw_label_agreement(c, master)
    draw_spatial(c, pairs)
    draw_limitations(c)
    draw_atlas_intro(c, 10)
    c.showPage()
    page_number = 11
    for origin_id in full["origin_validation_id"].dropna().astype(str).drop_duplicates().sort_values():
        group = full[full["origin_validation_id"].astype(str) == origin_id].sort_values("patch_number")
        draw_origin_page(c, origin_id, group, page_number)
        c.showPage()
        page_number += 1
    extra = draw_patchless_pages(c, origin_inventory, page_number)
    if extra:
        page_number += extra
    c.save()
    print(OUTPUT_PDF)


if __name__ == "__main__":
    build()
