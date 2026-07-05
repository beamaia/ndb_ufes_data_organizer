# Phase 1: Feature Extraction

Phase 1 creates the origin-patch mapping and extracts frozen embeddings from every configured pretrained backbone. It is an execution pipeline, not a model-training phase.

## Architecture

`scripts/phase1.py` is the executable entrypoint. It configures model cache locations, authenticates with HuggingFace when credentials are available, creates the mapping, iterates over the model registry, and records run metadata.

Core helpers:

- `scripts/src/phase1/extraction_func.py`: creates the mapping and saves embedding dictionaries.
- `scripts/src/phase1/feature_extractor.py`: loads one model, applies model-specific preprocessing, extracts embeddings, and caches patch features.
- `scripts/src/phase1/metadata_tracker.py`: records per-model extraction metadata.
- `scripts/src/phase1/config.yaml`: declares model IDs, preprocessing, extraction method, output dimension, and registry metadata.

Model loading is shared through `scripts/src/models/`. External model cache configuration and HuggingFace authentication live under `scripts/src/utils/` because they are not Phase-1-specific behavior.

## Inputs

| Input | Path |
| --- | --- |
| Patch metadata | `data/ndb_ufes/patch/parcial_pndb_ufes.csv` |
| Patch images | `data/ndb_ufes/patch_level/images/` |
| Model registry | `scripts/src/phase1/config.yaml` |
| Optional environment credentials | `.env` with `HUGGINGFACE_TOKEN` or compatible HuggingFace token variables |

Expected current data cardinality is 203 matched origins and 3,086 patch rows.

## Outputs

| Output | Path |
| --- | --- |
| Origin-patch mapping | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` |
| Embedding dictionaries | `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl` |
| Temporary feature cache | `results/phase1_feature_cache/` |
| Run metadata | `results/phase1_metadata/master_runs.json` |
| Human summary | `results/phase1_metadata/runs_summary.txt` |

Each embedding dictionary is keyed by `origin_id`; each value is a NumPy array with shape `(patch_count_for_origin, model_output_dim)`.

## Preprocessing Contract

Every backbone uses the preprocessing declared in `config.yaml`: resize size, optional crop size, interpolation, normalization mean, and normalization standard deviation. The pipeline does not apply one universal ImageNet normalization to every model.

Extraction methods are registry-driven:

| Method | Behavior |
| --- | --- |
| `cls_token` | Use the transformer CLS token. |
| `cls_mean_concat` | Concatenate CLS token and mean patch-token embedding; used by Virchow. |
| `global_avg_pool` | Average CNN feature maps or transformer token features. |

The cache fingerprint includes model ID, preprocessing, output dimension, extraction method, and normalization settings so stale features from another preprocessing contract are not reused.

## Run

```bash
uv run python scripts/phase1.py
```

The current completed run extracted all configured models and created embeddings for all 203 origins and 3,086 patches. See [Phase 1 Results](phase1-results.md) for the current artifact summary.

## Manual Use

```python
from src.phase1.extraction_func import (
    create_origin_patch_mapping,
    extract_wsi_level_features,
)

mapping = create_origin_patch_mapping(
    source_csv_path="data/ndb_ufes/patch/parcial_pndb_ufes.csv",
    patch_image_dir="data/ndb_ufes/patch_level/images",
    output_csv_path="data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv",
)

embedding_path = extract_wsi_level_features(
    model_name="virchow",
    origin_patch_mapping=mapping,
    batch_size=32,
    device="mps",
)
```

## Audit Checklist

- Mapping has 203 unique origins.
- Saved embeddings contain the same 203 origin keys.
- Total embedded patch arrays sum to 3,086 patches.
- The metadata tracker records each configured model run.
- HuggingFace-gated models use accepted model terms and a valid token.
- Feature cache lives under `results/phase1_feature_cache/`, not an unrelated local disk cache.

## Troubleshooting

If model downloads fail, confirm HuggingFace terms are accepted for gated models and that `.env` or the shell contains a valid token.

If extraction runs out of memory, reduce `BATCH_SIZE` in `scripts/phase1.py` or pass a smaller batch size to `run()`.

If embeddings look incompatible with a model, clear `results/phase1_feature_cache/` and rerun; cache keys should normally prevent this, but clearing the cache is the quickest sanity reset.

**Last verified**: 29 June 2026.
