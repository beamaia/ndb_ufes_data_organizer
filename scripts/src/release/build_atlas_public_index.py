"""Build the small, public source-image index used by the documentation site.

The source inventory contains the atlas-level linkage result. This export keeps
only pseudonymous IDs, aggregate counts, labels, and evidence summaries. It
intentionally excludes SAB case prefixes, raw image names, and filesystem paths.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from src.release.atlas_methods import bbox_iou, coverage_metrics


VALIDATED_DIR = ROOT / "results/phase0/validated_linkage"
OUTPUT_DIR = ROOT / "docs/assets/atlas"
INVENTORY_CSV = VALIDATED_DIR / "validated_wsi_inventory.csv"
PATCH_LINKAGE_CSV = VALIDATED_DIR / "validated_patch_wsi_linkage.csv"
SIMILARITY_CSV = VALIDATED_DIR / "validated_wsi_patch_similarity.csv"
SUMMARY_JSON = VALIDATED_DIR / "validated_linkage_summary.json"
SAB_COORDINATE_SUMMARY_JSON = (
    ROOT
    / "results/phase0/sab_coordinate_recovery/sab_patch_coordinate_recovery_summary.json"
)
SAB_CONSISTENCY_SUMMARY_JSON = (
    ROOT / "results/phase0/sab_consistency_validation/validation_summary.json"
)
RELATIONSHIP_CSV = ROOT / "data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv"
RELATIONSHIP_SUMMARY_JSON = ROOT / "results/phase3/current_thesis_batches/relationship_update_summary.json"
ARTIFACT_MANIFEST_JSON = ROOT / "results/phase3/current_thesis_batches/artifact_manifest.json"
SCHEMA_PATH = OUTPUT_DIR / "atlas_schema.json"
CONFLICT_REPORT_PATH = OUTPUT_DIR / "metadata_conflict_summary.json"
METHODS_PATH = OUTPUT_DIR / "atlas_methods.json"
RELEASE_FACTS_PATH = OUTPUT_DIR / "release_facts.json"

PUBLIC_INDEX_SCHEMA = {
    "schema_version": 2,
    "name": "NDB-UFES/SAB public source-image index",
    "format": "csv",
    "privacy_mode": "public_pseudonymous",
    "identifier": "validated_wsi_id",
    "description": (
        "One public-safe row per source-image group. Counts are atlas-level evidence "
        "summaries and are not a replacement for thesis relationship metadata."
    ),
    "columns": [
        {"name": "validated_wsi_id", "type": "string", "required": True, "nullable": False, "description": "Retained compatibility name for the pseudonymous source-image group."},
        {"name": "source", "type": "string", "required": True, "nullable": False, "allowed_values": ["both", "SAB-only recovered source image"], "description": "Evidence source role for the source-image group."},
        {"name": "patch_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Number of atlas patches assigned to the source image."},
        {"name": "patch_pair_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Number of unordered same-source-image patch pairs, n × (n - 1) / 2."},
        {"name": "similarity_pair_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Number of same-source-image pair rows present in the validated similarity artifact; this can be lower than the theoretical pair count."},
        {"name": "patches_with_overlap", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Number of patches that overlap at least one other patch by recovered coordinates."},
        {"name": "overlapping_pair_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Number of same-source-image patch pairs with positive coordinate overlap."},
        {"name": "mapped_image_area_percent", "type": "number", "required": True, "nullable": False, "minimum": 0, "maximum": 100, "description": "Union of clipped patch boxes divided by displayed source-image area, as a percentage."},
        {"name": "repeated_sampled_area_percent", "type": "number", "required": True, "nullable": False, "minimum": 0, "maximum": 100, "description": "Multiply-covered coordinate area divided by mapped patch union area, as a percentage."},
        {"name": "repeated_full_wsi_image_area_percent", "type": "number", "required": True, "nullable": False, "minimum": 0, "maximum": 100, "description": "Retained field name for multiply-covered coordinate area divided by displayed source-image area, as a percentage."},
        {"name": "ndb_wsi_label", "type": "string", "required": True, "nullable": True, "description": "Retained field name for the source-level label carried by public NDB-UFES, when available."},
        {"name": "sab_wsi_label", "type": "string", "required": True, "nullable": True, "description": "Retained field name for the source-level label carried by SAB, when available."},
        {"name": "public_ndb_origin_ids", "type": "string", "required": True, "nullable": True, "encoding": "pipe-delimited public origin IDs", "description": "Public NDB origin identifiers supporting the source-image match."},
        {"name": "public_ndb_wsi_matches", "type": "number", "required": True, "nullable": True, "description": "Retained field name for the number of public NDB-UFES source-image matches recorded for the group."},
        {"name": "patches_oscc", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas patches carrying the complete OSCC label."},
        {"name": "patches_with_dysplasia", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas patches carrying the complete dysplasia label."},
        {"name": "patches_without_dysplasia", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas patches carrying the complete without-dysplasia label."},
        {"name": "patch_labels_unavailable", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas patches without an available complete patch label."},
        {"name": "evidence_summary", "type": "json_string", "required": True, "nullable": False, "description": "JSON object encoded as CSV text with atlas linkage-evidence counts."},
        {"name": "manual_review_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas rows requiring manual review in the validated-linkage output."},
        {"name": "metadata_conflict_patch_count", "type": "integer", "required": True, "nullable": False, "minimum": 0, "description": "Atlas patches flagged with metadata conflict; this is not a final label decision."},
    ],
    "excluded_private_fields": [
        "sab_case_prefix",
        "sab_origin_image_id",
        "sab_origin_path",
    ],
}


def _build_wsi_coordinate_metrics(linkage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for wsi_id, group in linkage.groupby("final_validated_wsi_id", sort=True):
        group = group.reset_index(drop=True)
        width = float(group["sab_origin_width"].iloc[0])
        height = float(group["sab_origin_height"].iloc[0])
        boxes = [
            (float(row.x), float(row.y), float(row.x + row.width), float(row.y + row.height))
            for row in group.itertuples()
        ]
        coverage = coverage_metrics(boxes, width, height)
        overlapping_pairs = 0
        overlapping_patch_indexes: set[int] = set()
        for index_a in range(len(boxes)):
            for index_b in range(index_a + 1, len(boxes)):
                box_a = {"x": boxes[index_a][0], "y": boxes[index_a][1], "x2": boxes[index_a][2], "y2": boxes[index_a][3]}
                box_b = {"x": boxes[index_b][0], "y": boxes[index_b][1], "x2": boxes[index_b][2], "y2": boxes[index_b][3]}
                iou = bbox_iou(box_a, box_b)
                if not math.isnan(iou) and iou > 0:
                    overlapping_pairs += 1
                    overlapping_patch_indexes.update((index_a, index_b))
        rows.append(
            {
                "validated_wsi_id": wsi_id,
                "patch_pair_count": len(group) * (len(group) - 1) // 2,
                "patches_with_overlap": len(overlapping_patch_indexes),
                "overlapping_pair_count": overlapping_pairs,
                "mapped_image_area_percent": coverage["mapped_image_area_percent"],
                "repeated_sampled_area_percent": coverage["repeated_sampled_area_percent"],
                "repeated_full_wsi_image_area_percent": coverage["repeated_full_wsi_image_area_percent"],
            }
        )
    return pd.DataFrame(rows)


def _build_similarity_counts(similarity: pd.DataFrame) -> pd.DataFrame:
    return (
        similarity.groupby("final_validated_wsi_id")
        .size()
        .rename("similarity_pair_count")
        .reset_index()
        .rename(columns={"final_validated_wsi_id": "validated_wsi_id"})
    )

ATLAS_METHODS = {
    "schema_version": 1,
    "report_type": "atlas_method_contract",
    "privacy_mode": "public_methods",
    "scope": "validated source-image linkage and same-source-image patch-pair evidence",
    "source_code": [
        {
            "path": "scripts/src/phase0/sab_patch_coordinate_recovery.py",
            "role": "recover patch coordinates inside candidate SAB source images",
        },
        {
            "path": "scripts/src/phase0/dataset_alignment_report.py",
            "role": "compute same-source-image boxes, fingerprints, color distances, and pair relations",
        },
        {
            "path": "scripts/src/phase0/validated_linkage.py",
            "role": "assign retained source-image group IDs and carry pair evidence into atlas outputs",
        },
        {
            "path": "scripts/src/release/atlas_methods.py",
            "role": "reusable coverage, IoU, and pair-relation helpers with a fixture cross-check",
        },
    ],
    "coordinate_recovery": {
        "patch_shape": "512x512 pixels when the source patch is standard-sized",
        "exact_match": {
            "mae_threshold": 0.0,
            "max_abs_diff_required": 0,
            "status": "exact_pixel_match",
        },
        "near_match": {
            "mae_threshold": 1.0,
            "max_abs_diff_threshold": 5,
            "status": "near_pixel_match",
        },
        "search": "OpenCV TM_SQDIFF_NORMED template matching after grayscale conversion; equal-size images use origin position (0, 0).",
        "atlas_caution": "A recovered coordinate is placement evidence, not a diagnosis or a claim that the patch is clinically representative.",
    },
    "same_wsi_pair_metrics": {
        "pair_count": "n * (n - 1) / 2 for n patches assigned to one source image",
        "iou": {
            "formula": "intersection_area / union_area",
            "overlap_rule": "spatially_overlapping when IoU > 0; spatially_distinct when IoU == 0",
        },
        "visual_fingerprint_similarity": {
            "resize": "32x32 pixels",
            "channels": "RGB scaled to [0, 1] concatenated with OpenCV LAB channels",
            "normalization": "mean-center the concatenated vector, then L2-normalize",
            "similarity": "cosine similarity, implemented as the dot product of normalized vectors",
            "classification_thresholds": {
                "similarity_at_least": 0.995,
                "lab_mean_delta_at_most": 6.0,
            },
        },
        "lab_mean_delta": {
            "formula": "Euclidean distance between the mean LAB vectors of the two full patch images",
            "interpretation": "lower values indicate more similar average LAB color; this is not a stain-normalization score",
        },
        "pair_relation": {
            "decision_order": [
                "If coordinates require review: feature_similar_coordinate_requires_review when the feature rule passes; otherwise coordinate_unavailable_or_requires_review.",
                "If coordinates overlap and the feature rule passes: feature_similar_and_spatially_overlapping.",
                "If coordinates are distinct and the feature rule passes: feature_similar_without_spatial_overlap.",
                "Otherwise retain spatially_overlapping when IoU > 0, or spatially_distinct when IoU == 0.",
            ],
        },
    },
    "atlas_panel_area_measures": {
        "mapped_image_area": {
            "formula": "area(union of all clipped patch boxes) / area(displayed source image)",
            "reported_as": "percentage",
            "evidence_basis": "Atlas panel definition and coordinate fixture cross-check",
        },
        "repeated_sampled_area": {
            "formula": "area(coordinate pixels covered by at least two patch boxes) / area(union of all clipped patch boxes)",
            "reported_as": "percentage",
            "evidence_basis": "Atlas panel definition and coordinate fixture cross-check",
        },
        "repeated_full_wsi_image_area": {
            "formula": "area(coordinate pixels covered by at least two patch boxes) / area(displayed source image)",
            "reported_as": "percentage",
            "evidence_basis": "Atlas panel definition and coordinate fixture cross-check",
        },
    },
    "area_measure_boundary": "The current reusable helper freezes the formulas, but the atlas panel renderer/configuration that originally wrote every DOCX value still needs to be connected to this helper before a future regenerated atlas is declared byte-for-byte method-equivalent.",
    "interpretation_limits": [
        "Thresholds classify review evidence; they do not establish diagnostic equivalence or biological identity.",
        "Same-source-image pair metrics are descriptive and should not be used as model-performance measurements.",
        "The three atlas-panel area denominators are now explicit and fixture-checked; the original DOCX renderer still needs to be connected to the helper for full regeneration provenance.",
    ],
}


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).sort_index().items()}


def _boolish_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _normalized_public_origin_ids(series: pd.Series) -> set[str]:
    normalized: set[str] = set()
    for value in series.dropna():
        try:
            numeric = float(value)
            if numeric.is_integer():
                normalized.add(str(int(numeric)))
                continue
        except (TypeError, ValueError):
            pass
        text = str(value).strip()
        if text:
            normalized.add(text)
    return normalized


def _build_linkage_layer_reconciliation(
    linkage: pd.DataFrame,
    relationship: pd.DataFrame,
) -> dict:
    """Compare the two public-origin classifications without exporting row IDs."""

    relationship_rows = relationship[
        ["patch_id", "found", "linked_ndb_origin_id"]
    ].copy()
    atlas_rows = linkage[
        [
            "ndb_patch",
            "final_validated_wsi_id",
            "previous_public_ndb_wsi_match",
            "origin_validation_id",
            "linkage_evidence_level",
            "current_metadata_vs_complete_patch_label_status",
        ]
    ].copy()
    comparison = relationship_rows.merge(
        atlas_rows,
        left_on="patch_id",
        right_on="ndb_patch",
        how="inner",
        validate="one_to_one",
    )
    if len(comparison) != len(relationship_rows) or len(comparison) != len(atlas_rows):
        raise ValueError(
            "relationship and atlas linkage tables do not cover the same patch IDs"
        )

    comparison["current_public_match"] = _boolish_series(comparison["found"])
    comparison["atlas_both_source"] = comparison[
        "final_validated_wsi_id"
    ].astype(str).str.startswith("public_ndb_wsi_")
    comparison["metadata_missing"] = comparison[
        "current_metadata_vs_complete_patch_label_status"
    ].eq("current_metadata_missing_patch")
    comparison["metadata_conflict_with_agreeing_patch_label"] = (
        comparison["linkage_evidence_level"].eq(
            "validated_exact_with_metadata_conflict"
        )
        & comparison["current_metadata_vs_complete_patch_label_status"].eq(
            "agrees"
        )
    )

    current_match_atlas_both = int(
        (
            comparison["current_public_match"]
            & comparison["atlas_both_source"]
        ).sum()
    )
    current_match_atlas_sab_only = int(
        (
            comparison["current_public_match"]
            & ~comparison["atlas_both_source"]
        ).sum()
    )
    current_no_match_atlas_both = int(
        (
            ~comparison["current_public_match"]
            & comparison["atlas_both_source"]
        ).sum()
    )
    current_no_match_atlas_sab_only = int(
        (
            ~comparison["current_public_match"]
            & ~comparison["atlas_both_source"]
        ).sum()
    )
    different_public_match_status = comparison[
        "current_public_match"
    ].ne(comparison["atlas_both_source"])

    current_public_origins = _normalized_public_origin_ids(
        relationship_rows.loc[
            _boolish_series(relationship_rows["found"]),
            "linked_ndb_origin_id",
        ]
    )
    atlas_public_origins = _normalized_public_origin_ids(
        linkage["previous_public_ndb_wsi_match"]
    )

    atlas_both_rows = comparison["atlas_both_source"]
    atlas_preconsolidation_source_ids = int(
        comparison["origin_validation_id"].nunique()
    )
    atlas_both_preconsolidation_source_ids = int(
        comparison.loc[atlas_both_rows, "origin_validation_id"].nunique()
    )
    atlas_sab_only_preconsolidation_source_ids = int(
        comparison.loc[~atlas_both_rows, "origin_validation_id"].nunique()
    )
    atlas_final_source_groups = int(
        comparison["final_validated_wsi_id"].nunique()
    )

    return {
        "patch_rows": int(len(comparison)),
        "current_relationship_patch_roles": {
            "with_public_ndb_ufes_origin_match": int(
                comparison["current_public_match"].sum()
            ),
            "without_public_ndb_ufes_origin_match": int(
                (~comparison["current_public_match"]).sum()
            ),
        },
        "atlas_source_roles": {
            "public_ndb_ufes_and_sab_patch_rows": int(atlas_both_rows.sum()),
            "sab_only_patch_rows": int((~atlas_both_rows).sum()),
        },
        "row_status_comparison": {
            "current_match_and_atlas_both_source": current_match_atlas_both,
            "current_match_and_atlas_sab_only": current_match_atlas_sab_only,
            "current_no_match_and_atlas_both_source": current_no_match_atlas_both,
            "current_no_match_and_atlas_sab_only": current_no_match_atlas_sab_only,
            "different_public_match_status_rows": (
                current_match_atlas_sab_only + current_no_match_atlas_both
            ),
            "metadata_conflict_with_agreeing_patch_label_rows": int(
                comparison["metadata_conflict_with_agreeing_patch_label"].sum()
            ),
            "overlap_with_metadata_conflict_agreeing_patch_label_rows": int(
                (
                    different_public_match_status
                    & comparison["metadata_conflict_with_agreeing_patch_label"]
                ).sum()
            ),
            "current_no_match_rows_with_missing_reconstructed_metadata": int(
                (
                    ~comparison["current_public_match"]
                    & comparison["metadata_missing"]
                ).sum()
            ),
            "current_no_match_status_equals_missing_metadata_status": bool(
                (~comparison["current_public_match"]).equals(
                    comparison["metadata_missing"]
                )
            ),
        },
        "public_origin_sets": {
            "current_relationship_public_origins": int(
                len(current_public_origins)
            ),
            "atlas_public_origins": int(len(atlas_public_origins)),
            "same_public_origin_id_set": current_public_origins
            == atlas_public_origins,
        },
        "atlas_group_consolidation": {
            "sab_source_ids_before_final_grouping": atlas_preconsolidation_source_ids,
            "sab_source_ids_mapped_to_public_atlas_groups": (
                atlas_both_preconsolidation_source_ids
            ),
            "sab_source_ids_retained_as_sab_only_groups": (
                atlas_sab_only_preconsolidation_source_ids
            ),
            "final_atlas_source_image_groups": atlas_final_source_groups,
            "source_ids_consolidated_by_public_origin_grouping": (
                atlas_preconsolidation_source_ids - atlas_final_source_groups
            ),
        },
    }


def _build_conflict_report(linkage: pd.DataFrame) -> dict:
    conflict = linkage[linkage["linkage_evidence_level"].eq("validated_exact_with_metadata_conflict")]
    disagreements = linkage[linkage["current_metadata_vs_complete_patch_label_status"].eq("disagrees")]
    source_role = linkage["final_validated_wsi_id"].astype(str).str.startswith("public_").map(
        {True: "public_ndb_wsi", False: "sab_only_wsi"}
    )
    conflict_source_role = source_role.loc[conflict.index]
    mismatch_pairs = (
        disagreements.groupby(
            ["ndb_ufes_patch_label", "current_reconstructed_patch_label"], dropna=False
        )
        .size()
        .sort_index()
    )

    return {
        "schema_version": 1,
        "report_type": "metadata_conflict_review",
        "privacy_mode": "public_aggregate",
        "description": (
            "Aggregate review counts for the atlas metadata-conflict cohort. "
            "This report preserves the complete patch labels and reconstructed "
            "metadata as separate layers; it does not select a canonical label."
        ),
        "source_artifact": str(PATCH_LINKAGE_CSV.relative_to(ROOT)),
        "scope": {
            "patch_rows": int(len(linkage)),
            "complete_patch_label_agreement_rows": int(
                linkage["patch_label_agreement_status"].eq("agrees").sum()
            ),
            "metadata_status_counts": _counts(
                linkage["current_metadata_vs_complete_patch_label_status"]
            ),
            "complete_patch_label_counts": _counts(linkage["ndb_ufes_patch_label"]),
            "reconstructed_metadata_label_counts": _counts(
                linkage["current_reconstructed_patch_label"]
            ),
            "evidence_level_counts": _counts(linkage["linkage_evidence_level"]),
            "metadata_conflict_rows": int(len(conflict)),
        },
        "conflict_rows": {
            "by_metadata_status": _counts(
                conflict["current_metadata_vs_complete_patch_label_status"]
            ),
            "by_wsi_source_role": _counts(conflict_source_role),
            "by_dataset_use_status": _counts(conflict["dataset_use_status"]),
            "by_reconstructed_metadata_label": _counts(
                conflict["current_reconstructed_patch_label"]
            ),
        },
        "complete_label_to_reconstructed_label_mismatch_pairs": [
            {
                "complete_patch_label": str(complete_label),
                "reconstructed_metadata_label": str(reconstructed_label),
                "rows": int(rows),
            }
            for (complete_label, reconstructed_label), rows in mismatch_pairs.items()
        ],
        "reading_notes": [
            "The complete NDB-UFES and SAB patch-label sources agree for every atlas patch.",
            "The reconstructed metadata layer is a separate provenance layer and is missing for 677 rows.",
            "The 1,489-row metadata-conflict cohort includes 59 rows whose reconstructed patch label agrees; another metadata field is what triggers the conflict flag.",
            "No canonical training label is chosen by this report.",
        ],
    }


def _build_release_facts(
    summary: dict,
    relationship_summary: dict,
    artifact_manifest: dict,
    linkage_layer_reconciliation: dict,
    sab_coordinate_summary: dict,
    sab_consistency_summary: dict,
    all_coordinate_patch_pairs: int,
) -> dict:
    """Build the small public fact contract used by reader-facing pages."""

    validation = artifact_manifest.get("validation", {})
    batches = {}
    for batch_name in ("batch1", "batch2", "batch3"):
        batch = validation[batch_name]
        batches[batch_name] = {
            "release_status": (
                "canonical"
                if batch_name in {"batch1", "batch2"}
                else "exploratory_archive"
            ),
            "patch_rows": int(batch["rows"]),
            "fold_counts": {str(key): int(value) for key, value in batch["fold_counts"].items()},
            "class_counts": {str(key): int(value) for key, value in batch["class_counts"].items()},
            "origin_groups": int(batch["origins"]),
            "patient_case_groups": int(batch["patient_case_groups"]),
            "origins_crossing_folds": int(batch["origins_crossing_folds"]),
            "patient_case_groups_crossing_folds": int(batch["patient_case_groups_crossing_folds"]),
            "missing_images": int(batch["missing_images"]),
            "without_public_ndb_ufes_match_rows": int(
                batch["missing_linkage_metadata_rows"]
            ),
        }

    pruning = artifact_manifest["batch3_virchow_pruning"]
    return {
        "schema_version": 3,
        "report_type": "public_release_facts",
        "privacy_mode": "public_aggregate",
        "generated_by": "scripts/src/release/build_atlas_public_index.py",
        "description": (
            "Aggregate atlas and thesis-batch facts for reader-facing documentation. "
            "This file contains no row-level private SAB identifiers."
        ),
        "atlas_scope": {
            "patch_rows": int(summary["patches"]),
            "patches_with_coordinates": int(summary["patches_with_coordinates"]),
            "patches_with_final_wsi_id": int(summary["patches_with_final_wsi_id"]),
            "validated_wsi_count": int(summary["validated_wsi_count"]),
            "validated_wsi_with_public_ndb_match": int(summary["validated_wsi_with_public_ndb_match"]),
            "validated_wsi_sab_only": int(summary["validated_wsi_sab_only"]),
            "patch_label_agreement_rows": int(summary["label_agreement_counts"]["agrees"]),
            "same_wsi_patch_pairs": int(summary["same_wsi_patch_pairs"]),
            "all_coordinate_patch_pairs": int(all_coordinate_patch_pairs),
            "patches_with_metadata_conflict": int(summary["patches_with_metadata_conflict"]),
        },
        "public_ndb_ufes_match_scope": {
            "sab_linked_patch_rows": int(relationship_summary["patch_rows"]),
            "matched_patch_rows": int(relationship_summary["linked_patch_rows"]),
            "without_public_match_patch_rows": int(
                relationship_summary["missing_linkage_patch_rows"]
            ),
            "public_origin_or_fallback_groups": int(relationship_summary["pndb_origins"]),
            "matched_public_origins": int(relationship_summary["linked_pndb_origins"]),
            "without_public_match_fallback_groups": int(
                relationship_summary["missing_linkage_pndb_origins"]
            ),
        },
        "linkage_layer_reconciliation": linkage_layer_reconciliation,
        "source_image_inventory_scope": {
            "public_ndb_ufes_source_image_files": int(
                sab_consistency_summary["current_origin_images"]
            ),
            "public_source_image_files_exact_matched_to_sab": int(
                sab_consistency_summary[
                    "current_origin_images_exact_matched_to_sab"
                ]
            ),
            "public_source_image_files_without_sab_match": int(
                sab_consistency_summary["current_origin_images_unmatched_to_sab"]
            ),
            "sab_source_ids_with_patch_coordinates_before_final_grouping": int(
                sab_coordinate_summary["unique_sab_origins"]
            ),
            "final_patch_carrying_atlas_source_image_groups": int(
                summary["validated_wsi_count"]
            ),
        },
        "thesis_batches": batches,
        "canonical_experiment_batches": ["batch1", "batch2"],
        "batch3_virchow_pruning": {
            "threshold": float(pruning["threshold"]),
            "before_patch_rows": int(pruning["before_patch_rows"]),
            "after_patch_rows": int(pruning["after_patch_rows"]),
            "removed_patch_rows": int(pruning["removed_patch_rows"]),
            "near_duplicate_pairs": int(pruning["near_duplicate_pairs"]),
            "near_duplicate_groups": int(pruning["near_duplicate_groups"]),
        },
    }


def main() -> None:
    inventory = pd.read_csv(INVENTORY_CSV)
    linkage = pd.read_csv(PATCH_LINKAGE_CSV, keep_default_na=False)
    similarity = pd.read_csv(SIMILARITY_CSV, keep_default_na=False)
    coordinate_metrics = _build_wsi_coordinate_metrics(linkage)
    coordinate_metrics = coordinate_metrics.merge(
        _build_similarity_counts(similarity), on="validated_wsi_id", how="left"
    )
    coordinate_metrics["similarity_pair_count"] = coordinate_metrics["similarity_pair_count"].fillna(0).astype(int)
    summary = json.loads(SUMMARY_JSON.read_text())
    sab_coordinate_summary = json.loads(SAB_COORDINATE_SUMMARY_JSON.read_text())
    sab_consistency_summary = json.loads(SAB_CONSISTENCY_SUMMARY_JSON.read_text())
    relationship = pd.read_csv(RELATIONSHIP_CSV)
    relationship_summary = json.loads(RELATIONSHIP_SUMMARY_JSON.read_text())
    artifact_manifest = json.loads(ARTIFACT_MANIFEST_JSON.read_text())
    linkage_layer_reconciliation = _build_linkage_layer_reconciliation(
        linkage,
        relationship,
    )

    public = inventory[
        [
            "final_validated_wsi_id",
            "wsi_source",
            "n_patches",
            "wsi_label_from_ndb_ufes",
            "wsi_label_from_sab",
            "previous_reconstructed_ndb_origin_ids",
            "previous_public_ndb_wsi_matches",
            "n_ndb_patch_oscc",
            "n_ndb_patch_with_dysplasia",
            "n_ndb_patch_without_dysplasia",
            "n_ndb_patch_label_unavailable",
            "linkage_evidence_counts",
            "requires_manual_review_count",
            "metadata_conflict_count",
        ]
    ].rename(
        columns={
            "final_validated_wsi_id": "validated_wsi_id",
            "wsi_source": "source",
            "n_patches": "patch_count",
            "wsi_label_from_ndb_ufes": "ndb_wsi_label",
            "wsi_label_from_sab": "sab_wsi_label",
            "previous_reconstructed_ndb_origin_ids": "public_ndb_origin_ids",
            "previous_public_ndb_wsi_matches": "public_ndb_wsi_matches",
            "n_ndb_patch_oscc": "patches_oscc",
            "n_ndb_patch_with_dysplasia": "patches_with_dysplasia",
            "n_ndb_patch_without_dysplasia": "patches_without_dysplasia",
            "n_ndb_patch_label_unavailable": "patch_labels_unavailable",
            "linkage_evidence_counts": "evidence_summary",
            "requires_manual_review_count": "manual_review_count",
            "metadata_conflict_count": "metadata_conflict_patch_count",
        }
    )
    public = public.merge(coordinate_metrics, on="validated_wsi_id", how="left", validate="one_to_one")
    public["source"] = public["source"].replace(
        {"SAB-only recovered WSI": "SAB-only recovered source image"}
    )
    public_columns = [column["name"] for column in PUBLIC_INDEX_SCHEMA["columns"]]
    public = public[public_columns]
    public = public.sort_values("validated_wsi_id", kind="stable")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = OUTPUT_DIR / "validated_wsi_index.csv"
    manifest_path = OUTPUT_DIR / "atlas_manifest.json"
    public.to_csv(index_path, index=False)
    SCHEMA_PATH.write_text(json.dumps(PUBLIC_INDEX_SCHEMA, indent=2) + "\n")
    CONFLICT_REPORT_PATH.write_text(
        json.dumps(_build_conflict_report(linkage), indent=2) + "\n"
    )
    METHODS_PATH.write_text(json.dumps(ATLAS_METHODS, indent=2) + "\n")
    RELEASE_FACTS_PATH.write_text(
        json.dumps(
            _build_release_facts(
                summary,
                relationship_summary,
                artifact_manifest,
                linkage_layer_reconciliation,
                sab_coordinate_summary,
                sab_consistency_summary,
                int(coordinate_metrics["patch_pair_count"].sum()),
            ),
            indent=2,
        )
        + "\n"
    )

    manifest = {
        "schema_version": 2,
        "privacy_mode": "public_pseudonymous",
        "generated_on": date.today().isoformat(),
        "generated_by": "scripts/src/release/build_atlas_public_index.py",
        "source_artifacts": {
            "validated_wsi_inventory": str(INVENTORY_CSV.relative_to(ROOT)),
            "validated_wsi_patch_similarity": str(SIMILARITY_CSV.relative_to(ROOT)),
            "validated_linkage_summary": str(SUMMARY_JSON.relative_to(ROOT)),
            "thesis_relationship_summary": str(RELATIONSHIP_SUMMARY_JSON.relative_to(ROOT)),
            "thesis_artifact_manifest": str(ARTIFACT_MANIFEST_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "public_wsi_index": str(index_path.relative_to(ROOT)),
            "manifest": str(manifest_path.relative_to(ROOT)),
            "schema": str(SCHEMA_PATH.relative_to(ROOT)),
            "metadata_conflict_summary": str(CONFLICT_REPORT_PATH.relative_to(ROOT)),
            "methods": str(METHODS_PATH.relative_to(ROOT)),
            "release_facts": str(RELEASE_FACTS_PATH.relative_to(ROOT)),
        },
        "atlas_scope": {
            "patch_rows": int(summary["patches"]),
            "patches_with_coordinates": int(summary["patches_with_coordinates"]),
            "patches_with_final_wsi_id": int(summary["patches_with_final_wsi_id"]),
            "validated_wsi_count": int(summary["validated_wsi_count"]),
            "validated_wsi_with_public_ndb_match": int(summary["validated_wsi_with_public_ndb_match"]),
            "validated_wsi_sab_only": int(summary["validated_wsi_sab_only"]),
            "patch_label_agreement_rows": int(summary["label_agreement_counts"]["agrees"]),
            "same_wsi_patch_pairs": int(summary["same_wsi_patch_pairs"]),
            "all_coordinate_patch_pairs": int(coordinate_metrics["patch_pair_count"].sum()),
            "wsi_rows_with_coordinate_metrics": int(len(coordinate_metrics)),
            "patches_with_metadata_conflict": int(summary["patches_with_metadata_conflict"]),
        },
        "public_ndb_ufes_match_scope": {
            "sab_linked_patch_rows": int(relationship_summary["patch_rows"]),
            "matched_patch_rows": int(relationship_summary["linked_patch_rows"]),
            "without_public_match_patch_rows": int(
                relationship_summary["missing_linkage_patch_rows"]
            ),
        },
        "excluded_private_fields": [
            "sab_case_prefix",
            "sab_origin_image_id",
            "sab_origin_path",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(index_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
