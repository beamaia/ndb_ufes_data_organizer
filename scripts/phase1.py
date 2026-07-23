import time
from datetime import datetime
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent.parent
EXTERNAL_MODEL_CACHE_DIR = PROJECT_ROOT / ".cache"

from src.utils.model_environment import (
    authenticate_huggingface,
    configure_external_model_caches,
)

configure_external_model_caches(EXTERNAL_MODEL_CACHE_DIR)

from src.utils.logger import logger
from src.phase1.extraction_func import (
    extract_wsi_level_features,
    create_origin_patch_mapping
)
from src.models.model_loader import ModelLoader
from src.phase1.metadata_tracker import MetadataTracker, ModelRunMetadata

REGISTRY_PATH = str(PROJECT_ROOT / 'scripts/src/phase1/config.yaml')
MODELS_TO_EXTRACT = ModelLoader(registry_path=REGISTRY_PATH).list_available_models()

SOURCE_CSV_PATH = str(PROJECT_ROOT / 'data/ndb_ufes/patch/parcial_pndb_ufes.csv')
PATCH_IMAGE_DIR = str(PROJECT_ROOT / 'data/ndb_ufes/patch_level/images')
OUTPUT_MAPPING_CSV = str(PROJECT_ROOT / 'data/ndb_ufes/patch_level/csvs/origin_patch_mapping.csv')

EMBEDDINGS_OUTPUT_DIR = str(PROJECT_ROOT / 'data/embeddings/')
CACHE_DIR = str(PROJECT_ROOT / 'results/phase1/feature_cache')

BATCH_SIZE = 32
DEVICE = 'mps'
LOG_SEPARATOR = "-" * 80


def log_phase_start(run_timestamp: str):
    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 1: FEATURE EXTRACTION PIPELINE")
    logger.info(LOG_SEPARATOR)
    logger.info(f"Run timestamp: {run_timestamp}")
    logger.info("")


def log_step_start(step_number: int, description: str):
    logger.info(LOG_SEPARATOR)
    logger.info(f"STEP {step_number}: {description}")
    logger.info(LOG_SEPARATOR)
    logger.info("")


def log_model_start(idx: int, total_models: int, model_name: str, model_config):
    logger.info(LOG_SEPARATOR)
    logger.info(f"MODEL {idx}/{total_models}: {model_name.upper()}")
    logger.info(LOG_SEPARATOR)
    logger.info("")
    logger.info(f"Model config: {model_config.description}")
    logger.info(f"\tPriority: {model_config.priority}")
    logger.info(f"\tCategory: {model_config.category}")
    logger.info(f"\tOutput dim: {model_config.output_dim}")
    logger.info("")
    logger.info(f"Extracting features for {model_name}...")


def log_phase_end(
    successful_extractions: int,
    total_models: int,
    metadata_tracker: MetadataTracker
):
    stats = metadata_tracker.get_stats()

    logger.info(LOG_SEPARATOR)
    logger.info("PHASE 1 COMPLETE")
    logger.info(LOG_SEPARATOR)
    logger.info("")
    logger.info("Extraction summary:")
    logger.info(f"\tSuccessfully extracted {successful_extractions}/{total_models} models")
    logger.info("")
    logger.info("Overall Statistics:")
    logger.info(f"\tSuccess Rate: {stats['success_rate']:.1f}%")
    logger.info(f"\tAvg Extraction Time: {stats['avg_extraction_time']:.2f}s")
    logger.info(f"\tTotal Patches Processed: {stats['total_patches_processed']}")
    logger.info(f"\tTotal Extraction Time: {stats['total_extraction_time']:.2f}s")
    logger.info("")
    logger.info(LOG_SEPARATOR)
    logger.info("Metadata Location:")
    logger.info(f"\tMaster File: {metadata_tracker.master_file}")
    logger.info(f"\tSummary File: {metadata_tracker.metadata_dir / 'runs_summary.txt'}")
    logger.info(LOG_SEPARATOR)
    logger.info("")


def cleanup_cache():
    cache_path = Path(CACHE_DIR)
    if cache_path.exists():
        logger.info("Cleaning up temporary cache...")
        shutil.rmtree(cache_path)
        logger.info("Cache cleaned\n")


def run(device: str = DEVICE, batch_size: int = BATCH_SIZE):
    """
    Run Phase 1: Feature Extraction Pipeline
    
    Args:
        device: Device ('mps', 'cuda', or 'cpu')
        batch_size: Batch size for feature extraction
    """
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    metadata_tracker = MetadataTracker()
    
    log_phase_start(run_timestamp)
    
    logger.info("Authenticating with HuggingFace Hub")
    authenticate_huggingface(PROJECT_ROOT / ".env")
    logger.info("Successfully authenticated")
    logger.info("")
    
    logger.info("Loading model registry")
    loader = ModelLoader()
    logger.info(f"Registry loaded with {len(loader.registry.models)} models")
    logger.info("")
    
    log_step_start(1, "Creating origin-patch mapping (one-time)")
    
    origin_patch_mapping = create_origin_patch_mapping(
        source_csv_path=SOURCE_CSV_PATH,
        patch_image_dir=PATCH_IMAGE_DIR,
        output_csv_path=OUTPUT_MAPPING_CSV
    )
    
    total_models = len(loader.registry.models)
    successful_extractions = 0
    
    for idx, (model_name, model_config) in enumerate(loader.registry.models.items(), 1):
        log_model_start(idx, total_models, model_name, model_config)
        
        extraction_start_time = time.time()
        
        try:
            embeddings_path = extract_wsi_level_features(
                model_name=model_name,
                origin_patch_mapping=origin_patch_mapping,
                batch_size=batch_size,
                device=device
            )
            
            extraction_duration = time.time() - extraction_start_time
            
            num_patches = len(origin_patch_mapping)
            num_origins = len(origin_patch_mapping)
            patches_per_second = num_patches / extraction_duration if extraction_duration > 0 else 0
            
            metadata = ModelRunMetadata(
                run_timestamp=run_timestamp,
                model_name=model_name,
                model_id=model_config.model_id,
                description=model_config.description,
                priority=model_config.priority,
                category=str(model_config.category),
                source=str(model_config.source),
                extract_method=str(model_config.extract_method),
                input_size=model_config.input_size,
                output_dim=model_config.output_dim,
                batch_size=batch_size,
                device=device,
                num_labels=loader.registry.num_labels,
                pretrained=model_config.pretrained,
                num_patches=num_patches,
                num_origins=num_origins,
                avg_patches_per_origin=num_patches / num_origins if num_origins > 0 else 0,
                cache_hits=num_patches,  # from cache (if using feature cache)
                cache_total=num_patches,
                cache_hit_rate_percent=100.0,  # features are cached
                extraction_duration_seconds=extraction_duration,
                patches_per_second=patches_per_second,
                embeddings_output_path=str(embeddings_path),
                status="success"
            )
            
            metadata_tracker.add_run(metadata)
            successful_extractions += 1
            
            logger.info(f"Extraction complete: {embeddings_path}")
            
        except Exception as e:
            extraction_duration = time.time() - extraction_start_time
            
            metadata = ModelRunMetadata(
                run_timestamp=run_timestamp,
                model_name=model_name,
                model_id=model_config.model_id,
                description=model_config.description,
                priority=model_config.priority,
                category=str(model_config.category),
                source=str(model_config.source),
                extract_method=str(model_config.extract_method),
                input_size=model_config.input_size,
                output_dim=model_config.output_dim,
                batch_size=batch_size,
                device=device,
                num_labels=loader.registry.num_labels,
                pretrained=model_config.pretrained,
                num_patches=0,
                num_origins=0,
                avg_patches_per_origin=0.0,
                cache_hits=0,
                cache_total=0,
                cache_hit_rate_percent=0.0,
                extraction_duration_seconds=extraction_duration,
                patches_per_second=0.0,
                embeddings_output_path="",
                status="failed",
                error_message=str(e)
            )
            
            metadata_tracker.add_run(metadata)
            
            logger.error(f"Extraction failed for {model_name}: {e}")
        
        logger.info(LOG_SEPARATOR)
        logger.info("")
    
    metadata_tracker.save()
    log_phase_end(successful_extractions, total_models, metadata_tracker)

if __name__ == "__main__":
    run()
