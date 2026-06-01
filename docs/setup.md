# Setup & Installation

Complete step-by-step guide to setting up the NDB-UFES Data Organizer on your local machine.

---

## System Requirements

- **Python**: 3.10-3.12 (3.12 recommended)
- **OS**: macOS (M1/M2/M3/M4), Linux, or Windows
- **Storage**: ~20 GB for full dataset (DVC S3 remote)
- **GPU/Accelerator**: 
  - Optional: NVIDIA CUDA 11.8+ (Linux) 
  - Optional: Apple Metal Performance (macOS M-series)
  - CPU mode supported but slower

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/ndb_ufes_data_organizer.git
cd ndb_ufes_data_organizer
```

---

## Step 2: Install uv

Install uv if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

uv creates and manages the project virtual environment in `.venv/`.

---

## Step 3: Install Dependencies

```bash
uv sync
```

**Key packages** (see `pyproject.toml` for full list):
- `torch>=2.0.0` — Deep learning framework
- `torchvision>=0.15.0` — Vision utilities
- `transformers>=4.30.0` — HuggingFace model hub
- `scikit-learn>=1.6.1` — Clustering + preprocessing
- `pandas>=2.2.3` — Data manipulation
- `numpy>=2.2.1` — Numerical computing
- `plotly>=5.13.0` — Interactive 3D visualizations
- `dvc>=3.58.0` — Data version control
- `dvc-s3>=3.2.0` — AWS S3 remote for DVC
- `timm==1.0.26` — PyTorch Image Models

**Installation time**: 5-10 minutes (depending on internet speed)

### Verify Installation

```bash
uv run python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
uv run python -c "import transformers; print(f'Transformers version: {transformers.__version__}')"
```

---

## Step 4: Data Setup with DVC

### Download Data

The dataset is version-controlled with **DVC** (Data Version Control) on AWS S3.

```bash
# Initialize DVC (if not already done)
uv run dvc remote list  # Should show 's3://dvc-ndb-ufes/data' as default

# Download all data (images, CSVs, metadata)
uv run dvc pull
```

**Expected download**:
- `data/ndb_ufes/origin_level/` — 238 WSI images (~5 GB)
- `data/ndb_ufes/patch_level/images/` — 3,768 patch images (~2 GB)
- `data/ndb_ufes/patch_level/csvs/` — Metadata CSVs (~1 MB)
- `data/ndb_ufes/link_level/` — 3,055 link images (~2 GB)

**Download time**: 10-20 minutes (depending on network)

### DVC Configuration

DVC remote is pre-configured in `data.dvc`:
```yaml
remote:
  s3:
    url: s3://dvc-ndb-ufes/data
```

To use custom AWS credentials, set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

---

## Step 5: Setup API Credentials (Optional but Recommended)

### HuggingFace Hub

Several models require authentication for optimal performance:

```bash
# Interactive login
uv run huggingface-cli login

# Or via environment variable
export HUGGINGFACE_TOKEN=your_token_here
```

Get your token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## Step 6: Verify Setup

### Quick Verification Script

```bash
uv run python -c "
import torch
import pandas as pd
from pathlib import Path
from src.models.model_loader import ModelLoader

# Check torch + device
print('PyTorch version:', torch.__version__)
print('Device available:', 'MPS' if torch.backends.mps.is_available() else 'CUDA' if torch.cuda.is_available() else 'CPU')

# Check data files
patch_csv = Path('data/ndb_ufes/patch_level/csvs/parcial_pndb_ufes.csv')
print(f'Parcial CSV exists: {patch_csv.exists()}')

# Check model registry
loader = ModelLoader(registry_path='scripts/src/phase1/config.yaml')
models = loader.list_available_models()
print(f'Model registry loaded: {len(models)} models available')
print(f'Models: {models[:3]}...')
"
```

**Expected output**:
```
PyTorch version: 2.x.x
Device available: MPS
Parcial CSV exists: True
Model registry loaded: 12 models available
Models: ['uni', 'virchow', 'ctranspath']...
```

### Directory Structure Check

```bash
# Verify key directories exist
ls -la data/ndb_ufes/patch_level/images/ | head -5
ls -la data/ndb_ufes/patch_level/csvs/
ls -la scripts/src/phase1/
```

**Expected**:
- `data/ndb_ufes/patch_level/images/` contains ~3,768 PNG files (p0001.png, p0002.png, ...)
- `data/ndb_ufes/patch_level/csvs/` contains `parcial_pndb_ufes.csv`
- `scripts/src/phase1/` contains `extraction_func.py`, `feature_extractor.py`, `metadata_tracker.py`, and `config.yaml`

---

## Step 7: Run Phase 1 (Optional - Full Test)

Test the entire pipeline with a small subset:

```bash
# Run Phase 1 (extracts embeddings + creates visualizations)
uv run python scripts/phase1.py
```

**Expected**:
- Creates `data/embeddings/embeddings_wsi_level_uni_*.pkl` (embeddings file)
- Creates `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` (mapping file)
- Writes run metadata under `results/phase1_metadata/`
- **Total runtime**: 2-5 minutes (M4 Mac with MPS)

**Output sample**:
```
------------------------------------------------------------------------
PHASE 1: FEATURE EXTRACTION AND VISUALIZATION PIPELINE
------------------------------------------------------------------------

FeatureExtractor Initialized
  Model: uni
  Description: UNI - Pathology Foundation Model (768D, ...)
  Input size: 224x224
  Output dim: 768
  Extract method: cls_token
  Device: mps
  Batch size: 32

Extracting embeddings: 100%|████| 3086/3086 [00:42<00:00, 73.14it/s]

Extraction Complete:
  Model: uni
  Origins: 203
  Total patches: 3086
  Avg patches/origin: 15.2
  Feature shape per origin: (n_patches, 768)
```

---

## Step 8: View Documentation Locally (GitHub Pages)

To view this documentation site locally with embedded visualizations:

```bash
uv sync --extra docs
```

### Refresh Visualization Files

```bash
uv run python scripts/copy_visualizations.py
```

Existing HTML visualizations are served from `docs/visualizations/`. If new visualization files are regenerated, this script copies them into the docs folder and normalizes filenames for embedding.

### Serve Locally

```bash
uv run mkdocs serve
```

Then open **http://localhost:8000** in your browser.

**Features**:
- Navigate all documentation pages
- View embedded 3D cluster visualizations
- Full-text search (Ctrl+K / Cmd+K)
- Mobile-responsive design
- Dark mode toggle

---

## Troubleshooting

### Issue: `torch` import fails

**Solution**: Reinstall PyTorch for your device:
```bash
# For Apple Silicon (M-series)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/nightly/cpu

# For NVIDIA CUDA 11.8
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Issue: DVC pull fails with S3 error

**Solution**: Check AWS credentials and DVC config:
```bash
aws sts get-caller-identity  # Verify AWS credentials
uv run dvc remote list  # Check remote configuration
uv run dvc pull -vv  # Verbose output for debugging
```

### Issue: HuggingFace model download is slow/fails

**Solution**: Set HF cache directory and retry:
```bash
export HF_HOME=/path/to/cache  # Use faster disk if available
uv run python scripts/phase1.py  # Retry with cache
```

### Issue: Out of memory (OOM) during extraction

**Solution**: Reduce batch size in `scripts/phase1.py`:
```python
BATCH_SIZE = 32  # Change to 16 or 8
```

### Issue: GPU/MPS not detected

**Solution**: Check device setup:
```python
# For MPS (Apple Metal)
import torch
print(torch.backends.mps.is_available())  # Should be True
print(torch.backends.mps.is_built())       # Should be True

# For CUDA
torch.cuda.is_available()  # Should be True
torch.cuda.get_device_name(0)  # Should show GPU name
```

---

## Next Steps

1. **Verify setup** with the verification script above
2. **Read [Pipeline Overview](pipeline.md)** to understand what each phase does
3. **Run Phase 1** to extract embeddings and see results
4. **Check [Phase 1: Results & Visualizations](phase1-results.md)** to interpret outputs
5. **Explore data structure** with [Data Organization & Dictionary](data-dictionary.md)

---

**Last updated**: April 2026
