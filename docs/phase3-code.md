# Phase 3: Fold Creation

Implementation guide for stratified cross-validation fold assignment.

---

## Overview

Phase 3 creates six-fold assignments where all patches from an origin stay in the same fold, stratified by diagnosis, morphological cluster, gender, and age group. The algorithm ensures leakage-safe partitions suitable for training, validation, and test splits.

**Input:**
- Phase 2 parameters: `clustering_params.json`
- Phase 2 selected embeddings: path specified in `clustering_params.json`
- Patch metadata: `data/ndb_ufes/patch/parcial_pndb_ufes.csv`
- Origin mapping: `data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv`

**Output:**
- Origin-level folds: `results/phase3_fold_creation/fold_assignments_origin.csv`
- Patch-level folds: `results/phase3_fold_creation/fold_assignments_patch_level.csv`
- Stratification audit: `results/phase3_fold_creation/stratification_variables_audit.csv`

---

## Architecture

Phase 3 is structured as a top-level runner with one main implementation module:

```
scripts/phase3.py                           ← Main execution entry point
├── calls: phase3_fold_creation.main()

scripts/src/phase3/
├── phase3_fold_creation.py                 ← Core fold creation
│   ├── load_patch_metadata()               ← Load patch CSV
│   ├── aggregate_to_origin_level()         ← Compute origin stats
│   ├── apply_pca_kmeans()                  ← Apply Phase 2 params
│   ├── create_stratification_keys()        ← Build fold strata
│   ├── greedy_lpt_fold_assignment()        ← Assign folds
│   ├── broadcast_to_patch_level_and_save() ← Expand to patches
│   └── validate_folds()                    ← Check invariants
└── phase3_visualize_clusters.py            ← Optional visualizations

scripts/src/utils/logger.py                 ← Logging
```

All functions are importable with no side effects. Only `scripts/phase3.py` executes work.

---

## Algorithm

### Step 1: Load and Prepare Data

Phase 3 loads patch-level metadata and aggregates statistics to origin level:

```python
patch_df = load_patch_metadata("data/ndb_ufes/patch/parcial_pndb_ufes.csv")
origin_df = aggregate_to_origin_level(patch_df)
```

For each origin, compute:
- `origin_diagnosis`: most common diagnosis across patches
- `patch_count`: number of patches
- `gender`, `skin_color`, `age_group`: modal value across patches

### Step 2: Apply PCA and K-Means

Load the Phase 2 selected parameters and embeddings:

```python
params = load_params("clustering_params.json")
embeddings_file = params["embeddings_file"]

embeddings_dict = load_embeddings(embeddings_file)
embeddings = aggregate_embeddings_to_wsi(embeddings_dict, origin_ids)
```

Apply PCA and K-Means with Phase 2 parameters:

```python
clusters = apply_pca_kmeans(embeddings, params)
origin_df["morph_cluster"] = clusters
```

Result: each origin is assigned a morphological cluster (0, 1, 2, 3, etc.).

### Step 3: Create Stratification Keys

Audit which variables should enter fold construction:

```python
audit_df = evaluate_stratification_variables(origin_df)
audit_df.to_csv("results/phase3_fold_creation/stratification_variables_audit.csv")
```

The audit gate checks each variable for:
- **Missingness:** If missing rate exceeds 25%, exclude
- **Category support:** If any non-missing category has fewer than 6 origins, exclude
- **Requirement:** Required variables (`origin_diagnosis`, `morph_cluster`, `gender`, `age_group`) are always included

Create a stratification key by concatenating included variables:

```python
stratification_key = "origin_diagnosis=OSCC|morph_cluster=c2|gender=M|age_group=2"
```

Each unique key defines a stratum (subgroup). Origins in the same stratum will be distributed across folds as evenly as possible.

### Step 4: Greedy LPT Bin-Packing

Assign each origin to a fold using the Longest Processing Time (LPT) greedy algorithm:

**Algorithm:**

For each unique stratification key:
1. Collect all origins with that key
2. Sort origins by `patch_count` (descending)
3. For each origin (largest-first):
   - Assign to the fold with the current minimum total patch count
   - Update that fold's total patch count

**Rationale:** Processing largest origins first ensures large clusters are distributed across folds, producing balanced fold sizes.

**Example:**

```
Stratum "OSCC|c2|M|2": 20 origins with patch counts [50, 48, 45, 40, ...]

Fold sizes (initially): [0, 0, 0, 0, 0, 0]

Assign origin with 50 patches to fold 0: [50, 0, 0, 0, 0, 0]
Assign origin with 48 patches to fold 1: [50, 48, 0, 0, 0, 0]
Assign origin with 45 patches to fold 2: [50, 48, 45, 0, 0, 0]
...continue until all origins assigned

Final fold sizes: [514, 513, 515, 512, 514, 518]  (well balanced)
```

### Step 5: Broadcast to Patch Level

Create a mapping from origin_id to fold:

```python
origin_fold_map = dict(zip(origin_df["origin_id"], origin_df["fold"]))
```

Map each patch to its origin's fold:

```python
patch_df["fold"] = patch_df["origin_id"].map(origin_fold_map)
```

Save origin-level and patch-level assignments:

```
results/phase3_fold_creation/fold_assignments_origin.csv  (203 rows)
results/phase3_fold_creation/fold_assignments_patch_level.csv  (3,086 rows)
```

### Step 6: Validate

Check fold invariants:

- All origins assigned to exactly one fold
- All patches inherit their origin's fold
- No origin spans multiple folds (zero data leakage)
- Fold sizes are balanced (within acceptable range)

---

## API Reference

### `main()`

**Purpose:** Execute the complete Phase 3 pipeline.

**Parameters:** None (uses configuration constants in module)

**Returns:** None (writes files to disk)

**Constants:**

```python
N_FOLDS = 6
RANDOM_STATE = 42
MAX_MISSING_RATE_FOR_STRATIFICATION = 0.25

REQUIRED_STRATIFICATION_COLUMNS = (
    "origin_diagnosis",
    "morph_cluster",
    "gender",
    "age_group",
)

OPTIONAL_STRATIFICATION_COLUMNS = ()  # Add only after audit gate

DESCRIPTIVE_METADATA_COLUMNS = (
    "gender", "skin_color", "age_group", "tobacco_use",
    "alcohol_consumption", "sun_exposure", "localization", "larger_size",
)
```

**Example:**

```python
from src.phase3.phase3_fold_creation import main

main()  # Runs full pipeline
```

### `apply_pca_kmeans(embeddings, params)`

**Purpose:** Apply PCA and K-Means clustering to embeddings.

**Parameters:**
- `embeddings` (np.ndarray): Shape (n_origins, embedding_dim)
- `params` (dict): Keys `pca_components`, `kmeans_clusters`

**Returns:**
- Cluster assignments (np.ndarray): Shape (n_origins,), values 0 to K-1

### `greedy_lpt_fold_assignment(origin_df, n_folds=6)`

**Purpose:** Assign origins to folds using LPT bin-packing within strata.

**Parameters:**
- `origin_df` (DataFrame): Must have `patch_count` and `stratification_key` columns
- `n_folds` (int): Number of folds

**Returns:**
- origin_df with new `fold` column

---

## Stratification Variable Audit

The audit file `stratification_variables_audit.csv` documents which variables enter fold construction:

| Column | Description |
| --- | --- |
| `column` | Variable name |
| `role` | `required`, `optional`, `descriptive`, or `missing_from_data` |
| `status` | Inclusion decision: `included_required`, `included_optional`, `excluded_high_missingness`, `excluded_low_category_support`, `excluded_descriptive_only` |
| `missing_count` | Null/`Not informed` count |
| `missing_rate` | Fraction missing |
| `n_categories` | Non-missing category count |
| `min_category_count` | Smallest category size |
| `reason` | Human-readable explanation |

**Interpretation:** By default, `origin_diagnosis`, `morph_cluster`, `gender`, and `age_group` should have status `included_required`. All other demographic/clinical fields should have status `excluded_descriptive_only` (retained in output CSVs but not used for fold construction).

---

## Output Files

### Origin-Level Folds

Path: `results/phase3_fold_creation/fold_assignments_origin.csv`

Rows: 203 (one per origin)

Columns:
- `origin_id`: Origin identifier
- `origin_diagnosis`: Diagnostic class used for stratification
- `patch_diagnoses`: Unique diagnoses in patches from this origin
- `gender`, `skin_color`, `age_group`: Demographics
- `morph_cluster`: Morphology cluster from Phase 2
- `patch_count`: Number of patches in matched subset
- `stratification_key`: Concatenated stratification variables
- `fold`: Fold assignment (0-5)

**Use this file when you need origin-level statistics or want to audit stratification.**

### Patch-Level Folds

Path: `results/phase3_fold_creation/fold_assignments_patch_level.csv`

Rows: 3,086 (one per patch)

Columns:
- `origin_id`: Parent origin
- `patch`: Patch identifier
- `diagnosis`: Diagnostic class
- `gender`, `skin_color`, `age_group`: Demographics
- `fold`: Fold assignment (inherited from origin)

**Use this file when training models on patch-level data.**

---

## Running Phase 3

```bash
cd /Volumes/ssd/thesis_organization/ndb_ufes_data_organizer
uv run python scripts/phase3.py
```

Phase 3 reads the selected parameters from Phase 2 output (`clustering_params.json`) and the embedding file path it specifies, then creates folds and writes outputs under `results/phase3_fold_creation/`.

Verify outputs:
- Check fold balance (similar patch counts across folds)
- Review stratification audit (required variables included, descriptive excluded)
- Confirm no origin spans multiple folds
