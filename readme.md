# NDB-UFES Data Organizer

Repository for the final public NDB-UFES oral histopathology experiment assignments, validated patch-to-source-image linkage, canonical results, data dictionary, reproducibility notes, and leakage-aware reuse guidance.

This repository publishes data-organization and result artifacts. Model training remains in a separate repository.

## Final Scope

Both released experiments contain all 3,763 P-NDB-UFES patches. The validated linkage assigns them to 251 source-image groups:

| Source-image role | Groups | Patches |
| --- | ---: | ---: |
| Public NDB-UFES + SAB evidence | 203 | 3,111 |
| SAB-only evidence | 48 | 652 |
| **Total** | **251** | **3,763** |

Experiment 1 is the released patch-level reference split. Experiment 2 is the patient-first grouped split and keeps validated source-image and patient/case groups within one fold.

## Public Documentation

The published wiki is available at:

https://beamaia.github.io/ndb_ufes_data_organizer/

Key pages:

- `docs/factsheet.md`: final scope, linkage, labels, experiments, and reuse limits.
- `docs/data-dictionary.md`: public files, counts, columns, and field interpretation.
- `docs/thesis-experiment-batches.md`: frozen two-experiment design.
- `docs/experiment-results.md`: canonical metrics, figures, statistics, and run provenance.
- `docs/reproducibility.md`: final bundle and documentation validation commands.

Preview locally:

```bash
uv sync --extra docs
uv run python -m mkdocs serve
```

Open `http://127.0.0.1:8000/ndb_ufes_data_organizer/`.

## Build the Final Public Outputs

```bash
uv sync
uv run python scripts/src/release/build_canonical_experiment_release.py
uv run python scripts/src/release/generate_research_ready_tables.py --profile public
```

The sanitized bundle is written under `release/v1.0.0/public/`.

## Validate the Wiki

```bash
uv sync --extra docs
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

Private source-image identifiers, private crosswalks, direct patient/lesion identifiers, local paths, checkpoints, and raw MLflow storage are excluded from the public payload.

## Source Dataset

Download NDB-UFES from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

DVC/AWS S3 synchronization is maintainer-only and is not the public download path.

## Leakage-Aware Use

Use the released fold assignments instead of random patch-level splits. Keep validated source-image and patient/case groups within one train, validation, or test partition. Fold 5 is held out from training and validation.

## Licensing

Repository code is licensed under GPL-3.0. Documentation and derived public artifacts are provided under CC BY 4.0; see `LICENSE-DOCS.md` and `NOTICE`. Software citation metadata is in `CITATION.cff`.

## Lab Attribution

This work is attributed to the [Nature-inspired Computing Lab, Labcin](https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling).

## Implementation Support

This project uses AI-assisted tools, including GitHub Copilot, Claude, and OpenAI Codex, to support implementation and documentation.

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
