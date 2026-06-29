import pathlib as pl
import warnings
from enum import Enum
from aenum import MultiValueEnum
from pydantic import BaseModel, Field, model_validator
from typing import Optional

class SourceEnum(str, Enum):
    huggingface = "huggingface"
    torchvision = "torchvision"
    custom = "custom"
    
    def __str__(self):
        return self.value

class CategoryEnum(str, Enum):
    histopathology = "histopathology"
    imagenet = "imagenet"
    
    def __str__(self):
        return self.value

class ExtractMethodEnum(str, Enum):
    cls_token = "cls_token"
    cls_mean_concat = "cls_mean_concat"
    global_avg_pool = "global_avg_pool"
    
    def __str__(self):
        return self.value


class InterpolationEnum(str, Enum):
    bilinear = "bilinear"
    bicubic = "bicubic"

    def __str__(self):
        return self.value

class ModelConfig(BaseModel):
    description: str = Field(alias="description")
    source: SourceEnum = Field(alias="source")
    model_id: str = Field(alias="model_id")
    category: CategoryEnum = Field(alias="category")
    priority: int = Field(alias="priority")
    input_size: int = Field(alias="input_size")
    resize_size: int = Field(alias="resize_size")
    crop_size: Optional[int] = Field(alias="crop_size")
    interpolation: InterpolationEnum = Field(alias="interpolation")
    output_dim: int = Field(alias="output_dim")
    extract_method: ExtractMethodEnum = Field(alias="extract_method")
    pretrained: bool = Field(True, alias="pretrained")
    weights_path: Optional[str] = Field(None, alias="weights_path")
    normalization_mean: list[float] = Field(alias="normalization_mean")
    normalization_std: list[float] = Field(alias="normalization_std")
    
    @model_validator(mode="after")
    def validate_priority(self):
        if not 1 <= self.priority <= 3:
            raise ValueError(f"Priority must be between 1-3, got {self.priority}")
        return self
    
    @model_validator(mode="after")
    def validate_dimensions(self):
        if self.input_size <= 0:
            raise ValueError(f"input_size must be positive, got {self.input_size}")
        if self.resize_size <= 0:
            raise ValueError(f"resize_size must be positive, got {self.resize_size}")
        if self.crop_size is not None and self.crop_size <= 0:
            raise ValueError(f"crop_size must be positive, got {self.crop_size}")
        if self.output_dim <= 0:
            raise ValueError(f"output_dim must be positive, got {self.output_dim}")
        if len(self.normalization_mean) != 3 or len(self.normalization_std) != 3:
            raise ValueError("normalization_mean and normalization_std must have three values")
        if any(value <= 0 for value in self.normalization_std):
            raise ValueError("normalization_std values must be positive")
        return self
    
    @model_validator(mode="after")
    def validate_custom_weights(self):
        if self.source == SourceEnum.custom and self.weights_path is None:
            warnings.warn(
                f"Model '{self.model_id}' has source='custom' but weights_path is null. "
                f"You must provide a path to the model weights for this to work.",
                UserWarning
            )
        return self

class ModelRegistry(BaseModel):
    num_labels: int = Field(default=3, alias="num_labels")
    models: dict[str, ModelConfig] = Field(alias="models")
    
    def get_model(self, model_name: str) -> ModelConfig:
        if model_name not in self.models:
            available = ", ".join(self.models.keys())
            raise ValueError(f"Model '{model_name}' not found. Available: {available}")
        return self.models[model_name]
    
    def list_by_category(self, category: CategoryEnum) -> dict[str, ModelConfig]:
        return {
            name: model for name, model in self.models.items()
            if model.category == category
        }
    
    def list_by_priority(self, priority: int) -> dict[str, ModelConfig]:
        return {
            name: model for name, model in self.models.items()
            if model.priority == priority
        }
    
    def list_histogram_models(self) -> dict[str, ModelConfig]:
        return self.list_by_category(CategoryEnum.histopathology)
    
    def get_preferred_models(self) -> dict[str, ModelConfig]:
        return self.list_by_priority(1)
    
    def __str__(self):
        dashes = "-" * 90
        message = f"\n{dashes}\nMODEL REGISTRY SUMMARY\n{dashes}\n"
        message += f"Global num_labels parameter: {self.num_labels}\n"
        
        for priority in [1, 2, 3]:
            models_at_priority = self.list_by_priority(priority)
            if models_at_priority:
                priority_label = {1: "RECOMMENDED", 2: "GOOD", 3: "ALTERNATIVE"}[priority]
                message += f"\n** Priority {priority} ({priority_label}):\n"
                for name, model in models_at_priority.items():
                    message += f"  - {name}: {model.description}\n"
        
        message += f"\n{dashes}\nTOTAL MODELS: {len(self.models)}\n{dashes}\n"
        return message