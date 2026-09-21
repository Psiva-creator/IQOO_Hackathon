"""
Convenience module in insight-engine exposing the Local AI Model Integration Layer.
Enables seamless integration with InsightEngine while maintaining clean separation of concerns.
"""

import os
import sys

# Ensure root directory is on python path for importing ai_model package
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from ai_model import (
    LocalAIModel,
    FallbackAIModel,
    AIModelInput,
    AIModelResponse,
    PromptFormatter,
    BaseOnDeviceSLM,
    get_local_ai_model,
    register_model_provider,
    generate_coaching,
    generateCoaching
)

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
    "generateCoaching"
]
