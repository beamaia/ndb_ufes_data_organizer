# Phase 1 Code

Phase 1 creates the origin-patch mapping and extracts frozen embeddings from every configured pretrained backbone. It is an execution pipeline, not a model-training phase.

## Entrypoint

```text
scripts/phase1.py
```

`run(device: str = DEVICE, batch_size: int = BATCH_SIZE) -> None`

Purpose:

- Configure model cache directories on the project SSD.
- Authenticate with Hugging Face when credentials are available.
- Create the origin-patch mapping.
- Iterate through the model registry.
- Extract and save embeddings.
- Record metadata for every model run.

Side effects:

- Writes `origin_patch_mapping.csv`.
- Writes embedding pickle files under `data/embeddings/`.
- Writes metadata under `results/phase1/metadata/`.
- Uses `results/phase1/feature_cache/` for patch-level feature reuse.

## Public Helper Functions

### `load_patch_dataframe(fold_csv_path)`

Location:

```text
scripts/src/phase1/extraction_func.py
```

Inputs:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `fold_csv_path` | path-like | CSV containing patch metadata. |

Returns:

- `pandas.DataFrame` loaded from the CSV.

Side effects:

- Logs row count and column names.

### `create_origin_patch_mapping(source_csv_path, patch_image_dir, output_csv_path)`

Location:

```text
scripts/src/phase1/extraction_func.py
```

Inputs:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `source_csv_path` | path-like | Patch metadata with `origin`, `patch`, and `diagnosis`. |
| `patch_image_dir` | path-like | Directory containing patch PNG files. |
| `output_csv_path` | path-like | Destination for the generated mapping CSV. |

Returns:

- `pandas.DataFrame` with `origin_id`, `class`, `patch_count`, `patch_ids`, and `image_paths`.

Validation behavior:

- Only existing patch image paths are included.
- Origins with no existing patch image paths are skipped.

Side effects:

- Writes the mapping CSV.
- Logs class distribution and per-origin patch-count summary.

### `extract_wsi_level_features(model_name, origin_patch_mapping, batch_size=32, device="mps", output_dir=DEFAULT_EMBEDDINGS_DIR)`

Location:

```text
scripts/src/phase1/extraction_func.py
```

Inputs:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `model_name` | string | Model key from `scripts/src/phase1/config.yaml`. |
| `origin_patch_mapping` | `pandas.DataFrame` | Output from `create_origin_patch_mapping()`. |
| `batch_size` | integer | Patch batch size for extraction. |
| `device` | string | `mps`, `cuda`, or `cpu`. |
| `output_dir` | path-like | Destination directory for embedding pickle files. |

Returns:

- String path to the saved embedding pickle file.

Output format:

```python
{
    origin_id: np.ndarray,  # shape: (patch_count_for_origin, model_output_dim)
}
```

Side effects:

- Loads one configured model through `FeatureExtractor`.
- Writes `embeddings_wsi_level_{model}_{timestamp}.pkl`.

## Feature Extraction Class

### `FeatureExtractor`

Location:

```text
scripts/src/phase1/feature_extractor.py
```

Responsibility:

- Load one configured model.
- Build model-specific preprocessing.
- Extract patch embeddings.
- Cache patch features using a preprocessing-aware fingerprint.

Important behavior:

- Preprocessing comes from the model registry.
- There is no universal ImageNet-normalization fallback.
- Cache keys include model identity, preprocessing settings, output dimension, extraction method, and normalization statistics.

## Shared Model Environment Functions

### `configure_external_model_caches(cache_root: Path) -> None`

Location:

```text
scripts/src/utils/model_environment.py
```

Purpose:

- Point Hugging Face, Transformers, and Torch model caches to a project-controlled cache root before model-loading imports happen.

### `authenticate_huggingface(env_path: Path | None = None) -> None`

Location:

```text
scripts/src/utils/model_environment.py
```

Purpose:

- Load Hugging Face credentials from `.env` or environment variables when available.
- Authenticate optional gated models without making Phase 1 code own token logic.

## Configuration Contract

Model behavior is declared in:

```text
scripts/src/phase1/config.yaml
```

Important fields:

| Field | Meaning |
| --- | --- |
| `model_id` | Source model identifier. |
| `source` | Model provider or loader family. |
| `output_dim` | Expected feature dimension. |
| `extract_method` | Feature pooling method. |
| `preprocessing` | Resize, crop, interpolation, mean, and standard deviation. |

## Run

```bash
uv run python scripts/phase1.py
```

See [Phase 1 Results](phase1-results.md) for the current artifact summary.

## Validation Checklist

- Mapping has 203 unique origins.
- Saved embeddings contain the same 203 origin keys.
- Total embedded patch arrays sum to 3,086 patches.
- The metadata tracker records each configured model run.
- Hugging Face gated models use accepted model terms and a valid token.
- Feature cache lives under `results/phase1/feature_cache/`.

**Last verified**: 29 June 2026.
