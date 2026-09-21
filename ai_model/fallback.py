"""
Deterministic offline fallback coach implementation.
Operates 100% locally and offline without external dependencies or neural networks.
Guarantees deterministic, reproducible, explainable coaching for any telemetry state.
"""

from __future__ import annotations
import time
from typing import Any, Dict, Union

from .base import LocalAIModel
from .models import AIModelInput, AIModelResponse


class FallbackAIModel(LocalAIModel):
    """
    Deterministic rule-based offline coach.
    Ensures the application provides intelligent, structured, supportive coaching
    even when no local small LLM is installed or available on the device.
    """

    @property
    def model_name(self) -> str:
        return "deterministic-fallback-v1"

    @property
    def is_fallback(self) -> bool:
        return True

    def generate_coaching(self, input_data: Union[AIModelInput, Dict[str, Any]]) -> AIModelResponse:
        """
        Generate deterministic structured coaching from telemetry evidence.
        Guaranteed to produce identical output for identical inputs.
        """
        start_time = time.perf_counter()

        # Parse and sanitize input evidence
        if isinstance(input_data, AIModelInput):
            evidence = input_data
        elif isinstance(input_data, dict):
            evidence = AIModelInput.from_dict(input_data)
        else:
            evidence = AIModelInput()

        task = evidence.current_task
        score = evidence.productivity_score
        fatigue = evidence.fatigue
        fatigue_lvl = evidence.fatigue_level
        distraction = evidence.distraction
        switches = evidence.context_switches
        ctx = evidence.context
        peak = evidence.peak_window
        is_peak = evidence.is_in_peak_window
        risk = evidence.risk_level
        conf = evidence.confidence
        trigger = evidence.detected_trigger

        # 1. Missing / Insufficient Evidence (Cold Start)
        is_insufficient = (
            conf == "LOW" and
            (score == 0 or score == 50) and
            fatigue == 0 and
            switches == 0 and
            trigger in [None, "NONE", "CALIBRATING", "LOW_CONFIDENCE"]
        )
        if is_insufficient:
            msg = "Focus calibration in progress. Log your focus blocks to unlock personalized coaching."
            reason = "Insufficient behavioral telemetry to detect detailed fatigue or context patterns."
            action = "Track at least 5 focus sessions across different hours to calibrate your personal model."
            return AIModelResponse(
                message=msg,
                reason=reason,
                action=action,
                confidence="LOW",
                provider=self.model_name,
                is_fallback=True,
                latency_ms=round((time.perf_counter() - start_time) * 1000.0, 3)
            )

        # 2. High Fatigue + Frequent Context Switching (Prompt Exemplar Rule)
        # Example: fatigue=78, contextSwitches=7, risk=HIGH
        # Output: "You're showing signs of fatigue and frequent context switching. Take a short break before continuing."
        if (fatigue >= 65 or fatigue_lvl == "HIGH") and (switches >= 5 or distraction >= 50):
            msg = "You're showing signs of fatigue and frequent context switching. Take a short break before continuing."
            reason = f"Fatigue score is elevated ({fatigue}/100) and {switches} context switches were detected under {risk} risk."
            action = "Take a short 10-minute break before continuing."
            res_conf = "HIGH" if conf in ["HIGH", "MEDIUM"] else "MEDIUM"

        # 3. High Fatigue / Screen Strain
        elif fatigue >= 65 or fatigue_lvl == "HIGH" or trigger in ["HIGH_FATIGUE_STRAIN", "EXCESSIVE_SCREEN_TIME", "SEVERE_COGNITIVE_BURNOUT"]:
            if trigger == "EXCESSIVE_SCREEN_TIME":
                msg = f"Extended screen time is depleting your cognitive endurance. Step away from {task} for a screen break."
                reason = f"Fatigue level is high ({fatigue}/100) due to continuous screen strain."
                action = "Step away from all screens for a 15-minute physical reset."
            else:
                msg = f"High fatigue detected during {task}. Step away for a restorative break before resuming."
                reason = f"Cognitive fatigue score ({fatigue}/100) has reached the high threshold."
                action = "Take a 15-minute recovery walk or pause active tasks."
            res_conf = "HIGH"

        # 4. High Distraction / Context Switching
        elif switches >= 6 or distraction >= 60 or trigger == "RAPID_CONTEXT_SWITCHING":
            msg = f"Frequent context switching detected during {task}. Close secondary tabs and focus on one milestone."
            reason = f"Elevated distraction with {switches} context switches disrupting sustained attention."
            action = "Mute non-essential notifications and start a 25-minute single-task sprint."
            res_conf = "HIGH"

        # 5. Suboptimal Context / Off-Peak Friction / High Risk
        elif trigger in ["VULNERABLE_TASK_CONTEXT", "OFF_PEAK_FRICTION", "PRODUCTIVITY_DROP"] or risk == "HIGH":
            if trigger == "VULNERABLE_TASK_CONTEXT":
                msg = f"Working on {task} in {ctx} shows high friction. Relocate to your best focus environment or shift to planning."
                reason = f"Historical completion for {task} is significantly lower in {ctx}."
                action = "Relocate this session or shift to structured planning work."
            elif not is_peak and peak not in ["Insufficient Data", "None detected"]:
                msg = f"Working outside your peak window. Cap this {task} block at 25 minutes and reschedule deep work to {peak}."
                reason = f"Timing is outside your calibrated peak window ({peak}) with elevated task friction."
                action = f"Cap current session at 25 minutes and schedule demanding blocks for {peak}."
            else:
                msg = f"Readiness for {task} is at risk. Take a short breather and simplify your immediate task goal."
                reason = f"Composite focus readiness ({score}/100) indicates elevated friction in {ctx}."
                action = "Take a 5-minute breather before starting a focused sprint."
            res_conf = "MEDIUM" if conf == "LOW" else "HIGH"

        # 6. Optimal Flow State
        elif score >= 80 and fatigue < 35 and switches <= 2 and risk != "HIGH":
            msg = f"Optimal focus state achieved for {task}. Maintain your sustained momentum."
            reason = f"High productivity readiness ({score}/100) with low fatigue and minimal interruptions in {ctx}."
            action = f"Protect this focus block and continue uninterrupted in {ctx}."
            res_conf = "HIGH"

        # 7. Normal Pacing (Default Steady State)
        else:
            msg = f"Pacing is steady for {task}. Keep working through your current milestone."
            reason = f"Balanced productivity readiness ({score}/100) with manageable fatigue levels."
            action = "Continue your current task block with planned regular intervals."
            res_conf = "MEDIUM" if conf == "LOW" else "HIGH"

        latency = round((time.perf_counter() - start_time) * 1000.0, 3)
        return AIModelResponse(
            message=msg,
            reason=reason,
            action=action,
            confidence=res_conf,
            provider=self.model_name,
            is_fallback=True,
            latency_ms=latency
        )
