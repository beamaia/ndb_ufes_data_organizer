# Phase 2: Morphology Tuning

Implementation guide for Phase 2 clustering parameter selection.

---

## Overview

Phase 2 evaluates frozen embeddings from Phase 1 to identify PCA and K-Means settings that produce meaningful morphological clustering. These clusters are then used in Phase 3 to stratify folds and ensure morphological balance across training and validation partitions.

**Input:**
- Embeddings from Phase 1: `data/embeddings/embeddings_wsi_level_{model}_*.pkl` (one file per model)
- Phase 1 origin mapping: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`

**Output:**
- Per-model tuning results under `results/phase2_tuning/`
- Selected parameters written to `clustering_params.json` (root directory)
- Phase 3 receives the selected model, embedding file path, and parameters

---

## Architecture

Phase 2 is structured as a top-level runner with modular helper functions:

```
scripts/phase2.py                          ← Main execution entry point
├── calls functions from each module below

scripts/src/phase2/
├── tune_clustering.py                     ← Core tuning logic
│   ├── discover_latest_embeddings()       ← Find Phase 1 output files
│   ├── load_embeddings()                  ← Load pickle files
│   ├── aggregate_to_wsi_level()           ← Mean-pool patches to origins
│   └── run_grid_search()                  ← Run PCA + K-Means grid
├── phase2_average_results.py              ← Aggregate repeated runs
│   ├── average_results()                  ← Compute mean/std metrics
│   └── save_averaged_results()            ← Write CSV
├── phase2_save_params.py                  ← Parameter selection
│   ├── select_optimal_params()            ← Choose best combination
│   └── save_optimal_params()              ← Write JSON
├── phase2_enhanced_visualizations.py      ← Generate plots
│   ├── create_basic_visualizations()      ← Elbow curves, silhouette
│   └── create_enhanced_visualizations()   ← Additional analysis
└── config.yaml                            ← Configuration

scripts/src/utils/logger.py                ← Logging
```

All functions in `scripts/src/phase2/` are importable modules with no side effects. Only `scripts/phase2.py` executes work.

---

## Configuration

Phase 2 behavior is controlled by `scripts/src/phase2/config.yaml`:

```yaml
tuning:
  pca_components_to_test: [2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25, 30]
  kmeans_clusters_to_test: [2, 3, 4, 5, 6, 7, 8, 9]
  n_runs: 5                                 # Repeated K-Means runs
  random_state: 42                          # Reproducibility seed
```

**Default parameters explained:**
- **PCA components:** Test 2 to 30 dimensions to explore complexity-variance trade-off
- **K-Means clusters:** Test 2 to 9 clusters to find meaningful morphological groupings
- **n_runs:** Repeat K-Means 5 times with different random initializations to assess stability
- **random_state:** Set seed for reproducibility; each run uses `random_state + run_id`

Modify these values to control model selection scope. Five runs is the recommended default; use three only for quick exploration.

---

## Workflow

### Step 1: Discover Embeddings

```bash
uv run python scripts/phase2.py
```

Phase 2 automatically discovers the latest embedding file for each model by parsing filenames:

```
embeddings_wsi_level_{model}_{YYYYMMDD}_{HHMMSS}.pkl
```

All discovered models are logged. Verify that your intended models appear in the output.

### Step 2: Mean-Pool Embeddings

For each model, Phase 2 loads the Phase 1 embeddings (patch-level vectors) and aggregates them to origin-level vectors using mean pooling:

```
wsi_embedding[origin_i] = mean(patch_embeddings[origin_i])
```

This produces one 768D (or model-specific dimension) vector per origin, ready for clustering.

### Step 3: Run Grid Search

For each origin-level embedding matrix, Phase 2 evaluates all parameter combinations:

1. **Apply PCA** with each specified number of components
2. **For each PCA setting, run K-Means** with each specified cluster count
3. **Repeat n_runs times** with different random states
4. **Compute metrics** for each run: silhouette score, inertia, explained variance, cluster sizes

Outputs per model per run:

```
results/phase2_tuning/phase2_all_results_{model}_run{N}.csv
```

### Step 4: Average Results

Phase 2 computes mean and standard deviation of metrics across repeated runs and saves averaged results:

```
results/phase2_tuning/phase2_all_results_{model}_averaged.csv
```

Tables include:
- `pca_components`
- `kmeans_clusters`
- `pca_explained_var`
- `inertia` (mean and std)
- `silhouette` (mean and std)

### Step 5: Select Optimal Parameters

Phase 2 selects the parameter combination with the highest mean silhouette score:

```python
best_params = averaged_results.loc[averaged_results['silhouette'].idxmax()]
```

For each model, saves:

```
results/phase2_tuning/clustering_params_{model}.json
```

Then across all models, selects the single best model and writes to:

```
clustering_params.json
```

This file is read by Phase 3.

---

## API Reference

### `run_grid_search(wsi_features, pca_components, cluster_counts, random_state, run_id)`

**Purpose:** Evaluate all PCA/K-Means combinations for a single model in a single run.

**Parameters:**
- `wsi_features` (np.ndarray): Shape (n_origins, embedding_dim)
- `pca_components` (list[int]): PCA dimensions to test
- `cluster_counts` (list[int]): K-Means cluster counts to test
- `random_state` (int): Random seed for reproducibility
- `run_id` (int): Run identifier (used only for logging)

**Returns:**
- DataFrame with columns: `pca_components`, `kmeans_clusters`, `pca_explained_var`, `inertia`, `silhouette`, `run`, `random_state`

**Example:**

```python
from src.phase2.tune_clustering import run_grid_search
import numpy as np

wsi_features = np.random.randn(203, 768)  # Example: 203 origins, 768D embeddings
results = run_grid_search(
    wsi_features=wsi_features,
    pca_components=[2, 3, 4, 5],
    cluster_counts=[2, 3, 4],
    random_state=42,
    run_id=1
)
print(results.shape)  # (16, 7) - 4 PCA × 3 clusters × 1 run
```

### `discover_latest_embeddings(pattern)`

**Purpose:** Find the latest Phase 1 embedding file for each model.

**Parameters:**
- `pattern` (str): Glob pattern matching embedding filenames, typically `"data/embeddings/embeddings_wsi_level_*.pkl"`

**Returns:**
- Dictionary mapping model names to file paths

**Example:**

```python
from src.phase2.tune_clustering import discover_latest_embeddings

embeddings = discover_latest_embeddings("data/embeddings/embeddings_wsi_level_*.pkl")
for model_name, path in embeddings.items():
    print(f"{model_name}: {path}")
```

### `average_results(result_dataframes)`

**Purpose:** Compute mean and standard deviation of metrics across multiple runs.

**Parameters:**
- `result_dataframes` (list[DataFrame]): Results from multiple `run_grid_search()` calls

**Returns:**
- DataFrame with aggregated metrics

---

## Interpreting Results

### Silhouette Score

Silhouette score ranges from -1 to 1, measuring how well-separated clusters are:

- **Close to 1:** Clusters are well-separated; samples are far from neighboring clusters
- **Close to 0:** Clusters overlap; samples are equidistant from their own and neighboring clusters
- **Close to -1:** Clusters are poorly separated; samples are closer to neighboring clusters

**Recommendation:** Silhouette score is useful but not sufficient. A high silhouette score does not guarantee useful morphological stratification for folds.

### Stability and Variance

Always examine standard deviation across repeated runs:

```
silhouette (mean ± std)
inertia (mean ± std)
```

Low standard deviation indicates stable clustering across random initializations. High variance suggests sensitivity to random seed.

### Cluster Sizes

Examine per-run cluster sizes:

```python
import pandas as pd

# After clustering
cluster_dist = pd.Series(kmeans.labels_).value_counts().sort_index()
print(cluster_dist)  # Should be reasonably balanced across clusters
```

Imbalanced cluster sizes (e.g., one cluster has 150 origins; another has 10) indicate poor morphological separation and weak stratification signal.

---

## Selection Criteria

When choosing the final model and parameters for Phase 3, consider:

1. **Silhouette score:** Higher is better, but do not maximize this alone
2. **Stability:** Low variance across repeated runs
3. **Cluster sizes:** Roughly balanced (no single cluster dominates)
4. **Interpretability:** Cluster interpretation makes sense for fold stratification
5. **Practical balance:** Selected parameters should yield folds with good diagnosis and demographic balance

**Do not** select parameters based on downstream model training performance. Doing so risks data leakage and circular reasoning.

---

## Running Phase 2

```bash
cd /Volumes/ssd/thesis_organization/ndb_ufes_data_organizer
uv run python scripts/phase2.py
```

Expected output:
- Console log showing model discovery, tuning progress, and selected parameters
- CSV files under `results/phase2_tuning/`
- `clustering_params.json` at repository root

The selected parameters in `clustering_params.json` are passed to Phase 3.
