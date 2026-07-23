#!/usr/bin/env python3
"""Execute Phase 3 fold creation from the accepted Phase 2 selection."""

from pathlib import Path

from src.phase3.phase3_fold_creation import (
    aggregate_embeddings_to_wsi,
    aggregate_to_origin_level,
    apply_pca_kmeans,
    broadcast_to_patch_level,
    create_stratification_keys,
    load_embeddings,
    load_expected_origin_ids,
    load_params,
    load_patch_metadata,
    save_outputs,
    stratum_round_robin_lpt_assignment,
    validate_folds,
)
from src.utils.logger import logger


PROJECT_ROOT = Path(__file__).parent.parent
PARAMS_FILE = PROJECT_ROOT / "clustering_params.json"
PATCH_DATA_FILE = PROJECT_ROOT / "data/ndb_ufes/patch/parcial_pndb_ufes.csv"
ORIGIN_MAPPING_FILE = (
    PROJECT_ROOT / "data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "results/phase3/fold_creation"
LOG_SEPARATOR = "=" * 80


def project_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def run() -> dict:
    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 3: STRATIFIED SIX-FOLD CREATION")
    logger.info(LOG_SEPARATOR)

    params = load_params(PARAMS_FILE)
    embeddings_path = project_path(params["embeddings_file"])
    expected_origin_ids = load_expected_origin_ids(ORIGIN_MAPPING_FILE)
    patch_df = load_patch_metadata(PATCH_DATA_FILE, expected_origin_ids)
    origin_df = aggregate_to_origin_level(patch_df)
    embeddings = load_embeddings(embeddings_path)
    wsi_features = aggregate_embeddings_to_wsi(embeddings, expected_origin_ids)

    logger.info(
        f"Using {params['model_name']} embeddings with "
        f"PCA={params['pca_components']} and K={params['kmeans_clusters']}"
    )
    labels, clustering_diagnostics = apply_pca_kmeans(wsi_features, params)
    origin_df, validation_df, included_columns = create_stratification_keys(
        origin_df,
        labels,
    )
    origin_df = stratum_round_robin_lpt_assignment(origin_df)
    patch_output = broadcast_to_patch_level(origin_df, patch_df)
    validation = validate_folds(origin_df, patch_output, expected_origin_ids)
    validation.update({
        "model_name": params["model_name"],
        "embeddings_file": str(embeddings_path),
        "pca_components": int(params["pca_components"]),
        "kmeans_clusters": int(params["kmeans_clusters"]),
        "random_state": int(params["random_state"]),
        "selection_constraints": params["selection_constraints"],
        "clustering": clustering_diagnostics,
        "stratification_columns": included_columns,
    })
    save_outputs(origin_df, patch_output, validation_df, validation, OUTPUT_DIR)

    logger.info(f"Assigned {validation['origin_count']} origins and {validation['patch_count']} patches")
    logger.info(f"Patch counts by fold: {validation['fold_patch_counts']}")
    logger.info(f"Patch imbalance ratio: {validation['patch_imbalance_ratio']:.3f}")
    logger.info(f"Outputs saved under {OUTPUT_DIR}")
    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 3 COMPLETE")
    logger.info(LOG_SEPARATOR)
    return validation


if __name__ == "__main__":
    run()
