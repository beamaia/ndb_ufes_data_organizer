# Manual Validation Guide

Trust generated artifacts only after checking lineage and invariants.

## Repository State

```bash
git status --short
git status --ignored --short
dvc status
```

Do not confuse local generated results or scratch Markdown files with canonical public documentation.

## Phase 1

Inspect `scripts/phase1.py`, the model registry, wrappers, and latest metadata. Confirm:

- 203 mapping rows and 3,086 total patches.
- 11 successful current embedding files.
- exact origin-key agreement for every embedding dictionary.
- model-specific preprocessing with no generic normalization fallback.
- cache and output paths are on the SSD.

## Phase 2

Inspect `scripts/phase2.py`, `phase2_tune_clustering.py`, `phase2_save_params.py`, and `phase2_model_selection.csv`.

Confirm:

- 11 model rows appear in the summary.
- accepted configurations have minimum cluster size at least 11 and ratio at most 5.
- Swin is explicitly rejected rather than selected or treated as a pipeline crash.
- Virchow/PCA=2/K=3 is derived as the highest-silhouette eligible result.
- selection did not use downstream model performance.

## Phase 3

Inspect `scripts/phase3.py`, `phase3_fold_creation.py`, and `fold_validation.json`.

Required checks:

```text
origin_count = 203
patch_count = 3086
fold IDs = 0..5
max folds per origin = 1
max stratum fold-count range <= 1
patch imbalance ratio <= 1.10
```

Also confirm that origin `0` appears in both fold CSVs. The older 202-origin/3,066-patch files are superseded.

## Stratification Validation

Read `results/phase3/fold_creation/stratification_variables_validation.csv`.
Diagnosis, morphology cluster, gender, and age group must be
`included_required`. A required variable that fails missingness or six-fold
category support must stop the run.

High-missingness clinical fields must not silently enter `stratification_key`.

## Leakage Review

Acceptable:

- frozen external embeddings used before downstream training.
- deterministic fold creation based on metadata and unsupervised morphology.

Reject:

- patch-level random splits.
- one origin in multiple folds.
- feature extractors fine-tuned on all labels before fold creation.
- fold or clustering selection from validation/test performance.

## Documentation Acceptance

```bash
uv run python scripts/src/release/validate_public_atlas_pdf.py
uv run python scripts/src/release/validate_atlas_public_index.py
uv run --extra docs python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

Check desktop and mobile views. All pages must remain reachable through the left sidebar or mobile drawer, with page-local headings available in the table of contents.
