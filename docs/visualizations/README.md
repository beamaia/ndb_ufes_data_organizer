# Visualization Files

This folder contains interactive Plotly visualizations used by the documentation site.

## Phase 1 Exploratory Visualizations

The copied Phase 1 files show patch-level and origin-level 3D PCA projections for the extracted embeddings.

Representative files:

- [UNI patch clusters](patch_clusters_3d_uni.html)
- [UNI origin clusters](wsi_clusters_3d_uni.html)
- [CTransPath patch clusters](patch_clusters_3d_ctranspath.html)
- [CTransPath origin clusters](wsi_clusters_3d_ctranspath.html)
- Additional files for the other extracted models.

These views are exploratory. Phase 2 selection is made by eligibility rules and mean silhouette, not by visual preference.

## Generated Result Visualizations

The generated result and dataset-statistics figures are created by:

```bash
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py
```

The complete dataset-statistics Plotly set is available on [Exploratory Analysis](../exploratory-analysis.md) with fast static previews and in-place interactive loading. [Dataset Figure Gallery](../dataset-figure-gallery.md) keeps the same generated set as a neutral figure index.

Interactive outputs:

- [Phase 2 model selection](generated/phase2_model_selection.html)
- [Phase 2 tuning diagnostics](../phase2-tuning-diagnostics.md)
- [Dataset diagnosis summary](generated/dataset_diagnosis_summary.html)
- [Source task counts](generated/source_task_counts.html)
- [Top Cramer's V associations](generated/top_cramers_v.html)
- [Fold origin and patch percentages](generated/fold_origin_patch_percent.html)
- [Fold diagnosis percentages](generated/fold_diagnosis_percent.html)
- [Fold origin diagnosis percentages](generated/fold_origin_diagnosis_percent.html)
- [Fold morphology cluster percentages](generated/fold_morph_cluster_percent.html)
- [Fold gender percentages](generated/fold_gender_percent.html)
- [Fold age-group percentages](generated/fold_age_group_percent.html)
- [Combined stratum spread](generated/fold_combined_stratum_spread.html)
- 55 Phase 2 tuning diagnostic figures under `generated/phase2_*.html`.
- 52 converted dataset-statistics figures under `generated/01a_*.html` through `generated/10_*.html`.

Static documentation copies are saved under:

```text
docs/assets/generated/
```

Plotly preview PNGs are saved under:

```text
docs/assets/generated/plotly_previews/
```

Curated thesis-ready PNG, SVG, and PDF copies are saved under:

```text
results/phase4/thesis_figures/
```

To generate full Plotly PNG, SVG, and PDF copies for thesis reuse, run:

```bash
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py --export-plotly-thesis
```

## Refresh Phase 1 Visualization Files

To copy regenerated Phase 1 visualization HTML files:

```bash
uv run python scripts/src/docs/copy_visualizations.py
```

This script copies regenerated HTML visualization files into `docs/visualizations/` and normalizes their filenames for cleaner URLs.

The visualization HTML files use the shared local `plotly-3.5.0.min.js` asset in this directory instead of embedding a full Plotly bundle in every file. This keeps GitHub Pages deployments smaller while preserving offline/local rendering.

## Viewing

Once files are in place:

1. Run `uv run --extra docs python -m mkdocs serve -a 127.0.0.1:8000` from the project root.
2. Open `http://127.0.0.1:8000/ndb_ufes_data_organizer/visualizations/`.
3. Open the linked HTML files for interactive Plotly views.
