from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances, silhouette_samples, silhouette_score

from src.phase0_dataset_builder.sources import DEFAULT_PATCH_IMAGE_DIR, DIAGNOSIS_COLOR, SHORT_LABEL
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


TRAITS_NAME = "cluster_traits.csv"
TRAITS_VIEW_NAME = "cluster_traits.png"
TRAIT_STEPS_NAME = "cluster_trait_steps.png"
ZOOM_NAME = "cluster_zoom.csv"
SIFT_BACKED = ("by_eye_agrees_with_sift", "derived_from_sift")  # possible zooms that a SIFT scale of about 4x to a related picture supports
WHITE = 0.8  # a pixel whose three channels are all above this is background (glass), not tissue
SMALLEST_REGION = 20  # pixels: dark regions smaller than this are dropped as noise
TRAITS = {"background_share": "background (share of the patch)", "hematoxylin": "hematoxylin (purple stain)", "eosin": "eosin (pink stain)",
          "dark_region_diameter": "median diameter of the dark regions (pixels)", "dark_regions": "dark regions in the patch"}


def trait_masks(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, np.ndarray]:
    """The steps behind the traits of a patch: its RGB pixels, the tissue mask (not background glass), the hematoxylin channel of the colour
    deconvolution, Otsu's threshold on that channel over the tissue, and the dark regions: the connected pixels above the threshold, numbered 1, 2, ...
    Hematoxylin stains nuclei, so the dark regions could be nuclei or groups of touching nuclei; they were not checked as such."""
    from skimage.color import rgb2hed
    from skimage.filters import threshold_otsu
    from skimage.measure import label
    from skimage.morphology import remove_small_objects

    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255
    tissue = ~(rgb.min(axis=2) > WHITE)
    hed = rgb2hed(rgb)
    if tissue.sum() < SMALLEST_REGION:
        return rgb, tissue, hed, np.nan, np.zeros(tissue.shape, dtype=int)
    threshold = float(threshold_otsu(hed[..., 0][tissue]))
    regions = label(remove_small_objects(tissue & (hed[..., 0] > threshold), SMALLEST_REGION))
    return rgb, tissue, hed, threshold, regions


def patch_traits(path: Path) -> dict[str, float]:
    """Simple measures of how a patch looks: how much of it is background, how strong the two stains are on the tissue, and the size and number of the
    dark regions (see ``trait_masks``). The size of a region is its equivalent diameter, the diameter of a circle with the same area, sqrt(4 area / pi);
    in pixels it grows with the zoom of the picture."""
    _, tissue, hed, _, regions = trait_masks(path)
    traits = {"background_share": float(1 - tissue.mean()), "hematoxylin": np.nan, "eosin": np.nan, "dark_region_diameter": np.nan, "dark_regions": 0.0}
    if tissue.sum() < SMALLEST_REGION:
        return traits
    traits["hematoxylin"], traits["eosin"] = float(hed[..., 0][tissue].mean()), float(hed[..., 1][tissue].mean())
    areas = np.bincount(regions.ravel())[1:]
    if len(areas):
        traits["dark_region_diameter"], traits["dark_regions"] = float(np.median(np.sqrt(4 * areas / np.pi))), float(len(areas))
    return traits


def draw_trait_row(row, path: Path, name: str, display_px: int | None = None) -> None:
    """Five panels on one row of axes: the image, its hematoxylin channel, the pixels above Otsu's threshold, the dark regions that are kept (outlined on
    the image), and the background mask. The masks are computed on the full image; ``display_px`` only shrinks what is drawn (longest side)."""
    from skimage.segmentation import find_boundaries

    rgb, tissue, hed, threshold, regions = trait_masks(path)
    diameters = np.sqrt(4 * np.bincount(regions.ravel())[1:] / np.pi)
    outlined = rgb.copy()
    outlined[find_boundaries(regions)] = (1.0, 0.85, 0.0)
    step = max(1, max(rgb.shape[:2]) // display_px) if display_px else 1
    panels = [
        (rgb, None, name),
        (hed[..., 0], "Purples", "hematoxylin channel (dark = more stain)"),
        (tissue & (hed[..., 0] > threshold), "gray_r", f"above Otsu's threshold ({threshold:.3f})"),
        (outlined, None, f"{len(diameters)} dark regions kept, median diameter {np.median(diameters) if len(diameters) else 0:.0f} px"),
        (~tissue, "gray_r", f"background: {1 - tissue.mean():.0%} of the image"),
    ]
    for ax, (image, cmap, title) in zip(row, panels):
        ax.imshow(image[::step, ::step], cmap=cmap, interpolation="nearest" if cmap == "gray_r" else "antialiased")
        ax.set_title(title, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])


def render_trait_steps(paths: dict[str, Path], output: Path) -> None:
    """For each patch (one row): what the traits measure, step by step (see ``draw_trait_row``)."""
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(len(paths), 5, figsize=(17, 3.6 * len(paths)), constrained_layout=True, squeeze=False)
    for row, (name, path) in zip(axes, paths.items()):
        draw_trait_row(row, path, f"{name}: the patch")
    figure.savefig(output, dpi=110)
    plt.close(figure)


def cramers_v(rows: pd.Series, columns: pd.Series) -> tuple[pd.DataFrame, float, float]:
    """The contingency table of two labellings, Cramér's V (0 = independent, 1 = one fixes the other) and the p-value of the chi-squared test."""
    from scipy.stats import chi2_contingency

    table = pd.crosstab(rows, columns)
    chi2, p, _, _ = chi2_contingency(table, correction=False)  # no Yates correction on 2x2 tables, so V is the same measure on every table
    return table, float(np.sqrt(chi2 / (table.to_numpy().sum() * (min(table.shape) - 1)))), float(p)


def zoom_association(traits: pd.DataFrame) -> pd.DataFrame:
    """How the possible zoom goes with the cluster and with the label, for all pictures and for the SIFT-backed ones only. The zoom belongs to the
    picture, so the patches of one picture are not independent: Cramér's V is given on patches and on pictures (the cluster most of its patches fall
    in, its NDB-UFES diagnosis), the p-value only on pictures. Within each patch label, cluster against zoom tells whether the clusters follow the
    zoom by themselves or only through the label."""
    traits = traits[traits["possible_zoom"] != ""]
    pictures = traits.groupby("histopath_id").agg(possible_zoom=("possible_zoom", "first"), zoom_evidence=("zoom_evidence", "first"),
                                                  cluster=("cluster", lambda c: c.mode().iloc[0]), ndb_diagnosis=("ndb_diagnosis", "first"))
    pictures["ndb_diagnosis"] = pictures["ndb_diagnosis"].replace("", NOT_IN_NDB)
    rows = []
    for subset in ("all", "sift_backed"):
        patches_in = traits if subset == "all" else traits[traits["zoom_evidence"].isin(SIFT_BACKED)]
        pictures_in = pictures if subset == "all" else pictures[pictures["zoom_evidence"].isin(SIFT_BACKED)]
        comparisons = [("patches", "cluster", patches_in), ("patches", "patch_diagnosis", patches_in),
                       ("pictures", "cluster", pictures_in), ("pictures", "ndb_diagnosis", pictures_in)]
        comparisons += [("patches", f"cluster within {SHORT_LABEL[label]}", patches_in[patches_in["patch_diagnosis"] == label]) for label in CLASSES]
        for unit, against, data in comparisons:
            table, v, p = cramers_v(data[against.split(" within ")[0]], data["possible_zoom"])
            logger.info(f"{subset}, {unit}: {against} against possible zoom (Cramér's V {v:.2f}" + (f", p {p:.2g})" if unit == "pictures" else ")") + f"\n{table.to_string()}")
            rows.append({"subset": subset, "unit": unit, "against": against, "n": int(table.to_numpy().sum()), "cramers_v": round(v, 3),
                         "p_value": p if unit == "pictures" else np.nan})
    return pd.DataFrame(rows)


def render_cluster_traits(traits: pd.DataFrame, output: Path) -> None:
    """One box plot per trait (each cluster split by patch label), the median dark-region diameter of each picture, and the share of patches at a possible 40x
    in each cluster, split by patch label."""
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 4, figsize=(18, 8.5), constrained_layout=True)
    clusters = sorted(traits["cluster"].unique())
    width = 0.8 / len(CLASSES)
    for ax, (column, title) in zip(axes.flat, TRAITS.items()):
        for k, label in enumerate(CLASSES):
            values = [traits.loc[(traits["cluster"] == c) & (traits["patch_diagnosis"] == label), column].dropna() for c in clusters]
            ax.boxplot(values, positions=np.arange(len(clusters)) + (k - 1) * width, widths=width * 0.9, showfliers=False, patch_artist=True,
                       boxprops={"facecolor": DIAGNOSIS_COLOR[label], "alpha": 0.6}, medianprops={"color": "black"})
        ax.set_xticks(range(len(clusters)), [f"cluster {c}" for c in clusters])
        ax.set_title(title)
        if column == "dark_region_diameter":
            ax.set_yscale("log")
    for label in CLASSES:
        axes.flat[5].scatter([], [], color=DIAGNOSIS_COLOR[label], label=SHORT_LABEL[label])
    axes.flat[5].legend(title="patch label", loc="center")
    axes.flat[5].axis("off")

    pictures = traits.groupby("histopath_id").agg(diameter=("dark_region_diameter", "median"), cluster=("cluster", lambda c: c.mode().iloc[0]))
    bins = np.logspace(np.log10(pictures["diameter"].min()), np.log10(pictures["diameter"].max()), 30)
    for c in clusters:
        axes.flat[6].hist(pictures.loc[pictures["cluster"] == c, "diameter"], bins=bins, alpha=0.6, label=f"cluster {c} (most of its patches)")
    axes.flat[6].set_xscale("log")
    axes.flat[6].set_title("median dark-region diameter of each picture")
    axes.flat[6].set_xlabel("pixels (log scale)")
    axes.flat[6].legend(fontsize=8)

    share = traits[traits["possible_zoom"] != ""].groupby(["cluster", "patch_diagnosis"])["possible_zoom"].apply(lambda z: (z == "40x").mean() * 100)
    share = share.unstack().reindex(index=clusters, columns=list(CLASSES))
    for k, label in enumerate(CLASSES):
        axes.flat[7].bar(np.arange(len(clusters)) + (k - 1) * width, share[label], width=width * 0.9, color=DIAGNOSIS_COLOR[label], alpha=0.6)
    axes.flat[7].axhline((traits["possible_zoom"] == "40x").mean() * 100, color="grey", linestyle="--", linewidth=1, label="all patches")
    axes.flat[7].set_xticks(range(len(clusters)), [f"cluster {c}" for c in clusters])
    axes.flat[7].set_ylim(0, 100)
    axes.flat[7].set_title("patches at a possible 40x (%)")
    axes.flat[7].legend(fontsize=8)
    figure.savefig(output, dpi=130)
    plt.close(figure)


def run_cluster_traits(args: argparse.Namespace) -> dict:
    from scipy.stats import spearmanr

    output_dir = Path(args.output_dir)
    patches = pd.read_csv(args.patch_table, dtype=str, keep_default_na=False).set_index("patch_id")
    clusters = pd.read_csv(output_dir / CLUSTERS_NAME, dtype={"patch_id": str}).set_index("patch_id")[f"cluster_k{args.clusters}"]
    patch_ids, matrix = load_embeddings(args.embeddings)
    axes = pd.DataFrame(reduce_embeddings(matrix, 2), columns=["pc1", "pc2"], index=pd.Index(patch_ids, name="patch_id"))

    centre = axes.loc[clusters.index].groupby(clusters).transform("mean")
    distance = np.hypot(*(axes.loc[clusters.index] - centre).to_numpy().T)
    typical = pd.Series(distance, index=clusters.index).groupby(clusters).idxmin()  # the patch closest to the centre of each cluster
    render_trait_steps({f"cluster {c}": args.patch_images / f"{patch_id}.png" for c, patch_id in typical.items()}, output_dir / TRAIT_STEPS_NAME)
    logger.info(f"Wrote {output_dir / TRAIT_STEPS_NAME}: the steps of the measures on the most typical patch of each cluster")

    rows = []
    for n, patch_id in enumerate(clusters.index, start=1):
        rows.append({"patch_id": patch_id, **patch_traits(args.patch_images / f"{patch_id}.png")})
        if n % 500 == 0:
            logger.info(f"Measured {n} of {len(clusters)} patches")
    traits = pd.DataFrame(rows).set_index("patch_id").join(clusters.rename("cluster")).join(patches[["patch_diagnosis", "histopath_id", "ndb_diagnosis", "possible_zoom", "zoom_evidence"]]).join(axes)
    traits.round(4).to_csv(output_dir / TRAITS_NAME)

    logger.info(f"Median of each trait by cluster:\n{traits.groupby('cluster')[list(TRAITS)].median().round(3).to_string()}")
    logger.info(f"Median of each trait by cluster and patch label:\n{traits.groupby(['cluster', 'patch_diagnosis'])[list(TRAITS)].median().round(3).to_string()}")
    correlation = pd.DataFrame({axis: {trait: spearmanr(traits[trait], traits[axis], nan_policy='omit')[0] for trait in TRAITS} for axis in ("pc1", "pc2")})
    logger.info(f"Spearman correlation of each trait with the two PCA components (what the axes of the cluster picture stand for):\n{correlation.round(2).to_string()}")

    logger.info(f"Median of each trait by possible zoom:\n{traits.groupby('possible_zoom')[list(TRAITS)].median().round(3).to_string()}")

    zoom = zoom_association(traits)
    zoom.to_csv(output_dir / ZOOM_NAME, index=False)
    render_cluster_traits(traits, output_dir / TRAITS_VIEW_NAME)
    logger.info(f"Outputs saved under {output_dir}")
    picture_v = zoom.query("subset == 'all' and unit == 'pictures' and against == 'cluster'")["cramers_v"].item()
    return {"patches": len(traits), "cluster_zoom_cramers_v_pictures": picture_v, "table": str(output_dir / ZOOM_NAME), "picture": str(output_dir / TRAITS_VIEW_NAME)}


def cluster_traits_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure simple traits of every patch (background, stains, size and count of the dark regions) and compare them across the clusters.")
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--patch-table", type=Path, default=DEFAULT_PATCH_TABLE)
    parser.add_argument("--patch-images", type=Path, default=DEFAULT_PATCH_IMAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CLUSTER_DIR)
    parser.add_argument("--clusters", type=int, default=3, help="Which clustering of patch_clusters.csv to describe.")
    return parser
