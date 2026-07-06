# Phase 1 Results

Phase 1 creates the origin-patch mapping and extracts frozen patch embeddings for every configured backbone. These outputs are the input pool for Phase 2 morphology tuning.

## Current Outputs

| Output | Path | Current Status |
| --- | --- | --- |
| Origin-patch mapping | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` | 203 origins and 3,086 patches |
| Embeddings | `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl` | one dictionary per configured model |
| Run metadata | `results/phase1_metadata/master_runs.json` | completed run record |
| Run summary | `results/phase1_metadata/runs_summary.txt` | human-readable extraction summary |
| Exploratory visualizations | `docs/visualizations/` | retained for visual review |

The current completed run covers all 11 configured pretrained backbones. Every model uses registry-defined preprocessing, including resize, crop, interpolation, normalization mean, and normalization standard deviation. There is no shared ImageNet-normalization fallback.

## Embedding Format

Each embedding file is a Python pickle dictionary keyed by origin ID:

```python
{
    origin_id: np.ndarray,  # shape: (num_patches_for_origin, model_output_dim)
}
```

Expected current cardinality:

| Metric | Value |
| --- | ---: |
| Origins | 203 |
| Patches | 3,086 |
| Virchow feature dimension | 2,560 |
| Accepted Phase 2 model | Virchow |

## Visual Inspection

The interactive Plotly files are exploratory views of patch-level and origin-level PCA projections. They help show whether embeddings contain visible morphology structure, but they are not the acceptance rule for Phase 2.

Representative Phase 1 visualizations:

| View | File |
| --- | --- |
| UNI patch clusters | [patch_clusters_3d_uni.html](visualizations/patch_clusters_3d_uni.html) |
| UNI origin clusters | [wsi_clusters_3d_uni.html](visualizations/wsi_clusters_3d_uni.html) |
| CTransPath patch clusters | [patch_clusters_3d_ctranspath.html](visualizations/patch_clusters_3d_ctranspath.html) |
| CTransPath origin clusters | [wsi_clusters_3d_ctranspath.html](visualizations/wsi_clusters_3d_ctranspath.html) |

How to read these visualizations:

- Each point is a patch or origin-level mean embedding.
- Axes are PCA components used only for visualization.
- Nearby points have similar frozen embedding representations.
- Visual separation is exploratory. Phase 2 still applies explicit eligibility rules and model-selection criteria.

See [Visualizations](visualizations/README.md) for the complete copied HTML set.

## Reproducibility Checks

Before using Phase 1 outputs downstream, confirm:

- `origin_patch_mapping.csv` contains 203 origins.
- Every selected embedding file has the same 203 origin keys.
- Total embedded patch rows sum to 3,086.
- `results/phase1_metadata/master_runs.json` records the completed model runs.

Run Phase 1 from the repository root:

```bash
uv run python scripts/phase1.py
```

<div class="ndb-next" markdown>
<strong>Next result:</strong> [Phase 2 Results](phase2-results.md)
</div>

**Last verified**: 29 June 2026.
