import argparse
import json
import pickle
import textwrap
from pathlib import Path

import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

from src.phase0.patch_similarity import cosine_similarity_matrix
from src.release.atlas_methods import bbox_iou, pair_relation
from src.phase0.recovery_audit import (
    DEFAULT_ACCEPTED_METADATA,
    DEFAULT_ORIGIN_IMAGE_DIR,
    DEFAULT_RAW_PATCH_DIR,
    normalized_origin_id,
    patch_number,
)


DEFAULT_SAB_AUDIT_DIR = Path("results/phase0/sab_consistency_audit")
DEFAULT_OUTPUT_DIR = Path("results/phase0/dataset_alignment_report")
DEFAULT_EMBEDDINGS_PATH = Path("data/embeddings/embeddings_wsi_level_virchow_20260628_223154.pkl")
DEFAULT_RECOVERED_COORDINATES = Path("results/phase0/sab_coordinate_recovery/sab_patch_recovered_coordinates.csv")
DEFAULT_LOGO_PATH = Path("docs/assets/branding/labcin-logo.png")
DEFAULT_ORIGIN_INVENTORY = Path("results/phase0/recovery_audit/origin_image_inventory.csv")
PRIVATE_OUTPUT_DIRNAME = "private_lab_crosswalks"
PUBLIC_PRIVATE_COLUMNS = {
    "sab_origin_image_id",
    "sab_origin_image_id_recovered",
    "sab_case_prefix",
    "sab_case_prefix_recovered",
    "sab_origin_path",
    "sab_origin_path_recovered",
    "sab_patch_filename",
    "sab_patch_path",
    "sab_patch_path_recovered",
    "ndb_patch_path",
    "ndb_patch_path_recovered",
    "ndb_origin_path_from_sab_origin_exact_match",
}


def read_rgb(path: str | Path) -> np.ndarray | None:
    if not path or pd.isna(path):
        return None
    image = cv.imread(str(path), cv.IMREAD_COLOR)
    if image is None:
        return None
    return cv.cvtColor(image, cv.COLOR_BGR2RGB)


def safe_value(value, default=""):
    if value is None or pd.isna(value):
        return default
    return value


def image_path_for_origin(origin_image_dir: Path, origin_id) -> Path:
    return Path(origin_image_dir) / f"{normalized_origin_id(origin_id)}.png"


def patch_path(raw_patch_dir: Path, patch_id: str) -> Path:
    return Path(raw_patch_dir) / f"{patch_id}.png"


def classify_review_status(row: pd.Series) -> str:
    plausibility = row.get("patch_vs_origin_plausibility_status", "")
    source = row.get("source_convergence_status", "")
    origin_status = row.get("origin_folder_vs_current_metadata_status", "")
    patch_status = row.get("patch_csv_vs_sab_split_status", "")
    if plausibility == "impossible_or_high_conflict":
        return "biologically_implausible_or_high_conflict"
    if source in {"origin_and_patch_sources_disagree", "origin_sources_disagree", "patch_sources_disagree"}:
        return "source_disagreement"
    if origin_status == "broad_folder_only" or plausibility == "broad_origin_requires_review":
        return "requires_manual_review"
    if source == "insufficient_metadata" or patch_status == "missing_current_patch_metadata":
        return "metadata_insufficient"
    return "source_convergent"


def build_source_alignment_master(audit_dir: Path) -> pd.DataFrame:
    table = pd.read_csv(Path(audit_dir) / "patch_origin_plausibility_audit.csv")
    table["dataset_use_status"] = table.apply(classify_review_status, axis=1)
    accepted_label = table["current_patch_label_normalized"].fillna("unknown").astype(str)
    sab_label = table["sab_split_label_normalized"].fillna("unknown").astype(str)
    table["ndb_ufes_accepted_patch_label"] = accepted_label.where(accepted_label != "unknown", "missing_from_accepted_metadata")
    table["sab_patch_split_label"] = sab_label
    table["best_available_patch_label"] = accepted_label.where(accepted_label != "unknown", sab_label)
    table["best_available_patch_label_source"] = np.where(
        accepted_label != "unknown",
        "NDB-UFES accepted metadata",
        "SAB patch split folder",
    )
    keep_columns = [
        "ndb_patch",
        "ndb_patch_path",
        "current_patch_diagnosis",
        "current_patch_label_normalized",
        "ndb_ufes_accepted_patch_label",
        "sab_patch_split_label",
        "best_available_patch_label",
        "best_available_patch_label_source",
        "ndb_origin_id_from_patch_csv",
        "current_origin_diagnosis_from_patch_csv",
        "current_origin_label_from_patch_csv",
        "sab_patch_filename",
        "sab_patch_path",
        "sab_split",
        "sab_split_class",
        "sab_split_label_normalized",
        "sab_origin_image_id",
        "sab_case_prefix",
        "sab_origin_folder",
        "sab_origin_folder_label_normalized",
        "sab_origin_path",
        "ndb_origin_id_from_sab_origin_exact_match",
        "ndb_origin_path_from_sab_origin_exact_match",
        "current_origin_diagnosis_from_sab_origin_exact_match",
        "current_origin_label_from_sab_origin_exact_match",
        "patch_exact_match_found",
        "sab_origin_exact_current_ndb_match_found",
        "origin_folder_vs_current_metadata_status",
        "patch_csv_vs_sab_split_status",
        "patch_vs_origin_plausibility_status",
        "severity_direction",
        "source_convergence_status",
        "review_priority",
        "dataset_use_status",
    ]
    return table[[column for column in keep_columns if column in table.columns]].copy()


def attach_public_origin_ids(master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    master = master.copy()
    real_ids = sorted(master["sab_origin_image_id"].dropna().astype(str).unique())
    mapping = {real_id: f"origin_audit_{index:04d}" for index, real_id in enumerate(real_ids, start=1)}
    master["origin_audit_id"] = master["sab_origin_image_id"].astype(str).map(mapping)
    crosswalk_columns = [
        "origin_audit_id",
        "sab_origin_image_id",
        "sab_case_prefix",
        "sab_origin_folder",
        "sab_origin_folder_label_normalized",
        "sab_origin_path",
        "ndb_origin_id_from_sab_origin_exact_match",
        "ndb_origin_path_from_sab_origin_exact_match",
        "current_origin_diagnosis_from_sab_origin_exact_match",
        "current_origin_label_from_sab_origin_exact_match",
        "sab_origin_exact_current_ndb_match_found",
    ]
    crosswalk = master[[column for column in crosswalk_columns if column in master.columns]].drop_duplicates()
    return master, crosswalk.sort_values("origin_audit_id")


def public_release_table(table: pd.DataFrame) -> pd.DataFrame:
    drop_columns = [column for column in PUBLIC_PRIVATE_COLUMNS if column in table.columns]
    return table.drop(columns=drop_columns)


def build_origin_patch_composition(master: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for origin_key, group in master.groupby("origin_audit_id", dropna=False):
        accepted_labels = group["ndb_ufes_accepted_patch_label"].fillna("missing_from_accepted_metadata").astype(str)
        accepted_present = accepted_labels[accepted_labels != "missing_from_accepted_metadata"]
        best_labels = group["best_available_patch_label"].fillna("unknown").astype(str)
        sab_split_labels = group["sab_patch_split_label"].fillna("unknown").astype(str)
        statuses = group["dataset_use_status"].fillna("unknown").astype(str)
        rows.append({
            "origin_audit_id": origin_key,
            "sab_origin_folder": safe_value(group["sab_origin_folder"].iloc[0]),
            "sab_origin_folder_label_normalized": safe_value(group["sab_origin_folder_label_normalized"].iloc[0]),
            "current_ndb_origin_id_exact_match": safe_value(group["ndb_origin_id_from_sab_origin_exact_match"].iloc[0]),
            "n_patches": int(len(group)),
            "n_ndb_ufes_accepted_patch_labels_present": int(accepted_present.nunique()),
            "n_best_available_patch_labels": int(best_labels.nunique()),
            "ndb_ufes_accepted_patch_label_counts": json.dumps(accepted_labels.value_counts().to_dict(), sort_keys=True),
            "best_available_patch_label_counts": json.dumps(best_labels.value_counts().to_dict(), sort_keys=True),
            "sab_split_label_counts": json.dumps(sab_split_labels.value_counts().to_dict(), sort_keys=True),
            "dataset_use_status_counts": json.dumps(statuses.value_counts().to_dict(), sort_keys=True),
            "has_multiple_best_available_patch_labels": bool(best_labels.nunique() > 1),
            "n_source_disagreement": int((statuses == "source_disagreement").sum()),
            "n_biologically_implausible_or_high_conflict": int((statuses == "biologically_implausible_or_high_conflict").sum()),
            "n_metadata_insufficient": int((statuses == "metadata_insufficient").sum()),
        })
    return pd.DataFrame(rows).sort_values(
        ["n_biologically_implausible_or_high_conflict", "n_source_disagreement", "n_patches"],
        ascending=[False, False, False],
    )


def coordinate_status(row: pd.Series, origin_image_dir: Path) -> str:
    needed = ["top_left_x", "top_left_y", "bottom_right_x", "bottom_right_y"]
    if any(column not in row or pd.isna(row[column]) for column in needed):
        return "coordinate_missing"
    x1, y1, x2, y2 = [float(row[column]) for column in needed]
    if x2 <= x1 or y2 <= y1:
        return "coordinate_invalid_order"
    origin_path = image_path_for_origin(origin_image_dir, row["origin"])
    image = read_rgb(origin_path)
    if image is None:
        return "origin_image_missing"
    height, width = image.shape[:2]
    patch_width = x2 - x1
    patch_height = y2 - y1
    inside = x1 >= 0 and y1 >= 0 and x2 <= width and y2 <= height
    patch_sized = abs(patch_width - 512) <= 2 and abs(patch_height - 512) <= 2
    if inside and patch_sized:
        return "inside_origin_bounds_patch_sized"
    if inside:
        return "inside_origin_bounds_nonstandard_size"
    return "outside_origin_bounds_requires_review"


def load_embeddings(path: Path) -> dict:
    if not Path(path).exists():
        return {}
    with Path(path).open("rb") as handle:
        return pickle.load(handle)


def visual_fingerprint(path: str | Path, size: int = 32) -> np.ndarray | None:
    image = read_rgb(path)
    if image is None:
        return None
    small = cv.resize(image, (size, size), interpolation=cv.INTER_AREA).astype(np.float32) / 255.0
    lab = cv.cvtColor((small * 255).astype(np.uint8), cv.COLOR_RGB2LAB).astype(np.float32)
    vector = np.concatenate([small.reshape(-1), lab.reshape(-1)])
    vector = vector - float(vector.mean())
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return None
    return vector / norm


def cosine_from_vectors(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return np.nan
    return float(np.dot(a, b))


def lab_mean_delta(path_a: str | Path, path_b: str | Path) -> float:
    image_a = read_rgb(path_a)
    image_b = read_rgb(path_b)
    if image_a is None or image_b is None:
        return np.nan
    lab_a = cv.cvtColor(image_a, cv.COLOR_RGB2LAB).reshape(-1, 3).mean(axis=0)
    lab_b = cv.cvtColor(image_b, cv.COLOR_RGB2LAB).reshape(-1, 3).mean(axis=0)
    return float(np.linalg.norm(lab_a - lab_b))


def lab_mean_vector(path: str | Path) -> np.ndarray | None:
    image = read_rgb(path)
    if image is None:
        return None
    return cv.cvtColor(image, cv.COLOR_RGB2LAB).reshape(-1, 3).mean(axis=0)


def vector_distance(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return np.nan
    return float(np.linalg.norm(a - b))


def recovered_coordinate_status(row: pd.Series) -> str:
    status = str(row.get("coordinate_recovery_status", "missing"))
    if status in {"exact_pixel_match", "near_pixel_match"}:
        return "recovered_from_sab_exact_or_near_pixel_match"
    return f"recovery_requires_review_{status}"


def build_patch_pair_similarity(
    master: pd.DataFrame,
    recovered_coordinates: pd.DataFrame,
    similarity_threshold: float,
    color_delta_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metadata = master.merge(
        recovered_coordinates,
        on="ndb_patch",
        how="left",
        suffixes=("", "_recovered"),
    )
    metadata["patch_number"] = metadata["ndb_patch"].map(patch_number)
    metadata["coordinate_status"] = metadata.apply(recovered_coordinate_status, axis=1)
    metadata["visual_fingerprint"] = metadata["ndb_patch_path"].map(visual_fingerprint)
    metadata["lab_mean"] = metadata["ndb_patch_path"].map(lab_mean_vector)
    rows = []
    for origin_id, group in metadata.groupby("origin_audit_id", dropna=False):
        ordered = group.sort_values("patch_number").reset_index(drop=True)
        for index_a in range(len(ordered)):
            for index_b in range(index_a + 1, len(ordered)):
                a = ordered.iloc[index_a]
                b = ordered.iloc[index_b]
                both_valid = (
                    a["coordinate_status"] == "recovered_from_sab_exact_or_near_pixel_match"
                    and b["coordinate_status"] == "recovered_from_sab_exact_or_near_pixel_match"
                )
                iou = bbox_iou(a, b, "recovered_") if both_valid else np.nan
                feature_similarity = cosine_from_vectors(a["visual_fingerprint"], b["visual_fingerprint"])
                color_delta = vector_distance(a["lab_mean"], b["lab_mean"])
                if pd.isna(iou):
                    coordinate_relation = "coordinate_unavailable_or_requires_review"
                elif iou > 0:
                    coordinate_relation = "spatially_overlapping"
                else:
                    coordinate_relation = "spatially_distinct"
                if pd.isna(feature_similarity):
                    feature_relation = "feature_similarity_unavailable"
                elif feature_similarity >= similarity_threshold and color_delta <= color_delta_threshold:
                    feature_relation = "feature_similar"
                else:
                    feature_relation = "feature_not_similar"
                relation = pair_relation(coordinate_relation, feature_relation, iou)
                rows.append({
                    "origin_audit_id": origin_id,
                    "sab_origin_folder": a.get("sab_origin_folder", ""),
                    "patch_a": a["ndb_patch"],
                    "patch_b": b["ndb_patch"],
                    "label_a": a.get("current_patch_label_normalized", ""),
                    "label_b": b.get("current_patch_label_normalized", ""),
                    "coordinate_status_a": a["coordinate_status"],
                    "coordinate_status_b": b["coordinate_status"],
                    "x_a": a.get("recovered_x", np.nan),
                    "y_a": a.get("recovered_y", np.nan),
                    "x2_a": a.get("recovered_x2", np.nan),
                    "y2_a": a.get("recovered_y2", np.nan),
                    "x_b": b.get("recovered_x", np.nan),
                    "y_b": b.get("recovered_y", np.nan),
                    "x2_b": b.get("recovered_x2", np.nan),
                    "y2_b": b.get("recovered_y2", np.nan),
                    "iou": iou,
                    "visual_fingerprint_similarity": feature_similarity,
                    "lab_mean_delta": color_delta,
                    "coordinate_relation": coordinate_relation,
                    "feature_relation": feature_relation,
                    "pair_relation": relation,
                })
    return metadata.drop(columns=["visual_fingerprint", "lab_mean"]), pd.DataFrame(rows)


def count_table(series: pd.Series) -> pd.DataFrame:
    counts = series.fillna("unknown").astype(str).value_counts().rename_axis("status").reset_index(name="count")
    counts["percent"] = counts["count"] / counts["count"].sum() * 100
    return counts


def write_count_csvs(master: pd.DataFrame, origins: pd.DataFrame, metadata: pd.DataFrame, pairs: pd.DataFrame, output_dir: Path) -> None:
    count_table(master["dataset_use_status"]).to_csv(output_dir / "dataset_use_status_counts.csv", index=False)
    count_table(master["patch_csv_vs_sab_split_status"]).to_csv(output_dir / "patch_label_source_status_counts.csv", index=False)
    count_table(master["origin_folder_vs_current_metadata_status"]).to_csv(output_dir / "origin_label_source_status_counts.csv", index=False)
    count_table(master["patch_vs_origin_plausibility_status"]).to_csv(output_dir / "patch_origin_plausibility_counts.csv", index=False)
    count_table(metadata["coordinate_status"]).to_csv(output_dir / "coordinate_status_counts.csv", index=False)
    if not pairs.empty:
        count_table(pairs["pair_relation"]).to_csv(output_dir / "patch_pair_relation_counts.csv", index=False)
        count_table(pairs["coordinate_relation"]).to_csv(output_dir / "patch_pair_coordinate_relation_counts.csv", index=False)
        count_table(pairs["feature_relation"]).to_csv(output_dir / "patch_pair_feature_relation_counts.csv", index=False)


def draw_bar(ax, series: pd.Series, title: str, color="#4C78A8") -> None:
    counts = series.fillna("unknown").astype(str).value_counts()
    ax.barh(range(len(counts)), counts.values, color=color)
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels(counts.index, fontsize=8)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("count")
    for index, value in enumerate(counts.values):
        ax.text(value, index, f" {value}", va="center", fontsize=8)


PAGE_A4_PORTRAIT = (8.27, 11.69)
PAGE_A4_LANDSCAPE = (11.69, 8.27)
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
    "coordinate_unavailable_or_requires_review": "coordinates unavailable",
}
LABEL_COLORS = {
    "oscc": "#D04A3A",
    "with_dysplasia": "#E2A23A",
    "without_dysplasia": "#3E78B2",
    "unknown": "#777777",
    "missing_from_accepted_metadata": "#777777",
}


def display_label(value: str) -> str:
    return LABEL_DISPLAY.get(str(value), str(value).replace("_", " "))


def display_status(value: str) -> str:
    return STATUS_DISPLAY.get(str(value), str(value).replace("_", " "))


def display_pair_relation(value: str) -> str:
    return PAIR_DISPLAY.get(str(value), str(value).replace("_", " "))


def add_logo(fig, logo_path: Path, x=0.62, y=0.86, w=0.25, h=0.08) -> None:
    if not logo_path or not Path(logo_path).exists():
        return
    ax = fig.add_axes([x, y, w, h])
    add_image_axis(ax, logo_path, "")


def add_wrapped_text(fig, text: str, x: float, y: float, width: int = 90, size: float = 9.5, weight: str = "normal", line_height: float = 0.026) -> float:
    for line in textwrap.wrap(text, width=width):
        fig.text(x, y, line, fontsize=size, fontweight=weight, va="top")
        y -= line_height
    return y


def wrap_cell(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(str(value), width=width)) if value is not None else ""


def add_table(
    ax,
    rows: list[list[str]],
    columns: list[str],
    font_size: float = 8.0,
    scale_y: float = 1.4,
    col_widths: list[float] | None = None,
    wrap_widths: list[int] | None = None,
) -> None:
    ax.axis("off")
    if wrap_widths:
        rows = [[wrap_cell(cell, wrap_widths[min(index, len(wrap_widths) - 1)]) for index, cell in enumerate(row)] for row in rows]
        columns = [wrap_cell(column, wrap_widths[min(index, len(wrap_widths) - 1)]) for index, column in enumerate(columns)]
    table = ax.table(cellText=rows, colLabels=columns, loc="upper left", cellLoc="left", colLoc="left", colWidths=col_widths)
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1, scale_y)
    for (row, _column), cell in table.get_celld().items():
        cell.set_edgecolor("#D9D9D9")
        if row == 0:
            cell.set_facecolor("#EFEFEF")
            cell.set_text_props(weight="bold")


def add_section_title(fig, title: str, subtitle: str | None = None, logo_path: Path | None = None) -> None:
    fig.text(0.08, 0.95, title, fontsize=18, fontweight="bold", va="top")
    if subtitle:
        add_wrapped_text(fig, subtitle, 0.08, 0.91, width=95, size=9.5, line_height=0.024)
    if logo_path:
        add_logo(fig, logo_path, x=0.72, y=0.91, w=0.18, h=0.055)


def count_rows(series: pd.Series, display_func=lambda x: x) -> list[list[str]]:
    counts = series.fillna("unknown").astype(str).value_counts()
    total = counts.sum()
    return [[display_func(index), f"{int(value)}", f"{value / total * 100:.1f}%"] for index, value in counts.items()]


def add_cover_page(pdf: PdfPages, logo_path: Path, audit_summary: dict, origins: pd.DataFrame) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_logo(fig, logo_path, x=0.58, y=0.86, w=0.28, h=0.09)
    fig.text(0.08, 0.78, "NDB-UFES and SAB Dataset Alignment Audit", fontsize=24, fontweight="bold", va="top")
    fig.text(0.08, 0.71, "Patch provenance, label convergence, and recovered WSI coordinates", fontsize=12, va="top", color="#444444")
    y = 0.62
    paragraphs = [
        "This document compares the public NDB-UFES dataset distributed through Mendeley with the private SAB laboratory dataset stored in laboratory computers and university cloud folders. The SAB files are treated as a trusted provenance source for this audit because they were used in earlier training pipelines and contain the origin-image hash names from which the patch files were generated.",
        "The goal is to validate whether the 3,763 patch images, their labels, and their origin-image relationships align across sources, and to identify patches or origin images that require manual review before being used in leakage-safe experiments.",
        "Public tables use pseudonymous origin_audit_id values. The real SAB origin filenames and paths are stored only in the private lab crosswalk.",
    ]
    for paragraph in paragraphs:
        y = add_wrapped_text(fig, paragraph, 0.08, y, width=92, size=10.5, line_height=0.028)
        y -= 0.018
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_dataset_definitions_page(pdf: PdfPages, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Dataset Sources", "Definitions used throughout this audit.", logo_path)
    rows = [
        [
            "NDB-UFES",
            "Public dataset distributed through Mendeley.",
            "Public WSI images, patch images, accepted metadata, patient/lesion fields, and task labels used in the current organized dataset.",
        ],
        [
            "SAB",
            "Private laboratory dataset stored in laboratory computers and university cloud folders.",
            "WSI folders named benigno, leucoplasia, and carcinoma; patch train/test folders; SAB origin hash names that link images to the local SAB system.",
        ],
        [
            "Accepted NDB-UFES metadata",
            "The current CSV treated as the organized public metadata table.",
            "Used when available, but not assumed to contain every patch-origin relationship found in SAB.",
        ],
        [
            "Origin audit ID",
            "Privacy-preserving pseudonym generated for each SAB origin image.",
            "Used in public reports instead of the SAB hash filename. The private crosswalk links it back to SAB for lab-only review.",
        ],
    ]
    ax = fig.add_axes([0.06, 0.45, 0.88, 0.40])
    add_table(
        ax,
        rows,
        ["Term", "Meaning", "Role in this audit"],
        font_size=6.4,
        scale_y=3.2,
        col_widths=[0.22, 0.30, 0.48],
        wrap_widths=[24, 34, 52],
    )
    y = 0.34
    y = add_wrapped_text(fig, "Observed file provenance: SAB WSI class folders have September 10, 2021 modification times on this disk. The SAB patch split contains 3,763 PNG files. These timestamps describe file provenance, not annotation date.", 0.08, y, width=92, size=9.2)
    add_wrapped_text(fig, "Important privacy note: SAB hash filenames may be linkable to the SAB system used by dental students. They are therefore excluded from public CSVs and public prose.", 0.08, y - 0.05, width=92, size=9.2)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_key_findings_page(pdf: PdfPages, master: pd.DataFrame, origins: pd.DataFrame, pairs: pd.DataFrame, audit_summary: dict, origin_inventory: pd.DataFrame | None, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Key Audit Findings", "Counts are reported as audit evidence, not as clinical truth claims.", logo_path)
    current_multi = int(origins["n_ndb_ufes_accepted_patch_labels_present"].gt(1).sum())
    best_multi = int(origins["has_multiple_best_available_patch_labels"].sum())
    patchless = int((origin_inventory["accepted_patch_count"] == 0).sum()) if origin_inventory is not None and "accepted_patch_count" in origin_inventory else "not computed"
    rows = [
        ["Patch identity", "3,763 / 3,763 NDB-UFES patch files exact-match SAB split patch files.", "The patch image set is shared between the sources."],
        ["WSI identity", "222 / 242 NDB-UFES WSI images exact-match a SAB WSI image.", "The WSI/origin set diverges across sources."],
        ["SAB WSI groups with patches", f"{origins['origin_audit_id'].nunique()} origin_audit_id groups.", "The SAB split links patches to more origin groups than the public WSI set exact-matches."],
        ["NDB-UFES public WSI without accepted patches", str(patchless), "These are public origin images that currently do not contribute accepted patch rows."],
        ["Origins with >1 accepted NDB-UFES patch label", str(current_multi), "This excludes patches missing from the accepted metadata table."],
        ["Origins with >1 best available patch label", str(best_multi), "This uses accepted NDB-UFES labels when present, otherwise SAB split labels."],
        ["Patch pairs spatially compared", f"{len(pairs):,}", "Comparisons are within the same SAB origin only."],
    ]
    ax = fig.add_axes([0.05, 0.20, 0.90, 0.68])
    add_table(
        ax,
        rows,
        ["Question", "Result", "Interpretation"],
        font_size=6.8,
        scale_y=2.85,
        col_widths=[0.28, 0.31, 0.41],
        wrap_widths=[30, 35, 48],
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_status_dictionary_page(pdf: PdfPages, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "How to Read the Audit Flags", "The report separates source convergence from biological or logical plausibility.", logo_path)
    rows = [
        ["Sources converge", "Available labels from NDB-UFES and SAB do not show a relevant disagreement.", "Usually low priority."],
        ["Source labels differ", "The accepted NDB-UFES label and the SAB split/folder label differ at patch or origin level.", "Review before using for model training."],
        ["Needs manual review", "A broad SAB folder, missing current metadata, or ambiguous source context prevents a clean decision.", "Candidate-only until reviewed."],
        ["High biological/source conflict", "A non-OSCC origin context is linked to an OSCC/carcinoma patch label.", "Do not silently include without manual adjudication."],
        ["Metadata incomplete", "The exact image exists, but the accepted public metadata does not fully describe it.", "Recoverable evidence, but not final metadata."],
    ]
    ax = fig.add_axes([0.06, 0.48, 0.88, 0.38])
    add_table(
        ax,
        rows,
        ["Reader-facing flag", "Meaning", "Suggested action"],
        font_size=7.0,
        scale_y=2.5,
        col_widths=[0.24, 0.41, 0.35],
        wrap_widths=[25, 48, 40],
    )
    rows2 = [
        ["NDB-UFES accepted metadata label", "Patch diagnosis found in the current public organized metadata CSV."],
        ["SAB patch split label", "Patch class inferred from the SAB train/test class folder after exact image matching."],
        ["Best available patch label", "NDB-UFES accepted metadata label when present; otherwise SAB patch split label."],
        ["SAB origin folder label", "Origin-level context from the private SAB WSI folder name; leucoplasia is broad and does not specify dysplasia."],
    ]
    ax2 = fig.add_axes([0.06, 0.16, 0.88, 0.22])
    add_table(ax2, rows2, ["Label term", "Definition"], font_size=7.2, scale_y=2.1, col_widths=[0.32, 0.68], wrap_widths=[34, 72])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_counts_page(pdf: PdfPages, master: pd.DataFrame, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Source Convergence Counts", "Tables are used here instead of unlabeled charts so the categories can be read directly.", logo_path)
    rows1 = count_rows(master["dataset_use_status"], display_status)
    rows2 = count_rows(master["patch_csv_vs_sab_split_status"], lambda value: {
        "agrees": "accepted NDB-UFES and SAB split agree",
        "disagrees": "accepted NDB-UFES and SAB split differ",
        "missing_current_patch_metadata": "missing from accepted NDB-UFES metadata",
    }.get(str(value), str(value)))
    ax1 = fig.add_axes([0.06, 0.55, 0.88, 0.31])
    add_table(ax1, rows1, ["Audit interpretation", "Patches", "Percent"], font_size=7.8, scale_y=1.95, col_widths=[0.62, 0.19, 0.19], wrap_widths=[58, 12, 12])
    ax2 = fig.add_axes([0.06, 0.18, 0.88, 0.26])
    add_table(ax2, rows2, ["Patch label comparison", "Patches", "Percent"], font_size=7.8, scale_y=1.95, col_widths=[0.62, 0.19, 0.19], wrap_widths=[58, 12, 12])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_label_crosstab_page(pdf: PdfPages, master: pd.DataFrame, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Patch Label Agreement", "Rows are labels from accepted NDB-UFES metadata. Columns are labels from the SAB patch split.", logo_path)
    rows = []
    crosstab = pd.crosstab(
        master["ndb_ufes_accepted_patch_label"].fillna("missing_from_accepted_metadata"),
        master["sab_patch_split_label"].fillna("unknown"),
    )
    for index, row in crosstab.iterrows():
        rows.append([display_label(index)] + [str(int(row.get(column, 0))) for column in ["without_dysplasia", "with_dysplasia", "oscc"]])
    ax = fig.add_axes([0.08, 0.52, 0.84, 0.30])
    add_table(
        ax,
        rows,
        ["NDB-UFES accepted metadata", "SAB without dysplasia", "SAB with dysplasia", "SAB OSCC"],
        font_size=7.0,
        scale_y=2.0,
        col_widths=[0.34, 0.22, 0.22, 0.22],
        wrap_widths=[32, 20, 20, 14],
    )
    y = 0.38
    y = add_wrapped_text(fig, "Interpretation: cells away from the diagonal indicate that the same patch image carries different class information depending on which source is used. The row 'missing from accepted metadata' means the patch is absent from the accepted NDB-UFES metadata table but still has a SAB split label.", 0.08, y, width=92, size=9.2)
    add_wrapped_text(fig, "This table should not be read as a pathologist disagreement matrix. It is a source-alignment matrix between dataset versions.", 0.08, y - 0.05, width=92, size=9.2)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_spatial_similarity_page(pdf: PdfPages, pairs: pd.DataFrame, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Patch Spatial and Visual Relationships", "Pairwise comparisons are computed only within the same SAB origin image.", logo_path)
    rows = count_rows(pairs["pair_relation"], display_pair_relation)
    ax = fig.add_axes([0.06, 0.52, 0.88, 0.30])
    add_table(ax, rows, ["Patch-pair category", "Pairs", "Percent"], font_size=7.8, scale_y=1.9, col_widths=[0.62, 0.19, 0.19], wrap_widths=[58, 12, 12])
    paragraphs = [
        "Spatial relationship comes from recovered pixel coordinates: two 512 x 512 patches either overlap on the same SAB origin image or they do not.",
        "Visual relationship uses a conservative patch fingerprint: patches are called visually similar only when their downsampled color/structure fingerprint is high and their mean LAB color difference is low.",
        "The category 'visually similar but spatially separate' indicates repeated or similar morphology within the same WSI, not duplicated tissue. 'Visually similar and spatially overlapping' indicates near-duplicate or shared-tissue evidence.",
    ]
    y = 0.42
    for paragraph in paragraphs:
        y = add_wrapped_text(fig, paragraph, 0.08, y, width=98, size=8.6, line_height=0.023)
        y -= 0.014
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_limitations_page(pdf: PdfPages, logo_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_A4_PORTRAIT)
    add_section_title(fig, "Use and Limitations", "This audit prepares evidence for manual review and leakage-safe experiments.", logo_path)
    rows = [
        ["Do not publish private linkage keys", "Use origin_audit_id publicly. Keep the private crosswalk inside the lab."],
        ["Do not treat flags as final clinical judgment", "Flags identify source inconsistencies and plausibility concerns; they do not replace blind pathology review."],
        ["Recovered coordinates are evidence", "Coordinates were recovered by exact pixel matching between patches and SAB WSI images."],
        ["Suspicious patches are candidates for exclusion or adjudication", "Experiments can compare all linked data versus stricter reviewed subsets."],
        ["Patch labels can be patch-specific", "A patch label may differ from a broad origin context, especially for leukoplakia; OSCC under non-OSCC origin context is treated as high conflict."],
    ]
    ax = fig.add_axes([0.06, 0.35, 0.88, 0.50])
    add_table(ax, rows, ["Rule", "Meaning"], font_size=7.4, scale_y=2.55, col_widths=[0.34, 0.66], wrap_widths=[36, 72])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_text_page(pdf: PdfPages, title: str, lines: list[str]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.04, 0.96, title, fontsize=17, fontweight="bold", va="top")
    y = 0.90
    for line in lines:
        fig.text(0.05, y, line, fontsize=10, va="top")
        y -= 0.033
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_summary_pages(pdf: PdfPages, master: pd.DataFrame, origins: pd.DataFrame, metadata: pd.DataFrame, pairs: pd.DataFrame, audit_summary: dict) -> None:
    lines = [
        "Purpose: document what exists in NDB and SAB, where it can be found, and how source labels align.",
        "",
        f"NDB patch images audited: {audit_summary.get('current_patch_images', len(master))}",
        f"NDB patches exact-matched to SAB split patches: {audit_summary.get('current_patch_images_exact_matched_to_sab', int(master['patch_exact_match_found'].sum()))}",
        f"Current NDB origin images audited: {audit_summary.get('current_origin_images', 'unknown')}",
        f"Current NDB origin images exact-matched to SAB origins: {audit_summary.get('current_origin_images_exact_matched_to_sab', 'unknown')}",
        f"SAB origin groups represented by patches: {origins['origin_audit_id'].nunique()}",
        f"SAB origins with multiple current patch labels: {int(origins['has_multiple_current_patch_labels'].sum())}",
        "",
        "Public files use origin_audit_id pseudonyms. Real SAB origin filenames/paths are written only to the private lab crosswalk.",
        "",
        "Dataset-use status is an audit category, not a clinical truth score.",
        "source_convergent: available source labels agree or no relevant disagreement was detected.",
        "source_disagreement: SAB/current labels diverge at patch and/or origin level.",
        "requires_manual_review: broad/ambiguous source folders or ambiguous plausibility need review.",
        "biologically_implausible_or_high_conflict: OSCC/carcinoma patch under non-OSCC origin context.",
        "metadata_insufficient: exact image evidence exists, but current metadata is missing or incomplete.",
    ]
    add_text_page(pdf, "Dataset Source Alignment Report", lines)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    draw_bar(axes[0, 0], master["dataset_use_status"], "Dataset-use status", "#4C78A8")
    draw_bar(axes[0, 1], master["patch_csv_vs_sab_split_status"], "Patch label source status", "#F58518")
    draw_bar(axes[1, 0], master["origin_folder_vs_current_metadata_status"], "Origin label source status", "#54A24B")
    draw_bar(axes[1, 1], master["patch_vs_origin_plausibility_status"], "Patch-origin plausibility", "#B279A2")
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    draw_bar(axes[0], metadata["coordinate_status"], "Recovered coordinate status", "#72B7B2")
    if pairs.empty:
        axes[1].text(0.5, 0.5, "No pair similarity table", ha="center", va="center")
        axes[1].axis("off")
    else:
        draw_bar(axes[1], pairs["pair_relation"], "Patch pair spatial/visual relationship", "#E45756")
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_image_axis(ax, path, title: str) -> None:
    image = read_rgb(path)
    if image is None:
        ax.text(0.5, 0.5, "not available", ha="center", va="center")
    else:
        ax.imshow(image)
    ax.set_title(title, fontsize=9)
    ax.axis("off")


def add_source_case_page(pdf: PdfPages, row: pd.Series, title: str) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.04, 0.96, title, fontsize=15, fontweight="bold", va="top")
    fields = [
        f"NDB patch: {row.get('ndb_patch', '')}",
        f"Current patch label: {row.get('current_patch_label_normalized', '')}",
        f"SAB split label: {row.get('sab_split_label_normalized', '')} ({row.get('sab_split_class', '')})",
        f"SAB origin audit ID: {row.get('origin_audit_id', '')}",
        f"SAB origin folder label: {row.get('sab_origin_folder_label_normalized', '')} ({row.get('sab_origin_folder', '')})",
        f"Current NDB origin from patch CSV: {row.get('ndb_origin_id_from_patch_csv', '')} / {row.get('current_origin_label_from_patch_csv', '')}",
        f"Exact NDB origin match from SAB origin: {row.get('ndb_origin_id_from_sab_origin_exact_match', '')}",
        f"Source status: {row.get('source_convergence_status', '')}",
        f"Use status: {row.get('dataset_use_status', '')}",
        f"Plausibility: {row.get('patch_vs_origin_plausibility_status', '')}",
    ]
    for index, line in enumerate(fields):
        fig.text(0.04, 0.90 - index * 0.026, line, fontsize=9, va="top")
    axes = [
        fig.add_axes([0.04, 0.10, 0.21, 0.30]),
        fig.add_axes([0.28, 0.10, 0.21, 0.30]),
        fig.add_axes([0.52, 0.10, 0.21, 0.30]),
        fig.add_axes([0.76, 0.10, 0.21, 0.30]),
    ]
    add_image_axis(axes[0], row.get("ndb_patch_path", ""), "NDB patch")
    add_image_axis(axes[1], row.get("sab_patch_path", ""), "SAB patch")
    add_image_axis(axes[2], row.get("sab_origin_path", ""), "SAB origin")
    add_image_axis(axes[3], row.get("ndb_origin_path_from_sab_origin_exact_match", ""), "NDB origin exact match")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_origin_bbox_page(pdf: PdfPages, origin_id: str, metadata: pd.DataFrame, raw_patch_dir: Path, origin_image_dir: Path, pair_rows: pd.DataFrame) -> None:
    group = metadata[metadata["origin_audit_id"].astype(str) == str(origin_id)].sort_values("patch_number")
    if group.empty:
        return
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.04, 0.96, f"SAB origin {origin_id}: recovered patch coordinates", fontsize=15, fontweight="bold", va="top")
    label_counts = group["current_patch_label_normalized"].fillna("unknown").value_counts().to_dict()
    coord_counts = group["coordinate_status"].value_counts().to_dict()
    fig.text(0.04, 0.91, f"Patches: {len(group)} | Current patch labels: {label_counts} | Coordinate status: {coord_counts}", fontsize=9, va="top")

    ax_origin = fig.add_axes([0.04, 0.25, 0.45, 0.55])
    origin_path = group["sab_origin_path"].dropna().astype(str).iloc[0] if group["sab_origin_path"].notna().any() else ""
    image = read_rgb(origin_path)
    if image is None:
        ax_origin.text(0.5, 0.5, "origin image not available", ha="center", va="center")
    else:
        ax_origin.imshow(image)
        colors = {"oscc": "#E45756", "with_dysplasia": "#F58518", "without_dysplasia": "#4C78A8", "unknown": "#666666"}
        for _, row in group.iterrows():
            if row["coordinate_status"] != "recovered_from_sab_exact_or_near_pixel_match":
                continue
            x1, y1 = float(row["recovered_x"]), float(row["recovered_y"])
            x2, y2 = float(row["recovered_x2"]), float(row["recovered_y2"])
            label = safe_value(row.get("current_patch_label_normalized"), "unknown")
            rect = Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1.3, edgecolor=colors.get(label, "#000000"), facecolor="none")
            ax_origin.add_patch(rect)
            ax_origin.text(x1, y1, row["ndb_patch"], fontsize=6, color="black", bbox={"facecolor": "white", "alpha": 0.6, "pad": 0.5})
    ax_origin.set_title("SAB origin image with recovered patch boxes")
    ax_origin.axis("off")

    example_pairs = pair_rows[pair_rows["origin_audit_id"].astype(str) == str(origin_id)].copy()
    example_pairs = example_pairs.sort_values(["visual_fingerprint_similarity", "iou"], ascending=[False, False]).head(2)
    for pair_index, pair in enumerate(example_pairs.itertuples(index=False)):
        y = 0.53 - pair_index * 0.28
        fig.text(0.54, y + 0.19, f"{pair.pair_relation}: {pair.patch_a} - {pair.patch_b} | visual={pair.visual_fingerprint_similarity:.3f} | IoU={pair.iou if not pd.isna(pair.iou) else 'NA'}", fontsize=8)
        ax_a = fig.add_axes([0.54, y, 0.18, 0.17])
        ax_b = fig.add_axes([0.75, y, 0.18, 0.17])
        add_image_axis(ax_a, patch_path(raw_patch_dir, pair.patch_a), pair.patch_a)
        add_image_axis(ax_b, patch_path(raw_patch_dir, pair.patch_b), pair.patch_b)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_private_origin_atlas_page(pdf: PdfPages, origin_id: str, metadata: pd.DataFrame, raw_patch_dir: Path) -> None:
    group = metadata[metadata["origin_audit_id"].astype(str) == str(origin_id)].sort_values("patch_number")
    if group.empty:
        return
    fig = plt.figure(figsize=PAGE_A4_LANDSCAPE)
    folder = safe_value(group["sab_origin_folder"].iloc[0])
    folder_label = display_label(safe_value(group["sab_origin_folder_label_normalized"].iloc[0], "unknown"))
    accepted_match = safe_value(group["ndb_origin_id_from_sab_origin_exact_match"].iloc[0], "not matched")
    best_counts = group["best_available_patch_label"].fillna("unknown").astype(str).value_counts().to_dict()
    status_counts = group["dataset_use_status"].fillna("unknown").astype(str).value_counts().to_dict()
    fig.text(0.03, 0.96, f"{origin_id}", fontsize=15, fontweight="bold", va="top")
    fig.text(0.03, 0.925, f"SAB WSI folder: {folder} ({folder_label}) | NDB-UFES exact WSI match: {accepted_match} | patches: {len(group)}", fontsize=8.5, va="top")
    fig.text(0.03, 0.900, f"Best available patch labels: {json.dumps({display_label(k): int(v) for k, v in best_counts.items()}, sort_keys=True)}", fontsize=8.0, va="top")
    fig.text(0.03, 0.878, f"Audit interpretation counts: {json.dumps({display_status(k): int(v) for k, v in status_counts.items()}, sort_keys=True)}", fontsize=8.0, va="top")

    ax_origin = fig.add_axes([0.03, 0.08, 0.47, 0.75])
    origin_path = group["sab_origin_path"].dropna().astype(str).iloc[0] if group["sab_origin_path"].notna().any() else ""
    image = read_rgb(origin_path)
    if image is None:
        ax_origin.text(0.5, 0.5, "SAB WSI image not available", ha="center", va="center")
    else:
        ax_origin.imshow(image)
        legend_labels = set()
        for _, row in group.iterrows():
            if row["coordinate_status"] != "recovered_from_sab_exact_or_near_pixel_match":
                continue
            label = safe_value(row.get("best_available_patch_label"), "unknown")
            legend_labels.add(label)
            x1, y1 = float(row["recovered_x"]), float(row["recovered_y"])
            x2, y2 = float(row["recovered_x2"]), float(row["recovered_y2"])
            rect = Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1.0, edgecolor=LABEL_COLORS.get(label, "#000000"), facecolor="none")
            ax_origin.add_patch(rect)
            ax_origin.text(x1, y1, row["ndb_patch"], fontsize=5.5, color="black", bbox={"facecolor": "white", "alpha": 0.55, "pad": 0.4})
        handles = [Line2D([0], [0], color=LABEL_COLORS.get(label, "#000000"), lw=2, label=display_label(label)) for label in sorted(legend_labels)]
        if handles:
            ax_origin.legend(handles=handles, loc="lower right", fontsize=6, framealpha=0.85)
    ax_origin.set_title("SAB WSI with recovered patch coordinates", fontsize=9)
    ax_origin.axis("off")

    patch_area_left = 0.54
    patch_area_bottom = 0.08
    patch_area_width = 0.43
    patch_area_height = 0.75
    columns = 5
    rows = 4
    cell_w = patch_area_width / columns
    cell_h = patch_area_height / rows
    for index, (_, row) in enumerate(group.head(columns * rows).iterrows()):
        col = index % columns
        line = index // columns
        ax = fig.add_axes([
            patch_area_left + col * cell_w + 0.006,
            patch_area_bottom + (rows - line - 1) * cell_h + 0.016,
            cell_w - 0.012,
            cell_h - 0.036,
        ])
        add_image_axis(ax, patch_path(raw_patch_dir, row["ndb_patch"]), "")
        label = display_label(safe_value(row.get("best_available_patch_label"), "unknown"))
        source = safe_value(row.get("best_available_patch_label_source"), "")
        ax.set_title(f"{row['ndb_patch']} | {label}\n{source}", fontsize=5.7)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_patchless_ndb_contact_pages(pdf: PdfPages, origin_inventory: pd.DataFrame, page_title: str = "NDB-UFES WSI images without accepted patches") -> int:
    if origin_inventory is None or origin_inventory.empty or "accepted_patch_count" not in origin_inventory:
        return 0
    patchless = origin_inventory[origin_inventory["accepted_patch_count"] == 0].copy()
    if patchless.empty:
        return 0
    pages = 0
    per_page = 12
    for start in range(0, len(patchless), per_page):
        chunk = patchless.iloc[start:start + per_page]
        fig = plt.figure(figsize=PAGE_A4_LANDSCAPE)
        fig.text(0.03, 0.96, page_title, fontsize=15, fontweight="bold", va="top")
        fig.text(0.03, 0.925, "These public NDB-UFES origin images currently have zero accepted patch rows in the organized patch metadata.", fontsize=8.5, va="top")
        columns = 4
        rows = 3
        for index, (_, row) in enumerate(chunk.iterrows()):
            col = index % columns
            line = index // columns
            ax = fig.add_axes([0.04 + col * 0.235, 0.08 + (rows - line - 1) * 0.26, 0.20, 0.20])
            add_image_axis(ax, row.get("origin_image_path", ""), "")
            title = f"NDB WSI {row.get('origin_id', '')}\n{row.get('diagnosis', '')}"
            ax.set_title(title, fontsize=7)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        pages += 1
    return pages


def write_private_origin_atlas(
    output_pdf: Path,
    metadata: pd.DataFrame,
    raw_patch_dir: Path,
    origin_inventory: pd.DataFrame | None,
) -> int:
    pages = 0
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_pdf) as pdf:
        fig = plt.figure(figsize=PAGE_A4_LANDSCAPE)
        fig.text(0.05, 0.72, "Private Origin Atlas", fontsize=24, fontweight="bold", va="top")
        fig.text(0.05, 0.64, "Lab-only document. Contains SAB WSI images and visual patch-origin relationships.", fontsize=12, va="top")
        fig.text(0.05, 0.56, "Each origin_audit_id page shows the SAB WSI, recovered patch coordinates, and all linked patch thumbnails.", fontsize=10, va="top")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        pages += 1
        for origin_id in metadata["origin_audit_id"].dropna().astype(str).drop_duplicates().sort_values():
            add_private_origin_atlas_page(pdf, origin_id, metadata, raw_patch_dir)
            pages += 1
        pages += add_patchless_ndb_contact_pages(pdf, origin_inventory)
    return pages


def write_pdf_report(
    output_pdf: Path,
    master: pd.DataFrame,
    origins: pd.DataFrame,
    metadata: pd.DataFrame,
    pairs: pd.DataFrame,
    raw_patch_dir: Path,
    origin_image_dir: Path,
    audit_summary: dict,
    max_examples_per_status: int,
    logo_path: Path,
    origin_inventory: pd.DataFrame | None,
) -> int:
    pages = 0
    with PdfPages(output_pdf) as pdf:
        add_cover_page(pdf, logo_path, audit_summary, origins)
        add_dataset_definitions_page(pdf, logo_path)
        add_key_findings_page(pdf, master, origins, pairs, audit_summary, origin_inventory, logo_path)
        add_status_dictionary_page(pdf, logo_path)
        add_counts_page(pdf, master, logo_path)
        add_label_crosstab_page(pdf, master, logo_path)
        add_spatial_similarity_page(pdf, pairs, logo_path)
        add_limitations_page(pdf, logo_path)
        pages += 8
    return pages


def run_dataset_alignment_report(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = Path(args.sab_audit_dir)
    audit_summary_path = audit_dir / "audit_summary.json"
    audit_summary = json.loads(audit_summary_path.read_text()) if audit_summary_path.exists() else {}

    master = build_source_alignment_master(audit_dir)
    master, private_crosswalk = attach_public_origin_ids(master)
    origins = build_origin_patch_composition(master)
    recovered_coordinates = pd.read_csv(args.recovered_coordinates)
    origin_inventory = pd.read_csv(args.origin_inventory) if args.origin_inventory and Path(args.origin_inventory).exists() else None
    accepted_with_coords, pairs = build_patch_pair_similarity(
        master,
        recovered_coordinates,
        args.similarity_threshold,
        args.color_delta_threshold,
    )

    private_dir = output_dir / PRIVATE_OUTPUT_DIRNAME
    private_dir.mkdir(parents=True, exist_ok=True)
    private_crosswalk.to_csv(private_dir / "origin_audit_private_crosswalk.csv", index=False)

    public_release_table(master).to_csv(output_dir / "source_alignment_master.csv", index=False)
    public_release_table(origins).to_csv(output_dir / "origin_patch_composition.csv", index=False)
    public_release_table(accepted_with_coords).to_csv(output_dir / "patch_coordinate_status.csv", index=False)
    public_release_table(pairs).to_csv(output_dir / "patch_spatial_feature_similarity.csv", index=False)
    review = master[master["dataset_use_status"] != "source_convergent"].copy()
    public_release_table(review).to_csv(output_dir / "review_needed_cases.csv", index=False)
    write_count_csvs(master, origins, accepted_with_coords, pairs, output_dir)

    output_pdf = output_dir / args.output_pdf
    pages = write_pdf_report(
        output_pdf,
        master,
        origins,
        accepted_with_coords,
        pairs,
        args.raw_patch_dir,
        args.origin_image_dir,
        audit_summary,
        args.max_examples_per_status,
        args.logo,
        origin_inventory,
    )
    private_atlas = private_dir / "private_origin_atlas.pdf"
    if args.skip_private_atlas and private_atlas.exists():
        atlas_pages = None
    else:
        atlas_pages = write_private_origin_atlas(
            private_atlas,
            accepted_with_coords,
            args.raw_patch_dir,
            origin_inventory,
        )
    summary = {
        "source_alignment_rows": int(len(master)),
        "sab_origins_with_patches": int(origins["origin_audit_id"].nunique()),
        "patches_with_recovered_coordinate_status": int(len(accepted_with_coords)),
        "patch_pairs": int(len(pairs)),
        "review_needed_cases": int(len(review)),
        "output_pdf": str(output_pdf),
        "private_origin_crosswalk": str(private_dir / "origin_audit_private_crosswalk.csv"),
        "private_origin_atlas": str(private_atlas),
        "pdf_pages": int(pages),
        "private_origin_atlas_pages": int(atlas_pages) if atlas_pages is not None else "not rebuilt",
    }
    (output_dir / "dataset_alignment_report_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def dataset_alignment_report_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a dataset source-alignment and patch-structure report.")
    parser.add_argument("--sab-audit-dir", type=Path, default=DEFAULT_SAB_AUDIT_DIR)
    parser.add_argument("--accepted-metadata", type=Path, default=DEFAULT_ACCEPTED_METADATA)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--origin-image-dir", type=Path, default=DEFAULT_ORIGIN_IMAGE_DIR)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS_PATH)
    parser.add_argument("--recovered-coordinates", type=Path, default=DEFAULT_RECOVERED_COORDINATES)
    parser.add_argument("--origin-inventory", type=Path, default=DEFAULT_ORIGIN_INVENTORY)
    parser.add_argument("--logo", type=Path, default=DEFAULT_LOGO_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-pdf", default="dataset_source_alignment_and_patch_structure_report.pdf")
    parser.add_argument("--similarity-threshold", type=float, default=0.995)
    parser.add_argument("--color-delta-threshold", type=float, default=6.0)
    parser.add_argument("--max-examples-per-status", type=int, default=3)
    parser.add_argument("--skip-private-atlas", action="store_true", help="Rebuild public tables/PDF without regenerating the image-heavy private atlas if it already exists.")
    return parser
