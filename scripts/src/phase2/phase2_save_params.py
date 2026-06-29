import json
from pathlib import Path

import pandas as pd


class NoEligibleClusteringError(ValueError):
    """Raised when a model has no fold-ready clustering configuration."""


def select_optimal_params(
    results: pd.DataFrame,
    random_state: int,
    min_cluster_size: int,
    max_cluster_size_ratio: float,
) -> dict:
    if results.empty:
        raise ValueError("Cannot select parameters from empty results")

    eligible = results[
        (results["min_cluster_size_min"] >= min_cluster_size)
        & (results["cluster_size_ratio_max"] <= max_cluster_size_ratio)
    ]
    if eligible.empty:
        raise NoEligibleClusteringError(
            "No clustering configuration satisfies the fold-readiness constraints: "
            f"minimum cluster size {min_cluster_size}, maximum size ratio "
            f"{max_cluster_size_ratio}"
        )

    best = eligible.loc[eligible["silhouette_mean"].idxmax()]
    return {
        "pca_components": int(best["pca_components"]),
        "kmeans_clusters": int(best["kmeans_clusters"]),
        "silhouette_score": float(best["silhouette_mean"]),
        "silhouette_std": float(best["silhouette_std"]),
        "explained_variance": float(best["pca_explained_var"]),
        "inertia": float(best["inertia_mean"]),
        "inertia_std": float(best["inertia_std"]),
        "min_cluster_size": int(best["min_cluster_size_min"]),
        "mean_min_cluster_size": float(best["min_cluster_size_mean"]),
        "max_cluster_size": int(best["max_cluster_size_max"]),
        "mean_max_cluster_size": float(best["max_cluster_size_mean"]),
        "max_cluster_size_ratio": float(best["cluster_size_ratio_max"]),
        "mean_cluster_size_ratio": float(best["cluster_size_ratio_mean"]),
        "selection_constraints": {
            "min_cluster_size": min_cluster_size,
            "max_cluster_size_ratio": max_cluster_size_ratio,
        },
        "random_state": random_state,
        "runs": int(best["runs"]),
    }


def save_optimal_params(params: dict, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as params_file:
        json.dump(params, params_file, indent=2)
