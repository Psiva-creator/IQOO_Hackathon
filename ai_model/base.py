"""
Base interface for Local AI Model providers.
Provides abstraction for on-device coaching generation with pluggable engines.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from .models import AIModelInput, AIModelResponse


class LocalAIModel(ABC):
    """
    Abstract interface for on-device local AI models.
    Can be backed by deterministic fallback heuristics, or future on-device SLMs
    (e.g., Gemma 2B, TinyLlama 1.1B, Phi-3, Qwen) executed via on-device runtimes.
    """

    @abstractmethod
    def generate_coaching(self, input_data: Union[AIModelInput, Dict[str, Any]]) -> AIModelResponse:
        """
        Generate natural-language coaching from structured evidence.

        Args:
            input_data: AIModelInput instance or dictionary of structured evidence.

        Returns:
            AIModelResponse: Structured coaching message, reason, action, and confidence.
        """
        pass

    def generateCoaching(self, structuredEvidence: Union[AIModelInput, Dict[str, Any]]) -> AIModelResponse:
        """
        CamelCase method alias for seamless cross-platform parity with Kotlin/Android API.
        """
        return self.generate_coaching(structuredEvidence)

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Unique identifier of the underlying model implementation."""
        pass

    @property
    @abstractmethod
    def is_fallback(self) -> bool:
        """True if this model runs offline deterministic heuristics rather than an active neural network."""
        pass

    @property
    def is_ready(self) -> bool:
        """True if the model is initialized and ready for inference."""
        return True
