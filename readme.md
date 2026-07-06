# NDB-UFES Data Organizer

Repository for organizing the public NDB-UFES oral histopathology dataset into leakage-safe cross-validation folds, with a data dictionary, factsheet, reproducibility notes, and audit guidance for public reuse.

This repository is a data organizer. It is not a downstream model-training repository.

## Purpose

- Create cross-validation folds where patches from the same origin/WSI never cross folds.
- Publish fold assignment files that external users can reuse consistently.
- Document labels, task fields, demographics/risk factors, missingness, limitations, and leakage-safe usage.
- Use frozen pretrained embeddings only as an optional morphology-aware fold stratification signal.

## Public Documentation

The published documentation site is available at:

https://beamaia.github.io/ndb_ufes_data_organizer/

This work is attributed to the Nature-inspired Computing Lab, Labcin:

https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling

The documentation source lives in `docs/` and is wired through `mkdocs.yml`.

- `docs/factsheet.md`: required public dataset factsheet.
- `docs/data-dictionary.md`: current CSV schemas, counts, labels, and field notes.
- `docs/pipeline.md`: phase overview and leakage framing.
- `docs/reproducibility.md`: commands and expected outputs.

Serve locally with:

```bash
uv sync --extra docs
uv run mkdocs serve
```

## Quick Start

Install dependencies:

```bash
uv sync
```

Download the public source dataset from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

DVC/AWS S3 synchronization is maintainer-only and is not the public download path.

Run implemented phases:

```bash
uv run python scripts/phase1.py
uv run python scripts/phase2.py
uv run python scripts/phase3.py
```

Regenerate documentation figures and wiki Plotly previews:

```bash
uv run --extra docs python scripts/generate_wiki_figures.py
```

Generate full Plotly PNG, SVG, and PDF thesis copies only when needed:

```bash
uv run --extra docs python scripts/generate_wiki_figures.py --export-plotly-thesis
```

## Current Key Artifacts

Current canonical generated artifacts:

- `results/phase2_tuning/phase2_model_selection.csv`
- `clustering_params.json`
- `results/phase3_fold_creation/fold_assignments_origin.csv`
- `results/phase3_fold_creation/fold_assignments_patch_level.csv`
- `results/phase3_fold_creation/fold_validation.json`

## Dataset Snapshot

Matched subset available for fold design:

| Item | Count |
| --- | ---: |
| Patch rows | 3,086 |
| Matched origins | 203 |
| Planned folds | 6 |
| Diagnostic classes | 3 |

Patch-level diagnosis counts:

| Diagnosis | Patch count |
| --- | ---: |
| OSCC | 1,517 |
| Leukoplakia with dysplasia | 930 |
| Leukoplakia without dysplasia | 639 |

## Leakage-Safe Use

Once folds are finalized, use the provided fold assignments instead of random patch-level splits. All patches sharing an `origin_id` must remain in the same train/validation/test partition.

Frozen external pretrained embeddings may be used for unsupervised morphology-aware stratification, but fold construction must not be chosen using downstream validation/test performance.

## Development Notes

Before publishing a new documentation release:

- verify all fold invariants.
- decide which root Markdown files should be promoted, archived, or deleted.
- keep Phase 4 out of the accepted release path until it has an independent audit.

## Implementation Support

This project uses AI-assisted tools, including GitHub Copilot, Claude, and OpenAI Codex, to enhance productivity and improve documentation.

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
