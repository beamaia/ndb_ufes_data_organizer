"""Validate the root-level public atlas PDF before release.

The public atlas is intentionally separate from the MkDocs payload. This check
keeps the release copy below GitHub's per-file limit and rejects the private
identifiers and local provenance that are present in the LAB-only atlas.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_ATLAS = ROOT / "NDB_UFES_SAB_atlas_public.pdf"

EXPECTED_PAGES = 587
EXPECTED_WSI_IDS = 251
EXPECTED_PATIENT_CASE_GROUPS = 64
GITHUB_FILE_LIMIT_BYTES = 100_000_000

FORBIDDEN_PATTERNS = {
    "raw SAB case prefix": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "absolute local path": re.compile(r"/(?:Users|Volumes)/[^\s]+"),
    "email address": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
}
WSI_ID_PATTERN = re.compile(
    r"\b(?:public_ndb|sab_only)_wsi_\d+\b",
    flags=re.IGNORECASE,
)
PATIENT_CASE_GROUP_PATTERN = re.compile(
    r"\bpatient\s*/\s*case\s+group\s+(\d+)\b",
    flags=re.IGNORECASE,
)


def main() -> None:
    if not PUBLIC_ATLAS.is_file():
        raise SystemExit(f"missing root-level public atlas: {PUBLIC_ATLAS}")

    byte_count = PUBLIC_ATLAS.stat().st_size
    if byte_count >= GITHUB_FILE_LIMIT_BYTES:
        raise SystemExit(
            "public atlas exceeds GitHub's 100 MB per-file limit: "
            f"{byte_count:,} bytes"
        )

    reader = PdfReader(PUBLIC_ATLAS)
    if reader.is_encrypted:
        raise SystemExit("public atlas must not be encrypted")
    if len(reader.pages) != EXPECTED_PAGES:
        raise SystemExit(
            f"expected {EXPECTED_PAGES} public-atlas pages, found {len(reader.pages)}"
        )

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = text.lower()
    if "public version" not in normalized_text:
        raise SystemExit("public atlas does not identify itself as the PUBLIC version")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            raise SystemExit(f"public atlas contains forbidden {label}")

    wsi_ids = {value.lower() for value in WSI_ID_PATTERN.findall(text)}
    if len(wsi_ids) != EXPECTED_WSI_IDS:
        raise SystemExit(
            f"expected {EXPECTED_WSI_IDS} public WSI IDs, found {len(wsi_ids)}"
        )

    patient_case_groups = {
        int(value) for value in PATIENT_CASE_GROUP_PATTERN.findall(text)
    }
    if len(patient_case_groups) != EXPECTED_PATIENT_CASE_GROUPS:
        raise SystemExit(
            "expected "
            f"{EXPECTED_PATIENT_CASE_GROUPS} patient/case groups, "
            f"found {len(patient_case_groups)}"
        )

    digest = hashlib.sha256(PUBLIC_ATLAS.read_bytes()).hexdigest()
    print(
        "validated root-level public atlas: "
        f"{len(reader.pages)} pages, {len(wsi_ids)} WSI IDs, "
        f"{len(patient_case_groups)} patient/case groups, "
        f"{byte_count:,} bytes, sha256={digest}"
    )


if __name__ == "__main__":
    main()
