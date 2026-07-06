# Reproducibility

Last verified: 29 June 2026.

## Environment

```bash
uv sync
```

Public users should download the source dataset from Mendeley Data and place it under the expected `data/ndb_ufes/` paths. Maintainer-only data synchronization may use DVC when the private remote credentials are available.

Hugging Face credentials may be provided through `.env`. Phase 1 accepts `HUGGINGFACE_TOKEN` and configures external model caches under the repository `.cache/` directory on the SSD.

## Phase 1

```bash
uv run python scripts/phase1.py
```

Expected current cardinality: 203 origins and 3,086 patches for every embedding model. Confirm the completed run in `results/phase1_metadata/master_runs.json` and `runs_summary.txt`.

## Phase 2

```bash
uv run python scripts/phase2.py
```

Review:

- `results/phase2_tuning/phase2_model_selection.csv`
- `results/phase2_tuning/clustering_params_{model}.json`
- `clustering_params.json`

Every accepted row must have `min_cluster_size >= 11` and `max_cluster_size_ratio <= 5`. The current accepted result is Virchow/PCA=2/K=3. Swin is expected to be present as rejected, not to abort the run.

## Phase 3

```bash
uv run python scripts/phase3.py
```

The command writes the two fold CSVs, stratification audit, and `fold_validation.json` under `results/phase3_fold_creation/`.

Quick verification:

```bash
uv run python - <<'PY'
import json
import pandas as pd

base = "results/phase3_fold_creation"
origins = pd.read_csv(f"{base}/fold_assignments_origin.csv")
patches = pd.read_csv(f"{base}/fold_assignments_patch_level.csv")
report = json.load(open(f"{base}/fold_validation.json"))

assert len(origins) == 203
assert len(patches) == 3086
assert set(origins.origin_id) == set(patches.origin_id)
assert patches.groupby("origin_id").fold.nunique().max() == 1
assert set(origins.fold) == set(range(6))
assert report["max_stratum_fold_count_range"] <= 1
assert report["patch_imbalance_ratio"] <= 1.10
print(report)
PY
```

Current fold patch counts are 520, 510, 511, 511, 524, and 510.

## Tests

```bash
uv run python -m unittest discover -s tests -v
uv run python scripts/generate_wiki_figures.py
uv run --extra docs mkdocs build --strict
```

The unit suite covers eligibility filtering, degenerate-cluster rejection, preservation of origin `0`, exact origin-set validation, deterministic assignment, stratum spread, and leakage detection.

## Reproducibility Boundary

The selected feature extractor is frozen and external. Phase 2 uses no downstream labels or model performance to choose the clustering. The fold files must be used at origin level: never resplit patch rows independently.
