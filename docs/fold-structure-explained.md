# Understanding Fold Structure

## Origins and Patches

The matched subset contains 203 origins and 3,086 image patches. An origin is the parent specimen image. Each origin contributes multiple patches. Origin `0` is a valid parent with 20 patches.

The core invariant is:

```text
one origin_id -> one fold
```

All patches inherit the fold of their parent origin. Randomly splitting patch rows would leak specimen-specific information between training and evaluation.

## Why Six Folds

Six folds retain enough origins per evaluation split while allowing each supported diagnosis, morphology cluster, gender, and age group to be spread throughout the cross-validation structure. Six is a project design choice, not a claim that it is universally optimal.

## Morphology Signal

Phase 2 selected frozen Virchow embeddings with PCA=2 and K=3. The morphology clusters contain 101, 67, and 35 origins. Configurations are not accepted unless every cluster has at least 11 origins and the largest/smallest ratio is at most 5.

This feature use does not by itself prevent the same backbone from being trained later. The leakage boundary is procedural: do not fine-tune it on the full labeled dataset before fold construction, and do not choose folds based on downstream validation/test results.

## Combined Strata

Phase 3 combines:

- origin diagnosis.
- morphology cluster.
- gender.
- age group.

All four passed missingness and six-fold support checks in the current run. Other clinical fields remain descriptive.

## Round-Robin LPT

Within each combined stratum, origins are sorted by patch count, largest first. Successive blocks of six are assigned to six distinct folds. At each step, Phase 3 chooses the least-loaded unused fold, then breaks ties by origin count and fold ID.

This differs from global greedy LPT: a complete six-origin block cannot place two origins into the same fold. Consequently, the count of any combined stratum differs by no more than one across folds.

## Validated Result

| Fold | Origins | Origin % | Patches | Patch % |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 31 | 15.27 | 520 | 16.85 |
| 1 | 36 | 17.73 | 510 | 16.53 |
| 2 | 31 | 15.27 | 511 | 16.56 |
| 3 | 34 | 16.75 | 511 | 16.56 |
| 4 | 37 | 18.23 | 524 | 16.98 |
| 5 | 34 | 16.75 | 510 | 16.53 |

The maximum/minimum patch ratio is 1.02745. No origin spans folds, no row is unassigned, and every combined stratum has a fold-count range at most one.

## Fold Balance

The first check is total fold size. Origins and patches are shown together because a fold can contain a similar number of origins but still differ in patch count when some origins contribute more patches than others.

<iframe class="plotly-embed" src="../visualizations/generated/fold_origin_patch_percent.html" title="Fold origin and patch percentages" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: each fold has one origin-share bar and one patch-share bar. A good fold design keeps both close while still respecting origin locking and stratum spread.</p>

## Diagnosis Spread

Diagnosis is one of the variables that must remain visible after fold assignment. The patch-level view is shown first because patches are the rows used for most downstream image-model training. The origin-level view follows because folds are actually assigned at origin level.

<iframe class="plotly-embed" src="../visualizations/generated/fold_diagnosis_percent.html" title="Patch diagnosis share within each fold" loading="lazy"></iframe>

<p class="figure-caption">Each fold bar sums to 100 percent. The segments show how patch-level diagnostic labels are distributed inside that fold.</p>

<iframe class="plotly-embed" src="../visualizations/generated/fold_origin_diagnosis_percent.html" title="Origin Diagnosis Share Within Each Fold" loading="lazy"></iframe>

<p class="figure-caption">This is the origin-level companion view. It checks the distribution that Phase 3 directly assigns before folds are broadcast to patches.</p>

## Stratification Variables

Phase 3 included four required stratification variables: diagnosis, morphology cluster, gender, and age group. These plots show the fold-level origin share for the non-diagnosis variables.

<iframe class="plotly-embed" src="../visualizations/generated/fold_morph_cluster_percent.html" title="Morphology Cluster Share Within Each Fold" loading="lazy"></iframe>

<p class="figure-caption">Morphology clusters come from the accepted Virchow PCA=2/K=3 Phase 2 selection. This plot checks whether the selected morphology signal is represented across folds.</p>

<iframe class="plotly-embed" src="../visualizations/generated/fold_gender_percent.html" title="Gender share within each fold" loading="lazy"></iframe>

<p class="figure-caption">Gender passed the required support check and is included in the combined stratum key.</p>

<iframe class="plotly-embed" src="../visualizations/generated/fold_age_group_percent.html" title="Age Group Share Within Each Fold" loading="lazy"></iframe>

<p class="figure-caption">Age Group passed the required support check and is included in the combined stratum key.</p>

## Combined Stratum Spread

The assignment algorithm does not balance each variable independently in isolation. It balances combined strata formed from diagnosis, morphology cluster, gender, and age group.

<iframe class="plotly-embed" src="../visualizations/generated/fold_combined_stratum_spread.html" title="Combined stratum spread across folds" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: the x-axis is the maximum minus minimum origin count across the six folds for each combined stratum. The current validation requires the maximum range to be at most 1.</p>

Use `fold_assignments_patch_level.csv` for patch training rows and `fold_assignments_origin.csv` for origin-level analysis. Fold rotation should be declared before comparing downstream models.

<div class="ndb-next" markdown>
<strong>Related result:</strong> [Phase 3 Results](phase3-results.md)
</div>
