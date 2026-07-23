# Setup and installation

This is the shortest path from a clean checkout to either the pipeline or the documentation site. The public source data comes from Mendeley; the private DVC remote is only for maintainer-side synchronization.

## System Requirements

| Requirement | Recommendation |
| --- | --- |
| Python | 3.10 through 3.12 |
| Environment manager | `uv` |
| Storage | About 20 GB for the full public dataset and generated artifacts |
| Accelerator | Optional CUDA, Apple Metal/MPS, or CPU |

## Clone the repository

```bash
git clone https://github.com/beamaia/ndb_ufes_data_organizer.git
cd ndb_ufes_data_organizer
```

## Documentation-only quickstart

After `uv` is available, you can read, validate, and build the wiki without
downloading private DVC data or the LAB atlas. The root-level public PDF is a
repository artifact, while the committed lightweight atlas assets are the
documentation payload:

```bash
uv sync --extra docs
uv run python scripts/src/release/validate_public_atlas_pdf.py
uv run python scripts/src/release/validate_atlas_public_index.py
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
uv run python -m mkdocs serve
```

Open `http://127.0.0.1:8000/ndb_ufes_data_organizer/`. The same strict build is used by the deployment workflow. The full pipeline setup below is only needed when you want to regenerate research artifacts, figures, or the public atlas export from local inputs.

## Install dependencies

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

## Download the dataset

Download NDB-UFES from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

After downloading, place the dataset files under the expected local `data/ndb_ufes/` structure. The organizer expects patch metadata, patch images, origin metadata, and relationship files to be available locally.

Expected key locations:

| Item | Expected Path |
| --- | --- |
| Patch metadata | `data/ndb_ufes/patch/parcial_pndb_ufes.csv` |
| Patch images | `data/ndb_ufes/patch_level/images/` |
| Origin metadata | `data/ndb_ufes/origin_level/csvs/ndb-ufes.csv` |
| Origin-patch mapping output | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` |

!!! note "Maintainer-only data sync"
    This repository also has a DVC/AWS S3 workflow for the maintainer's local data management. That remote is not the public distribution path. Public users should use the Mendeley Data link above.

## Optional credentials

Some pretrained feature extractors are hosted on Hugging Face and may require accepted model terms plus an access token.

```bash
uv run huggingface-cli login
```

Or set a token in the shell:

```bash
export HUGGINGFACE_TOKEN=your_token_here
```

Phase 1 also reads compatible Hugging Face token variables from `.env`.

## Verify the environment

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

## Run the pipeline

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
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py
```

Verify the canonical stored-run evidence and generate the public release
bundle without retraining:

```bash
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
```

## View the documentation locally

```bash
uv sync --extra docs
uv run python scripts/src/docs/copy_visualizations.py
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py
uv run python -m mkdocs serve
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
uv run python -m mkdocs build --strict
```

Fix missing links, missing images, or navigation entries before publishing.
