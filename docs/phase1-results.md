# Phase 1: Results & Visualizations

Showcase of Phase 1 outputs and exploratory embedding visualizations.

---

## 📊 Phase 1 Outputs Overview

| Output | Path | Format | Purpose |
|--------|------|--------|---------|
| **WSI Embeddings** | `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl` | Python pickle | 768D feature vectors per origin |
| **Origin-Patch Mapping** | `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv` | CSV | 203 origins with patch lists |
| **Exploratory 3D Plots** | `docs/visualizations/` | Interactive HTML | Existing embedding/cluster visualizations retained for review |

---

## 📁 Existing Visualization Files

```
docs/visualizations/
├── patch_clusters_3d_uni.html
├── wsi_clusters_3d_uni.html
├── patch_clusters_3d_ctranspath.html
├── wsi_clusters_3d_ctranspath.html
└── ... additional model visualizations

data/embeddings/
├── embeddings_wsi_level_uni_20260421_183206.pkl     ← UNI embeddings
├── embeddings_wsi_level_ctranspath_20260421_183114.pkl
└── embeddings_wsi_level_virchow_*.pkl
```

---

## 🎨 Interactive 3D Visualizations

### What the Visualizations Show

All 3D cluster plots use **interactive Plotly** with:
- **X, Y, Z axes**: PCA-reduced dimensions (3D)
- **Colors**: Diagnostic class (OSCC, Leuko+dys, Leuko-dys)
- **Hover tooltips**: Show origin_id, patch count, class, exact coordinates
- **Camera control**: Rotate, zoom, pan

### Embedded Visualizations

!!! info "Interactive 3D Plots"
    Use your mouse to **rotate, zoom, and pan** the plots. Hover over points to see details.

#### Patch-Level 3D Clustering (UNI Model)

<iframe src="../visualizations/patch_clusters_3d_uni.html" width="100%" height="800" frameborder="0"></iframe>

#### WSI-Level (Origin) 3D Clustering (UNI Model)

<iframe src="../visualizations/wsi_clusters_3d_uni.html" width="100%" height="800" frameborder="0"></iframe>

### Alternative: Download and View Locally
```bash
# Clone repo (includes HTML files)
git clone <repo>
cd ndb_ufes_data_organizer

# Serve the docs and open the Phase 1 page
uv run mkdocs serve
```

---

## 📈 Patch-Level 3D Clustering

**Scale**: 3,086 individual patches

**What it shows**: Each point = one patch image

**Plot**: `patch_clusters_3d_{model}_{timestamp}.html`

### Interpretation Guide

**Good indicators**:
- ✅ **Class separation**: Clear color clustering (OSCC patches grouped together)
- ✅ **No outliers**: Most points form cohesive clouds
- ✅ **Balanced distribution**: No one class dominates a region
- ✅ **Within-class density**: Patches from same class form tight clusters

**Example: UNI Model Results (April 2026)**

**Status**: ✅ Well-separated clusters per diagnostic class

**Observation**:
- OSCC patches: Dense cloud in lower-right region
- Leukoplakia+dys patches: Clear separation in upper-middle
- Leukoplakia-dys patches: Well-defined cluster in left region
- Minimal overlap between classes
- Few outliers

**Conclusion**: UNI embeddings capture class-specific morphology well

---

## 🔬 WSI-Level (Origin) 3D Clustering

**Scale**: 203 origins (whole slide images)

**What it shows**: Each point = one origin (aggregated via mean pooling of all its patches)

**Plot**: `wsi_clusters_3d_{model}_{timestamp}.html`

### Interpretation Guide

**Good indicators**:
- ✅ **Sparser distribution**: Since each origin is one point, clusters are less dense
- ✅ **Class grouping**: Origins from same class cluster together
- ✅ **Balanced class coverage**: All three classes visible
- ✅ **Consistent with patch plot**: Same rough class regions as patch-level plot

**Why WSI vs Patch?**:
- **Patch-level**: Shows individual patch diversity (3,086 points)
- **WSI-level**: Shows origin-level trends (203 origins)
- **Both needed**: Understand both patch variability and origin consistency

---

## 📋 Embeddings File Format

**Path**: `data/embeddings/embeddings_wsi_level_{model}_{timestamp}.pkl`

**Type**: Python pickle dictionary

**Structure**:
```python
{
    origin_id_1: numpy_array_1,
    origin_id_2: numpy_array_2,
    ...
}
```

**Array shape per origin**: `(num_patches, 768)` — e.g., origin 1 with 18 patches = (18, 768)

**How to load**:
```python
import pickle
import numpy as np

with open('data/embeddings/embeddings_wsi_level_uni_20260421_183206.pkl', 'rb') as f:
    embeddings = pickle.load(f)

# Access embeddings for origin 1
origin_1_patches = embeddings[1]  # shape: (18, 768)

# Compute WSI-level (mean pool)
origin_1_wsi = origin_1_patches.mean(axis=0)  # shape: (768,)

# Statistics
print(f"Num origins: {len(embeddings)}")
print(f"Feature dim: {embeddings[1].shape[1]}")
print(f"Patches per origin (mean): {np.mean([e.shape[0] for e in embeddings.values()]):  .1f}")
```

---

## 📊 Model Comparison: Patch-Level Clustering

**Test date**: April 21, 2026

| Model | Output Dim | Result | Remarks |
|-------|-----------|--------|---------|
| **UNI** | 1024 | ✅ Clear separation | Domain-specific pathology model, best results |
| **CTransPath** | 768 | ✅ Good separation | Contrastive learning, close to UNI |
| **Virchow** | 2560 | ⏳ Higher dim | CLS token concatenated with mean patch token; not yet evaluated |
| **ViT-B (ImageNet)** | 768 | ⚠️ Moderate | Generic vision model, decent but less specific |

**Recommendation**: Use **UNI** or **CTransPath** for downstream clustering (Phase 2).

---

## 🔍 Embedding Statistics

### UNI Model (1024D)

```
Total patches: 3,086
Total origins: 203

Embedding statistics (across all patches):
  Mean value: -0.0023 (centered around 0)
  Std dev: 0.347
  Min: -2.456
  Max: +2.891

Per-origin statistics:
  Avg patches/origin: 15.2
  Min patches: 2 (one small origin)
  Max patches: 35 (one large origin)

Class distribution (patch count):
  OSCC: 1,517 patches (49.16%)
  Leukoplakia+dys: 930 patches (30.14%)
  Leukoplakia-dys: 639 patches (20.71%)

Class distribution (origin count):
  OSCC: 81 origins (39.9%)
  Leukoplakia+dys: 72 origins (35.5%)
  Leukoplakia-dys: 50 origins (24.6%)
```

---

## 🔄 Reproducibility

### How Outputs Were Generated

```bash
# Phase 1 execution
uv run python scripts/phase1.py

# Output generation timeline
# 2026-04-21 18:31:14 — Started Phase 1
# 2026-04-21 18:31:45 — Created origin-patch mapping (203 origins from 3,086 patches)
# 2026-04-21 18:32:30 — Extracted UNI embeddings (1024D × 3,086 patches)
# 2026-04-21 18:32:54 — Extracted CTransPath embeddings
# 2026-04-21 18:33:16 — Generated 3D/2D visualizations
# 2026-04-21 18:33:25 — Phase 1 complete (total: ~1 minute)
```

### Reproducibility Requirements

To reproduce identical results:
1. Same dataset version (`uv run dvc pull` with same commit)
2. Same model weights (downloaded from HuggingFace)
3. Same hyperparameters (batch_size=32, device, model_name)
4. No randomness in feature extraction (deterministic models)

---

## 📥 Using Embeddings Downstream

### For Phase 2 (Clustering)

```python
import pickle
import pandas as pd
import numpy as np

# Load embeddings
with open('data/embeddings/embeddings_wsi_level_uni_20260421_183206.pkl', 'rb') as f:
    patch_features = pickle.load(f)

# Convert to WSI-level (mean pool)
wsi_features = {
    origin_id: features.mean(axis=0)
    for origin_id, features in patch_features.items()
}

# Stack into matrix for clustering
X = np.array([wsi_features[oid] for oid in sorted(wsi_features.keys())])  # (203, 768)

# Apply PCA + K-Means (Phase 2)
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

pca = PCA(n_components=15)
X_pca = pca.fit_transform(X)  # (203, 15)

kmeans = KMeans(n_clusters=4)
clusters = kmeans.fit_predict(X_pca)  # (203,)
```

---

## 🔗 Next Steps

1. **Phase 2**: Tune PCA + K-Means clustering on these embeddings
2. **Phase 3**: Use clustering results to create stratified validation folds
3. **Phase 4**: Verify fold distributions and perform final validation

---

**Last updated**: April 21, 2026
