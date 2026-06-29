# Reproducibility

This page records how to regenerate and audit the organizer artifacts. It intentionally separates current working commands from stale or empty entrypoints.

## Environment

Install dependencies:

```bash
uv sync
```

Pull DVC-managed data if the remote is configured:

```bash
uv run dvc pull
```

## Current Script Inventory

| Script | Current status |
| --- | --- |
| `scripts/phase1.py` | Implemented entrypoint for feature extraction. |
| `scripts/phase2.py` | Implemented entrypoint for PCA/K-Means tuning. |
| `scripts/phase3.py` | Implemented entrypoint for Phase 3 fold creation. |
| `scripts/src/phase3/phase3_fold_creation.py` | Implemented Phase 3 fold creation module using Phase 2-selected embeddings and parameters. |
| `scripts/src/phase3/phase3_visualize_clusters.py` | Optional Phase 3 visualization helper module. |
| `scripts/src/phase4/*.py` | Phase 4 implementations exist, but some paths are stale and require audit before rerun. |

## Phase 1: Feature Extraction

Command:

```bash
uv run python scripts/phase1.py
```

Expected outputs:

- `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`
- `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl`
- `results/phase1_metadata/`
- optional `results/phase1_feature_cache/`

Audit checks:

```bash
uv run python - <<'PY'
import csv
for path in [
    "data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv",
    "data/ndb_ufes/patch/parcial_pndb_ufes.csv",
]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    print(path, len(rows), "rows")
PY
```

## Phase 2: Morphology Tuning

Command:

```bash
uv run python scripts/phase2.py
```

Expected outputs when rerun:

- per-model tuning tables;
- averaged tuning summaries;
- selected-parameter files;
- visual summaries for reviewing PCA/K-Means behavior.
- `clustering_params.json`, recording the selected model and exact embedding input for Phase 3.

`scripts/phase2.py` is the only Phase 2 executable. Modules under `scripts/src/phase2/` expose reusable loading, tuning, averaging, selection, and visualization functions without import-time execution.

These files are not treated as fixed documentation artifacts yet because Phase 2 is expected to be rerun.

Recommended policy:

- use 5 repeated K-Means runs by default;
- use 3 only as an exploratory shortcut;
- compare mean and standard deviation, cluster sizes, and interpretability;
- do not select the stratification configuration using downstream model performance.

After rerun, summarize candidate configurations only after confirming the output schema and accepted model list.

## Phase 3: Fold Creation

Use the top-level `scripts/phase3.py` runner for Phase 3 fold creation; audit outputs and parameters as needed.

Implementation file to audit:

```text
scripts/src/phase3/phase3_fold_creation.py
```

Existing fold outputs to audit:

- `data/ndb_ufes/origin_level/csvs/fold_assignments_origin.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv`
- `data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_with_images.csv`

Expected output from a current Phase 3 rerun:

- `results/phase3_fold_creation/stratification_variables_audit.csv`

The audit file records which variables entered the fold key and why additional demographic/clinical variables were excluded or retained as descriptive fields.

Invariant check:

```bash
uv run python - <<'PY'
import csv, collections
patch_file = "data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv"
rows = list(csv.DictReader(open(patch_file, newline="")))
by_origin = collections.defaultdict(set)
fold_counts = collections.Counter()
for r in rows:
    by_origin[r["origin_id"]].add(r["fold"])
    fold_counts[r["fold"]] += 1
bad = {origin: folds for origin, folds in by_origin.items() if len(folds) != 1}
print("patch rows:", len(rows))
print("origins:", len(by_origin))
print("fold counts:", dict(sorted(fold_counts.items())))
print("origins spanning multiple folds:", len(bad))
PY
```

Observed provisional artifact shape:

- 3,086 patch rows;
- 203 origins;
- zero origins spanning multiple folds.

Do not treat fold counts as final while Phase 2 morphology selection remains under audit. A current Phase 3 rerun should also produce `stratification_variables_audit.csv`, showing which variables were included in or excluded from fold construction.

## Phase 4: Validation and Public Documentation

Do not treat the top-level `scripts/phase4.py` as working until it is implemented.

Audit these implementation files before running:

- `scripts/src/phase4/phase4_feature_analysis.py`
- `scripts/src/phase4/phase4_data_analysis.py`
- `scripts/src/phase4/phase4_causal_interpretability.py`
- `scripts/src/phase4/validate_causal_interpretability.py`

Before rerun, check and update paths to match the current fold output locations.

## Documentation Build

Serve the documentation locally:

```bash
uv sync --extra docs
uv run mkdocs serve
```

The documentation should include:

- Home
- Dataset Factsheet
- Setup & Installation
- Pipeline Overview
- Reproducibility
- Implementation Status
- Phase 1 code/results pages
- Data Dictionary

## Cleanup Rule

Do not delete root Markdown files until the manual audit confirms whether their content has been promoted into `docs/`, archived, or superseded.
