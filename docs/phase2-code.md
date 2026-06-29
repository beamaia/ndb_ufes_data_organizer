# Phase 2: Morphology Tuning

Phase 2 selects a fold-ready morphology signal from frozen Phase 1 embeddings.

## Architecture

`scripts/phase2.py` is the sole execution script. The modules below expose functions and have no independent `main()` flow:

- `scripts/src/phase2/phase2_tune_clustering.py`: discovery, loading, pooling, PCA/K-Means grid
- `scripts/src/phase2/phase2_average_results.py`: repeated-run aggregation
- `scripts/src/phase2/phase2_save_params.py`: eligibility filtering and selection
- `scripts/src/phase2/phase2_enhanced_visualizations.py`: diagnostic figures
- `scripts/src/phase2/config.yaml`: grid, thresholds, and output paths

## Configuration

The current grid tests PCA dimensions `2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25, 30`, K values `2` through `9`, and five seeds beginning at `42`.

Selection constraints:

```yaml
selection:
  min_cluster_size: 11
  max_cluster_size_ratio: 5.0
```

These constraints are checked across every repeated run for a configuration. A mathematically high silhouette is not enough if the clusters cannot support six-fold construction.

## Result Columns

Per-run CSVs contain:

- `pca_components`, `kmeans_clusters`, `pca_explained_var`
- `inertia`, `silhouette`
- `min_cluster_size`, `max_cluster_size`, `cluster_size_ratio`
- `run`, `random_state`

Averaged CSVs add mean/std fields and worst-case support fields such as `min_cluster_size_min`, `max_cluster_size_max`, and `cluster_size_ratio_max`.

## Selection Outputs

- `results/phase2_tuning/clustering_params_{model}.json`: accepted parameters or explicit rejection diagnostics
- `results/phase2_tuning/phase2_model_selection.csv`: one-row-per-model eligibility summary
- `clustering_params.json`: accepted global selection consumed by Phase 3

The completed run evaluated 112 configurations per model. Ten models had eligible configurations. Swin had none; its former 202/1 split is recorded as rejected.

## Accepted Configuration

| Field | Value |
| --- | ---: |
| Model | Virchow |
| Embedding run | `20260628_223154` |
| PCA | 2 |
| K | 3 |
| Mean silhouette | 0.663275 |
| Explained variance | 0.457611 |
| Cluster sizes | 101, 67, 35 |
| Size ratio | 2.885714 |

The result is derived from the grid and eligibility rules; it is not hardcoded.

## Run

```bash
uv run python scripts/phase2.py
```

Inspect `phase2_model_selection.csv` and the selected JSON before running Phase 3.
