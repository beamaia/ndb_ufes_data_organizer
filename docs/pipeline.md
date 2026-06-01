# Pipeline Overview

The pipeline organizes a public oral histopathology dataset into leakage-safe folds. Its purpose is data organization and documentation, not downstream model training.

## Phase Flow

```text
Raw metadata + patch images
  -> Phase 1: feature extraction and origin-patch mapping
  -> Phase 2: morphology tuning from frozen embeddings
  -> Phase 3: leakage-safe fold creation
  -> Phase 4: validation, factsheet, and public documentation
```

## Phase 1: Feature Extraction

Goal: create origin-patch mappings and frozen embedding files that can be used for morphology-aware fold stratification.

Current entrypoint:

```bash
uv run python scripts/phase1.py
```

Main implementation files:

- `scripts/phase1.py`
- `scripts/src/phase1/extraction_func.py`
- `scripts/src/phase1/feature_extractor.py`
- `scripts/src/models/model_loader.py`
- `scripts/src/models/model_wrappers.py`
- `scripts/src/phase1/config.yaml`

Expected inputs:

- `data/ndb_ufes/patch/parcial_pndb_ufes.csv`
- patch images under `data/ndb_ufes/patch_level/images/` or `data/ndb_ufes/patch/images/`, depending on the script path being audited

Expected outputs:

- `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`
- `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl`
- `results/phase1_metadata/`
- optional feature cache under `results/phase1_feature_cache/`

Audit focus:

- Confirm all patch paths exist and point to the intended image directory.
- Confirm output embeddings are grouped by origin and contain patch-level vectors.
- Confirm caches are not stale before accepting regenerated outputs.
- Confirm model wrappers and preprocessing are appropriate for each model family.

## Phase 2: Morphology Tuning

Goal: identify frozen embedding models and PCA/K-Means settings that produce useful morphology strata for fold balancing.

Current entrypoint:

```bash
uv run python scripts/phase2.py
```

Main implementation files:

- `scripts/phase2.py`
- `scripts/src/phase2/config.yaml`

Current configuration:

- PCA components: `2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25, 30`
- K-Means clusters: `2, 3, 4, 5, 6, 7, 8, 9`
- repeated runs: `5`
- primary metric in code: silhouette

Expected inputs:

- `data/embeddings/embeddings_wsi_level_*.pkl`
- `data/ndb_ufes/origin_level/csvs/ndb-ufes.csv`

Expected outputs when rerun:

- per-model tuning tables;
- averaged tuning summaries;
- selected-parameter files;
- visual summaries for reviewing PCA/K-Means behavior.

These files are not treated as committed documentation artifacts yet because Phase 2 will be rerun before final fold creation.

Audit focus:

- Repeated K-Means should use mean and standard deviation across runs.
- Five runs is the recommended default; three runs is only an exploratory shortcut.
- Do not select the model/config using downstream training or test results.
- Do not rely only on highest silhouette. Also check cluster sizes, stability, interpretability, and whether clusters are useful for fold stratification.
- Existing provisional folds should be checked against the final accepted Phase 2 configuration before publication.

## Phase 3: Fold Creation

Goal: assign every origin to exactly one fold, then broadcast that assignment to every patch.

Current state:

- `scripts/phase3.py` is empty.
- Implementation exists at `scripts/src/phase3/phase3_fold_creation.py`.
- Existing provisional fold outputs are currently under `data/ndb_ufes/origin_level/csvs/` and `data/ndb_ufes/patch_level/csvs/`.

Provisional fold artifacts observed:

- `data/ndb_ufes/origin_level/csvs/fold_assignments_origin.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv`

Audit focus:

- Every patch has exactly one origin.
- Every origin appears in exactly one fold.
- Every patch inherits its origin's fold.
- Fold balance is checked by patch count, origin count, diagnosis, morphology cluster, gender, and age group.
- Fold construction should use origin diagnosis, the selected morphology cluster, gender, and age group by default.
- Other demographic and clinical fields with high `Not informed`/missingness are factsheet descriptors, not automatic stratification variables.
- Any additional demographic or clinical field promoted into fold construction must pass the saved stratification-variable audit.
- Provisional folds must be compared with the final accepted Phase 2 morphology configuration before treating them as final.

## Phase 4: Validation and Public Documentation

Goal: validate finalized folds and publish dataset documentation.

Current state:

- `scripts/phase4.py` is empty.
- Implementations exist under `scripts/src/phase4/`.
- Some Phase 4 files still point to old output paths and should be audited before execution.

Relevant files:

- `scripts/src/phase4/phase4_feature_analysis.py`
- `scripts/src/phase4/phase4_data_analysis.py`
- `scripts/src/phase4/phase4_causal_interpretability.py`
- `scripts/src/phase4/validate_causal_interpretability.py`

Audit focus:

- Avoid overclaiming from chi-square tests. A non-significant p-value does not prove folds are identical.
- Treat causal/risk-factor metadata as descriptive public dataset information unless a separate causal analysis is explicitly designed.
- Ensure public docs include provenance, citation, task labels, demographics/risk factors, limitations, and leakage-safe usage.

## Leakage Policy

Acceptable:

- Frozen external pretrained embeddings used for unsupervised morphology-aware stratification.
- Selecting fold strata before downstream model training.

Not acceptable:

- Fine-tuning the embedding model on all dataset labels before fold creation.
- Choosing folds or the stratification model because they improve downstream validation/test performance.
- Splitting patches from the same origin across train/validation/test folds.

## Current Artifact Summary

The current worktree contains provisional fold artifacts from an earlier run:

- 203 origin rows with fold assignments.
- 3,086 patch rows in the detailed patch-level fold file.

Because Phase 2 morphology selection is still under audit, do not publish fold-count summaries as final results yet. Recompute or explicitly validate Phase 3 after choosing the Phase 2 model/config.
