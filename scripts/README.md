# Scripts

Top-level scripts are phase entrypoints only; the code is in `src/`.

- `phase0.py`: builds the dataset tables (`src/phase0_dataset_builder/`).
- `phase1.py`: embeddings, morphology clusters and folds (`src/phase1_folds/`).
- `src/models/`: the model registry, loader and feature extractor used for the embeddings.
- `phase2.py`: renders what the wiki and the thesis show: the atlases, statistics, charts and the generated pages (`src/phase2_report/`).
- `src/release/`: the checks and validators run before publishing, and the v1.0.0 release builder.

The whole build is described in `../dvc.yaml`; `uv run dvc repro` runs it in order.

## Phase 0: dataset tables

Run from the repository root:

```bash
uv run python scripts/phase0.py picture-features    # SIFT features of every picture (cache)
uv run python scripts/phase0.py picture-relations   # which pictures show the same tissue
uv run python scripts/phase0.py patch-pool-search   # template-match every patch in every picture (slow, run once)
uv run python scripts/phase0.py patch-placements    # project patches into related pictures
uv run python scripts/phase0.py patch-table         # patch, picture and case tables, with all checks and the case groups
```

`patch-table` writes `results/phase0/dataset_tables/`: the `public` tables carry pseudonyms only, the `private_lab` tables (git-ignored) carry case prefixes and file paths.

## Phase 1: folds

```bash
uv run python scripts/phase1.py patch-embeddings    # Virchow embedding of every patch
uv run python scripts/phase1.py cluster-choices     # how well the patches cluster, for 2 to 9 clusters (optional)
uv run python scripts/phase1.py patch-clusters      # the 3 morphology clusters
uv run python scripts/phase1.py cluster-view        # picture of the clusters (optional)
uv run python scripts/phase1.py folds               # the folds and their summary table
```

## Phase 2: atlases and pages

```bash
uv run python scripts/phase2.py patient-atlas       # PDF: every picture with its patch boxes, each patch beside its crop
uv run python scripts/phase2.py aligned-atlas       # PDF: related pictures rotated into one frame
uv run python scripts/phase2.py stats               # every table and statistic as a CSV file
uv run python scripts/phase2.py figures             # the SVG charts of the wiki
uv run python scripts/phase2.py pages               # the generated wiki pages
```

The atlases are written to `../atlases/` and published in git.

## Before publishing

```bash
uv run python scripts/src/release/check_repo.py
```
