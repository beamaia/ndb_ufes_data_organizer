# Data Dictionary

This page defines the final public experiment tables, source-image index, result files, labels, identifiers, and scope counts.

## Final Scope

| Item | Count |
| --- | ---: |
| P-NDB-UFES patches in each experiment | 3,763 |
| Public NDB-UFES + SAB source-image groups | 203 |
| Patches in public NDB-UFES + SAB groups | 3,111 |
| SAB-only source-image groups | 48 |
| Patches in SAB-only groups | 652 |
| Total source-image groups | 251 |
| Diagnostic classes | 3 |
| Folds | 6 |
| Canonical parent runs | 6 |
| Canonical child-fold evaluations | 30 |

The 3,111 patches in both-source groups are the public NDB-UFES-linked set. The 652 SAB-only patches remain in the complete experiment scope and have validated SAB source-image grouping.

## Core Terms

| Term | Meaning |
| --- | --- |
| Patch | A cropped histopathology image used as one experiment row. |
| Source image | The histopathology image from which one or more patches were derived. No complete-slide status is assumed. |
| Both-source group | A source-image group supported by public NDB-UFES and SAB evidence. |
| SAB-only group | A source-image group supported by SAB evidence without a public NDB-UFES source-image counterpart. |
| Experiment 1 | The released patch-level reference split. |
| Experiment 2 | The patient-first grouped split that keeps validated source-image and patient/case groups within one fold. |
| Cross-validation fold | One of folds 0–4, rotated through validation while the other four train. |
| Held-out test fold | Fold 5, excluded from training and validation. |

## Public Bundle Files

| File | Rows | Purpose |
| --- | ---: | --- |
| [Download Experiment 1 fold CSV](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/release/v1.0.0/public/tables/experiment1_patch_assignments.csv) | 3,763 | Final Experiment 1 reference patch assignments. |
| [Download Experiment 2 fold CSV](https://raw.githubusercontent.com/beamaia/ndb_ufes_data_organizer/main/release/v1.0.0/public/tables/experiment2_patch_assignments.csv) | 3,763 | Final Experiment 2 patient-first grouped patch assignments. |
| `tables/validated_wsi_index.csv` | 251 | Public-pseudonymous source-image index. |
| `experiments/results_summary.csv` | 6 | One aggregate row per experiment/model pair. |
| `experiments/fold_test_metrics.csv` | 30 | One held-out evaluation row per child fold. |
| `experiments/canonical_run_validation.csv` | 6 | Validation status for each parent run. |
| `experiments/canonical_run_manifest.json` | 1 manifest | Frozen run, dataset, parameter, duration, and metric provenance. |
| `validation_report.json` | 1 report | Machine-readable public-bundle validation result. |

The exact source-index filename retains a technical identifier used by the executable release tooling. In reader-facing text, it is the source-image index.

## Experiment Assignment Tables

Both assignment tables use the same columns and patch ID set.

| Column or group | Meaning |
| --- | --- |
| `patch_id` | Public patch pseudonym. |
| `diagnosis` | Final three-class diagnostic label. |
| `fold` | Integer fold ID from 0 through 5. |
| `role` | `cross_validation` for folds 0–4 or `held_out_test` for fold 5. |
| `public_origin_id` | Public-pseudonymous origin identifier. |
| `public_group_id` | Public-pseudonymous fold-group identifier. |
| `public_wsi_id` | Executable column name for the public source-image identifier. |
| `image_path` | Repository-relative public patch path. |
| provenance fields | Public-safe source and metadata provenance. |
| approved clinical fields | Deidentified localization, lesion-size, risk-factor, demographic, and dysplasia-severity values. |

Direct identifiers, raw private source identifiers, local absolute paths, and private crosswalks are excluded.

## Source-Image Index

The source-image index has one row per validated group. Its fields describe:

- public source-image identifier and source role,
- patch and patch-pair counts,
- coordinate and overlap coverage,
- public-safe diagnostic summaries,
- public origin linkage where available,
- evidence and manual-review summaries.

Interpret coverage and similarity fields as technical linkage evidence, not biological conclusions or proof that two images are duplicates.

## Diagnosis Labels

| Label | Patch count |
| --- | ---: |
| `OSCC` | 1,126 |
| `Leukoplakia with dysplasia` | 1,930 |
| `Leukoplakia without dysplasia` | 707 |

## Fold Contract

| Role | Folds | Use |
| --- | --- | --- |
| Cross-validation | 0–4 | Four folds train and one validates in each rotation. |
| Held-out test | 5 | Evaluates each resulting checkpoint and is never used for training or validation. |

| Experiment | Fold counts, 0–5 |
| --- | --- |
| Experiment 1 | 628/627/627/627/627/627 |
| Experiment 2 | 627/631/627/626/626/626 |

## Canonical Result Fields

The aggregate result table reports, for each experiment/model pair:

- fold count,
- balanced-accuracy mean and population standard deviation,
- macro-precision mean and population standard deviation,
- macro-F1 mean and population standard deviation.

Balanced accuracy equals macro recall in this three-class implementation. The fold-level table retains both values as a machine-readable consistency check.

## Privacy and Reuse

The public bundle may contain public pseudonyms, repository-relative paths, diagnosis, fold role, public-safe provenance, and approved deidentified clinical fields. It must not contain raw SAB case prefixes, original private image names, direct patient/lesion identifiers, private crosswalks, local absolute paths, credentials, checkpoints, or raw MLflow storage.

Use the assignment tables as released. Do not randomly resplit patch rows or move linked source-image and patient/case groups across partitions.
