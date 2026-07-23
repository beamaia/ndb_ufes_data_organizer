# Implementation Status

Documentation/index verified: 23 July 2026. Pipeline artifacts referenced below come from the validated runs noted in each section.

## Atlas Linkage Status

The phase-0 validated-linkage output assigns all 3,763 patch rows to 251 validated WSI IDs and recovers coordinates for all 3,763 rows. The inventory contains 203 public NDB-UFES + SAB WSI groups and 48 SAB-only recovered WSI groups. Patch labels agree across the complete NDB-UFES and SAB patch sources for all 3,763 rows; 1,489 rows still carry a metadata-conflict flag and should be interpreted with the [Metadata Conflict Review](metadata-conflict-review.md) and [Atlas Guide](atlas-guide.md).

The public-pseudonymous [Atlas Index](atlas-index.md) and [Atlas Manifest](assets/atlas/atlas_manifest.json) are generated from the phase-0 inventory. This atlas linkage layer covers all 3,763 SAB-linked patches. The separate public NDB-UFES matching layer contains 3,086 rows matched to public origin images and 677 rows without a public NDB-UFES origin match.

## Current Thesis Linkage And Experiment Status

The current thesis/article artifacts update the relationship between
P-NDB-UFES patches, SAB images, and public NDB-UFES origins. The patch-level
relationship file contains all 3,763 SAB-linked P-NDB-UFES patch rows. Of
these, 3,086 match public NDB-UFES origin images; the remaining 677 do not.

Current files:

| File | Purpose |
| --- | --- |
| `data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv` | Current patch-level P-NDB-UFES to NDB/SAB relationship table. |
| `data/ndb_ufes/link_level/csvs/pndb_ndb_origin_relationships.csv` | Current origin/fallback-group relationship summary. |
| `results/phase3/current_thesis_batches/` | Current batch CSVs, linkage summary, metadata consistency summary, and feature-diversity summary. |

The final comparison is complete. Experiment 1 uses the 3,763-row
original-comparable Batch 1 split; Experiment 2 uses the 3,763-row
patient-first grouped Batch 2 split. Experiment 2 has no recovered origin or
patient/case group crossing folds. Batch 3 contains 3,351 rows after Virchow
cosine pruning, but is archived as exploratory and is not part of the final
model comparison.

The six canonical parent runs and 30 child folds have been validated. See
[Canonical Experiment Results](experiment-results.md) and the
[machine-readable manifest](assets/experiments/canonical_run_manifest.json).

The Phase 1--3 sections below describe the 3,086-patch public
NDB-UFES-matched organizer run used for the earlier embedding and fold-design
work. They are still part of the project history, but should be read together
with the current full-scope relationship files above.

## Phase 0: Data Checks

The current documentation includes Origin 0011 as a demonstration example for patch-overlap and leakage-risk review. It is not a complete contamination case set. Full image-level disposition work is paused pending human-in-the-loop validation.

All origin-patch pairs currently accepted into the matched fold-design set were checked visually by a human. Not all possible patches have been matched or dispositioned, so the contamination page should be read as conservative quality-control documentation rather than final exclusion criteria.

Status: **paused pending human validation**.

## Phase 1: Feature Extraction

The current Phase 1 run completed successfully for all 11 configured pretrained backbones. It generated a 203-origin mapping and timestamped embedding dictionaries under `data/embeddings/`. Model-specific preprocessing is used. There is no universal ImageNet-normalization fallback.

Evidence:

- entrypoint: `scripts/phase1.py`
- registry: `scripts/src/phase1/config.yaml`
- run metadata: `results/phase1/metadata/master_runs.json`
- mapping: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`

Status: **complete for the current inputs and registry**. Run completed on 28 June 2026 and documentation was last verified on 29 June 2026.

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

Status: **complete and accepted**. Last verified on 29 June 2026.

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

Status: **complete and validated**. Last verified on 29 June 2026.

## Phase 4: Reporting And Experiment Release

The v1.0.0 reporting path verifies the six canonical parents and 30 stored
child-fold records without retraining. It publishes sanitized result tables,
figures, exploratory statistics, and provenance. Legacy Phase 4 analysis
modules remain historical and are not required by the release builder.

Status: **accepted for the v1.0.0 public release path**.
