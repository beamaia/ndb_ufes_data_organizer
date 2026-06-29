import json
from pathlib import Path

import pandas as pd


def select_optimal_params(results: pd.DataFrame, random_state: int) -> dict:
    if results.empty:
        raise ValueError("Cannot select parameters from empty results")

    best = results.loc[results["silhouette_mean"].idxmax()]
    return {
        "pca_components": int(best["pca_components"]),
        "kmeans_clusters": int(best["kmeans_clusters"]),
        "silhouette_score": float(best["silhouette_mean"]),
        "silhouette_std": float(best["silhouette_std"]),
        "explained_variance": float(best["pca_explained_var"]),
        "inertia": float(best["inertia_mean"]),
        "inertia_std": float(best["inertia_std"]),
        "random_state": random_state,
        "runs": int(best["runs"]),
    }


def save_optimal_params(params: dict, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as params_file:
        json.dump(params, params_file, indent=2)
