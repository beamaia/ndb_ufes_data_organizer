# Phase 3: Fold Creation

Phase 3 converts the accepted morphology selection into deterministic, leakage-safe six-fold assignments.

## Inputs

- `clustering_params.json`
- the exact `embeddings_file` named by that JSON
- `data/ndb_ufes/patch/parcial_pndb_ufes.csv`
- `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`

There is no fallback embedding path. The parameter file must provide model, embedding file, PCA components, K, seed, and selection constraints.

## Architecture

`scripts/phase3.py` owns execution and paths. `scripts/src/phase3/phase3_fold_creation.py` contains import-safe functions for loading, exact-set checks, clustering, stratification, assignment, validation, and saving.

## Strict Data Checks

Phase 3 rejects:

- missing, non-integer, duplicated, or unexpected origin IDs;
- any mismatch among mapping, patch metadata, and embedding keys;
- duplicate patch IDs or non-finite embeddings;
- non-finite PCA/K-Means results or missing requested clusters;
- a selected clustering that violates the Phase 2 eligibility constraints.

Origin ID `0` is valid and retained. The obsolete logic that converted missing IDs to zero and then dropped zero has been removed.

## Stratification Audit

The required variables are `origin_diagnosis`, `morph_cluster`, `gender`, and `age_group`. Each must have at most 25% missing values and at least six origins in every category; failure aborts fold creation.

The current run includes all four. Other clinical fields remain descriptive. The decisions are saved to `stratification_variables_audit.csv`.

## Assignment Algorithm

The deterministic stratum round-robin LPT algorithm works within each combined stratum:

1. Sort origins by descending patch count and ascending origin ID.
2. Take successive blocks of six origins.
3. Within each block, assign each origin to a distinct fold.
4. Choose among unused folds by total patch load, then origin count, then fold ID.

Thus every complete block contributes exactly one origin to each fold. Incomplete blocks contribute to distinct least-loaded folds. This guarantees a per-stratum fold-count range no greater than one while retaining global patch balance.

## Validation

`validate_folds()` raises on origin mismatch, unassigned rows, invalid/missing fold IDs, origin leakage, per-stratum range above one, or patch-count ratio above 1.10.

The machine-readable report is `results/phase3_fold_creation/fold_validation.json`.

Current result:

| Metric | Value |
| --- | ---: |
| Origins | 203 |
| Patches | 3,086 |
| Origin counts by fold | 31, 36, 31, 34, 37, 34 |
| Patch counts by fold | 520, 510, 511, 511, 524, 510 |
| Patch ratio | 1.02745 |
| Maximum folds per origin | 1 |
| Maximum stratum range | 1 |

The previous 202-origin/3,066-patch output is superseded because it omitted origin `0` and its 20 patches.

## Outputs

- `results/phase3_fold_creation/fold_assignments_origin.csv`
- `results/phase3_fold_creation/fold_assignments_patch_level.csv`
- `results/phase3_fold_creation/stratification_variables_audit.csv`
- `results/phase3_fold_creation/fold_validation.json`

## Run

```bash
uv run python scripts/phase3.py
```
