import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


N_FOLDS = 6
MAX_MISSING_RATE_FOR_STRATIFICATION = 0.25
MAX_PATCH_IMBALANCE_RATIO = 1.10

REQUIRED_STRATIFICATION_COLUMNS = (
    "origin_diagnosis",
    "morph_cluster",
    "gender",
    "age_group",
)
OPTIONAL_STRATIFICATION_COLUMNS = ()
DESCRIPTIVE_METADATA_COLUMNS = (
    "gender",
    "skin_color",
    "age_group",
    "tobacco_use",
    "alcohol_consumption",
    "sun_exposure",
    "localization",
    "larger_size",
)
MISSING_STRINGS = {
    "",
    "nan",
    "none",
    "null",
    "na",
    "n/a",
    "unknown",
    "missing",
    "not informed",
}


def load_params(path: Path) -> dict:
    with Path(path).open() as params_file:
        params = json.load(params_file)
    required = {
        "model_name",
        "embeddings_file",
        "pca_components",
        "kmeans_clusters",
        "random_state",
        "selection_constraints",
    }
    missing = sorted(required - params.keys())
    if missing:
        raise ValueError(f"Phase 2 parameters are missing required keys: {missing}")
    return params


def load_embeddings(path: Path) -> dict:
    with Path(path).open("rb") as embeddings_file:
        embeddings = pickle.load(embeddings_file)
    if not isinstance(embeddings, dict) or not embeddings:
        raise ValueError(f"Expected a non-empty embeddings dictionary in {path}")
    return embeddings


def load_expected_origin_ids(path: Path) -> list[int]:
    mapping = pd.read_csv(path)
    if "origin_id" not in mapping.columns:
        raise ValueError(f"Origin mapping must contain 'origin_id': {path}")
    if mapping["origin_id"].isna().any() or mapping["origin_id"].duplicated().any():
        raise ValueError(f"Origin mapping contains missing or duplicate IDs: {path}")
    return sorted(mapping["origin_id"].astype(int).tolist())


def load_patch_metadata(path: Path, expected_origin_ids: list[int]) -> pd.DataFrame:
    patch_df = pd.read_csv(path)
    required = {"origin", "patch", "diagnosis"}
    missing = sorted(required - set(patch_df.columns))
    if missing:
        raise ValueError(f"Patch metadata is missing required columns: {missing}")

    origin_values = pd.to_numeric(patch_df["origin"], errors="coerce")
    if origin_values.isna().any():
        raise ValueError("Patch metadata contains missing or non-numeric origin IDs")
    if not np.equal(origin_values, np.floor(origin_values)).all():
        raise ValueError("Patch metadata contains non-integer origin IDs")
    patch_df["origin"] = origin_values.astype(int)

    if patch_df["patch"].duplicated().any():
        raise ValueError("Patch metadata contains duplicate patch IDs")
    actual_origins = set(patch_df["origin"])
    expected_origins = set(expected_origin_ids)
    if actual_origins != expected_origins:
        raise ValueError(
            "Patch/mapping origin mismatch: "
            f"{len(expected_origins - actual_origins)} missing and "
            f"{len(actual_origins - expected_origins)} unexpected origins"
        )
    return patch_df


def aggregate_to_origin_level(patch_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for origin_id, origin_patches in patch_df.groupby("origin", sort=True):
        row = {
            "origin_id": int(origin_id),
            "origin_diagnosis": origin_patches["diagnosis"].mode().iloc[0],
            "patch_diagnoses": ",".join(
                sorted(origin_patches["diagnosis"].astype(str).unique())
            ),
            "patch_count": int(len(origin_patches)),
            "patch_ids": ",".join(origin_patches["patch"].astype(str)),
        }
        for column in DESCRIPTIVE_METADATA_COLUMNS:
            if column in origin_patches.columns:
                counts = origin_patches[column].value_counts(dropna=False)
                row[column] = counts.index[0]
        rows.append(row)
    return pd.DataFrame(rows).sort_values("origin_id").reset_index(drop=True)


def aggregate_embeddings_to_wsi(
    embeddings: dict,
    origin_ids: list[int],
) -> np.ndarray:
    expected = set(origin_ids)
    actual = set(embeddings)
    if actual != expected:
        raise ValueError(
            "Embedding/origin mismatch: "
            f"{len(expected - actual)} missing and {len(actual - expected)} unexpected origins"
        )

    features = []
    feature_dim = None
    for origin_id in origin_ids:
        patch_features = np.asarray(embeddings[origin_id])
        if patch_features.ndim != 2 or patch_features.shape[0] == 0:
            raise ValueError(
                f"Origin {origin_id} has invalid embedding shape {patch_features.shape}"
            )
        if feature_dim is None:
            feature_dim = patch_features.shape[1]
        elif patch_features.shape[1] != feature_dim:
            raise ValueError(f"Origin {origin_id} has inconsistent embedding dimensions")
        if not np.isfinite(patch_features).all():
            raise ValueError(f"Origin {origin_id} contains non-finite embeddings")
        features.append(patch_features.mean(axis=0))
    return np.vstack(features).astype(np.float64, copy=False)


def apply_pca_kmeans(embeddings: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    pca_components = int(params["pca_components"])
    cluster_count = int(params["kmeans_clusters"])
    random_state = int(params["random_state"])

    pca = PCA(n_components=pca_components, svd_solver="full")
    reduced = np.ascontiguousarray(pca.fit_transform(embeddings))
    kmeans = KMeans(
        n_clusters=cluster_count,
        random_state=random_state,
        n_init=10,
    )
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        labels = kmeans.fit_predict(reduced)

    if not np.isfinite(kmeans.cluster_centers_).all() or not np.isfinite(kmeans.inertia_):
        raise FloatingPointError("K-Means produced non-finite results")
    if len(np.unique(labels)) != cluster_count:
        raise ValueError(
            f"K-Means produced {len(np.unique(labels))} clusters; expected {cluster_count}"
        )

    sizes = np.bincount(labels, minlength=cluster_count)
    size_ratio = float(sizes.max() / sizes.min())
    constraints = params["selection_constraints"]
    if sizes.min() < int(constraints["min_cluster_size"]):
        raise ValueError("Selected clustering violates the minimum cluster-size constraint")
    if size_ratio > float(constraints["max_cluster_size_ratio"]):
        raise ValueError("Selected clustering violates the cluster-imbalance constraint")

    diagnostics = {
        "explained_variance": float(pca.explained_variance_ratio_.sum()),
        "inertia": float(kmeans.inertia_),
        "cluster_sizes": sizes.astype(int).tolist(),
        "cluster_size_ratio": size_ratio,
    }
    return labels, diagnostics


def missing_value_mask(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.casefold()
    return series.isna() | normalized.isin(MISSING_STRINGS)


def summarize_column_for_stratification(series: pd.Series) -> dict:
    missing_mask = missing_value_mask(series)
    counts = series[~missing_mask].value_counts(dropna=True)
    return {
        "missing_count": int(missing_mask.sum()),
        "missing_rate": float(missing_mask.mean()) if len(series) else 0.0,
        "n_categories": int(len(counts)),
        "min_category_count": int(counts.min()) if not counts.empty else 0,
    }


def evaluate_stratification_variables(
    origin_df: pd.DataFrame,
    required_columns=REQUIRED_STRATIFICATION_COLUMNS,
    optional_columns=OPTIONAL_STRATIFICATION_COLUMNS,
    descriptive_columns=DESCRIPTIVE_METADATA_COLUMNS,
    max_missing_rate=MAX_MISSING_RATE_FOR_STRATIFICATION,
    n_folds=N_FOLDS,
) -> pd.DataFrame:
    rows = []
    required_set = set(required_columns)
    optional_set = set(optional_columns)
    columns = list(dict.fromkeys(required_columns + optional_columns + descriptive_columns))

    for column in columns:
        role = (
            "required" if column in required_set
            else "optional" if column in optional_set
            else "descriptive"
        )
        if column not in origin_df.columns:
            rows.append({
                "column": column,
                "role": role,
                "status": "blocked_required" if role == "required" else "excluded_missing",
                "missing_count": "",
                "missing_rate": "",
                "n_categories": "",
                "min_category_count": "",
                "reason": "column is not present",
            })
            continue

        summary = summarize_column_for_stratification(origin_df[column])
        if summary["missing_rate"] > max_missing_rate:
            status = "blocked_required" if role == "required" else "excluded_high_missingness"
            reason = f"missing rate exceeds {max_missing_rate:.0%}"
        elif summary["min_category_count"] < n_folds:
            status = "blocked_required" if role == "required" else "excluded_low_support"
            reason = f"a category has fewer than {n_folds} origins"
        elif role == "required":
            status = "included_required"
            reason = "required variable passed missingness and support checks"
        elif role == "optional":
            status = "included_optional"
            reason = "optional variable passed missingness and support checks"
        else:
            status = "excluded_descriptive_only"
            reason = "retained for reporting, not fold construction"
        rows.append({"column": column, "role": role, "status": status, **summary, "reason": reason})
    return pd.DataFrame(rows)


def build_stratification_key(
    origin_df: pd.DataFrame,
    audit_df: pd.DataFrame,
) -> tuple[pd.Series, list[str]]:
    blocked = audit_df[
        (audit_df["role"] == "required")
        & (audit_df["status"] != "included_required")
    ]
    if not blocked.empty:
        details = "; ".join(
            f"{row.column}: {row.reason}" for row in blocked.itertuples()
        )
        raise ValueError(f"Required stratification audit failed: {details}")

    included = audit_df.loc[
        audit_df["status"].isin(["included_required", "included_optional"]),
        "column",
    ].tolist()
    parts = []
    for column in included:
        values = origin_df[column].astype(str).str.strip().str.replace(r"\s+", "-", regex=True)
        if column == "morph_cluster":
            values = "c" + values
        parts.append(column + "=" + values)
    return pd.concat(parts, axis=1).agg("|".join, axis=1), included


def create_stratification_keys(
    origin_df: pd.DataFrame,
    clusters: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    if len(origin_df) != len(clusters):
        raise ValueError("Cluster assignments do not align with origin rows")
    result = origin_df.copy()
    result["morph_cluster"] = clusters.astype(int)
    audit = evaluate_stratification_variables(result)
    result["stratification_key"], included = build_stratification_key(result, audit)
    return result, audit, included


def stratum_round_robin_lpt_assignment(
    origin_df: pd.DataFrame,
    n_folds: int = N_FOLDS,
) -> pd.DataFrame:
    required = {"origin_id", "patch_count", "stratification_key"}
    if not required.issubset(origin_df.columns):
        raise ValueError(f"Fold assignment requires columns: {sorted(required)}")

    result = origin_df.reset_index(drop=True).copy()
    assignments = np.full(len(result), -1, dtype=int)
    fold_patch_counts = np.zeros(n_folds, dtype=int)
    fold_origin_counts = np.zeros(n_folds, dtype=int)
    groups = sorted(
        result.groupby("stratification_key").groups.items(),
        key=lambda item: (len(item[1]), item[0]),
    )

    for _, indices in groups:
        ordered = result.loc[indices].sort_values(
            ["patch_count", "origin_id"],
            ascending=[False, True],
        ).index.tolist()
        for start in range(0, len(ordered), n_folds):
            available_folds = set(range(n_folds))
            for index in ordered[start:start + n_folds]:
                fold = min(
                    available_folds,
                    key=lambda candidate: (
                        fold_patch_counts[candidate],
                        fold_origin_counts[candidate],
                        candidate,
                    ),
                )
                assignments[index] = fold
                fold_patch_counts[fold] += int(result.loc[index, "patch_count"])
                fold_origin_counts[fold] += 1
                available_folds.remove(fold)

    result["fold"] = assignments
    return result


def broadcast_to_patch_level(
    origin_df: pd.DataFrame,
    patch_df: pd.DataFrame,
) -> pd.DataFrame:
    fold_map = dict(zip(origin_df["origin_id"], origin_df["fold"]))
    result = patch_df.copy()
    result["origin_id"] = result["origin"].astype(int)
    result["fold"] = result["origin_id"].map(fold_map)
    if result["fold"].isna().any():
        raise ValueError("Some patches could not inherit an origin fold")
    result["fold"] = result["fold"].astype(int)
    return result


def validate_folds(
    origin_df: pd.DataFrame,
    patch_df: pd.DataFrame,
    expected_origin_ids: list[int],
    n_folds: int = N_FOLDS,
    max_patch_imbalance_ratio: float = MAX_PATCH_IMBALANCE_RATIO,
) -> dict:
    expected = set(expected_origin_ids)
    if set(origin_df["origin_id"]) != expected or set(patch_df["origin_id"]) != expected:
        raise ValueError("Final fold outputs do not contain the expected origin set")
    if origin_df["fold"].isna().any() or patch_df["fold"].isna().any():
        raise ValueError("Final fold outputs contain unassigned rows")
    if set(origin_df["fold"]) != set(range(n_folds)):
        raise ValueError("Final fold output does not contain every fold ID")
    if patch_df.groupby("origin_id")["fold"].nunique().max() != 1:
        raise ValueError("An origin spans multiple folds")

    patch_counts = patch_df["fold"].value_counts().sort_index()
    patch_ratio = float(patch_counts.max() / patch_counts.min())
    if patch_ratio > max_patch_imbalance_ratio:
        raise ValueError(
            f"Patch imbalance ratio {patch_ratio:.3f} exceeds "
            f"{max_patch_imbalance_ratio:.3f}"
        )

    stratum_counts = pd.crosstab(origin_df["fold"], origin_df["stratification_key"])
    max_stratum_range = int((stratum_counts.max() - stratum_counts.min()).max())
    if max_stratum_range > 1:
        raise ValueError("A combined stratum differs by more than one origin across folds")

    return {
        "origin_count": int(len(origin_df)),
        "patch_count": int(len(patch_df)),
        "fold_origin_counts": {
            str(key): int(value)
            for key, value in origin_df["fold"].value_counts().sort_index().items()
        },
        "fold_patch_counts": {
            str(key): int(value) for key, value in patch_counts.items()
        },
        "patch_imbalance_ratio": patch_ratio,
        "max_stratum_fold_count_range": max_stratum_range,
        "max_folds_per_origin": int(
            patch_df.groupby("origin_id")["fold"].nunique().max()
        ),
    }


def save_outputs(
    origin_df: pd.DataFrame,
    patch_df: pd.DataFrame,
    audit_df: pd.DataFrame,
    validation: dict,
    output_dir: Path,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    origin_columns = [
        "origin_id",
        "origin_diagnosis",
        "patch_diagnoses",
        *[column for column in DESCRIPTIVE_METADATA_COLUMNS if column in origin_df.columns],
        "morph_cluster",
        "patch_count",
        "stratification_key",
        "fold",
    ]
    patch_columns = [
        "origin_id",
        "patch",
        "diagnosis",
        *[column for column in DESCRIPTIVE_METADATA_COLUMNS if column in patch_df.columns],
        "fold",
    ]
    origin_df[origin_columns].sort_values("origin_id").to_csv(
        output_dir / "fold_assignments_origin.csv",
        index=False,
    )
    patch_df[patch_columns].to_csv(
        output_dir / "fold_assignments_patch_level.csv",
        index=False,
    )
    audit_df.to_csv(output_dir / "stratification_variables_audit.csv", index=False)
    with (output_dir / "fold_validation.json").open("w") as validation_file:
        json.dump(validation, validation_file, indent=2)
