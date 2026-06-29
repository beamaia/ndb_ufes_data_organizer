# Data Dictionary

This page documents the current organized data files used by this repository. It focuses on public reuse: what each file contains, how files relate to each other, and which fields require caution.

## Dataset Levels

| Level | Meaning | Current key files |
| --- | --- | --- |
| Origin / WSI | Original whole-slide or origin-level image/metadata row. | `data/ndb_ufes/origin_level/csvs/ndb-ufes.csv`, `data/ndb_ufes/origin_level/csvs/fold_assignments_origin.csv` |
| Patch | Patch-level rows linked back to an origin. | `data/ndb_ufes/patch/parcial_pndb_ufes.csv`, `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv` |
| Link | Relationship images/files between original NDB-UFES and patch data. | `data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv` |

## Current Counts

| Item | Count |
| --- | ---: |
| Origin metadata rows in `ndb-ufes.csv` | 237 |
| Matched origins currently available for fold design | 203 |
| Patch rows in `parcial_pndb_ufes.csv` | 3,086 |
| Patch rows available for fold design | 3,086 |
| Planned number of folds | 6 |

The difference between 237 origin metadata rows and 203 matched origins should be documented as part of the matching/filtering process. Do not assume all original origins are present in the fold-design subset.

## Class Labels

Patch-level diagnosis distribution in the organized subset:

| Diagnosis | Patch count |
| --- | ---: |
| OSCC | 1,517 |
| Leukoplakia with dysplasia | 930 |
| Leukoplakia without dysplasia | 639 |

Origin-level diagnosis distribution in the matched fold-design subset:

| Diagnosis | Origin count |
| --- | ---: |
| OSCC | 81 |
| Leukoplakia with dysplasia | 72 |
| Leukoplakia without dysplasia | 50 |

## Understanding Fold Structure

Folds ensure leakage-safe training and validation. This section explains the design.

### Origin-Level Locking

The fundamental invariant is: **one origin → one fold**. All patches from an origin must be assigned to the same fold. This prevents the model from training and evaluating on different patches from the same specimen.

Example:
- Origin 5 has 20 patches
- Origin 5 is assigned to fold 2
- All patches 5_0, 5_1, ..., 5_19 are assigned to fold 2
- No patch from Origin 5 appears in folds 0, 1, 3, 4, or 5

### Fold Stratification

Folds are not randomly assigned. Instead, origins are distributed across folds to balance diagnostic class, morphological characteristics, gender, and age group. This ensures each fold is representative of the full dataset.

The stratification process:
1. Group origins by a stratification key (concatenation of diagnosis, morphology cluster, gender, age group)
2. Within each group, sort origins by patch count (largest first)
3. Assign each origin to the fold with the current smallest total patch count (greedy Longest Processing Time algorithm)

Result: folds have balanced patch counts and balanced representation of key variables.

See [Fold Structure Explained](fold-structure-explained.md) for algorithm details, balance metrics, and leakage safety guarantees.

## Required Fold Assignment Files

### Origin-Level Folds

Path:

```text
data/ndb_ufes/origin_level/csvs/fold_assignments_origin.csv
```

Rows: 203

Columns:

| Column | Meaning |
| --- | --- |
| `origin_id` | Origin/WSI identifier used by the matched fold-design subset. |
| `true_class` | Origin-level diagnostic class. |
| `morph_cluster` | Morphology cluster assigned during stratification. Existing artifacts use four clusters, but this should be audited against Phase 2. |
| `patch_count` | Number of patches from this origin in the matched subset. |
| `fold` | Fold assignment, integer `0` through `5`. |

Audit invariant: each `origin_id` must appear exactly once and have exactly one `fold`.

### Patch-Level Fold Summary

Path:

```text
data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level.csv
```

Rows: 203

This file is origin-level in practice, despite the filename. It contains one row per origin with comma-separated patch IDs and pipe-separated image paths.

Columns:

| Column | Meaning |
| --- | --- |
| `origin_id` | Origin identifier. |
| `class` | Diagnostic class. |
| `patch_count` | Number of patches for the origin. |
| `patch_ids` | Comma-separated patch IDs. |
| `image_paths` | Pipe-separated image paths. |
| `fold` | Fold assignment. |

Audit note: because this file is not one row per patch, downstream users who need patch-level rows should use the detailed or image-expanded files below.

### Patch-Level Detailed Folds

Path:

```text
data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv
```

Rows: 3,086

Columns:

| Column | Meaning |
| --- | --- |
| `patch_id` | Synthetic patch identifier in the current fold artifact, e.g. `0_0`. |
| `origin_id` | Parent origin. |
| `class` | Patch/origin diagnostic class used for fold balancing. |
| `morph_cluster` | Morphology cluster inherited from the origin. |
| `fold` | Fold assignment inherited from the origin. |

Audit invariant: every patch row must have a fold and all rows with the same `origin_id` must share the same fold.

### Patch-Level Folds With Image Paths

Path:

```text
data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv
```

Rows: 3,086

Columns:

| Column | Meaning |
| --- | --- |
| `patch_id` | Synthetic patch identifier in the current fold artifact. |
| `origin_id` | Parent origin. |
| `image_name` | Patch image name, e.g. `p0321`. |
| `image_path` | Path to patch image. |
| `class` | Diagnostic class. |
| `morph_cluster` | Morphology cluster inherited from the origin. |
| `fold` | Fold assignment inherited from the origin. |

This is the most convenient public file for users who need one row per patch plus an image reference.

## Source Metadata Files

### Patch Metadata

Path:

```text
data/ndb_ufes/patch/parcial_pndb_ufes.csv
```

Rows: 3,086

Important columns:

| Column | Meaning |
| --- | --- |
| `patch` | Patch image ID, e.g. `p0000`. |
| `origin` | Origin/WSI ID. |
| `public_id`, `lesion_id`, `patient_id` | Identifiers from the source dataset. |
| `path` | Origin image path/name from source metadata. |
| `localization` | Lesion/localization field. |
| `larger_size` | Size-related metadata field from source. |
| `tobacco_use` | Risk factor field: `Yes`, `No`, `Former`, or `Not informed`. |
| `alcohol_consumption` | Risk factor field: `Yes`, `No`, `Former`, or `Not informed`. |
| `sun_exposure` | Risk factor field: `Yes`, `No`, or `Not informed`. |
| `gender` | `M` or `F` in current organized subset. |
| `skin_color` | `White`, `Black`, `Brown`, or `Not informed` in current organized subset. |
| `age_group` | Encoded age group from source metadata: `0` = younger than 40 years, `1` = 40-60 years, `2` = older than 60 years. |
| `diagnosis` | Diagnostic class. |
| `dysplasia_severity` | Dysplasia severity metadata where applicable. |
| `TaskII`, `TaskIII`, `TaskIV` | Source task labels. |
| `top_left_x`, `top_left_y`, `bottom_right_x`, `bottom_right_y` | ROI/patch coordinate fields. Deferred for analysis until patch-origin-coordinate associations are rerun; some prior image-origin associations were incorrect. |

### Origin Metadata

Path:

```text
data/ndb_ufes/origin_level/csvs/ndb-ufes.csv
```

Rows: 237

This file contains origin-level metadata with similar diagnosis, demographic, risk factor, and task-label columns. The matched fold-design subset is smaller than this file.

## Task Labels

The source study defines four classification tasks across RMDS and NDB-UFES. This repository organizes NDB-UFES, so Task II, Task III, and Task IV are the relevant task fields.

| Task | Dataset | Labels | Definition |
| --- | --- | --- | --- |
| Task I | RMDS | Normal / OSCC | Histopathological-image classification for normal versus OSCC samples. No demographic or clinical data are available. Not part of this NDB-UFES organizer. |
| Task II | NDB-UFES | Leukoplakia / OSCC | Differentiates samples diagnosed as leukoplakia or OSCC. |
| Task III | NDB-UFES | Absence / Presence of dysplasia | Differentiates samples identified with or without dysplasia. OSCC lesions are labeled as presence of dysplasia. |
| Task IV | NDB-UFES | OSCC / Leukoplakia with dysplasia / Leukoplakia without dysplasia | Three-class diagnosis task. |

Observed task label values in the current patch metadata:

| Field | Observed values | Interpretation for users |
| --- | --- | --- |
| `TaskII` | `OSCC`, `Leukoplakia` | Binary OSCC vs leukoplakia grouping. |
| `TaskIII` | `Presence`, `Absence` | Dysplasia presence grouping; OSCC is included in `Presence`. |
| `TaskIV` | `OSCC`, `Leukoplakia with dysplasia`, `Leukoplakia without dysplasia` | Three-class diagnostic task. |

The source paper reports the full origin-level NDB-UFES task counts as: Task II: 146 leukoplakia and 91 OSCC; Task III: 180 presence and 57 absence; Task IV: 91 OSCC, 89 leukoplakia with dysplasia, and 57 leukoplakia without dysplasia.

## Demographics and Risk Factors

Patch-level observed distributions:

| Field | Values |
| --- | --- |
| `gender` | `M`: 1,850; `F`: 1,236 |
| `skin_color` | `Not informed`: 1,393; `White`: 1,184; `Black`: 335; `Brown`: 174 |
| `tobacco_use` | `Not informed`: 1,425; `Yes`: 920; `No`: 496; `Former`: 245 |
| `alcohol_consumption` | `Not informed`: 1,425; `No`: 743; `Former`: 500; `Yes`: 418 |
| `sun_exposure` | `Not informed`: 1,465; `No`: 1,123; `Yes`: 498 |
| `age_group` | `2` (> 60 years): 1,496; `1` (40-60 years): 1,392; `0` (< 40 years): 198 |

These fields are useful for factsheets, subgroup summaries, and fairness-aware reporting. They should not be treated as causal adjustment variables without a separate causal design.

## Validated Fold Artifacts

The canonical current files are under `results/phase3_fold_creation/`. They contain 203 origin rows and 3,086 patch rows and were regenerated from the accepted Virchow/PCA=2/K=3 selection. Earlier Swin-based and 202-origin files are superseded.

### Stratification Variable Audit

Path:

```text
results/phase3_fold_creation/stratification_variables_audit.csv
```

Columns:

| Column | Meaning |
| --- | --- |
| `column` | Candidate origin-level variable reviewed for fold construction. |
| `role` | `required`, `optional`, or `descriptive`. |
| `status` | Inclusion/exclusion decision, such as `included_required`, `included_optional`, `excluded_descriptive_only`, `excluded_high_missingness`, or `excluded_low_support`. |
| `missing_count` | Number of origin rows considered missing after normalizing null-like values and `Not informed`. |
| `missing_rate` | Fraction of origin rows considered missing. |
| `n_categories` | Number of non-missing categories. |
| `min_category_count` | Smallest non-missing category count. |
| `reason` | Human-readable explanation for the decision. |

By default, fold construction should use `origin_diagnosis`, `morph_cluster`, `gender`, and `age_group`. Other demographic and clinical variables are descriptive factsheet fields unless they are explicitly promoted and pass the audit gate. Variables with high `Not informed` or missingness should not silently affect fold assignment.

## Morphology Clusters

The accepted origin-level morphology clusters contain:

| Cluster | Origin count |
| --- | ---: |
| 0 | 101 |
| 1 | 67 |
| 2 | 35 |

Cluster labels are nominal K-Means identifiers, not diagnoses or severity levels.

## File Status Notes

- `data/` is ignored by Git in the current `.gitignore`; data files are expected to be handled by DVC or local regeneration.
- `results/` is currently untracked and includes generated artifacts.
- Several root Markdown files are untracked audit/deliverable notes and should be promoted, archived, or deleted after manual review.
