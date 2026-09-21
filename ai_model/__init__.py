"""
Local AI Model Integration Layer.
Clean, privacy-preserving abstraction for on-device natural-language coaching.
"""

from .base import LocalAIModel
from .models import AIModelInput, AIModelResponse
from .fallback import FallbackAIModel
from .formatter import PromptFormatter
from .registry import BaseOnDeviceSLM, get_local_ai_model, register_model_provider

__all__ = [
    "LocalAIModel",
    "FallbackAIModel",
    "AIModelInput",
    "AIModelResponse",
    "PromptFormatter",
    "BaseOnDeviceSLM",
    "get_local_ai_model",
    "register_model_provider",
    "generate_coaching",
    "generateCoaching",
]


def generate_coaching(evidence) -> AIModelResponse:
    """Convenience top-level function using the default local model provider."""
    model = get_local_ai_model()
    return model.generate_coaching(evidence)


generateCoaching = generate_coaching
