# Phase 3 Results

Phase 3 consumes the accepted Phase 2 selection and writes deterministic leakage-safe fold assignments. The current output assigns all 203 origins and all 3,086 patch rows.

## Validation Summary

| Metric | Value |
| --- | ---: |
| Origins assigned | 203 |
| Patches assigned | 3,086 |
| Fold IDs | 0 through 5 |
| Patch-count ratio | 1.02745 |
| Maximum folds per origin | 1 |
| Maximum per-stratum fold-count range | 1 |

Origin `0` is retained. The older 202-origin and 3,066-patch artifacts are superseded.

## Fold Balance

| Fold | Origins | Origin % | Patches | Patch % |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 31 | 15.27 | 520 | 16.85 |
| 1 | 36 | 17.73 | 510 | 16.53 |
| 2 | 31 | 15.27 | 511 | 16.56 |
| 3 | 34 | 16.75 | 511 | 16.56 |
| 4 | 37 | 18.23 | 524 | 16.98 |
| 5 | 34 | 16.75 | 510 | 16.53 |

<iframe class="plotly-embed" src="../visualizations/generated/fold_origin_patch_percent.html" title="Fold origin and patch percentages" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: origin percentages count parent images. Patch percentages count patch rows. A fold may have fewer origins and still have a similar patch share if its origins contain more patches.</p>

<iframe class="plotly-embed" src="../visualizations/generated/fold_diagnosis_percent.html" title="Fold diagnosis percentages" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: each bar sums to 100 percent within one fold. The segments show the diagnosis mix among patch rows in that fold.</p>

For the fuller stratification view, see [Fold Structure](fold-structure-explained.md).

## Output Artifacts

| Artifact | Purpose |
| --- | --- |
| `results/phase3_fold_creation/fold_assignments_origin.csv` | One row per origin with fold and stratification metadata. |
| `results/phase3_fold_creation/fold_assignments_patch_level.csv` | One row per patch with inherited fold assignment. |
| `results/phase3_fold_creation/stratification_variables_audit.csv` | Required and descriptive variable audit. |
| `results/phase3_fold_creation/fold_validation.json` | Machine-readable validation report. |
| `docs/assets/generated/fold_balance_summary.csv` | Documentation fold percentage summary. |
| `results/thesis_figures/fold_origin_patch_percent.svg` | Thesis-ready fold balance vector export. |
| `results/thesis_figures/fold_diagnosis_percent.svg` | Thesis-ready diagnosis balance vector export. |

## Interpretation

The fold construction passes the current leakage-safety contract:

- Every patch inherits the fold of its parent origin.
- No origin appears in more than one fold.
- Every requested fold ID exists.
- Combined strata are spread so their fold-count range is at most one.
- Patch imbalance remains below the 1.10 ceiling.

<div class="ndb-next" markdown>
<strong>Next read:</strong> [Fold Structure](fold-structure-explained.md)
</div>

**Last verified**: 29 June 2026.
