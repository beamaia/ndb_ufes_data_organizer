# NDB-UFES Data Organizer

This repository organizes the public NDB-UFES / P-NDB-UFES oral histopathology data into leakage-safe cross-validation folds and supporting documentation.

The final product of this repo is not a trained model. It is a public data organization package: fold assignment files, data dictionary, factsheet, reproducibility notes, and audit guidance.

## Repository Purpose

- Create 6-fold assignments where all patches from the same origin image stay in the same fold, after Phase 2 morphology selection is accepted.
- Document the dataset so external users can understand labels, demographics, risk factors, task fields, known limitations, and correct usage.
- Use frozen pretrained embeddings only as an optional morphology-aware stratification signal.
- Avoid downstream model-training claims or fold choices based on validation/test performance.

## Required Public Deliverables

| Deliverable | Purpose |
| --- | --- |
| `fold_assignments_origin.csv` | One row per origin/WSI with fold, diagnosis, patch count, and morphology cluster where available. |
| `fold_assignments_patch_level*.csv` | Patch-level fold assignments with origin ID, diagnosis/class, fold, and image reference where available. |
| [Data Dictionary](data-dictionary.md) | File relationships, columns, counts, labels, task fields, and missingness notes. |
| [Factsheet](factsheet.md) | Dataset provenance, citation, task labels, demographics/risk factors, limitations, and leakage-safe use guidance. |
| [Exploratory Analysis](exploratory-analysis.md) | Descriptive figures for diagnosis distributions, metadata, missingness, and association checks. |
| [Contamination Checks](contamination-analysis.md) | Image-level checks for suspicious patch similarity and origin-patch matching behavior. |
| [Reproducibility](reproducibility.md) | Commands, expected outputs, and audit checkpoints for regenerating artifacts. |
| [Pipeline](pipeline.md) | Concise explanation of why each phase exists and how outputs flow. |
| [Implementation Status](status.md) | WIP status for each phase and notes about what still needs review. |

## Dataset at a Glance

Current matched patch subset for fold design:

| Metric | Count |
| --- | ---: |
| Patch rows available for fold design | 3,086 |
| Matched origins available for fold design | 203 |
| Diagnostic classes | 3 |
| OSCC patches | 1,517 |
| Leukoplakia with dysplasia patches | 930 |
| Leukoplakia without dysplasia patches | 639 |

Original origin-level metadata currently contains 237 rows. The matched fold-design subset contains 203 origins and 3,086 patches.

## Start Here

1. Read the [Factsheet](factsheet.md) for public dataset context and correct usage.
2. Read the [Data Dictionary](data-dictionary.md) before using any CSV.
3. Read the [Pipeline](pipeline.md) to understand how folds are intended to be produced.
4. Check [Implementation Status](status.md) before trusting, deleting, or committing generated artifacts.

## Current Implementation Caveat

The repository is mid-reorganization. Some documentation and root Markdown files were generated during previous audit sessions and should not be assumed canonical. The current docs intentionally identify stale paths, empty top-level scripts, and artifacts that need manual verification.

Known high-priority checks:

- `scripts/phase3.py` is now active as the Phase 3 runner; `scripts/phase4.py` remains an empty entrypoint.
- Phase 3 implementation exists under `scripts/src/phase3/`; Phase 4 implementations are still undergoing review.
- Phase 2 morphology tuning is expected to be rerun before final fold publication, and provisional fold artifacts should be checked against the accepted configuration.
- Root Markdown files should be promoted into `docs/`, archived, or deleted after manual audit.

## Citation

Falcao Ribeiro de Assis, Maria Clara; Lima, Leandro Muniz de; de Barros, Liliana Aparecida Pimenta; Velloso, Tania Regina; Krohling, Renato; Camisasca, Danielle (2023), "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data", Mendeley Data, V4, doi: 10.17632/bbmmm4wgr8.4.
