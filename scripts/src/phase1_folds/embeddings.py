from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.phase0_dataset_builder.sources import DEFAULT_PATCH_IMAGE_DIR
from src.phase1_folds.folds import DEFAULT_PATCH_TABLE
from src.utils.logger import logger


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL = "virchow"
REGISTRY = PROJECT_ROOT / "scripts/src/models/registry.yaml"
MODEL_CACHE = PROJECT_ROOT / ".cache"
EMBEDDINGS = Path("results/phase1/embeddings/virchow_patch_embeddings.npz")


def run_patch_embeddings(args: argparse.Namespace) -> dict:
    """Virchow embedding of every patch. Patches already in the extractor's cache are reused; the others are extracted and added to it."""
    from src.utils.model_environment import configure_external_model_caches

    configure_external_model_caches(MODEL_CACHE)  # before the model libraries are imported
    if not args.allow_download:
        os.environ["HF_HUB_OFFLINE"] = "1"  # the weights are in the local cache
    from src.models.feature_extractor import FeatureExtractor

    patch_ids = sorted(pd.read_csv(args.patch_table, dtype=str, keep_default_na=False)["patch_id"])
    paths = [str(Path(args.patch_image_dir) / f"{patch_id}.png") for patch_id in patch_ids]
    extractor = FeatureExtractor(MODEL, device=args.device, batch_size=args.batch_size, registry_path=str(REGISTRY))
    features = extractor.extract_from_paths(paths, patch_ids)  # every patch is its own "origin", so the result is one vector per patch

    missing = [patch_id for patch_id in patch_ids if patch_id not in features]
    if missing:
        raise ValueError(f"{len(missing)} patches have no embedding, e.g. {missing[:5]}")
    matrix = np.stack([features[patch_id][0] for patch_id in patch_ids]).astype(np.float32)
    if not np.isfinite(matrix).all():
        raise ValueError("Some embeddings contain NaN or infinite values")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, patch_ids=np.array(patch_ids), embeddings=matrix)
    logger.info(f"Saved {len(patch_ids)} embeddings of {matrix.shape[1]} numbers to {output}")
    return {
        "patches": len(patch_ids),
        "already_in_cache": extractor.cache_hits,
        "newly_extracted": extractor.cache_misses,
        "embedding_size": int(matrix.shape[1]),
        "file": str(output),
    }


def patch_embeddings_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Virchow embedding of every patch; only the patches not yet in the cache are extracted.")
    parser.add_argument("--patch-table", type=Path, default=DEFAULT_PATCH_TABLE)
    parser.add_argument("--patch-image-dir", type=Path, default=DEFAULT_PATCH_IMAGE_DIR)
    parser.add_argument("--output", type=Path, default=EMBEDDINGS)
    parser.add_argument("--device", default="mps", help="mps (Mac), cuda or cpu.")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--allow-download", action="store_true", help="Let the model libraries reach the network; by default the cached weights are used offline.")
    return parser
