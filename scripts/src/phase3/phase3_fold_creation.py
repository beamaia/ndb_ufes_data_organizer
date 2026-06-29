#!/usr/bin/env python3
"""
Phase 3: Stratified 6-Fold Creation with Missingness-Aware Stratification
- Origin-level diagnosis: Clinical diagnosis of the WSI
- Morphological clusters: From Phase 2 optimal parameters
- Gender and age group: default fold-construction variables
- Other demographic/clinical variables: retained as descriptive metadata unless
  explicitly promoted and accepted by the audit gate
- Constraint: All patches from same origin must be in same fold (no data leakage)
"""

import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import logging

# ---------------------------------------------------------------------------=
# CONFIGURATION
# ---------------------------------------------------------------------------=
EMBEDDINGS_FILE = "data/embeddings_wsi_level.pkl"
PATCH_DATA_FILE = "data/ndb_ufes/patch/parcial_pndb_ufes.csv"
ORIGIN_MAPPING_FILE = "data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv"
PARAMS_FILE = "clustering_params.json"
OUTPUT_DIR = Path("results/phase3_fold_creation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_FOLDS = 6
RANDOM_STATE = 42
MAX_MISSING_RATE_FOR_STRATIFICATION = 0.25

REQUIRED_STRATIFICATION_COLUMNS = (
    "origin_diagnosis",
    "morph_cluster",
    "gender",
    "age_group",
)

# Keep empty by default. An additional demographic/clinical variable must be explicitly
# promoted here and pass the audit gate before it can affect fold construction.
OPTIONAL_STRATIFICATION_COLUMNS = ()

DESCRIPTIVE_METADATA_COLUMNS = (
    "gender",
    "skin_color",
    "age_group",
    "tobacco_use",
    "alcohol_consumption",
    "sun_exposure",
    "localization",
    "larger_size",
)

MISSING_STRINGS = {
    "",
    "nan",
    "none",
    "null",
    "na",
    "n/a",
    "unknown",
    "missing",
    "not informed",
}

# ---------------------------------------------------------------------------=
# SETUP LOGGING
# ---------------------------------------------------------------------------=
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def missing_value_mask(series):
    """Return True for null values and known textual missing-value markers."""
    normalized = series.astype("string").str.strip().str.casefold()
    return series.isna() | normalized.isin(MISSING_STRINGS)

def summarize_column_for_stratification(series):
    """Summarize missingness and category support for a candidate variable."""
    missing_mask = missing_value_mask(series)
    non_missing = series[~missing_mask]
    counts = non_missing.value_counts(dropna=True)
    return {
        "missing_count": int(missing_mask.sum()),
        "missing_rate": float(missing_mask.mean()) if len(series) else 0.0,
        "n_categories": int(counts.shape[0]),
        "min_category_count": int(counts.min()) if not counts.empty else 0,
    }

def evaluate_stratification_variables(
    origin_df,
    required_columns=REQUIRED_STRATIFICATION_COLUMNS,
    optional_columns=OPTIONAL_STRATIFICATION_COLUMNS,
    descriptive_columns=DESCRIPTIVE_METADATA_COLUMNS,
    max_missing_rate=MAX_MISSING_RATE_FOR_STRATIFICATION,
    n_folds=N_FOLDS,
):
    """Audit which variables are allowed to affect fold construction."""
    rows = []
    required_set = set(required_columns)
    optional_set = set(optional_columns)
    all_columns = list(dict.fromkeys(required_columns + optional_columns + descriptive_columns))

    for column in all_columns:
        if column not in origin_df.columns:
            rows.append({
                "column": column,
                "role": "missing_from_data",
                "status": "excluded_leakage_risk",
                "missing_count": "",
                "missing_rate": "",
                "n_categories": "",
                "min_category_count": "",
                "reason": "column is not present in the origin-level dataframe",
            })
            continue

        summary = summarize_column_for_stratification(origin_df[column])
        if column in required_set:
            role = "required"
            status = "included_required"
            reason = "required fold-construction variable"
        elif summary["missing_rate"] > max_missing_rate:
            role = "optional" if column in optional_set else "descriptive"
            status = "excluded_high_missingness"
            reason = f"missing_rate exceeds {max_missing_rate:.0%} threshold"
        elif summary["min_category_count"] < n_folds:
            role = "optional" if column in optional_set else "descriptive"
            status = "excluded_low_category_support"
            reason = f"at least one non-missing category has fewer than {n_folds} origins"
        elif column in optional_set:
            role = "optional"
            status = "included_optional"
            reason = "explicitly promoted and passed missingness/support gates"
        else:
            role = "descriptive"
            status = "excluded_descriptive_only"
            reason = "descriptive factsheet field; not automatically used for stratification"

        rows.append({
            "column": column,
            "role": role,
            "status": status,
            **summary,
            "reason": reason,
        })

    return pd.DataFrame(rows)

def build_stratification_key(origin_df, audit_df):
    """Build fold strata only from variables that passed the audit."""
    included_columns = audit_df.loc[
        audit_df["status"].isin(["included_required", "included_optional"]),
        "column",
    ].tolist()

    key_parts = []
    for column in included_columns:
        values = origin_df[column].astype(str).str.strip().str.replace(r"\s+", "-", regex=True)
        if column == "morph_cluster":
            values = "c" + values
        key_parts.append(column + "=" + values)

    if not key_parts:
        raise ValueError("No stratification variables were included after audit.")

    return pd.concat(key_parts, axis=1).agg("|".join, axis=1), included_columns

def load_embeddings(path):
    """Load pickled embeddings dict {origin_id: (n_patches, 768)}."""
    with open(path, 'rb') as f:
        return pickle.load(f)

def load_params(path):
    """Load optimal clustering parameters."""
    with open(path, 'r') as f:
        return json.load(f)

# ---------------------------------------------------------------------------=
# STEP 1: LOAD AND PREPARE DATA
# ---------------------------------------------------------------------------=
def load_patch_metadata(patch_file):
    """Load patch-level metadata and aggregate to origin level."""
    logger.info(f"[1a] Loading patch metadata from {patch_file}...")
    patch_df = pd.read_csv(patch_file)
    
    # Convert origin to int, handling empty values
    patch_df['origin'] = pd.to_numeric(patch_df['origin'], errors='coerce').fillna(0).astype(int)
    
    # Remove rows with origin = 0 (empty/invalid)
    patch_df = patch_df[patch_df['origin'] > 0].reset_index(drop=True)
    
    logger.info(f"  Loaded {len(patch_df)} patches from {patch_df['origin'].nunique()} origins")
    logger.info(f"  Diagnoses: {sorted(patch_df['diagnosis'].unique())}")
    logger.info(f"  Genders: {sorted(patch_df['gender'].unique())}")
    logger.info(f"  Skin colors: {sorted(patch_df['skin_color'].unique())}")
    
    return patch_df

def aggregate_to_origin_level(patch_df):
    """Aggregate patch-level metadata to origin level."""
    logger.info(f"\n[1b] Aggregating patch data to origin level...")
    
    origin_data = []
    
    for origin_id in sorted(patch_df['origin'].unique()):
        origin_patches = patch_df[patch_df['origin'] == origin_id]
        
        # Origin diagnosis = most common diagnosis in patches from this origin
        origin_diagnosis = origin_patches['diagnosis'].mode()[0]
        
        # Patch diagnoses (classes): comma-separated unique diagnoses
        patch_diagnoses = ','.join(sorted(origin_patches['diagnosis'].unique()))
        
        # Patch count
        patch_count = len(origin_patches)
        patch_ids = ','.join(origin_patches['patch'].astype(str))
        
        row = {
            'origin_id': origin_id,
            'origin_diagnosis': origin_diagnosis,
            'patch_diagnoses': patch_diagnoses,
            'patch_count': patch_count,
            'patch_ids': patch_ids
        }

        for column in DESCRIPTIVE_METADATA_COLUMNS:
            if column in origin_patches.columns:
                counts = origin_patches[column].value_counts(dropna=False)
                row[column] = counts.index[0] if len(counts) > 0 else "not informed"

        origin_data.append(row)
    
    origin_df = pd.DataFrame(origin_data)
    logger.info(f"  Aggregated to {len(origin_df)} origins")
    logger.info(f"  Origin diagnoses: {sorted(origin_df['origin_diagnosis'].unique())}")
    
    return origin_df, patch_df

def aggregate_embeddings_to_wsi(embeddings_dict, origin_ids):
    """Aggregate patch embeddings to WSI level (mean pooling)."""
    logger.info(f"\n[1c] Loading and aggregating embeddings...")
    
    embeddings = []
    valid_origins = []
    
    for origin_id in sorted(origin_ids):
        if origin_id in embeddings_dict:
            patch_embeddings = embeddings_dict[origin_id]
            wsi_embedding = np.mean(patch_embeddings, axis=0)
            embeddings.append(wsi_embedding)
            valid_origins.append(origin_id)
    
    logger.info(f"  Aggregated {len(valid_origins)} WSI embeddings, shape: {np.array(embeddings).shape}")
    
    return np.array(embeddings), valid_origins

# ---------------------------------------------------------------------------=
# STEP 2: APPLY CLUSTERING & CREATE STRATIFICATION KEYS
# ---------------------------------------------------------------------------=
def apply_pca_kmeans(embeddings, params):
    """Apply PCA and K-Means clustering."""
    logger.info(f"\n[2a] Applying PCA reduction...")
    
    n_pca = params['pca_components']
    n_clusters = params['kmeans_clusters']
    
    pca = PCA(n_components=n_pca, random_state=RANDOM_STATE)
    pca_features = pca.fit_transform(embeddings)
    
    logger.info(f"  PCA: {embeddings.shape[1]}D → {n_pca}D")
    logger.info(f"  Explained variance: {pca.explained_variance_ratio_.sum():.1%}")
    
    logger.info(f"\n[2b] Applying K-Means clustering (K={n_clusters})...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    clusters = kmeans.fit_predict(pca_features)
    
    logger.info(f"  Cluster distribution: {np.bincount(clusters)}")
    
    return clusters

def create_stratification_keys(origin_df, clusters, output_dir=OUTPUT_DIR):
    """Create audited stratification keys."""
    logger.info(f"\n[2c] Creating missingness-aware stratification keys...")
    
    origin_df['morph_cluster'] = clusters

    audit_df = evaluate_stratification_variables(origin_df)
    audit_csv = output_dir / 'stratification_variables_audit.csv'
    audit_df.to_csv(audit_csv, index=False)

    origin_df['stratification_key'], included_columns = build_stratification_key(origin_df, audit_df)
    
    n_strata = origin_df['stratification_key'].nunique()
    logger.info(f"  Created {n_strata} unique stratification subgroups")
    logger.info(f"  Included variables: {included_columns}")
    logger.info(f"  Saved stratification audit: {audit_csv}")
    logger.info(f"  Excluded descriptive variables remain available for factsheet/reporting.")
    
    return origin_df

# ---------------------------------------------------------------------------=
# STEP 3: GREEDY LPT BIN-PACKING FOR FOLD ASSIGNMENT
# ---------------------------------------------------------------------------=
def greedy_lpt_fold_assignment(origin_df, n_folds=6):
    """
    Greedy Longest Processing Time (LPT) bin-packing within each stratification subgroup.
    
    Algorithm:
    1. For each unique stratification key:
       - Sort origins by patch_count (descending)
       - For each origin, assign to fold with minimum current patch count
    2. Result: Balanced fold sizes across all strata
    """
    logger.info(f"\n[3] Executing greedy LPT bin-packing within stratification subgroups...")
    
    fold_assignments = np.zeros(len(origin_df), dtype=int)
    fold_patches = np.zeros(n_folds, dtype=int)
    
    # Group by stratification key
    strata_groups = origin_df.groupby('stratification_key').groups
    
    for strat_key, indices in strata_groups.items():
        # Sort by patch_count descending
        sorted_indices = indices[origin_df.loc[indices, 'patch_count'].argsort()[::-1]]
        
        for idx in sorted_indices:
            patch_count = origin_df.loc[idx, 'patch_count']
            
            # Find fold with minimum current patch count
            min_fold = np.argmin(fold_patches)
            fold_assignments[idx] = min_fold
            fold_patches[min_fold] += patch_count
    
    origin_df['fold'] = fold_assignments
    
    # Print statistics
    logger.info(f"\n  Fold statistics:")
    for fold_id in range(n_folds):
        fold_origins = origin_df[origin_df['fold'] == fold_id]
        fold_patches_count = fold_origins['patch_count'].sum()
        logger.info(f"    Fold {fold_id}: {len(fold_origins):3d} origins, {fold_patches_count:4d} patches")
    
    # Balance metrics
    patch_counts = np.array([origin_df[origin_df['fold'] == f]['patch_count'].sum() for f in range(n_folds)])
    logger.info(f"\n  Balance metrics:")
    logger.info(f"    Mean patches/fold: {patch_counts.mean():.1f}")
    logger.info(f"    Std dev: {patch_counts.std():.1f}")
    logger.info(f"    Min/Max: {patch_counts.min()}/{patch_counts.max()}")
    logger.info(f"    Balance ratio: {patch_counts.max() / patch_counts.min():.3f}")
    
    return origin_df

# ---------------------------------------------------------------------------=
# STEP 4: BROADCAST TO PATCH LEVEL & SAVE
# ---------------------------------------------------------------------------=
def broadcast_to_patch_level_and_save(origin_df, patch_df, output_dir):
    """Broadcast fold assignments to patch level and save CSVs."""
    logger.info(f"\n[4a] Broadcasting fold assignments to patch level...")
    
    # Create origin_id to fold mapping
    origin_fold_map = dict(zip(origin_df['origin_id'], origin_df['fold']))
    
    # Map patches to origins and assign folds
    patch_df['origin_id'] = patch_df['origin'].astype(int)
    patch_df['fold'] = patch_df['origin_id'].map(origin_fold_map)
    
    logger.info(f"  {len(patch_df)} patches assigned to folds")
    
    # Save origin-level fold assignments with descriptive metadata retained.
    origin_columns = [
        'origin_id', 'origin_diagnosis', 'patch_diagnoses',
        *[col for col in DESCRIPTIVE_METADATA_COLUMNS if col in origin_df.columns],
        'morph_cluster', 'patch_count', 'stratification_key', 'fold'
    ]
    origin_output = origin_df[origin_columns].sort_values('origin_id')
    
    origin_csv = output_dir / 'fold_assignments_origin.csv'
    origin_output.to_csv(origin_csv, index=False)
    logger.info(f"\n[4b] Saved: {origin_csv}")
    
    # Save patch-level fold assignments with metadata
    patch_columns = [
        'origin_id', 'patch', 'diagnosis',
        *[col for col in DESCRIPTIVE_METADATA_COLUMNS if col in patch_df.columns],
        'fold'
    ]
    patch_output = patch_df[patch_columns].copy()
    
    patch_csv = output_dir / 'fold_assignments_patch_level.csv'
    patch_output.to_csv(patch_csv, index=False)
    logger.info(f"[4c] Saved: {patch_csv} ({len(patch_output)} patches)")
    
    return origin_df, patch_df

# ---------------------------------------------------------------------------=
# STEP 5: VALIDATION
# ---------------------------------------------------------------------------=
def validate_folds(origin_df, patch_df):
    """Validate fold assignments and stratification."""
    logger.info(f"\n[5] VALIDATION:")
    
    # Check 1: All origins assigned
    unassigned = origin_df['fold'].isna().sum()
    logger.info(f"  Unassigned origins: {unassigned} (should be 0)")
    
    # Check 2: No data leakage (each origin in exactly one fold)
    origin_fold_counts = patch_df.groupby('origin_id')['fold'].nunique()
    max_folds_per_origin = origin_fold_counts.max()
    logger.info(f"  Max folds per origin: {max_folds_per_origin} (should be 1)")
    
    # Check 3: Fold balance
    patch_counts = patch_df['fold'].value_counts().sort_index()
    logger.info(f"  Patches per fold: {dict(patch_counts)}")
    logger.info(f"    Std dev: {patch_counts.std():.1f}")
    logger.info(f"    Range: {patch_counts.min()}-{patch_counts.max()}")
    
    # Check 4: Class distribution per fold
    logger.info(f"\n  Class distribution per fold:")
    class_fold_cross = pd.crosstab(patch_df['fold'], patch_df['diagnosis'])
    print(class_fold_cross)
    
    # Check 5: Descriptive metadata distributions per fold.
    # These variables are reporting checks, not automatic construction targets.
    for column in DESCRIPTIVE_METADATA_COLUMNS:
        if column in patch_df.columns:
            logger.info(f"\n  {column} distribution per fold (descriptive balance check only):")
            metadata_fold_cross = pd.crosstab(patch_df['fold'], patch_df[column])
            print(metadata_fold_cross)
    
    return True

# ---------------------------------------------------------------------------=
# MAIN EXECUTION
# ---------------------------------------------------------------------------=
def main():
    """Main Phase 3 pipeline."""
    logger.info("-"*80)
    logger.info("PHASE 3: STRATIFIED 6-FOLD CROSS-VALIDATION WITH DUAL-LEVEL DIAGNOSIS")
    logger.info("-"*80 + "\n")
    
    # Load data
    patch_df = load_patch_metadata(PATCH_DATA_FILE)
    origin_df, patch_df = aggregate_to_origin_level(patch_df)
    
# Load parameters and selected embeddings path from Phase 2 output
    logger.info(f"\n[1d] Loading clustering parameters...")
    params = load_params(PARAMS_FILE)
    embeddings_path = params.get("embeddings_file", EMBEDDINGS_FILE)
    logger.info(f"  Embeddings file: {embeddings_path}")
    logger.info(f"  PCA components: {params['pca_components']}")
    logger.info(f"  K-Means clusters: {params['kmeans_clusters']}")

    # Load embeddings
    embeddings_dict = load_embeddings(embeddings_path)
    embeddings, valid_origins = aggregate_embeddings_to_wsi(embeddings_dict, origin_df['origin_id'].values)

    # Filter origin_df to valid origins (those with embeddings)
    origin_df = origin_df[origin_df['origin_id'].isin(valid_origins)].reset_index(drop=True)
    
    # Apply clustering and stratification
    clusters = apply_pca_kmeans(embeddings, params)
    origin_df = create_stratification_keys(origin_df, clusters)
    
    # Fold assignment
    origin_df = greedy_lpt_fold_assignment(origin_df, n_folds=N_FOLDS)
    
    # Save and broadcast
    origin_df, patch_df = broadcast_to_patch_level_and_save(origin_df, patch_df, OUTPUT_DIR)
    
    # Validation
    validate_folds(origin_df, patch_df)
    
    logger.info("-"*80)
    logger.info("PHASE 3 COMPLETE")
    logger.info("-"*80 + "\n")

if __name__ == '__main__':
    main()
