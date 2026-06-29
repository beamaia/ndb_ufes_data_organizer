# Implementation Status

Last verified: 29 June 2026.

## Phase 0: Data Checks

Contamination figures and representative cases exist, but manual case disposition remains ongoing. This work does not block the current fold-generation pipeline.

Status: **in progress**.

## Phase 1: Feature Extraction

The current Phase 1 run completed successfully for all 11 configured pretrained backbones. It generated a 203-origin mapping and timestamped embedding dictionaries under `data/embeddings/`. Model-specific preprocessing is used; there is no universal ImageNet-normalization fallback.

Evidence:

- entrypoint: `scripts/phase1.py`
- registry: `scripts/src/phase1/config.yaml`
- run metadata: `results/phase1_metadata/master_runs.json`
- mapping: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`

Status: **complete for the current inputs and registry**.

## Phase 2: Morphology Tuning

Phase 2 completed the five-run PCA/K-Means grid for 11 models. A configuration is eligible only when every cluster contains at least 11 origins and the largest/smallest cluster ratio is at most 5. Eligible configurations are ranked by mean silhouette.

Accepted selection:

| Field | Value |
| --- | --- |
| Model | Virchow |
| PCA components | 2 |
| K-Means clusters | 3 |
| Mean silhouette | 0.663275 |
| Cluster sizes | 101, 67, 35 |
| Largest/smallest ratio | 2.8857 |

Swin's former PCA=2/K=2 result produced a 202/1 split. It is now rejected by the eligibility gate and is superseded.

Status: **complete and accepted**.

## Phase 3: Fold Creation

Phase 3 was regenerated from the accepted Virchow parameters. Origin ID `0` is retained, and exact origin-set validation prevents silent row loss.

| Validation | Result |
| --- | ---: |
| Origins assigned | 203 |
| Patches assigned | 3,086 |
| Folds | 6 |
| Fold patch counts | 520, 510, 511, 511, 524, 510 |
| Patch-count ratio | 1.02745 |
| Maximum folds per origin | 1 |
| Maximum per-stratum fold-count range | 1 |

The earlier 202-origin/3,066-patch files omitted valid origin `0` and are superseded.

Status: **complete and validated**.

## Phase 4: Reporting

The documentation and Phase 3 validation report now cover the core public fold checks. The separate Phase 4 analysis entrypoint is not yet an active release requirement and its older analysis modules still need an independent audit.

Status: **not yet accepted**.
