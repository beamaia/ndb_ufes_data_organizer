from pathlib import Path

import pandas as pd


def average_results(run_results: list[pd.DataFrame]) -> pd.DataFrame:
    if not run_results:
        raise ValueError("At least one grid-search result is required")

    combined = pd.concat(run_results, ignore_index=True)
    averaged = combined.groupby(
        ["pca_components", "kmeans_clusters"],
        as_index=False,
    ).agg(
        pca_explained_var=("pca_explained_var", "mean"),
        inertia_mean=("inertia", "mean"),
        inertia_std=("inertia", "std"),
        silhouette_mean=("silhouette", "mean"),
        silhouette_std=("silhouette", "std"),
        runs=("run", "nunique"),
    )

    std_columns = ["inertia_std", "silhouette_std"]
    averaged[std_columns] = averaged[std_columns].fillna(0.0)
    return averaged


def save_averaged_results(results: pd.DataFrame, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
