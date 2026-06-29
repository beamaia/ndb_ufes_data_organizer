import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from sklearn.decomposition import PCA
from pathlib import Path
import logging
import plotly.graph_objects as go
from datetime import datetime

logger = logging.getLogger(__name__)

# PIN: this module is currently not called by the active pipeline. If moved to
# Phase 3, reassess whether these post-clustering pca plots still answer a real
# audit/reporting question before wiring them into an entrypoint.

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

WSI_CLUSTERS_CSV = 'results/phase3_fold_creation/fold_assignments_origin.csv'
PATCH_CLUSTERS_CSV = 'data/ndb_ufes/patch_level/csvs/fold_assignments_patch_level_detailed.csv'
METADATA_CSV = 'data/ndb_ufes/origin_level/csvs/ndb-ufes.csv'

PCA_COMPONENTS_2D = 2
PCA_COMPONENTS_3D = 3
RANDOM_STATE = 42

CLASS_COLORS = {
    'OSCC': '#1f77b4',  # Blue
    'Leukoplakia with dysplasia': '#ff7f0e',  # Orange
    'Leukoplakia without dysplasia': '#2ca02c'  # Green
}

CLUSTER_MARKERS = {
    0: 'o',  # circle
    1: 's',  # square
    2: '^',  # triangle
    3: '*'   # star
}

CLUSTER_MARKERS_PLOTLY = {
    0: 'circle',         # circle
    1: 'square',         # square
    2: 'diamond',        # diamond (closest to triangle)
    3: 'cross'           # cross (closest to star)
}

CLUSTER_NAMES_READABLE = {
    0: 'Cluster 1',
    1: 'Cluster 2',
    2: 'Cluster 3',
    3: 'Cluster 4'
}


def load_wsi_embeddings(embeddings_file):
    """Load WSI-level (origin-level) embeddings from pickle."""
    logger.info(f"Loading WSI embeddings from {embeddings_file}...")
    with open(embeddings_file, 'rb') as f:
        wsi_data = pickle.load(f)
    
    # Convert to dataframe: origin_id -> embedding (mean pooled from patches)
    origins = []
    embeddings = []
    for origin_id in sorted(wsi_data.keys()):
        patch_embeddings = wsi_data[origin_id]  # Shape: (n_patches, D)
        # Mean pool patches to get single WSI embedding
        wsi_embedding = np.mean(patch_embeddings, axis=0)  # Shape: (D,)
        origins.append(int(origin_id))
        embeddings.append(wsi_embedding)
    
    embeddings_array = np.array(embeddings)  # Shape: (n_origins, D)
    logger.info(f"Loaded {len(origins)} WSI embeddings, shape: {embeddings_array.shape}")
    return origins, embeddings_array


def load_wsi_metadata():
    """Load WSI cluster assignments and diagnostic classes."""
    logger.info("Loading WSI metadata...")
    
    # Load cluster assignments
    clusters_df = pd.read_csv(WSI_CLUSTERS_CSV)
    
    # Use origin_diagnosis from clusters_df (diagnostic class for each WSI)
    wsi_df = clusters_df[['origin_id', 'origin_diagnosis', 'morph_cluster']].copy()
    wsi_df.rename(columns={'origin_diagnosis': 'class'}, inplace=True)
    
    logger.info(f"Loaded metadata for {len(wsi_df)} origins")
    logger.info(f"   Classes: {wsi_df['class'].unique()}")
    logger.info(f"   Clusters: {sorted(wsi_df['morph_cluster'].unique())}")
    
    return wsi_df


def load_patch_metadata():
    """Load patch-level cluster assignments and classes."""
    logger.info("Loading patch metadata...")
    patch_df = pd.read_csv(PATCH_CLUSTERS_CSV)
    
    logger.info(f"Loaded metadata for {len(patch_df)} patches")
    logger.info(f"   Classes: {patch_df['class'].unique()}")
    logger.info(f"   Clusters: {sorted(patch_df['morph_cluster'].unique())}")
    
    return patch_df


def apply_pca(embeddings, n_components=2):
    """Apply PCA reduction to embeddings."""
    pca = PCA(n_components=n_components, random_state=RANDOM_STATE)
    reduced = pca.fit_transform(embeddings)
    explained_var = pca.explained_variance_ratio_.sum()
    logger.info(f"PCA: {embeddings.shape[1]}D → {n_components}D, "
                f"explained variance: {explained_var:.3f}")
    return reduced, pca


def create_wsi_2d_plot(wsi_features_2d, wsi_df, model_name, timestamp, output_dir):
    """Create 2D scatter plot of WSI clusters with class colors."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    class_list = ['All data', 'OSCC', 'Leukoplakia with dysplasia', 'Leukoplakia without dysplasia']
    
    for idx, (ax, class_filter) in enumerate(zip(axes, class_list)):
        # Filter data
        if class_filter == 'All data':
            mask = np.ones(len(wsi_df), dtype=bool)
            title = 'All WSIs (Origins)'
        else:
            mask = wsi_df['class'] == class_filter
            title = f'{class_filter} (n={mask.sum()})'
        
        filtered_features = wsi_features_2d[mask]
        filtered_df = wsi_df[mask].reset_index(drop=True)
        
        # Plot each cluster
        for cluster in sorted(filtered_df['morph_cluster'].unique()):
            cluster_mask = filtered_df['morph_cluster'] == cluster
            
            # For this cluster, plot by class
            for class_name in CLASS_COLORS.keys():
                class_cluster_mask = cluster_mask & (filtered_df['class'] == class_name)
                if class_cluster_mask.sum() > 0:
                    indices = np.where(class_cluster_mask)[0]
                    ax.scatter(
                        filtered_features[indices, 0],
                        filtered_features[indices, 1],
                        c=CLASS_COLORS[class_name],
                        marker=CLUSTER_MARKERS[cluster],
                        s=150,
                        alpha=0.7,
                        edgecolors='black',
                        linewidth=0.5,
                        label=f'{class_name} (C{cluster})' if idx == 0 else ''
                    )
        
        ax.set_xlabel('PC1', fontsize=12, fontweight='bold')
        ax.set_ylabel('PC2', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Create custom legend
    class_patches = [mpatches.Patch(facecolor=color, edgecolor='black', label=class_name)
                     for class_name, color in CLASS_COLORS.items()]
    cluster_lines = [Line2D([0], [0], marker=marker, color='w', markerfacecolor='gray',
                            markersize=8, markeredgecolor='black', label=f'Cluster {cluster}')
                     for cluster, marker in CLUSTER_MARKERS.items()]
    
    fig.legend(handles=class_patches + cluster_lines, loc='upper center', 
               bbox_to_anchor=(0.5, -0.02), ncol=7, fontsize=11, frameon=True)
    
    fig.suptitle(f'WSI-Level Cluster Analysis: PCA 2D Projection ({model_name})', 
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_path = output_dir / f'wsi_clusters_2d_{model_name}_{timestamp}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved: {output_path}")
    plt.close()


def create_patch_2d_plot(wsi_ids_patch, patch_features_2d, patch_df, model_name, timestamp, output_dir):
    """Create 2D scatter plot of patch clusters with class colors."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    class_list = ['All data', 'OSCC', 'Leukoplakia with dysplasia', 'Leukoplakia without dysplasia']
    
    for idx, (ax, class_filter) in enumerate(zip(axes, class_list)):
        # Filter data
        if class_filter == 'All data':
            mask = np.ones(len(patch_df), dtype=bool)
            title = 'All Patches'
        else:
            mask = patch_df['class'] == class_filter
            title = f'{class_filter} (n={mask.sum()})'
        
        filtered_features = patch_features_2d[mask]
        filtered_df = patch_df[mask].reset_index(drop=True)
        
        # Plot each cluster
        for cluster in sorted(filtered_df['morph_cluster'].unique()):
            cluster_mask = filtered_df['morph_cluster'] == cluster
            
            # For this cluster, plot by class
            for class_name in CLASS_COLORS.keys():
                class_cluster_mask = cluster_mask & (filtered_df['class'] == class_name)
                if class_cluster_mask.sum() > 0:
                    indices = np.where(class_cluster_mask)[0]
                    ax.scatter(
                        filtered_features[indices, 0],
                        filtered_features[indices, 1],
                        c=CLASS_COLORS[class_name],
                        marker=CLUSTER_MARKERS[cluster],
                        s=100,
                        alpha=0.6,
                        edgecolors='black',
                        linewidth=0.3,
                        label=f'{class_name} (C{cluster})' if idx == 0 else ''
                    )
        
        ax.set_xlabel('PC1', fontsize=12, fontweight='bold')
        ax.set_ylabel('PC2', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Create custom legend
    class_patches = [mpatches.Patch(facecolor=color, edgecolor='black', label=class_name)
                     for class_name, color in CLASS_COLORS.items()]
    cluster_lines = [Line2D([0], [0], marker=marker, color='w', markerfacecolor='gray',
                            markersize=8, markeredgecolor='black', label=f'Cluster {cluster}')
                     for cluster, marker in CLUSTER_MARKERS.items()]
    
    fig.legend(handles=class_patches + cluster_lines, loc='upper center', 
               bbox_to_anchor=(0.5, -0.02), ncol=7, fontsize=11, frameon=True)
    
    fig.suptitle(f'Patch-Level Cluster Analysis: PCA 2D Projection ({model_name})', 
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_path = output_dir / f'patch_clusters_2d_{model_name}_{timestamp}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved: {output_path}")
    plt.close()


def create_wsi_3d_plot(wsi_features_3d, wsi_df, origin_ids, model_name, timestamp, output_dir):
    """Create interactive 3D scatter plot of WSI clusters."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    wsi_df_3d = wsi_df.copy()
    wsi_df_3d['PC1'] = wsi_features_3d[:, 0]
    wsi_df_3d['PC2'] = wsi_features_3d[:, 1]
    wsi_df_3d['PC3'] = wsi_features_3d[:, 2]
    wsi_df_3d['origin_id'] = origin_ids
    wsi_df_3d.loc[:, 'color'] = wsi_df_3d['class'].map(CLASS_COLORS)  # Use .loc[] to avoid ChainedAssignmentWarning
    wsi_df_3d.loc[:, 'marker'] = wsi_df_3d['morph_cluster'].map(CLUSTER_MARKERS_PLOTLY)  # Use .loc[] to avoid ChainedAssignmentWarning
    wsi_df_3d.loc[:, 'hover_text'] = (wsi_df_3d['origin_id'].astype(str) + ' | ' + 
                                wsi_df_3d['class'] + ' | ' + 
                                'Cluster ' + wsi_df_3d['morph_cluster'].astype(str))  # Use .loc[] to avoid ChainedAssignmentWarning
    
    fig = go.Figure()
    
    for class_name in CLASS_COLORS.keys():
        for cluster in range(4):
            mask = (wsi_df_3d['class'] == class_name) & (wsi_df_3d['morph_cluster'] == cluster)
            subset = wsi_df_3d[mask]
            
            if len(subset) > 0:
                fig.add_trace(go.Scatter3d(
                    x=subset['PC1'],
                    y=subset['PC2'],
                    z=subset['PC3'],
                    mode='markers',
                    name=f'{class_name} (C{cluster})',
                    marker=dict(
                        size=8,
                        color=subset['color'].iloc[0],
                        symbol=subset['marker'].iloc[0],
                        opacity=0.8,
                        line=dict(color='black', width=1)
                    ),
                    text=subset['hover_text'],
                    hovertemplate='<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<br>PC3: %{z:.2f}<extra></extra>'
                ))
    
    fig.update_layout(
        title=f'WSI-Level Clusters: 3D PCA Projection ({model_name})',
        scene=dict(
            xaxis_title='PC1',
            yaxis_title='PC2',
            zaxis_title='PC3',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            )
        ),
        width=1000,
        height=900,
        hovermode='closest'
    )
    
    output_path = output_dir / f'wsi_clusters_3d_{model_name}_{timestamp}.html'
    fig.write_html(str(output_path))
    logger.info(f"Saved: {output_path}")


def create_patch_3d_plot(wsi_ids_patch, patch_features_3d, patch_df, model_name, timestamp, output_dir):
    """Create interactive 3D scatter plot of patch clusters."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    patch_df_3d = patch_df.copy()
    patch_df_3d['PC1'] = patch_features_3d[:, 0]
    patch_df_3d['PC2'] = patch_features_3d[:, 1]
    patch_df_3d['PC3'] = patch_features_3d[:, 2]
    patch_df_3d.loc[:, 'color'] = patch_df_3d['class'].map(CLASS_COLORS)  # Use .loc[] to avoid ChainedAssignmentWarning
    patch_df_3d.loc[:, 'marker'] = patch_df_3d['morph_cluster'].map(CLUSTER_MARKERS_PLOTLY)  # Use .loc[] to avoid ChainedAssignmentWarning
    patch_df_3d.loc[:, 'hover_text'] = (patch_df_3d['patch_id'].astype(str) + ' | ' + 
                                  'Origin ' + patch_df_3d['origin_id'].astype(str) + ' | ' +
                                  patch_df_3d['class'] + ' | ' + 
                                  'Cluster ' + patch_df_3d['morph_cluster'].astype(str))  # Use .loc[] to avoid ChainedAssignmentWarning
    
    fig = go.Figure()
    
    for class_name in CLASS_COLORS.keys():
        for cluster in range(4):
            mask = (patch_df_3d['class'] == class_name) & (patch_df_3d['morph_cluster'] == cluster)
            subset = patch_df_3d[mask]
            
            if len(subset) > 0:
                fig.add_trace(go.Scatter3d(
                    x=subset['PC1'],
                    y=subset['PC2'],
                    z=subset['PC3'],
                    mode='markers',
                    name=f'{class_name} (C{cluster})',
                    marker=dict(
                        size=5,
                        color=subset['color'].iloc[0],
                        symbol=subset['marker'].iloc[0],
                        opacity=0.7,
                        line=dict(color='black', width=0.5)
                    ),
                    text=subset['hover_text'],
                    hovertemplate='<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<br>PC3: %{z:.2f}<extra></extra>'
                ))
    
    fig.update_layout(
        title=f'Patch-Level Clusters: 3D PCA Projection ({model_name})',
        scene=dict(
            xaxis_title='PC1',
            yaxis_title='PC2',
            zaxis_title='PC3',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            )
        ),
        width=1000,
        height=900,
        hovermode='closest'
    )
    
    output_path = output_dir / f'patch_clusters_3d_{model_name}_{timestamp}.html'
    fig.write_html(str(output_path))
    logger.info(f"Saved: {output_path}")


def visualize_embeddings(model_name, embeddings_file, timestamp=None, output_dir='results/phase1_visualizations'):
    """
    Main visualization pipeline.
    
    Args:
        model_name: Name of the model (e.g., 'uni', 'vit_base_patch16_224')
        embeddings_file: Path to embeddings pickle file
        timestamp: Timestamp string for output files (default: current time)
        output_dir: Directory to save visualizations
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("-"*70)
    logger.info(f"PHASE 1: CLUSTER VISUALIZATION - {model_name.upper()}")
    logger.info(f"Timestamp: {timestamp}")
    logger.info("-"*70 + "\n")
    
    # Load data
    logger.info("[1] Loading data...")
    origin_ids, wsi_embeddings = load_wsi_embeddings(embeddings_file)
    wsi_df = load_wsi_metadata()
    patch_df = load_patch_metadata()
    
    # Ensure origin_ids match the WSI dataframe
    # First filter wsi_df to only include origins that have embeddings
    origin_ids_sorted = sorted(origin_ids)
    wsi_df = wsi_df[wsi_df['origin_id'].isin(origin_ids_sorted)].sort_values('origin_id').reset_index(drop=True)
    
    # Then filter origin_ids_sorted to only include origins that are in wsi_df
    # This ensures they have the same length
    wsi_origin_ids = set(wsi_df['origin_id'].values)
    origin_ids_sorted = [oid for oid in origin_ids_sorted if oid in wsi_origin_ids]
    
    logger.info(f"Aligned {len(origin_ids_sorted)} origins between embeddings and metadata")
    
    # Reorder embeddings to match sorted origin_ids
    embeddings_reordered = []
    for oid in origin_ids_sorted:
        for orig_id, emb in zip(origin_ids, wsi_embeddings):
            if int(orig_id) == oid:
                embeddings_reordered.append(emb)
                break
    wsi_embeddings = np.array(embeddings_reordered)
    
    logger.info(f"\n[2] Applying PCA for WSI-level features...")
    wsi_features_2d, pca_2d = apply_pca(wsi_embeddings, PCA_COMPONENTS_2D)
    wsi_features_3d, pca_3d = apply_pca(wsi_embeddings, PCA_COMPONENTS_3D)
    
    # For patch-level visualization: map patches to origins
    logger.info(f"\n[3] Mapping patches to origins...")
    wsi_to_patch_map = {}
    for idx, origin_id in enumerate(origin_ids_sorted):
        wsi_to_patch_map[origin_id] = idx
    
    patch_origins = patch_df['origin_id'].values
    patch_indices = np.array([wsi_to_patch_map.get(oid, -1) for oid in patch_origins])
    valid_patches = patch_indices >= 0
    patch_df_valid = patch_df[valid_patches].reset_index(drop=True)
    patch_indices_valid = patch_indices[valid_patches]
    
    # Create patch-level feature arrays (replicate WSI features for each patch)
    patch_features_2d = wsi_features_2d[patch_indices_valid]
    patch_features_3d = wsi_features_3d[patch_indices_valid]
    
    logger.info(f"{len(patch_df_valid)} patches mapped to {len(np.unique(patch_indices_valid))} origins")
    
    logger.info(f"\n[4] Creating 2D scatter plots...")
    create_wsi_2d_plot(wsi_features_2d, wsi_df, model_name, timestamp, output_dir)
    create_patch_2d_plot(patch_indices_valid, patch_features_2d, patch_df_valid, model_name, timestamp, output_dir)
    
    logger.info(f"\n[5] Creating 3D interactive plots...")
    create_wsi_3d_plot(wsi_features_3d, wsi_df, origin_ids_sorted, model_name, timestamp, output_dir)
    create_patch_3d_plot(patch_indices_valid, patch_features_3d, patch_df_valid, model_name, timestamp, output_dir)
    
    logger.info(f"\n" + "="*70)
    logger.info(f"VISUALIZATION COMPLETE ({model_name})")
    logger.info("="*70)
    logger.info(f"Output directory: {output_dir}/")
    logger.info(f"  - wsi_clusters_2d_{model_name}_{timestamp}.png")
    logger.info(f"  - patch_clusters_2d_{model_name}_{timestamp}.png")
    logger.info(f"  - wsi_clusters_3d_{model_name}_{timestamp}.html")
    logger.info(f"  - patch_clusters_3d_{model_name}_{timestamp}.html")
    logger.info("\n")
