from pathlib import Path

from src.phase2.phase2_average_results import average_results, save_averaged_results
from src.phase2.phase2_enhanced_visualizations import (
    create_basic_visualizations,
    create_enhanced_visualizations,
)
from src.phase2.phase2_save_params import select_optimal_params, save_optimal_params
from scripts.src.phase2.phase2_tune_clustering import (
    aggregate_to_wsi_level,
    discover_latest_embeddings,
    load_config,
    load_embeddings,
    load_origin_ids,
    run_grid_search,
)
from src.utils.logger import logger


PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "scripts/src/phase2/config.yaml"
LOG_SEPARATOR = "=" * 80


def project_path(path: str) -> Path:
    configured_path = Path(path)
    if configured_path.is_absolute():
        return configured_path
    return PROJECT_ROOT / configured_path


def configured_output_path(template: str, **values) -> Path:
    return project_path(template.format(**values))


def log_phase_start(model_count: int) -> None:
    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 2: CLUSTERING PARAMETER TUNING")
    logger.info(f"Processing {model_count} models")
    logger.info(LOG_SEPARATOR)


def log_phase_end(optimal_params: dict[str, dict], selected_params: dict) -> None:
    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 2 COMPLETE")
    logger.info(LOG_SEPARATOR)
    for model_name, params in sorted(optimal_params.items()):
        logger.info(
            f"{model_name:30s} PCA={params['pca_components']:2d}, "
            f"K={params['kmeans_clusters']}, "
            f"silhouette={params['silhouette_score']:.4f} "
            f"+/- {params['silhouette_std']:.4f}"
        )
    logger.info("-" * 80)
    logger.info(
        f"Selected model: {selected_params['model_name']} "
        f"(PCA={selected_params['pca_components']}, "
        f"K={selected_params['kmeans_clusters']}, "
        f"silhouette={selected_params['silhouette_score']:.4f})"
    )


def run(config_path: Path = CONFIG_PATH) -> dict[str, dict]:
    config = load_config(config_path)
    tuning = config["tuning"]
    inputs = config["input"]
    outputs = config["output"]
    visualizations = config.get("visualizations", {})

    embedding_pattern = str(project_path(inputs["embeddings_pattern"]))
    logger.info(f"Searching for embeddings matching: {embedding_pattern}")
    embedding_files = discover_latest_embeddings(embedding_pattern)
    origin_ids = load_origin_ids(project_path(inputs["origin_metadata_file"]))
    logger.info(f"Loaded {len(origin_ids)} Phase 1 origins")
    log_phase_start(len(embedding_files))

    all_optimal_params = {}
    failed_models = {}

    for model_index, (model_name, embeddings_path) in enumerate(
        embedding_files.items(),
        start=1,
    ):
        logger.info("-" * 80)
        logger.info(f"MODEL {model_index}/{len(embedding_files)}: {model_name.upper()}")
        logger.info("-" * 80)

        try:
            embeddings = load_embeddings(embeddings_path)
            wsi_features = aggregate_to_wsi_level(embeddings, origin_ids)
            logger.info(f"WSI feature matrix: {wsi_features.shape}")

            run_results = []
            for run_id in range(1, tuning["n_runs"] + 1):
                random_state = tuning["random_state"] + run_id - 1
                logger.info(
                    f"Run {run_id}/{tuning['n_runs']} "
                    f"(random_state={random_state})"
                )
                results = run_grid_search(
                    wsi_features=wsi_features,
                    pca_components=tuning["pca_components_to_test"],
                    cluster_counts=tuning["kmeans_clusters_to_test"],
                    random_state=random_state,
                    run_id=run_id,
                )
                run_path = configured_output_path(
                    outputs["run_results_template"],
                    model=model_name,
                    run_id=run_id,
                )
                run_path.parent.mkdir(parents=True, exist_ok=True)
                results.to_csv(run_path, index=False)
                run_results.append(results)

            averaged_results = average_results(run_results)
            averaged_path = configured_output_path(
                outputs["averaged_results_template"],
                model=model_name,
            )
            save_averaged_results(averaged_results, averaged_path)

            create_basic_visualizations(
                results=averaged_results,
                model_name=model_name,
                elbow_path=configured_output_path(
                    visualizations["elbow_curves_template"],
                    model=model_name,
                ),
                silhouette_path=configured_output_path(
                    visualizations["silhouette_heatmap_template"],
                    model=model_name,
                ),
            )
            create_enhanced_visualizations(
                results=averaged_results,
                model_name=model_name,
                output_dir=project_path(outputs["results_dir"]),
            )

            params = select_optimal_params(
                averaged_results,
                random_state=tuning["random_state"],
            )
            params_path = configured_output_path(
                outputs["params_template"],
                model=model_name,
            )
            save_optimal_params(params, params_path)
            all_optimal_params[model_name] = params
            logger.info(
                f"Selected PCA={params['pca_components']}, "
                f"K={params['kmeans_clusters']}, "
                f"silhouette={params['silhouette_score']:.4f}"
            )
        except Exception as error:
            failed_models[model_name] = str(error)
            logger.exception(f"Failed to tune {model_name}")

    if failed_models:
        failures = "; ".join(
            f"{model}: {error}" for model, error in sorted(failed_models.items())
        )
        raise RuntimeError(f"Phase 2 failed for {len(failed_models)} models: {failures}")

    selected_model = max(
        all_optimal_params,
        key=lambda model_name: all_optimal_params[model_name]["silhouette_score"],
    )
    selected_params = {
        "model_name": selected_model,
        "embeddings_file": str(embedding_files[selected_model]),
        **all_optimal_params[selected_model],
    }
    selected_params_path = project_path(outputs["selected_params_file"])
    save_optimal_params(selected_params, selected_params_path)

    log_phase_end(all_optimal_params, selected_params)
    logger.info(f"Results saved under {project_path(outputs['results_dir'])}")
    logger.info(f"Selected model parameters saved to {selected_params_path}")
    return selected_params


if __name__ == "__main__":
    run()
