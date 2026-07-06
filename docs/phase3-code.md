# Phase 3 Code

Phase 3 converts the accepted morphology selection into deterministic leakage-safe six-fold assignments.

## Entrypoint

```text
scripts/phase3.py
```

`run() -> dict`

Purpose:

- Load the accepted Phase 2 parameter file.
- Reload the exact selected embedding file.
- Validate mapping, patch metadata, and embedding origin sets.
- Reproduce the selected PCA/K-Means clustering.
- Audit stratification variables.
- Assign folds with stratum round-robin LPT.
- Save origin-level and patch-level outputs.
- Save a machine-readable validation report.

Returns:

- Validation dictionary written to `fold_validation.json`.

## Loading Functions

Location:

```text
scripts/src/phase3/phase3_fold_creation.py
```

### `load_params(path: Path) -> dict`

Loads `clustering_params.json`.

Required keys:

- `model_name`
- `embeddings_file`
- `pca_components`
- `kmeans_clusters`
- `random_state`
- `selection_constraints`

Raises `ValueError` when required keys are missing.

### `load_embeddings(path: Path) -> dict`

Loads the selected embedding pickle file.

Validation behavior:

- Requires a non-empty dictionary.

### `load_expected_origin_ids(path: Path) -> list[int]`

Loads origin IDs from the Phase 1 mapping.

Validation behavior:

- Requires `origin_id`.
- Rejects missing IDs.
- Rejects duplicate IDs.
- Preserves origin `0` as valid.

### `load_patch_metadata(path: Path, expected_origin_ids: list[int]) -> pd.DataFrame`

Loads patch metadata.

Validation behavior:

- Requires `origin`, `patch`, and `diagnosis`.
- Rejects missing, non-numeric, or non-integer origins.
- Rejects duplicate patch IDs.
- Requires exact origin-set agreement with the Phase 1 mapping.

## Aggregation Functions

### `aggregate_to_origin_level(patch_df: pd.DataFrame) -> pd.DataFrame`

Creates one origin-level row per origin with diagnosis, patch count, patch IDs, and descriptive metadata.

### `aggregate_embeddings_to_wsi(embeddings: dict, origin_ids: list[int]) -> np.ndarray`

Mean-pools patch embeddings to one vector per origin.

Validation behavior:

- Embedding keys must exactly match expected origin IDs.
- Every origin must have a non-empty two-dimensional embedding array.
- Feature dimensions must be consistent.
- All embedding values must be finite.

## Clustering Functions

### `apply_pca_kmeans(embeddings: np.ndarray, params: dict) -> tuple[np.ndarray, dict]`

Reproduces Phase 2 PCA/K-Means using the selected PCA components, K, and seed.

Validation behavior:

- Rejects non-finite K-Means centers or inertia.
- Rejects missing requested clusters.
- Rechecks minimum cluster size and maximum cluster-size ratio.

Returns:

- Cluster labels aligned to origin rows.
- Diagnostics with explained variance, inertia, cluster sizes, and cluster ratio.

## Stratification Functions

### `missing_value_mask(series: pd.Series) -> pd.Series`

Normalizes missing-like strings such as empty values, `nan`, `unknown`, and `not informed`.

### `summarize_column_for_stratification(series: pd.Series) -> dict`

Reports missing count, missing rate, number of categories, and minimum category count.

### `evaluate_stratification_variables(...) -> pd.DataFrame`

Audits required, optional, and descriptive variables.

Current required variables:

- `origin_diagnosis`
- `morph_cluster`
- `gender`
- `age_group`

Gate:

- Missing rate must be at most 25 percent.
- Every category must have at least six origins.
- Required-variable failure blocks fold creation.

### `build_stratification_key(origin_df, audit_df) -> tuple[pd.Series, list[str]]`

Builds the combined stratum key from included required and optional variables.

Raises `ValueError` if any required variable failed the audit.

### `create_stratification_keys(origin_df, clusters) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]`

Adds morphology clusters, audits variables, and creates the combined stratification key.

## Assignment Functions

### `stratum_round_robin_lpt_assignment(origin_df, n_folds=6) -> pd.DataFrame`

Assigns folds deterministically within each combined stratum.

Algorithm:

1. Sort origins inside each stratum by descending patch count and ascending origin ID.
2. Process origins in blocks of six.
3. Assign each origin in a block to a distinct fold.
4. Choose among unused folds by patch load, then origin count, then fold ID.

Guarantee:

- A complete six-origin block contributes one origin to each fold.
- Each supported combined stratum differs by at most one origin across folds.

### `broadcast_to_patch_level(origin_df, patch_df) -> pd.DataFrame`

Maps origin-level folds onto patch rows.

Validation behavior:

- Raises if any patch cannot inherit an origin fold.

## Validation And Saving Functions

### `validate_folds(origin_df, patch_df, expected_origin_ids, n_folds=6, max_patch_imbalance_ratio=1.10) -> dict`

Raises on:

- origin-set mismatch.
- unassigned rows.
- missing or invalid fold IDs.
- origin leakage.
- combined stratum range above one.
- patch-count ratio above 1.10.

Returns:

- origin count.
- patch count.
- origin counts by fold.
- patch counts by fold.
- patch imbalance ratio.
- maximum stratum fold-count range.
- maximum folds per origin.

### `save_outputs(origin_df, patch_df, audit_df, validation, output_dir) -> None`

Writes:

- `fold_assignments_origin.csv`
- `fold_assignments_patch_level.csv`
- `stratification_variables_audit.csv`
- `fold_validation.json`

## Run

```bash
uv run python scripts/phase3.py
```

See [Phase 3 Results](phase3-results.md) for the current validated outputs.
