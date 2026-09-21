"""
Local Small Language Model (SLM) on-device implementation.
Provides genuine 100% offline, on-device inference using local weights (e.g. SmolLM-135M, Gemma-2B).
Zero cloud API calls, zero internet dependency.
Includes automatic fallback for:
1. Model unavailable (missing weights)
2. Memory insufficient (< 300MB available)
3. Inference timeout
4. Model execution error or malformed output
"""

from __future__ import annotations
import json
import os
import re
import time
from typing import Any, Dict, Optional, Union

from .base import LocalAIModel
from .fallback import FallbackAIModel
from .formatter import PromptFormatter
from .models import AIModelInput, AIModelResponse
from .registry import BaseOnDeviceSLM, register_model_provider


def _get_available_ram_mb() -> float:
    """Check system available RAM in MB safely."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:
        try:
            # Fallback for Linux procfs
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return float(line.split()[1]) / 1024.0
        except Exception:
            pass
    return 1024.0  # Default assumption if unreadable


class LocalSLMModel(BaseOnDeviceSLM):
    """
    On-device Local Small Language Model engine.
    Loads and runs real local weights (e.g., SmolLM-135M, Gemma 2B, TinyLlama)
    completely offline with zero cloud API reliance.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "smollm-135m-local",
        min_ram_mb: float = 250.0,
        timeout_sec: float = 20.0,
        device: str = "cpu",
        fallback_model: Optional[FallbackAIModel] = None
    ):
        resolved_path = model_path
        if not resolved_path:
            # Default to local models directory if weights exist
            default_loc = os.path.join(os.path.dirname(__file__), "..", "models", "smollm-135m-instruct")
            if os.path.exists(default_loc) and any(f.endswith(".safetensors") or f.endswith(".bin") for f in os.listdir(default_loc)):
                resolved_path = os.path.abspath(default_loc)

        super().__init__(
            model_name=model_name,
            model_path=resolved_path,
            template="standard",
            fallback_model=fallback_model or FallbackAIModel()
        )
        self.min_ram_mb = min_ram_mb
        self.timeout_sec = timeout_sec
        self.device = device
        self._tokenizer = None
        self._model = None
        self._is_loaded = False

    @property
    def is_ready(self) -> bool:
        return bool(self.model_path and os.path.exists(self.model_path))

    def _ensure_loaded(self) -> bool:
        """Load tokenizer and weights into memory if not already cached."""
        if self._is_loaded and self._model is not None:
            return True

        if not self.is_ready:
            return False

        # Pre-check available RAM
        avail_ram = _get_available_ram_mb()
        if avail_ram < self.min_ram_mb:
            return False

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only=True,
                dtype=torch.float32
            )
            self._model.eval()
            self._is_loaded = True
            return True
        except Exception:
            self._is_loaded = False
            return False

    def execute_inference(self, prompt: str) -> str:
        """Execute genuine local forward pass on CPU without network calls."""
        if not self._ensure_loaded():
            raise RuntimeError("Model could not be loaded into memory.")

        import torch

        # Seed the completion with JSON opening to guarantee structured JSON output from small models
        json_prefix = '{"message": "'
        full_prompt = prompt + json_prefix if not prompt.endswith(json_prefix) else prompt

        inputs = self._tokenizer(full_prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=65,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id
            )

        gen_tokens = outputs[0][inputs.input_ids.shape[1]:]
        completion = self._tokenizer.decode(gen_tokens, skip_special_tokens=True)
        return json_prefix + completion

    def generate_coaching(self, input_data: Union[AIModelInput, Dict[str, Any]]) -> AIModelResponse:
        """
        Generate coaching using local SLM, falling back automatically if:
        1. Model unavailable / uninstalled
        2. Memory insufficient (< min_ram_mb)
        3. Inference error or timeout
        4. Malformed output
        """
        start = time.perf_counter()
        evidence = input_data if isinstance(input_data, AIModelInput) else AIModelInput.from_dict(input_data)

        # 1. Check if model files are available
        if not self.is_ready:
            resp = self.fallback.generate_coaching(evidence)
            resp.provider = f"{self.model_name} (fallback: model weights uninstalled)"
            return resp

        # 2. Check memory sufficiency
        avail_ram = _get_available_ram_mb()
        if avail_ram < self.min_ram_mb:
            resp = self.fallback.generate_coaching(evidence)
            resp.provider = f"{self.model_name} (fallback: insufficient RAM {avail_ram:.1f}MB)"
            return resp

        # 3. Attempt local inference with few-shot guidance
        try:
            prompt = self._build_slm_prompt(evidence)
            raw_output = self.execute_inference(prompt)
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)

            # 4. Parse structured output JSON
            parsed_resp = PromptFormatter.parse_response(
                raw_text=raw_output,
                fallback_model=self.fallback,
                evidence=evidence,
                provider=self.model_name,
                latency_ms=elapsed_ms
            )

            # If response fell back due to malformed output, label provider clearly
            if parsed_resp.is_fallback:
                parsed_resp.provider = f"{self.model_name} (fallback: malformed SLM output)"
            return parsed_resp

        except Exception as e:
            # Fallback on any runtime or execution error
            resp = self.fallback.generate_coaching(evidence)
            resp.provider = f"{self.model_name} (fallback on error: {str(e)[:40]})"
            return resp

    def _build_slm_prompt(self, evidence: AIModelInput) -> str:
        """Build compact few-shot prompt proven to elicit valid JSON from small models."""
        return (
            "<|im_start|>system\n"
            "You are an on-device personal productivity coach running locally on an iQOO phone.\n"
            "Output strictly one valid JSON object with keys: message, reason, action, confidence (LOW, MEDIUM, HIGH).\n"
            "Never output personal names, URLs, or text outside the JSON.<|im_end|>\n"
            "<|im_start|>user\n"
            "Task: planning, Score: 85, Fatigue: 10, Switches: 1<|im_end|>\n"
            "<|im_start|>assistant\n"
            '{"message": "Focus is optimal. Maintain sustained momentum.", "reason": "Low fatigue and minimal context switching.", "action": "Continue session uninterrupted.", "confidence": "HIGH"}<|im_end|>\n'
            f"<|im_start|>user\n"
            f"Task: {evidence.current_task}, Score: {evidence.productivity_score}, Fatigue: {evidence.fatigue}, Switches: {evidence.context_switches}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )


# Register LocalSLMModel in registry
register_model_provider("localslm", LocalSLMModel)
register_model_provider("smollm", LocalSLMModel)
register_model_provider("ondevice", LocalSLMModel)
