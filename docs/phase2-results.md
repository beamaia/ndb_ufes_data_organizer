# Phase 2 Results

Phase 2 selects a fold-ready morphology signal from frozen Phase 1 embeddings. The current accepted selection is Virchow with PCA=2 and K=3.

## Selection Rule

A configuration is eligible only when it satisfies both constraints:

| Constraint | Required Value |
| --- | ---: |
| Minimum cluster size | at least 11 origins |
| Largest/smallest cluster ratio | at most 5.0 |

Eligible configurations are ranked by mean silhouette across repeated runs. The selected result is derived from the grid. It is not hardcoded.

## Accepted Configuration

| Field | Value |
| --- | ---: |
| Model | Virchow |
| Embedding run | `20260628_223154` |
| PCA components | 2 |
| K-Means clusters | 3 |
| Mean silhouette | 0.663275 |
| Explained variance | 0.457611 |
| Cluster sizes | 101, 67, 35 |
| Largest/smallest ratio | 2.885714 |

Swin's former degenerate result is superseded. It produced fold-hostile cluster structure and is rejected by the current eligibility gate.

## Model Comparison

<iframe class="plotly-embed" src="../visualizations/generated/phase2_model_selection.html" title="Phase 2 model selection" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: each bar is the best eligible silhouette score for one model. Green bars passed fold-readiness constraints. Rejected models are not allowed to become Phase 3 inputs, even if an individual silhouette value looks high.</p>

## Tuning Diagnostics

The selection summary above is the final decision view, but it is not the only Phase 2 evidence. The full tuning diagnostics include:

- Elbow curves for inertia across K-Means cluster counts.
- Inertia-by-PCA curves for each model.
- Silhouette-by-K curves.
- Averaged silhouette heatmaps across PCA components and K clusters.
- Top 10 configurations per model, with fold-ready and rejected configurations separated.

These plots are explained for readers without a clustering background on [Phase 2 Tuning Diagnostics](phase2-tuning-diagnostics.md).

## Output Artifacts

| Artifact | Purpose |
| --- | --- |
| `results/phase2/tuning/phase2_model_selection.csv` | One-row-per-model selection summary. |
| `results/phase2/tuning/clustering_params_{model}.json` | Accepted parameters or rejection diagnostics for each model. |
| `clustering_params.json` | Global accepted selection consumed by Phase 3. |
| `docs/phase2-tuning-diagnostics.md` | Website page with the full Phase 2 tuning diagnostic figures. |
| `docs/assets/generated/phase2_model_selection.png` | Static documentation figure. |
| `results/phase4/thesis_figures/phase2_model_selection.svg` | Thesis-ready vector export. |
| `results/phase4/thesis_figures/phase2_model_selection.pdf` | Thesis-ready PDF export. |

## Interpretation

Virchow is accepted because it has the highest mean silhouette among configurations that can support six-fold construction. The selection uses frozen external embeddings and unsupervised clustering. It does not use downstream classifier validation or test performance.

<div class="ndb-next" markdown>
<strong>Next result:</strong> [Phase 3 Results](phase3-results.md)
</div>

**Last verified**: 29 June 2026.
