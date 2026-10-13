from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances, silhouette_samples, silhouette_score

from src.phase0_dataset_builder.sources import DIAGNOSIS_COLOR, SHORT_LABEL
from src.phase1_folds.embeddings import EMBEDDINGS
from src.phase1_folds.folds import CLASSES, DEFAULT_PATCH_TABLE, NOT_IN_NDB
from src.utils.logger import logger


DEFAULT_CLUSTER_DIR = Path("results/phase1/clusters")
CHOICES_NAME = "cluster_choices.csv"
CLUSTERS_NAME = "patch_clusters.csv"
VIEW_NAME = "cluster_view.png"
PCA_COMPONENTS = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25, 30]  # the same search as the last research
CLUSTER_COUNTS = range(2, 10)
SEEDS = [42, 43, 44, 45, 46]
MIN_CLUSTER_SHARE = 0.05  # every cluster holds at least this share of the patches
MAX_SIZE_RATIO = 5.0  # the largest cluster holds at most this many times the patches of the smallest


def load_embeddings(path: Path) -> tuple[list[str], np.ndarray]:
    stored = np.load(path)
    return [str(patch_id) for patch_id in stored["patch_ids"]], stored["embeddings"]


def kmeans_labels(reduced: np.ndarray, clusters: int, seed: int) -> np.ndarray:
    """K-Means labels. Some Mac builds of the maths library warn about harmless overflows, so the warnings are silenced and the result is checked instead."""
    kmeans = KMeans(n_clusters=clusters, random_state=seed, n_init=10)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        labels = kmeans.fit_predict(reduced)
    if not np.isfinite(kmeans.cluster_centers_).all() or not np.isfinite(kmeans.inertia_):
        raise FloatingPointError(f"K-Means produced non-finite results ({clusters} clusters, seed {seed})")
    if len(np.unique(labels)) != clusters:
        raise ValueError(f"K-Means produced {len(np.unique(labels))} clusters instead of {clusters}")
    return labels


def cluster_choices(matrix: np.ndarray) -> pd.DataFrame:
    """For every number of PCA components and of clusters: how well separated the clusters are, and whether their sizes are acceptable."""
    matrix = matrix.astype(np.float64)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        pca = PCA(n_components=max(PCA_COMPONENTS), svd_solver="full").fit(matrix)
        reduced_all = pca.transform(matrix)
    if not np.isfinite(reduced_all).all():
        raise FloatingPointError("The PCA of the embeddings is not finite")
    explained = np.cumsum(pca.explained_variance_ratio_)
    rows = []
    for components in PCA_COMPONENTS:
        reduced = np.ascontiguousarray(reduced_all[:, :components])
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            distances = pairwise_distances(reduced)
        if not np.isfinite(distances).all():
            raise FloatingPointError(f"The distances between the patches are not finite ({components} PCA components)")
        for clusters in CLUSTER_COUNTS:
            silhouettes = []
            for seed in SEEDS:
                labels = kmeans_labels(reduced, clusters, seed)
                silhouettes.append(silhouette_score(distances, labels, metric="precomputed"))
                if seed == SEEDS[0]:  # the clustering that will be used: seed 42
                    sizes = np.bincount(labels, minlength=clusters)
            rows.append({
                "pca_components": components,
                "clusters": clusters,
                "silhouette": float(np.mean(silhouettes)),
                "silhouette_std": float(np.std(silhouettes)),
                "explained_variance": float(explained[components - 1]),
                "smallest_cluster": int(sizes.min()),
                "largest_cluster": int(sizes.max()),
                "size_ratio": float(sizes.max() / max(sizes.min(), 1)),
                "sizes_acceptable": bool(sizes.min() >= MIN_CLUSTER_SHARE * len(matrix) and sizes.max() / max(sizes.min(), 1) <= MAX_SIZE_RATIO),
            })
        logger.info(f"Tried {components} PCA components")
    return pd.DataFrame(rows)


def run_cluster_choices(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_ids, matrix = load_embeddings(args.embeddings)
    logger.info(f"Clustering {len(patch_ids)} patches ({matrix.shape[1]} numbers each) with {len(PCA_COMPONENTS)} PCA sizes and {len(CLUSTER_COUNTS)} cluster counts, {len(SEEDS)} runs each")
    choices = cluster_choices(matrix)
    table = choices.sort_values(["sizes_acceptable", "silhouette"], ascending=[False, False]).round(4)
    table.to_csv(output_dir / CHOICES_NAME, index=False)

    acceptable = table[table["sizes_acceptable"]]
    best_per_count = acceptable.sort_values("silhouette", ascending=False).drop_duplicates("clusters").sort_values("clusters")
    logger.info(f"Best acceptable choice for each number of clusters:\n{best_per_count[['clusters', 'pca_components', 'silhouette', 'smallest_cluster', 'largest_cluster', 'explained_variance']].to_string(index=False)}")
    best = acceptable.iloc[0]
    logger.info(f"Outputs saved under {output_dir}")
    return {
        "choices_tried": len(table),
        "choices_with_acceptable_sizes": len(acceptable),
        "best_by_silhouette": f"{int(best['clusters'])} clusters, {int(best['pca_components'])} PCA components, silhouette {best['silhouette']}",
    }


def cluster_choices_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show how well separated the patch embeddings cluster, for each number of PCA components and of clusters.")
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CLUSTER_DIR)
    return parser


def by_size(labels: np.ndarray) -> np.ndarray:
    """Cluster 0 is the largest, then 1, and so on, so the numbers mean the same on every run."""
    order = np.argsort(-np.bincount(labels), kind="stable")
    return np.argsort(order)[labels]


def reduce_embeddings(matrix: np.ndarray, components: int) -> np.ndarray:
    """The embeddings after a PCA to the given number of components."""
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        reduced = np.ascontiguousarray(PCA(n_components=components, svd_solver="full").fit_transform(matrix.astype(np.float64)))
    if not np.isfinite(reduced).all():
        raise FloatingPointError("The PCA of the embeddings is not finite")
    return reduced


def patch_clusters(matrix: np.ndarray, components: int, cluster_counts: list[int], seed: int) -> dict[int, np.ndarray]:
    """For each number of clusters: the cluster of every patch, after a PCA to the given number of components."""
    reduced = reduce_embeddings(matrix, components)
    return {clusters: by_size(kmeans_labels(reduced, clusters, seed)) for clusters in cluster_counts}


def cluster_profile(labels: pd.Series, patches: pd.DataFrame) -> pd.DataFrame:
    """One row per cluster: its patches by patch label, by NDB-UFES diagnosis of the picture, and the number of case groups it reaches."""
    table = pd.DataFrame({"patches": labels.value_counts().sort_index()})
    for label in CLASSES:
        table[SHORT_LABEL[label]] = (patches["patch_diagnosis"] == label).groupby(labels).sum()
    ndb = patches["ndb_diagnosis"].replace("", NOT_IN_NDB)
    for label in CLASSES:
        table[f"NDB {SHORT_LABEL[label]}"] = (ndb == label).groupby(labels).sum()
    table["no NDB"] = (ndb == NOT_IN_NDB).groupby(labels).sum()
    table["case groups"] = patches.groupby(labels)["case_group"].nunique()
    return table


def class_shares(profile: pd.DataFrame) -> pd.DataFrame:
    """For each class, the percentage of its patches that fall in each cluster."""
    columns = [SHORT_LABEL[label] for label in CLASSES]
    return (profile[columns] / profile[columns].sum() * 100).round(1)


def run_patch_clusters(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_ids, matrix = load_embeddings(args.embeddings)
    patches = pd.read_csv(args.patch_table, dtype=str, keep_default_na=False).set_index("patch_id").loc[patch_ids]
    clusters = patch_clusters(matrix, args.pca, args.clusters, args.seed)
    table = pd.DataFrame({f"cluster_k{count}": labels for count, labels in clusters.items()}, index=pd.Index(patch_ids, name="patch_id"))
    table.to_csv(output_dir / CLUSTERS_NAME)

    for count in args.clusters:
        labels = table[f"cluster_k{count}"]
        profile = cluster_profile(labels, patches)
        logger.info(f"{count} clusters (PCA {args.pca}, seed {args.seed}); cluster 0 is the largest:\n{profile.to_string()}")
        logger.info(f"{count} clusters: percentage of each class that falls in each cluster:\n{class_shares(profile).to_string()}")
    logger.info(f"Outputs saved under {output_dir}")
    return {"patches": len(patch_ids), "clusterings": [f"{count} clusters" for count in args.clusters], "pca_components": args.pca, "seed": args.seed}


def patch_clusters_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster every patch on its embedding and show what each cluster is made of.")
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--patch-table", type=Path, default=DEFAULT_PATCH_TABLE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CLUSTER_DIR)
    parser.add_argument("--pca", type=int, default=2, help="PCA components before the clustering.")
    parser.add_argument("--clusters", type=int, nargs="+", default=[3], help="One clustering for each number given; 3 is the choice made (see notes/thesis_notes.md).")
    parser.add_argument("--seed", type=int, default=SEEDS[0])
    return parser


def render_cluster_view(reduced: np.ndarray, clusters: dict[int, np.ndarray], patches: pd.DataFrame, output: Path) -> None:
    """Left: the patches by patch label. Then, for each clustering: the patches by cluster (top) and by their own silhouette (bottom)."""
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    counts = list(clusters)
    figure = plt.figure(figsize=(5 + 4.2 * len(counts), 8.5), constrained_layout=True)
    grid = figure.add_gridspec(2, 1 + len(counts), width_ratios=[1.35] + [1] * len(counts))
    style = {"s": 7, "alpha": 0.55, "linewidths": 0}

    by_label = figure.add_subplot(grid[:, 0])
    for label in CLASSES:
        chosen = (patches["patch_diagnosis"] == label).to_numpy()
        by_label.scatter(reduced[chosen, 0], reduced[chosen, 1], color=DIAGNOSIS_COLOR[label], label=f"{SHORT_LABEL[label]}: {int(chosen.sum())}", **style)
    by_label.set_title("the same patches coloured by patch label")
    by_label.legend(markerscale=2.5, title="patch label")
    by_label.set_xlabel("PCA component 1")
    by_label.set_ylabel("PCA component 2")

    palette = plt.get_cmap("tab10")
    for column, count in enumerate(counts, start=1):
        labels = clusters[count]
        top = figure.add_subplot(grid[0, column])
        for cluster in range(count):
            chosen = labels == cluster
            top.scatter(reduced[chosen, 0], reduced[chosen, 1], color=palette(cluster), label=f"cluster {cluster}: {int(chosen.sum())}", **style)
        top.set_title(f"{count} clusters")
        top.legend(markerscale=2.5, fontsize=8)

        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            scores = silhouette_samples(reduced, labels)
        if not np.isfinite(scores).all():
            raise FloatingPointError("The silhouette scores are not finite")
        bottom = figure.add_subplot(grid[1, column])
        shown = bottom.scatter(reduced[:, 0], reduced[:, 1], c=scores, cmap="RdYlGn", vmin=-0.2, vmax=1.0, **style)
        bottom.set_title(f"silhouette of each patch, mean {scores.mean():.2f}\n{int((scores < 0.25).sum())} patches below 0.25", fontsize=10)
        bottom.set_xlabel("PCA component 1")
    figure.colorbar(shown, ax=figure.axes[-1], label="silhouette (1 = clearly in its cluster, 0 = between clusters)", shrink=0.8)
    figure.savefig(output, dpi=130)
    plt.close(figure)


def run_cluster_view(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_ids, matrix = load_embeddings(args.embeddings)
    patches = pd.read_csv(args.patch_table, dtype=str, keep_default_na=False).set_index("patch_id").loc[patch_ids]
    reduced = reduce_embeddings(matrix, args.pca)
    clusters = {count: by_size(kmeans_labels(reduced, count, args.seed)) for count in args.clusters}
    render_cluster_view(reduced[:, :2], clusters, patches, output_dir / VIEW_NAME)
    logger.info(f"Outputs saved under {output_dir}")
    return {"patches": len(patch_ids), "clusterings": [f"{count} clusters" for count in args.clusters], "picture": str(output_dir / VIEW_NAME)}


def cluster_view_arg_parser() -> argparse.ArgumentParser:
    parser = patch_clusters_arg_parser()
    parser.description = "Draw the patches in the PCA plane: by patch label, by cluster, and by their own silhouette."
    parser.set_defaults(clusters=[3, 4, 5])
    return parser
