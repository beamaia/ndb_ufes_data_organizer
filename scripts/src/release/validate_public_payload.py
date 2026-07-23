#!/usr/bin/env python3
"""Scan the built public site or release bundle for release-blocking leaks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader


TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".svg",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
PATTERNS = {
    "absolute path": re.compile(r"(?:/Users/|/Volumes/|[A-Za-z]:\\\\)"),
    "private SAB case prefix": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "email address": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:password|secret|token|api[_-]?key)\s*[:=]\s*"
    r"[\"']?([^\s\"'<>]+)"
)
PLACEHOLDER_PARTS = (
    "${",
    "example",
    "placeholder",
    "replace",
    "your_",
)


def scan_text(path: Path, text: str) -> list[str]:
    failures = []
    for label, pattern in PATTERNS.items():
        if pattern.search(text):
            failures.append(f"{path}: {label}")
    for match in SECRET_ASSIGNMENT.finditer(text):
        value = match.group(1).lower()
        if not any(part in value for part in PLACEHOLDER_PARTS):
            failures.append(f"{path}: possible non-placeholder secret assignment")
            break
    return failures


def extracted_pdf_text(path: Path) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--max-mib",
        type=float,
        help="Fail if the complete payload is not strictly below this size.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Payload directory does not exist: {root}")

    files = [path for path in root.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    failures = []
    for path in files:
        if path.suffix.lower() in TEXT_SUFFIXES:
            failures.extend(scan_text(path, path.read_text(encoding="utf-8")))
        elif path.suffix.lower() == ".pdf":
            failures.extend(scan_text(path, extracted_pdf_text(path)))

    if args.max_mib is not None:
        limit = args.max_mib * 1024 * 1024
        if total_bytes >= limit:
            failures.append(
                f"{root}: {total_bytes / 1024 / 1024:.2f} MiB is not below "
                f"{args.max_mib:.2f} MiB"
            )

    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"validated public payload: {len(files)} files, "
        f"{total_bytes / 1024 / 1024:.2f} MiB"
    )


if __name__ == "__main__":
    main()
