# Dataset Factsheet

I use this factsheet to explain the organized NDB-UFES fold files, the atlas-backed linkage view, and the limits that matter for reuse. It is written for anyone who needs the provenance, labels, folds, demographics/risk factors, and leakage rules in one place.

## Dataset Identity

Name: NDB-UFES Data Organizer fold files

Source dataset:

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.

Public source page:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

Lab attribution:

[Nature-inspired Computing Lab, Labcin](https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling)

## Purpose of This Repository

I organize the public dataset into grouped folds and publish the decisions
needed to reuse them. Model training remains in the separate training
repository; this repository publishes the validated, sanitized thesis result
summary and provenance.

Main outputs:

- origin-level fold assignments,
- patch-level fold assignments,
- data dictionary,
- reproducibility notes,
- validation guide,
- public factsheet.

## Thesis Experiment Update

The completed thesis/article comparison uses the full 3,763-patch P-NDB-UFES
scope in two experiments: the original-comparable Batch 1 split and the
patient-first grouped, lower-contamination-risk Batch 2 split. MobileNetV2,
DenseNet-121, and ResNet-50 were evaluated. Batch 3 is retained only as an
exploratory Virchow-pruned archive. See [Thesis Experiment Design](thesis-experiment-batches.md)
and [Canonical Experiment Results](experiment-results.md).

The matched-subset fold files below remain useful because they document the SAB-linked subset where source/WSI linkage and embeddings were available at that stage. Their 3,086-patch count should be described as the SAB-linked subset count, not as the full P-NDB-UFES patch count.

## Validated WSI Atlas View

The atlas provides a second, complementary view of the full 3,763-patch scope. Through recovered coordinate and pixel-containment evidence, all 3,763 patches are assigned to 251 validated WSI IDs: 203 with public NDB-UFES + SAB evidence and 48 SAB-only recovered WSI groups. The separate thesis relationship table still reports 3,086 rows with recovered metadata linkage and 677 rows with missing metadata linkage. These are different linkage layers, not competing dataset totals.

The public-safe [Atlas Index](atlas-index.md) provides one searchable row per validated WSI. It excludes raw SAB case prefixes, image names, and local filesystem paths. Use the [Atlas Guide](atlas-guide.md) for the evidence definitions and interpretation cautions.

## Matched Subset

Current matched subset available for fold design:

| Item | Count |
| --- | ---: |
| Patch rows | 3,086 |
| Matched origins currently available for fold design | 203 |
| Planned folds | 6 |
| Diagnostic classes | 3 |

Original origin-level metadata currently contains 237 rows. The matched subset contains the origins/patches currently available for fold design.

## Diagnostic Labels

Patch-level class distribution:

| Diagnosis | Patch count |
| --- | ---: |
| OSCC | 1,517 |
| Leukoplakia with dysplasia | 930 |
| Leukoplakia without dysplasia | 639 |

Origin-level fold distribution:

| Diagnosis | Origin count |
| --- | ---: |
| OSCC | 81 |
| Leukoplakia with dysplasia | 72 |
| Leukoplakia without dysplasia | 50 |

## Task Labels

The source study defined four classification tasks across RMDS and NDB-UFES. This organizer focuses on the NDB-UFES tasks:

| Task | Dataset | Labels | Definition |
| --- | --- | --- | --- |
| Task I | RMDS | Normal / OSCC | Classification using histopathological images only. No demographic or clinical data are available. This task is outside this NDB-UFES organizer. |
| Task II | NDB-UFES | Leukoplakia / OSCC | Classification differentiating samples diagnosed as leukoplakia or OSCC. The source study used histopathological images plus demographic/clinical data. |
| Task III | NDB-UFES | Absence / Presence of dysplasia | Classification differentiating samples with or without dysplasia. OSCC lesions are labeled as presence of dysplasia. |
| Task IV | NDB-UFES | OSCC / Leukoplakia with dysplasia / Leukoplakia without dysplasia | Three-class classification differentiating OSCC, leukoplakia with dysplasia, and leukoplakia without dysplasia. |

Observed task label values in the current patch metadata:

| Field | Values |
| --- | --- |
| `TaskII` | `OSCC`, `Leukoplakia` |
| `TaskIII` | `Presence`, `Absence` |
| `TaskIV` | `OSCC`, `Leukoplakia with dysplasia`, `Leukoplakia without dysplasia` |

Source-paper full origin-level NDB-UFES task counts:

| Task | Class | Origin count |
| --- | --- | ---: |
| Task II | Leukoplakia | 146 |
| Task II | OSCC | 91 |
| Task III | Presence | 180 |
| Task III | Absence | 57 |
| Task IV | OSCC | 91 |
| Task IV | Leukoplakia with dysplasia | 89 |
| Task IV | Leukoplakia without dysplasia | 57 |

## Demographics and Risk Factors

The organized patch metadata includes:

- `gender`
- `skin_color`
- `age_group` (`0`: younger than 40 years, `1`: 40-60 years, `2`: older than 60 years)
- `tobacco_use`
- `alcohol_consumption`
- `sun_exposure`
- `localization`
- `larger_size`
- `dysplasia_severity`
- ROI coordinates: `top_left_x`, `top_left_y`, `bottom_right_x`, `bottom_right_y`. These are deferred because patch-origin-coordinate associations need to be rerun before ROI coverage figures are published.

Observed missingness is substantial for some fields. For example, patch-level `Not informed` values appear in skin color, tobacco use, alcohol consumption, and sun exposure. These fields are useful for documentation and subgroup reporting, but should not be treated as complete clinical covariates without checking missingness.

## Exploratory Findings Used In This Factsheet

The exploratory figures are not separate from this factsheet. They are the evidence used to decide what should be summarized, what should be treated cautiously, and what should remain descriptive.

| Finding | Evidence | Interpretation |
| --- | --- | --- |
| Matched subset. | 203 matched origins from 237 source metadata rows. | The fold files describe the current matched fold-design subset, not every row in the source metadata copy. |
| Patch counts and origin counts differ. | 81 OSCC origins produce 1,517 OSCC patch rows. 72 leukoplakia-with-dysplasia origins produce 930 patch rows. 50 leukoplakia-without-dysplasia origins produce 639 patch rows. | Patch-level class balance should not be read as origin-level prevalence. |
| Risk-factor metadata has high `Not informed` rates. | At origin level, `Not informed` is 50.25% for sun exposure, 48.28% for alcohol consumption, 48.28% for tobacco use, and 47.29% for skin color. | These fields are useful for context and review, but they should not silently control fold construction. |
| Patch-level risk-factor metadata shows the same limitation. | At patch level, `Not informed` is 47.47% for sun exposure, 46.18% for alcohol consumption, 46.18% for tobacco use, and 45.14% for skin color. | Patch-row metadata inherits the same caution. |
| Dysplasia severity is incomplete. | Missingness is 64.53% at origin level and 69.86% at patch level. | Dysplasia severity should be interpreted with diagnosis context and should not be treated as a complete covariate. |
| Fold stratification uses supported variables. | Phase 3 used diagnosis, Virchow morphology cluster, gender, and age group. | These variables passed the required missingness and six-fold support checks for the current run. |

See [Exploratory Analysis](exploratory-analysis.md) for the full preview-first Plotly figure set and [Understanding Fold Structure](fold-structure-explained.md) for fold-level stratification views.

## Generated Dataset Figures

These figures summarize the current matched subset and source-paper task counts. Interactive Plotly versions are embedded below. Static documentation copies are saved under `docs/assets/generated/`, and thesis-ready exports are saved under `results/phase4/thesis_figures/`.

How to read these figures:

- Count bars show how many rows belong to each label.
- Percent labels show the share inside the plotted level, usually origin-level or patch-level.
- Origin-level plots count parent images. Patch-level plots count patch rows.
- Association matrices are descriptive. They do not prove causality or validate downstream model performance.

The larger exploratory figure set is documented on [Exploratory Analysis](exploratory-analysis.md), and the full converted Plotly gallery is available on [Dataset Figure Gallery](dataset-figure-gallery.md).

<iframe class="plotly-embed" src="../visualizations/generated/dataset_diagnosis_summary.html" title="Matched subset diagnosis counts" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: origin counts show parent images. Patch counts show patch rows. The two views differ because origins contribute different numbers of patches.</p>

<iframe class="plotly-embed" src="../visualizations/generated/source_task_counts.html" title="Source task counts" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: each panel is one source-paper task. Bars are origin counts for the classes defined by that task.</p>

<iframe class="plotly-embed" src="../visualizations/generated/top_cramers_v.html" title="Top categorical associations by Cramer's V" loading="lazy"></iframe>

<p class="figure-caption">How to read this figure: each bar is Cramer's V for one pair of categorical variables. Values closer to 0 indicate weak association. Values closer to 1 indicate stronger association. This is a descriptive truth-table-style summary, not a causal test.</p>

## Fold Construction Status

Current thesis note: use the two-experiment design in
[Thesis Experiment Design](thesis-experiment-batches.md). The paragraph below
describes the older SAB-linked matched-subset Phase 3 organizer run.

The current fold construction completed and passed its strict validation report:

- all patches from the same origin stay in the same fold.
- folds are balanced by patch count.
- folds preserve diagnostic class distribution.
- morphology-aware clustering can be used as an additional stratification signal.

Phase 2 selected frozen Virchow embeddings with PCA=2 and K=3 after applying minimum cluster-size and maximum imbalance constraints. Phase 3 assigned all 203 origins and 3,086 patches. Fold patch counts are 520, 510, 511, 511, 524, and 510. No origin spans folds. Earlier Swin and 202-origin artifacts are superseded.

## Leakage-Safe Usage

Required:

- split by `fold`, not by random patch rows.
- keep all rows with the same `origin_id` in the same train/validation/test partition.
- once finalized, use the provided fold assignments when comparing models.
- document which fold(s) were used for train, validation, and test.

Avoid:

- random patch-level splits.
- selecting folds after seeing downstream model performance.
- fine-tuning an embedding model on all labels before using its features to construct folds.
- treating patches from the same origin as independent observations in evaluation.

Frozen external pretrained embeddings used only for unsupervised morphology-aware stratification are acceptable as a data organization step, provided downstream model performance did not influence the stratification choice.

## Known Caveats

- Some generated root Markdown files are historical notes rather than canonical documentation.
- `scripts/phase4.py` and its older analysis modules have not been accepted as part of the current release path.
- Current canonical folds are under `results/phase3/fold_creation/`. Similarly named files under data directories may be historical and should not replace them.
- `fold_assignments_patch_level.csv` under the canonical results directory contains exactly 3,086 patch rows.
- Coordinate-derived ROI coverage plots are deferred. Patch-origin-coordinate associations need to be regenerated before patch coverage areas are shown on origin images.
- Chi-square tests in validation scripts should not be interpreted as proof that folds are identical.

## Recommended Citation Language

This project is not packaged as a reusable Python package yet. If using the current fold assignment files or documentation from this repository, cite the original dataset and describe this repository as a fold/data-organization layer. Example:

```text
We used the public NDB-UFES dataset (Mendeley Data V4, doi: 10.17632/bbmmm4wgr8.4) with origin-level cross-validation folds generated by the NDB-UFES Data Organizer. Folds were constructed so that patches from the same origin image did not appear in multiple folds.
```
