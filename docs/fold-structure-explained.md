# Understanding Fold Structure

This guide explains how folds are organized and why this structure prevents data leakage.

---

## Hierarchy: Origins and Patches

The dataset has two levels of data organization:

### Origin Level

An **origin** is a whole-slide or tissue image (WSI) from a single patient specimen. The dataset contains:
- 237 origins in total from source metadata
- 203 origins in the matched fold-design subset (origins with corresponding patch images)

Each origin has:
- One diagnostic label (e.g., OSCC, Leukoplakia with dysplasia)
- Demographic and risk factor metadata (gender, age group, etc.)
- Multiple patch crops extracted from its image

### Patch Level

A **patch** is a smaller image crop extracted from an origin. The dataset contains:
- 3,086 patches in the matched fold-design subset
- Patches are organized hierarchically under their parent origin
- Each patch inherits its origin's diagnosis and demographics

**Key relationship:**

```
Origin 0 (OSCC, Female, 55 years) ← 1 diagnostic label per origin
  ├── Patch 0_0
  ├── Patch 0_1
  ├── Patch 0_2
  └── ... (15 patches total from this origin)

Origin 1 (Leukoplakia with dysplasia, Male, 62 years)
  ├── Patch 1_0
  ├── Patch 1_1
  └── ... (18 patches total from this origin)

... and so on for all 203 origins
```

---

## The Core Invariant: No Leakage

Folds are structured to satisfy this critical property:

**One origin → One fold**

All patches from the same origin must be assigned to the same fold. This prevents **data leakage** where the model unknowingly trains and evaluates on different patches from the same specimen.

**Example:**

```
Origin 5 has 20 patches and is assigned to fold 2.
Patches 5_0, 5_1, ..., 5_19 all receive fold = 2.
```

During model training:
- Training folds: 0, 1, 2, 3, 4 (for k-fold cross-validation)
- Validation fold: 5
- All 20 patches from Origin 5 go to the validation fold
- No patch from Origin 5 appears in any training fold

This invariant ensures that validation performance reflects generalization to new specimens, not memorization of the same specimen seen in different patches.

---

## Why Six Folds?

Six folds are chosen to satisfy three constraints:

1. **Minimum class representation:** With six folds and 203 origins, an average fold contains ~34 origins. The smallest diagnostic class (Leukoplakia without dysplasia) has 50 origins, allowing reliable within-class stratification across folds.

2. **Morphological cluster balance:** With 6 clusters and 6 folds, there is potential for each cluster to be represented in each fold without excessive fragmentation.

3. **Standard validation practice:** Six-fold cross-validation is common in medical imaging and provides reasonable statistical power while managing computational cost.

---

## Fold Stratification

Folds are not randomly assigned. Instead, origins are distributed across folds to balance specific variables, ensuring each fold is representative of the full dataset.

### Stratification Variables

By default, folds are stratified by:

1. **Diagnosis** (required): OSCC, Leukoplakia with dysplasia, Leukoplakia without dysplasia
2. **Morphology cluster** (required): Output from Phase 2 K-Means clustering (e.g., 4 clusters)
3. **Gender** (required): Male, Female (missing ~0%)
4. **Age group** (required): 0 (<40), 1 (40-60), 2 (>60)

These four variables create **stratification subgroups** (strata). Each unique combination defines a stratum:

```
Stratum 1: OSCC, Cluster_2, Male, age_group_2
Stratum 2: OSCC, Cluster_2, Female, age_group_1
Stratum 3: OSCC, Cluster_3, Male, age_group_2
... (many more combinations)
```

### Why Stratify?

Stratification ensures:
- Each fold has roughly equal numbers of OSCC vs. Leukoplakia cases
- Morphological diversity is balanced across folds
- Gender representation is balanced
- Age group distribution is balanced

Without stratification, random splitting might accidentally create a fold with 70% male origins, making that fold unrepresentative.

---

## The Fold Assignment Algorithm

Phase 3 uses **greedy Longest Processing Time (LPT) bin-packing** to achieve balance:

### Step-by-Step

**Input:** 203 origins, each with a `patch_count` and `stratification_key`

**Process:**

1. Group origins by their stratification key
2. Within each stratum, sort origins by patch count (largest first)
3. Initialize six empty folds with patch-count totals of 0
4. For each origin (in sorted order):
   - Assign to the fold with the smallest current total patch count
   - Update that fold's total

### Example

```
Stratum "OSCC|Cluster_2|Male|2": 12 origins with patch counts

Origins sorted by patch count (descends): [50, 48, 45, 44, 40, 38, 35, 33, 30, 28, 25, 20]

Fold totals (initially): [0, 0, 0, 0, 0, 0]

Assign origin with 50 patches:
  → Fold with min total: Fold 0
  → Fold 0 total: 0 + 50 = 50
  Fold totals: [50, 0, 0, 0, 0, 0]

Assign origin with 48 patches:
  → Fold with min total: Fold 1
  → Fold 1 total: 0 + 48 = 48
  Fold totals: [50, 48, 0, 0, 0, 0]

Continue... until all origins assigned

Final fold totals: [50+40+30, 48+44+28, 45+35+25, 43+33+20, ...]
                ≈ [120, 120, 105, 96, ...]  (roughly balanced)
```

**Result:** Folds have similar total patch counts, supporting balanced training and validation sets.

---

## Fold Balance Metrics

After fold assignment, Phase 3 reports balance statistics:

### Patch Count Balance

```
Fold 0: 514 patches
Fold 1: 513 patches
Fold 2: 515 patches
Fold 3: 512 patches
Fold 4: 514 patches
Fold 5: 518 patches

Mean: 514.3
Std dev: 2.0
Min/Max: 512 / 518
Balance ratio: 518 / 512 = 1.01
```

**Interpretation:**
- **Balance ratio close to 1.0** (e.g., 1.01) indicates excellent fold balance
- **Std dev < 5** indicates minimal variation
- Folds with 512-518 patches are nearly equal-sized

### Diagnosis Distribution

Check that each diagnostic class is represented in each fold:

```
Fold   OSCC  Leuk_dys  Leuk_no_dys
  0     253      196        65
  1     251      197        65
  2     258      191        66
  3     248      201        63
  4     253      195        66
  5     254      150        114
```

Ideally, each row is proportional to the overall diagnosis distribution (48% OSCC, 30% Leuk_dys, 21% Leuk_no_dys).

### Class-Specific Balance

Report balance per diagnostic class:

```
OSCC:
  Folds: [253, 251, 258, 248, 253, 254]
  Range: 248-258 patches
  Ratio: 258/248 = 1.04

Leuk_dys:
  Folds: [196, 197, 191, 201, 195, 150]
  Range: 150-201 patches
  Ratio: 201/150 = 1.34  ← Higher variance; possible imbalance

Leuk_no_dys:
  Folds: [65, 65, 66, 63, 66, 114]
  Range: 63-114 patches
  Ratio: 114/63 = 1.81  ← Larger imbalance
```

If a class shows high variance across folds (ratio > 1.5), consider:
- Reviewing Phase 2 morphology clustering (does it stratify this class well?)
- Adjusting stratification variables in Phase 3
- Accepting the imbalance if it reflects genuine dataset properties

---

## Phases 2 and 3: How They Connect

**Phase 2** produces:
- Morphology clusters (via PCA + K-Means) that capture visual/structural patterns
- Parameters saved to `clustering_params.json`

**Phase 3** uses Phase 2 output:
- Reads selected embeddings and parameters from `clustering_params.json`
- Applies Phase 2's PCA + K-Means to assign each origin to a morphology cluster
- Uses that cluster as one of the stratification variables

**Why this connection matters:**
- Morphology clusters represent visual diversity in the dataset
- By stratifying folds to include all clusters, we ensure each fold contains visual diversity
- This supports robust model training (each fold sees the full range of morphological variation)

---

## Leakage Prevention Summary

The fold structure prevents leakage by enforcing:

1. **Origin-level locking:** All patches from one origin stay together in one fold
2. **No downstream selection:** Folds are chosen before model training, not based on validation performance
3. **Stratification at creation time:** Fold assignments use only Phase 1-2 outputs (embeddings, clusters), not downstream model predictions
4. **Frozen embeddings:** Phase 2 uses frozen pretrained models, not fine-tuned on this dataset's labels

Users of these folds should:
- Use one fold for validation and five for training (standard k-fold)
- Never select folds based on which produces the best validation performance
- Never fine-tune embeddings on the full dataset including validation/test labels
- Treat validation/test results as estimates of generalization to new specimens, not new patches of same specimens

---

## Next Steps

Use the generated folds for model training and evaluation:

**Files to use:**

- `results/phase3_fold_creation/fold_assignments_patch_level.csv` — For patch-level model training
- `results/phase3_fold_creation/fold_assignments_origin.csv` — For origin-level analysis or per-origin metrics

**Verification:**

Run the invariant checks in [Reproducibility](reproducibility.md#phase-3-fold-creation) to confirm no data leakage.
