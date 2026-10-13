# NDB-UFES Data Organizer

Rebuilds the dataset behind the P-NDB-UFES oral histopathology patches: every patch is tied to its parent picture, pictures and patients that share evidence are grouped into case groups, and the folds never split a case group. It publishes the tables, the folds, a factsheet and a data dictionary.

This repository builds the dataset and the folds. Model training is in a separate repository, `ndb_ufes_training_pipeline`, which reads the folds from here.

## The dataset

| Item | Count |
| --- | ---: |
| Patches (512 × 512 pixels) | 3,763 |
| Parent pictures | 288 |
| Cases (masked patients) / case groups | 64 / 63 |
| Classes | 3 |
| Folds | 6 |

The full numbers, generated from the tables, are in `docs/factsheet-ndb-ufes.md`, `docs/factsheet-p-ndb-ufes.md`, `docs/old-folds.md` and `docs/folds.md`. Every column is described in `docs/data-dictionary.md`.

## Use the folds

Download `results/phase1/folds/fold_assignments.csv` and use its `fold` column instead of a random patch-level split. Patches of one case group are always in one fold, so patches of the same patient never sit on both sides of an evaluation. The three patches with an empty `fold` are exact duplicates and are left out. The label to predict is `patch_diagnosis`.

## Documentation

The wiki is published at https://beamaia.github.io/ndb_ufes_data_organizer/.

```bash
uv sync --extra docs
uv run python -m mkdocs serve
```

Open `http://127.0.0.1:8000/ndb_ufes_data_organizer/`.

## Rebuild

```bash
uv run dvc pull      # maintainers only: the source data and pipeline outputs
uv run dvc repro     # runs every stage of dvc.yaml
```

The stages, their commands and what each guarantees are in `docs/reproducibility.md`. DVC and the private S3 remote are for the maintainers; the public source data is on Mendeley Data (below).

## Check before publishing

```bash
uv run python scripts/src/release/check_repo.py
uv run python -m mkdocs build --strict
uv run python scripts/src/release/validate_static_site.py site
uv run python scripts/src/release/validate_public_payload.py site --max-mib 55
```

The first command scans everything git would publish for case prefixes, SAB photo names, local paths and oversized files, and checks that every published column is in the data dictionary. SAB images, case prefixes, file names and paths are private and never published; the public tables use pseudonyms.

## Source dataset

Download NDB-UFES from Mendeley Data:

```text
https://data.mendeley.com/datasets/bbmmm4wgr8/4
```

## Licensing

Repository code is licensed under GPL-3.0. Documentation and derived public artifacts are provided under CC BY 4.0; see `LICENSE-DOCS.md` and `NOTICE`. Software citation metadata is in `CITATION.cff`.

## Lab Attribution

This work is attributed to the [Nature-inspired Computing Lab, Labcin](https://www.researchgate.net/lab/Nature-inspired-Computing-Lab-Labcin-Renato-Krohling).

## Implementation Support

This project uses AI-assisted tools, including GitHub Copilot, Claude, and OpenAI Codex, to support implementation and documentation.

## Citation

Falcao Ribeiro de Assis, Maria Clara. Lima, Leandro Muniz de. de Barros, Liliana Aparecida Pimenta. Velloso, Tania Regina. Krohling, Renato. Camisasca, Danielle. 2023. "NDB-UFES: An oral cancer and leukoplakia dataset composed of histopathological images and patient data." Mendeley Data, V4. doi: 10.17632/bbmmm4wgr8.4.
