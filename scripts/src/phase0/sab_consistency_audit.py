import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src.phase0.recovery_audit import (
    DEFAULT_ACCEPTED_METADATA,
    DEFAULT_ORIGIN_IMAGE_DIR,
    DEFAULT_ORIGIN_METADATA,
    DEFAULT_RAW_PATCH_DIR,
    normalized_origin_id,
    patch_number,
)


DEFAULT_SAB_ROOT = Path("/Volumes/ssd/SAB")
DEFAULT_OUTPUT_DIR = Path("results/phase0/sab_consistency_audit")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

NORMALIZED_LABELS = {
    "oscc": "oscc",
    "oral squamous cell carcinoma": "oscc",
    "carcinoma": "oscc",
    "leukoplakia with dysplasia": "with_dysplasia",
    "with dysplasia": "with_dysplasia",
    "with_dysplasia": "with_dysplasia",
    "leukoplakia without dysplasia": "without_dysplasia",
    "without dysplasia": "without_dysplasia",
    "no_dysplasia": "without_dysplasia",
    "without_dysplasia": "without_dysplasia",
}

SAB_ORIGIN_FOLDER_LABELS = {
    "benigno": "without_dysplasia",
    "carcinoma": "oscc",
    "leucoplasia": "broad_leukoplakia_unknown_dysplasia",
}

SAB_SPLIT_LABELS = {
    "carcinoma": "oscc",
    "no_dysplasia": "without_dysplasia",
    "with_dysplasia": "with_dysplasia",
}

SEVERITY_ORDER = {
    "without_dysplasia": 0,
    "with_dysplasia": 1,
    "oscc": 2,
}


def image_hash_and_size(path: Path) -> tuple[str, int, int]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        array = np.asarray(rgb)
        return hashlib.sha256(array.tobytes()).hexdigest(), rgb.size[0], rgb.size[1]


def normalize_label(value) -> str:
    if pd.isna(value):
        return "unknown"
    text = str(value).strip().lower()
    return NORMALIZED_LABELS.get(text, "unknown")


def sab_origin_folder_label(folder) -> str:
    if pd.isna(folder):
        return "unknown"
    return SAB_ORIGIN_FOLDER_LABELS.get(str(folder).strip().lower(), "unknown")


def sab_split_label(folder) -> str:
    if pd.isna(folder):
        return "unknown"
    return SAB_SPLIT_LABELS.get(str(folder).strip().lower(), "unknown")


def case_prefix(origin_image_id) -> str:
    if pd.isna(origin_image_id):
        return ""
    return str(origin_image_id).split("_", 1)[0]


def parse_sab_patch_stem(stem: str) -> tuple[str, int | None]:
    if "_" not in stem:
        return stem, None
    origin_id, patch_text = stem.rsplit("_", 1)
    try:
        return origin_id, int(patch_text)
    except ValueError:
        return origin_id, None


def inventory_current_origins(origin_image_dir: Path, origin_metadata_path: Path) -> pd.DataFrame:
    metadata = pd.read_csv(origin_metadata_path).copy()
    metadata["ndb_origin_id"] = metadata["path"].map(normalized_origin_id)
    metadata["current_origin_label_normalized"] = metadata["diagnosis"].map(normalize_label)
    metadata = metadata.set_index("ndb_origin_id", drop=False)
    rows = []
    for path in sorted(Path(origin_image_dir).glob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not path.stem.isdigit():
            continue
        origin_id = normalized_origin_id(path.name)
        digest, width, height = image_hash_and_size(path)
        row = {
            "ndb_origin_id": origin_id,
            "ndb_origin_path": str(path),
            "origin_pixel_hash": digest,
            "ndb_origin_width": width,
            "ndb_origin_height": height,
            "current_origin_diagnosis": "",
            "current_origin_taskiv": "",
            "current_origin_label_normalized": "unknown",
            "patient_id": "",
            "lesion_id": "",
            "public_id": "",
        }
        if origin_id in metadata.index:
            meta = metadata.loc[origin_id]
            for source, target in [
                ("diagnosis", "current_origin_diagnosis"),
                ("TaskIV", "current_origin_taskiv"),
                ("current_origin_label_normalized", "current_origin_label_normalized"),
                ("patient_id", "patient_id"),
                ("lesion_id", "lesion_id"),
                ("public_id", "public_id"),
            ]:
                row[target] = meta.get(source, "")
        rows.append(row)
    return pd.DataFrame(rows)


def inventory_sab_origins(sab_root: Path) -> pd.DataFrame:
    rows = []
    for folder in ["benigno", "carcinoma", "leucoplasia"]:
        for path in sorted((Path(sab_root) / folder).glob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            digest, width, height = image_hash_and_size(path)
            rows.append({
                "sab_origin_image_id": path.stem,
                "sab_case_prefix": case_prefix(path.stem),
                "sab_origin_folder": folder,
                "sab_origin_folder_label_normalized": sab_origin_folder_label(folder),
                "sab_origin_path": str(path),
                "origin_pixel_hash": digest,
                "sab_origin_width": width,
                "sab_origin_height": height,
            })
    return pd.DataFrame(rows)


def inventory_current_patches(raw_patch_dir: Path, accepted_metadata_path: Path) -> pd.DataFrame:
    accepted = pd.read_csv(accepted_metadata_path).copy()
    accepted["ndb_patch"] = accepted["patch"].astype(str)
    accepted["ndb_origin_id_from_patch_csv"] = accepted["origin"].map(normalized_origin_id)
    accepted["current_patch_label_normalized"] = accepted["diagnosis"].map(normalize_label)
    accepted = accepted.set_index("ndb_patch", drop=False)
    rows = []
    for path in sorted(Path(raw_patch_dir).glob("p*.png")):
        number = patch_number(path.stem)
        if number is None:
            continue
        digest, width, height = image_hash_and_size(path)
        row = {
            "ndb_patch": path.stem,
            "ndb_patch_number": number,
            "ndb_patch_path": str(path),
            "patch_pixel_hash": digest,
            "ndb_patch_width": width,
            "ndb_patch_height": height,
            "current_patch_metadata_found": path.stem in accepted.index,
            "current_patch_diagnosis": "",
            "current_patch_taskiv": "",
            "current_patch_label_normalized": "unknown",
            "ndb_origin_id_from_patch_csv": "",
        }
        if path.stem in accepted.index:
            meta = accepted.loc[path.stem]
            row["current_patch_diagnosis"] = meta.get("diagnosis", "")
            row["current_patch_taskiv"] = meta.get("TaskIV", "")
            row["current_patch_label_normalized"] = meta.get("current_patch_label_normalized", "unknown")
            row["ndb_origin_id_from_patch_csv"] = meta.get("ndb_origin_id_from_patch_csv", "")
        rows.append(row)
    return pd.DataFrame(rows)


def inventory_sab_patches(sab_root: Path, sab_origins: pd.DataFrame) -> pd.DataFrame:
    origin_lookup = sab_origins.set_index("sab_origin_image_id").to_dict("index")
    rows = []
    for path in sorted((Path(sab_root) / "data_train_test").glob("*/*/*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(sab_root)
        split = relative.parts[1]
        split_class = relative.parts[2]
        origin_id, sab_patch_index = parse_sab_patch_stem(path.stem)
        origin = origin_lookup.get(origin_id, {})
        digest, width, height = image_hash_and_size(path)
        rows.append({
            "sab_patch_filename": path.name,
            "sab_patch_path": str(path),
            "sab_split": split,
            "sab_split_class": split_class,
            "sab_split_label_normalized": sab_split_label(split_class),
            "sab_origin_image_id": origin_id,
            "sab_case_prefix": case_prefix(origin_id),
            "sab_patch_index_zero_based": sab_patch_index,
            "sab_origin_folder": origin.get("sab_origin_folder", ""),
            "sab_origin_folder_label_normalized": origin.get("sab_origin_folder_label_normalized", "unknown"),
            "sab_origin_path": origin.get("sab_origin_path", ""),
            "patch_pixel_hash": digest,
            "sab_patch_width": width,
            "sab_patch_height": height,
        })
    return pd.DataFrame(rows)


def origin_folder_vs_metadata_status(current_label: str, sab_folder_label: str, exact_match: bool) -> str:
    if not exact_match:
        return "no_current_origin_match"
    if sab_folder_label == "broad_leukoplakia_unknown_dysplasia":
        return "broad_folder_only"
    if current_label == "unknown" or sab_folder_label == "unknown":
        return "no_current_origin_match"
    return "agrees" if current_label == sab_folder_label else "disagrees"


def patch_csv_vs_sab_split_status(current_patch_found: bool, current_label: str, sab_match_found: bool, sab_label: str) -> str:
    if not current_patch_found:
        return "missing_current_patch_metadata"
    if not sab_match_found:
        return "no_sab_patch_match"
    if current_label == "unknown" or sab_label == "unknown":
        return "disagrees"
    return "agrees" if current_label == sab_label else "disagrees"


def source_convergence_status(origin_status: str, patch_status: str) -> str:
    origin_disagrees = origin_status == "disagrees"
    patch_disagrees = patch_status == "disagrees"
    insufficient = origin_status == "no_current_origin_match" or patch_status in {
        "no_sab_patch_match",
        "missing_current_patch_metadata",
    }
    if origin_disagrees and patch_disagrees:
        return "origin_and_patch_sources_disagree"
    if origin_disagrees:
        return "origin_sources_disagree"
    if patch_disagrees:
        return "patch_sources_disagree"
    if insufficient:
        return "insufficient_metadata"
    return "all_available_sources_agree"


def severity_direction(patch_label: str, origin_label: str) -> str:
    if origin_label == "broad_leukoplakia_unknown_dysplasia":
        return "broad_origin_uncertain"
    if patch_label not in SEVERITY_ORDER or origin_label not in SEVERITY_ORDER:
        return "unknown"
    diff = SEVERITY_ORDER[patch_label] - SEVERITY_ORDER[origin_label]
    if diff == 0:
        return "same"
    if diff > 0:
        return "patch_more_severe_than_origin"
    return "patch_less_severe_than_origin"


def patch_vs_origin_plausibility(patch_label: str, origin_label: str) -> str:
    if patch_label == "unknown" or origin_label == "unknown":
        return "unknown_origin_metadata"
    if origin_label == "broad_leukoplakia_unknown_dysplasia":
        return "broad_origin_requires_review" if patch_label == "oscc" else "plausible"
    if origin_label in {"without_dysplasia", "with_dysplasia"}:
        if patch_label == "oscc":
            return "impossible_or_high_conflict"
        if patch_label != origin_label:
            return "plausible_but_origin_patch_disagreement"
        return "plausible"
    if origin_label == "oscc":
        return "plausible"
    return "unknown_origin_metadata"


def review_priority(origin_status: str, patch_status: str, plausibility: str) -> str:
    if plausibility == "impossible_or_high_conflict":
        return "critical"
    if patch_status == "disagrees" or origin_status == "disagrees":
        return "high"
    if plausibility in {"plausible_but_origin_patch_disagreement", "broad_origin_requires_review"}:
        return "medium"
    return "low"


def best_origin_label(row) -> str:
    current = row.get("current_origin_label_normalized", "unknown")
    if current != "unknown":
        return current
    sab = row.get("sab_origin_folder_label_normalized", "unknown")
    if sab:
        return sab
    return "unknown"


def best_patch_label(row) -> str:
    current = row.get("current_patch_label_normalized", "unknown")
    if current != "unknown":
        return current
    sab = row.get("sab_split_label_normalized", "unknown")
    if sab:
        return sab
    return "unknown"


def has_known_label(value) -> bool:
    return isinstance(value, str) and value not in {"", "unknown"}


def build_origin_source_convergence(current_origins: pd.DataFrame, sab_origins: pd.DataFrame) -> pd.DataFrame:
    table = current_origins.merge(
        sab_origins,
        on="origin_pixel_hash",
        how="left",
        indicator=True,
        suffixes=("", "_sab"),
    )
    table["origin_exact_match_found"] = table["_merge"].eq("both")
    table = table.drop(columns=["_merge"])
    table["origin_folder_vs_current_metadata_status"] = table.apply(
        lambda row: origin_folder_vs_metadata_status(
            row.get("current_origin_label_normalized", "unknown"),
            row.get("sab_origin_folder_label_normalized", "unknown"),
            bool(row.get("origin_exact_match_found", False)),
        ),
        axis=1,
    )
    table["source_convergence_status"] = table["origin_folder_vs_current_metadata_status"].map({
        "agrees": "all_available_sources_agree",
        "broad_folder_only": "all_available_sources_agree",
        "disagrees": "origin_sources_disagree",
        "no_current_origin_match": "insufficient_metadata",
    })
    return table


def build_patch_source_convergence(
    current_patches: pd.DataFrame,
    sab_patches: pd.DataFrame,
    origin_source: pd.DataFrame,
    current_origins: pd.DataFrame,
) -> pd.DataFrame:
    sab_match_counts = sab_patches.groupby("patch_pixel_hash").size().rename("sab_duplicate_patch_hash_match_count")
    sab_first = (
        sab_patches.sort_values(["patch_pixel_hash", "sab_patch_path"])
        .drop_duplicates("patch_pixel_hash", keep="first")
        .copy()
    )
    patch = current_patches.merge(
        sab_first,
        on="patch_pixel_hash",
        how="left",
        indicator=True,
        suffixes=("", "_sab"),
    )
    patch = patch.merge(sab_match_counts, on="patch_pixel_hash", how="left")
    patch["sab_duplicate_patch_hash_match_count"] = patch["sab_duplicate_patch_hash_match_count"].fillna(0).astype(int)
    patch["patch_exact_match_found"] = patch["_merge"].eq("both")
    patch = patch.drop(columns=["_merge"])

    sab_origin_to_current = origin_source[[
        "sab_origin_image_id",
        "ndb_origin_id",
        "ndb_origin_path",
        "current_origin_diagnosis",
        "current_origin_label_normalized",
        "origin_exact_match_found",
        "origin_folder_vs_current_metadata_status",
    ]].rename(columns={
        "ndb_origin_id": "ndb_origin_id_from_sab_origin_exact_match",
        "ndb_origin_path": "ndb_origin_path_from_sab_origin_exact_match",
        "current_origin_diagnosis": "current_origin_diagnosis_from_sab_origin_exact_match",
        "current_origin_label_normalized": "current_origin_label_from_sab_origin_exact_match",
        "origin_exact_match_found": "sab_origin_exact_current_ndb_match_found",
    })
    patch = patch.merge(sab_origin_to_current, on="sab_origin_image_id", how="left")

    patch_origin_meta = current_origins[[
        "ndb_origin_id",
        "current_origin_diagnosis",
        "current_origin_label_normalized",
    ]].rename(columns={
        "ndb_origin_id": "ndb_origin_id_from_patch_csv",
        "current_origin_diagnosis": "current_origin_diagnosis_from_patch_csv",
        "current_origin_label_normalized": "current_origin_label_from_patch_csv",
    })
    patch = patch.merge(patch_origin_meta, on="ndb_origin_id_from_patch_csv", how="left")

    patch["patch_csv_vs_sab_split_status"] = patch.apply(
        lambda row: patch_csv_vs_sab_split_status(
            bool(row.get("current_patch_metadata_found", False)),
            row.get("current_patch_label_normalized", "unknown"),
            bool(row.get("patch_exact_match_found", False)),
            row.get("sab_split_label_normalized", "unknown"),
        ),
        axis=1,
    )
    return patch


def build_patch_origin_plausibility(patch_source: pd.DataFrame) -> pd.DataFrame:
    table = patch_source.copy()
    table["best_available_origin_label_normalized"] = table.apply(
        lambda row: row.get("current_origin_label_from_patch_csv", "unknown")
        if has_known_label(row.get("current_origin_label_from_patch_csv", "unknown"))
        else (
            row.get("current_origin_label_from_sab_origin_exact_match", "unknown")
            if has_known_label(row.get("current_origin_label_from_sab_origin_exact_match", "unknown"))
            else row.get("sab_origin_folder_label_normalized", "unknown")
        ),
        axis=1,
    )
    table["best_available_patch_label_normalized"] = table.apply(best_patch_label, axis=1)
    table["patch_vs_origin_plausibility_status"] = table.apply(
        lambda row: patch_vs_origin_plausibility(
            row["best_available_patch_label_normalized"],
            row["best_available_origin_label_normalized"],
        ),
        axis=1,
    )
    table["severity_direction"] = table.apply(
        lambda row: severity_direction(
            row["best_available_patch_label_normalized"],
            row["best_available_origin_label_normalized"],
        ),
        axis=1,
    )
    table["origin_folder_vs_current_metadata_status"] = table["origin_folder_vs_current_metadata_status"].fillna(
        "no_current_origin_match"
    )
    table["source_convergence_status"] = table.apply(
        lambda row: source_convergence_status(
            row.get("origin_folder_vs_current_metadata_status", "no_current_origin_match"),
            row.get("patch_csv_vs_sab_split_status", "no_sab_patch_match"),
        ),
        axis=1,
    )
    table["review_priority"] = table.apply(
        lambda row: review_priority(
            row.get("origin_folder_vs_current_metadata_status", "no_current_origin_match"),
            row.get("patch_csv_vs_sab_split_status", "no_sab_patch_match"),
            row.get("patch_vs_origin_plausibility_status", "unknown_origin_metadata"),
        ),
        axis=1,
    )
    return table


def build_case_prefix_summary(patch_origin: pd.DataFrame) -> pd.DataFrame:
    grouped = patch_origin.copy()
    grouped["sab_case_prefix"] = grouped["sab_case_prefix"].fillna("")
    rows = []
    for prefix, group in grouped[grouped["sab_case_prefix"] != ""].groupby("sab_case_prefix"):
        rows.append({
            "case_prefix": prefix,
            "n_origin_images": int(group["sab_origin_image_id"].nunique()),
            "n_patches": int(group["ndb_patch"].nunique()),
            "origin_diagnoses_seen": "|".join(sorted(set(group["best_available_origin_label_normalized"].dropna()))),
            "patch_labels_seen": "|".join(sorted(set(group["best_available_patch_label_normalized"].dropna()))),
            "n_critical_conflicts": int((group["review_priority"] == "critical").sum()),
            "n_high_conflicts": int((group["review_priority"] == "high").sum()),
            "n_medium_conflicts": int((group["review_priority"] == "medium").sum()),
        })
    return pd.DataFrame(rows).sort_values(
        ["n_critical_conflicts", "n_high_conflicts", "n_medium_conflicts", "n_patches"],
        ascending=[False, False, False, False],
    )


def audit_summary(
    origin_source: pd.DataFrame,
    patch_source: pd.DataFrame,
    patch_origin: pd.DataFrame,
    case_summary: pd.DataFrame,
) -> dict:
    return {
        "current_origin_images": int(len(origin_source)),
        "current_origin_images_exact_matched_to_sab": int(origin_source["origin_exact_match_found"].sum()),
        "current_origin_images_unmatched_to_sab": int((~origin_source["origin_exact_match_found"]).sum()),
        "origin_folder_vs_current_metadata_status_counts": origin_source["origin_folder_vs_current_metadata_status"].value_counts(dropna=False).to_dict(),
        "current_patch_images": int(len(patch_source)),
        "current_patch_images_exact_matched_to_sab": int(patch_source["patch_exact_match_found"].sum()),
        "current_patch_images_unmatched_to_sab": int((~patch_source["patch_exact_match_found"]).sum()),
        "patch_csv_vs_sab_split_status_counts": patch_source["patch_csv_vs_sab_split_status"].value_counts(dropna=False).to_dict(),
        "patch_vs_origin_plausibility_status_counts": patch_origin["patch_vs_origin_plausibility_status"].value_counts(dropna=False).to_dict(),
        "review_priority_counts": patch_origin["review_priority"].value_counts(dropna=False).to_dict(),
        "case_prefixes": int(len(case_summary)),
    }


def run_sab_consistency_audit(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_origins = inventory_current_origins(args.origin_image_dir, args.origin_metadata)
    sab_origins = inventory_sab_origins(args.sab_root)
    current_patches = inventory_current_patches(args.raw_patch_dir, args.accepted_metadata)
    sab_patches = inventory_sab_patches(args.sab_root, sab_origins)

    origin_source = build_origin_source_convergence(current_origins, sab_origins)
    patch_source = build_patch_source_convergence(current_patches, sab_patches, origin_source, current_origins)
    patch_origin = build_patch_origin_plausibility(patch_source)
    case_summary = build_case_prefix_summary(patch_origin)
    summary = audit_summary(origin_source, patch_source, patch_origin, case_summary)

    origin_source.to_csv(output_dir / "origin_source_convergence.csv", index=False)
    patch_source.to_csv(output_dir / "patch_source_convergence.csv", index=False)
    patch_origin.to_csv(output_dir / "patch_origin_plausibility_audit.csv", index=False)
    case_summary.to_csv(output_dir / "case_prefix_plausibility_summary.csv", index=False)
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def sab_consistency_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit SAB/current NDB source convergence and patch-origin plausibility.")
    parser.add_argument("--sab-root", type=Path, default=DEFAULT_SAB_ROOT)
    parser.add_argument("--raw-patch-dir", type=Path, default=DEFAULT_RAW_PATCH_DIR)
    parser.add_argument("--origin-image-dir", type=Path, default=DEFAULT_ORIGIN_IMAGE_DIR)
    parser.add_argument("--accepted-metadata", type=Path, default=DEFAULT_ACCEPTED_METADATA)
    parser.add_argument("--origin-metadata", type=Path, default=DEFAULT_ORIGIN_METADATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser
