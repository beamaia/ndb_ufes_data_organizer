# Implementation Status

This page records what each phase is intended to do and what still needs review. The repository is mid-reorganization, so this page is intentionally conservative.

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
- code exists for repeated PCA/K-Means tuning across embedding models;
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

WIP - current:

- top-level `scripts/phase3.py` is not yet an active entrypoint;
- implementation code exists under `scripts/src/phase3/`;
- some helper visualization scripts are exploratory and should be reviewed before committing as final pipeline code;
- provisional fold artifacts exist, but should be compared against the accepted Phase 2 configuration.

WIP - planned:

- wire a clean Phase 3 entrypoint;
- generate final origin-level and patch-level fold CSVs;
- verify origin integrity, patch inheritance, and fold balance;
- decide which visualization helpers survive as part of the final phase.

Status: WIP.

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
