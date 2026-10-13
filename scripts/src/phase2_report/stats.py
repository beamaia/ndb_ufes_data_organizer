"""Stage stats: every table and statistic the wiki shows, as one CSV file each, from the published tables and the patient data."""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import chi2_contingency

from src.phase0_dataset_builder.sources import NDB_METADATA, SEVERITY
from src.phase1_folds.clusters import load_embeddings, reduce_embeddings
from src.phase1_folds.embeddings import EMBEDDINGS
from src.phase1_folds.folds import add_patch_attributes
from src.utils.logger import logger


TABLES = Path("results/phase0/dataset_tables")
FOLDS = Path("results/phase1/folds")
CLUSTERS = Path("results/phase1/clusters/patch_clusters.csv")
ORIGINAL_FOLD_FILES = [  # the six folds published with P-NDB-UFES: five folders, and a sixth that was the test set
    Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_folders.csv"),
    Path("data/ndb_ufes/patch_level/csvs/sabpatch_parsed_test.csv"),
]
OUTPUT_DIR = Path("results/phase2/tables")
RANDOM_DRAWS = 20  # random divisions of the patches, averaged, as the level that no structure gives
SEED = 42
LABELS = [diagnosis.value for diagnosis, _ in sorted(SEVERITY.items(), key=lambda item: item[1])]  # from least to most severe
NOT_IN_NDB = "not in NDB-UFES"
PATCH_SIDE = 512
NDB_VARIABLES = ["diagnosis", "gender", "age_group", "skin_color", "localization", "tobacco_use", "alcohol_consumption", "sun_exposure"]
NDB_LISTED_VALUES = 8  # a column with at most this many distinct values is listed with them in the column table
UNITS = {"cases": "case_pseudonym", "case groups": "case_group", "parent pictures": "histopath_id", "groups of related pictures": "picture_group"}
FOLD_VARIABLES = {"patch label": "patch_diagnosis", "NDB-UFES diagnosis": "ndb", "gender": "gender", "age group": "age_group", "morphology cluster": "morph_cluster"}
PATCH_VARIABLES = {"patch label": "patch_diagnosis", "NDB-UFES diagnosis": "ndb", "gender": "gender", "age group": "age_group", "morphology cluster": "morph_cluster", "SAB folder": "sab_folder"}


def cramers_v(first: pd.Series, second: pd.Series) -> float:
    """How strongly two categorical variables are tied, from 0 (not at all) to 1 (one decides the other): Cramér's V of their counts."""
    table = pd.crosstab(first, second)
    smaller = min(table.shape) - 1
    if smaller == 0:
        return float("nan")
    chi2 = chi2_contingency(table, correction=False)[0]
    return float(np.sqrt(chi2 / (table.to_numpy().sum() * smaller)))


def correlation_matrix(frame: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Cramér's V between every two variables; ``columns`` maps the name shown to the column of ``frame``."""
    matrix = pd.DataFrame({a: {b: round(cramers_v(frame[columns[a]], frame[columns[b]]), 3) for b in columns} for a in columns})
    return matrix.rename_axis("variable").reset_index()


def original_folds(files: list[Path] = ORIGINAL_FOLD_FILES) -> pd.Series:
    """patch id -> folder number (1 to 6) of the folds published with P-NDB-UFES."""
    published = pd.concat([pd.read_csv(path, dtype=str) for path in files])
    return published.assign(patch_id=published["path"].str.removesuffix(".png")).set_index("patch_id")["folder"]


def fold_sets(assignments: pd.DataFrame) -> dict[str, pd.Series]:
    """patch id -> fold, for the new folds and for the original folds."""
    return {"new folds": assignments[assignments["fold"] != ""].set_index("patch_id")["fold"], "original folds": original_folds()}


def fold_balance(patch: pd.DataFrame, sets: dict[str, pd.Series]) -> pd.DataFrame:
    """For each value of each balanced variable: how far apart the folds are, as the share of the patches of the fold that have it
    in the fold with the highest share minus the fold with the lowest, in percentage points."""
    rows = []
    for name, folds in sets.items():
        frame = patch[patch["patch_id"].isin(folds.index)].assign(fold=lambda f: f["patch_id"].map(folds))
        for variable, column in FOLD_VARIABLES.items():
            shares = pd.crosstab(frame["fold"], frame[column], normalize="index") * 100
            rows += [{"fold_set": name, "variable": variable, "value": value, "spread_points": round(float(shares[value].max() - shares[value].min()), 1)} for value in shares.columns]
    return pd.DataFrame(rows)


def fold_spread(patch: pd.DataFrame, sets: dict[str, pd.Series]) -> pd.DataFrame:
    """For each kind of unit: how many units have their patches in one fold, in two folds, and so on."""
    rows = []
    for name, folds in sets.items():
        frame = patch[patch["patch_id"].isin(folds.index)].assign(fold=lambda f: f["patch_id"].map(folds))
        for unit, column in UNITS.items():
            in_folds = frame.groupby(column)["fold"].nunique().value_counts()
            rows += [{"fold_set": name, "unit": unit, "folds": int(count), "units": int(units)} for count, units in sorted(in_folds.items())]
    return pd.DataFrame(rows)


def pair_distances(distance: np.ndarray, folds: np.ndarray) -> dict[tuple[int, int], float]:
    """The energy distance between every two folds, on the distances between all the patches: 0 when two folds cover the space in the same way, larger the more differently."""
    names = sorted(set(folds))
    rows = {name: np.flatnonzero(folds == name) for name in names}
    within = {name: distance[np.ix_(rows[name], rows[name])].mean() for name in names}
    return {
        (a, b): float(np.sqrt(max(2 * distance[np.ix_(rows[names[a]], rows[names[b]])].mean() - within[names[a]] - within[names[b]], 0)))
        for a, b in combinations(range(len(names)), 2)
    }


def fold_distances(embeddings: Path, sets: dict[str, pd.Series]) -> pd.DataFrame:
    """How far apart the folds are in the plane of the first two PCA components of the patch embeddings, for the new folds, the original folds and random divisions."""
    patch_ids, matrix = load_embeddings(embeddings)
    coordinates = pd.DataFrame(reduce_embeddings(matrix, 2), index=patch_ids)
    rows = []
    for name, folds in sets.items():
        known = coordinates.index.intersection(folds.index)
        points, labels = coordinates.loc[known].to_numpy(), folds.loc[known].to_numpy()
        for (a, b), value in pair_distances(cdist(points, points), labels).items():
            rows.append({"fold_set": name, "fold_a": sorted(set(labels))[a], "fold_b": sorted(set(labels))[b], "distance": value})
    known = coordinates.index.intersection(sets["new folds"].index)
    points, sizes = coordinates.loc[known].to_numpy(), sets["new folds"].loc[known].value_counts().sort_index().to_numpy()
    distance, rng = cdist(points, points), np.random.default_rng(SEED)
    draws = [pair_distances(distance, rng.permutation(np.repeat(np.arange(len(sizes)), sizes))) for _ in range(RANDOM_DRAWS)]
    rows += [{"fold_set": "random division", "fold_a": str(a + 1), "fold_b": str(b + 1), "distance": float(np.mean([draw[(a, b)] for draw in draws]))} for (a, b) in draws[0]]
    table = pd.DataFrame(rows)
    table["distance"] = table["distance"].round(2)
    return table


def overlapping_patches(patch: pd.DataFrame, sets: dict[str, pd.Series], shares=(0.25, 0.5, 0.75)) -> pd.DataFrame:
    """Pairs of patches from one parent picture that share at least the given part of their area, and how many such pairs are in different folds."""
    pairs = []
    for _, group in patch.groupby("histopath_id"):
        x, y = group["x"].astype(int).to_numpy(), group["y"].astype(int).to_numpy()
        first, second = np.triu_indices(len(group), k=1)
        shared = np.clip(PATCH_SIDE - np.abs(x[first] - x[second]), 0, None) * np.clip(PATCH_SIDE - np.abs(y[first] - y[second]), 0, None) / PATCH_SIDE**2
        ids = group["patch_id"].to_numpy()
        pairs.append(pd.DataFrame({"a": ids[first], "b": ids[second], "shared": shared}))
    pairs = pd.concat(pairs)
    rows = []
    for name, folds in sets.items():
        known = pairs[pairs["a"].isin(folds.index) & pairs["b"].isin(folds.index)]
        different = known["a"].map(folds).to_numpy() != known["b"].map(folds).to_numpy()
        for share in shares:
            chosen = known["shared"].to_numpy() >= share
            rows.append({"fold_set": name, "shared_area_at_least": f"{share:.0%}", "pairs": int(chosen.sum()), "pairs_in_different_folds": int((chosen & different).sum()),
                         "share_in_different_folds": round(float((chosen & different).sum() / max(chosen.sum(), 1)), 4)})
    return pd.DataFrame(rows)


def ndb_tables(metadata: pd.DataFrame, picture: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The NDB-UFES images: what is in them, and how the diagnosis relates to the patient data. The unit is the image."""
    distributions = pd.DataFrame([
        {"variable": variable, "value": value, "images": int(count), "share": round(count / len(metadata), 4)}
        for variable in NDB_VARIABLES for value, count in metadata[variable].replace("", "missing").value_counts().items()
    ])
    with_patches = set(picture.loc[picture["n_patches"].astype(int) > 0, "ndb_origin_id"]) - {""}
    origin = metadata["path"].map(lambda path: Path(path).stem)
    glance = pd.DataFrame([
        {"item": "images", "value": len(metadata)}, {"item": "patients", "value": metadata["patient_id"].nunique()},
        {"item": "lesions", "value": metadata["lesion_id"].nunique()}, {"item": "images with patches in P-NDB-UFES", "value": int(origin.isin(with_patches).sum())},
        {"item": "images without patches", "value": int((~origin.isin(with_patches)).sum())},
    ])
    patched = pd.crosstab(metadata["diagnosis"], origin.isin(with_patches).map({True: "with patches", False: "without patches"})).reindex(LABELS).fillna(0).astype(int).reset_index()
    correlations = correlation_matrix(metadata.replace("", "missing"), {variable: variable for variable in NDB_VARIABLES})
    columns = pd.DataFrame([
        {"column": column, "filled": int((metadata[column] != "").sum()), "values": ", ".join(sorted(set(metadata[column]) - {""})) if metadata[column].nunique() <= NDB_LISTED_VALUES else f"{metadata[column].nunique()} distinct"}
        for column in metadata.columns
    ])
    return {"ndb_at_a_glance": glance, "ndb_columns": columns, "ndb_distributions": distributions, "ndb_images_with_patches": patched, "ndb_correlations": correlations}


def picture_tables(patch: pd.DataFrame, picture: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The parent pictures: patches per picture, SAB folder against the NDB-UFES diagnosis, and how related pictures differ in zoom."""
    per_picture = patch.groupby("histopath_id").size()
    dataset_of = picture.set_index("histopath_id")["datasets"]
    summaries = []
    for name, sizes in (("all pictures with patches", per_picture), *((f"pictures in {d}", per_picture[dataset_of.reindex(per_picture.index) == d]) for d in ("ndb+sab", "sab"))):
        summaries.append({"pictures": name, "count": len(sizes), "mean": round(float(sizes.mean()), 1), "median": float(sizes.median()), "q1": float(sizes.quantile(0.25)), "q3": float(sizes.quantile(0.75)), "smallest": int(sizes.min()), "largest": int(sizes.max())})
    in_both = picture[picture["datasets"] == "ndb+sab"]
    folder_vs_diagnosis = pd.crosstab(in_both["sab_folders"], in_both["ndb_diagnosis"]).reindex(columns=LABELS, fill_value=0).reset_index()
    benign = patch[patch["sab_folder"] == "benigno"]["patch_diagnosis"].value_counts().reindex(LABELS, fill_value=0)
    benign_row = pd.DataFrame([{"sab_folders": "benigno (no picture in NDB-UFES; its patches by patch label)", **benign.to_dict()}])
    pairs = {}
    for row in picture.itertuples():
        for part in filter(None, row.overlap_with_group.split(" | ")):
            other, values = part.split(": ")
            seen = dict(item.split("=") for item in values.split())
            key = tuple(sorted((row.histopath_id, other)))
            if key not in pairs:
                scale = float(seen["scale"])
                pairs[key] = {"picture_a": key[0], "picture_b": key[1], "zoom_factor": round(max(scale, 1 / scale), 2), "zoomed": max(scale, 1 / scale) > 1.25}
    return {"patches_per_picture": pd.DataFrame(summaries), "sab_folder_vs_diagnosis": pd.concat([folder_vs_diagnosis, benign_row], ignore_index=True), "related_pictures": pd.DataFrame(pairs.values())}


def run_stats(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_table = pd.read_csv(args.tables / "patch_table_public.csv", dtype=str, keep_default_na=False)
    picture = pd.read_csv(args.tables / "picture_table_public.csv", dtype=str, keep_default_na=False)
    assignments = pd.read_csv(args.folds / "fold_assignments.csv", dtype=str, keep_default_na=False)
    metadata = pd.read_csv(args.ndb_metadata, dtype=str, keep_default_na=False)
    patch = add_patch_attributes(patch_table, args.ndb_metadata, args.clusters, "cluster_k3")
    patch["ndb"] = patch["ndb_diagnosis"].replace("", NOT_IN_NDB)
    sets = fold_sets(assignments)

    tables = {
        "fold_balance": fold_balance(patch, sets), "fold_spread": fold_spread(patch, sets),
        "overlapping_patches": overlapping_patches(patch, sets), "fold_distances": fold_distances(args.embeddings, sets), "patch_correlations": correlation_matrix(patch, PATCH_VARIABLES),
        **ndb_tables(metadata, picture), **picture_tables(patch, picture),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
        logger.info(f"{name}: {len(table)} rows")
    logger.info(f"Outputs saved under {output_dir}")
    return {"tables": len(tables), "folder": str(output_dir)}


def stats_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write every table and statistic the wiki shows, one CSV file each.")
    parser.add_argument("--tables", type=Path, default=TABLES)
    parser.add_argument("--folds", type=Path, default=FOLDS)
    parser.add_argument("--clusters", type=Path, default=CLUSTERS)
    parser.add_argument("--ndb-metadata", type=Path, default=NDB_METADATA)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser
