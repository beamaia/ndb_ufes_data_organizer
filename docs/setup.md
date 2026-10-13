# Setup and Installation

## System Requirements

| Requirement | Recommendation |
| --- | --- |
| Python | 3.10 through 3.12 |
| Environment manager | `uv` |
| Storage | About 8 GB for the data and the results |
| Accelerator | Only for the Virchow embeddings; the Mac GPU (`mps`) or CUDA, or a CPU with patience |

## Clone and Install

```bash
git clone https://github.com/beamaia/ndb_ufes_data_organizer.git
cd ndb_ufes_data_organizer
uv sync --extra docs
```

## Preview the Wiki

```bash
uv run python -m mkdocs serve
```

Open `http://127.0.0.1:8000/ndb_ufes_data_organizer/`.

## Build and Validate the Wiki

```bash
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

The deployment workflow runs the same steps.

## Get the Data

The published tables and folds are in git and need nothing else. To rebuild them you need the source data:

- **P-NDB-UFES patches and NDB-UFES origin images:** public, from Mendeley Data: `https://data.mendeley.com/datasets/bbmmm4wgr8/4`.
- **SAB images and the SAB patch crops:** private, kept by the maintainers.

The maintainers keep the whole `data/` folder and the pipeline outputs in a private DVC remote:

```bash
uv run dvc pull
```

## Rebuild the Dataset and the Folds

```bash
uv run dvc repro
```

This runs the stages of `dvc.yaml` in order, and only the stages whose inputs or code changed. The stages can also be run one by one; see [Reproducibility](reproducibility.md).

The embedding stage uses the Virchow model. Its weights are read from the local cache (`.cache/huggingface`) without network access; pass `--allow-download` to the stage to let it fetch them.

## Check the Repository Before Publishing

```bash
uv run python scripts/src/release/check_repo.py
```

It fails if any file git would publish contains a case prefix, a SAB photo name, a path on a local machine, or is larger than 5 MB, or if a published table has a column the data dictionary does not describe.

## Troubleshooting

### MkDocs Is Not Installed

```bash
uv sync --extra docs
```

### Documentation Build Fails

```bash
uv run python -m mkdocs build --strict
```

Fix every reported missing link, missing asset or navigation error before publishing.
