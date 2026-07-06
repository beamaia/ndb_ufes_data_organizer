# Phase 2 Tuning Diagnostics

This page documents the diagnostic plots used to choose the Phase 2 morphology signal. The figures are generated from the averaged Phase 2 result files when repeated runs are available. The final accepted selection is still derived by rule: a configuration must be fold-ready first, and only eligible configurations are ranked by silhouette.

## Selected Result

| Field | Value |
| --- | ---: |
| Model | Virchow |
| PCA components | 2 |
| K-Means clusters | 3 |
| Mean silhouette | 0.663275 |
| Minimum cluster size | 35 origins |
| Largest/smallest cluster ratio | 2.89 |

## How To Read The Diagnostics

- **PCA components** means how many compressed embedding dimensions are kept before clustering. Lower values are simpler. Higher values keep more detail but can add noise.
- **K** is the number of clusters requested from K-Means. In this project, clusters are not labels. They are morphology groups used as one stratification signal for fold construction.
- **Inertia** measures how tightly points sit around their cluster centers. Lower is tighter. Inertia usually drops when K increases, so it is read by looking for an elbow where the drop starts slowing down.
- **Silhouette** measures how separated the clusters are. Higher is usually better, but it can be misleading if one cluster is tiny.
- **Fold-ready** means every cluster has at least 11 origins and the largest cluster is no more than 5 times the smallest cluster.
- **Rejected** configurations are not allowed to drive Phase 3, even if their silhouette is high, because they would make unsafe or unstable folds.

## Figure Guide

- **Elbow curve**. Read from left to right. A sharp early drop means adding clusters helped. A flat line means extra clusters are doing less useful work.
- **Inertia by PCA**. Read whether adding PCA components keeps reducing cluster spread. A lower curve is tighter, but this is not enough on its own.
- **Silhouette by K**. Read peaks as cleaner separations for a given PCA setting.
- **Silhouette heatmap**. Rows are PCA components and columns are K. Stronger color means higher silhouette. A red outlined marker shows the accepted configuration when the model has one.
- **Top 10 configurations**. Green bars are fold-ready. Red bars fail fold-readiness and are shown only to explain why a high score was not selected.

## Virchow

### Virchow: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_virchow.html" data-plotly-title="Virchow: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_virchow.png" alt="Virchow: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### Virchow: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_virchow.html" data-plotly-title="Virchow: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_virchow.png" alt="Virchow: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### Virchow: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_virchow.html" data-plotly-title="Virchow: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_virchow.png" alt="Virchow: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### Virchow: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_virchow.html" data-plotly-title="Virchow: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_virchow.png" alt="Virchow: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### Virchow: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_virchow.html" data-plotly-title="Virchow: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_virchow.png" alt="Virchow: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## MoCo v3 ViT Small

### MoCo v3 ViT Small: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_mocov3_vit_small.html" data-plotly-title="MoCo v3 ViT Small: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_mocov3_vit_small.png" alt="MoCo v3 ViT Small: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### MoCo v3 ViT Small: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_mocov3_vit_small.html" data-plotly-title="MoCo v3 ViT Small: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_mocov3_vit_small.png" alt="MoCo v3 ViT Small: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### MoCo v3 ViT Small: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_mocov3_vit_small.html" data-plotly-title="MoCo v3 ViT Small: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_mocov3_vit_small.png" alt="MoCo v3 ViT Small: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### MoCo v3 ViT Small: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_mocov3_vit_small.html" data-plotly-title="MoCo v3 ViT Small: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_mocov3_vit_small.png" alt="MoCo v3 ViT Small: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### MoCo v3 ViT Small: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_mocov3_vit_small.html" data-plotly-title="MoCo v3 ViT Small: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_mocov3_vit_small.png" alt="MoCo v3 ViT Small: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## EfficientNet B0

### EfficientNet B0: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_efficientnet_b0.html" data-plotly-title="EfficientNet B0: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_efficientnet_b0.png" alt="EfficientNet B0: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### EfficientNet B0: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_efficientnet_b0.html" data-plotly-title="EfficientNet B0: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_efficientnet_b0.png" alt="EfficientNet B0: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### EfficientNet B0: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_efficientnet_b0.html" data-plotly-title="EfficientNet B0: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_efficientnet_b0.png" alt="EfficientNet B0: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### EfficientNet B0: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_efficientnet_b0.html" data-plotly-title="EfficientNet B0: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_efficientnet_b0.png" alt="EfficientNet B0: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### EfficientNet B0: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_efficientnet_b0.html" data-plotly-title="EfficientNet B0: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_efficientnet_b0.png" alt="EfficientNet B0: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## DeiT Base Patch 16 224

### DeiT Base Patch 16 224: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_deit_base_patch16_224.html" data-plotly-title="DeiT Base Patch 16 224: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_deit_base_patch16_224.png" alt="DeiT Base Patch 16 224: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### DeiT Base Patch 16 224: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_deit_base_patch16_224.html" data-plotly-title="DeiT Base Patch 16 224: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_deit_base_patch16_224.png" alt="DeiT Base Patch 16 224: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### DeiT Base Patch 16 224: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_deit_base_patch16_224.html" data-plotly-title="DeiT Base Patch 16 224: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_deit_base_patch16_224.png" alt="DeiT Base Patch 16 224: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### DeiT Base Patch 16 224: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_deit_base_patch16_224.html" data-plotly-title="DeiT Base Patch 16 224: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_deit_base_patch16_224.png" alt="DeiT Base Patch 16 224: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### DeiT Base Patch 16 224: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_deit_base_patch16_224.html" data-plotly-title="DeiT Base Patch 16 224: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_deit_base_patch16_224.png" alt="DeiT Base Patch 16 224: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## ViT Large Patch 16 224

### ViT Large Patch 16 224: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_vit_large_patch16_224.html" data-plotly-title="ViT Large Patch 16 224: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_vit_large_patch16_224.png" alt="ViT Large Patch 16 224: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### ViT Large Patch 16 224: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_vit_large_patch16_224.html" data-plotly-title="ViT Large Patch 16 224: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_vit_large_patch16_224.png" alt="ViT Large Patch 16 224: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### ViT Large Patch 16 224: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_vit_large_patch16_224.html" data-plotly-title="ViT Large Patch 16 224: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_vit_large_patch16_224.png" alt="ViT Large Patch 16 224: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### ViT Large Patch 16 224: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_vit_large_patch16_224.html" data-plotly-title="ViT Large Patch 16 224: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_vit_large_patch16_224.png" alt="ViT Large Patch 16 224: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### ViT Large Patch 16 224: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_vit_large_patch16_224.html" data-plotly-title="ViT Large Patch 16 224: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_vit_large_patch16_224.png" alt="ViT Large Patch 16 224: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## EfficientNet B1

### EfficientNet B1: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_efficientnet_b1.html" data-plotly-title="EfficientNet B1: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_efficientnet_b1.png" alt="EfficientNet B1: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### EfficientNet B1: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_efficientnet_b1.html" data-plotly-title="EfficientNet B1: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_efficientnet_b1.png" alt="EfficientNet B1: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### EfficientNet B1: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_efficientnet_b1.html" data-plotly-title="EfficientNet B1: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_efficientnet_b1.png" alt="EfficientNet B1: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### EfficientNet B1: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_efficientnet_b1.html" data-plotly-title="EfficientNet B1: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_efficientnet_b1.png" alt="EfficientNet B1: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### EfficientNet B1: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_efficientnet_b1.html" data-plotly-title="EfficientNet B1: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_efficientnet_b1.png" alt="EfficientNet B1: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## ViT Base Patch 32 224

### ViT Base Patch 32 224: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_vit_base_patch32_224.html" data-plotly-title="ViT Base Patch 32 224: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_vit_base_patch32_224.png" alt="ViT Base Patch 32 224: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### ViT Base Patch 32 224: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_vit_base_patch32_224.html" data-plotly-title="ViT Base Patch 32 224: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_vit_base_patch32_224.png" alt="ViT Base Patch 32 224: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### ViT Base Patch 32 224: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_vit_base_patch32_224.html" data-plotly-title="ViT Base Patch 32 224: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_vit_base_patch32_224.png" alt="ViT Base Patch 32 224: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### ViT Base Patch 32 224: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_vit_base_patch32_224.html" data-plotly-title="ViT Base Patch 32 224: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_vit_base_patch32_224.png" alt="ViT Base Patch 32 224: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### ViT Base Patch 32 224: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_vit_base_patch32_224.html" data-plotly-title="ViT Base Patch 32 224: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_vit_base_patch32_224.png" alt="ViT Base Patch 32 224: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## UNI

### UNI: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_uni.html" data-plotly-title="UNI: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_uni.png" alt="UNI: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### UNI: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_uni.html" data-plotly-title="UNI: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_uni.png" alt="UNI: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### UNI: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_uni.html" data-plotly-title="UNI: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_uni.png" alt="UNI: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### UNI: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_uni.html" data-plotly-title="UNI: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_uni.png" alt="UNI: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### UNI: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_uni.html" data-plotly-title="UNI: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_uni.png" alt="UNI: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## ViT Base Patch 16 224

### ViT Base Patch 16 224: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_vit_base_patch16_224.html" data-plotly-title="ViT Base Patch 16 224: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_vit_base_patch16_224.png" alt="ViT Base Patch 16 224: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### ViT Base Patch 16 224: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_vit_base_patch16_224.html" data-plotly-title="ViT Base Patch 16 224: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_vit_base_patch16_224.png" alt="ViT Base Patch 16 224: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### ViT Base Patch 16 224: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_vit_base_patch16_224.html" data-plotly-title="ViT Base Patch 16 224: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_vit_base_patch16_224.png" alt="ViT Base Patch 16 224: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### ViT Base Patch 16 224: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_vit_base_patch16_224.html" data-plotly-title="ViT Base Patch 16 224: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_vit_base_patch16_224.png" alt="ViT Base Patch 16 224: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### ViT Base Patch 16 224: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_vit_base_patch16_224.html" data-plotly-title="ViT Base Patch 16 224: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_vit_base_patch16_224.png" alt="ViT Base Patch 16 224: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## CTransPath

### CTransPath: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_ctranspath.html" data-plotly-title="CTransPath: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_ctranspath.png" alt="CTransPath: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### CTransPath: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_ctranspath.html" data-plotly-title="CTransPath: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_ctranspath.png" alt="CTransPath: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### CTransPath: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_ctranspath.html" data-plotly-title="CTransPath: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_ctranspath.png" alt="CTransPath: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### CTransPath: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_ctranspath.html" data-plotly-title="CTransPath: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_ctranspath.png" alt="CTransPath: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### CTransPath: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_ctranspath.html" data-plotly-title="CTransPath: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_ctranspath.png" alt="CTransPath: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

## Swin Base Patch4 Window7 224

### Swin Base Patch4 Window7 224: Elbow Curve

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_elbow_swin_base_patch4_window7_224.html" data-plotly-title="Swin Base Patch4 Window7 224: Elbow Curve">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_elbow_swin_base_patch4_window7_224.png" alt="Swin Base Patch4 Window7 224: Elbow Curve" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how much K-Means inertia drops as more clusters are added. Look for the bend where adding clusters stops helping as much.</p>

### Swin Base Patch4 Window7 224: Inertia By PCA Components

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_inertia_by_pca_swin_base_patch4_window7_224.html" data-plotly-title="Swin Base Patch4 Window7 224: Inertia By PCA Components">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_inertia_by_pca_swin_base_patch4_window7_224.png" alt="Swin Base Patch4 Window7 224: Inertia By PCA Components" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows whether keeping more PCA dimensions makes clusters tighter. Lower inertia is tighter, but it is not the final selection rule.</p>

### Swin Base Patch4 Window7 224: Silhouette By K

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_by_k_swin_base_patch4_window7_224.html" data-plotly-title="Swin Base Patch4 Window7 224: Silhouette By K">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_by_k_swin_base_patch4_window7_224.png" alt="Swin Base Patch4 Window7 224: Silhouette By K" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows how cluster separation changes as K changes. Peaks are useful candidates, but only fold-ready candidates can be selected.</p>

### Swin Base Patch4 Window7 224: Silhouette Heatmap

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_silhouette_heatmap_swin_base_patch4_window7_224.html" data-plotly-title="Swin Base Patch4 Window7 224: Silhouette Heatmap">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_silhouette_heatmap_swin_base_patch4_window7_224.png" alt="Swin Base Patch4 Window7 224: Silhouette Heatmap" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows the full PCA-by-K grid. Stronger color means higher silhouette. The red marker shows the accepted configuration when available.</p>

### Swin Base Patch4 Window7 224: Top 10 Configurations

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/phase2_top10_configurations_swin_base_patch4_window7_224.html" data-plotly-title="Swin Base Patch4 Window7 224: Top 10 Configurations">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/phase2_top10_configurations_swin_base_patch4_window7_224.png" alt="Swin Base Patch4 Window7 224: Top 10 Configurations" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Ranks the ten highest-silhouette configurations for this model. Red bars failed fold-readiness and are not valid Phase 3 inputs.</p>

<div class="ndb-next" markdown>
<strong>Next result:</strong> [Phase 3 Results](phase3-results.md)
</div>
