import pickle
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from src.utils.logger import logger


EMBEDDING_PREFIX = "embeddings_wsi_level_"


def load_config(config_path: Path) -> dict:
    with Path(config_path).open() as config_file:
        return yaml.safe_load(config_file)


def model_name_from_embedding_path(path: str | Path) -> str:
    filename = Path(path).stem
    if not filename.startswith(EMBEDDING_PREFIX):
        raise ValueError(f"Unexpected embedding filename: {path}")

    try:
        model_name, date, time = filename[len(EMBEDDING_PREFIX):].rsplit("_", 2)
    except ValueError as error:
        raise ValueError(f"Embedding filename has no valid timestamp: {path}") from error
    if not model_name or len(date) != 8 or len(time) != 6:
        raise ValueError(f"Embedding filename has no valid timestamp: {path}")
    if not date.isdigit() or not time.isdigit():
        raise ValueError(f"Embedding filename has no valid timestamp: {path}")
    return model_name


def discover_latest_embeddings(pattern: str) -> dict[str, Path]:
    paths = [Path(path) for path in glob(pattern)]
    if not paths:
        raise FileNotFoundError(f"No embeddings found matching {pattern}")

    embeddings_by_model: dict[str, list[Path]] = {}
    for path in sorted(paths):
        try:
            model_name = model_name_from_embedding_path(path)
        except ValueError as error:
            logger.warning(str(error))
            continue
        embeddings_by_model.setdefault(model_name, []).append(path)

    if not embeddings_by_model:
        raise FileNotFoundError(f"No valid timestamped embeddings found matching {pattern}")

    latest_embeddings = {}
    for model_name, model_paths in sorted(embeddings_by_model.items()):
        latest_path = max(model_paths, key=lambda path: path.stem.rsplit("_", 2)[1:])
        latest_embeddings[model_name] = latest_path
        logger.info(f"  {model_name:30s} -> {latest_path}")
    return latest_embeddings


def load_embeddings(path: Path) -> dict:
    with Path(path).open("rb") as embeddings_file:
        embeddings = pickle.load(embeddings_file)
    if not isinstance(embeddings, dict) or not embeddings:
        raise ValueError(f"Expected a non-empty embeddings dictionary in {path}")
    return embeddings


def load_origin_ids(path: Path) -> list:
    metadata = pd.read_csv(path)
    if "origin_id" not in metadata.columns:
        raise ValueError(f"Origin metadata must contain an 'origin_id' column: {path}")
    if metadata["origin_id"].duplicated().any():
        raise ValueError(f"Origin metadata contains duplicate origin IDs: {path}")
    return sorted(metadata["origin_id"].tolist())


def aggregate_to_wsi_level(embeddings: dict, origin_ids: list) -> np.ndarray:
    origin_id_set = set(origin_ids)
    missing_origins = [origin_id for origin_id in origin_ids if origin_id not in embeddings]
    extra_origins = [origin_id for origin_id in embeddings if origin_id not in origin_id_set]
    if missing_origins or extra_origins:
        raise ValueError(
            "Embedding/metadata origin mismatch: "
            f"{len(missing_origins)} missing and {len(extra_origins)} unexpected origins"
        )

    wsi_features = []
    embedding_dim = None
    for origin_id in origin_ids:
        patch_embeddings = np.asarray(embeddings[origin_id])
        if patch_embeddings.ndim != 2 or patch_embeddings.shape[0] == 0:
            raise ValueError(
                f"Origin {origin_id} has invalid patch embeddings shape "
                f"{patch_embeddings.shape}"
            )
        if embedding_dim is None:
            embedding_dim = patch_embeddings.shape[1]
        elif patch_embeddings.shape[1] != embedding_dim:
            raise ValueError(
                f"Origin {origin_id} has {patch_embeddings.shape[1]} features; "
                f"expected {embedding_dim}"
            )
        if not np.isfinite(patch_embeddings).all():
            raise ValueError(f"Origin {origin_id} contains non-finite embeddings")
        wsi_features.append(patch_embeddings.mean(axis=0))

    return np.vstack(wsi_features)


def run_grid_search(
    wsi_features: np.ndarray,
    pca_components: list[int],
    cluster_counts: list[int],
    random_state: int,
    run_id: int,
) -> pd.DataFrame:
    wsi_features = np.asarray(wsi_features, dtype=np.float64)
    max_components = min(wsi_features.shape)
    invalid_components = [value for value in pca_components if value > max_components]
    if invalid_components:
        raise ValueError(
            f"PCA components {invalid_components} exceed the maximum {max_components}"
        )

    invalid_clusters = [value for value in cluster_counts if not 2 <= value < len(wsi_features)]
    if invalid_clusters:
        raise ValueError(
            f"Cluster counts {invalid_clusters} must be between 2 and "
            f"{len(wsi_features) - 1}"
        )

    max_requested_components = max(pca_components)
    pca = PCA(n_components=max_requested_components, svd_solver="full")
    all_reduced_features = pca.fit_transform(wsi_features)
    cumulative_explained_variance = np.cumsum(pca.explained_variance_ratio_)

    results = []
    for component_count in pca_components:
        reduced_features = np.ascontiguousarray(
            all_reduced_features[:, :component_count]
        )
        explained_variance = float(cumulative_explained_variance[component_count - 1])
        distances = squareform(pdist(reduced_features, metric="euclidean"))
        for cluster_count in cluster_counts:
            kmeans = KMeans(
                n_clusters=cluster_count,
                random_state=random_state,
                n_init=10,
            )
            # macOS Accelerate can raise false floating-point flags for finite,
            # accurate matrix products used by scikit-learn's k-means++ setup.
            with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
                labels = kmeans.fit_predict(reduced_features)

            if not np.isfinite(kmeans.cluster_centers_).all():
                raise FloatingPointError("K-Means produced non-finite cluster centers")
            if not np.isfinite(kmeans.inertia_):
                raise FloatingPointError("K-Means produced non-finite inertia")
            if len(np.unique(labels)) != cluster_count:
                raise ValueError(
                    f"K-Means produced {len(np.unique(labels))} clusters; "
                    f"expected {cluster_count}"
                )
            cluster_sizes = np.bincount(labels, minlength=cluster_count)
            results.append({
                "pca_components": component_count,
                "kmeans_clusters": cluster_count,
                "pca_explained_var": explained_variance,
                "inertia": float(kmeans.inertia_),
                "silhouette": float(
                    silhouette_score(distances, labels, metric="precomputed")
                ),
                "min_cluster_size": int(cluster_sizes.min()),
                "max_cluster_size": int(cluster_sizes.max()),
                "cluster_size_ratio": float(
                    cluster_sizes.max() / cluster_sizes.min()
                ),
                "run": run_id,
                "random_state": random_state,
            })

    return pd.DataFrame(results)
