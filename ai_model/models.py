"""
Data models and contracts for the Local AI Model Integration Layer.
Defines AIModelInput (privacy-filtered telemetry evidence) and AIModelResponse (structured coaching).
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union

# Whitelist of allowed sanitized task types to ensure no raw personal notes leak
ALLOWED_TASK_TYPES = {
    "coding", "writing", "meeting", "reading", "planning",
    "exercise", "design", "research", "admin", "general"
}

# Whitelist of sanitized context locations
STANDARD_CONTEXTS = {
    "home office", "office", "cafe", "library", "meeting room",
    "transit", "home", "remote", "focus room"
}


def _sanitize_string(val: str, max_length: int = 120) -> str:
    """
    Strip potential PII, URLs, GPS coordinates, UUIDs, MAC addresses, phone numbers,
    and long numeric IDs from string values.
    """
    if not val:
        return ""
    # Strip URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "[URL_REDACTED]", str(val))
    # Strip email addresses
    cleaned = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_REDACTED]", cleaned)
    # Strip GPS coordinates (e.g. 37.7749, -122.4194)
    cleaned = re.sub(r"[-+]?\d{1,3}\.\d+,\s*[-+]?\d{1,3}\.\d+", "[GPS_REDACTED]", cleaned)
    # Strip UUIDs / device IDs
    cleaned = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "[DEVICE_ID_REDACTED]", cleaned)
    # Strip MAC addresses
    cleaned = re.sub(r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", "[DEVICE_ID_REDACTED]", cleaned)
    # Strip phone numbers
    cleaned = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]", cleaned)
    # Strip large digit sequences (>= 7 digits)
    cleaned = re.sub(r"\b\d{7,}\b", "[ID_REDACTED]", cleaned)
    return cleaned.strip()[:max_length]


@dataclass
class AIModelInput:
    """
    Structured, privacy-preserving evidence passed from the Insight Engine to the Local AI Model.
    Contains only aggregated behavioral metrics; strips raw personal titles, notes, and coordinates.
    """
    current_task: str = "general"
    productivity_score: int = 50
    fatigue: int = 0
    fatigue_level: str = "LOW"
    distraction: int = 0
    context_switches: int = 0
    context: str = "Home Office"
    peak_window: str = "09:00 - 11:00"
    is_in_peak_window: bool = False
    prediction: int = 50
    risk_level: str = "LOW"
    confidence: str = "MEDIUM"
    detected_trigger: Optional[str] = None
    facts: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Clamp numeric ranges
        self.productivity_score = max(0, min(100, int(self.productivity_score)))
        self.fatigue = max(0, min(100, int(self.fatigue)))
        self.distraction = max(0, min(100, int(self.distraction)))
        self.context_switches = max(0, int(self.context_switches))
        self.prediction = max(0, min(100, int(self.prediction)))

        # Sanitize task type: do not allow raw task titles like "Fix bug with client John Doe"
        t_clean = re.sub(r"[^a-zA-Z0-9\s_-]", " ", str(self.current_task)).lower()
        matched = False
        for allowed in ALLOWED_TASK_TYPES:
            if re.search(r"\b" + re.escape(allowed) + r"\b", t_clean):
                self.current_task = allowed
                matched = True
                break
        if not matched:
            raw_stripped = str(self.current_task).strip().lower()
            if re.fullmatch(r"[a-z0-9_-]{1,24}", raw_stripped) and not any(ch.isdigit() for ch in raw_stripped[:3]):
                if not re.search(r"https?://|www\.|\@|[-+]?\d{1,3}\.\d+", raw_stripped):
                    self.current_task = raw_stripped
                    matched = True
            if not matched:
                self.current_task = "general"

        # Normalize enum fields
        self.fatigue_level = self.fatigue_level.upper() if self.fatigue_level in ["LOW", "MEDIUM", "HIGH"] else (
            "HIGH" if self.fatigue >= 65 else ("MEDIUM" if self.fatigue >= 35 else "LOW")
        )
        self.risk_level = self.risk_level.upper() if self.risk_level in ["LOW", "MEDIUM", "HIGH"] else "LOW"
        self.confidence = self.confidence.upper() if self.confidence in ["LOW", "MEDIUM", "HIGH"] else "MEDIUM"

        # Sanitize context location
        ctx_clean = str(self.context).strip()
        if ctx_clean.lower() in STANDARD_CONTEXTS:
            self.context = ctx_clean.title()
        elif re.search(r"[-+]?\d{1,3}\.\d+", ctx_clean) or re.search(r"https?://|www\.", ctx_clean):
            self.context = "Home Office"
        else:
            sanitized_ctx = _sanitize_string(ctx_clean, max_length=30)
            self.context = sanitized_ctx.title() if sanitized_ctx else "Home Office"

        # Sanitize peak window
        self.peak_window = _sanitize_string(str(self.peak_window), max_length=30) or "09:00 - 11:00"

        # Sanitize detected trigger
        if self.detected_trigger:
            self.detected_trigger = _sanitize_string(str(self.detected_trigger), max_length=40)

        # Sanitize facts list
        self.facts = [_sanitize_string(f, max_length=120) for f in self.facts if f]

    # CamelCase aliases for Kotlin / Android schema compatibility
    @property
    def currentTask(self) -> str:
        return self.current_task

    @property
    def productivityScore(self) -> int:
        return self.productivity_score

    @property
    def fatigueLevel(self) -> str:
        return self.fatigue_level

    @property
    def contextSwitches(self) -> int:
        return self.context_switches

    @property
    def peakWindow(self) -> str:
        return self.peak_window

    @property
    def isInPeakWindow(self) -> bool:
        return self.is_in_peak_window

    @property
    def riskLevel(self) -> str:
        return self.risk_level

    @property
    def detectedTrigger(self) -> Optional[str]:
        return self.detected_trigger

    def to_dict(self, camel_case: bool = True) -> Dict[str, Any]:
        """Convert input evidence to dictionary adhering to contracts/ai_model.schema.json."""
        if camel_case:
            return {
                "currentTask": self.current_task,
                "productivityScore": self.productivity_score,
                "fatigue": self.fatigue,
                "fatigueLevel": self.fatigue_level,
                "distraction": self.distraction,
                "contextSwitches": self.context_switches,
                "context": self.context,
                "peakWindow": self.peak_window,
                "isInPeakWindow": self.is_in_peak_window,
                "prediction": self.prediction,
                "riskLevel": self.risk_level,
                "confidence": self.confidence,
                "detectedTrigger": self.detected_trigger,
                "facts": list(self.facts)
            }
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AIModelInput:
        """Create AIModelInput from arbitrary dict supporting camelCase or snake_case."""
        if not data:
            return cls(
                productivity_score=0,
                fatigue=0,
                distraction=0,
                context_switches=0,
                confidence="LOW",
                detected_trigger="CALIBRATING"
            )

        # Handle nested structuredEvidence if present
        evidence = data.get("structuredEvidence", data)

        task = (
            evidence.get("currentTask") or
            evidence.get("current_task") or
            evidence.get("taskType") or
            evidence.get("task_type") or
            "general"
        )
        score = (
            evidence.get("productivityScore") or
            evidence.get("productivity_score") or
            evidence.get("score") or
            50
        )
        fatigue_val = evidence.get("fatigue")
        if isinstance(fatigue_val, dict):
            fatigue_score = fatigue_val.get("score", 0)
            fatigue_lvl = fatigue_val.get("level", "LOW")
        else:
            fatigue_score = (
                evidence.get("fatigueScore") or
                evidence.get("fatigue_score") or
                fatigue_val or
                0
            )
            fatigue_lvl = (
                evidence.get("fatigueLevel") or
                evidence.get("fatigue_level") or
                ("HIGH" if int(fatigue_score) >= 65 else ("MEDIUM" if int(fatigue_score) >= 35 else "LOW"))
            )

        distraction_val = evidence.get("distraction")
        if isinstance(distraction_val, dict):
            distraction_score = distraction_val.get("score", 0)
        else:
            distraction_score = (
                evidence.get("distractionScore") or
                evidence.get("distraction_score") or
                distraction_val or
                0
            )

        switches = (
            evidence.get("contextSwitches") or
            evidence.get("context_switches") or
            evidence.get("recentContextSwitches") or
            evidence.get("recent_context_switches") or
            0
        )

        ctx = (
            evidence.get("context") or
            evidence.get("location") or
            evidence.get("currentContext") or
            "Home Office"
        )

        peak = (
            evidence.get("peakWindow") or
            evidence.get("peak_window") or
            evidence.get("bestFocusWindow") or
            evidence.get("best_focus_window") or
            evidence.get("peakHour") or
            "09:00 - 11:00"
        )

        is_peak = bool(
            evidence.get("isInPeakWindow") or
            evidence.get("is_in_peak_window", False)
        )

        pred = (
            evidence.get("prediction") or
            evidence.get("predictedScore") or
            evidence.get("predicted_score") or
            score
        )

        risk = (
            evidence.get("riskLevel") or
            evidence.get("risk_level") or
            evidence.get("risk") or
            ("HIGH" if int(pred) < 45 else ("MEDIUM" if int(pred) < 70 else "LOW"))
        )

        conf = (
            evidence.get("confidence") or
            evidence.get("confidenceLevel") or
            evidence.get("confidence_level") or
            "MEDIUM"
        )

        trigger = (
            evidence.get("detectedTrigger") or
            evidence.get("detected_trigger") or
            evidence.get("trigger")
        )

        facts_raw = evidence.get("facts") or evidence.get("evidence") or []
        facts = list(facts_raw) if isinstance(facts_raw, list) else []

        return cls(
            current_task=str(task),
            productivity_score=int(score),
            fatigue=int(fatigue_score),
            fatigue_level=str(fatigue_lvl),
            distraction=int(distraction_score),
            context_switches=int(switches),
            context=str(ctx),
            peak_window=str(peak),
            is_in_peak_window=is_peak,
            prediction=int(pred),
            risk_level=str(risk),
            confidence=str(conf),
            detected_trigger=str(trigger) if trigger else None,
            facts=facts
        )

    @classmethod
    def from_evidence(cls, evidence: Dict[str, Any]) -> AIModelInput:
        """Alias for from_dict for semantic clarity when receiving structured evidence."""
        return cls.from_dict(evidence)


@dataclass
class AIModelResponse:
    """
    Structured natural-language coaching output produced by a Local AI Model or deterministic fallback.
    Complies strictly with contracts/ai_model.schema.json.
    """
    message: str
    reason: str
    action: str
    confidence: str = "HIGH"
    provider: str = "fallback"
    is_fallback: bool = True
    model_name: Optional[str] = None
    latency_ms: float = 0.0

    def __post_init__(self):
        # Enforce non-empty string defaults
        if not self.message:
            self.message = "Take a short pause to refresh your cognitive focus."
        if not self.reason:
            self.reason = "Routine focus pacing checkpoint."
        if not self.action:
            self.action = "Pause for 5 minutes."

        self.confidence = self.confidence.upper() if self.confidence in ["LOW", "MEDIUM", "HIGH"] else "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary adhering to contracts/ai_model.schema.json."""
        return {
            "message": self.message,
            "reason": self.reason,
            "action": self.action,
            "confidence": self.confidence,
            "provider": self.provider,
            "isFallback": self.is_fallback
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    # Dictionary-like subscripting support (response["message"])
    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        if key in d:
            return d[key]
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
