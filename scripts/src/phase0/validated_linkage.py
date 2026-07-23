import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ALIGNMENT_DIR = Path("results/phase0/dataset_alignment_report")
DEFAULT_OUTPUT_DIR = Path("results/phase0/validated_linkage")
DEFAULT_COORDINATES = DEFAULT_ALIGNMENT_DIR / "patch_coordinate_status.csv"
DEFAULT_PRIVATE_CROSSWALK = DEFAULT_ALIGNMENT_DIR / "private_lab_crosswalks/origin_validation_private_crosswalk.csv"
DEFAULT_PAIR_SIMILARITY = DEFAULT_ALIGNMENT_DIR / "patch_spatial_feature_similarity.csv"
DEFAULT_COMPLETE_NDB_LABELS = Path("data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv")
DEFAULT_SAB_PARSED_FOLDERS = Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_folders.csv")
DEFAULT_SAB_PARSED_TEST = Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_test.csv")

PRIVATE_COLUMNS = {
    "sab_origin_image_id",
    "sab_case_prefix",
    "sab_origin_path",
}


def normalize_label(value) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    text = str(value).strip().lower().replace("-", " ").replace("_", " ")
    if not text or text in {"nan", "none", "unknown"}:
        return "unknown"
    if "oscc" in text or "carcinoma" in text:
        return "oscc"
    if "with dysplasia" in text or text == "dysplasia" or "dysplasia" in text and "without" not in text and "no dysplasia" not in text:
        return "with_dysplasia"
    if "without dysplasia" in text or "no dysplasia" in text or "benigno" in text:
        return "without_dysplasia"
    return text.replace(" ", "_")


def boolish(value) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def public_wsi_id(origin_validation_id: str) -> str:
    suffix = str(origin_validation_id).replace("origin_validation_", "")
    return f"validated_wsi_{suffix}"


def public_ndb_wsi_id(value) -> str:
    return f"public_ndb_wsi_{format_id(value).zfill(4)}"


def sab_only_wsi_id(origin_validation_id: str) -> str:
    suffix = str(origin_validation_id).replace("origin_validation_", "")
    return f"sab_only_wsi_{suffix}"


def load_complete_ndb_patch_labels(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["ndb_patch", "ndb_ufes_patch_label_from_complete_source", "ndb_ufes_patch_label_source"])
    table = pd.read_csv(path)
    required = {"image_name", "class"}
    if not required.issubset(table.columns):
        return pd.DataFrame(columns=["ndb_patch", "ndb_ufes_patch_label_from_complete_source", "ndb_ufes_patch_label_source"])
    labels = table[["image_name", "class"]].copy()
    labels["ndb_patch"] = labels["image_name"].astype(str).str.replace(".png", "", regex=False)
    labels["ndb_ufes_patch_label_from_complete_source"] = labels["class"].map(normalize_label)
    labels["ndb_ufes_patch_label_source"] = path.name
    return labels[["ndb_patch", "ndb_ufes_patch_label_from_complete_source", "ndb_ufes_patch_label_source"]].drop_duplicates("ndb_patch")


def load_complete_sab_patch_labels(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        table = pd.read_csv(path)
        if not {"path", "lesion"}.issubset(table.columns):
            continue
        labels = table[["path", "lesion"]].copy()
        labels["ndb_patch"] = labels["path"].astype(str).str.replace(".png", "", regex=False)
        labels["sab_patch_label_from_complete_source"] = labels["lesion"].map(normalize_label)
        labels["sab_patch_label_source"] = path.name
        frames.append(labels[["ndb_patch", "sab_patch_label_from_complete_source", "sab_patch_label_source"]])
    if not frames:
        return pd.DataFrame(columns=["ndb_patch", "sab_patch_label_from_complete_source", "sab_patch_label_source"])
    return pd.concat(frames, ignore_index=True).drop_duplicates("ndb_patch")


def label_agreement_status(ndb_label: str, sab_label: str, ndb_status: str) -> str:
    if ndb_status != "available":
        return "patch_label_not_available"
    if sab_label in {"", "unknown"}:
        return "sab_label_not_available"
    return "agrees" if ndb_label == sab_label else "disagrees"


def linkage_evidence_level(row: pd.Series) -> str:
    if row["pixel_containment_status"] != "exact_pixel_match":
        return "requires_manual_review"
    conflict_statuses = {
        "source_disagreement",
        "biologically_implausible_or_high_conflict",
    }
    if (
        row.get("dataset_use_status") in conflict_statuses
        or row.get("patch_label_agreement_status") == "disagrees"
        or row.get("patch_vs_origin_plausibility_status") == "impossible_or_high_conflict"
    ):
        return "validated_exact_with_metadata_conflict"
    if boolish(row.get("sab_origin_exact_current_ndb_match_found")):
        return "validated_exact_public_wsi"
    return "validated_exact_sab_only"


def reviewer_status(evidence_level: str) -> str:
    if evidence_level == "requires_manual_review":
        return "manual_review_required"
    if evidence_level == "validated_exact_with_metadata_conflict":
        return "expert_metadata_review_recommended"
    return "auto_validated_by_pixel_containment"


def linkage_notes(row: pd.Series) -> str:
    notes = []
    if row["linkage_evidence_level"] == "validated_exact_sab_only":
        notes.append("SAB WSI contains patch exactly, but no exact public NDB-UFES WSI match was found.")
    if row["linkage_evidence_level"] == "validated_exact_with_metadata_conflict":
        notes.append("Patch-to-WSI linkage is exact, but label or metadata sources disagree.")
    if row["linkage_evidence_level"] == "requires_manual_review":
        notes.append("Exact pixel containment was not available.")
    if row.get("current_metadata_vs_complete_patch_label_status") == "disagrees":
        notes.append("Current reconstructed metadata label differs from the complete parsed patch label CSV.")
    return " ".join(notes)


def build_validated_patch_linkage(
    coordinates: pd.DataFrame,
    private_crosswalk: pd.DataFrame,
    complete_ndb_labels: pd.DataFrame | None = None,
    complete_sab_labels: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    table = coordinates.copy()
    if complete_ndb_labels is not None and not complete_ndb_labels.empty:
        table = table.merge(complete_ndb_labels, on="ndb_patch", how="left")
    else:
        table["ndb_ufes_patch_label_from_complete_source"] = np.nan
        table["ndb_ufes_patch_label_source"] = np.nan
    if complete_sab_labels is not None and not complete_sab_labels.empty:
        table = table.merge(complete_sab_labels, on="ndb_patch", how="left")
    else:
        table["sab_patch_label_from_complete_source"] = np.nan
        table["sab_patch_label_source"] = np.nan

    complete_patch_label = table["sab_patch_label_from_complete_source"].fillna(table["ndb_ufes_patch_label_from_complete_source"])
    table["ndb_ufes_patch_label"] = complete_patch_label.fillna(table["current_patch_label_normalized"].map(normalize_label))
    table.loc[table["ndb_ufes_patch_label"].isin(["unknown", "missing_from_accepted_metadata"]), "ndb_ufes_patch_label"] = "unknown"
    table["ndb_ufes_patch_label_status"] = np.where(table["ndb_ufes_patch_label"] == "unknown", "not_available", "available")
    table["ndb_ufes_patch_label_source"] = np.where(
        table["sab_patch_label_from_complete_source"].notna(),
        table["sab_patch_label_source"],
        table["ndb_ufes_patch_label_source"],
    )
    table["sab_patch_label"] = table["sab_patch_label_from_complete_source"].fillna(table["sab_patch_split_label"].map(normalize_label))
    table["sab_patch_label_status"] = np.where(table["sab_patch_label"].isin(["", "unknown"]), "not_available", "available")
    current_metadata_label = table["current_patch_label_normalized"].map(normalize_label)
    table["current_reconstructed_patch_label"] = current_metadata_label
    table["current_metadata_vs_complete_patch_label_status"] = np.select(
        [
            current_metadata_label.eq("unknown"),
            table["ndb_ufes_patch_label"].eq("unknown"),
            current_metadata_label.eq(table["ndb_ufes_patch_label"]),
        ],
        [
            "current_metadata_missing_patch",
            "complete_patch_label_missing",
            "agrees",
        ],
        default="disagrees",
    )
    table["patch_label_agreement_status"] = table.apply(
        lambda row: label_agreement_status(row["ndb_ufes_patch_label"], row["sab_patch_label"], row["ndb_ufes_patch_label_status"]),
        axis=1,
    )
    has_public_wsi_match = table["ndb_origin_id_from_sab_origin_exact_match"].notna()
    table["validated_wsi_id"] = np.where(
        has_public_wsi_match,
        table["ndb_origin_id_from_sab_origin_exact_match"].map(public_ndb_wsi_id),
        table["origin_validation_id"].map(sab_only_wsi_id),
    )
    table["public_wsi_pseudonym"] = table["validated_wsi_id"]
    table["final_validated_wsi_id"] = table["validated_wsi_id"]
    table["previous_reconstructed_ndb_origin_id"] = table["ndb_origin_id_from_patch_csv"]
    table["previous_public_ndb_wsi_match"] = table["ndb_origin_id_from_sab_origin_exact_match"]
    table["pixel_containment_status"] = table["coordinate_recovery_status"].fillna("missing")
    table["x"] = table["recovered_x"]
    table["y"] = table["recovered_y"]
    table["width"] = table["recovered_width"]
    table["height"] = table["recovered_height"]
    table["linkage_evidence_level"] = table.apply(linkage_evidence_level, axis=1)
    table["reviewer_status"] = table["linkage_evidence_level"].map(reviewer_status)
    table["notes"] = table.apply(linkage_notes, axis=1)

    private = table.merge(private_crosswalk, on="origin_validation_id", how="left", suffixes=("", "_private"))
    columns = [
        "ndb_patch",
        "ndb_ufes_patch_label",
        "ndb_ufes_patch_label_status",
        "sab_patch_label",
        "sab_patch_label_status",
        "patch_label_agreement_status",
        "current_reconstructed_patch_label",
        "current_metadata_vs_complete_patch_label_status",
        "final_validated_wsi_id",
        "public_wsi_pseudonym",
        "previous_reconstructed_ndb_origin_id",
        "previous_public_ndb_wsi_match",
        "pixel_containment_status",
        "x",
        "y",
        "width",
        "height",
        "linkage_evidence_level",
        "reviewer_status",
        "notes",
        "origin_validation_id",
        "sab_origin_folder",
        "sab_origin_folder_label_normalized",
        "current_origin_label_from_patch_csv",
        "current_origin_label_from_sab_origin_exact_match",
        "ndb_ufes_patch_label_source",
        "sab_patch_label_source",
        "dataset_use_status",
        "patch_vs_origin_plausibility_status",
        "coordinate_status",
        "sab_origin_width",
        "sab_origin_height",
    ]
    private_columns = columns + [
        "sab_origin_image_id",
        "sab_case_prefix",
        "sab_origin_path",
    ]
    public = private[[column for column in columns if column in private.columns]].copy()
    private = private[[column for column in private_columns if column in private.columns]].copy()
    return public.sort_values("ndb_patch"), private.sort_values("ndb_patch")


def build_wsi_inventory(validated_private: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for wsi_id, group in validated_private.groupby("final_validated_wsi_id"):
        has_public_match = group["previous_public_ndb_wsi_match"].notna().any()
        wsi_source = "both" if has_public_match else "SAB-only recovered WSI"
        ndb_labels = group["ndb_ufes_patch_label"].fillna("unknown").astype(str).value_counts().to_dict()
        sab_labels = group["sab_patch_label"].fillna("unknown").astype(str).value_counts().to_dict()
        evidence_counts = group["linkage_evidence_level"].fillna("unknown").astype(str).value_counts().to_dict()
        rows.append({
            "final_validated_wsi_id": wsi_id,
            "public_wsi_pseudonym": group["public_wsi_pseudonym"].iloc[0],
            "n_patches": int(len(group)),
            "wsi_source": wsi_source,
            "wsi_label_from_ndb_ufes": first_non_empty(group.get("current_origin_label_from_sab_origin_exact_match")),
            "wsi_label_from_sab": first_non_empty(group.get("sab_origin_folder_label_normalized")),
            "previous_reconstructed_ndb_origin_ids": "|".join(sorted(set(format_id(value) for value in group["previous_reconstructed_ndb_origin_id"].dropna()))),
            "previous_public_ndb_wsi_matches": "|".join(sorted(set(format_id(value) for value in group["previous_public_ndb_wsi_match"].dropna()))),
            "n_ndb_patch_oscc": int(ndb_labels.get("oscc", 0)),
            "n_ndb_patch_with_dysplasia": int(ndb_labels.get("with_dysplasia", 0)),
            "n_ndb_patch_without_dysplasia": int(ndb_labels.get("without_dysplasia", 0)),
            "n_ndb_patch_label_unavailable": int(ndb_labels.get("unknown", 0)),
            "n_sab_patch_oscc": int(sab_labels.get("oscc", 0)),
            "n_sab_patch_with_dysplasia": int(sab_labels.get("with_dysplasia", 0)),
            "n_sab_patch_without_dysplasia": int(sab_labels.get("without_dysplasia", 0)),
            "linkage_evidence_counts": json.dumps(evidence_counts, sort_keys=True),
            "requires_manual_review_count": int(evidence_counts.get("requires_manual_review", 0)),
            "metadata_conflict_count": int(evidence_counts.get("validated_exact_with_metadata_conflict", 0)),
        })
    inventory = pd.DataFrame(rows).sort_values(["requires_manual_review_count", "metadata_conflict_count", "n_patches"], ascending=[False, False, False])
    crosswalk = validated_private[[
        "public_wsi_pseudonym",
        "origin_validation_id",
        "sab_origin_image_id",
        "sab_case_prefix",
        "sab_origin_folder",
        "sab_origin_folder_label_normalized",
        "sab_origin_path",
        "previous_public_ndb_wsi_match",
    ]].drop_duplicates().sort_values("public_wsi_pseudonym")
    return inventory, crosswalk


def first_non_empty(series) -> str:
    if series is None:
        return ""
    for value in series:
        if value is not None and not pd.isna(value) and str(value).strip() and str(value) != "nan":
            return str(value)
    return ""


def format_id(value) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        numeric = float(value)
        if numeric.is_integer():
            return str(int(numeric))
    except (TypeError, ValueError):
        pass
    return str(value)


def build_patch_label_agreement(validated: pd.DataFrame) -> pd.DataFrame:
    return validated[[
        "ndb_patch",
        "ndb_ufes_patch_label",
        "ndb_ufes_patch_label_status",
        "sab_patch_label",
        "patch_label_agreement_status",
        "final_validated_wsi_id",
        "public_wsi_pseudonym",
    ]].rename(columns={"ndb_patch": "patch_id"}).sort_values("patch_id")


def build_validated_similarity(pairs: pd.DataFrame, validated: pd.DataFrame) -> pd.DataFrame:
    mapping = validated[["ndb_patch", "final_validated_wsi_id", "public_wsi_pseudonym"]].drop_duplicates()
    by_patch = mapping.set_index("ndb_patch")
    output = pairs.copy()
    output["final_validated_wsi_id"] = output["patch_a"].map(by_patch["final_validated_wsi_id"])
    output["public_wsi_pseudonym"] = output["patch_a"].map(by_patch["public_wsi_pseudonym"])
    keep = [
        "final_validated_wsi_id",
        "public_wsi_pseudonym",
        "patch_a",
        "patch_b",
        "iou",
        "visual_fingerprint_similarity",
        "lab_mean_delta",
        "coordinate_relation",
        "feature_relation",
        "pair_relation",
        "x_a",
        "y_a",
        "x2_a",
        "y2_a",
        "x_b",
        "y_b",
        "x2_b",
        "y2_b",
    ]
    return output[[column for column in keep if column in output.columns]].sort_values(["final_validated_wsi_id", "patch_a", "patch_b"])


def build_summary(validated: pd.DataFrame, inventory: pd.DataFrame, similarity: pd.DataFrame) -> dict:
    return {
        "patches": int(len(validated)),
        "validated_wsi_count": int(validated["final_validated_wsi_id"].nunique()),
        "patches_with_final_wsi_id": int(validated["final_validated_wsi_id"].notna().sum()),
        "patches_with_coordinates": int(validated[["x", "y", "width", "height"]].notna().all(axis=1).sum()),
        "patches_requiring_manual_review": int((validated["linkage_evidence_level"] == "requires_manual_review").sum()),
        "patches_with_metadata_conflict": int((validated["linkage_evidence_level"] == "validated_exact_with_metadata_conflict").sum()),
        "patches_with_unavailable_patch_label": int((validated["ndb_ufes_patch_label_status"] != "available").sum()),
        "patches_missing_from_current_reconstructed_metadata": int((validated["current_metadata_vs_complete_patch_label_status"] == "current_metadata_missing_patch").sum()),
        "patches_where_current_metadata_label_differs_from_complete_patch_label": int((validated["current_metadata_vs_complete_patch_label_status"] == "disagrees").sum()),
        "validated_wsi_with_public_ndb_match": int((inventory["wsi_source"] == "both").sum()),
        "validated_wsi_sab_only": int((inventory["wsi_source"] == "SAB-only recovered WSI").sum()),
        "same_wsi_patch_pairs": int(len(similarity)),
        "evidence_level_counts": validated["linkage_evidence_level"].value_counts().to_dict(),
        "label_agreement_counts": validated["patch_label_agreement_status"].value_counts().to_dict(),
    }


def run_validated_linkage(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    private_dir = output_dir / "private_lab_crosswalks"
    output_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    coordinates = pd.read_csv(args.coordinates)
    private_crosswalk = pd.read_csv(args.private_crosswalk)
    complete_ndb_labels = load_complete_ndb_patch_labels(args.complete_ndb_labels)
    pairs = pd.read_csv(args.pair_similarity)
    complete_sab_labels = load_complete_sab_patch_labels([args.sab_parsed_folders, args.sab_parsed_test])

    validated, validated_private = build_validated_patch_linkage(coordinates, private_crosswalk, complete_ndb_labels, complete_sab_labels)
    inventory, private_crosswalk_out = build_wsi_inventory(validated_private)
    label_agreement = build_patch_label_agreement(validated)
    similarity = build_validated_similarity(pairs, validated)
    summary = build_summary(validated, inventory, similarity)

    validated.to_csv(output_dir / "validated_patch_wsi_linkage.csv", index=False)
    inventory.to_csv(output_dir / "validated_wsi_inventory.csv", index=False)
    label_agreement.to_csv(output_dir / "validated_patch_label_agreement.csv", index=False)
    similarity.to_csv(output_dir / "validated_wsi_patch_similarity.csv", index=False)
    validated_private.to_csv(private_dir / "private_validated_patch_wsi_linkage.csv", index=False)
    private_crosswalk_out.to_csv(private_dir / "private_validated_wsi_crosswalk.csv", index=False)
    (output_dir / "validated_linkage_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def validated_linkage_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build validated patch-to-WSI linkage artifacts from SAB pixel containment evidence.")
    parser.add_argument("--coordinates", type=Path, default=DEFAULT_COORDINATES)
    parser.add_argument("--private-crosswalk", type=Path, default=DEFAULT_PRIVATE_CROSSWALK)
    parser.add_argument("--pair-similarity", type=Path, default=DEFAULT_PAIR_SIMILARITY)
    parser.add_argument("--complete-ndb-labels", type=Path, default=DEFAULT_COMPLETE_NDB_LABELS)
    parser.add_argument("--sab-parsed-folders", type=Path, default=DEFAULT_SAB_PARSED_FOLDERS)
    parser.add_argument("--sab-parsed-test", type=Path, default=DEFAULT_SAB_PARSED_TEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser
