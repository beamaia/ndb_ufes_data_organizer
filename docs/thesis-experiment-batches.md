# Thesis Experiment Design

Last verified: 23 July 2026.

The final thesis comparison contains two experiments over the same 3,763
P-NDB-UFES patches:

1. **Experiment 1 / Batch 1** reproduces the original-comparable patch split.
   It is the historical reference and retains known origin and patient/case
   overlap across folds.
2. **Experiment 2 / Batch 2** uses a patient-first grouped,
   lower-contamination-risk split. Linked source-image and patient/case groups, and their
   patches remain in one fold.

The completed comparison uses MobileNetV2, DenseNet-121, and ResNet-50. See
[Canonical Experiment Results](experiment-results.md) for the validated model
results and stored-run provenance.

## Scope

| Item | Final value |
| --- | ---: |
| P-NDB-UFES patch rows in each experiment | 3,763 |
| Diagnostic classes | 3 |
| Cross-validation folds | 0 through 4 |
| Held-out test fold | 5 |
| Models per experiment | 3 |
| Trained checkpoints per model | 5 |
| Canonical parent runs | 6 |
| Canonical child-fold runs | 30 |

The classes are oral squamous cell carcinoma (OSCC), leukoplakia with
dysplasia, and leukoplakia without dysplasia.

## Fold Contract

Folds 0–4 rotate as validation folds. In each rotation, four folds train the
model and the remaining fold validates it. Fold 5 is never used for training
or validation. Every resulting checkpoint is evaluated on fold 5, so the
reported held-out result summarizes five checkpoint evaluations.

![Class distribution across the six folds by experiment](assets/experiments/fold_class_distribution.svg)

| Experiment | Fold counts, 0–5 | Origin groups crossing folds | Patient/case groups crossing folds |
| --- | --- | ---: | ---: |
| Experiment 1 | 628/627/627/627/627/627 | 201 | 61 |
| Experiment 2 | 627/631/627/626/626/626 | 0 | 0 |

Experiment 2 is described as **lower contamination risk**, not
contamination-free. Grouping addresses known relationships but cannot prove
that every relationship in the source material was recovered.

## Class Counts

Both experiments retain the same complete patch scope:

| Diagnosis | Patches |
| --- | ---: |
| OSCC | 1,126 |
| Leukoplakia with dysplasia | 1,930 |
| Leukoplakia without dysplasia | 707 |

The fold-level class counts are included in the manuscript and can be
recomputed from the public, sanitized experiment assignment tables.

## Linkage Layers

The atlas and relationship metadata answer different questions:

| Layer | Scope | Meaning |
| --- | --- | --- |
| SAB/atlas source-image linkage | 3,763 patches, 251 source-image groups | SAB and coordinate/pixel evidence place every patch on a linked source image. |
| Public NDB-UFES origin matching | 3,086 matched rows + 677 rows without a public match | Records whether each SAB-linked patch can also join to a public NDB-UFES origin image and its metadata. |

Rows without a public NDB-UFES origin match are retained. They receive unique
fallback grouping where a stronger public match is unavailable; unrelated
unknown samples are not merged into one artificial patient.

## Frozen Hyperparameters

| Setting | Value |
| --- | --- |
| Initialization and mode | ImageNet pretrained, full fine-tuning |
| Seed | 42 |
| Batch size | 30 |
| Epoch ceiling | 150 |
| Loss | Weighted cross-entropy |
| Optimizer | SGD, learning rate 0.001, momentum 0.9 |
| Scheduler | ReduceLROnPlateau on validation loss |
| Scheduler factor / patience / minimum LR | 0.1 / 10 / 0.000001 |
| Early-stopping patience / minimum delta | 15 / 0.001 |

Scheduler patience means ten validation-loss epochs without sufficient
improvement. It does not mean an unconditional learning-rate reduction every
ten epochs.

## Exploratory Batch 3 Archive

Batch 3 applied Virchow cosine pruning to Batch 2 and retained 3,351 patches.
It was not included in the completed model comparison because the final
experiment matrix was reduced to the two directly comparable split
strategies. Its CSVs and pruning review remain available as exploratory history,
but they are excluded from the v1.0.0 public research bundle and final result
claims.

## Public Reuse

The v1.0.0 public bundle contains two deidentified assignment tables with
public patch IDs, public origin/group/source-image pseudonyms, repository-relative image
paths, fold roles, metadata status/provenance, and approved deidentified
clinical fields. It excludes direct patient/lesion identifiers, SAB case
prefixes, private crosswalks, local paths, checkpoints, and raw MLflow storage.
