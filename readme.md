# NDB-UFES Data Organizer

Repository for organizing the public NDB-UFES oral histopathology dataset into
leakage-safe cross-validation folds, with a patch-to-source-image atlas, data
dictionary, factsheet, reproducibility notes, and validation guidance for
public reuse.

This repository is a data organizer. It is not a downstream model-training repository.

## Purpose

- Create cross-validation folds where patches from the same source image never cross folds.
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
- `docs/atlas-guide.md`: how to read the patch-to-source-image atlas and its two linkage layers.
- `docs/atlas-index.md`: lightweight public-pseudonymous source-image index and manifest.
- `docs/release-facts.md`: readable scope snapshot backed by the public release-facts JSON.
- `docs/thesis-experiment-batches.md`: frozen Experiment 1/2 design and Batch 3 archive boundary.
- `docs/experiment-results.md`: metrics, fold distributions, execution times, confusion matrices, loss figures, and exploratory statistics.
- [`NDB_UFES_SAB_atlas_public.pdf`](NDB_UFES_SAB_atlas_public.pdf): the
  sanitized, root-level 251-source-image atlas release artifact.

Serve locally with:

```bash
uv sync --extra docs
uv run python scripts/src/release/validate_public_atlas_pdf.py
uv run python scripts/src/release/validate_atlas_public_index.py
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
uv run python -m mkdocs serve
```

The root-level public PDF is a repository release artifact and is deliberately
not copied into the MkDocs payload, which remains below its 55 MB gate. The
editable DOCX source and the identifier-bearing LAB PDF are local-only,
ignored artifacts. The public-pseudonymous atlas index, manifest, schema,
methods contract, and aggregate conflict report provide the searchable web
surface.

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
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py
```

Build the documentation exactly as the deployment workflow does:

```bash
uv run --extra docs python -m mkdocs build --strict
```

Generate full Plotly PNG, SVG, and PDF thesis copies only when needed:

```bash
uv run --extra docs python scripts/src/docs/generate_wiki_figures.py --export-plotly-thesis
```

## Current Key Artifacts

Current canonical generated artifacts:

- `docs/assets/experiments/canonical_run_manifest.json`
- `docs/assets/experiments/canonical_results.csv`
- `release/v1.0.0/public/`
- `results/phase2/tuning/phase2_model_selection.csv`
- `clustering_params.json`
- `results/phase3/fold_creation/fold_assignments_origin.csv`
- `results/phase3/fold_creation/fold_assignments_patch_level.csv`
- `results/phase3/fold_creation/fold_validation.json`

## Current Scope Snapshot

The repository currently tracks three related scopes:

| Item | Count |
| --- | ---: |
| Full P-NDB-UFES patch rows used to start the thesis batches | 3,763 |
| Patches matched to public NDB-UFES origins and used in the earlier metadata/embedding analyses | 3,086 |
| SAB-linked patches without a public NDB-UFES origin match | 677 |
| Source-image groups in the atlas | 251 |
| Public NDB-UFES + SAB / SAB-only source-image groups | 203 / 48 |
| Matched origins available for the older fold-design run | 203 |
| Planned folds for that run | 6 |

The 3,763, 3,086/677, and 251 counts describe different layers. See
[Thesis Experiment Design](docs/thesis-experiment-batches.md),
[Canonical Experiment Results](docs/experiment-results.md), and
[Atlas Guide](docs/atlas-guide.md) before comparing them.

Patch-level diagnosis counts:

| Diagnosis | Patch count |
| --- | ---: |
| OSCC | 1,517 |
| Leukoplakia with dysplasia | 930 |
| Leukoplakia without dysplasia | 639 |

## Leakage-Safe Use

Once folds are finalized, use the provided fold assignments instead of random patch-level splits. All patches sharing an `origin_id` must remain in the same train/validation/test partition.

Frozen external pretrained embeddings may be used for unsupervised morphology-aware stratification, but fold construction must not be chosen using downstream validation/test performance.

## Release validation

Before publishing a new documentation release:

- verify all fold and public-export invariants.
- reproduce the six published aggregates from the 30 stored child-fold records.
- run the forbidden-field, identifier, email, secret, and absolute-path scans.
- build MkDocs in strict mode and keep the site payload below 55 MB.

Experiment 1 and Experiment 2 are the final thesis comparisons. Batch 3 is an
exploratory archive and is not part of the default release matrix.

## Licensing

Repository code is licensed under GPL-3.0. Documentation and derived public
artifacts are provided under CC BY 4.0; see `LICENSE-DOCS.md` and `NOTICE`.
Software citation metadata is in `CITATION.cff`.

## Implementation Support

This project uses AI-assisted tools, including GitHub Copilot, Claude, and OpenAI Codex, to enhance productivity and improve documentation.

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
