import os
from pathlib import Path

from dotenv import load_dotenv


def configure_external_model_caches(cache_root: Path) -> None:
    """Configure model-library caches beneath the provided directory."""
    cache_root = Path(cache_root).resolve()
    huggingface_home = cache_root / "huggingface"
    huggingface_hub_cache = huggingface_home / "hub"
    transformers_cache = cache_root / "transformers"
    torch_home = cache_root / "torch"

    for cache_dir in (
        huggingface_home,
        huggingface_hub_cache,
        transformers_cache,
        torch_home,
    ):
        cache_dir.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(huggingface_home)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(huggingface_hub_cache)
    os.environ["HF_HUB_CACHE"] = str(huggingface_hub_cache)
    os.environ["TRANSFORMERS_CACHE"] = str(transformers_cache)
    os.environ["TORCH_HOME"] = str(torch_home)


def authenticate_huggingface(env_path: Path | None = None) -> None:
    """Authenticate with a token from the environment or cached Hub login."""
    if env_path is not None:
        load_dotenv(env_path)

    from huggingface_hub import login

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if token:
        login(token=token)
    else:
        login()
