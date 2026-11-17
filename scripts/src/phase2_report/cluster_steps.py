"""Figures that explain PCA and k-means on the real patch embeddings (Virchow), for the slides and the thesis.

Three figures, written to the folder given to the slides command:
- ``pca_toy.png``: how PCA is calculated, on made-up points in two dimensions (2,560 dimensions cannot be drawn): the points and their mean, the centered points with
  their two components, one point and its shadow on the first component, and every point as its two PCA numbers.
- ``pca_steps.png``: the share of the variation of the embeddings held by each of the first PCA components, and the patches in the plane of the first two.
- ``kmeans_steps.png``: k-means in that plane, round by round: the starting centers (k-means++), the first assignment with where the centers move, and the final clusters.
- ``silhouette_toy.png``: how the silhouette of one point is calculated, on made-up clusters: a well-placed point and a point on a border, each with the distances
  to its own cluster (a) and to the nearest other cluster (b).
- ``silhouette_steps.png``: the silhouette of every patch for the folds' morphology clusters, sorted within each cluster, with their mean.

The run drawn here starts from one k-means++ start with the seed of the folds. The clustering used for the folds keeps the best of 10 starts, so the two are compared
and the share of patches on which they agree is logged and returned.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
from sklearn.cluster import kmeans_plusplus
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from src.phase1_folds.clusters import PCA_COMPONENTS, by_size, kmeans_labels, load_embeddings, reduce_embeddings  # noqa: E402
from src.phase1_folds.embeddings import EMBEDDINGS  # noqa: E402
from src.phase2_report.figures import CHOSEN_CLUSTERS, CHOSEN_PCA, CLUSTER_COLOR  # noqa: E402
from src.utils.logger import logger  # noqa: E402

SEED = 42  # the seed of the clustering used for the folds
DARK = "#3a3a3a"  # text in dark gray, as on the other slide figures
POINT = "#b8bcc4"  # a patch before it belongs to a cluster
STYLE = {"text.color": DARK, "axes.labelcolor": DARK, "xtick.color": DARK, "ytick.color": DARK, "axes.edgecolor": DARK, "axes.titleweight": "normal"}
ACCENT = "#e34948"  # the mean, and the one point followed through the PCA explanation
TOY_SEED = 0  # the made-up points of the PCA explanation are drawn the same way on every run
TOY_MEAN, TOY_ANGLE, TOY_SPREAD = np.array([6.0, 4.0]), np.deg2rad(35), (2.0, 0.45)  # a long thin cloud, away from the origin, along a diagonal


def toy_points(n: int = 80) -> np.ndarray:
    """Made-up points in two dimensions that vary together: spread widely along a diagonal and little across it."""
    rng = np.random.default_rng(TOY_SEED)
    along = np.array([np.cos(TOY_ANGLE), np.sin(TOY_ANGLE)])
    across = np.array([-along[1], along[0]])
    return TOY_MEAN + rng.normal(0, TOY_SPREAD[0], n)[:, None] * along + rng.normal(0, TOY_SPREAD[1], n)[:, None] * across


def toy_pca(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """PCA written out, step by step: the mean, the centered points, the eigenvalues and eigenvectors of the covariance matrix (largest first, each pointing to the
    right), and the projection of every point (one dot product per component)."""
    mean = points.mean(axis=0)
    centered = points - mean
    covariance = centered.T @ centered / (len(points) - 1)
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    vectors = vectors * np.where(vectors[0] < 0, -1, 1)
    if np.linalg.det(vectors) < 0:  # component 2 a quarter turn counterclockwise from component 1, so the PCA plane is the same picture only turned
        vectors[:, 1] *= -1
    return mean, centered, values, vectors, centered @ vectors


def pca_toy_figure(path: Path) -> dict:
    """Four panels on made-up points: the points and their mean, the centered points with the two components, one point and its shadow on component 1, and
    every point as its two PCA numbers. The shares of the variation are checked against scikit-learn's PCA."""
    points = toy_points()
    mean, centered, values, vectors, z = toy_pca(points)
    share = values / values.sum() * 100
    if not np.allclose(share, PCA(n_components=2).fit(points).explained_variance_ratio_ * 100):
        raise ValueError("The PCA written out does not agree with scikit-learn")
    chosen = int(np.argmax(np.where(np.abs(z[:, 1]) > 0.4, z[:, 0], -np.inf)))  # far along component 1 and visibly off it, so the drop to its shadow shows
    point, shadow = centered[chosen], z[chosen, 0] * vectors[:, 0]
    reach = float(np.abs(np.vstack([centered, z])).max()) + 0.8
    component_color = [CLUSTER_COLOR[0], CLUSTER_COLOR[1]]
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 4, figsize=(18, 4.9))
        axes[0].scatter(points[:, 0], points[:, 1], s=14, alpha=0.6, linewidths=0, color=DARK)
        axes[0].scatter(*mean, s=150, marker="X", color=ACCENT, edgecolors="white", linewidths=1, zorder=3)
        axes[0].annotate("", xy=(0, 0), xytext=mean, arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 1.6})
        axes[0].text(mean[0] * 0.6, 0.4, "subtract\nthe mean", color=ACCENT, fontsize=11, va="top")  # below the arrow, where there are no points
        high = float(points.max()) + 1
        middle = (points[:, 1].min() + points[:, 1].max()) / 2
        axes[0].set_xlim(-1.5, high)
        axes[0].set_ylim(middle - (high + 1.5) / 2, middle + (high + 1.5) / 2)  # as wide as tall, so the panel has the size of the others
        axes[0].set_title("1. The points and their mean", fontsize=12)
        axes[1].scatter(centered[:, 0], centered[:, 1], s=14, alpha=0.6, linewidths=0, color=DARK)
        for k in range(2):
            tip = 2 * np.sqrt(values[k]) * vectors[:, k]
            axes[1].axline((0, 0), vectors[:, k], color=component_color[k], lw=0.8, ls="--")
            axes[1].annotate("", xy=tip, xytext=(0, 0), arrowprops={"arrowstyle": "->", "color": component_color[k], "lw": 2.2})
            axes[1].text(0.03, 0.11 - 0.07 * k, f"component {k + 1}: {share[k]:.0f}% of the variation", color=component_color[k], fontsize=10.5,
                         transform=axes[1].transAxes)  # in the empty lower-left corner, not on the points
        axes[1].set_title("2–3. Centered, with the directions\nof most spread", fontsize=12)
        axes[2].scatter(centered[:, 0], centered[:, 1], s=14, alpha=0.25, linewidths=0, color=DARK)
        axes[2].axline((0, 0), vectors[:, 0], color=component_color[0], lw=0.8, ls="--")
        axes[2].annotate("", xy=shadow, xytext=(0, 0), arrowprops={"arrowstyle": "->", "color": component_color[0], "lw": 2.2})
        axes[2].plot(*np.column_stack([point, shadow]), color=ACCENT, lw=1.2, ls=":")
        axes[2].scatter(*point, s=60, color=ACCENT, zorder=3)
        axes[2].scatter(*shadow, s=40, color=component_color[0], zorder=3)
        axes[2].text(0.97, 0.05, f"$z_1 = {z[chosen, 0]:.2f}$: the length of the arrow\nfrom the origin to the shadow", color=component_color[0], fontsize=10.5,
                     ha="right", transform=axes[2].transAxes)  # in the empty lower-right corner
        axes[2].set_title("4. One point and its shadow\non component 1", fontsize=12)
        axes[3].scatter(z[:, 0], z[:, 1], s=14, alpha=0.6, linewidths=0, color=DARK)
        axes[3].scatter(z[chosen, 0], z[chosen, 1], s=60, color=ACCENT, zorder=3)
        axes[3].set_title("Every point as its two\nPCA numbers $(z_1, z_2)$", fontsize=12)
        for axis in axes[1:]:
            axis.set_xlim(-reach, reach)
            axis.set_ylim(-reach, reach)
        for axis in axes:
            axis.axhline(0, color=POINT, lw=0.8, zorder=0)
            axis.axvline(0, color=POINT, lw=0.8, zorder=0)
            axis.set_aspect("equal")
            axis.spines[["top", "right"]].set_visible(False)
        for axis in axes[:3]:
            axis.set_xlabel("dimension 1")
        axes[0].set_ylabel("dimension 2")
        axes[3].set_xlabel("component 1 ($z_1$)")
        axes[3].set_ylabel("component 2 ($z_2$)")
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"pca toy: components hold {share[0]:.1f}% and {share[1]:.1f}% of the variation, the followed point has z = ({z[chosen, 0]:.2f}, {z[chosen, 1]:.2f}), written to {path}")
    return {"pca_toy_shares": f"{share[0]:.1f}% / {share[1]:.1f}%"}


def lloyd_rounds(points: np.ndarray, centers: np.ndarray) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """The rounds of k-means from the given centers, until the assignments stop changing. Each round: the cluster of every point, the centers it started from, and
    the centers after moving each one to the mean of its points."""
    rounds, labels = [], None
    while True:
        distances = ((points[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new = distances.argmin(axis=1)
        if labels is not None and (new == labels).all():
            return rounds
        if len(np.unique(new)) != len(centers):
            raise ValueError("A k-means round left a cluster empty")
        labels = new
        moved = np.stack([points[labels == j].mean(axis=0) for j in range(len(centers))])
        rounds.append((labels, centers, moved))
        centers = moved


def pca_figure(matrix: np.ndarray, plane: np.ndarray, path: Path) -> float:
    """Left: the share of the variation held by each component, up to the most components tried for the clusters. Right: the patches in the plane of the first two.
    Returns the share held by the first two components."""
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        share = PCA(n_components=max(PCA_COMPONENTS), svd_solver="full").fit(matrix.astype(np.float64)).explained_variance_ratio_ * 100
    first_two = float(share[:CHOSEN_PCA].sum())
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.2, 1]})
        positions = np.arange(1, len(share) + 1)
        axes[0].bar(positions, share, color=[DARK if p <= CHOSEN_PCA else POINT for p in positions])
        axes[0].set_xlabel("PCA component")
        axes[0].set_ylabel("Share of the variation (%)")
        axes[0].set_title(f"Variation held by each component\n(the first two hold {first_two:.1f}%)", fontsize=12)
        axes[1].scatter(plane[:, 0], plane[:, 1], s=4, alpha=0.5, linewidths=0, color=DARK, rasterized=True)
        axes[1].set_xlabel(f"PCA component 1 ({share[0]:.1f}%)")
        axes[1].set_ylabel(f"PCA component 2 ({share[1]:.1f}%)")
        axes[1].set_title(f"The {len(plane):,} patches on the first two components", fontsize=12)
        for axis in axes:
            axis.spines[["top", "right"]].set_visible(False)
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"pca: {matrix.shape[1]} numbers per patch, the first two components hold {first_two:.1f}% of the variation, written to {path}")
    return first_two


def kmeans_figure(plane: np.ndarray, rounds: list, order: np.ndarray, path: Path) -> None:
    """Three panels in the PCA plane: the starting centers, the first round (assignment and the move of each center), and the last round. ``order`` turns the
    cluster numbers of the drawn run into the numbers of the folds' clusters, so the colors are the same as in the chapter's cluster figure."""
    colors = np.array(CLUSTER_COLOR)
    first_labels, start, first_moved = rounds[0]
    last_labels, _, final = rounds[-1]
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharex=True, sharey=True)
        axes[0].scatter(plane[:, 0], plane[:, 1], s=4, alpha=0.5, linewidths=0, color=POINT, rasterized=True)
        axes[0].scatter(start[:, 0], start[:, 1], s=160, marker="X", color=colors[order], edgecolors=DARK, linewidths=1.2, zorder=3)
        axes[0].set_title(f"Start: {len(start)} centers chosen with k-means++", fontsize=12)
        axes[1].scatter(plane[:, 0], plane[:, 1], s=4, alpha=0.5, linewidths=0, color=colors[order[first_labels]], rasterized=True)
        for old, new in zip(start, first_moved):
            axes[1].annotate("", xy=new, xytext=old, arrowprops={"arrowstyle": "->", "color": DARK, "lw": 1.6}, zorder=4)
        axes[1].scatter(first_moved[:, 0], first_moved[:, 1], s=160, marker="X", color=colors[order], edgecolors=DARK, linewidths=1.2, zorder=3)
        axes[1].set_title("Round 1: each patch goes to its nearest center,\nand each center moves to the mean of its patches", fontsize=12)
        axes[2].scatter(plane[:, 0], plane[:, 1], s=4, alpha=0.5, linewidths=0, color=colors[order[last_labels]], rasterized=True)
        axes[2].scatter(final[:, 0], final[:, 1], s=160, marker="X", color=colors[order], edgecolors=DARK, linewidths=1.2, zorder=3)
        axes[2].set_title(f"Round {len(rounds)}: the assignments stop changing", fontsize=12)
        for axis in axes:
            axis.set_xlabel("PCA component 1")
            axis.spines[["top", "right"]].set_visible(False)
        axes[0].set_ylabel("PCA component 2")
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"kmeans: {len(rounds)} rounds from the k-means++ start (seed {SEED}), written to {path}")


def a_and_b(points: np.ndarray, labels: np.ndarray, i: int) -> tuple[float, float, int]:
    """The silhouette parts of one point, written out: its mean distance to the other points of its own cluster (a), its mean distance to the points of the
    nearest other cluster (b), and which cluster that is."""
    distances = np.linalg.norm(points - points[i], axis=1)
    own = (labels == labels[i]) & (np.arange(len(points)) != i)
    others = {c: float(distances[labels == c].mean()) for c in np.unique(labels) if c != labels[i]}
    nearest = min(others, key=others.get)
    return float(distances[own].mean()), others[nearest], int(nearest)


def silhouette_toy_figure(path: Path) -> dict:
    """Two panels on made-up clusters (grouped with the same k-means as the patches): the best-placed point and the point closest to a border, each with a line to
    every point of its own cluster (a) and, dashed, to every point of the nearest other cluster (b). The written-out values are checked against scikit-learn."""
    rng = np.random.default_rng(TOY_SEED)
    points = np.vstack([center + rng.normal(0, 0.9, (14, 2)) for center in ([0.0, 0.0], [4.5, 0.5], [2.0, 4.5])])
    labels = by_size(kmeans_labels(points, CHOSEN_CLUSTERS, SEED))
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        s = silhouette_samples(points, labels)
    shown = {"Well placed": int(np.argmax(s)), "On a border": int(np.argmin(np.abs(s)))}
    with plt.rc_context(STYLE):
        figure, axes = plt.subplots(1, 2, figsize=(12, 5.6), sharex=True, sharey=True)
        for axis, (title, i) in zip(axes, shown.items()):
            a, b, nearest = a_and_b(points, labels, i)
            if not np.isclose((b - a) / max(a, b), s[i]):
                raise ValueError("The silhouette written out does not agree with scikit-learn")
            for j in np.flatnonzero((labels == labels[i]) & (np.arange(len(points)) != i)):
                axis.plot(*np.column_stack([points[i], points[j]]), color=CLUSTER_COLOR[labels[i]], lw=0.8, alpha=0.6, zorder=1)
            for j in np.flatnonzero(labels == nearest):
                axis.plot(*np.column_stack([points[i], points[j]]), color=CLUSTER_COLOR[nearest], lw=0.8, alpha=0.6, ls="--", zorder=1)
            axis.scatter(points[:, 0], points[:, 1], s=28, color=[CLUSTER_COLOR[label] for label in labels], edgecolors="white", linewidths=0.6, zorder=2)
            axis.scatter(*points[i], s=130, color=ACCENT, edgecolors="white", linewidths=1, zorder=3)
            axis.set_title(f"{title}: $a = {a:.2f}$, $b = {b:.2f}$\n$s = (b - a) / \\max(a, b) = {s[i]:.2f}$", fontsize=12)
            axis.set_aspect("equal")
            axis.spines[["top", "right"]].set_visible(False)
            axis.set_xlabel("dimension 1")
        axes[0].set_ylabel("dimension 2")
        figure.text(0.5, -0.05, "solid lines: distances to its own cluster (their mean is $a$)    dashed lines: distances to the nearest other cluster (their mean is $b$)",
                    ha="center", fontsize=10.5)
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"silhouette toy: s = {s[shown['Well placed']]:.2f} (well placed) and {s[shown['On a border']]:.2f} (border), written to {path}")
    return {"silhouette_toy": f"{s[shown['Well placed']]:.2f} / {s[shown['On a border']]:.2f}"}


def silhouette_figure(plane: np.ndarray, used: np.ndarray, path: Path) -> dict:
    """The silhouette of every patch for the folds' clusters, in the plane they were made in: one band per cluster, sorted, and the mean as a dashed line."""
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        s = silhouette_samples(plane, used)
    if not np.isfinite(s).all():
        raise FloatingPointError("The silhouettes of the patches are not finite")
    mean, below = float(s.mean()), float((s < 0).mean())
    with plt.rc_context(STYLE):
        figure, axis = plt.subplots(figsize=(9, 5.6))
        start, ticks, names = 0, [], []
        for cluster in range(CHOSEN_CLUSTERS):
            values = np.sort(s[used == cluster])
            axis.fill_betweenx(np.arange(start, start + len(values)), 0, values, color=CLUSTER_COLOR[cluster], linewidth=0)
            ticks.append(start + len(values) / 2)
            names.append(f"cluster {cluster}\n{len(values):,} patches")
            start += len(values) + 60  # a gap between the clusters
        axis.axvline(mean, color=ACCENT, ls="--", lw=1.6)  # named in the title, so no label sits on the bands
        axis.axvline(0, color=DARK, lw=0.8)
        axis.set_yticks(ticks, names)
        axis.set_xlim(min(float(s.min()), 0) - 0.05, 1)
        axis.set_xlabel("silhouette $s$ of each patch")
        axis.set_title(f"Silhouette of each patch, by morphology cluster\nmean {mean:.2f} (dashed red line), {below:.1%} of the patches below 0", fontsize=12)
        axis.spines[["top", "right"]].set_visible(False)
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figure)
    logger.info(f"silhouette: mean {mean:.3f} for the folds' clusters (seed {SEED}), {below:.1%} of the patches below 0, written to {path}")
    return {"silhouette_mean": round(mean, 3), "silhouette_below_zero": round(below, 4)}


def cluster_steps(out: Path, embeddings: Path = EMBEDDINGS) -> dict:
    toy = pca_toy_figure(out / "pca_toy.png")
    _, matrix = load_embeddings(embeddings)
    plane = reduce_embeddings(matrix, CHOSEN_PCA)  # the plane the folds' clusters were made in
    first_two = pca_figure(matrix, plane, out / "pca_steps.png")

    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):  # the same harmless Mac maths-library warnings that kmeans_labels silences
        start, _ = kmeans_plusplus(plane, n_clusters=CHOSEN_CLUSTERS, random_state=SEED)
    if not np.isfinite(start).all():
        raise FloatingPointError("The k-means++ start is not finite")
    rounds = lloyd_rounds(plane, start)
    last_labels = rounds[-1][0]
    order = np.argsort(np.argsort(-np.bincount(last_labels, minlength=CHOSEN_CLUSTERS), kind="stable"))  # drawn cluster -> its size rank, as by_size numbers clusters
    used = by_size(kmeans_labels(plane, CHOSEN_CLUSTERS, SEED))
    agreement = float((order[last_labels] == used).mean())
    if agreement < 0.99:
        logger.warning(f"The drawn k-means run agrees with the folds' clusters on only {agreement:.1%} of the patches")
    kmeans_figure(plane, rounds, order, out / "kmeans_steps.png")
    toy |= silhouette_toy_figure(out / "silhouette_toy.png") | silhouette_figure(plane, used, out / "silhouette_steps.png")
    return {"embedding_numbers": int(matrix.shape[1]), "pca_first_two_share": round(first_two, 1), "kmeans_rounds": len(rounds),
            "kmeans_agreement_with_folds": round(agreement, 4)} | toy
