import pickle
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from src.phase1.feature_extractor import FeatureExtractor
from src.utils.logger import logger

# ----------------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------------

SOURCE_CSV_PATH = 'data/ndb_ufes/patch_level/csvs/parcial_pndb_ufes.csv'
PATCH_IMAGE_DIR = 'data/ndb_ufes/patch_level/images'
OUTPUT_MAPPING_CSV = 'data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv'

BATCH_SIZE = 32  
DEVICE = 'mps'   # Apple M4

# Output
DEFAULT_EMBEDDINGS_DIR = 'data/embeddings'

# ----------------------------------------------------------------------------

def load_patch_dataframe(fold_csv_path):
    """Load patch-level data from existing fold CSV."""
    df = pd.read_csv(fold_csv_path)
    logger.info(f"Loaded {len(df)} patches from {fold_csv_path}")
    logger.info(f"Columns: {list(df.columns)}")
    return df


def create_origin_patch_mapping(source_csv_path, patch_image_dir, output_csv_path):
    """
    Create a mapping of origin_id to patch files and class labels.
    Sources from complete patch-to-origin csv (parcial_pndb_ufes.csv).
    
    Args:
        source_csv_path: Path to source csv with patch information
        patch_image_dir: Directory containing patch images
        output_csv_path: Path to save the mapping csv
    
    Returns:
        DataFrame with columns: origin_id, class, patch_count, patch_ids, image_paths
    """
    df = load_patch_dataframe(source_csv_path)
    
    patch_dir = Path(patch_image_dir)    
    origin_metadata = []
    
    logger.info(f"Creating mapping from {len(df)} patches")
    
    for origin_id, group in df.groupby('origin'):
        # use 'diagnosis' as class label
        class_label = group['diagnosis'].iloc[0]
        patch_ids = group['patch'].unique().tolist()
        
        existing_patches = []
        for patch_id in patch_ids:
            patch_path = patch_dir / f"{patch_id}.png"
            if patch_path.exists():
                existing_patches.append(str(patch_path))
        
        if existing_patches:
            origin_metadata.append({
                'origin_id': origin_id,
                'class': class_label,
                'patch_count': len(existing_patches),
                'patch_ids': ','.join(patch_ids),
                'image_paths': '|'.join(existing_patches)
            })
    
    mapping_df = pd.DataFrame(origin_metadata)
    mapping_df.to_csv(output_csv_path, index=False)
    logger.info(f"Created mapping for {len(mapping_df)} origins -> {output_csv_path}")
    logger.info(f"Class distribution:\n{mapping_df['class'].value_counts()}")
    logger.info(f"Patch count stats (per origin):\n{mapping_df['patch_count'].describe()}")
    
    return mapping_df


def extract_wsi_level_features(
    model_name, 
    origin_patch_mapping, 
    batch_size=32, 
    device='mps',
    output_dir=DEFAULT_EMBEDDINGS_DIR
):
    """
    Main extraction pipeline: Load patches -> Extract embeddings -> Aggregate to WSI level.
    
    Args:
        model_name: Name of model from registry (e.g., 'uni', 'vit_base_patch16_224', 'resnet50')
        origin_patch_mapping: DataFrame with origin_id and image_paths (from create_origin_patch_mapping)
        batch_size: Batch size for feature extraction (default: 32)
        device: Device to use - 'mps', 'cpu', or 'cuda' (default: 'mps')
        output_dir: Directory to save embeddings (default: 'data/embeddings')
        
    Returns:
        embeddings_output_path: Path to the saved embeddings pickle file
    """
    extractor = FeatureExtractor(
        model_name=model_name, 
        device=device, 
        batch_size=batch_size
    )
    
    # build list of patch paths and origin ids
    all_patch_paths = []
    all_origin_ids = []
    
    for _, row in origin_patch_mapping.iterrows():
        paths = row['image_paths'].split('|')
        origin_id = row['origin_id']
        all_patch_paths.extend(paths)
        all_origin_ids.extend([origin_id] * len(paths))
    
    logger.info(f"Total patches to extract: {len(all_patch_paths)}")

    patch_features_dict = extractor.extract_from_paths(all_patch_paths, all_origin_ids)

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_pkl_filename = f"embeddings_wsi_level_{model_name}_{timestamp}.pkl"
    output_pkl_path = output_dir_path / output_pkl_filename
    
    with open(output_pkl_path, 'wb') as f:
        pickle.dump(patch_features_dict, f)
    logger.info(f"Saved embeddings to {output_pkl_path}")
    
    n_origins = len(patch_features_dict)
    total_patches = sum(len(v) for v in patch_features_dict.values())
    avg_patches_per_origin = total_patches / n_origins if n_origins > 0 else 0
    output_dim = extractor.config.output_dim
    
    logger.info(f"{'-'*60}")
    logger.info(f"Extraction Complete:")
    logger.info(f"  Model: {model_name}")
    logger.info(f"  Origins: {n_origins}")
    logger.info(f"  Total patches: {total_patches}")
    logger.info(f"  Avg patches/origin: {avg_patches_per_origin:.1f}")
    logger.info(f"  Feature shape per origin: (n_patches, {output_dim})")
    logger.info(f"  Saved to: {output_pkl_path}")
    logger.info(f"{'-'*60}\n")
    
    return str(output_pkl_path)