import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def _save_figure(figure, output_path: Path, dpi: int = 200) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def create_basic_visualizations(
    results: pd.DataFrame,
    model_name: str,
    elbow_path: Path,
    silhouette_path: Path,
) -> None:
    component_counts = sorted(results["pca_components"].unique())
    column_count = min(4, len(component_counts))
    row_count = math.ceil(len(component_counts) / column_count)
    figure, axes = plt.subplots(
        row_count,
        column_count,
        figsize=(5 * column_count, 4 * row_count),
        squeeze=False,
    )

    for axis, component_count in zip(axes.flat, component_counts):
        subset = results[results["pca_components"] == component_count].sort_values(
            "kmeans_clusters"
        )
        axis.errorbar(
            subset["kmeans_clusters"],
            subset["inertia_mean"],
            yerr=subset["inertia_std"],
            fmt="o-",
            capsize=3,
        )
        axis.set_xlabel("Clusters")
        axis.set_ylabel("Mean inertia")
        axis.set_title(
            f"PCA {component_count} "
            f"({subset.iloc[0]['pca_explained_var']:.1%} variance)"
        )
        axis.grid(alpha=0.3)

    for axis in list(axes.flat)[len(component_counts):]:
        axis.set_visible(False)
    figure.suptitle(f"K-Means elbow curves: {model_name}")
    figure.tight_layout()
    _save_figure(figure, elbow_path)

    pivot = results.pivot(
        index="kmeans_clusters",
        columns="pca_components",
        values="silhouette_mean",
    )
    figure, axis = plt.subplots(figsize=(12, 7))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".3f",
        cmap="RdYlGn",
        cbar_kws={"label": "Mean silhouette score"},
        ax=axis,
    )
    axis.set_xlabel("PCA components")
    axis.set_ylabel("Clusters")
    axis.set_title(f"Silhouette scores: {model_name}")
    figure.tight_layout()
    _save_figure(figure, silhouette_path)


def create_enhanced_visualizations(
    results: pd.DataFrame,
    model_name: str,
    output_dir: Path,
) -> None:
    output_dir = Path(output_dir)
    top_results = results.nlargest(10, "silhouette_mean").reset_index(drop=True).copy()
    top_results["label"] = (
        "PCA=" + top_results["pca_components"].astype(str)
        + ", K=" + top_results["kmeans_clusters"].astype(str)
    )

    figure, axis = plt.subplots(figsize=(14, 6))
    positions = np.arange(len(top_results))
    bars = axis.bar(
        positions,
        top_results["silhouette_mean"],
        yerr=top_results["silhouette_std"],
        capsize=4,
        color=sns.color_palette("viridis", len(top_results)),
    )
    bars[0].set_color("#d1495b")
    axis.set_xticks(positions, top_results["label"], rotation=45, ha="right")
    axis.set_xlabel("Configuration")
    axis.set_ylabel("Mean silhouette score")
    axis.set_title(f"Top clustering configurations: {model_name}")
    axis.grid(axis="y", alpha=0.3)
    figure.tight_layout()
    _save_figure(figure, output_dir / f"top10_configurations_{model_name}.png", dpi=300)

    figure, axis = plt.subplots(figsize=(12, 6))
    for cluster_count in sorted(results["kmeans_clusters"].unique()):
        subset = results[results["kmeans_clusters"] == cluster_count].sort_values(
            "pca_components"
        )
        axis.plot(
            subset["pca_components"],
            subset["silhouette_mean"],
            "o-",
            label=f"K={cluster_count}",
        )
    axis.set_xlabel("PCA components")
    axis.set_ylabel("Mean silhouette score")
    axis.set_title(f"Silhouette sensitivity: {model_name}")
    axis.legend()
    axis.grid(alpha=0.3)
    figure.tight_layout()
    _save_figure(figure, output_dir / f"silhouette_by_k_{model_name}.png", dpi=300)

    figure, axis = plt.subplots(figsize=(12, 6))
    for component_count in sorted(results["pca_components"].unique()):
        subset = results[results["pca_components"] == component_count].sort_values(
            "kmeans_clusters"
        )
        axis.plot(
            subset["kmeans_clusters"],
            subset["inertia_mean"],
            "o-",
            label=f"PCA={component_count}",
        )
    axis.set_xlabel("Clusters")
    axis.set_ylabel("Mean inertia")
    axis.set_title(f"Inertia sensitivity: {model_name}")
    axis.legend(ncol=2, fontsize=8)
    axis.grid(alpha=0.3)
    figure.tight_layout()
    _save_figure(figure, output_dir / f"inertia_by_pca_{model_name}.png", dpi=300)
