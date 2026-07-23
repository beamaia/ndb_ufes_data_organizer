# Data Dictionary

This page documents the current organized data files used by this repository. It focuses on public reuse: what each file contains, how files relate to each other, and which fields require caution.

## Which source answers which question?

The following map identifies the authoritative source for each question. The
files are related, but they do not describe identical scopes.

| Question | Use this source | Current scope | Do not substitute it with |
| --- | --- | ---: | --- |
| What is in the final thesis comparison? | [Thesis Experiment Design](thesis-experiment-batches.md) and the current relationship files | Two 3,763-row experiments; Batch 3 archived as exploratory | The older 3,086-row fold-design run |
| Which patches belong in the older leakage-safe fold files? | `results/phase3/fold_creation/` and the Phase 1--3 pages | 3,086 patches, 203 origins, 6 folds | The full-scope thesis batch CSVs |
| Which source image contains each atlas patch? | `results/phase0/validated_linkage/` or the public [Atlas Index](atlas-index.md) | 3,763 SAB-linked patches, 251 source-image groups, coordinates for all represented patches | The 3,086 public NDB-UFES-matched rows |
| What can be loaded by the public website? | `docs/assets/atlas/` plus the Markdown pages | 251 public-pseudonymous source-image rows and small JSON contracts | The root public PDF remains a repository download; the LAB PDF, editable DOCX, and raw SAB crosswalk are excluded |
| Where are label and metadata disagreements summarized? | [Metadata Conflict Review](metadata-conflict-review.md) and `metadata_conflict_summary.json` | 1,489 atlas conflict-flagged rows | A silent relabeling or automatic exclusion rule |

When one layer changes, its source artifact, public summary, and corresponding
[Atlas Gap Map](atlas-gap-map.md) entry must be updated together. This prevents
one number from acquiring different meanings on different pages.

## Dataset Levels

| Level | Meaning | Current key files |
| --- | --- | --- |
| Origin / source image | Original source-image or origin-level metadata row. These images are not established as whole-slide images. | `data/ndb_ufes/origin_level/csvs/ndb-ufes.csv`, `results/phase3/fold_creation/fold_assignments_origin.csv` |
| Patch | Patch-level rows linked back to an origin. | `data/ndb_ufes/patch/parcial_pndb_ufes.csv`, `results/phase3/fold_creation/fold_assignments_patch_level.csv` |
| Link | Relationship images/files between original NDB-UFES and patch data. | `data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv` |

## Current NDB-UFES Match Counts

The current thesis/article reassessment uses all 3,763 SAB-linked P-NDB-UFES
patches. It also records which rows can be matched to a public NDB-UFES origin
image and its metadata.

| Item | Count |
| --- | ---: |
| Full P-NDB-UFES patch rows | 3,763 |
| Patch rows matched to public NDB-UFES origins | 3,086 |
| SAB-linked patch rows without a public NDB-UFES origin match | 677 |
| P-NDB origin or fallback groups | 880 |
| Linked P-NDB origins | 203 |
| Missing-linkage fallback groups | 677 |

Updated relationship files:

| File | Level | Rows | Meaning |
| --- | --- | ---: | --- |
| `data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv` | Patch | 3,763 | Current patch-level table recording SAB linkage and the optional public NDB-UFES origin match. |
| `data/ndb_ufes/link_level/csvs/pndb_ndb_origin_relationships.csv` | Origin/group | 880 | Current origin/fallback-group relationship summary. |
| `results/phase3/current_thesis_batches/linkage_scope_summary.csv` | Summary | 6 | Counts for thesis figures and tables. |

The counts below describe the public NDB-UFES-matched organizer files and
should not be used alone as the full 3,763-patch experiment scope.

## Source-Image Atlas Index

The atlas linkage output is a separate, public-pseudonymous view of the same
3,763 patch rows. It assigns all rows to a source-image group using recovered
coordinate/pixel-containment evidence, including rows whose thesis metadata
linkage is missing.

The existing `*_wsi_*` field names and pseudonyms are retained for
compatibility with generated artifacts. They identify source-image groups and
do not establish that the underlying images are whole-slide images.

| File | Level | Rows | Meaning |
| --- | --- | ---: | --- |
| `docs/assets/atlas/validated_wsi_index.csv` | Source image | 251 | One public-safe row per source-image group. |
| `docs/assets/atlas/atlas_manifest.json` | Manifest | 1 | Counts, source artifacts, privacy mode, and excluded private fields. |
| `docs/assets/atlas/atlas_schema.json` | Schema | 1 | Versioned public-index field contract: types, nullability, allowed source roles, and CSV encodings. |
| `docs/assets/atlas/metadata_conflict_summary.json` | Aggregate review | 1 | Public-safe counts describing complete-label agreement, reconstructed-metadata disagreement, missing metadata, and mismatch pairs. |
| `docs/assets/atlas/atlas_methods.json` | Methods | 1 | Implemented coordinate, pair-metric, threshold, pair-relation, and area-denominator contract; original DOCX renderer provenance remains pending. |
| `docs/assets/atlas/release_facts.json` | Release facts | 1 | Public aggregate atlas scope, canonical Batch 1/2 status, and exploratory Batch 3 review totals. |
| `results/phase0/validated_linkage/validated_patch_wsi_linkage.csv` | Patch | 3,763 | Atlas-level patch-to-source-image evidence and recovered coordinates. |
| `results/phase0/validated_linkage/validated_wsi_inventory.csv` | Source image | 251 | Source inventory used to build the public index. |

The public index includes these fields:

| Field | Meaning |
| --- | --- |
| `validated_wsi_id` | Retained compatibility name for the pseudonymous source-image group. |
| `source` | `both` for public NDB-UFES + SAB evidence, or `SAB-only recovered source image`. |
| `patch_count` | Number of atlas patches assigned to the source image. |
| `patch_pair_count` | Number of unordered same-source-image patch pairs, `n × (n - 1) / 2`. |
| `similarity_pair_count` | Number of same-source-image pair rows present in the validated similarity artifact; it can be lower than `patch_pair_count`. |
| `patches_with_overlap` | Number of patches that overlap at least one other patch by recovered coordinates. |
| `overlapping_pair_count` | Number of same-source-image patch pairs with positive coordinate overlap. |
| `mapped_image_area_percent` | Union of clipped patch boxes divided by displayed source-image area. |
| `repeated_sampled_area_percent` | Multiply-covered coordinate area divided by mapped patch union area. |
| `repeated_full_wsi_image_area_percent` | Retained field name for multiply-covered coordinate area divided by displayed source-image area. |
| `ndb_wsi_label`, `sab_wsi_label` | Retained field names for source-level labels; these may differ and should not be silently merged. |
| `patches_oscc`, `patches_with_dysplasia`, `patches_without_dysplasia` | Counts of complete patch labels carried by the validated linkage output. |
| `evidence_summary` | JSON-like count of atlas linkage-evidence categories for the source-image group. |
| `metadata_conflict_patch_count` | Patches where the atlas records a metadata conflict requiring caution. |

Raw SAB case prefixes, image names, and local paths are intentionally excluded. See [Atlas Index](atlas-index.md) for the downloadable files and [Atlas Guide](atlas-guide.md) for the two linkage layers.

## Matched-Subset Counts

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

| Topic | Meaning |
| --- | --- |
| Origin | Origin 5 has 20 patches. |
| Assigned fold | Origin 5 is assigned to fold 2. |
| Patch inheritance | All patches from Origin 5 are assigned to fold 2. |
| Leakage rule | No patch from Origin 5 appears in folds 0, 1, 3, 4, or 5. |

### Fold Stratification

Folds are not randomly assigned. Instead, origins are distributed across folds to balance diagnostic class, morphological characteristics, gender, and age group. This ensures each fold is representative of the full dataset.

The stratification process:

1. Group origins by a stratification key (concatenation of diagnosis, morphology cluster, gender, age group)
2. Within each group, sort origins by patch count (largest first)
3. Process each group in blocks of six origins
4. Assign each origin in a block to a distinct currently least-loaded fold
5. Break ties by fold origin count and then fold ID

Result: folds have balanced patch counts and each supported combined stratum differs by at most one origin across folds.

See [Fold Structure Explained](fold-structure-explained.md) for algorithm details, balance metrics, and leakage safety guarantees.

## Required Fold Assignment Files

The canonical current fold files are under `results/phase3/fold_creation/`. Older similarly named CSVs under `data/ndb_ufes/` may remain from previous runs, but they should not replace the canonical Phase 3 outputs unless they are regenerated and validated.

### Origin-Level Folds

Path:

```text
results/phase3/fold_creation/fold_assignments_origin.csv
```

Rows: 203

Columns:

| Column | Meaning |
| --- | --- |
| `origin_id` | Source-image/origin identifier used by the matched fold-design subset. |
| `origin_diagnosis` | Origin-level diagnostic class. |
| `patch_diagnoses` | Pipe-separated patch-level diagnoses observed for the origin. |
| `gender`, `skin_color`, `age_group` | Demographic fields copied from the organized metadata. |
| `tobacco_use`, `alcohol_consumption`, `sun_exposure` | Risk-factor fields copied from the organized metadata. |
| `localization`, `larger_size` | Lesion metadata fields copied from the organized metadata. |
| `morph_cluster` | Accepted Phase 2 morphology cluster, from Virchow with PCA=2 and K=3. |
| `patch_count` | Number of patches from this origin in the matched subset. |
| `stratification_key` | Combined stratum used by Phase 3 for round-robin LPT assignment. |
| `fold` | Fold assignment, integer `0` through `5`. |

Validation invariant: each `origin_id` must appear exactly once and have exactly one `fold`.

### Patch-Level Folds

Path:

```text
results/phase3/fold_creation/fold_assignments_patch_level.csv
```

Rows: 3,086

Columns:

| Column | Meaning |
| --- | --- |
| `origin_id` | Parent origin. |
| `patch` | Source patch image ID, e.g. `p0020`. |
| `diagnosis` | Patch diagnostic class used for reporting and validation. |
| `gender`, `skin_color`, `age_group` | Demographic fields inherited from the parent origin metadata. |
| `tobacco_use`, `alcohol_consumption`, `sun_exposure` | Risk-factor fields inherited from the parent origin metadata. |
| `localization`, `larger_size` | Lesion metadata fields inherited from the parent origin metadata. |
| `fold` | Fold assignment inherited from the origin. |

Validation invariant: every patch row must have a fold and all rows with the same `origin_id` must share the same fold.

### Legacy Data-Directory Fold Files

The repository may also contain fold CSVs under `data/ndb_ufes/origin_level/csvs/` and `data/ndb_ufes/patch_level/csvs/`. Treat those as local or historical copies unless they are explicitly synchronized with `results/phase3/fold_creation/` after a validated Phase 3 run.

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
| `origin` | Source-image/origin ID. |
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
| `top_left_x`, `top_left_y`, `bottom_right_x`, `bottom_right_y` | ROI/patch coordinate fields. Deferred for analysis until patch-origin-coordinate associations are rerun. Some prior image-origin associations were incorrect. |

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
| `TaskIII` | `Presence`, `Absence` | Dysplasia presence grouping. OSCC is included in `Presence`. |
| `TaskIV` | `OSCC`, `Leukoplakia with dysplasia`, `Leukoplakia without dysplasia` | Three-class diagnostic task. |

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

Patch-level observed distributions:

| Field | Values |
| --- | --- |
| `gender` | `M`: 1,850. `F`: 1,236. |
| `skin_color` | `Not informed`: 1,393. `White`: 1,184. `Black`: 335. `Brown`: 174. |
| `tobacco_use` | `Not informed`: 1,425. `Yes`: 920. `No`: 496. `Former`: 245. |
| `alcohol_consumption` | `Not informed`: 1,425. `No`: 743. `Former`: 500. `Yes`: 418. |
| `sun_exposure` | `Not informed`: 1,465. `No`: 1,123. `Yes`: 498. |
| `age_group` | `2` (> 60 years): 1,496. `1` (40-60 years): 1,392. `0` (< 40 years): 198. |

These fields are useful for factsheets, subgroup summaries, and fairness-aware reporting. They should not be treated as causal adjustment variables without a separate causal design.

## Validated Fold Artifacts

The canonical current files are under `results/phase3/fold_creation/`. They contain 203 origin rows and 3,086 patch rows and were regenerated from the accepted Virchow/PCA=2/K=3 selection. Earlier Swin-based and 202-origin files are superseded.

### Stratification Variable Validation

Path:

```text
results/phase3/fold_creation/stratification_variables_validation.csv
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

By default, fold construction should use `origin_diagnosis`, `morph_cluster`, `gender`, and `age_group`. Other demographic and clinical variables are descriptive factsheet fields unless they are explicitly promoted and pass the validation gate. Variables with high `Not informed` or missingness should not silently affect fold assignment.

## Morphology Clusters

The accepted origin-level morphology clusters contain:

| Cluster | Origin count |
| --- | ---: |
| 0 | 101 |
| 1 | 67 |
| 2 | 35 |

Cluster labels are nominal K-Means identifiers, not diagnoses or severity levels.

## File Status Notes

- `data/` is ignored by Git in the current `.gitignore`. Public users should retrieve source data from Mendeley. Maintainer-only data synchronization may use DVC.
- `results/` contains generated artifacts. Public documentation should point to validated Phase 3 outputs and committed thesis/static figure exports, not arbitrary intermediate files.
- Several root Markdown files are untracked review/deliverable notes and should be promoted, archived, or deleted after manual review.
