"""Scan everything git would publish for private content and for files too large for the repository."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.logger import logger  # noqa: E402


MAX_FILE_MB = 5.0
ATLAS_MAX_MB = 50.0  # the two atlas PDFs in atlases/ are published in git; GitHub warns above 50 MB and refuses above 100 MB
PRIVATE_PATTERNS = {
    "SAB case prefix": re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),
    "SAB photo name": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_\d+"),
    "SAB path": re.compile(r"data/SAB/"),
    "absolute path": re.compile(r"/(?:Users|Volumes|home)/[A-Za-z0-9_.-]+"),
}
PUBLISHED_TABLES = [
    "results/phase0/dataset_tables/patch_table_public.csv",
    "results/phase0/dataset_tables/picture_table_public.csv",
    "results/phase0/dataset_tables/case_table_public.csv",
    "results/phase1/folds/fold_assignments.csv",
    "results/phase1/folds/fold_summary.csv",
    "results/phase1/clusters/patch_clusters.csv",
    "results/phase2/tables/ndb_at_a_glance.csv",
    "results/phase2/tables/ndb_columns.csv",
    "results/phase2/tables/ndb_distributions.csv",
    "results/phase2/tables/ndb_correlations.csv",
    "results/phase2/tables/patch_correlations.csv",
    "results/phase2/tables/ndb_images_with_patches.csv",
    "results/phase2/tables/patches_per_picture.csv",
    "results/phase2/tables/sab_folder_vs_diagnosis.csv",
    "results/phase2/tables/related_pictures.csv",
    "results/phase2/tables/fold_balance.csv",
    "results/phase2/tables/fold_spread.csv",
    "results/phase2/tables/fold_distances.csv",
    "results/phase2/tables/overlapping_patches.csv",
]
DATA_DICTIONARY = "docs/data-dictionary.md"
DEFINE_THE_PATTERNS = {"scripts/src/release/check_repo.py", "scripts/src/phase0_dataset_builder/cases.py"}  # these files contain the patterns themselves


def publishable_files() -> list[str]:
    """Files git tracks, plus new files it would add (not ignored), that still exist."""
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True, check=True).stdout
    return sorted(path for path in set(listed.splitlines()) if Path(path).is_file())


def pdf_text(path: str) -> str | None:
    """The text of a PDF, read with Ghostscript; None when Ghostscript is not installed."""
    ghostscript = shutil.which("gs")
    if ghostscript is None:
        return None
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "text.txt"
        subprocess.run([ghostscript, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", f"-sOutputFile={target}", path], check=True)
        return target.read_text(encoding="utf-8", errors="replace")


def scan(paths: list[str], max_file_mb: float = MAX_FILE_MB) -> tuple[list[str], list[str]]:
    """Findings about private content, and files over the size limit."""
    private, large = [], []
    for path in paths:
        size_mb = Path(path).stat().st_size / 1e6
        limit = ATLAS_MAX_MB if path.startswith("atlases/") else max_file_mb
        if size_mb > limit:
            large.append(f"{path}: {size_mb:.1f} MB (limit {limit:g})")
        if path in DEFINE_THE_PATTERNS:
            continue
        if path.endswith(".pdf"):
            text = pdf_text(path)
            if text is None:
                logger.warning(f"{path}: Ghostscript is not installed, so the text of this PDF was not scanned")
                continue
        else:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # images and other binary files carry no readable text to scan
        for label, pattern in PRIVATE_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                private.append(f"{path}: {len(matches)} x {label}, e.g. {matches[0]!r}")
    return private, large


def undocumented_columns() -> list[str]:
    """Columns of the published tables that the data dictionary does not mention, and published tables that are missing."""
    dictionary = Path(DATA_DICTIONARY).read_text(encoding="utf-8")
    problems = []
    for table in PUBLISHED_TABLES:
        if not Path(table).is_file():
            problems.append(f"{table}: the file is missing")
            continue
        header = Path(table).read_text(encoding="utf-8").splitlines()[0].split(",")
        problems += [f"{table}: column {column!r} is not in {DATA_DICTIONARY}" for column in header if f"`{column}`" not in dictionary]
    return problems


def run_check_repo(args: argparse.Namespace) -> int:
    paths = publishable_files()
    private, large = scan(paths, args.max_file_mb)
    logger.info(f"Scanned {len(paths)} files that git would publish")
    for finding in private:
        logger.warning(f"Private content: {finding}")
    for finding in large:
        logger.warning(f"Too large: {finding}")
    undocumented = undocumented_columns()
    for finding in undocumented:
        logger.warning(f"Data dictionary: {finding}")
    if private or large or undocumented:
        logger.error(f"{len(private)} files with private content, {len(large)} files that are too large, {len(undocumented)} data dictionary gaps")
        return 1
    logger.info("Clean: no private content, no oversized files, every published column is in the data dictionary")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-file-mb", type=float, default=MAX_FILE_MB)
    return run_check_repo(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
