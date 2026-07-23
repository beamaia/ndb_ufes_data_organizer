"""Validate the committed, public-pseudonymous atlas index.

This check deliberately reads only the files that the documentation site ships.
It can therefore run in CI without private SAB data or the local phase-0 result
tree. The stronger source-to-export check remains the responsibility of the
index-generation step on the machine that has the validated linkage outputs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ATLAS_DIR = ROOT / "docs/assets/atlas"
INDEX_PATH = ATLAS_DIR / "validated_wsi_index.csv"
MANIFEST_PATH = ATLAS_DIR / "atlas_manifest.json"
SCHEMA_PATH = ATLAS_DIR / "atlas_schema.json"
CONFLICT_REPORT_PATH = ATLAS_DIR / "metadata_conflict_summary.json"
METHODS_PATH = ATLAS_DIR / "atlas_methods.json"
RELEASE_FACTS_PATH = ATLAS_DIR / "release_facts.json"

EXPECTED_COLUMNS = [
    "validated_wsi_id",
    "source",
    "patch_count",
    "patch_pair_count",
    "similarity_pair_count",
    "patches_with_overlap",
    "overlapping_pair_count",
    "mapped_image_area_percent",
    "repeated_sampled_area_percent",
    "repeated_full_wsi_image_area_percent",
    "ndb_wsi_label",
    "sab_wsi_label",
    "public_ndb_origin_ids",
    "public_ndb_wsi_matches",
    "patches_oscc",
    "patches_with_dysplasia",
    "patches_without_dysplasia",
    "patch_labels_unavailable",
    "evidence_summary",
    "manual_review_count",
    "metadata_conflict_patch_count",
]

FORBIDDEN_FIELDS = {
    "sab_case_prefix",
    "sab_origin_image_id",
    "sab_origin_path",
    "case_prefix",
    "origin_image_id",
    "origin_path",
}
FORBIDDEN_VALUE_MARKERS = ("/Volumes/ssd/SAB/", "\\SAB\\")


def main() -> None:
    if not INDEX_PATH.is_file():
        raise SystemExit(f"missing public atlas index: {INDEX_PATH}")
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"missing atlas manifest: {MANIFEST_PATH}")
    if not SCHEMA_PATH.is_file():
        raise SystemExit(f"missing atlas schema: {SCHEMA_PATH}")
    if not CONFLICT_REPORT_PATH.is_file():
        raise SystemExit(f"missing metadata-conflict summary: {CONFLICT_REPORT_PATH}")
    if not METHODS_PATH.is_file():
        raise SystemExit(f"missing atlas methods contract: {METHODS_PATH}")
    if not RELEASE_FACTS_PATH.is_file():
        raise SystemExit(f"missing public release facts: {RELEASE_FACTS_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text())
    schema = json.loads(SCHEMA_PATH.read_text())
    conflict_report = json.loads(CONFLICT_REPORT_PATH.read_text())
    methods = json.loads(METHODS_PATH.read_text())
    release_facts = json.loads(RELEASE_FACTS_PATH.read_text())
    if manifest.get("schema_version") != 2:
        raise SystemExit("unsupported atlas manifest schema_version")
    if manifest.get("privacy_mode") != "public_pseudonymous":
        raise SystemExit("atlas manifest must declare public_pseudonymous privacy_mode")
    if schema.get("schema_version") != manifest["schema_version"]:
        raise SystemExit("atlas schema and manifest versions do not match")
    if schema.get("privacy_mode") != manifest["privacy_mode"]:
        raise SystemExit("atlas schema and manifest privacy modes do not match")
    schema_columns = [column["name"] for column in schema.get("columns", [])]
    if schema_columns != EXPECTED_COLUMNS:
        raise SystemExit("atlas schema columns do not match the public index contract")
    if set(schema.get("excluded_private_fields", [])) != set(manifest.get("excluded_private_fields", [])):
        raise SystemExit("atlas schema and manifest excluded private fields do not match")
    if conflict_report.get("schema_version") != 1:
        raise SystemExit("unsupported metadata-conflict summary schema_version")
    if conflict_report.get("privacy_mode") != "public_aggregate":
        raise SystemExit("metadata-conflict summary must be public_aggregate")
    if methods.get("schema_version") != 1:
        raise SystemExit("unsupported atlas methods schema_version")
    if methods.get("report_type") != "atlas_method_contract":
        raise SystemExit("atlas methods file has the wrong report_type")
    if methods.get("privacy_mode") != "public_methods":
        raise SystemExit("atlas methods file must be public_methods")
    if release_facts.get("schema_version") != 2:
        raise SystemExit("unsupported public release facts schema_version")
    if release_facts.get("report_type") != "public_release_facts":
        raise SystemExit("public release facts have the wrong report_type")
    if release_facts.get("privacy_mode") != "public_aggregate":
        raise SystemExit("public release facts must be public_aggregate")
    if methods.get("same_wsi_pair_metrics", {}).get("visual_fingerprint_similarity", {}).get("classification_thresholds") != {
        "similarity_at_least": 0.995,
        "lab_mean_delta_at_most": 6.0,
    }:
        raise SystemExit("atlas methods fingerprint thresholds do not match the documented contract")
    methods_text = METHODS_PATH.read_text()
    if any(marker in methods_text for marker in ("/Volumes/ssd/SAB/", "sab_origin_image_id", "sab_case_prefix", "sab_origin_path")):
        raise SystemExit("atlas methods contract contains private SAB provenance")
    conflict_text = CONFLICT_REPORT_PATH.read_text()
    if any(marker in conflict_text for marker in ("/Volumes/ssd/SAB/", "public_ndb_wsi_", "sab_only_wsi_")):
        raise SystemExit("metadata-conflict summary contains a row-level or local private identifier")
    release_facts_text = RELEASE_FACTS_PATH.read_text()
    if any(
        marker in release_facts_text
        for marker in ("/Volumes/ssd/SAB/", "sab_case_prefix", "sab_origin_image_id", "sab_origin_path")
    ):
        raise SystemExit("public release facts contain private SAB provenance")

    with INDEX_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise SystemExit(
                "public atlas index columns do not match the release contract: "
                f"{reader.fieldnames!r}"
            )
        if FORBIDDEN_FIELDS.intersection(reader.fieldnames):
            raise SystemExit("public atlas index contains a forbidden private field")
        rows = list(reader)

    if not rows:
        raise SystemExit("public atlas index is empty")

    ids = [row["validated_wsi_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("public atlas index contains duplicate validated_wsi_id values")

    source_counts = {source: sum(row["source"] == source for row in rows) for source in {row["source"] for row in rows}}
    atlas_scope = manifest["atlas_scope"]
    expected_rows = int(atlas_scope["validated_wsi_count"])
    if len(rows) != expected_rows:
        raise SystemExit(f"expected {expected_rows} WSI rows, found {len(rows)}")

    numeric_columns = [
        "patch_count",
        "patch_pair_count",
        "similarity_pair_count",
        "patches_with_overlap",
        "overlapping_pair_count",
        "mapped_image_area_percent",
        "repeated_sampled_area_percent",
        "repeated_full_wsi_image_area_percent",
        "patches_oscc",
        "patches_with_dysplasia",
        "patches_without_dysplasia",
        "patch_labels_unavailable",
        "manual_review_count",
        "metadata_conflict_patch_count",
    ]
    for row in rows:
        for column in numeric_columns:
            try:
                int(row[column])
            except ValueError as error:
                if column.endswith("_percent"):
                    try:
                        float(row[column])
                        continue
                    except ValueError:
                        pass
                raise SystemExit(f"non-numeric {column} in {row['validated_wsi_id']}") from error
        pair_count = int(row["patch_pair_count"])
        overlap_pair_count = int(row["overlapping_pair_count"])
        patches_with_overlap = int(row["patches_with_overlap"])
        if not (0 <= overlap_pair_count <= pair_count):
            raise SystemExit(f"invalid overlapping_pair_count in {row['validated_wsi_id']}")
        if not (0 <= int(row["similarity_pair_count"]) <= pair_count):
            raise SystemExit(f"invalid similarity_pair_count in {row['validated_wsi_id']}")
        if not (0 <= patches_with_overlap <= int(row["patch_count"])):
            raise SystemExit(f"invalid patches_with_overlap in {row['validated_wsi_id']}")
        for column in ("mapped_image_area_percent", "repeated_sampled_area_percent", "repeated_full_wsi_image_area_percent"):
            if not 0 <= float(row[column]) <= 100:
                raise SystemExit(f"invalid percentage in {column} for {row['validated_wsi_id']}")
        if any(marker in value for value in row.values() for marker in FORBIDDEN_VALUE_MARKERS):
            raise SystemExit("public atlas index contains a raw local SAB path")

    checks = {
        "patch rows": (sum(int(row["patch_count"]) for row in rows), int(atlas_scope["patch_rows"])),
        "all coordinate patch pairs": (sum(int(row["patch_pair_count"]) for row in rows), int(atlas_scope["all_coordinate_patch_pairs"])),
        "available similarity pairs": (sum(int(row["similarity_pair_count"]) for row in rows), int(atlas_scope["same_wsi_patch_pairs"])),
        "public NDB-UFES + SAB groups": (source_counts.get("both", 0), int(atlas_scope["validated_wsi_with_public_ndb_match"])),
        "SAB-only groups": (source_counts.get("SAB-only recovered WSI", 0), int(atlas_scope["validated_wsi_sab_only"])),
        "metadata-conflict patches": (
            sum(int(row["metadata_conflict_patch_count"]) for row in rows),
            int(atlas_scope["patches_with_metadata_conflict"]),
        ),
    }
    for label, (actual, expected) in checks.items():
        if actual != expected:
            raise SystemExit(f"{label}: expected {expected}, found {actual}")

    facts_atlas_scope = release_facts.get("atlas_scope", {})
    for key in (
        "patch_rows",
        "patches_with_coordinates",
        "patches_with_final_wsi_id",
        "validated_wsi_count",
        "validated_wsi_with_public_ndb_match",
        "validated_wsi_sab_only",
        "patch_label_agreement_rows",
        "same_wsi_patch_pairs",
        "all_coordinate_patch_pairs",
        "patches_with_metadata_conflict",
    ):
        if int(facts_atlas_scope.get(key, -1)) != int(
            atlas_scope.get(key, -2)
        ):
            raise SystemExit(f"public release facts atlas scope mismatch for {key}")

    facts_match_scope = release_facts.get("public_ndb_ufes_match_scope", {})
    manifest_match_scope = manifest.get("public_ndb_ufes_match_scope", {})
    for key in (
        "sab_linked_patch_rows",
        "matched_patch_rows",
        "without_public_match_patch_rows",
    ):
        if int(facts_match_scope.get(key, -1)) != int(
            manifest_match_scope.get(key, -2)
        ):
            raise SystemExit(f"public release facts NDB-UFES match scope mismatch for {key}")

    batches = release_facts.get("thesis_batches", {})
    if release_facts.get("canonical_experiment_batches") != ["batch1", "batch2"]:
        raise SystemExit("public release facts must declare Batch 1 and Batch 2 canonical")
    for batch_name in ("batch1", "batch2", "batch3"):
        batch = batches.get(batch_name, {})
        expected_status = (
            "canonical" if batch_name in {"batch1", "batch2"} else "exploratory_archive"
        )
        if batch.get("release_status") != expected_status:
            raise SystemExit(f"public release facts status mismatch for {batch_name}")
        patch_rows = int(batch.get("patch_rows", -1))
        fold_counts = {str(key): int(value) for key, value in batch.get("fold_counts", {}).items()}
        class_counts = {str(key): int(value) for key, value in batch.get("class_counts", {}).items()}
        if patch_rows < 0 or sum(fold_counts.values()) != patch_rows:
            raise SystemExit(f"public release facts fold counts do not cover {batch_name}")
        if sum(class_counts.values()) != patch_rows:
            raise SystemExit(f"public release facts class counts do not cover {batch_name}")
        if int(batch.get("missing_images", -1)) != 0:
            raise SystemExit(f"public release facts report missing images for {batch_name}")
        if int(batch.get("without_public_ndb_ufes_match_rows", -1)) != int(
            facts_match_scope.get("without_public_match_patch_rows", -2)
        ):
            raise SystemExit(
                f"public release facts public NDB-UFES match count mismatch for {batch_name}"
            )

    pruning = release_facts.get("batch3_virchow_pruning", {})
    if int(pruning.get("before_patch_rows", -1)) != int(batches["batch1"]["patch_rows"]):
        raise SystemExit("public release facts pruning input does not match batch1")
    if int(pruning.get("after_patch_rows", -1)) != int(batches["batch3"]["patch_rows"]):
        raise SystemExit("public release facts pruning output does not match batch3")
    if int(pruning.get("removed_patch_rows", -1)) != int(
        pruning["before_patch_rows"]
    ) - int(pruning["after_patch_rows"]):
        raise SystemExit("public release facts pruning difference is inconsistent")

    excluded = set(manifest.get("excluded_private_fields", []))
    if not FORBIDDEN_FIELDS.intersection(excluded):
        raise SystemExit("manifest does not record excluded private fields")

    report_scope = conflict_report.get("scope", {})
    if int(report_scope.get("patch_rows", -1)) != int(atlas_scope["patch_rows"]):
        raise SystemExit("metadata-conflict summary patch scope does not match the atlas manifest")
    if int(report_scope.get("metadata_conflict_rows", -1)) != int(atlas_scope["patches_with_metadata_conflict"]):
        raise SystemExit("metadata-conflict summary conflict count does not match the atlas manifest")
    if int(report_scope.get("complete_patch_label_agreement_rows", -1)) != int(atlas_scope["patch_label_agreement_rows"]):
        raise SystemExit("metadata-conflict summary label-agreement count does not match the atlas manifest")

    status_counts = report_scope.get("metadata_status_counts", {})
    if sum(int(value) for value in status_counts.values()) != int(atlas_scope["patch_rows"]):
        raise SystemExit("metadata status counts do not cover the atlas patch scope")
    mismatch_rows = sum(
        int(item["rows"])
        for item in conflict_report.get("complete_label_to_reconstructed_label_mismatch_pairs", [])
    )
    if mismatch_rows != int(status_counts.get("disagrees", -1)):
        raise SystemExit("metadata mismatch-pair counts do not match disagreement rows")
    for key in ("by_metadata_status", "by_wsi_source_role", "by_dataset_use_status", "by_reconstructed_metadata_label"):
        values = conflict_report.get("conflict_rows", {}).get(key, {})
        if sum(int(value) for value in values.values()) != int(report_scope["metadata_conflict_rows"]):
            raise SystemExit(f"metadata-conflict summary {key} counts do not cover the conflict cohort")

    expected_report_path = manifest.get("outputs", {}).get("metadata_conflict_summary")
    if expected_report_path != str(CONFLICT_REPORT_PATH.relative_to(ROOT)):
        raise SystemExit("atlas manifest does not point to the metadata-conflict summary")
    expected_methods_path = manifest.get("outputs", {}).get("methods")
    if expected_methods_path != str(METHODS_PATH.relative_to(ROOT)):
        raise SystemExit("atlas manifest does not point to the methods contract")
    expected_release_facts_path = manifest.get("outputs", {}).get("release_facts")
    if expected_release_facts_path != str(RELEASE_FACTS_PATH.relative_to(ROOT)):
        raise SystemExit("atlas manifest does not point to public release facts")

    print(f"validated public atlas index: {len(rows)} WSI rows, {checks['patch rows'][0]} patches")


if __name__ == "__main__":
    main()
