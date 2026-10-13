from __future__ import annotations

import argparse
import itertools
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.phase0_dataset_builder.cases import FOLDER_DIFFERS, find_leaks
from src.phase0_dataset_builder.sources import NDB_METADATA, SHORT_LABEL, Diagnosis
from src.utils.logger import logger


DEFAULT_PATCH_TABLE = Path("results/phase0/dataset_tables/patch_table_public.csv")
DEFAULT_PICTURE_TABLE = Path("results/phase0/dataset_tables/picture_table_public.csv")
DEFAULT_NDB_METADATA = NDB_METADATA
DEFAULT_CLUSTERS = Path("results/phase1/clusters/patch_clusters.csv")
CLUSTER_COLUMN = "cluster_k3"  # the clustering chosen: 3 clusters
DEFAULT_OUTPUT_DIR = Path("results/phase1/folds")
OUTPUT_NAME = "fold_assignments.csv"
SUMMARY_NAME = "fold_summary.csv"
N_FOLDS = 6
N_STARTS = 200  # random starting points tried besides the greedy one
MIN_IMPROVEMENT = 1e-12  # a swap must lower the total deviation by more than this, so the search always ends
MAX_IMBALANCE_RATIO = 1.10  # the largest fold may hold at most this many times the patches of the smallest
CLASSES = tuple(diagnosis.value for diagnosis in Diagnosis)
NOT_IN_NDB = "not in NDB-UFES"
UNKNOWN = "unknown"  # gender and age group of patches whose picture is not in NDB-UFES
NDB_COLUMNS = [*(f"NDB-UFES {label}" for label in CLASSES), NOT_IN_NDB]
BALANCE_GROUPS = ("label", "ndb", "metadata", "cluster")  # what the folds can balance; the patch label and the total always count
OUTPUT_COLUMNS = ["patch_id", "case_group", "fold", "patch_diagnosis", "dropped_duplicate_of"]
ALLOWED_CELLS = {  # the only shapes a cell of the published file may have
    "patch_id": r"p\d{4}",
    "case_group": r"group_\d{3}",
    "fold": r"[0-5]?",
    "patch_diagnosis": "|".join(re.escape(label) for label in CLASSES),
    "dropped_duplicate_of": r"(p\d{4})?",
}


def load_patches(patch_table: Path) -> pd.DataFrame:
    return pd.read_csv(patch_table, dtype=str, keep_default_na=False)


def duplicates_to_drop(patches: pd.DataFrame) -> dict[str, str]:
    """Patch id -> the patch it duplicates, for every patch that is not the lowest id of its group of identical patches."""
    dropped = {}
    for row in patches.itertuples():
        twins = row.identical_patch_ids.split()
        keeper = min([row.patch_id, *twins])
        if twins and keeper != row.patch_id:
            dropped[row.patch_id] = keeper
    return dropped


def add_patch_attributes(patches: pd.DataFrame, metadata_csv: Path, clusters_csv: Path, cluster_column: str) -> pd.DataFrame:
    """The patches with the gender and age group of their NDB-UFES patient ("unknown" when the picture is not in NDB-UFES) and their morphology cluster."""
    metadata = pd.read_csv(metadata_csv, dtype=str, keep_default_na=False)
    by_origin = metadata.set_index(metadata["path"].map(lambda path: Path(path).stem))[["gender", "age_group"]]
    clusters = pd.read_csv(clusters_csv, dtype=str).set_index("patch_id")[cluster_column]
    result = patches.copy()
    result["gender"] = result["ndb_origin_id"].map(by_origin["gender"]).fillna(UNKNOWN)
    result["age_group"] = result["ndb_origin_id"].map(by_origin["age_group"]).fillna(UNKNOWN)
    result["morph_cluster"] = result["patch_id"].map(clusters)
    if result["morph_cluster"].isna().any():
        raise ValueError(f"{int(result['morph_cluster'].isna().sum())} patches have no cluster in {clusters_csv}")
    return result


def counts_by(patches: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    """One row per case group: its patches for each value of the column, in columns named with the prefix."""
    table = patches.groupby(["case_group", column]).size().unstack(fill_value=0)
    table.columns = [f"{prefix} {value}" for value in table.columns]
    return table


def group_class_counts(patches: pd.DataFrame) -> pd.DataFrame:
    """One row per case group: its patches per patch label, per NDB-UFES diagnosis of their picture, per gender, age group and cluster, and in total."""
    by_label = patches.groupby(["case_group", "patch_diagnosis"]).size().unstack(fill_value=0).reindex(columns=list(CLASSES), fill_value=0)
    ndb = patches["ndb_diagnosis"].replace("", NOT_IN_NDB)
    by_ndb = patches.groupby(["case_group", ndb]).size().unstack(fill_value=0).reindex(columns=[*CLASSES, NOT_IN_NDB], fill_value=0)
    by_ndb.columns = NDB_COLUMNS
    counts = by_label.join(by_ndb)
    for column, prefix in (("gender", "gender"), ("age_group", "age group"), ("morph_cluster", "cluster")):
        counts = counts.join(counts_by(patches, column, prefix))
    counts["patches"] = by_label.sum(axis=1)
    return counts.reset_index()


def count_columns(groups: pd.DataFrame) -> list[str]:
    """The counted columns of the group table; "patches", the total, is the last one."""
    return [column for column in groups.columns if column != "case_group"]


def column_group(column: str) -> str:
    """Which kind of count a column is: the patch label (and total), the NDB-UFES diagnosis, the metadata, or the cluster."""
    if column in (*CLASSES, "patches"):
        return "label"
    if column.startswith("NDB-UFES ") or column == NOT_IN_NDB:
        return "ndb"
    if column.startswith(("gender ", "age group ")):
        return "metadata"
    if column.startswith("cluster "):
        return "cluster"
    raise ValueError(f"Unknown column {column!r}")


def balance_weights(groups: pd.DataFrame, balance: list[str]) -> np.ndarray:
    """1 for each count the cost looks at: the kinds of count asked for, and always the patch label and the total."""
    chosen = {"label", *balance}
    return np.array([1.0 if column_group(column) in chosen else 0.0 for column in count_columns(groups)])


def fold_targets(groups: pd.DataFrame) -> np.ndarray:
    """What each fold should hold: an equal share of every count."""
    return groups[count_columns(groups)].to_numpy(float).sum(axis=0) / N_FOLDS


def fold_cost(fold_counts: np.ndarray, targets: np.ndarray, weights: np.ndarray) -> float:
    """How far one fold is from its targets: the squared relative deviation of each count the weights select."""
    return float((weights * ((fold_counts - targets) / targets) ** 2).sum())


def greedy_assignment(groups: pd.DataFrame, weights: np.ndarray) -> dict[str, int]:
    """Largest groups first, each into the fold where it adds the least deviation; a tie goes to the lowest fold."""
    targets = fold_targets(groups)
    counts = groups.set_index("case_group")[count_columns(groups)].astype(float)
    folds = np.zeros((N_FOLDS, len(targets)))
    assignment = {}
    for group in groups.sort_values(["patches", "case_group"], ascending=[False, True])["case_group"]:
        vector = counts.loc[group].to_numpy()
        added = [fold_cost(folds[fold] + vector, targets, weights) - fold_cost(folds[fold], targets, weights) for fold in range(N_FOLDS)]
        best = int(np.argmin(added))
        folds[best] += vector
        assignment[group] = best
    return assignment


def fold_counts(groups: pd.DataFrame, assignment: dict[str, int]) -> np.ndarray:
    """Every count for each fold, one row per fold."""
    columns = groups.set_index("case_group")[count_columns(groups)].astype(float)
    folds = np.zeros((N_FOLDS, columns.shape[1]))
    for group, fold in assignment.items():
        folds[fold] += columns.loc[group].to_numpy()
    return folds


def improve_assignment(groups: pd.DataFrame, assignment: dict[str, int], weights: np.ndarray) -> dict[str, int]:
    """Move one group to another fold, or exchange two groups between their folds, whenever that lowers the total deviation.

    Moves are tried before exchanges, always in the same order, and the search stops when a full pass changes nothing.
    """
    targets = fold_targets(groups)
    columns = groups.set_index("case_group")[count_columns(groups)].astype(float)
    vectors = {group: row.to_numpy() for group, row in columns.iterrows()}
    assignment = dict(assignment)
    folds = fold_counts(groups, assignment)
    cost = lambda counts: fold_cost(counts, targets, weights)
    improved = True
    while improved:
        improved = False
        for group in sorted(assignment):  # moves
            source = assignment[group]
            for target in range(N_FOLDS):
                if target == source:
                    continue
                before = cost(folds[source]) + cost(folds[target])
                after = cost(folds[source] - vectors[group]) + cost(folds[target] + vectors[group])
                if after < before - MIN_IMPROVEMENT:
                    folds[source], folds[target] = folds[source] - vectors[group], folds[target] + vectors[group]
                    assignment[group] = target
                    improved = True
                    source = target
        for first, second in itertools.combinations(sorted(assignment), 2):  # exchanges
            a, b = assignment[first], assignment[second]
            if a == b:
                continue
            new_a = folds[a] - vectors[first] + vectors[second]
            new_b = folds[b] - vectors[second] + vectors[first]
            if cost(new_a) + cost(new_b) < cost(folds[a]) + cost(folds[b]) - MIN_IMPROVEMENT:
                folds[a], folds[b] = new_a, new_b
                assignment[first], assignment[second] = b, a
                improved = True
    return assignment


def random_start(groups: pd.DataFrame, seed: int) -> dict[str, int]:
    """A starting point: the groups in a random order (fixed by the seed), dealt to the folds in turn."""
    order = np.random.default_rng(seed).permutation(sorted(groups["case_group"]))
    return {group: index % N_FOLDS for index, group in enumerate(order)}


def total_cost(groups: pd.DataFrame, assignment: dict[str, int], weights: np.ndarray) -> float:
    targets = fold_targets(groups)
    return sum(fold_cost(fold, targets, weights) for fold in fold_counts(groups, assignment))


def cost_by_column(groups: pd.DataFrame, assignment: dict[str, int], weights: np.ndarray) -> dict[str, float]:
    """How much of the total cost each count contributes, summed over the folds, largest first."""
    folds, targets = fold_counts(groups, assignment), fold_targets(groups)
    terms = (weights * ((folds - targets) / targets) ** 2).sum(axis=0)
    shares = {column: round(float(term), 3) for column, term, weight in zip(count_columns(groups), terms, weights) if weight > 0}
    return dict(sorted(shares.items(), key=lambda item: -item[1]))


def search_assignment(groups: pd.DataFrame, greedy: dict[str, int], weights: np.ndarray, starts: int) -> tuple[dict[str, int], dict]:
    """Improve the greedy assignment and ``starts`` random ones with moves and exchanges, and keep the one with the lowest cost."""
    candidates = [improve_assignment(groups, start, weights) for start in [greedy, *(random_start(groups, seed) for seed in range(starts))]]
    costs = np.array([total_cost(groups, candidate, weights) for candidate in candidates])
    best = int(np.argmin(costs))  # the first one when several are equally good
    return candidates[best], {
        "starts": len(candidates),
        "cost_from_the_greedy_start": round(float(costs[0]), 4),
        "best_cost": round(float(costs[best]), 4),
        "best_start": "greedy" if best == 0 else f"random seed {best - 1}",
        "cost_over_all_starts_min_median_max": [round(float(value), 3) for value in (costs.min(), np.median(costs), costs.max())],
    }


def assign_folds(patches: pd.DataFrame, assignment: dict[str, int]) -> pd.DataFrame:
    """The kept patches with the fold of their case group."""
    return patches.assign(fold=patches["case_group"].map(assignment))


def validate_folds(kept: pd.DataFrame, dropped: dict[str, str], max_imbalance: float = MAX_IMBALANCE_RATIO) -> dict:
    """Stop with every broken guarantee listed; otherwise return the measurements for the summary."""
    problems = []
    if kept["fold"].isna().any():
        problems.append(f"{int(kept['fold'].isna().sum())} patches have no fold")
    if kept["patch_id"].duplicated().any():
        problems.append("a patch appears more than once")
    for column, name in (("case_group", "case groups"), ("histopath_id", "pictures"), ("picture_group", "groups of related pictures")):
        spread = kept.groupby(column)["fold"].nunique()
        if (spread > 1).any():
            problems.append(f"{int((spread > 1).sum())} {name} appear in more than one fold")
    missing_keepers = set(dropped.values()) - set(kept["patch_id"])
    if missing_keepers:
        problems.append(f"patches kept in place of a dropped duplicate are not in the folds: {sorted(missing_keepers)}")

    per_class = kept.groupby(["fold", "patch_diagnosis"]).size().unstack(fill_value=0)
    per_class = per_class.reindex(index=range(N_FOLDS), columns=list(CLASSES), fill_value=0)
    if (per_class == 0).any().any():
        problems.append("a fold has no patch of some class")
    sizes = per_class.sum(axis=1)
    ratio = float(sizes.max() / sizes.min()) if sizes.min() > 0 else float("inf")
    if ratio > max_imbalance:
        problems.append(f"the largest fold holds {ratio:.3f} times the patches of the smallest (limit {max_imbalance})")
    if problems:
        raise ValueError("The folds break their guarantees: " + "; ".join(problems))
    return {"patches_per_fold": {int(fold): int(count) for fold, count in sizes.items()}, "imbalance_ratio": ratio}


def check_public_output(table: pd.DataFrame) -> None:
    """Stop unless the file has exactly the allowed columns and every cell has an allowed shape; the phase 0 leak patterns run as well."""
    if list(table.columns) != OUTPUT_COLUMNS:
        raise ValueError(f"The output must have exactly the columns {OUTPUT_COLUMNS}, not {list(table.columns)}")
    cells = table.astype({"fold": "Int64"}).astype(str).replace({"<NA>": "", "nan": ""})
    problems = []
    for column, pattern in ALLOWED_CELLS.items():
        not_allowed = ~cells[column].str.fullmatch(pattern)
        if not_allowed.any():
            problems.append(f"{int(not_allowed.sum())} cells of {column} are not of the form {pattern}")
    problems += find_leaks(cells)
    if problems:
        raise ValueError("The output would leak or hold unexpected content: " + "; ".join(problems))


def output_table(patches: pd.DataFrame, kept: pd.DataFrame, dropped: dict[str, str]) -> pd.DataFrame:
    """Every patch, with its fold; a dropped duplicate has no fold and names the patch kept in its place."""
    fold_of = dict(zip(kept["patch_id"], kept["fold"].astype(int)))
    table = pd.DataFrame({
        "patch_id": patches["patch_id"],
        "case_group": patches["case_group"],
        "fold": patches["patch_id"].map(fold_of).astype("Int64"),
        "patch_diagnosis": patches["patch_diagnosis"],
        "dropped_duplicate_of": patches["patch_id"].map(dropped).fillna(""),
    })
    return table.sort_values("patch_id").reset_index(drop=True)


def balance(groups: pd.DataFrame, assignment: dict[str, int], weights: np.ndarray) -> dict:
    """Largest fold over smallest fold, and the total deviation from the targets."""
    folds = fold_counts(groups, assignment)
    targets = fold_targets(groups)
    return {"imbalance_ratio": round(float(folds[:, -1].max() / folds[:, -1].min()), 3), "total_cost": round(sum(fold_cost(fold, targets, weights) for fold in folds), 4)}


def fold_summary(groups: pd.DataFrame, assignment: dict[str, int], kept: pd.DataFrame) -> pd.DataFrame:
    """One readable table: a row per fold, then the total, the ideal share of one fold, and the largest gap from it."""
    columns = ["patches"] + [column for column in count_columns(groups) if column != "patches"]
    counts = pd.DataFrame(fold_counts(groups, assignment), columns=count_columns(groups)).astype(int)[columns]
    names = {**{label: SHORT_LABEL[label] for label in CLASSES}, **{f"NDB-UFES {label}": f"NDB {SHORT_LABEL[label]}" for label in CLASSES}, NOT_IN_NDB: "no NDB"}
    table = pd.DataFrame({"groups": kept.groupby("fold")["case_group"].nunique()})
    for column in columns:
        table[names.get(column, column)] = counts[column]
    table["benigno"] = kept[kept["sab_folder"] == "benigno"].groupby("fold").size().reindex(range(N_FOLDS), fill_value=0)
    table.index = table.index.astype(int)
    total, ideal = table.sum(), table.sum() / N_FOLDS
    gap = ((table - ideal).abs() / ideal * 100).max().round(1)
    summary = pd.concat([table.astype(float), pd.DataFrame({"total": total, "ideal per fold": ideal.round(1), "largest gap %": gap}).T])
    summary.index.name = "fold"
    return summary.map(lambda value: f"{value:g}")


def benigno_report(kept: pd.DataFrame, pictures: pd.DataFrame) -> dict:
    """Benign pictures that have a similar picture in another folder: they stay in the folds; this only shows where they went."""
    similar_elsewhere = set(pictures.loc[(pictures["sab_folders"] == "benigno") & pictures["group_conflicts"].str.contains(FOLDER_DIFFERS), "histopath_id"])
    with_similar = kept[kept["histopath_id"].isin(similar_elsewhere)]
    return {
        "benigno_pictures_with_a_similar_picture_in_another_folder": len(similar_elsewhere),
        "their_patches": len(with_similar),
        "their_folds": sorted(int(fold) for fold in with_similar["fold"].unique()),
    }


def run_folds(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patches = add_patch_attributes(load_patches(args.patch_table), args.ndb_metadata, args.clusters, args.cluster_column)
    pictures = pd.read_csv(args.picture_table, dtype=str, keep_default_na=False)
    dropped = duplicates_to_drop(patches)
    kept = patches[~patches["patch_id"].isin(dropped)]
    groups = group_class_counts(kept)
    logger.info(f"{len(kept)} patches in {len(groups)} case groups; {len(dropped)} duplicate patches dropped: {dropped}")
    totals = groups.drop(columns="case_group").sum().astype(int).to_dict()
    logger.info(f"Patches counted per column: {totals}")

    weights = balance_weights(groups, args.balance)
    greedy = greedy_assignment(groups, weights)
    assignment, search = search_assignment(groups, greedy, weights, args.starts)
    before, after = balance(groups, greedy, weights), balance(groups, assignment, weights)
    logger.info(f"Balancing on {sorted({"label", *args.balance})}. Greedy assignment alone: {before}; best of {search['starts']} starts after moves and swaps: {after}")
    logger.info(f"Search: {search}")
    logger.info(f"Where the cost comes from, by count (each is the sum over the 6 folds of ((count - ideal) / ideal) squared): {cost_by_column(groups, assignment, weights)}")

    kept = assign_folds(kept, assignment)
    validation = validate_folds(kept, dropped, args.max_imbalance)
    table = output_table(patches, kept, dropped)
    check_public_output(table)
    table.to_csv(output_dir / OUTPUT_NAME, index=False)

    summary = fold_summary(groups, assignment, kept)
    summary.to_csv(output_dir / SUMMARY_NAME)
    for start in range(0, summary.shape[1], 10):  # the table is wide: the same rows, ten columns at a time
        logger.info(f"Folds, columns {start + 1} to {min(start + 10, summary.shape[1])} (Dys+ with dysplasia, Dys- without; NDB: diagnosis of the picture in NDB-UFES; benigno: SAB benigno folder):\n{summary.iloc[:, start:start + 10].to_string()}")
    logger.info(f"Outputs saved under {output_dir}")
    return {
        "patches_in_folds": len(kept),
        "duplicates_dropped": len(dropped),
        "case_groups": len(groups),
        "greedy": before,
        "best_found": after,
        "search": search,
        **validation,
        **benigno_report(kept, pictures),
    }


def folds_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assign the case groups to folds: largest first, each to the fold that keeps sizes and class mix closest to equal, then swaps.")
    parser.add_argument("--patch-table", type=Path, default=DEFAULT_PATCH_TABLE)
    parser.add_argument("--picture-table", type=Path, default=DEFAULT_PICTURE_TABLE)
    parser.add_argument("--ndb-metadata", type=Path, default=DEFAULT_NDB_METADATA)
    parser.add_argument("--clusters", type=Path, default=DEFAULT_CLUSTERS, help="Patch clusters from the patch-clusters command.")
    parser.add_argument("--cluster-column", default=CLUSTER_COLUMN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--starts", type=int, default=N_STARTS, help="Random starting points tried besides the greedy one; the best result is kept.")
    parser.add_argument("--max-imbalance", type=float, default=MAX_IMBALANCE_RATIO, help="Largest fold over smallest fold, at most.")
    parser.add_argument("--balance", nargs="+", choices=BALANCE_GROUPS, default=list(BALANCE_GROUPS), help="What the folds balance: the patch label and the total always count; add the NDB-UFES diagnosis (ndb), gender and age group (metadata), and the morphology clusters (cluster).")
    return parser
