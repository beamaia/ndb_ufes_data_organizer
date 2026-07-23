# Setup and Installation

## System Requirements

| Requirement | Recommendation |
| --- | --- |
| Python | 3.10 through 3.12 |
| Environment manager | `uv` |
| Storage | About 20 GB when the public source dataset is also downloaded |
| Accelerator | Not required to rebuild the final public outputs or wiki |

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

Open:

```text
http://127.0.0.1:8000/ndb_ufes_data_organizer/
```

## Build and Validate the Wiki

```bash
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

The deployment workflow uses the same strict build and validation path.

## Rebuild the Final Public Outputs

The release builders use the frozen assignment and stored-run artifacts. They do not retrain the canonical models.

```bash
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
```

The sanitized bundle is written to:

```text
release/v1.0.0/public/
```

## Download the Source Dataset

Download NDB-UFES from Mendeley Data when source images or metadata are needed:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

The private DVC remote is maintainer-only and is not the public download path.

## Maintainer DVC Workflow

Use these commands only with the configured private remote credentials:

```bash
uv run dvc status
uv run dvc pull
```

## Troubleshooting

### MkDocs Is Not Installed

```bash
uv sync --extra docs
```

### Documentation Build Fails

```bash
uv run python -m mkdocs build --strict
```

Fix every reported missing link, missing asset, or navigation error before publishing.
