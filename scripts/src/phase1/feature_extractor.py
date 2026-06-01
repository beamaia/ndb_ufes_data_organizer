import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import numpy as np
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
import gc
import psutil

from src.utils.logger import logger
from src.models.model_loader import ModelLoader

# ImageNet normalization (standard for all models? will decide later)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

class FeatureExtractor:    
    def __init__(self, model_name, device='mps', batch_size=32, registry_path=None):
        """
        Initialize feature extractor with a model from registry.
        
        Args:
            model_name: Name of model from registry (e.g., 'vit_base_patch16_224', 'uni', 'resnet50')
            device: 'mps' (Metal on Mac), 'cpu', or 'cuda'
            batch_size: Batch size for feature extraction
            registry_path: Path to model registry YAML. If None, uses default.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.original_batch_size = batch_size  # track original for adaptive sizing
        
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
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Description: {self.config.description}")
        logger.info(f"  Input size: {self.config.input_size}x{self.config.input_size}")
        logger.info(f"  Output dim: {self.config.output_dim}")
        logger.info(f"  Extract method: {self.config.extract_method}")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"{'-'*80}\n")
        
        # setup caching
        self.cache_dir = self._get_cache_dir()
        self.cache_enabled = True
        self.cache_hits = 0
        self.cache_misses = 0
        
        # setup adaptive batch sizing
        self.memory_threshold_gb = 2.0  # minimum free ram threshold
        self.batch_size_levels = [self.batch_size, max(16, self.batch_size // 2), max(8, self.batch_size // 4)]
        self.current_batch_level = 0  # index batch_size_levels
    
    def _get_cache_dir(self):
        """Get cache directory for this model, creating it if needed."""
        cache_base = Path('results/phase1_feature_cache')
        cache_path = cache_base / self.model_name
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    
    def clear_cache(self):
        """Clear all cached embeddings for this model."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_hits = 0
            self.cache_misses = 0
            logger.info(f"Cleared cache for model: {self.model_name}")
    
    def _get_cache_file_path(self, patch_path):
        """Generate cache file path for a patch."""
        patch_name = Path(patch_path).stem 
        return self.cache_dir / f"{patch_name}.pkl"
    
    def _load_from_cache(self, patch_path):
        """Load embedding from cache if it exists."""
        if not self.cache_enabled:
            return None
        
        cache_file = self._get_cache_file_path(patch_path)
        if cache_file.exists():
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    embedding = pickle.load(f)
                self.cache_hits += 1
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cache for {patch_path}: {e}")
                return None
        
        self.cache_misses += 1
        return None
    
    def _save_to_cache(self, patch_path, embedding):
        """Save embedding to cache."""
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
        """Get available system ram in gb"""
        return psutil.virtual_memory().available / (1024 ** 3)
    
    def _adjust_batch_size_if_needed(self):
        """Check memory and reduce batch size if threshold exceeded"""
        available_gb = self._get_available_memory_gb()
        
        if available_gb < self.memory_threshold_gb and self.current_batch_level < len(self.batch_size_levels) - 1:
            # need to reduce batch size
            self.current_batch_level += 1
            new_batch_size = self.batch_size_levels[self.current_batch_level]
            logger.warning(f"Low memory ({available_gb:.2f}GB free). Reducing batch size from {self.batch_size} to {new_batch_size}")
            self.batch_size = new_batch_size
            return True
        elif available_gb >= self.memory_threshold_gb * 1.5 and self.current_batch_level > 0:
            # can increase batch size IF memory recovered
            self.current_batch_level -= 1
            new_batch_size = self.batch_size_levels[self.current_batch_level]
            logger.info(f"Memory recovered ({available_gb:.2f}GB free). Increasing batch size to {new_batch_size}")
            self.batch_size = new_batch_size
            return True
        
        return False
    
    def _setup_device(self, device='mps'):
        """Setup and validate device"""
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
        """Get transforms for the model based on input size"""
        input_size = self.config.input_size
        return transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=IMAGENET_MEAN,
                std=IMAGENET_STD # ? i wonder if I should always use it
            )
        ])
    
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
                # vit: use [CLS] token (position 0)
                output = self.model.forward_features(image_tensors)  # (B, num_tokens, dim)
                embeddings = output[:, 0, :]  # (B, dim) - take [CLS] token
                
            elif extract_method == "global_avg_pool":
                # ResNet, EfficientNet, Swin: global average pooling
                features = self.model.forward_features(image_tensors)  # (B, dim, H, W) or (B, num_tokens, dim)
                
                # handles transformers and cnn
                if features.dim() == 4:
                    # CNN features (B, C, H, W) -> 3d
                    embeddings = F.adaptive_avg_pool2d(features, (1, 1))  # (B, C, 1, 1)
                    embeddings = embeddings.squeeze(-1).squeeze(-1)  # (B, C)
                else:
                    # transformer features (B, num_tokens, dim) - take mean -> 2d
                    embeddings = features.mean(dim=1)  # (B, dim)
            else:
                raise ValueError(f"Unknown extract method: {extract_method}")
            
            embeddings = embeddings.cpu().numpy()
        
        # memory cleanup
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
                        # CACHE HIT - use cached embedding
                        origin_id = batch_origins[i]
                        patch_features_dict[origin_id].append(cached_emb)
                    else:
                        # CACHE MISS - need to load and extract
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
                        patch_path, _, _, origin_id = batch_images[j][1], batch_images[j][2], batch_images[j][3], batch_images[j][3]
                        self._save_to_cache(batch_images[j][1], emb)
                        patch_features_dict[batch_images[j][3]].append(emb)
                    
                    del image_tensors, embeddings, batch_images
                    gc.collect()  # force garbage collection
                
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