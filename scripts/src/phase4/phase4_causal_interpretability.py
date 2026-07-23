#!/usr/bin/env python3
"""
Phase 4.5: Extend Fold Assignments with Causal & Interpretability Metadata

Extends existing fold assignments with:
- Risk factors (tobacco_use, alcohol_consumption, sun_exposure)
- Dysplasia severity & localization (mediator variables)
- Spatial/ROI data (patch coordinates → visual feature anchoring)
- Diagnostic task labels (TaskII, TaskIII, TaskIV)
- Age group & causal groups (for stratified fairness analysis)

Creates extended CSVs ready for causal analysis and post-training bias detection.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------=
# CONFIGURATION
# ---------------------------------------------------------------------------=
PATCH_DATA_FILE = "data/ndb_ufes/patch/parcial_pndb_ufes.csv"
FOLD_PATCH_FILE = "results/phase3/fold_creation/fold_assignments_patch_level.csv"
FOLD_ORIGIN_FILE = "results/phase3/fold_creation/fold_assignments_origin.csv"
OUTPUT_DIR = Path("results/phase4_causal_interpretability")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\n" + "-"*80)
print("PHASE 4.5: CAUSAL & INTERPRETABILITY METADATA EXTENSION")
print("-"*80)

# ---------------------------------------------------------------------------=
# LOAD DATA
# ---------------------------------------------------------------------------=
print("\n[1] Loading data...")
patch_data = pd.read_csv(PATCH_DATA_FILE)
fold_patch = pd.read_csv(FOLD_PATCH_FILE)
fold_origin = pd.read_csv(FOLD_ORIGIN_FILE)

print(f"  Patch data: {len(patch_data)} rows, {len(patch_data.columns)} columns")
print(f"  Fold (patch level): {len(fold_patch)} rows")
print(f"  Fold (origin level): {len(fold_origin)} rows")

# ---------------------------------------------------------------------------=
# EXTEND PATCH-LEVEL FOLD ASSIGNMENTS
# ---------------------------------------------------------------------------=
print("\n[2] Extending patch-level fold assignments...")

fold_patch_ext = fold_patch.copy()

# Merge with patch metadata containing causal/interpretability variables
patch_metadata = patch_data[[
    'patch', 'tobacco_use', 'alcohol_consumption', 'sun_exposure', 'age_group',
    'dysplasia_severity', 'localization', 'larger_size',
    'TaskII', 'TaskIII', 'TaskIV',
    'top_left_x', 'top_left_y', 'bottom_right_x', 'bottom_right_y'
]]

fold_patch_ext = fold_patch_ext.merge(patch_metadata, on='patch', how='left')

# Calculate ROI spatial features
fold_patch_ext['roi_width'] = (
    fold_patch_ext['bottom_right_x'] - fold_patch_ext['top_left_x']
).abs()
fold_patch_ext['roi_height'] = (
    fold_patch_ext['bottom_right_y'] - fold_patch_ext['top_left_y']
).abs()
fold_patch_ext['roi_area'] = fold_patch_ext['roi_width'] * fold_patch_ext['roi_height']

print(f"  Added: tobacco_use, alcohol_consumption, sun_exposure")
print(f"  Added: dysplasia_severity, localization, age_group")
print(f"  Added: TaskII, TaskIII, TaskIV")
print(f"  Added: ROI coordinates & metrics (width, height, area)")

# Create causal group for subgroup analysis: age_NN_tob_Y/N_alc_Y/N
fold_patch_ext['causal_group'] = (
    'age_' + fold_patch_ext['age_group'].astype(str).str.zfill(2) + '_' +
    'tob_' + fold_patch_ext['tobacco_use'].str[0].str.lower() + '_' +
    'alc_' + fold_patch_ext['alcohol_consumption'].str[0].str.lower()
)
print(f"  Created: causal_group for stratified fairness analysis")

# Reorder columns for readability
priority_cols = ['origin_id', 'patch', 'fold', 'diagnosis', 'gender', 'skin_color']
causal_cols = ['age_group', 'tobacco_use', 'alcohol_consumption', 'sun_exposure', 'causal_group']
interp_cols = [
    'dysplasia_severity', 'localization', 'larger_size',
    'roi_width', 'roi_height', 'roi_area',
    'top_left_x', 'top_left_y', 'bottom_right_x', 'bottom_right_y',
    'TaskII', 'TaskIII', 'TaskIV'
]
other_cols = [c for c in fold_patch_ext.columns if c not in priority_cols + causal_cols + interp_cols]

fold_patch_ext = fold_patch_ext[priority_cols + causal_cols + interp_cols + other_cols]

# Save extended patch-level
patch_output = OUTPUT_DIR / 'fold_assignments_patch_level_extended.csv'
fold_patch_ext.to_csv(patch_output, index=False)
print(f"  → Saved: {patch_output.name}\n")

# ---------------------------------------------------------------------------=
# EXTEND ORIGIN-LEVEL FOLD ASSIGNMENTS
# ---------------------------------------------------------------------------=
print("[3] Extending origin-level fold assignments...")

fold_origin_ext = fold_origin.copy()

# Aggregate causal/interpretability data to origin level using mode (most common value)
origin_agg = patch_data.groupby('origin').agg({
    'age_group': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'tobacco_use': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'alcohol_consumption': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'sun_exposure': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'dysplasia_severity': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'localization': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
}).reset_index().rename(columns={'origin': 'origin_id'})

# Add diagnostic tasks (may have NaN values)
for task in ['TaskII', 'TaskIII', 'TaskIV']:
    task_mode = patch_data.groupby('origin')[task].apply(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    ).reset_index()
    task_mode.columns = ['origin_id', task]
    origin_agg = origin_agg.merge(task_mode, on='origin_id', how='left')

# Merge with existing fold_origin
fold_origin_ext = fold_origin_ext.merge(origin_agg, on='origin_id', how='left')

# Add risk factor prevalence (% Yes per origin)
for risk_col in ['tobacco_use', 'alcohol_consumption', 'sun_exposure']:
    yes_counts = patch_data[patch_data[risk_col] == 'Yes'].groupby('origin').size()
    total_counts = patch_data.groupby('origin').size()
    yes_pct = (yes_counts / total_counts * 100).fillna(0).astype(int)
    yes_pct.index.name = 'origin_id'
    
    col_name = f'{risk_col}_prevalence_pct'
    fold_origin_ext[col_name] = fold_origin_ext['origin_id'].map(yes_pct).fillna(0).astype(int)

print(f"  Aggregated to origin level: age_group, risk factors, dysplasia_severity")
print(f"  Added: Risk factor prevalence % (tobacco, alcohol, sun_exposure)")

# Create causal group at origin level
fold_origin_ext['causal_group'] = (
    'age_' + fold_origin_ext['age_group'].astype(str).str.zfill(2) + '_' +
    'tob_' + fold_origin_ext['tobacco_use'].str[0].str.lower() + '_' +
    'alc_' + fold_origin_ext['alcohol_consumption'].str[0].str.lower()
)

# Reorder columns
priority_cols = ['origin_id', 'fold', 'origin_diagnosis', 'patch_count', 'gender', 'skin_color', 'morph_cluster']
causal_cols = [
    'age_group', 'tobacco_use', 'alcohol_consumption', 'sun_exposure',
    'tobacco_use_prevalence_pct', 'alcohol_consumption_prevalence_pct', 
    'sun_exposure_prevalence_pct', 'causal_group'
]
interp_cols = ['dysplasia_severity', 'localization', 'TaskII', 'TaskIII', 'TaskIV']
other_cols = [c for c in fold_origin_ext.columns if c not in priority_cols + causal_cols + interp_cols]

fold_origin_ext = fold_origin_ext[priority_cols + causal_cols + interp_cols + other_cols]

# Save extended origin-level
origin_output = OUTPUT_DIR / 'fold_assignments_origin_extended.csv'
fold_origin_ext.to_csv(origin_output, index=False)
print(f"  → Saved: {origin_output.name}\n")

# ---------------------------------------------------------------------------=
# DATA QUALITY REPORT
# ---------------------------------------------------------------------------=
print("[4] Data Quality Report...")

print(f"\n  RISK FACTORS (Patch Level Distribution):")
for col in ['tobacco_use', 'alcohol_consumption', 'sun_exposure']:
    print(f"    {col}:")
    dist = fold_patch_ext[col].value_counts(dropna=False)
    for val, count in dist.items():
        pct = 100 * count / len(fold_patch_ext)
        print(f"      {val}: {count:,} ({pct:.1f}%)")

print(f"\n  INTERPRETABILITY DATA (Patch Level):")
print(f"    Dysplasia severity (top 5):")
for val, count in fold_patch_ext['dysplasia_severity'].value_counts(dropna=False).head(5).items():
    print(f"      {val}: {count:,}")
print(f"    Localization (top 5):")
for val, count in fold_patch_ext['localization'].value_counts(dropna=False).head(5).items():
    print(f"      {val}: {count:,}")
print(f"    ROI coverage: {fold_patch_ext['roi_area'].notna().sum():,}/{len(fold_patch_ext):,} patches")
print(f"    ROI area - Mean: {fold_patch_ext['roi_area'].mean():.0f}px², Std: {fold_patch_ext['roi_area'].std():.0f}px²")

print(f"\n  DIAGNOSTIC TASKS:")
for task in ['TaskII', 'TaskIII', 'TaskIV']:
    filled = fold_patch_ext[task].notna().sum()
    print(f"    {task}: {filled:,}/{len(fold_patch_ext):,} patches ({100*filled/len(fold_patch_ext):.1f}%)")

print(f"\n  CAUSAL GROUPS (Patch Level):")
print(f"    Unique groups: {fold_patch_ext['causal_group'].nunique()}")
print(f"    Top 5 groups:")
for group, count in fold_patch_ext['causal_group'].value_counts().head(5).items():
    pct = 100 * count / len(fold_patch_ext)
    print(f"      {group}: {count:,} ({pct:.1f}%)")

print(f"\n  FOLD BALANCE (Patches per fold):")
fold_stats = fold_patch_ext.groupby('fold').size().describe()
for fold_id in sorted(fold_patch_ext['fold'].unique()):
    count = len(fold_patch_ext[fold_patch_ext['fold'] == fold_id])
    print(f"    Fold {fold_id}: {count:,} patches")
print(f"    Mean: {fold_stats['mean']:.0f}, Std: {fold_stats['std']:.1f}, Min: {fold_stats['min']:.0f}, Max: {fold_stats['max']:.0f}")

# ---------------------------------------------------------------------------=
# SUMMARY STATISTICS
# ---------------------------------------------------------------------------=
print("\n[5] Creating summary statistics...")

summary = pd.DataFrame([{
    'total_patches': len(fold_patch_ext),
    'total_origins': fold_origin_ext['origin_id'].nunique(),
    'num_folds': fold_patch_ext['fold'].nunique(),
    'causal_groups_count': fold_patch_ext['causal_group'].nunique(),
    'tobacco_yes_pct': round((fold_patch_ext['tobacco_use'] == 'Yes').mean() * 100, 1),
    'alcohol_yes_pct': round((fold_patch_ext['alcohol_consumption'] == 'Yes').mean() * 100, 1),
    'sun_yes_pct': round((fold_patch_ext['sun_exposure'] == 'Yes').mean() * 100, 1),
    'roi_area_mean': round(fold_patch_ext['roi_area'].mean(), 0),
    'roi_area_std': round(fold_patch_ext['roi_area'].std(), 0),
}])

summary_output = OUTPUT_DIR / 'causal_interpretability_summary.csv'
summary.to_csv(summary_output, index=False)
print(f"  Saved: causal_interpretability_summary.csv")

# ---------------------------------------------------------------------------=
# FINAL OUTPUT
# ---------------------------------------------------------------------------=
print("\n" + "-"*80)
print("CAUSAL & INTERPRETABILITY METADATA EXTENSION COMPLETE")
print("-"*80)
print(f"\nGenerated Files in {OUTPUT_DIR}/:")
print(f"  1. fold_assignments_patch_level_extended.csv ({len(fold_patch_ext):,} rows, extended)")
print(f"  2. fold_assignments_origin_extended.csv ({len(fold_origin_ext):,} rows, extended)")
print(f"  3. causal_interpretability_summary.csv (metadata summary)")
print(f"\nKey Features Added:")
print(f"  Risk factors: tobacco_use, alcohol_consumption, sun_exposure")
print(f"  Interpretability: dysplasia_severity, localization, roi_metrics")
print(f"  Spatial: coordinates + area, width, height")
print(f"  Diagnostic tasks: TaskII, TaskIII, TaskIV")
print(f"  Causal groups: For stratified fairness/bias analysis")
print(f"  Age groups: For demographic stratification")
print(f"\nReady for post-training bias detection & causal discovery!\n")
