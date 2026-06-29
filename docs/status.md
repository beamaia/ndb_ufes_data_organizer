# Implementation Status

This page records what each phase is intended to do and its current status. Phases 1-3 are implemented and active. Phase 4 remains in planning.

## Phase 0: Data Checks and Contamination Review

Purpose:

- inspect image matching between patches and origin images;
- identify duplicate-like or suspicious patch cases;
- document any exclusions or accepted limitations.

WIP - current:

- exploratory contamination figures exist and representative examples are shown in [Contamination Checks](contamination-analysis.md);
- this stage is being used for manual data-quality review.

WIP - planned:

- consolidate accepted, excluded, and documented suspicious cases;
- reflect any decisions in the data dictionary and reproducibility notes.

Status: WIP.

## Phase 1: Feature Extraction

Purpose:

- create origin-patch mapping;
- extract frozen embeddings for candidate pretrained models;
- save WSI-level embedding dictionaries for Phase 2.

WIP - current:

- active entrypoint: `scripts/phase1.py`;
- implementation files are under `scripts/src/phase1/` and `scripts/src/models/`;
- run metadata is written under `results/phase1_metadata/`.

WIP - planned:

- rerun after final path checks;
- confirm generated embeddings are grouped correctly by origin;
- keep embedding visualizations as exploratory review material, not as Phase 1 acceptance criteria.

Status: implemented, still needs final rerun/audit before publication.

## Phase 2: Morphology Tuning

Purpose:

- aggregate patch embeddings to origin-level vectors;
- evaluate PCA/K-Means combinations;
- generate tuning plots and parameter files;
- select a morphology signal for fold stratification.

WIP - current:

- active entrypoint: `scripts/phase2.py`;
- supporting modules under `scripts/src/phase2/` contain importable functions only;
- code exists for repeated PCA/K-Means tuning across embedding models;
- origin validation uses the exact 203-origin Phase 1 mapping and rejects mismatches;
- the selected model and parameters are written to root-level `clustering_params.json`;
- outputs are intentionally not documented as committed results because this phase will be rerun.

WIP - planned:

- rerun Phase 2 after accepting Phase 1 embeddings;
- review cluster sizes, stability, silhouette, and interpretability;
- select one morphology configuration for Phase 3.

Status: implemented, selection WIP.

## Phase 3: Fold Creation

Purpose:

- assign each origin to one fold;
- broadcast origin folds to patch-level records;
- balance folds by diagnosis and accepted stratification variables;
- save public fold assignment CSVs.

Current:

- active entrypoint: `scripts/phase3.py`;
- implementation code in `scripts/src/phase3/phase3_fold_creation.py` consumes Phase 2 parameters from `clustering_params.json`;
- helper visualization module: `scripts/src/phase3/phase3_visualize_clusters.py`;
- provisional fold artifacts generated at `results/phase3_fold_creation/`;
- stratification variable audit output: `stratification_variables_audit.csv` (documents inclusion/exclusion decisions).

Output files:

- `fold_assignments_origin.csv` (203 origins, one per row)
- `fold_assignments_patch_level.csv` (3,086 patches, one per row)
- `stratification_variables_audit.csv` (audit trail for stratification decisions)

Verification:

- Origin-level locking: every origin assigned to exactly one fold
- Patch-level inheritance: all patches from an origin inherit its fold
- No data leakage: no origin spans multiple folds
- Fold balance: origin and patch counts balanced across folds; class and cluster distributions balanced

Status: implemented and active.

## Phase 4: Validation and Public Documentation

Purpose:

- validate fold invariants;
- summarize dataset distributions and limitations;
- prepare final data dictionary, factsheet, and reproducibility notes.

WIP - current:

- top-level `scripts/phase4.py` is not yet an active entrypoint;
- implementation files exist under `scripts/src/phase4/`;
- some paths and assumptions need review before rerun.

WIP - planned:

- rerun validation after final folds are generated;
- update factsheet and data dictionary from finalized artifacts;
- keep public documentation focused on provenance, labels, limitations, and leakage-safe use.

Status: WIP.

## Commit Guidance

Commit files that are already useful and aligned with the current public documentation. Park exploratory Phase 3 helpers until Phase 3 is reviewed as a focused pass, so history stays clean and final filenames match the surviving code.
