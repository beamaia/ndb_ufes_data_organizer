# Phase 1 Results

Phase 1 creates the origin-to-patch mapping and extracts frozen patch embeddings for every configured backbone. These embeddings are inputs to Phase 2 morphology tuning; they are not downstream classifier features selected from validation performance.

## Current Outputs

| Output | Path | Status |
| --- | --- | --- |
| Origin-patch mapping | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` | 203 origins, 3,086 patches |
| Embeddings | `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl` | one dictionary per configured model |
| Run metadata | `results/phase1_metadata/master_runs.json` | completed run record |
| Run summary | `results/phase1_metadata/runs_summary.txt` | human-readable extraction summary |
| Exploratory plots | `docs/visualizations/` | retained for review, not acceptance criteria |

The current completed run covers all 11 configured pretrained backbones. Every model uses its registry-defined preprocessing, including model-specific resize, crop, interpolation, normalization mean, and normalization standard deviation. There is no shared ImageNet-normalization fallback.

## Embedding Format

Each embedding file is a Python pickle dictionary keyed by origin ID:

```python
{
    origin_id: np.ndarray,  # shape: (num_patches_for_origin, model_output_dim)
}
```

Example:

```python
import pickle

with open("data/embeddings/embeddings_wsi_level_virchow_20260628_223154.pkl", "rb") as f:
    embeddings = pickle.load(f)

origin_ids = sorted(embeddings)
origin_0_patch_embeddings = embeddings[0]
origin_0_wsi_embedding = origin_0_patch_embeddings.mean(axis=0)
```

Expected current cardinality:

| Metric | Value |
| --- | ---: |
| Origins | 203 |
| Patches | 3,086 |
| Virchow feature dimension | 2,560 |
| Accepted Phase 2 model | Virchow |

## Visualization Files

The interactive Plotly files under `docs/visualizations/` are exploratory views of patch-level and WSI-level PCA projections. They are useful for visual inspection, but the accepted morphology choice is made by Phase 2 eligibility rules and mean silhouette, not by visual preference.

Representative files:

```text
docs/visualizations/patch_clusters_3d_uni.html
docs/visualizations/wsi_clusters_3d_uni.html
docs/visualizations/patch_clusters_3d_ctranspath.html
docs/visualizations/wsi_clusters_3d_ctranspath.html
```

The visualization page lists all copied HTML files: [Visualizations](visualizations/README.md). Virchow is the accepted Phase 2 embedding model, but the current copied visualization set is exploratory and does not need to contain one plot per accepted downstream choice.

## Downstream Use

Phase 2 mean-pools patch embeddings to one vector per origin, evaluates PCA/K-Means configurations, rejects fold-hostile clusterings, and selects the best eligible morphology signal. The accepted current selection is Virchow with PCA=2 and K=3.

Phase 3 consumes `clustering_params.json`, reloads the exact selected embedding file, reproduces the PCA/K-Means assignment, and creates fold assignments for all 203 origins and 3,086 patches.

## Reproducibility

Run Phase 1 from the repository root:

```bash
uv run python scripts/phase1.py
```

Before using outputs downstream, confirm:

- `origin_patch_mapping.csv` contains 203 origins;
- every selected embedding file has the same 203 origin keys;
- total embedded patch rows sum to 3,086;
- `results/phase1_metadata/master_runs.json` records the completed model runs.

See [Reproducibility](reproducibility.md) for the full audit checklist.

**Last verified**: 29 June 2026.
