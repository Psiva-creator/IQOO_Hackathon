"""
Model provider registry and pluggable on-device SLM adapter.
Allows swapping model providers (FallbackAIModel -> Gemma/TinyLlama/ONNX) without changing client code.
"""

from __future__ import annotations
import time
from abc import abstractmethod
from typing import Any, Callable, Dict, Optional, Type, Union

from .base import LocalAIModel
from .fallback import FallbackAIModel
from .formatter import PromptFormatter
from .models import AIModelInput, AIModelResponse


class BaseOnDeviceSLM(LocalAIModel):
    """
    Base adapter for on-device Small Language Models (Gemma 2B, TinyLlama 1.1B, Phi-3, etc.).
    Provides prompt formatting, token generation hooks, and automatic resilient fallback
    to FallbackAIModel if model weights are missing or inference encounters errors.
    
    This class represents the EXACT integration point where the future on-device model plugs in.
    """

    def __init__(
        self,
        model_name: str = "gemma-2b-ondevice",
        model_path: Optional[str] = None,
        template: str = "standard",
        fallback_model: Optional[FallbackAIModel] = None
    ):
        self._model_name = model_name
        self.model_path = model_path
        self.template = template
        self.fallback = fallback_model or FallbackAIModel()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_fallback(self) -> bool:
        return False

    @property
    def is_ready(self) -> bool:
        """Check if local model weights are present and engine is loaded."""
        return self.model_path is not None

    @abstractmethod
    def execute_inference(self, prompt: str) -> str:
        """
        Execute forward inference on the local model engine (e.g. MediaPipe GenAI, ONNX Runtime, ExecuTorch).
        Subclasses implement this method once small model weights are downloaded.
        """
        raise NotImplementedError("On-device model inference engine not yet connected.")

    def generate_coaching(self, input_data: Union[AIModelInput, Dict[str, Any]]) -> AIModelResponse:
        """
        Generate coaching using the on-device SLM with automatic fallback.
        1. Formats privacy-filtered structured evidence into a compact prompt.
        2. Invokes local inference.
        3. Parses the generated JSON.
        4. If inference is not ready, fails, or produces invalid output, seamlessly falls back.
        """
        start = time.perf_counter()
        evidence = input_data if isinstance(input_data, AIModelInput) else AIModelInput.from_dict(input_data)

        # If model is not loaded, immediately delegate to deterministic fallback
        if not self.is_ready:
            resp = self.fallback.generate_coaching(evidence)
            resp.provider = f"{self.model_name} (fallback: model weights not loaded)"
            return resp

        try:
            prompt = PromptFormatter.format_prompt(evidence, template=self.template)
            raw_output = self.execute_inference(prompt)
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return PromptFormatter.parse_response(
                raw_text=raw_output,
                fallback_model=self.fallback,
                evidence=evidence,
                provider=self.model_name,
                latency_ms=elapsed_ms
            )
        except Exception:
            # Automatic graceful degradation to deterministic fallback
            resp = self.fallback.generate_coaching(evidence)
            resp.provider = f"{self.model_name} (fallback on error)"
            return resp


# Model Registry for runtime provider swapping
_REGISTRY: Dict[str, Union[Type[LocalAIModel], Callable[..., LocalAIModel]]] = {
    "fallback": FallbackAIModel,
    "deterministic": FallbackAIModel,
}


def register_model_provider(name: str, provider_factory: Union[Type[LocalAIModel], Callable[..., LocalAIModel]]) -> None:
    """Register a new LocalAIModel provider into the global registry."""
    _REGISTRY[name.lower()] = provider_factory


def get_local_ai_model(provider: str = "fallback", **kwargs: Any) -> LocalAIModel:
    """
    Factory function to retrieve a LocalAIModel instance.
    Defaults to FallbackAIModel when no provider is specified or model is absent.
    """
    provider_key = provider.lower()
    if provider_key in _REGISTRY:
        factory = _REGISTRY[provider_key]
        return factory(**kwargs) if kwargs else factory()
    # Graceful default: return FallbackAIModel
    return FallbackAIModel()
