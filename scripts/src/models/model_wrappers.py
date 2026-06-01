import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Union
from src.utils.logger import logger


class BaseModelWrapper(nn.Module):    
    def __init__(self, model, model_type: str):
        super().__init__()
        self.model = model
        self.model_type = model_type
        self.model.eval()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Standard forward pass returning embeddings"""
        return self.forward_features(x)
    
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract features from input. Should be overridden by subclasses.
        
        Args:
            x: Input tensor (B, 3, H, W)
            
        Returns:
            Features. Shape varies by model:
            - Transformer models: (B, num_tokens, D)
            - CNN models: (B, C, H, W)
        """
        raise NotImplementedError(f"forward_features not implemented for {self.model_type}")

class HFViTWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        HF ViT outputs: (B, num_tokens, D) with CLS token at position 0
        """
        outputs = self.model(x, output_hidden_states=False)
        # HF vit returns last_hidden_state which is (B, num_tokens, D)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class HFDeiTWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        HF DeiT outputs: (B, num_tokens, D)
        """
        outputs = self.model(x, output_hidden_states=False)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class HFSwinWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        HF Swin outputs final stage features.
        Returns spatial features, not token-based.
        """
        outputs = self.model(x, output_hidden_states=False)
        # swin returns (B, H*W, D) or (B, C, H, W) depending on version
        # last_hidden_state is (B, num_patches, D)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class HFSwinTransformerWrapper(BaseModelWrapper):    
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        HF Swin Transformer V2 - returns spatial features
        """
        outputs = self.model(x, output_hidden_states=False)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class HFPathologyFoundationWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Pathology foundation models are ViTs pretrained on histopathology.
        Output: (B, num_tokens, D) with CLS token at position 0
        
        Handles different output formats robustly.
        """
        try:
            outputs = self.model(x, output_hidden_states=False)
            
            # last_hidden_state (standard HF transformer output)
            if hasattr(outputs, 'last_hidden_state'):
                last_hidden_state = outputs.last_hidden_state
            # models might return outputs directly  
            elif isinstance(outputs, torch.Tensor):
                last_hidden_state = outputs
            #nested structure
            elif hasattr(outputs, 'hidden_states'):
                last_hidden_state = outputs.hidden_states[-1]
            else:
                # assume first output is the embeddings
                last_hidden_state = outputs[0] if isinstance(outputs, tuple) else outputs
            
            return last_hidden_state
        except Exception as e:
            logger.warning(f"Error in {self.__class__.__name__}.forward_features: {e}")
            raise


class UNIWrapper(HFPathologyFoundationWrapper):
    """Specific wrapper for UNI model (MahmoodLab/UNI)"""
    pass

class VirchowWrapper(HFPathologyFoundationWrapper):
    """Specific wrapper for Virchow model (paige-ai/Virchow)"""
    pass

class CTransPathWrapper(HFPathologyFoundationWrapper):
    """Specific wrapper for CTransPath model (kaczmarj/CTransPath)"""
    pass

class HFMoCoV3VitWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        MoCo v3 ViT outputs: (B, num_tokens, D)
        """
        outputs = self.model(x, output_hidden_states=False)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class HFTransPathNetWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        TransPathNet is a ViT-based model pretrained on histopathology.
        """
        outputs = self.model(x, output_hidden_states=False)
        last_hidden_state = outputs.last_hidden_state
        return last_hidden_state


class TorchvisionResNetWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        ResNet uses sequential feature extraction.
        We extract features before the final classification layers.
        Output: (B, C, H, W) spatial feature maps
        """
        x = self.model.conv1(x)
        x = self.model.bn1(x)
        x = self.model.relu(x)
        x = self.model.maxpool(x)
        
        x = self.model.layer1(x)
        x = self.model.layer2(x)
        x = self.model.layer3(x)
        x = self.model.layer4(x)
        
        # at this point: (B, 2048, 7, 7) for typical ResNet input of 224x224
        return x


class TorchvisionEfficientNetWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        EfficientNet extracts features layer by layer.
        Output: (B, C, H, W) spatial feature maps
        """
        # EfficientNet has a features attribute that is a Sequential module
        x = self.model.features(x)
        return x


class TorchvisionDenseNetWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        DenseNet extracts features from the dense blocks.
        Output: (B, C, H, W) spatial feature maps
        """
        x = self.model.features(x)
        return x


class TimmModelWrapper(BaseModelWrapper):
    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        TIMM models often have forward_features() natively.
        If not, fall back to forward() and handle the output.
        """
        if hasattr(self.model, 'forward_features'):
            return self.model.forward_features(x)
        else:
            output = self.model(x)
            return output


class ModelWrapperFactory:
    def wrap(self, model, model_name: str, source: str) -> BaseModelWrapper:
        """
        Wrap a model with the appropriate wrapper class.
        
        Args:
            model: The loaded PyTorch model
            model_name: Name/ID of the model from registry
            source: Source of the model ('huggingface', 'torchvision', 'custom', 'timm')
            
        Returns:
            Wrapped model with consistent forward_features() interface
        """
        
        logger.info(f"Wrapping model: {model_name}")
        
        if source == 'huggingface':
            return self._wrap_huggingface(model, model_name)
        
        elif source == 'torchvision':
            return self._wrap_torchvision(model, model_name)
        
        elif source == 'timm':
            logger.info(f"  -> Using TIMM model wrapper")
            return TimmModelWrapper(model, model_name)
        
        else:
            logger.warning(f"Unknown source {source}, using generic TIMM wrapper")
            return TimmModelWrapper(model, model_name)
    
    def __call__(self, model, model_name: str, source: str) -> BaseModelWrapper:
        """Allow the factory to be called directly"""
        return self.wrap(model, model_name, source)
    
    def _wrap_huggingface(self, model, model_name: str) -> BaseModelWrapper:
        """Wrap HuggingFace models with appropriate wrapper"""
        
        # pathology foundation models
        if 'uni' in model_name.lower() or 'MahmoodLab' in str(model):
            logger.info(f"  -> Using UNI wrapper")
            return UNIWrapper(model, model_name)
        
        elif 'virchow' in model_name.lower() or 'paige' in str(model):
            logger.info(f"  -> Using Virchow wrapper")
            return VirchowWrapper(model, model_name)
        
        elif 'ctranspath' in model_name.lower():
            logger.info(f"  -> Using CTransPath wrapper")
            return CTransPathWrapper(model, model_name)
        
        elif 'transpath' in model_name.lower():
            logger.info(f"  -> Using TransPathNet wrapper")
            return HFTransPathNetWrapper(model, model_name)
        
        elif 'mocov3' in model_name.lower() or 'mocov3_vit' in model_name.lower():
            logger.info(f"  -> Using MoCo V3 ViT wrapper")
            return HFMoCoV3VitWrapper(model, model_name)
        
        # vit
        elif 'vit' in model_name.lower() and 'deit' not in model_name.lower():
            logger.info(f"  -> Using HF ViT wrapper")
            return HFViTWrapper(model, model_name)
        
        elif 'deit' in model_name.lower():
            logger.info(f"  -> Using DeiT wrapper")
            return HFDeiTWrapper(model, model_name)
        
        elif 'swin' in model_name.lower():
            # check if it's SwinTransformer v2
            if 'swinv2' in model_name.lower() or 'v2' in model_name.lower():
                logger.info(f"  -> Using Swin Transformer V2 wrapper")
                return HFSwinTransformerWrapper(model, model_name)
            else:
                logger.info(f"  -> Using Swin Transformer wrapper")
                return HFSwinWrapper(model, model_name)
        
        else:
            logger.info(f"  -> Using generic HF ViT wrapper (default for HuggingFace)")
            return HFViTWrapper(model, model_name)
    
    def _wrap_torchvision(self, model, model_name: str) -> BaseModelWrapper:
        """Wrap Torchvision models with appropriate wrapper"""
        
        if 'resnet' in model_name.lower():
            logger.info(f"  -> Using Torchvision ResNet wrapper")
            return TorchvisionResNetWrapper(model, model_name)
        
        elif 'efficientnet' in model_name.lower():
            logger.info(f"  -> Using Torchvision EfficientNet wrapper")
            return TorchvisionEfficientNetWrapper(model, model_name)
        
        elif 'densenet' in model_name.lower():
            logger.info(f"  -> Using Torchvision DenseNet wrapper")
            return TorchvisionDenseNetWrapper(model, model_name)
        
        else:
            logger.warning(f"  -> No specific wrapper for {model_name}, using ResNet wrapper")
            return TorchvisionResNetWrapper(model, model_name)


wrap_model = ModelWrapperFactory()
