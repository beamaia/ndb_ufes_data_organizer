# NDB-UFES Data Organizer Project Recap

Date: 2026-06-28

## Executive Summary

The Git branch itself is aligned with `origin/main`, but the working tree contains a large amount of local, uncommitted work. The project appears to have grown from the committed DVC/data-management baseline into a multi-phase analysis pipeline with new scripts, generated tuning results, wiki documentation, and phase-specific outputs.

The external SSD workspace path temporarily disappeared during inspection:

```text
/Volumes/ssd/thesis_organization/ndb_ufes_data_organizer
```

The SSD has since been remounted and the repo is readable again. DVC status was re-run successfully and reported that the tracked `data/` output is modified relative to `data.dvc`. A follow-up `dvc diff` showed that this is only due to Finder metadata files, not a meaningful data or Phase 1 output change.

## Repository State Observed

The repo was on `main` and aligned with the remote:

```text
## main...origin/main
```

The latest committed revision was:

```text
52c4971 chores: update dvc
```

There were no commits ahead of or behind `origin/main` at the time of inspection.

However, the working tree was not clean. It contained one modified tracked file and many untracked files/directories.

## DVC State

The active file `data.dvc` tracks the `data/` directory:

```yaml
outs:
- md5: 520a37e238371cf271ecef502c153de9.dir
  size: 3892000770
  nfiles: 7093
  hash: md5
  path: data
```

This means the committed DVC metadata points to a `data/` snapshot of approximately:

- 3.89 GB
- 7,093 files

The DVC config uses this remote:

```text
s3://dvc-ndb-ufes/data/
```

with:

```text
[core]
    remote = dvc-ndb-ufes
    autostage = true
```

## DVC Verification Status

Running `dvc status` first failed because DVC attempted to access:

```text
/Library/Caches/dvc
```

After approval to run DVC outside the sandbox, `dvc status` started but then failed because the working directory disappeared:

```text
FileNotFoundError: [Errno 2] No such file or directory
```

At that point, `/Volumes` no longer showed the external SSD mount. Only these were visible:

```text
Macintosh HD
com.apple.TimeMachine.localsnapshots
```

After the SSD was remounted, `dvc status` completed successfully and reported:

```text
data.dvc:
	changed outs:
		modified:           data
```

This means DVC is functional again, but the current local `data/` directory does not match the snapshot recorded in `data.dvc`. The next decision is whether the local `data/` changes are intentional and should be recorded with `dvc add data`, or whether the local data should be restored to the committed DVC snapshot.

A follow-up `dvc diff --targets data.dvc` showed:

```text
Modified:
    data/
    data/.DS_Store
    data/ndb_ufes/.DS_Store

files summary: 2 modified
```

So the current DVC mismatch is caused by `.DS_Store` files, not by regenerated embeddings or dataset content.

## Phase 1 Execution Timeline

The recorded Phase 1 run metadata shows a full extraction run on:

```text
2026-04-22 00:30:30
```

The metadata summary reports:

```text
Status: 9/11 models successfully extracted
Failed models: virchow, vit_base_patch32_224
```

The successful April 22 outputs were:

```text
data/embeddings/embeddings_wsi_level_uni_20260422_003036.pkl
data/embeddings/embeddings_wsi_level_ctranspath_20260422_003039.pkl
data/embeddings/embeddings_wsi_level_mocov3_vit_small_20260422_003040.pkl
data/embeddings/embeddings_wsi_level_vit_base_patch16_224_20260422_003042.pkl
data/embeddings/embeddings_wsi_level_vit_large_patch16_224_20260422_003046.pkl
data/embeddings/embeddings_wsi_level_deit_base_patch16_224_20260422_003053.pkl
data/embeddings/embeddings_wsi_level_swin_base_patch4_window7_224_20260422_003056.pkl
data/embeddings/embeddings_wsi_level_efficientnet_b0_20260422_003058.pkl
data/embeddings/embeddings_wsi_level_efficientnet_b1_20260422_003059.pkl
```

There is also one later embedding file:

```text
data/embeddings/embeddings_wsi_level_uni_20260531_221952.pkl
```

That suggests UNI may have been rerun or regenerated separately on 2026-05-31 at 22:19:52. However, the Phase 1 metadata file was last updated on 2026-04-22, so the May 31 UNI file does not appear to be part of a fully recorded Phase 1 rerun.

The useful evidence is the absolute file timeline, not whether anything changed recently:

- 2026-04-14: main image/data files under `data/ndb_ufes/` were created or copied.
- 2026-04-15: fold assignment CSVs and related fold distribution output were created.
- 2026-04-21 to 2026-04-22: Phase 1 feature cache files were generated under `results/phase1_feature_cache/`.
- 2026-04-22 00:30 to 00:31: the recorded Phase 1 embedding outputs and metadata were generated.
- 2026-04-22 01:22: Phase 2 clustering/tuning outputs were generated.
- 2026-05-31 18:28 to 19:05: dataset statistics plots were generated.
- 2026-05-31 21:59: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` was modified.
- 2026-05-31 22:19: one later UNI embedding was generated: `data/embeddings/embeddings_wsi_level_uni_20260531_221952.pkl`.
- 2026-05-31 23:41: `.DS_Store` files inside `data/` were modified, which is what currently makes DVC report `data/` as changed.

So the evidence does not support a recent full Phase 1 rerun. It does support that Phase 1 was run around April 21-22, and that one UNI embedding file was generated later on May 31.

## Phase 1 ViT-Base-32 / CLIP Fix

The previous Phase 1 failure for `vit_base_patch32_224` was caused by treating `openai/clip-vit-base-patch32` as a plain Hugging Face ViT model. The model loaded successfully, but the wrapper called it positionally, so CLIP's vision tower received `pixel_values=None`.

Fixed in:

```text
scripts/src/models/model_wrappers.py
```

The fix adds a CLIP vision wrapper that calls the CLIP vision tower with:

```python
vision_model(pixel_values=x)
```

and returns ViT-style hidden states with shape:

```text
(batch_size, num_tokens, 768)
```

A one-image extraction test passed on 2026-06-28 and returned:

```text
{origin_id: (1, 768)}
```

## Phase 1 Model Cache Location

Phase 1 now redirects model/cache downloads to the SSD-backed project directory before importing Hugging Face, Transformers, Torch, or Torchvision model-loading code.

Cache root:

```text
/Volumes/ssd/thesis_organization/ndb_ufes_data_organizer/.cache/
```

Configured paths:

```text
HF_HOME=.cache/huggingface
HUGGINGFACE_HUB_CACHE=.cache/huggingface/hub
HF_HUB_CACHE=.cache/huggingface/hub
TRANSFORMERS_CACHE=.cache/transformers
TORCH_HOME=.cache/torch
```

This fixes the problem where Hugging Face downloads were using the nearly-full internal disk. It affects future downloads/runs; it does not automatically move or delete the existing cache under:

```text
/Users/beamaia/.cache/huggingface
```

## Phase 2 Audit

Phase 2 has a real implementation and existing generated outputs under:

```text
results/phase2_tuning/
```

However, Phase 2 should not be considered final until the current Phase 1 rerun finishes. As of 2026-06-28, fresh Phase 1 embeddings had already appeared for:

```text
data/embeddings/embeddings_wsi_level_uni_20260628_204738.pkl
data/embeddings/embeddings_wsi_level_ctranspath_20260628_205127.pkl
```

So running Phase 2 before Phase 1 finishes would mix new embeddings with older April embeddings.

A Phase 2 model-discovery bug was found and fixed in:

```text
scripts/src/phase2/tune_clustering.py
```

The old parser extracted only one underscore-delimited segment from filenames, so models such as `vit_base_patch16_224`, `vit_large_patch16_224`, `efficientnet_b0`, and `efficientnet_b1` collapsed into generic names like `vit` or `efficientnet`. The updated parser preserves the full model name from:

```text
embeddings_wsi_level_{model}_{YYYYMMDD}_{HHMMSS}.pkl
```

and selects the latest embedding file when multiple files exist for the same model.

Phase 2 was subsequently reorganized so `scripts/phase2.py` is the only executable entrypoint and `scripts/src/phase2/` contains importable functions without independent `main()` flows or import-time execution. It now validates the exact 203-origin Phase 1 mapping instead of inserting zero vectors for the 34 unmatched rows in the full 237-row origin metadata table. It writes per-model results under `results/phase2_tuning/` and the overall selected model, embedding path, and parameters to root-level `clustering_params.json` for Phase 3. Phase 3 now consumes the selected `embeddings_file` field, and `scripts/phase3.py` is wired as the active Phase 3 entrypoint.

## Split Leakage Policy

Using frozen external pretrained embeddings to create morphology-aware folds is acceptable if:

- the embedding model was not trained or fine-tuned on this dataset's labels before splitting;
- the choice of embedding model and clustering settings is made before downstream model training;
- the final fold choice is not selected based on downstream validation/test performance;
- all patches from one origin remain in the same fold.

Using the same pretrained architecture later for downstream model training is not automatically leakage, as long as training or fine-tuning only uses the training fold inside each split. For cleaner reporting, document which frozen feature extractor was used for fold construction and avoid claiming downstream performance is independent of that morphology-balancing choice.

Not acceptable:

- fine-tuning an embedding model on all dataset labels before fold creation;
- choosing the splitter model because it improves downstream scores;
- letting patches from the same origin appear in multiple folds.

## GitHub Pages Documentation

The canonical documentation source is:

```text
docs/
mkdocs.yml
```

The built site output is:

```text
site/
```

`site/` is ignored in `.gitignore` and should usually be generated rather than edited manually. GitHub Pages deployment is configured in:

```text
.github/workflows/deploy-docs.yml
```

The workflow builds MkDocs and publishes `./site` with `peaceiris/actions-gh-pages`.

The docs build passed with:

```bash
uv run --extra docs mkdocs build --strict
```

The only MkDocs warning was that these source pages exist but are not in the nav:

```text
docs/audit-guide.md
docs/visualizations/README.md
```

That is not a build failure. Add them to `mkdocs.yml` only if they should be visible in the public navigation.

## Modified Tracked File

One tracked file was modified:

```text
M main.py
```

The visible diff showed only an import change:

```python
from scripts.src.utils import logger
```

and the `cv2` import was moved below that import. No larger logic change was visible in the captured diff.

## Untracked Local Work

These untracked files/directories were present:

```text
clustering_params.json
enhance_fold_assignments.py
old_copilot_stuff/
results/phase1_metadata/
results/phase2_tuning/
scripts/phase2.py
scripts/phase3.py
scripts/phase4.py
scripts/src/phase2/
scripts/src/phase3/
scripts/src/phase4/
wiki_pages/
```

This is the main body of local work that still needs to be reviewed, cleaned, and either committed, ignored, or tracked with DVC.

## New Pipeline Work

The untracked files indicate a new multi-phase workflow.

### Phase 1: Feature Extraction / Metadata

Observed outputs:

```text
results/phase1_metadata/master_runs.json
results/phase1_metadata/runs_summary.txt
```

There is also an existing feature cache:

```text
results/phase1_feature_cache/
```

Observed size:

```text
169M results/phase1_feature_cache
```

This suggests Phase 1 has already produced cached model features and run metadata.

### Phase 2: Clustering Tuning

Observed directory:

```text
results/phase2_tuning/
```

Observed size:

```text
10M results/phase2_tuning
```

Phase 2 has generated tuning outputs for several feature extractors/models:

- `ctranspath`
- `deit`
- `efficientnet`
- `mocov3`
- `swin`
- `uni`
- `vit`

For these models, the directory contains:

- per-run CSV files
- averaged CSV files
- clustering parameter JSON files
- elbow curve plots
- inertia plots
- silhouette plots
- silhouette heatmaps
- top-10 configuration plots

The root-level `clustering_params.json` contained:

```json
{
  "pca_components": 2,
  "kmeans_clusters": 4,
  "silhouette_score": 0.4894331932067871,
  "silhouette_std": 5.3312014979157235e-08,
  "explained_variance": 0.3138089,
  "inertia": 3711.2794921875,
  "inertia_std": 0.0010557494292456,
  "random_state": 42
}
```

This appears to be the currently selected or exported clustering configuration.

### Phase 3: Fold Creation / Visualization

New Phase 3 code exists under:

```text
scripts/src/phase3/
```

Active Phase 3 files:

```text
phase3_fold_creation.py
phase3_visualize_clusters.py
```

Legacy exploratory helper scripts were removed from the active Phase 3 source tree.

However, the top-level entry file:

```text
scripts/phase3.py
```

was observed to be empty.

### Phase 4: Data / Feature / Causal Analysis

New Phase 4 code exists under:

```text
scripts/src/phase4/
```

Observed files included:

```text
phase4_causal_interpretability.py
phase4_data_analysis.py
phase4_feature_analysis.py
validate_causal_interpretability.py
```

However, the top-level entry file:

```text
scripts/phase4.py
```

was observed to be empty.

## Script Sizes Observed

Approximate line counts captured:

```text
493 scripts/phase2.py
0   scripts/phase3.py
0   scripts/phase4.py
45  enhance_fold_assignments.py
```

Phase source files under `scripts/src/phase2`, `scripts/src/phase3`, and `scripts/src/phase4` total several thousand lines.

This means substantial implementation exists, but the top-level Phase 3 and Phase 4 runners still need attention.

## Documentation Added

New wiki documentation exists under:

```text
wiki_pages/
```

Observed files:

```text
Data-Organization-&-Dictionary.md
Home.md
Phase-1-Feature-Extraction.md
Phase-1-Results-&-Visualizations.md
Pipeline-Overview.md
Setup-&-Installation.md
```

These docs appear to describe the project structure, setup, data dictionary, pipeline overview, and Phase 1 process/results.

## Old Copilot Material

An untracked directory exists:

```text
old_copilot_stuff/
```

Observed files included:

```text
CAUSAL_INTERPRETABILITY_SCHEMA.md
CODEBASE_DATA_STRUCTURE.md
DATASET_DICTIONARY.md
DELIVERABLES_PHASE4_CAUSAL.md
MASTER_AUDIT_CHECKLIST.md
PHASE3_SUMMARY.md
PHASE4_AUDIT_PLAN.md
PHASE4_CAUSAL_INTERPRETABILITY_SUMMARY.txt
PIPELINE_PLAN.md
REORGANIZATION_SUMMARY.md
REPRODUCIBILITY.md
```

This may be useful as reference material, but it should probably not be committed blindly without review.

## Generated / Cleanup Candidates

The repo contains generated or local-environment files that should be cleaned or ignored before committing:

```text
.DS_Store
__pycache__/
*.pyc
```

Observed examples included `.DS_Store` files under `results/` and `scripts/`, plus Python cache files under multiple `scripts/src/` subdirectories.

These should usually not be committed.

## What Needs To Be Done Next

1. Remove or ignore the `.DS_Store` files inside `data/` so DVC no longer reports meaningless data modifications.

2. Re-run Git status:

   ```bash
   git status --short --branch
   ```

3. Re-run DVC status:

   ```bash
   dvc status
   ```

4. Decide whether the May 31 UNI embedding should stay:

   ```text
   data/embeddings/embeddings_wsi_level_uni_20260531_221952.pkl
   ```

   It appears to already be part of the committed DVC snapshot, but it is not reflected in the April 22 Phase 1 metadata.

5. Decide what belongs in Git:

   Likely candidates:

   - phase scripts under `scripts/src/phase2/`
   - phase scripts under `scripts/src/phase3/`
   - phase scripts under `scripts/src/phase4/`
   - meaningful top-level runner scripts
   - curated wiki documentation
   - small configuration files such as selected clustering params

6. Decide what should not be committed:

   Likely cleanup or ignore candidates:

   - `.DS_Store`
   - `__pycache__/`
   - `*.pyc`
   - temporary/generated local artifacts
   - possibly `old_copilot_stuff/`

7. Decide how to handle generated results:

   For `results/phase2_tuning/`, choose one:

   - commit selected lightweight outputs to Git
   - track generated outputs with DVC
   - do not commit them and regenerate them from scripts

8. Fill or remove these empty files:

   ```text
   scripts/phase3.py
   scripts/phase4.py
   ```

9. Validate the pipeline end to end:

   - Phase 1 feature extraction / metadata
   - Phase 2 clustering tuning
   - Phase 3 fold creation and visualization
   - Phase 4 data, feature, and causal interpretability analysis

10. Commit the cleaned, intentional work.

## Bottom Line

The committed project baseline is intact and synced with GitHub. The active local work is a substantial expansion of the project into a multi-phase analysis pipeline, but it is not yet organized into a clean commit-ready state.

The top priority is now to clean or ignore the `.DS_Store` files that are making DVC report `data/` as modified. After that, the next priority is deciding what to commit, what to DVC-track, and what to clean out before preserving the new pipeline work.
