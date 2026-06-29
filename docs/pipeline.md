# Pipeline Overview

This repository organizes NDB-UFES into leakage-safe six-fold assignments. It does not train or select a downstream diagnostic model.

```text
Patch metadata and images
  -> Phase 1: frozen model-specific embeddings
  -> Phase 2: eligible morphology-clustering selection
  -> Phase 3: deterministic origin-level fold assignment
  -> validated origin and patch CSVs
```

## Phase 1

`scripts/phase1.py` creates the 203-origin mapping and extracts embeddings for all configured backbones. Each model uses its declared processor statistics, resize, crop, and interpolation settings.

Current output: 11 timestamped embedding dictionaries, each covering the same 203 origins and 3,086 patches.

## Phase 2

`scripts/phase2.py` is the only executable entrypoint. Helpers live under `scripts/src/phase2/`, including `phase2_tune_clustering.py`.

For each model, Phase 2:

1. Mean-pools patch embeddings into one vector per origin.
2. Evaluates 14 PCA dimensions by 8 K values over 5 seeds.
3. Records silhouette, inertia, explained variance, minimum/maximum cluster sizes, and size ratio.
4. Rejects configurations with a cluster below 11 origins or a size ratio above 5.
5. Ranks eligible configurations by mean silhouette.

The accepted result is Virchow with PCA=2 and K=3. The three clusters contain 101, 67, and 35 origins. Selection is based only on frozen unsupervised features and fold-readiness constraints, never downstream performance.

## Phase 3

`scripts/phase3.py` requires the selected model, embedding file, PCA, K, seed, and selection constraints from `clustering_params.json`. It validates exact agreement among mapping, patch metadata, and embeddings before clustering.

Required strata are diagnosis, morphology cluster, gender, and age group. Each required variable must pass the 25% missingness ceiling and have at least six origins in every category.

Assignment uses deterministic stratum round-robin LPT:

1. Sort each combined stratum by patch count, largest first.
2. Process origins in blocks of six.
3. Assign every origin in a block to a distinct currently least-loaded fold.
4. Break ties by fold origin count, then fold ID.

This preserves per-stratum spread while balancing patch totals. The final run assigned all 203 origins and 3,086 patches with a patch-count ratio of 1.02745.

## Leakage Policy

Allowed:

- frozen external pretrained embeddings for unsupervised stratification;
- choosing morphology parameters before downstream training.

Not allowed:

- random patch-level splitting;
- fine-tuning the feature extractor on all dataset labels before fold creation;
- choosing folds or morphology parameters from validation/test performance;
- placing patches from one origin in multiple folds.
