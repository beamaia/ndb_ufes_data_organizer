# Phase 2 Code

Phase 2 selects a fold-ready morphology signal from frozen Phase 1 embeddings.

## Entrypoint

```text
scripts/phase2.py
```

`run(config_path: Path = CONFIG_PATH) -> dict[str, dict]`

Purpose:

- Load Phase 2 configuration.
- Discover the latest embedding file for each configured model.
- Run repeated PCA/K-Means grid search.
- Average repeated runs.
- Apply fold-readiness eligibility rules.
- Save per-model diagnostics and the global accepted selection.

Returns:

- Dictionary keyed by model name with accepted parameter dictionaries or rejection diagnostics.

Failure behavior:

- A model with no eligible configuration is recorded as rejected.
- Phase 2 should not abort solely because Swin has no eligible configuration.
- Unexpected I/O or numeric failures should still raise.

## Tuning Functions

### `load_config(config_path: Path) -> dict`

Location:

```text
scripts/src/phase2/phase2_tune_clustering.py
```

Loads the YAML grid, input paths, output templates, and selection constraints.

### `model_name_from_embedding_path(path: str | Path) -> str`

Parses a model name from files named:

```text
embeddings_wsi_level_{model}_{YYYYMMDD}_{HHMMSS}.pkl
```

Raises `ValueError` if the filename does not match the timestamped embedding convention.

### `discover_latest_embeddings(pattern: str) -> dict[str, Path]`

Finds embedding files matching the configured glob and keeps the latest timestamp for each model.

Raises:

- `FileNotFoundError` when no valid embedding files are found.

### `load_embeddings(path: Path) -> dict`

Loads one embedding pickle file.

Validation behavior:

- Requires a non-empty dictionary.

### `load_origin_ids(path: Path) -> list`

Loads the expected origin IDs from the Phase 1 mapping.

Validation behavior:

- Requires an `origin_id` column.
- Rejects duplicate origin IDs.

### `aggregate_to_wsi_level(embeddings: dict, origin_ids: list) -> np.ndarray`

Mean-pools patch embeddings to one vector per origin.

Validation behavior:

- Embedding keys must exactly match the expected origin IDs.
- Every origin must have a two-dimensional, non-empty embedding array.
- Feature dimensions must be consistent across origins.
- All values must be finite.

### `run_grid_search(wsi_features, pca_components, cluster_counts, random_state, run_id) -> pd.DataFrame`

Runs PCA once at the maximum requested dimension, slices lower dimensions, then evaluates K-Means for each configured K.

Returns one row per PCA/K configuration with:

- explained variance.
- inertia.
- silhouette.
- minimum cluster size.
- maximum cluster size.
- cluster size ratio.
- run ID.
- random state.

## Averaging Functions

### `average_results(run_results: list[pd.DataFrame]) -> pd.DataFrame`

Location:

```text
scripts/src/phase2/phase2_average_results.py
```

Aggregates repeated grid-search runs by PCA and K.

Key outputs:

- `silhouette_mean`
- `silhouette_std`
- `inertia_mean`
- `inertia_std`
- `min_cluster_size_min`
- `max_cluster_size_max`
- `cluster_size_ratio_max`
- `runs`

### `save_averaged_results(results: pd.DataFrame, output_path: Path) -> None`

Writes averaged results to CSV.

## Selection Functions And Classes

### `NoEligibleClusteringError`

Location:

```text
scripts/src/phase2/phase2_save_params.py
```

Raised when a model has no clustering configuration that satisfies fold-readiness constraints.

### `select_optimal_params(results, random_state, min_cluster_size, max_cluster_size_ratio) -> dict`

Filters averaged results to eligible configurations and selects the highest mean silhouette.

Eligibility:

| Field | Rule |
| --- | --- |
| `min_cluster_size_min` | at least configured minimum cluster size |
| `cluster_size_ratio_max` | at most configured maximum ratio |

Returns:

- PCA components.
- K-Means cluster count.
- silhouette and inertia summaries.
- cluster-size diagnostics.
- selection constraints.
- random state and run count.

### `save_optimal_params(params: dict, output_path: Path) -> None`

Writes selected parameters or rejection diagnostics as JSON.

## Visualization Helpers

Location:

```text
scripts/src/phase2/phase2_enhanced_visualizations.py
```

These helper functions produce static tuning diagnostics such as silhouette curves, heatmaps, elbow curves, and top-configuration summaries. They are descriptive artifacts. They do not override the eligibility gate.

## Configuration Contract

Current selection constraints:

```yaml
selection:
  min_cluster_size: 11
  max_cluster_size_ratio: 5.0
```

Current grid:

- PCA dimensions: `2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25, 30`.
- K values: `2` through `9`.
- Repeated runs: 5.
- First seed: 42.

## Run

```bash
uv run python scripts/phase2.py
```

See [Phase 2 Results](phase2-results.md) for the accepted current selection.
