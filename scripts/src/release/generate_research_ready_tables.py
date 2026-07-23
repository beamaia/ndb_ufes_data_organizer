#!/usr/bin/env python3
"""Build an explicitly public or LAB research-ready release bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import OrderedDict
from pathlib import Path


DEFAULT_SOURCE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_S3_BASE_URI = "s3://REPLACE_WITH_BUCKET/ndb-ufes-sab"
PRIVATE_CASE_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
ABSOLUTE_PATH_RE = re.compile(r"(?:/Users/|/Volumes/|[A-Za-z]:\\\\)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
RELEASE_MARKER = ".ndb_release_bundle"

PUBLIC_PATCH_COLUMNS = [
    "patch_id",
    "diagnosis",
    "fold",
    "role",
    "public_origin_id",
    "public_group_id",
    "public_wsi_id",
    "image_path",
    "metadata_status",
    "metadata_conflict_status",
    "provenance_status",
    "localization",
    "lesion_size",
    "tobacco_use",
    "alcohol_consumption",
    "sun_exposure",
    "gender",
    "skin_color",
    "age_group",
    "dysplasia_severity",
]
PUBLIC_BATCHES = {
    "experiment1_patch_assignments.csv": (
        "results/phase3/current_thesis_batches/batch1_recovered_reference_patch_level.csv"
    ),
    "experiment2_patch_assignments.csv": (
        "results/phase3/current_thesis_batches/batch2_patient_first_patch_level.csv"
    ),
}


TABLE_COPY_PLAN = {
    "current_batches": [
        "results/phase3/current_thesis_batches/batch1_recovered_reference_patch_level.csv",
        "results/phase3/current_thesis_batches/batch2_patient_first_patch_level.csv",
        "results/phase3/current_thesis_batches/batch3_virchow_pruned_patch_level.csv",
        "results/phase3/current_thesis_batches/batch2_patient_first_group_level.csv",
        "results/phase3/current_thesis_batches/pndb_ndb_patch_relationships.csv",
        "results/phase3/current_thesis_batches/pndb_ndb_origin_relationships.csv",
    ],
    "validated_linkage": [
        "results/phase0/validated_linkage/validated_patch_wsi_linkage.csv",
        "results/phase0/validated_linkage/validated_wsi_inventory.csv",
        "results/phase0/validated_linkage/validated_patch_label_agreement.csv",
        "results/phase0/validated_linkage/validated_wsi_patch_similarity.csv",
    ],
    "phase0_validation_evidence": [
        "results/phase0/recovery_validation/raw_patch_inventory.csv",
        "results/phase0/recovery_validation/origin_image_inventory.csv",
        "results/phase0/recovery_validation/missing_patch_candidates.csv",
        "results/phase0/sab_consistency_validation/patch_source_convergence.csv",
        "results/phase0/sab_consistency_validation/patch_origin_plausibility_validation.csv",
        "results/phase0/sab_consistency_validation/origin_source_convergence.csv",
        "results/phase0/sab_coordinate_recovery/sab_patch_recovered_coordinates.csv",
    ],
    "fold_assignments": [
        "results/phase3/fold_creation/fold_assignments_origin.csv",
        "results/phase3/fold_creation/fold_assignments_patch_level.csv",
        "results/phase3/fold_creation/stratification_variables_validation.csv",
    ],
    "manifests": [
        "results/phase3/current_thesis_batches/artifact_manifest.json",
        "results/phase3/current_thesis_batches/relationship_update_summary.json",
        "results/phase0/validated_linkage/validated_linkage_summary.json",
        "results/phase0/sab_consistency_validation/validation_summary.json",
        "results/phase0/sab_coordinate_recovery/sab_patch_coordinate_recovery_summary.json",
        "results/phase3/fold_creation/fold_validation.json",
    ],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: OrderedDict[str, None] = OrderedDict()
        for row in rows:
            for key in row:
                seen.setdefault(key, None)
        fieldnames = list(seen)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_s3_base(uri: str) -> str:
    return uri.rstrip("/")


def s3_uri(base: str, key: str) -> str:
    return f"{normalize_s3_base(base)}/{key}"


def repo_relative(source_root: Path, path_value: str) -> str:
    if not path_value:
        return ""
    raw = path_value.strip()
    marker = "ndb_ufes_data_organizer/"
    if marker in raw:
        return raw.split(marker, 1)[1]
    path = Path(raw)
    if path.is_absolute():
        try:
            return str(path.relative_to(source_root))
        except ValueError:
            return ""
    return raw


def local_path_for(source_root: Path, path_value: str) -> Path | None:
    rel = repo_relative(source_root, path_value)
    if rel:
        return source_root / rel
    if path_value and Path(path_value).is_absolute():
        return Path(path_value)
    return None


def sha256_if_exists(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_size_if_exists(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    return str(path.stat().st_size)


def patch_id_from_row(row: dict[str, str]) -> str:
    for key in ("patch_id", "patch", "ndb_patch", "patch_a", "patch_b"):
        value = row.get(key, "")
        if value.startswith("p"):
            return value
    return ""


def public_wsi_origin_path(public_wsi_pseudonym: str) -> str:
    match = re.fullmatch(r"public_ndb_wsi_(\d{4})", public_wsi_pseudonym or "")
    if not match:
        return ""
    return f"data/ndb_ufes/origin_level/images/{match.group(1)}.png"


def build_lookup(source_root: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    linkage = read_csv(source_root / "results/phase0/validated_linkage/validated_patch_wsi_linkage.csv")
    inventory = read_csv(source_root / "results/phase0/validated_linkage/validated_wsi_inventory.csv")
    patch_lookup = {row["ndb_patch"]: row for row in linkage}
    wsi_lookup = {row["final_validated_wsi_id"]: row for row in inventory}
    return patch_lookup, wsi_lookup


def lab_patch_manifest_row(source_root: Path, s3_base: str, patch_id: str, patch_lookup: dict[str, dict[str, str]]) -> dict[str, object]:
    local_rel = f"data/ndb_ufes/patch_level/images/{patch_id}.png"
    local_path = source_root / local_rel
    link = patch_lookup.get(patch_id, {})
    manifest_id = f"lab_patch_{patch_id}"
    key = f"lab/patches/ndb/{patch_id}.png"
    return {
        "lab_image_manifest_id": manifest_id,
        "stable_internal_image_id": manifest_id,
        "image_level": "patch",
        "patch_id": patch_id,
        "final_validated_wsi_id": link.get("final_validated_wsi_id", ""),
        "public_wsi_pseudonym": link.get("public_wsi_pseudonym", ""),
        "lab_private_image_name": "",
        "repo_relative_local_path": local_rel,
        "source_local_path_exported": "",
        "s3_key": key,
        "s3_uri": s3_uri(s3_base, key),
        "access_tier": "lab",
        "file_exists_local": str(local_path.exists()),
        "file_size_bytes": file_size_if_exists(local_path),
        "sha256": sha256_if_exists(local_path),
        "notes": "Internal NDB/P-NDB patch image; de-identified patch id.",
    }


def public_patch_manifest_row(source_root: Path, s3_base: str, patch_id: str, patch_lookup: dict[str, dict[str, str]]) -> dict[str, object]:
    local_rel = f"data/ndb_ufes/patch_level/images/{patch_id}.png"
    local_path = source_root / local_rel
    link = patch_lookup.get(patch_id, {})
    manifest_id = f"public_patch_{patch_id}"
    filename = f"{patch_id}.png"
    key = f"public/patches/{filename}"
    return {
        "public_image_manifest_id": manifest_id,
        "public_image_id": manifest_id,
        "image_level": "patch",
        "patch_id": patch_id,
        "public_wsi_pseudonym": link.get("public_wsi_pseudonym", ""),
        "deidentified_filename": filename,
        "s3_key": key,
        "s3_uri": s3_uri(s3_base, key),
        "access_tier": "public_pending_release",
        "file_exists_local": str(local_path.exists()),
        "file_size_bytes": file_size_if_exists(local_path),
        "sha256": sha256_if_exists(local_path),
        "notes": "Public-ready patch image key; bucket/prefix remains private until release approval.",
    }


def lab_ndb_wsi_manifest_row(source_root: Path, s3_base: str, public_wsi: str, final_wsi: str) -> dict[str, object]:
    local_rel = public_wsi_origin_path(public_wsi)
    local_path = source_root / local_rel if local_rel else None
    origin_id = Path(local_rel).stem if local_rel else ""
    manifest_id = f"lab_wsi_{public_wsi}"
    key = f"lab/wsi/ndb_origin_{origin_id}.png" if origin_id else f"lab/wsi/{public_wsi}.png"
    return {
        "lab_image_manifest_id": manifest_id,
        "stable_internal_image_id": manifest_id,
        "image_level": "wsi_origin",
        "patch_id": "",
        "final_validated_wsi_id": final_wsi,
        "public_wsi_pseudonym": public_wsi,
        "lab_private_image_name": "",
        "repo_relative_local_path": local_rel,
        "source_local_path_exported": "",
        "s3_key": key,
        "s3_uri": s3_uri(s3_base, key),
        "access_tier": "lab",
        "file_exists_local": str(bool(local_path and local_path.exists())),
        "file_size_bytes": file_size_if_exists(local_path),
        "sha256": sha256_if_exists(local_path),
        "notes": "Internal NDB-UFES WSI/origin image.",
    }


def public_wsi_manifest_row(source_root: Path, s3_base: str, public_wsi: str, final_wsi: str) -> dict[str, object]:
    local_rel = public_wsi_origin_path(public_wsi)
    local_path = source_root / local_rel if local_rel else None
    filename = f"{public_wsi}.png"
    manifest_id = f"public_wsi_{public_wsi}"
    key = f"public/wsi/{filename}"
    return {
        "public_image_manifest_id": manifest_id,
        "public_image_id": manifest_id,
        "image_level": "wsi_origin",
        "patch_id": "",
        "public_wsi_pseudonym": public_wsi,
        "deidentified_filename": filename,
        "s3_key": key,
        "s3_uri": s3_uri(s3_base, key),
        "access_tier": "public_pending_release",
        "file_exists_local": str(bool(local_path and local_path.exists())),
        "file_size_bytes": file_size_if_exists(local_path),
        "sha256": sha256_if_exists(local_path),
        "notes": "Public-ready WSI/origin image key; prefix remains private until release approval.",
    }


def build_image_manifests(source_root: Path, output_root: Path, s3_base: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    patch_lookup, wsi_lookup = build_lookup(source_root)
    coordinates = read_csv(source_root / "results/phase0/sab_coordinate_recovery/sab_patch_recovered_coordinates.csv")
    patch_ids = sorted(patch_lookup)
    lab_rows: list[dict[str, object]] = []
    public_rows: list[dict[str, object]] = []

    for patch_id in patch_ids:
        lab_rows.append(lab_patch_manifest_row(source_root, s3_base, patch_id, patch_lookup))
        public_rows.append(public_patch_manifest_row(source_root, s3_base, patch_id, patch_lookup))

    public_wsi_seen: set[str] = set()
    for final_wsi, row in sorted(wsi_lookup.items()):
        public_wsi = row.get("public_wsi_pseudonym", "")
        if public_wsi.startswith("public_ndb_wsi_"):
            lab_rows.append(lab_ndb_wsi_manifest_row(source_root, s3_base, public_wsi, final_wsi))
            public_rows.append(public_wsi_manifest_row(source_root, s3_base, public_wsi, final_wsi))
            public_wsi_seen.add(public_wsi)

    sab_patch_seen: set[str] = set()
    sab_origin_seen: set[str] = set()
    for row in coordinates:
        patch_id = row.get("ndb_patch", "")
        link = patch_lookup.get(patch_id, {})
        sab_patch_path = row.get("sab_patch_path", "")
        sab_patch_name = Path(sab_patch_path).name if sab_patch_path else ""
        if sab_patch_name and sab_patch_name not in sab_patch_seen:
            sab_patch_seen.add(sab_patch_name)
            local_path = Path(sab_patch_path)
            manifest_id = f"lab_sab_patch_{Path(sab_patch_name).stem}"
            key = f"lab/patches/sab/{sab_patch_name}"
            lab_rows.append({
                "lab_image_manifest_id": manifest_id,
                "stable_internal_image_id": manifest_id,
                "image_level": "sab_patch",
                "patch_id": patch_id,
                "final_validated_wsi_id": link.get("final_validated_wsi_id", ""),
                "public_wsi_pseudonym": link.get("public_wsi_pseudonym", ""),
                "lab_private_image_name": sab_patch_name,
                "repo_relative_local_path": "",
                "source_local_path_exported": "",
                "s3_key": key,
                "s3_uri": s3_uri(s3_base, key),
                "access_tier": "lab",
                "file_exists_local": str(local_path.exists()),
                "file_size_bytes": file_size_if_exists(local_path),
                "sha256": sha256_if_exists(local_path),
                "notes": "Internal SAB patch image; contains private SAB filename/provenance.",
            })
        sab_origin_id = row.get("sab_origin_image_id", "")
        sab_origin_path = row.get("sab_origin_path", "")
        if sab_origin_id and sab_origin_id not in sab_origin_seen:
            sab_origin_seen.add(sab_origin_id)
            local_path = Path(sab_origin_path) if sab_origin_path else None
            filename = f"{sab_origin_id}.png"
            manifest_id = f"lab_sab_origin_{sab_origin_id}"
            key = f"lab/sab_origin_images/{filename}"
            lab_rows.append({
                "lab_image_manifest_id": manifest_id,
                "stable_internal_image_id": manifest_id,
                "image_level": "sab_origin",
                "patch_id": "",
                "final_validated_wsi_id": link.get("final_validated_wsi_id", ""),
                "public_wsi_pseudonym": link.get("public_wsi_pseudonym", ""),
                "lab_private_image_name": filename,
                "repo_relative_local_path": "",
                "source_local_path_exported": "",
                "s3_key": key,
                "s3_uri": s3_uri(s3_base, key),
                "access_tier": "lab",
                "file_exists_local": str(bool(local_path and local_path.exists())),
                "file_size_bytes": file_size_if_exists(local_path),
                "sha256": sha256_if_exists(local_path),
                "notes": "Internal SAB origin image; contains private case prefix/provenance.",
            })

    write_csv(output_root / "image_manifests/lab_image_manifest.csv", lab_rows)
    write_csv(output_root / "image_manifests/public_image_manifest.csv", public_rows)
    return lab_rows, public_rows


def manifest_ids_for_patch(patch_id: str) -> tuple[str, str]:
    return (f"lab_patch_{patch_id}" if patch_id else "", f"public_patch_{patch_id}" if patch_id else "")


def add_manifest_links(row: dict[str, str], patch_lookup: dict[str, dict[str, str]]) -> dict[str, str]:
    updated = dict(row)
    patch_id = patch_id_from_row(row)
    if patch_id:
        updated.setdefault("patch_id", patch_id)
        link = patch_lookup.get(patch_id, {})
        updated.setdefault("final_validated_wsi_id", link.get("final_validated_wsi_id", ""))
        updated.setdefault("public_wsi_pseudonym", link.get("public_wsi_pseudonym", ""))
        lab_id, public_id = manifest_ids_for_patch(patch_id)
        updated["lab_image_manifest_id"] = lab_id
        updated["public_image_manifest_id"] = public_id
    public_wsi = updated.get("public_wsi_pseudonym", "")
    if public_wsi:
        updated["lab_wsi_manifest_id"] = f"lab_wsi_{public_wsi}" if public_wsi.startswith("public_ndb_wsi_") else ""
        updated["public_wsi_manifest_id"] = f"public_wsi_{public_wsi}" if public_wsi.startswith("public_ndb_wsi_") else ""
    return normalize_path_values(updated)


def normalize_path_values(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    for key, value in list(updated.items()):
        if not value or "path" not in key.lower():
            continue
        if "/Volumes/ssd/thesis_organization/ndb_ufes_data_organizer/" in value:
            updated[key] = value.split("ndb_ufes_data_organizer/", 1)[1]
        elif "/Users/beamaia/thesis_organization/ndb_ufes_data_organizer/" in value:
            updated[key] = value.split("ndb_ufes_data_organizer/", 1)[1]
        elif value.startswith("/Volumes/ssd/SAB/"):
            updated[key] = Path(value).name
    return updated


def sanitize_text_paths(text: str) -> str:
    text = text.replace("/Volumes/ssd/thesis_organization/ndb_ufes_data_organizer/", "")
    text = text.replace("/Users/beamaia/thesis_organization/ndb_ufes_data_organizer/", "")
    return re.sub(r"/Volumes/ssd/SAB/[^\"]+", "[LAB_SAB_LOCAL_PATH_NOT_EXPORTED]", text)


def copy_research_tables(source_root: Path, output_root: Path) -> dict[str, dict[str, object]]:
    patch_lookup, _ = build_lookup(source_root)
    inventory: dict[str, dict[str, object]] = {}
    for group, rel_paths in TABLE_COPY_PLAN.items():
        target_dir = output_root / group
        target_dir.mkdir(parents=True, exist_ok=True)
        for rel_path in rel_paths:
            src = source_root / rel_path
            dst = target_dir / src.name
            if src.suffix == ".csv":
                rows = [add_manifest_links(row, patch_lookup) for row in read_csv(src)]
                write_csv(dst, rows)
                row_count = len(rows)
                columns = list(rows[0]) if rows else []
            else:
                dst.write_text(sanitize_text_paths(src.read_text(encoding="utf-8")), encoding="utf-8")
                row_count = ""
                columns = []
            inventory[str(dst.relative_to(output_root))] = {
                "source": rel_path,
                "row_count": row_count,
                "columns": columns,
            }
    return inventory


def write_notes(output_root: Path, s3_base: str, inventory: dict[str, dict[str, object]]) -> None:
    notes = f"""# Image Access Notes

This bundle uses manifests rather than local machine paths as the stable image access layer.

S3 base URI configured for this generated bundle:

`{normalize_s3_base(s3_base)}`

LAB image manifest:

- `image_manifests/lab_image_manifest.csv`
- Internal only.
- May contain SAB private image names, SAB case prefixes, and private provenance.
- Do not publish this file or the `lab/` S3 prefix.

PUBLIC image manifest:

- `image_manifests/public_image_manifest.csv`
- De-identified and public-ready, but still private until release approval.
- Does not contain SAB private image names or patient/case prefixes.

Important:

- Research tables should use `lab_image_manifest_id`, `public_image_manifest_id`, `lab_wsi_manifest_id`, and `public_wsi_manifest_id`.
- Do not depend on mounted external-drive paths; those paths are local to one machine.
- S3 object upload is not performed by this generator. Upload with the generated upload plan after choosing the real bucket.
"""
    (output_root / "image_manifests/image_access_notes.md").write_text(notes, encoding="utf-8")

    lines = [
        "# Research-Ready Tables",
        "",
        "This folder is a copied, readable bundle of key thesis tables. The original source files remain in `results/` and `data/`.",
        "",
        "Use the image manifest IDs in these tables to connect tabular rows to image objects.",
        "",
        "## Contents",
        "",
    ]
    for rel, meta in sorted(inventory.items()):
        row_count = meta["row_count"]
        count_text = f"{row_count} rows" if row_count != "" else "summary JSON"
        lines.append(f"- `{rel}`: copied from `{meta['source']}`; {count_text}.")
    lines.extend([
        "",
        "## Access tiers",
        "",
        "- LAB/private: internal only; may include private SAB provenance.",
        "- PUBLIC-ready: de-identified, but still private until publication is approved.",
        "",
        "## Primary vs supporting tables",
        "",
        "Primary tables are the current batch files, validated patch-to-WSI linkage, WSI inventory, fold assignments, and summary manifests.",
        "Supporting tables include label agreement, same-WSI patch similarity, missing-patch candidates, plausibility reviews, and coordinate status summaries.",
    ])
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_upload_plan(output_root: Path, s3_base: str) -> None:
    plan = f"""# S3 Upload Plan

Replace `s3://REPLACE_WITH_BUCKET/ndb-ufes-sab` with the real private bucket/prefix before upload.

Recommended upload shape:

```bash
aws s3 cp data/ndb_ufes/patch_level/images/ {normalize_s3_base(s3_base)}/lab/patches/ndb/ --recursive --exclude '*' --include '*.png'
aws s3 cp data/ndb_ufes/origin_level/images/ {normalize_s3_base(s3_base)}/lab/wsi/ --recursive --exclude '*' --include '*.png'
```

For PUBLIC-ready release, upload de-identified copies only:

```bash
aws s3 cp data/ndb_ufes/patch_level/images/ {normalize_s3_base(s3_base)}/public/patches/ --recursive --exclude '*' --include '*.png'
aws s3 cp data/ndb_ufes/origin_level/images/ {normalize_s3_base(s3_base)}/public/wsi/ --recursive --exclude '*' --include '*.png'
```

SAB private origin/patch upload needs the SAB drive mounted and should use the LAB manifest. Do not upload SAB private files to the public prefix.
"""
    (output_root / "image_manifests/s3_upload_plan.md").write_text(plan, encoding="utf-8")


def validate_bundle(output_root: Path, lab_rows: list[dict[str, object]], public_rows: list[dict[str, object]]) -> dict[str, object]:
    text_files = list(output_root.rglob("*.csv")) + list(output_root.rglob("*.json")) + list(output_root.rglob("*.md"))
    volumes_hits = []
    for path in text_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "/Volumes/ssd" in text:
            volumes_hits.append(str(path.relative_to(output_root)))

    public_manifest_text = (output_root / "image_manifests/public_image_manifest.csv").read_text(encoding="utf-8")
    public_private_pattern_hits = bool(PRIVATE_CASE_RE.search(public_manifest_text))
    public_sab_name_hits = bool(PRIVATE_CASE_RE.search(public_manifest_text))

    lab_missing = [row["lab_image_manifest_id"] for row in lab_rows if row.get("file_exists_local") != "True"]
    public_missing = [row["public_image_manifest_id"] for row in public_rows if row.get("file_exists_local") != "True"]

    patch_level_missing_manifest_refs = []
    for csv_path in output_root.rglob("*.csv"):
        if "image_manifest" in csv_path.name:
            continue
        rows = read_csv(csv_path)
        if not rows:
            continue
        if any(key in rows[0] for key in ("patch", "patch_id", "ndb_patch")):
            for idx, row in enumerate(rows, start=2):
                patch_id = patch_id_from_row(row)
                if patch_id and not row.get("lab_image_manifest_id"):
                    patch_level_missing_manifest_refs.append(f"{csv_path.relative_to(output_root)}:{idx}")
                    break

    result = {
        "no_volumes_ssd_paths_in_bundle": not volumes_hits,
        "volumes_ssd_path_hits": volumes_hits,
        "public_manifest_has_no_private_case_pattern": not public_private_pattern_hits,
        "public_manifest_has_no_sab_private_names": not public_sab_name_hits,
        "patch_level_rows_have_manifest_references": not patch_level_missing_manifest_refs,
        "patch_level_missing_manifest_reference_examples": patch_level_missing_manifest_refs[:20],
        "lab_manifest_rows": len(lab_rows),
        "public_manifest_rows": len(public_rows),
        "lab_manifest_missing_local_files": len(lab_missing),
        "public_manifest_missing_local_files": len(public_missing),
        "lab_missing_local_examples": lab_missing[:20],
        "public_missing_local_examples": public_missing[:20],
        "s3_upload_performed": False,
        "s3_upload_validation": "pending; network/S3 credentials are not available in this environment",
    }
    (output_root / "validation_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def public_id_map(values: set[str], prefix: str) -> dict[str, str]:
    def sort_key(value: str) -> tuple[int, float | str]:
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)

    return {
        value: f"{prefix}_{index:04d}"
        for index, value in enumerate(sorted(values, key=sort_key), start=1)
    }


def build_public_patch_rows(
    source_rows: list[dict[str, str]],
    linkage_lookup: dict[str, dict[str, str]],
    origin_ids: dict[str, str],
    group_ids: dict[str, str],
) -> list[dict[str, object]]:
    public_rows: list[dict[str, object]] = []
    for row in source_rows:
        patch_id = row["patch"]
        link = linkage_lookup.get(patch_id)
        if not link:
            raise ValueError(f"Missing atlas linkage for public patch {patch_id}")
        fold = int(row["fold"])
        role = "held_out_test" if fold == 5 else "cross_validation"
        if row.get("cv_role") and row["cv_role"] != role:
            raise ValueError(f"Unexpected role for {patch_id}: {row['cv_role']}")
        public_rows.append(
            {
                "patch_id": patch_id,
                "diagnosis": row["diagnosis"],
                "fold": fold,
                "role": role,
                "public_origin_id": origin_ids[row["origin_id"]],
                "public_group_id": group_ids[row["patient_case_group"]],
                "public_wsi_id": link["final_validated_wsi_id"],
                "image_path": f"data/ndb_ufes/patch_level/images/{patch_id}.png",
                "metadata_status": row.get("metadata_status", ""),
                "metadata_conflict_status": link.get(
                    "current_metadata_vs_complete_patch_label_status", ""
                ),
                "provenance_status": link.get("linkage_evidence_level", ""),
                "localization": row.get("localization", ""),
                "lesion_size": row.get("larger_size", ""),
                "tobacco_use": row.get("tobacco_use", ""),
                "alcohol_consumption": row.get("alcohol_consumption", ""),
                "sun_exposure": row.get("sun_exposure", ""),
                "gender": row.get("gender", ""),
                "skin_color": row.get("skin_color", ""),
                "age_group": row.get("age_group", ""),
                "dysplasia_severity": row.get("dysplasia_severity", ""),
            }
        )
    return public_rows


def validate_public_bundle(output_root: Path) -> dict[str, object]:
    failures: list[str] = []
    table_rows: dict[str, int] = {}
    for filename in PUBLIC_BATCHES:
        path = output_root / "tables" / filename
        rows = read_csv(path)
        table_rows[filename] = len(rows)
        if len(rows) != 3763:
            failures.append(f"{filename}: expected 3763 rows, found {len(rows)}")
        if rows and list(rows[0]) != PUBLIC_PATCH_COLUMNS:
            failures.append(f"{filename}: columns differ from the public allowlist")
        patch_ids = [row["patch_id"] for row in rows]
        if len(patch_ids) != len(set(patch_ids)):
            failures.append(f"{filename}: duplicate patch IDs")
        for row in rows:
            fold = int(row["fold"])
            expected_role = "held_out_test" if fold == 5 else "cross_validation"
            if row["role"] != expected_role:
                failures.append(f"{filename}: invalid fold role")
                break
            if not row["image_path"].startswith(
                "data/ndb_ufes/patch_level/images/"
            ):
                failures.append(f"{filename}: non-repository image path")
                break

    scanned_files = [
        path
        for path in output_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".csv", ".json", ".md", ".txt", ".svg"}
    ]
    scan_hits: dict[str, list[str]] = {
        "absolute_paths": [],
        "raw_case_prefixes": [],
        "emails": [],
        "secret_assignments": [],
    }
    secret_re = re.compile(
        r"(?i)(?:aws_secret_access_key|access_token|client_secret|password)\s*[:=]\s*[^\s<]+"
    )
    for path in scanned_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = str(path.relative_to(output_root))
        if ABSOLUTE_PATH_RE.search(text):
            scan_hits["absolute_paths"].append(relative)
        if PRIVATE_CASE_RE.search(text):
            scan_hits["raw_case_prefixes"].append(relative)
        if EMAIL_RE.search(text):
            scan_hits["emails"].append(relative)
        if secret_re.search(text):
            scan_hits["secret_assignments"].append(relative)
    for category, paths in scan_hits.items():
        if paths:
            failures.append(f"{category}: {paths}")

    report = {
        "schema_version": 1,
        "profile": "public",
        "status": "passed" if not failures else "failed",
        "table_rows": table_rows,
        "public_columns": PUBLIC_PATCH_COLUMNS,
        "scanned_text_files": len(scanned_files),
        "scan_hits": scan_hits,
        "failures": failures,
    }
    (output_root / "validation_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if failures:
        raise ValueError("Public bundle validation failed: " + "; ".join(failures))
    return report


def build_public_bundle(source_root: Path, output_root: Path) -> dict[str, object]:
    experiment_assets = source_root / "docs/assets/experiments"
    if not (experiment_assets / "canonical_run_manifest.json").is_file():
        raise FileNotFoundError(
            "Build docs/assets/experiments with "
            "build_canonical_experiment_release.py first"
        )
    batch_rows = {
        filename: read_csv(source_root / relative)
        for filename, relative in PUBLIC_BATCHES.items()
    }
    all_rows = [row for rows in batch_rows.values() for row in rows]
    origin_ids = public_id_map(
        {row["origin_id"] for row in all_rows},
        "public_origin",
    )
    group_ids = public_id_map(
        {row["patient_case_group"] for row in all_rows},
        "public_group",
    )
    linkage_rows = read_csv(
        source_root
        / "results/phase0/validated_linkage/validated_patch_wsi_linkage.csv"
    )
    linkage_lookup = {row["ndb_patch"]: row for row in linkage_rows}

    table_dir = output_root / "tables"
    experiment_dir = output_root / "experiments"
    figure_dir = output_root / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in batch_rows.items():
        public_rows = build_public_patch_rows(
            rows,
            linkage_lookup,
            origin_ids,
            group_ids,
        )
        write_csv(table_dir / filename, public_rows, PUBLIC_PATCH_COLUMNS)
    shutil.copy2(
        source_root / "docs/assets/atlas/validated_wsi_index.csv",
        table_dir / "validated_wsi_index.csv",
    )

    for filename in (
        "canonical_run_manifest.json",
        "canonical_run_validation.csv",
        "fold_test_metrics.csv",
        "results_summary.csv",
        "execution_times.csv",
        "statistics_within_experiment.csv",
        "statistics_between_experiments.csv",
        "confusion_matrix_selection.csv",
    ):
        shutil.copy2(experiment_assets / filename, experiment_dir / filename)
    for filename in (
        "fold_class_distribution.svg",
        "fig_confusion_matrices.png",
        "fig_confusion_matrices.pdf",
        "fig_train_validation_loss.png",
        "fig_train_validation_loss.pdf",
    ):
        shutil.copy2(experiment_assets / filename, figure_dir / filename)

    readme = """# NDB-UFES v1.0.0 Public Research Bundle

This public, sanitized package contains the two final thesis experiment split
tables, the public validated-WSI index, canonical stored-run evidence, summary
statistics, and result figures.

- Experiment 1 is the original-comparable patch split.
- Experiment 2 is the patient-first grouped, lower-contamination-risk split.
- Batch 3 is exploratory and is intentionally absent.
- No checkpoints, raw MLflow storage, private SAB provenance, direct
  patient/lesion identifiers, private crosswalks, or local paths are included.

The source NDB-UFES dataset and P-NDB-UFES patch dataset remain separate works
and must be cited from their original records. The documentation and derived
release tables in this bundle are provided under CC BY 4.0; repository code is
GPL-3.0-only.
"""
    (output_root / "README.md").write_text(readme, encoding="utf-8")
    (output_root / "LICENSE-DATA-AND-DOCS.txt").write_text(
        "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/\n"
        "Attribution: Beatriz Matias Santana Maia, NDB-UFES v1.0.0 derived "
        "research tables and documentation. Changes include deidentification, "
        "public pseudonyms, fold organization, and result summarization.\n",
        encoding="utf-8",
    )
    (output_root / RELEASE_MARKER).write_text("v1.0.0 public\n", encoding="utf-8")
    return validate_public_bundle(output_root)


def prepare_output(output_root: Path, source_root: Path) -> None:
    output_root = output_root.resolve()
    source_root = source_root.resolve()
    forbidden = {
        source_root,
        source_root.parent,
        Path("/").resolve(),
        Path.home().resolve(),
    }
    if output_root in forbidden:
        raise ValueError(f"Refusing unsafe output directory: {output_root}")
    if output_root.exists():
        marker = output_root / RELEASE_MARKER
        if not marker.is_file():
            raise ValueError(
                f"Refusing to replace unmarked directory: {output_root}"
            )
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--profile", choices=("public", "lab"), required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--s3-base-uri", default=DEFAULT_S3_BASE_URI)
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    if args.output_root is None:
        output_root = (
            source_root / "release/v1.0.0/public"
            if args.profile == "public"
            else source_root / "research_ready_tables/lab_v1.0.0"
        )
    else:
        output_root = args.output_root.resolve()
    prepare_output(output_root, source_root)

    if args.profile == "public":
        validation = build_public_bundle(source_root, output_root)
        print(f"Generated public bundle: {output_root}")
        print(json.dumps(validation, indent=2))
        return

    (output_root / RELEASE_MARKER).write_text(
        "v1.0.0 lab\n",
        encoding="utf-8",
    )
    for group in list(TABLE_COPY_PLAN) + ["image_manifests"]:
        (output_root / group).mkdir(parents=True, exist_ok=True)

    lab_rows, public_rows = build_image_manifests(source_root, output_root, args.s3_base_uri)
    inventory = copy_research_tables(source_root, output_root)
    write_notes(output_root, args.s3_base_uri, inventory)
    write_upload_plan(output_root, args.s3_base_uri)
    validation = validate_bundle(output_root, lab_rows, public_rows)
    print(f"Generated LAB bundle: {output_root}")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
