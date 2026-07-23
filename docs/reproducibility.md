# Reproducibility

Documentation/index verified: 19 July 2026. Pipeline artifacts referenced below come from the validated runs noted in each section.

## Current Thesis Relationship Artifacts

The current thesis/article artifacts include updated relationship CSVs that connect the full P-NDB-UFES patch scope to recovered NDB/SAB linkage where available.

Current expected outputs:

| File | Expected rows |
| --- | ---: |
| `data/ndb_ufes/link_level/csvs/ndb_pndb_relation.csv` | 3,763 patch rows |
| `data/ndb_ufes/link_level/csvs/pndb_ndb_origin_relationships.csv` | 880 origin/fallback-group rows |
| `results/phase3/current_thesis_batches/batch1_recovered_reference_patch_level.csv` | 3,763 patch rows |
| `results/phase3/current_thesis_batches/batch2_patient_first_patch_level.csv` | 3,763 patch rows |
| `results/phase3/current_thesis_batches/batch3_virchow_pruned_patch_level.csv` | 3,351 exploratory archive rows |
| `results/phase3/current_thesis_batches/linkage_scope_summary.csv` | 6 summary rows |

The Phase 1--3 commands below reproduce the SAB-linked matched-subset organizer
pipeline. The final thesis comparison uses Batch 1 and Batch 2 only; Batch 3 is
retained for explicitly labelled exploratory compatibility. Check the frozen
batch files against `results/phase3/current_thesis_batches/artifact_manifest.json`
and the relationship files above.

## Atlas public index

The atlas-facing public index is derived from the phase-0 validated-linkage inventory. It is deliberately small and excludes raw SAB case prefixes, image names, and local filesystem paths.

| File | Expected rows | Role |
| --- | ---: | --- |
| `docs/assets/atlas/validated_wsi_index.csv` | 251 | Public-pseudonymous WSI lookup table. |
| `docs/assets/atlas/atlas_manifest.json` | 1 | Scope, source, privacy, and excluded-field manifest. |
| `docs/assets/atlas/atlas_schema.json` | 1 | Versioned public-index field contract. |
| `docs/assets/atlas/metadata_conflict_summary.json` | 1 | Aggregate metadata-conflict review report. |
| `docs/assets/atlas/atlas_methods.json` | 1 | Implemented atlas formulas and threshold contract. |
| `docs/assets/atlas/release_facts.json` | 1 | Aggregate release facts used to cross-check the reader-facing scope and batch summaries. |

Regenerate it after a validated phase-0 linkage run:

```bash
uv run python scripts/src/release/build_atlas_public_index.py
```

Before committing or deploying the public export, run the data-free release check:

```bash
uv run python scripts/src/release/validate_atlas_public_index.py
```

The atlas layer assigns 3,763 patches to 251 validated WSI IDs. The thesis relationship layer remains separately described as 3,086 metadata-linked rows plus 677 rows with missing metadata linkage.

## Canonical experiment release

The release builder reads only the stored Experiment 1/2 parent and child-fold
records. It does not contact MLflow and does not retrain a model:

```bash
uv run python scripts/src/release/build_canonical_experiment_release.py
```

The builder requires six canonical parents, 30 child-fold records, folds 0--4
for every model/experiment pair, the frozen dataset hashes, and balanced
accuracy equal to macro recall. It independently recomputes the published
means and population standard deviations from the child metrics.

Create and scan the strictly deidentified public bundle with:

```bash
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
```

Internal exports require the separate `--profile lab` mode and use a different
destination. LAB artifacts must never be copied into the public bundle.

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

Expected current cardinality: 203 origins and 3,086 patches for every embedding model. Confirm the completed run in `results/phase1/metadata/master_runs.json` and `runs_summary.txt`.

## Phase 2

```bash
uv run python scripts/phase2.py
```

Review:

- `results/phase2/tuning/phase2_model_selection.csv`
- `results/phase2/tuning/clustering_params_{model}.json`
- `clustering_params.json`

Every accepted row must have `min_cluster_size >= 11` and `max_cluster_size_ratio <= 5`. The current accepted result is Virchow/PCA=2/K=3. Swin is expected to be present as rejected, not to abort the run.

## Phase 3

```bash
uv run python scripts/phase3.py
```

The command writes the two fold CSVs, stratification validation table, and
`fold_validation.json` under `results/phase3/fold_creation/`.

Quick verification:

```bash
uv run python - <<'PY'
import json
import pandas as pd

base = "results/phase3/fold_creation"
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

## Release validation

```bash
uv run python scripts/src/release/validate_public_atlas_pdf.py
uv run python scripts/src/release/validate_atlas_public_index.py
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py
uv run --extra docs python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

The public v1.0.0 repository does not ship the internal unit-test files. These
release validators check the published atlas, experiment evidence, wiki, and
public payload directly.

## Reproducibility Boundary

The selected feature extractor is frozen and external. Phase 2 uses no downstream labels or model performance to choose the clustering. The fold files must be used at origin level: never resplit patch rows independently.
