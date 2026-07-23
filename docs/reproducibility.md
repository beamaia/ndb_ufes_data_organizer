# Reproducibility

This page reproduces the final public bundle and documentation from the frozen repository artifacts. It does not retrain the six canonical model runs.

## Environment

```bash
uv sync --extra docs
```

Public users can download the source dataset from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

Maintainer-only data synchronization may use DVC when the configured private remote credentials are available.

## Build the Final Public Outputs

Verify the six canonical parent runs and 30 stored child-fold records, then regenerate the sanitized experiment artifacts:

```bash
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
```

The final bundle is written under:

```text
release/v1.0.0/public/
```

## Verify Final Scope

```bash
uv run python - <<'PY'
import pandas as pd

base = "release/v1.0.0/public"
experiment1 = pd.read_csv(f"{base}/tables/experiment1_patch_assignments.csv")
experiment2 = pd.read_csv(f"{base}/tables/experiment2_patch_assignments.csv")
source_index = pd.read_csv(f"{base}/tables/validated_wsi_index.csv")

assert len(experiment1) == 3763
assert len(experiment2) == 3763
assert len(source_index) == 251
assert source_index["patch_count"].sum() == 3763

source_totals = sorted(source_index.groupby("source")["patch_count"].sum())
assert source_totals == [652, 3111]
PY
```

The two experiment tables must contain identical patch ID sets and diagnosis totals. The source-image index must contain 203 both-source groups and 48 SAB-only groups.

## Verify Canonical Results

The canonical builder requires:

- six completed parent runs,
- 30 completed child-fold records,
- folds 0–4 for every model/experiment pair,
- the frozen dataset hashes,
- balanced accuracy equal to macro recall,
- published aggregates reproducible from child-fold metrics.

The machine-readable evidence is stored under `release/v1.0.0/public/experiments/`.

## Build and Validate the Wiki

Regenerate the factsheet and thesis figure bundles from the final public assignment tables and source-image index:

```bash
uv run python scripts/src/docs/generate_factsheet_figures.py
```

Then build and validate the site:

```bash
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

Preview the wiki locally:

```bash
uv run python -m mkdocs serve
```

Open:

```text
http://127.0.0.1:8000/ndb_ufes_data_organizer/
```

## Privacy Boundary

Only the public profile may be copied into the documentation site or distributed as the public bundle. LAB-profile artifacts, private crosswalks, raw SAB identifiers, direct patient/lesion identifiers, checkpoints, MLflow storage, secrets, and local paths must remain outside the public payload.
