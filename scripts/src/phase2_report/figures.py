"""Stage figures: the SVG charts of the wiki, drawn from the published tables and the statistics tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.phase0_dataset_builder.sources import AGE_GROUP_YEARS, DIAGNOSIS_COLOR, SEVERITY
from src.phase1_folds.clusters import load_embeddings, reduce_embeddings
from src.phase1_folds.embeddings import EMBEDDINGS
from src.utils.logger import logger


TABLES = Path("results/phase0/dataset_tables")
FOLDS = Path("results/phase1/folds")
CLUSTER_DIR = Path("results/phase1/clusters")
STATS = Path("results/phase2/tables")
OUTPUT_DIR = Path("docs/assets/figures")
LABELS = [diagnosis.value for diagnosis, _ in sorted(SEVERITY.items(), key=lambda item: item[1])]  # from least to most severe
COLORS = [DIAGNOSIS_COLOR[label] for label in LABELS]
NOT_IN_NDB = "not in NDB-UFES"
FOLD_SET_COLOR = {"new folds": "#2a9d8f", "original folds": "#e9c46a"}
CLUSTER_COLOR = ["#7b6fd6", "#2a9d8f", "#d4a017"]
FOLD_COLOR = ["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#e45756", "#72b7b2"]
CHOSEN_PCA, CHOSEN_CLUSTERS = 2, 3  # the clustering that is used
TEXT = "#8a8f98"  # readable on both the light and the dark wiki theme; the charts have no background
BAR = "#5b8fb9"

plt.rcParams.update({
    "svg.fonttype": "none", "svg.hashsalt": "ndb-ufes", "font.size": 9, "text.color": TEXT, "axes.labelcolor": TEXT, "xtick.color": TEXT, "ytick.color": TEXT,
    "axes.edgecolor": TEXT, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
    "legend.labelcolor": TEXT, "figure.facecolor": "none", "axes.facecolor": "none", "savefig.transparent": True,
})


def save(fig: plt.Figure, output_dir: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{name}.svg", format="svg", metadata={"Date": None}, dpi=150)
    plt.close(fig)
    logger.info(f"Wrote {output_dir / name}.svg")


def stacked_bars(ax: plt.Axes, table: pd.DataFrame) -> None:
    """One horizontal bar per row of ``table``, split by its columns, which are patch labels or diagnoses; each part shows its count and its share of the bar."""
    start = np.zeros(len(table))
    totals = table.sum(axis=1).to_numpy()
    for label, color in zip(LABELS, COLORS):
        values = table[label].to_numpy()
        positions = np.arange(len(table))
        ax.barh(positions, values, left=start, color=color, label=label)
        for position, value, offset, total in zip(positions, values, start, totals):
            if value >= totals.max() * 0.05:
                ax.text(offset + value / 2, position, f"{value:,} ({value / total:.0%})", ha="center", va="center", color="white", fontsize=8)
        start = start + values
    ax.set_yticks(np.arange(len(table)), list(table.index))
    ax.invert_yaxis()


def heatmap(matrix: pd.DataFrame, output_dir: Path, name: str) -> None:
    """Cramér's V between every two variables, from 0 (not tied) to 1 (one decides the other); the table is mirrored and the diagonal is a variable with itself."""
    matrix = matrix.set_index("variable")
    values = matrix.to_numpy(dtype=float)
    labels = [label.replace("_", " ") for label in matrix.columns]
    fig, ax = plt.subplots(figsize=(0.95 * len(matrix) + 2.6, 0.8 * len(matrix) + 1.8))
    image = ax.imshow(values, cmap="Blues", vmin=0, vmax=1)
    for (i, j), value in np.ndenumerate(values):
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9, color="white" if value > 0.5 else "black")
    ax.set_xticks(range(len(matrix)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix)), labels)
    ax.spines[:].set_visible(False)
    fig.colorbar(image, ax=ax, label="Cramér's V", pad=0.02, shrink=0.8)
    save(fig, output_dir, name)


def ndb_distributions(stats: Path, output_dir: Path) -> None:
    data = pd.read_csv(stats / "ndb_distributions.csv", dtype={"value": str})
    variables = list(dict.fromkeys(data["variable"]))
    rows = [variables[i:i + 2] for i in range(0, len(variables), 2)]  # two charts per row, tall rows for the variables with most values
    heights = [max(data["variable"].eq(variable).sum() for variable in row) for row in rows]
    fig, axes = plt.subplots(len(rows), 2, figsize=(10, 0.5 * sum(heights) + 1.8), gridspec_kw={"height_ratios": heights})
    for ax, variable in zip(axes.flat, variables):
        part = data[data["variable"] == variable]
        names = [f"{AGE_GROUP_YEARS[value]} (group {value})" if variable == "age_group" else value for value in part["value"]]
        ax.barh(names, part["images"], color=BAR)
        ax.invert_yaxis()
        ax.set_title(variable.replace("_", " "), fontsize=12)
        ax.tick_params(labelsize=11)
        for position, (count, share) in enumerate(zip(part["images"], part["share"])):
            ax.text(count, position, f" {count} ({share:.0%})", va="center", fontsize=11)
        ax.set_xlim(0, part["images"].max() * 1.45)
    save(fig, output_dir, "ndb_distributions")


def ndb_images_with_patches(stats: Path, output_dir: Path) -> None:
    data = pd.read_csv(stats / "ndb_images_with_patches.csv").set_index("diagnosis")
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.barh(data.index, data["with patches"], color=BAR, label="with patches")
    ax.barh(data.index, data["without patches"], left=data["with patches"], color="#c9ced6", label="without patches")
    for position, (a, b) in enumerate(zip(data["with patches"], data["without patches"])):
        ax.text(a / 2, position, f"{a} ({a / (a + b):.0%})", ha="center", va="center", color="white", fontsize=8)
        ax.text(a + b + 1, position, f"{b} ({b / (a + b):.0%})", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("NDB-UFES images")
    ax.set_xlim(0, (data["with patches"] + data["without patches"]).max() * 1.2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.45), ncol=3)
    save(fig, output_dir, "ndb_images_with_patches")


def patch_labels(patch: pd.DataFrame, output_dir: Path) -> None:
    """For the pictures of each NDB-UFES diagnosis, the share of their patches by patch label. Patches more severe than their picture are hatched."""
    with_diagnosis = patch[patch["ndb_diagnosis"] != ""]
    table = pd.crosstab(with_diagnosis["ndb_diagnosis"], with_diagnosis["patch_diagnosis"]).reindex(index=LABELS, columns=LABELS, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for row, (picture_label, counts) in enumerate(table.iterrows()):
        left = 0.0
        for severity, (label, color) in enumerate(zip(LABELS, COLORS)):
            share = counts[label] / counts.sum() * 100
            ax.barh(row, share, left=left, color=color, hatch="///" if severity > row else None, edgecolor="white", linewidth=0)
            if share >= 4:
                ax.text(left + share / 2, row, f"{counts[label]:,}\n{share:.0f}%", ha="center", va="center", color="white", fontsize=9, fontweight="bold",
                        bbox={"boxstyle": "round,pad=0.2", "facecolor": color, "edgecolor": "none"} if severity > row else None)
            left += share
    ax.set_yticks(range(len(table)), [f"Picture labeled\n{label}\n({table.loc[label].sum():,} patches)" for label in LABELS])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of the patches of those pictures, coloured by the patch label")
    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in COLORS] + [plt.Rectangle((0, 0), 1, 1, facecolor="#c9ced6", hatch="///", edgecolor="white")]
    ax.legend(handles, [*LABELS, "more severe than the picture"], loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    save(fig, output_dir, "patch_labels")


def sab_folders(stats: Path, output_dir: Path) -> None:
    data = pd.read_csv(stats / "sab_folder_vs_diagnosis.csv").set_index("sab_folders")
    data.index = [name.split(" (")[0] for name in data.index]
    fig, axes = plt.subplots(2, 1, figsize=(8, 4.2), gridspec_kw={"height_ratios": [2, 1]})
    stacked_bars(axes[0], data.iloc[:2])
    axes[0].set_title("Pictures in both datasets, by NDB-UFES diagnosis")
    stacked_bars(axes[1], data.iloc[2:])
    axes[1].set_title("benigno: patches by patch label")
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=3)
    save(fig, output_dir, "sab_folders")


def patches_per_picture(patch: pd.DataFrame, output_dir: Path) -> None:
    sizes = patch.groupby("histopath_id").size()
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.hist(sizes, bins=np.arange(0, sizes.max() + 3, 2), color=BAR, edgecolor="none")
    ax.axvline(sizes.median(), color=TEXT, linestyle="--")
    ax.text(sizes.median() + 0.5, ax.get_ylim()[1] * 0.92, f"median {sizes.median():.0f}", fontsize=8)
    ax.set_xlabel("Patches cut from one picture")
    ax.set_ylabel("Pictures")
    save(fig, output_dir, "patches_per_picture")


def related_zoom(stats: Path, output_dir: Path) -> None:
    data = pd.read_csv(stats / "related_pictures.csv")
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.hist(data["zoom_factor"], bins=np.arange(0.9, 5.0, 0.2), color=BAR, edgecolor="none")
    ax.set_xlabel("Zoom between two related pictures (1 means the same zoom)")
    ax.set_ylabel("Related pairs")
    ax.set_title(f"{int(data['zoomed'].sum())} of {len(data)} pairs differ in zoom")
    save(fig, output_dir, "related_zoom")


def share_gaps(summary: pd.DataFrame) -> pd.DataFrame:
    """For every value in every fold: its share of the fold's patches minus its share of all patches, in percentage points."""
    folds = summary[summary["fold"].isin([str(i) for i in range(6)])].set_index("fold").astype(float)
    total = summary.set_index("fold").loc["total"].astype(float)
    columns = [column for column in folds.columns if column not in ("groups", "patches", "benigno")]
    return folds[columns].div(folds["patches"], axis=0) * 100 - total[columns] / total["patches"] * 100


def fold_deviation(summary: pd.DataFrame, output_dir: Path) -> None:
    gap = share_gaps(summary)
    limit = 10
    fig, ax = plt.subplots(figsize=(12, 3.6))
    image = ax.imshow(gap.to_numpy().clip(-limit, limit), cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    for (i, j), value in np.ndenumerate(gap.to_numpy()):
        ax.text(j, i, f"{value:+.1f}", ha="center", va="center", fontsize=8, color="white" if abs(value) > 7 else "black")
    ax.set_xticks(range(len(gap.columns)), gap.columns, rotation=45, ha="right")
    ax.set_yticks(range(6), [f"fold {i}" for i in range(6)])
    ax.spines[:].set_visible(False)
    fig.colorbar(image, ax=ax, label="percentage points above (+) or below (−) the share in all folds", pad=0.01)
    save(fig, output_dir, "fold_deviation")


def fold_spread(stats: Path, output_dir: Path) -> None:
    """In how many folds the patches of one case, or of one picture, are found."""
    data = pd.read_csv(stats / "fold_spread.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    width = 0.38
    for ax, unit in zip(axes, ("cases", "parent pictures")):
        for k, (name, color) in enumerate(FOLD_SET_COLOR.items()):
            part = data[(data["fold_set"] == name) & (data["unit"] == unit)].set_index("folds")["units"].reindex(range(1, 7), fill_value=0)
            share = part / part.sum() * 100
            positions = np.arange(1, 7) + (k - 0.5) * width
            ax.bar(positions, share, width, color=color, label=name)
            for position, value in zip(positions, share):
                if value >= 1:
                    ax.text(position, value + 1, f"{value:.0f}%", ha="center", fontsize=8)
        ax.set_title(unit)
        ax.set_xlabel("In how many folds its patches are found")
        ax.set_ylim(0, 112)
    axes[0].set_ylabel("% of the units")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.1, -0.2), ncol=2)
    save(fig, output_dir, "fold_spread")


def fold_balance(stats: Path, output_dir: Path) -> None:
    """For each value of each balanced variable: how far apart the folds are, original folds against new folds."""
    data = pd.read_csv(stats / "fold_balance.csv", dtype={"value": str})
    order = data[data["fold_set"] == "new folds"][["variable", "value"]].reset_index(drop=True)
    names = [f"age group {AGE_GROUP_YEARS[v]}" if variable == "age group" and v in AGE_GROUP_YEARS else f"{variable} {v}" if variable == "age group" else f"{variable}: {v}" for variable, v in zip(order["variable"], order["value"])]
    fig, ax = plt.subplots(figsize=(8, 0.34 * len(order) + 1.8))
    height = 0.38
    for k, (name, color) in enumerate(FOLD_SET_COLOR.items()):
        part = data[data["fold_set"] == name].set_index(["variable", "value"])["spread_points"].reindex(list(zip(order["variable"], order["value"])))
        positions = np.arange(len(order)) + (k - 0.5) * height
        ax.barh(positions, part.to_numpy(), height, color=color, label=name)
        for position, value in zip(positions, part.to_numpy()):
            ax.text(value + 0.15, position, f"{value:.1f}", va="center", fontsize=8)
    ax.set_yticks(range(len(order)), names)
    ax.invert_yaxis()
    ax.set_xlabel("Spread in percentage points (highest share minus lowest)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    save(fig, output_dir, "fold_balance")


def embedding_frame(embeddings: Path, tables: Path, folds: Path, clusters: Path) -> pd.DataFrame:
    """Every patch with its first two PCA components, its label, its cluster, and its fold (empty for a dropped duplicate)."""
    patch_ids, matrix = load_embeddings(embeddings)
    coordinates = reduce_embeddings(matrix, CHOSEN_PCA)
    frame = pd.DataFrame(coordinates, columns=["pc1", "pc2"], index=pd.Index(patch_ids, name="patch_id"))
    frame["label"] = pd.read_csv(tables / "patch_table_public.csv", dtype=str).set_index("patch_id")["patch_diagnosis"]
    frame["cluster"] = pd.read_csv(clusters / "patch_clusters.csv", dtype=str).set_index("patch_id")["cluster_k3"].astype(int)
    frame["fold"] = pd.read_csv(folds / "fold_assignments.csv", dtype=str, keep_default_na=False).set_index("patch_id")["fold"]
    return frame


def embedding_view(frame: pd.DataFrame, output_dir: Path) -> None:
    """The same patches twice, in the plane of the first two PCA components: by patch label, and by morphology cluster."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharex=True, sharey=True)
    for label, color in zip(LABELS, COLORS):
        part = frame[frame["label"] == label]
        axes[0].scatter(part["pc1"], part["pc2"], s=6, alpha=0.5, linewidths=0, color=color, label=f"{label}: {len(part):,}", rasterized=True)
    axes[0].set_title("Coloured by patch label")
    for cluster, color in enumerate(CLUSTER_COLOR):
        part = frame[frame["cluster"] == cluster]
        axes[1].scatter(part["pc1"], part["pc2"], s=6, alpha=0.5, linewidths=0, color=color, label=f"cluster {cluster}: {len(part):,}", rasterized=True)
    axes[1].set_title("Coloured by morphology cluster")
    for ax in axes:
        ax.set_xlabel("PCA component 1")
        ax.legend(markerscale=3, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1)
    axes[0].set_ylabel("PCA component 2")
    save(fig, output_dir, "embedding_view")


def fold_distance_view(stats: Path, output_dir: Path) -> None:
    """How far apart every two folds are, for the original folds, the new folds and a random division of the patches, on one colour scale."""
    data = pd.read_csv(stats / "fold_distances.csv", dtype={"fold_a": str, "fold_b": str})
    sets = [("original folds", "folder"), ("new folds", "fold"), ("random division", "fold")]
    top = data["distance"].max()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    for ax, (name, word) in zip(axes, sets):
        part = data[data["fold_set"] == name]
        names = sorted(set(part["fold_a"]) | set(part["fold_b"]))
        matrix = np.zeros((len(names), len(names)))
        for row in part.itertuples():
            matrix[names.index(row.fold_a), names.index(row.fold_b)] = matrix[names.index(row.fold_b), names.index(row.fold_a)] = row.distance
        image = ax.imshow(matrix, cmap="Purples", vmin=0, vmax=top)
        for (i, j), value in np.ndenumerate(matrix):
            if i != j:
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9, color="white" if value > top * 0.6 else "black")
        ax.set_xticks(range(len(names)), names)
        ax.set_yticks(range(len(names)), names)
        ax.set_title(f"{name} (mean {part['distance'].mean():.2f})", fontsize=10)
        ax.set_xlabel(word)
        ax.spines[:].set_visible(False)
    fig.colorbar(image, ax=axes, label="Distance between two folds", shrink=0.8, pad=0.02)
    save(fig, output_dir, "fold_distances")


def cluster_choices(clusters: Path, output_dir: Path) -> None:
    """How well separated the clusters are (silhouette) for each number of PCA components and of clusters; cells whose clusters would be too small or too uneven are crossed out."""
    data = pd.read_csv(clusters / "cluster_choices.csv")
    silhouette = data.pivot(index="pca_components", columns="clusters", values="silhouette")
    acceptable = data.pivot(index="pca_components", columns="clusters", values="sizes_acceptable")
    fig, ax = plt.subplots(figsize=(8, 7))
    image = ax.imshow(silhouette.to_numpy(), cmap="Blues", vmin=0, vmax=silhouette.to_numpy().max(), aspect="auto")
    for (i, j), value in np.ndenumerate(silhouette.to_numpy()):
        usable = bool(acceptable.to_numpy()[i, j])
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9, color=("white" if value > 0.45 else "black") if usable else "#b0b5bd", fontstyle="normal" if usable else "italic")
    row, column = list(silhouette.index).index(CHOSEN_PCA), list(silhouette.columns).index(CHOSEN_CLUSTERS)
    ax.add_patch(plt.Rectangle((column - 0.5, row - 0.5), 1, 1, fill=False, edgecolor="#d62728", linewidth=2.5))
    ax.set_xticks(range(len(silhouette.columns)), silhouette.columns)
    ax.set_yticks(range(len(silhouette.index)), silhouette.index)
    ax.set_xlabel("Number of clusters")
    ax.set_ylabel("PCA components kept")
    ax.spines[:].set_visible(False)
    fig.colorbar(image, ax=ax, label="Silhouette (higher means better separated)", pad=0.02)
    save(fig, output_dir, "cluster_choices")


def run_figures(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    patch = pd.read_csv(args.tables / "patch_table_public.csv", dtype=str, keep_default_na=False)
    summary = pd.read_csv(args.folds / "fold_summary.csv", dtype=str, keep_default_na=False)
    frame = embedding_frame(args.embeddings, args.tables, args.folds, args.clusters)
    charts = [
        lambda: ndb_distributions(args.stats, output_dir), lambda: heatmap(pd.read_csv(args.stats / "ndb_correlations.csv"), output_dir, "ndb_correlations"), lambda: ndb_images_with_patches(args.stats, output_dir),
        lambda: patch_labels(patch, output_dir), lambda: heatmap(pd.read_csv(args.stats / "patch_correlations.csv"), output_dir, "patch_correlations"), lambda: sab_folders(args.stats, output_dir), lambda: patches_per_picture(patch, output_dir), lambda: related_zoom(args.stats, output_dir),
        lambda: embedding_view(frame, output_dir), lambda: fold_distance_view(args.stats, output_dir), lambda: cluster_choices(args.clusters, output_dir),
        lambda: fold_deviation(summary, output_dir), lambda: fold_spread(args.stats, output_dir), lambda: fold_balance(args.stats, output_dir),
    ]
    for chart in charts:
        chart()
    logger.info(f"Outputs saved under {output_dir}")
    return {"figures": len(charts), "folder": str(output_dir)}


def figures_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Draw the SVG charts of the wiki.")
    parser.add_argument("--tables", type=Path, default=TABLES)
    parser.add_argument("--folds", type=Path, default=FOLDS)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--clusters", type=Path, default=CLUSTER_DIR)
    parser.add_argument("--stats", type=Path, default=STATS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser
