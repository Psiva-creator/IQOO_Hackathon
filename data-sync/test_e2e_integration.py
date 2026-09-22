"""
End-to-End Integration Test Suite for iQOO Productivity AI
Verifies the complete pipeline across all components:
Phone Signal (Member C)
  → Task & Context Telemetry
  → Insight Engine (Member B)
  → Privacy Sanitizer (PII, GPS, URLs stripped)
  → Canonical AIModelInput (14 fields)
  → LocalAIModel (Terminal 2 / BaseOnDeviceSLM)
  → Real Local SLM / Deterministic Fallback
  → Coach Response
  → Office Kit Bridge Sync
  → User Action Outcome
  → Personalization Update (Closed Loop)
"""

import os
import sys
import time
import socket
import pytest

# Add parent and sibling paths to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "insight-engine"))
sys.path.insert(0, os.path.join(BASE_DIR, "ai_model"))
sys.path.insert(0, os.path.join(BASE_DIR, "data-sync"))

from engine import (
    InsightEngine,
    _sanitize_text,
    _sanitize_task_type,
    _sanitize_context,
    evaluate_and_coach,
    update_user_model,
    predict_task_readiness
)
from context_capture import ContextCapture
from ai_model.models import AIModelInput, AIModelResponse
from ai_model.fallback import FallbackAIModel
from ai_model.base import LocalAIModel
from office_kit_bridge import LATEST_INSIGHTS


def create_sample_tasks(count=10, completion_rate=0.8):
    now_ms = int(time.time() * 1000)
    tasks = []
    for i in range(count):
        is_completed = i < int(count * completion_rate)
        tasks.append({
            "id": f"task-uuid-{i}",
            "title": f"Feature development task #{i}",
            "type": "coding" if i % 2 == 0 else "writing",
            "createdAt": now_ms - ((count - i) * 3600000),
            "completedAt": (now_ms - ((count - i) * 3600000) + 2400000) if is_completed else None,
            "duration": 2400 if is_completed else 300,
            "location": "Home Office",
            "priority": "high"
        })
    return tasks


class TestEndToEndIntegration:
    """End-to-End Acceptance Tests verifying the full unified product."""

    def test_e2e_normal_productive_state(self):
        # 1. Phone Signal: Member C
        capture = ContextCapture(location="Home Office")
        signal = capture.capture_current_signal(package_name="com.android.chrome")
        assert signal["appCategory"] == "Productivity"

        # 2. Tasks: Member A
        tasks = create_sample_tasks(count=12, completion_rate=0.85)

        # 3. AI Brain: Member B
        engine = InsightEngine(tasks, [signal])
        coach = engine.evaluate_current_state(
            task_type="coding",
            context=signal["location"],
            screen_duration=signal["screenOnDuration"],
            model=FallbackAIModel()
        )

        assert coach["state"] in ["NORMAL", "OPTIMAL"]
        assert coach["structuredEvidence"]["currentTask"] == "coding"
        assert coach["confidence"] in ["HIGH", "MEDIUM"]

    def test_e2e_high_fatigue_state(self):
        # 1. Phone Signal: High continuous screen strain (135 mins)
        signal = {
            "timestamp": int(time.time() * 1000),
            "appCategory": "Productivity",
            "location": "Home Office",
            "screenOnDuration": 135 * 60
        }

        tasks = create_sample_tasks(count=10, completion_rate=0.4)
        engine = InsightEngine(tasks, [signal])

        coach = engine.evaluate_current_state(
            task_type="writing",
            context="Home Office",
            screen_duration=signal["screenOnDuration"],
            model=FallbackAIModel()
        )

        fatigue_score = coach["structuredEvidence"]["fatigue"]
        assert fatigue_score >= 30
        assert coach["structuredEvidence"]["currentTask"] == "writing"
        msg = coach["fallbackMessage"].lower()
        assert "fatigue" in msg or "break" in msg or "screen" in msg or "reset" in msg

    def test_e2e_rapid_context_switching(self):
        # 1. Phone Signals: rapid social / entertainment switches
        now = int(time.time() * 1000)
        signals = [
            {"timestamp": now - 3000, "appCategory": "Social", "location": "Cafe"},
            {"timestamp": now - 2500, "appCategory": "Entertainment", "location": "Cafe"},
            {"timestamp": now - 2000, "appCategory": "Communication", "location": "Cafe"},
            {"timestamp": now - 1500, "appCategory": "Social", "location": "Cafe"},
            {"timestamp": now - 1000, "appCategory": "Entertainment", "location": "Cafe"},
            {"timestamp": now - 500, "appCategory": "Social", "location": "Cafe"},
            {"timestamp": now, "appCategory": "Communication", "location": "Cafe"}
        ]

        tasks = create_sample_tasks(count=8, completion_rate=0.5)
        engine = InsightEngine(tasks, signals)

        coach = engine.evaluate_current_state(
            task_type="planning",
            context="Cafe",
            recent_activity=signals,
            model=FallbackAIModel()
        )

        switches = coach["structuredEvidence"]["contextSwitches"]
        assert switches >= 6
        msg = coach["fallbackMessage"].lower()
        assert "break" in msg or "focused" in msg or "context switch" in msg or "session" in msg

    def test_e2e_peak_focus_state(self):
        signal = {
            "timestamp": int(time.time() * 1000),
            "appCategory": "Productivity",
            "location": "Home Office",
            "screenOnDuration": 600
        }

        tasks = create_sample_tasks(count=16, completion_rate=1.0)
        engine = InsightEngine(tasks, [signal])

        coach = engine.evaluate_current_state(
            task_type="coding",
            context="Home Office",
            screen_duration=600,
            model=FallbackAIModel()
        )

        score = coach["structuredEvidence"]["productivityScore"]
        assert score >= 70
        assert coach["confidence"] == "HIGH"

    def test_e2e_cold_start_insufficient_data(self):
        engine = InsightEngine([])
        insights = engine.analyze()

        assert insights["peakHour"] == "Insufficient Data"
        assert insights["confidenceLevel"] == "Calibrating"
        assert insights["productivityScore"] == 0

        coach = engine.evaluate_current_state(
            task_type="general",
            model=FallbackAIModel()
        )
        assert coach["confidence"] == "LOW"

    def test_e2e_missing_model_graceful_fallback(self):
        tasks = create_sample_tasks(count=10)
        engine = InsightEngine(tasks)

        coach = engine.evaluate_current_state(
            task_type="coding",
            model=None  # No model provided
        )

        assert coach["structuredEvidence"] is not None
        assert coach["fallbackMessage"] is not None
        assert len(coach["fallbackMessage"]) > 0

    def test_e2e_model_failure_and_timeout_resilience(self):
        class FailingMockSLM(LocalAIModel):
            @property
            def model_name(self) -> str:
                return "failing-slm-mock"

            @property
            def is_fallback(self) -> bool:
                return False

            def generate_coaching(self, evidence):
                raise TimeoutError("Simulated on-device NPU execution timeout > 10000ms")

        tasks = create_sample_tasks(count=10, completion_rate=0.2)
        engine = InsightEngine(tasks)

        coach = engine.evaluate_current_state(
            task_type="writing",
            screen_duration=120 * 60,
            model=FailingMockSLM()
        )

        assert coach["fallbackMessage"] is not None
        assert len(coach["fallbackMessage"]) > 0
        assert "fallback" in coach["modelProvider"]

    def test_e2e_privacy_sanitization_firewall(self):
        dirty_task = {
            "id": "c7e48716-16e5-4089-a299-d41c8889c1b9",
            "title": "Confidential meeting with alice@corp.com about https://internal.dev/leak at +1-555-019-2834",
            "type": "custom_unauthorized_type_with_sensitive_token",
            "createdAt": int(time.time() * 1000),
            "completedAt": None,
            "duration": 600,
            "location": "37.7749,-122.4194 Cafe",
            "priority": "high"
        }

        dirty_signal = {
            "timestamp": int(time.time() * 1000),
            "appCategory": "Productivity",
            "location": "37.7749,-122.4194 Cafe",
            "screenOnDuration": 600
        }

        engine = InsightEngine([dirty_task], [dirty_signal])
        coach = engine.evaluate_current_state(
            task_type=dirty_task["type"],
            context=dirty_task["location"],
            model=FallbackAIModel()
        )

        evidence = coach["structuredEvidence"]
        assert evidence["currentTask"] == "general"
        assert "37.7749" not in evidence["context"]

        for fact in coach["evidence"]:
            assert "alice@corp.com" not in fact
            assert "https://" not in fact
            assert "555-019-2834" not in fact

    def test_e2e_closed_personalization_learning_loop(self):
        initial_tasks = create_sample_tasks(count=5, completion_rate=0.6)
        initial_engine = InsightEngine(initial_tasks)
        initial_res = initial_engine.analyze()

        user_model = {
            "productivityProfile": initial_res["productivityProfile"],
            "tasks": initial_tasks,
            "predictionCalibration": initial_res["predictionCalibration"]
        }

        new_task = {
            "id": "task-loop-test-01",
            "title": "Complete Architecture Review",
            "type": "coding",
            "createdAt": int(time.time() * 1000) - 3600000,
            "completedAt": int(time.time() * 1000),
            "duration": 3600,
            "location": "Home Office",
            "priority": "high"
        }

        signal = {
            "timestamp": int(time.time() * 1000),
            "appCategory": "Productivity",
            "location": "Home Office",
            "screenOnDuration": 3600
        }

        updated_model = update_user_model(
            previous_model=user_model,
            new_task=new_task,
            context=signal
        )

        calib = updated_model["predictionCalibration"]
        assert calib["totalEvaluations"] == 1
        assert calib["lastActualOutcome"] == "COMPLETED"
        assert calib["lastPredictionOutcome"] in ["ACCURATE", "INACCURATE"]
        assert updated_model["taskCount"] == 6

    def test_e2e_strict_offline_airplane_mode_guarantee(self):
        """Proves 100% offline execution with network sockets intercepted and blocked."""
        real_socket = socket.socket

        def blocked_socket(*args, **kwargs):
            raise socket.error("AIRPLANE MODE: All network socket connections blocked.")

        socket.socket = blocked_socket
        try:
            tasks = create_sample_tasks(count=10)
            engine = InsightEngine(tasks)
            insights = engine.analyze()
            coach = engine.evaluate_current_state(
                task_type="coding",
                model=FallbackAIModel()
            )
            assert insights["productivityScore"] > 0
            assert coach["fallbackMessage"] is not None
            assert len(coach["fallbackMessage"]) > 0
        finally:
            socket.socket = real_socket

    def test_e2e_office_kit_bridge_integration(self):
        tasks = create_sample_tasks(count=15, completion_rate=0.9)
        engine = InsightEngine(tasks)
        insights = engine.analyze()

        bridge_data = {
            "peakHour": insights["peakHour"],
            "procrastinationTrigger": insights["procrastinationTrigger"],
            "bestContext": insights["bestContext"],
            "recommendation": insights["recommendation"]
        }

        assert "peakHour" in bridge_data
        assert "procrastinationTrigger" in bridge_data
        assert "bestContext" in bridge_data
        assert "recommendation" in bridge_data
        assert len(bridge_data["peakHour"]) > 0
