import torch
import torch.nn.functional as F
from torchvision import transforms
from torchvision.transforms import InterpolationMode
from PIL import Image
import numpy as np
from pathlib import Path
import hashlib
import json
from tqdm import tqdm
from collections import defaultdict
import gc
import psutil

from src.utils.logger import logger
from src.models.model_loader import ModelLoader

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class FeatureExtractor:    
    def __init__(self, model_name, device='mps', batch_size=32, registry_path=None):
        """        
        Args:
            model_name: Name of model from registry (e.g., 'vit_base_patch16_224', 'uni', 'resnet50')
            device: 'mps' (Metal on Mac), 'cpu', or 'cuda'
            batch_size: Batch size for feature extraction
            registry_path: Path to model registry YAML. If None, uses default.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.original_batch_size = batch_size
        
        try:
            self.loader = ModelLoader(registry_path=registry_path)
            self.config = self.loader.get_model_config(model_name)
        except Exception as e:
            logger.error(f"Failed to load model config for {model_name}: {e}")
            raise
        
        self.device = self._setup_device(device)
        self.model = self.loader.load_model(model_name, device=self.device)
        self.transform = self._get_transforms()
        
        logger.info(f"{'-'*80}")
        logger.info(f"FeatureExtractor Initialized")
        logger.info(f"Model: {model_name}")
        logger.info(f"Description: {self.config.description}")
        logger.info(f"Input size: {self.config.input_size}x{self.config.input_size}")
        logger.info(f"Output dim: {self.config.output_dim}")
        logger.info(f"Extract method: {self.config.extract_method}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"{'-'*80}\n")
        
        self.cache_dir = self._get_cache_dir()
        self.cache_enabled = True
        self.cache_hits = 0
        self.cache_misses = 0
        
        self.memory_threshold_gb = 2.0
        self.batch_size_levels = [self.batch_size, max(16, self.batch_size // 2), max(8, self.batch_size // 4)]
        self.current_batch_level = 0
    
    def _get_cache_dir(self):
        cache_config = {
            "model_id": self.config.model_id,
            "input_size": self.config.input_size,
            "resize_size": self.config.resize_size,
            "crop_size": self.config.crop_size,
            "interpolation": str(self.config.interpolation),
            "output_dim": self.config.output_dim,
            "extract_method": str(self.config.extract_method),
            "normalization_mean": self.config.normalization_mean,
            "normalization_std": self.config.normalization_std,
        }
        fingerprint = hashlib.sha256(
            json.dumps(cache_config, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        cache_base = PROJECT_ROOT / 'results/phase1_feature_cache'
        cache_path = cache_base / self.model_name / fingerprint
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    
    def clear_cache(self):
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_hits = 0
            self.cache_misses = 0
            logger.info(f"Cleared cache for model: {self.model_name}")
    
    def _get_cache_file_path(self, patch_path):
        patch_name = Path(patch_path).stem 
        return self.cache_dir / f"{patch_name}.pkl"
    
    def _load_from_cache(self, patch_path):
        if not self.cache_enabled:
            return None
        
        cache_file = self._get_cache_file_path(patch_path)
        if cache_file.exists():
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    embedding = pickle.load(f)
                if np.asarray(embedding).shape[-1] != self.config.output_dim:
                    logger.warning(f"Ignoring incompatible cache entry: {cache_file}")
                    self.cache_misses += 1
                    return None
                self.cache_hits += 1
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cache for {patch_path}: {e}")
                return None
        
        self.cache_misses += 1
        return None
    
    def _save_to_cache(self, patch_path, embedding):
        if not self.cache_enabled:
            return
        
        cache_file = self._get_cache_file_path(patch_path)
        try:
            import pickle
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Failed to save cache for {patch_path}: {e}")
    
    def _get_available_memory_gb(self):
        return psutil.virtual_memory().available / (1024 ** 3)
    
    def _adjust_batch_size_if_needed(self):
        available_gb = self._get_available_memory_gb()
        
        if available_gb < self.memory_threshold_gb and self.current_batch_level < len(self.batch_size_levels) - 1:
            self.current_batch_level += 1
            new_batch_size = self.batch_size_levels[self.current_batch_level]
            logger.warning(f"Low memory ({available_gb:.2f}GB free). Reducing batch size from {self.batch_size} to {new_batch_size}")
            self.batch_size = new_batch_size
            return True
        elif available_gb >= self.memory_threshold_gb * 1.5 and self.current_batch_level > 0:
            self.current_batch_level -= 1
            new_batch_size = self.batch_size_levels[self.current_batch_level]
            logger.info(f"Memory recovered ({available_gb:.2f}GB free). Increasing batch size to {new_batch_size}")
            self.batch_size = new_batch_size
            return True
        
        return False
    
    def _setup_device(self, device='mps'):
        if device == 'mps':
            if torch.backends.mps.is_available():
                logger.info("Metal (apple M4) device available")
                return 'mps'
            else:
                logger.warning("MPS not available, falling back to CPU")
                return 'cpu'
        elif device == 'cuda':
            if torch.cuda.is_available():
                logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
                return 'cuda'
            else:
                logger.warning("CUDA not available, falling back to CPU")
                return 'cpu'
        return 'cpu'
    
    def _get_transforms(self):
        interpolation = {
            "bilinear": InterpolationMode.BILINEAR,
            "bicubic": InterpolationMode.BICUBIC,
        }[str(self.config.interpolation)]
        operations = [
            transforms.Resize(self.config.resize_size, interpolation=interpolation),
        ]
        if self.config.crop_size is not None:
            operations.append(transforms.CenterCrop(self.config.crop_size))
        operations.extend([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.config.normalization_mean,
                std=self.config.normalization_std,
            ),
        ])
        return transforms.Compose(operations)
    
    def extract_batch(self, image_tensors):
        """
        Extract embeddings from a batch of image tensors.
        Handles different extraction methods (ViT [CLS] token vs global pooling).
        
        Args:
            image_tensors: (B, 3, H, W) tensor
            
        Returns:
            embeddings: (B, D) numpy array
        """
        with torch.no_grad():
            image_tensors = image_tensors.to(self.device)
            extract_method = self.config.extract_method
            
            if extract_method == "cls_token":
                output = self.model.forward_features(image_tensors)
                embeddings = output[:, 0, :]

            elif extract_method == "cls_mean_concat":
                # Virchow: concatenate CLS with the mean of all patch tokens.
                output = self.model.forward_features(image_tensors)
                class_token = output[:, 0, :]
                mean_patch_token = output[:, 1:, :].mean(dim=1)
                embeddings = torch.cat((class_token, mean_patch_token), dim=-1)
                
            elif extract_method == "global_avg_pool":
                features = self.model.forward_features(image_tensors)
                
                if features.dim() == 4:
                    embeddings = F.adaptive_avg_pool2d(features, (1, 1))
                    embeddings = embeddings.squeeze(-1).squeeze(-1)
                else:
                    embeddings = features.mean(dim=1)
            else:
                raise ValueError(f"Unknown extract method: {extract_method}")

            if embeddings.ndim != 2 or embeddings.shape[1] != self.config.output_dim:
                raise ValueError(
                    f"{self.model_name} produced embeddings with shape "
                    f"{tuple(embeddings.shape)}; expected (batch, {self.config.output_dim})"
                )
            
            embeddings = embeddings.cpu().numpy()
        
        del image_tensors
        if self.device == 'mps':
            torch.mps.empty_cache()
        elif self.device == 'cuda':
            torch.cuda.empty_cache()
        
        return embeddings
    
    def extract_from_paths(self, patch_paths, origin_ids):
        """
        Extract embeddings from patch image files with caching and adaptive batch sizing.
        
        Args:
            patch_paths: List of image file paths
            origin_ids: Corresponding origin_id for each patch
            
        Returns:
            patch_features_dict: {origin_id: (n_patches, output_dim) array}
        """
        patch_features_dict = defaultdict(list)
        missing_patches = []
        
        logger.info(f"Processing {len(patch_paths)} patches with adaptive batch sizing...")
        
        with tqdm(total=len(patch_paths), desc="Extracting embeddings") as pbar:
            idx = 0
            while idx < len(patch_paths):
                self._adjust_batch_size_if_needed()
                
                end_idx = min(idx + self.batch_size, len(patch_paths))
                batch_paths = patch_paths[idx:end_idx]
                batch_origins = origin_ids[idx:end_idx]
                
                batch_images = []
                batch_paths_to_extract = []
                valid_indices = []
                
                for i, path in enumerate(batch_paths):
                    cached_emb = self._load_from_cache(path)
                    if cached_emb is not None:
                        origin_id = batch_origins[i]
                        patch_features_dict[origin_id].append(cached_emb)
                    else:
                        try:
                            img = Image.open(path).convert('RGB')
                            img_tensor = self.transform(img)
                            batch_images.append((img_tensor, path, i, batch_origins[i]))
                            batch_paths_to_extract.append(path)
                            valid_indices.append(i)
                        except Exception as e:
                            logger.warning(f"Failed to load {path}: {e}")
                            missing_patches.append(str(path))
                
                if batch_images:
                    image_tensors = torch.stack([b[0] for b in batch_images])
                    embeddings = self.extract_batch(image_tensors)
                    
                    for j, emb in enumerate(embeddings):
                        self._save_to_cache(batch_images[j][1], emb)
                        patch_features_dict[batch_images[j][3]].append(emb)
                    
                    del image_tensors, embeddings, batch_images
                    gc.collect()
                
                pbar.update(end_idx - idx)
                idx = end_idx
        
        for origin_id in patch_features_dict:
            patch_features_dict[origin_id] = np.array(patch_features_dict[origin_id])
        
        if missing_patches:
            logger.warning(f"Failed to load {len(missing_patches)} patches")
            for path in missing_patches[:5]:
                logger.debug(f"  - {path}")
        
        total_cache_attempts = self.cache_hits + self.cache_misses
        if total_cache_attempts > 0:
            cache_hit_rate = (self.cache_hits / total_cache_attempts) * 100
            logger.info(f"Cache Statistics: {self.cache_hits} hits / {total_cache_attempts} total ({cache_hit_rate:.1f}% hit rate)")
        
        return dict(patch_features_dict)
