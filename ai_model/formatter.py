"""
Prompt and Evidence Formatter for Local On-Device Small Language Models (SLMs).
Provides token-efficient prompt construction and resilient JSON response parsing
for future models such as Gemma 2B, TinyLlama 1.1B, Phi-3-mini, and Qwen 1.5B.
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional

from .fallback import FallbackAIModel
from .models import AIModelInput, AIModelResponse


class PromptFormatter:
    """
    Formats structured evidence into compact on-device LLM prompts
    and parses generated text back into structured AIModelResponse objects.
    """

    SYSTEM_INSTRUCTION = (
        "You are an on-device personal productivity coach running locally on an iQOO smartphone.\n"
        "Analyze the provided behavioral telemetry evidence and output exactly one JSON object with natural-language coaching.\n"
        "Rules:\n"
        "1. Never output personal data, names, or URLs.\n"
        "2. Keep the message to 1-2 concise, supportive, actionable sentences.\n"
        "3. Output strictly valid JSON with keys: 'message', 'reason', 'action', 'confidence' (LOW, MEDIUM, HIGH).\n"
        "4. No conversational filler or markdown formatting outside the JSON."
    )

    @classmethod
    def format_evidence_block(cls, evidence: AIModelInput) -> str:
        """Format privacy-preserving telemetry into a compact text block."""
        facts_str = "; ".join(evidence.facts[:3]) if evidence.facts else "No anomalous flags"
        return (
            f"Telemetry Evidence:\n"
            f"- Current Task: {evidence.current_task}\n"
            f"- Focus Score: {evidence.productivity_score}/100\n"
            f"- Cognitive Fatigue: {evidence.fatigue}/100 ({evidence.fatigue_level})\n"
            f"- Context Switches: {evidence.context_switches} (Distraction: {evidence.distraction}/100)\n"
            f"- Environment: {evidence.context}\n"
            f"- Peak Window: {evidence.peak_window} (In Peak: {evidence.is_in_peak_window})\n"
            f"- Predicted Readiness: {evidence.prediction}/100 (Risk: {evidence.risk_level})\n"
            f"- Calibration Confidence: {evidence.confidence}\n"
            f"- Primary Trigger: {evidence.detected_trigger or 'None'}\n"
            f"- Observations: {facts_str}"
        )

    @classmethod
    def format_prompt(cls, evidence: AIModelInput, template: str = "standard") -> str:
        """
        Build an SLM prompt tailored to specific on-device model chat templates.

        Supported templates:
        - 'standard': Clean universal system/user format
        - 'gemma': Gemma-specific turn format (<start_of_turn>user...<start_of_turn>model)
        - 'tinyllama': TinyLlama format (<|user|>...<|assistant|>)
        """
        evidence_text = cls.format_evidence_block(evidence)

        if template == "gemma":
            return (
                f"<start_of_turn>user\n"
                f"{cls.SYSTEM_INSTRUCTION}\n\n"
                f"{evidence_text}\n"
                f"Respond with JSON:\n"
                f"<start_of_turn>model\n"
            )
        elif template == "tinyllama":
            return (
                f"<|system|>\n"
                f"{cls.SYSTEM_INSTRUCTION}</s>\n"
                f"<|user|>\n"
                f"{evidence_text}</s>\n"
                f"<|assistant|>\n"
            )
        else:
            return (
                f"=== SYSTEM ===\n"
                f"{cls.SYSTEM_INSTRUCTION}\n\n"
                f"=== EVIDENCE ===\n"
                f"{evidence_text}\n\n"
                f"=== COACH OUTPUT (JSON) ===\n"
            )

    @classmethod
    def parse_response(
        cls,
        raw_text: str,
        fallback_model: Optional[FallbackAIModel] = None,
        evidence: Optional[AIModelInput] = None,
        provider: str = "local-slm",
        latency_ms: float = 0.0
    ) -> AIModelResponse:
        """
        Parse raw model text output into AIModelResponse.
        If the output is malformed or invalid JSON, automatically invokes
        the FallbackAIModel to guarantee resilient 100% uptime.
        """
        if not raw_text or not raw_text.strip():
            return cls._fallback_or_default(fallback_model, evidence, "Empty model response")

        # Strip markdown code fences if model wrapped response in ```json ... ```
        cleaned = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Look for outermost curly braces
            brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            json_str = brace_match.group(1) if brace_match else cleaned

        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed JSON is not a dictionary")

            msg = str(parsed.get("message", "")).strip()
            reason = str(parsed.get("reason", "")).strip()
            action = str(parsed.get("action", "")).strip()
            conf = str(parsed.get("confidence", "HIGH")).strip().upper()

            # Verify required fields
            if not msg or not action:
                raise ValueError("Missing required fields (message or action)")

            return AIModelResponse(
                message=msg,
                reason=reason or "On-device model generated coaching advice.",
                action=action,
                confidence=conf if conf in ["LOW", "MEDIUM", "HIGH"] else "HIGH",
                provider=provider,
                is_fallback=False,
                latency_ms=latency_ms
            )
        except Exception:
            # Resilient fallback on any JSON parse error
            return cls._fallback_or_default(fallback_model, evidence, "Malformed model output")

    @classmethod
    def _fallback_or_default(
        cls,
        fallback_model: Optional[FallbackAIModel],
        evidence: Optional[AIModelInput],
        reason_note: str
    ) -> AIModelResponse:
        if fallback_model is not None:
            resp = fallback_model.generate_coaching(evidence or AIModelInput())
            resp.provider = f"{resp.provider} (recovered from {reason_note})"
            return resp
        return AIModelResponse(
            message="Take a short pause to refresh your cognitive focus.",
            reason=f"Offline fallback active ({reason_note}).",
            action="Pause for 5 minutes before resuming.",
            confidence="MEDIUM",
            provider="fallback-recovery",
            is_fallback=True
        )
