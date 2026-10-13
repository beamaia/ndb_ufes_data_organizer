# Reproducibility

Everything in the published tables and folds is produced by code in this repository, from the source data, in a fixed order. Nothing is edited by hand.

## Who can run what

This pipeline is mainly for use in the lab. Two of the datasets behind it, SAB and patches_data, are internal and are not published, and the case prefixes, the case groups and the folds are built from them, so the full build cannot be repeated outside the lab. The published tables and folds are its result.

The matching code, though, can be used with the public data alone, NDB-UFES and P-NDB-UFES:

- **SIFT between pictures.** `picture-features` and `picture-relations` find the pictures that show the same tissue. On NDB-UFES alone, pass `--sab-root` an empty folder.
- **Template matching of patches.** `patch-pool-search` finds where each P-NDB-UFES patch sits, by exact pixels, in the NDB-UFES pictures. It needs the patch images, the published folds files that carry the patch labels, and the NDB-UFES images, and an empty `--sab-root`. A patch whose parent picture exists only in SAB is not found; in a trial on the first 40 patches, 25 were found exactly and the rest have a parent picture that is only in SAB.

## The pipeline

`dvc.yaml` lists the stages. `uv run dvc repro` runs all of them; `uv run dvc repro <stage>` runs one and what it needs.

| Stage | Command | What it produces |
| --- | --- | --- |
| `picture-features` | `uv run python scripts/phase0.py picture-features` | SIFT features of every parent picture. |
| `picture-relations` | `uv run python scripts/phase0.py picture-relations` | Which pictures show the same tissue (strong geometric relations). |
| `patch-pool-search` | `uv run python scripts/phase0.py patch-pool-search` | Every patch template-matched in every picture (slow; run once). Needs no private file. |
| `patch-placements` | `uv run python scripts/phase0.py patch-placements` | Each patch projected into related pictures and checked there. |
| `patch-table` | `uv run python scripts/phase0.py patch-table` | The patch, picture and case tables (public and private) with every check, and the case groups. |
| `patch-embeddings` | `uv run python scripts/phase1.py patch-embeddings` | A Virchow embedding of every patch. |
| `patch-clusters` | `uv run python scripts/phase1.py patch-clusters` | Three morphology clusters of the patches. |
| `folds` | `uv run python scripts/phase1.py folds` | The six folds and their summary. |
| `patient-atlas` | `uv run python scripts/phase2.py patient-atlas` | A PDF with every parent picture, its patch boxes and each patch beside its crop. |
| `aligned-atlas` | `uv run python scripts/phase2.py aligned-atlas` | A PDF with related pictures rotated into one frame. |
| `stats` | `uv run python scripts/phase2.py stats` | Every table and statistic as a CSV file. |
| `figures` | `uv run python scripts/phase2.py figures` | The SVG charts of the wiki. |
| `pages` | `uv run python scripts/phase2.py pages` | The generated wiki pages. |

Optional exploration that is not part of the pipeline: `cluster-choices` and `cluster-view` (how well the patches cluster).

## What each step guarantees

- **Patch to picture.** Each link is checked three ways: an exact pixel match inside the picture, a template search over all pictures that must name the picture in the SAB file name, and a pixel check against the SAB patch crop with the recorded file name and class.
- **Folds.** The `folds` stage stops, and writes nothing, if a case group, a picture or a group of related pictures would be in more than one fold, if a fold lacks one of the three classes, or if the largest fold holds more than 1.10 times the patches of the smallest.
- **Published files.** The folds stage checks that its output has only the allowed columns and that every cell has an allowed shape (a patch id, a group id, a fold number, a class name), on top of the leak patterns used for the tables.

## Determinism

The same inputs give the same files. SIFT matching uses exact search, the search for the folds uses fixed seeds, and group and picture ids come from the pixels. Rerunning a stage and comparing the outputs byte for byte gives identical files.

## What is private

The SAB images, the case prefixes behind the masked cases, the SAB file names, and all file paths are never published. They live in `private_lab` folders and in `data/`, which DVC keeps in a private remote; git ignores them. The published tables carry pseudonyms only (`case_NNN`, `group_NNN`) and repository-relative paths of public images.

`uv run python scripts/src/release/check_repo.py` scans everything git would publish for these identifiers and for oversized files, and it is the last step before a push.
