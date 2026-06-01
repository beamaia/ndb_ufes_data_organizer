import pathlib as pl
import yaml
from typing import Optional, Dict
from pydantic import ValidationError

import torch
from torchvision import models as torchvision_models

from transformers import AutoModel, AutoConfig
from transformers import ViTModel, SwinModel

from src.utils.logger import logger
from src.models.schemas.model_registry import ModelRegistry, ModelConfig, SourceEnum
from src.models.model_wrappers import wrap_model

class ModelLoader:    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Args:
            registry_path: Path to model_registry.yaml. If None, uses default location.
        """
        if registry_path is None:
            registry_path = pl.Path(__file__).parent.parent / "phase1" / "config.yaml"
            registry_path = pl.Path(registry_path)
        else:
            registry_path = pl.Path(registry_path)
        
        if not registry_path.exists():
            raise FileNotFoundError(f"Registry not found at {registry_path}")
        
        self.registry_path = registry_path
        self.registry = self._load_registry()
        logger.info(f"Loaded model registry from {registry_path}")
        logger.info(f"\tTotal models available: {len(self.registry.models)}")
        logger.info(f"\tGlobal num_labels: {self.registry.num_labels}")
    
    def _load_registry(self) -> ModelRegistry:
        """Load and validate the YAML registry"""
        try:
            with open(self.registry_path, 'r') as f:
                config = yaml.safe_load(f)
            
            registry = ModelRegistry(**config)
            return registry
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {self.registry_path}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error in registry: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            raise
    
    def get_model_config(self, model_name: str) -> ModelConfig:
        """
        Get configuration for a model without loading it
        
        Args:
            model_name: Name of model in registry
            
        Returns:
            ModelConfig object with all metadata
        """
        try:
            return self.registry.get_model(model_name)
        except ValueError as e:
            logger.error(str(e))
            raise
    
    def list_available_models(self) -> Dict[str, str]:
        """Get all available models with descriptions"""
        return {
            name: config.description 
            for name, config in self.registry.models.items()
        }
    
    def list_histopathology_models(self) -> Dict[str, str]:
        """Get all histopathology models"""
        models = self.registry.list_histogram_models()
        return {
            name: config.description 
            for name, config in models.items()
        }
    
    def list_preferred_models(self) -> Dict[str, str]:
        """Get Priority 1 models"""
        models = self.registry.get_preferred_models()
        return {
            name: config.description 
            for name, config in models.items()
        }
    
    def _setup_device(self, device: str = 'mps') -> str:
        """
        Setup and validate device. Default value 'mps' for apple M4
        
        Args:
            device: 'mps' (Metal on Mac), 'cuda', or 'cpu'
            
        Returns:
            Validated device string
        """
        if device == 'mps':
            if torch.backends.mps.is_available():
                logger.info("Metal (apple m4) device available")
                return 'mps'
            else:
                logger.warning("MPS not available, falling back to cpu")
                return 'cpu'
        elif device == 'cuda':
            if torch.cuda.is_available():
                logger.info(f"CUDA device available: {torch.cuda.get_device_name(0)}")
                return 'cuda'
            else:
                logger.warning("CUDA not available, falling back to cpu")
                return 'cpu'
        else:
            logger.info("Using cpu device")
            return 'cpu'
    
    def _load_huggingface_model(self, model_config: ModelConfig, device: str):
        """
        Load model from HuggingFace Hub
        
        Args:
            model_config: ModelConfig object
            device: Target device
            
        Returns:
            Loaded model
        """
        try:
            logger.info(f"Loading HuggingFace model: {model_config.model_id}")
            
            if 'virchow' in model_config.model_id.lower():
                return self._load_virchow_model(model_config, device)
            elif 'ctranspath' in model_config.model_id.lower():
                return self._load_ctranspath_model(model_config, device)
            elif 'transpath' in model_config.model_id.lower():
                return self._load_transpath_model(model_config, device)
            
            model = AutoModel.from_pretrained(
                model_config.model_id,
                trust_remote_code=True  # some models need this or else it's not downloaded
            )
            model = model.to(device)
            model.eval()
            logger.info(f"Successfully loaded {model_config.model_id}")
            return model
        except Exception as e:
            logger.error(f"Failed to load HuggingFace model {model_config.model_id}: {e}")
            raise
    
    def _load_virchow_model(self, model_config: ModelConfig, device: str):
        """
        Load Virchow model with special configuration handling.
        Virchow has a TIMM wrapper configuration that needs num_labels to be properly set.
        Uses global num_labels from registry to avoid config initialization errors.
        """
        try:
            logger.info(f"Loading Virchow model with special handling...")
            logger.info(f"  Using global num_labels: {self.registry.num_labels}")
            
            # important: set num_labels from registry
            config = AutoConfig.from_pretrained(
                model_config.model_id,
                trust_remote_code=True,
                num_labels=self.registry.num_labels
            )

            model = AutoModel.from_pretrained(
                model_config.model_id,
                config=config,
                trust_remote_code=True
            )
            
            model = model.to(device)
            model.eval()
            logger.info(f"Successfully loaded Virchow model")
            return model
        except Exception as e:
            logger.error(f"Failed to load Virchow model: {e}")
            raise
    
    def _load_ctranspath_model(self, model_config: ModelConfig, device: str):
        """
        Load CTransPath model with special handling.
        CTransPath doesn't have a standard model_type in config.json.
        CTransPath is based on Swin Transformer, so we load it as such.
        """
        try:
            logger.info(f"Loading CTransPath model with special handling...")
            
            # CTransPath is a swin-based model
            try:
                model = AutoModel.from_pretrained(
                    model_config.model_id,
                    trust_remote_code=True,
                    _from_remote=True
                )
            except ValueError as e:
                if "Unrecognized model" in str(e):
                    logger.warning("CTransPath config missing model_type, attempting alternative loading...")
                    
                    model = SwinModel.from_pretrained(
                        model_config.model_id,
                        trust_remote_code=True
                    )
                else:
                    raise
            
            model = model.to(device)
            model.eval()
            logger.info(f"Successfully loaded CTransPath model")
            return model
        except Exception as e:
            logger.error(f"Failed to load CTransPath model: {e}")
            logger.warning("CTransPath loading failed - check HuggingFace repo availability")
            raise
    
    def _load_transpath_model(self, model_config: ModelConfig, device: str):
        """
        Load TransPath model with special configuration handling.
        TransPath doesn't have a model_type in its config.json.
        TransPath is a ViT-based model for histopathology.
        """
        try:            
            logger.info(f"Loading TransPath model with special handling...")
            
            try:
                model = AutoModel.from_pretrained(
                    model_config.model_id,
                    trust_remote_code=True,
                    _from_remote=True
                )
            except ValueError as e:
                if "Unrecognized model" in str(e):
                    logger.warning("TransPath config missing model_type, attempting ViT loading...")
                    
                    model = ViTModel.from_pretrained(
                        model_config.model_id,
                        trust_remote_code=True
                    )
                else:
                    raise
            
            model = model.to(device)
            model.eval()
            logger.info(f"Successfully loaded TransPath model")
            return model
        except Exception as e:
            logger.error(f"Failed to load TransPath model: {e}")
            logger.warning("TransPath loading failed - check HuggingFace repo availability")
            raise
    
    def _load_torchvision_model(self, model_config: ModelConfig, device: str):
        """
        Load model from torchvision
        
        Args:
            model_config: ModelConfig object
            device: Target device
            
        Returns:
            Loaded model
        """
        try:
            logger.info(f"Loading torchvision model: {model_config.model_id}")
            
            if not hasattr(torchvision_models, model_config.model_id):
                available = ", ".join([m for m in dir(torchvision_models) 
                                     if not m.startswith('_')])
                raise ValueError(
                    f"Model {model_config.model_id} not found in torchvision. "
                    f"Available (top 100): {available[:100]}..."
                )
            
            model_fn = getattr(torchvision_models, model_config.model_id)
            
            if model_config.pretrained:
                model = model_fn(weights='DEFAULT')
            else:
                model = model_fn(weights=None)
            
            model = model.to(device)
            model.eval()
            logger.info(f"Successfully loaded {model_config.model_id} from torchvision")
            return model
        except Exception as e:
            logger.error(f"Failed to load torchvision model {model_config.model_id}: {e}")
            raise
    
    def _load_custom_model(self, model_config: ModelConfig, device: str):
        """
        Load model from custom weights file
        
        Args:
            model_config: ModelConfig object
            device: Target device
            
        Returns:
            Loaded model
            
        Raises:
            ValueError: If weights_path is not specified
        """
        if model_config.weights_path is None:
            raise ValueError(
                f"Custom model '{model_config.model_id}' requires weights_path to be set. "
                f"Please specify the path to the model weights in the registry."
            )
        
        weights_path = pl.Path(model_config.weights_path)
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}"
            )
        
        try:
            logger.info(f"Loading custom model from weights: {weights_path}")
            checkpoint = torch.load(weights_path, map_location=device)
            
            if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                model_state = checkpoint['state_dict']
            elif isinstance(checkpoint, dict) and 'model' in checkpoint:
                model_state = checkpoint['model']
            else:
                model_state = checkpoint
            
            logger.info(f"Successfully loaded custom model from {weights_path}")
            return model_state 
        except Exception as e:
            logger.error(f"Failed to load custom model from {weights_path}: {e}")
            raise
    
    def load_model(self, model_name: str, device: str = 'mps'):
        """
        Load a model by name from the registry and wrap it for consistent interface.
        
        Args:
            model_name: Name of model in registry
            device: 'mps', 'cuda', or 'cpu'
            
        Returns:
            Wrapped model with forward_features() method
            
        Raises:
            ValueError: If model not found or config invalid
            FileNotFoundError: If weights file not found
        """
        model_config = self.get_model_config(model_name)
        device = self._setup_device(device)
        
        logger.info(f"{'-'*80}")
        logger.info(f"Loading model: {model_name}")
        logger.info(f"Description: {model_config.description}")
        logger.info(f"Input size: {model_config.input_size}x{model_config.input_size}")
        logger.info(f"Output dim: {model_config.output_dim}")
        logger.info(f"Extract method: {model_config.extract_method}")
        logger.info(f"Device: {device}")
        logger.info(f"{'-'*80}\n")
        
        if model_config.source == SourceEnum.huggingface:
            model = self._load_huggingface_model(model_config, device)
        elif model_config.source == SourceEnum.torchvision:
            model = self._load_torchvision_model(model_config, device)
        elif model_config.source == SourceEnum.custom:
            model = self._load_custom_model(model_config, device)
        else:
            raise ValueError(f"Unknown source: {model_config.source}")
        
        # wrap the model for forward_features() interface
        wrapped_model = wrap_model(model, model_name, str(model_config.source))
        wrapped_model = wrapped_model.to(device)
        
        logger.info(f"Model loaded and wrapped successfully\n")
        
        return wrapped_model
    
    def print_registry(self):
        """Print formatted registry information"""
        logger.info(str(self.registry))
    
    def print_available_models(self):
        """Print all available models by category and priority"""
        logger.info("\n" + str(self.registry))
        
        logger.info("\nHistopathology Models (Domain-specific):")
        for name, desc in self.list_histopathology_models().items():
            config = self.get_model_config(name)
            logger.info(f"  [{config.priority}] {name}: {desc}")
        
        logger.info("\nImageNet Models (General vision):")
        imagenet_models = self.registry.list_by_category('imagenet')
        for name, config in imagenet_models.items():
            logger.info(f"  [{config.priority}] {name}: {config.description}")