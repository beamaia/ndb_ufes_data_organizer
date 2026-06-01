# Phase 1: Feature Extraction

Comprehensive guide to Phase 1 implementation, including complete API documentation, code walkthrough, and execution instructions.

---

## 📖 Overview

**Phase 1 Goal**: Extract semantic embeddings from histopathology patch images and create a mapping of patches to their origins (WSIs).

**Input**:
- 3,086 histopathology patch images (512×512 PNG)
- Patch-to-origin mapping (from `parcial_pndb_ufes.csv`)

**Output**:
- **Embeddings**: `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl` — Dictionary of 768D feature vectors
- **Mapping CSV**: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` — 203 origins with patch lists

**Status**: implemented, but final rerun/audit is still WIP.

---

## 🏗️ Architecture

Phase 1 is organized around mapping and embedding extraction:

```
scripts/phase1.py                          ← Main execution script
├── calls: create_origin_patch_mapping()
└── calls: extract_wsi_level_features()

scripts/src/phase1/
├── extraction_func.py                     ← Functions for mapping & extraction
│   ├── create_origin_patch_mapping()      ← Create origin→patch mapping
│   └── extract_wsi_level_features()       ← Extract embeddings
├── feature_extractor.py                   ← FeatureExtractor class
│   └── class FeatureExtractor              ← Main extraction worker class
└── config.yaml                            ← Model registry (12+ models)

scripts/src/models/
├── model_loader.py                        ← ModelLoader class
└── model_wrappers.py                      ← Model wrapper classes

scripts/src/utils/
└── logger.py                              ← Logging configuration
```

---

## 🔧 Complete API Reference

### 1. FeatureExtractor Class

**Location**: `scripts/src/phase1/feature_extractor.py`

Main class responsible for loading models and extracting embeddings from patch images.

#### `__init__(model_name, device='mps', batch_size=32, registry_path=None)`

Initialize a feature extractor for a specific model.

**Parameters**:
- `model_name` (str): Name of model from registry (e.g., `'uni'`, `'vit_base_patch16_224'`, `'virchow'`)
- `device` (str): Compute device — `'mps'` (Apple Metal), `'cuda'` (NVIDIA), or `'cpu'` (default: `'mps'`)
- `batch_size` (int): Number of images to process at once (default: `32`)
- `registry_path` (str): Path to model registry YAML (default: None → uses built-in path)

**Example**:
```python
from src.phase1.feature_extractor import FeatureExtractor

# Initialize for UNI model on Apple Metal
extractor = FeatureExtractor(
    model_name='uni',
    device='mps',
    batch_size=32
)
```

---

#### `extract_batch(image_tensors)`

Extract embeddings from a batch of preprocessed image tensors.

**Parameters**:
- `image_tensors` (torch.Tensor): Batch of images with shape `(B, 3, H, W)` where B=batch size

**Returns**:
- `embeddings` (np.ndarray): Shape `(B, output_dim)` where output_dim is 768 for ViT-B/UNI/CTransPath or 1024 for Virchow

**Example**:
```python
import torch

batch = torch.randn(32, 3, 224, 224)  # Random batch of 32 images
embeddings = extractor.extract_batch(batch)
print(embeddings.shape)  # (32, 768)
```

---

#### `extract_from_paths(patch_paths, origin_ids)`

Extract embeddings from image files on disk.

**Parameters**:
- `patch_paths` (list[str]): List of absolute paths to image files
- `origin_ids` (list[int]): Corresponding origin ID for each patch (same length as patch_paths)

**Returns**:
- `patch_features_dict` (dict): Dictionary with structure `{origin_id: np.ndarray}`
  - Keys: origin_id (int)
  - Values: (n_patches, output_dim) feature array for that origin

**Example**:
```python
patch_paths = [
    '/path/to/p0001.png',
    '/path/to/p0002.png',
    '/path/to/p0003.png',
]
origin_ids = [1, 1, 2]  # First two patches from origin 1, third from origin 2

features_dict = extractor.extract_from_paths(patch_paths, origin_ids)
# features_dict[1] = array of shape (2, 768) — two patches from origin 1
# features_dict[2] = array of shape (1, 768) — one patch from origin 2
```

---

### 2. extraction_func Module

**Location**: `scripts/src/phase1/extraction_func.py`

High-level functions for the complete extraction pipeline.

#### `create_origin_patch_mapping(source_csv_path, patch_image_dir, output_csv_path)`

Create a mapping CSV linking each origin (WSI) to its patches and files.

**Parameters**:
- `source_csv_path` (str): Path to source CSV with patch data (e.g., `parcial_pndb_ufes.csv`)
- `patch_image_dir` (str): Path to directory containing patch PNG images
- `output_csv_path` (str): Where to save the output mapping CSV

**Returns**:
- `mapping_df` (pd.DataFrame): DataFrame with columns:
  - `origin_id` (int): Origin identifier
  - `class` (str): Diagnostic class (OSCC, Leuko_dys, Leuko_no_dys)
  - `patch_count` (int): Number of patches for this origin
  - `patch_ids` (str): Comma-separated patch IDs
  - `image_paths` (str): Pipe-separated absolute paths to patch images

**Example**:
```python
from src.phase1.extraction_func import create_origin_patch_mapping

mapping_df = create_origin_patch_mapping(
    source_csv_path='data/ndb_ufes/patch/parcial_pndb_ufes.csv',
    patch_image_dir='data/ndb_ufes/patch_level/images',
    output_csv_path='data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv'
)
print(mapping_df.head())
print(f"Created mapping for {len(mapping_df)} origins")
```

---

#### `extract_wsi_level_features(model_name, mapping_df, output_pkl_path, batch_size=32, device='mps')`

Main extraction function: load patches → extract embeddings → save to pickle.

**Parameters**:
- `model_name` (str): Model from registry (e.g., `'uni'`, `'vit_base_patch16_224'`)
- `mapping_df` (pd.DataFrame): Origin-patch mapping from `create_origin_patch_mapping()` output
- `output_pkl_path` (str): Where to save embeddings pickle file
- `batch_size` (int): Batch size for extraction (default: 32)
- `device` (str): Device to use (default: 'mps')

**Returns**:
- `patch_features_dict` (dict): Same as FeatureExtractor.extract_from_paths() output

**Example**:
```python
from src.phase1.extraction_func import (
    create_origin_patch_mapping,
    extract_wsi_level_features
)

# Step 1: Create mapping
mapping_df = create_origin_patch_mapping(...)

# Step 2: Extract embeddings
features_dict = extract_wsi_level_features(
    model_name='uni',
    mapping_df=mapping_df,
    output_pkl_path='data/embeddings/embeddings_wsi_level_uni_20260421_120000.pkl',
    batch_size=32,
    device='mps'
)

# Access embeddings
origin_1_embeddings = features_dict[1]  # Shape: (18, 768)
```

---

### 3. Model Registry (config.yaml)

**Location**: `scripts/src/phase1/config.yaml`

Defines all available models for feature extraction.

**Available models**:

| Model | Output Dim | Category | Notes |
|-------|-----------|----------|-------|
| **uni** | 768 | Histopathology | UNI foundation model, 100M+ patches |
| **virchow** | 1024 | Histopathology | Clinical pathology, 2B+ patches |
| **ctranspath** | 768 | Histopathology | Swin Transformer + contrastive learning |
| **vit_base_patch16_224** | 768 | ImageNet | Standard ViT-B |
| **vit_small_patch16_224** | 384 | ImageNet | Standard ViT-S |

---

## 🚀 Execution

### Running Phase 1

#### Full Pipeline

```bash
# Run entire Phase 1 (creates mapping + extracts all models + visualizes)
uv run python scripts/phase1.py
```

**Expected output**:
```
--------
PHASE 1: FEATURE EXTRACTION AND VISUALIZATION PIPELINE
--------

Run timestamp: 20260421_120000

---
STEP 1: Creating origin-patch mapping (one-time)
---

Loaded 3086 patches from data/ndb_ufes/patch/parcial_pndb_ufes.csv
Created mapping for 203 origins -> data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv
Class distribution:
OSCC                           81
Leuko_dys                      72
Leuko_no_dys                   50

[Output continues for each model...]
```

**Runtime**: ~2-3 minutes per model (M4 Mac with Metal)

---

#### Manual Extraction (Single Model)

```python
from pathlib import Path
from src.phase1.extraction_func import (
    create_origin_patch_mapping,
    extract_wsi_level_features
)

PROJECT_ROOT = Path('.')

# Step 1: Create mapping
mapping_df = create_origin_patch_mapping(
    source_csv_path=str(PROJECT_ROOT / 'data/ndb_ufes/patch/parcial_pndb_ufes.csv'),
    patch_image_dir=str(PROJECT_ROOT / 'data/ndb_ufes/patch_level/images'),
    output_csv_path=str(PROJECT_ROOT / 'data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv')
)

# Step 2: Extract embeddings
features_dict = extract_wsi_level_features(
    model_name='uni',
    mapping_df=mapping_df,
    output_pkl_path=str(PROJECT_ROOT / 'data/embeddings/embeddings_wsi_level_uni.pkl'),
    batch_size=32,
    device='mps'
)

# Step 3: Use embeddings
import pickle
with open(PROJECT_ROOT / 'data/embeddings/embeddings_wsi_level_uni.pkl', 'rb') as f:
    embeddings = pickle.load(f)

print(f"Loaded embeddings for {len(embeddings)} origins")
print(f"Origin 1 shape: {embeddings[1].shape}")  # e.g., (18, 768)
```

---

## 📊 Configuration

### Device Selection

```python
# Option 1: Apple Metal Performance Shaders (fastest on M-series Mac)
extractor = FeatureExtractor(model_name='uni', device='mps')

# Option 2: NVIDIA CUDA (fastest on Linux/Windows with NVIDIA GPU)
extractor = FeatureExtractor(model_name='uni', device='cuda')

# Option 3: CPU (works everywhere, slowest)
extractor = FeatureExtractor(model_name='uni', device='cpu')
```

**Performance** (approximate, for UNI model):
- MPS (Apple M4): ~70 patches/second
- CUDA (RTX 3090): ~200 patches/second
- CPU: ~10 patches/second

---

### Batch Size

Batch size trades off memory usage and speed:

**Recommendations**:
- MPS (Apple Metal): batch_size=32 (1-2 GB)
- CUDA (RTX 3090): batch_size=64 (6-8 GB)
- CPU: batch_size=8 (500 MB)

If you get **OOM (Out of Memory)** errors, reduce batch_size in `scripts/phase1.py`:
```python
BATCH_SIZE = 16  # Change from 32
```

---

## ✅ Checklist for Phase 1

- [ ] Data downloaded (`uv run dvc pull`)
- [ ] Model registry loaded (`scripts/src/phase1/config.yaml` exists)
- [ ] Origin-patch mapping created
- [ ] Embeddings extracted
- [ ] Visualizations created
- [ ] All 203 origins have embedding features
- [ ] All 3,086 patches grouped by origin

---

## 🐛 Troubleshooting

### Issue: Model download fails (HuggingFace)

```
HFValidationError: Token is invalid
```

**Solution**: Authenticate with HuggingFace:
```bash
uv run huggingface-cli login
```

---

### Issue: Out of Memory (OOM)

```
RuntimeError: CUDA out of memory
```

**Solution**: Reduce batch size in Phase 1 config:
```python
# scripts/phase1.py
BATCH_SIZE = 8  # Reduce from 32
```

---

### Issue: Missing patches

```
WARNING: Failed to load /path/to/p0999.png: FileNotFoundError
```

**Solution**: Ensure all patch images downloaded:
```bash
uv run dvc pull data/ndb_ufes/patch_level/images/
ls data/ndb_ufes/patch_level/images/ | wc -l  # Should be ~3768
```

---

## 📚 References

- **Vision Transformers**: [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929)
- **UNI Model**: [Towards a general-purpose foundation model for computational pathology](https://www.nature.com/)
- **Virchow Model**: [A foundation model for clinical-grade computational pathology](https://www.nature.com/)

---

**Last updated**: April 2026
