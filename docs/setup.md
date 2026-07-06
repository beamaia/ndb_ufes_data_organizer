# Setup And Installation

This page describes how to run the organizer locally and how public users should retrieve the source dataset.

## System Requirements

| Requirement | Recommendation |
| --- | --- |
| Python | 3.10 through 3.12 |
| Environment manager | `uv` |
| Storage | About 20 GB for the full public dataset and generated artifacts |
| Accelerator | Optional CUDA, Apple Metal/MPS, or CPU |

## Clone The Repository

```bash
git clone https://github.com/beamaia/ndb_ufes_data_organizer.git
cd ndb_ufes_data_organizer
```

## Install Dependencies

Install `uv` if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

Create the project environment:

```bash
uv sync
```

For documentation work:

```bash
uv sync --extra docs
```

## Download The Dataset

Public users should download NDB-UFES from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

After downloading, place the dataset files under the expected local `data/ndb_ufes/` structure before running the pipeline. The current organizer expects patch metadata, patch images, origin metadata, and relationship files to be available locally.

Expected key locations:

| Item | Expected Path |
| --- | --- |
| Patch metadata | `data/ndb_ufes/patch/parcial_pndb_ufes.csv` |
| Patch images | `data/ndb_ufes/patch_level/images/` |
| Origin metadata | `data/ndb_ufes/origin_level/csvs/ndb-ufes.csv` |
| Origin-patch mapping output | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` |

!!! note "Maintainer-only data sync"
    This repository also has a DVC/AWS S3 workflow for the maintainer's local data management. That remote is not the public distribution path. Public users should use the Mendeley Data link above.

## Optional Credentials

Some pretrained feature extractors are hosted on Hugging Face and may require accepted model terms plus an access token.

```bash
uv run huggingface-cli login
```

Or set a token in the shell:

```bash
export HUGGINGFACE_TOKEN=your_token_here
```

Phase 1 also reads compatible Hugging Face token variables from `.env`.

## Verify The Environment

```bash
uv run python -c "import torch; print(torch.__version__)"
uv run python -c "import pandas as pd; print(pd.__version__)"
```

Check for the expected source data:

```bash
uv run python - <<'PY'
from pathlib import Path

required = [
    Path("data/ndb_ufes/patch/parcial_pndb_ufes.csv"),
    Path("data/ndb_ufes/patch_level/images"),
    Path("data/ndb_ufes/origin_level/csvs/ndb-ufes.csv"),
]

for path in required:
    print(f"{path}: {path.exists()}")
PY
```

## Run The Pipeline

Phase 1 extracts frozen embeddings:

```bash
uv run python scripts/phase1.py
```

Phase 2 selects the best fold-ready morphology signal:

```bash
uv run python scripts/phase2.py
```

Phase 3 creates leakage-safe fold assignments:

```bash
uv run python scripts/phase3.py
```

Regenerate documentation and thesis figures:

```bash
uv run python scripts/generate_wiki_figures.py
```

## View Documentation Locally

```bash
uv sync --extra docs
uv run python scripts/copy_visualizations.py
uv run python scripts/generate_wiki_figures.py
uv run mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000/ndb_ufes_data_organizer/
```

## Maintainer DVC Workflow

The DVC workflow is for the repository maintainer. Use it only if you have the configured remote credentials.

```bash
uv run dvc status
uv run dvc pull
```

Troubleshooting for maintainer DVC access:

```bash
uv run dvc remote list
uv run dvc pull -vv
```

## Troubleshooting

### Hugging Face Model Download Fails

Confirm that model terms are accepted on Hugging Face and that `HUGGINGFACE_TOKEN` is available.

### Out Of Memory During Phase 1

Lower the Phase 1 batch size in `scripts/phase1.py`, or run on CPU with a smaller batch size.

### Documentation Build Fails

Run:

```bash
uv run mkdocs build --strict
```

Fix missing links, missing images, or navigation entries before publishing.
