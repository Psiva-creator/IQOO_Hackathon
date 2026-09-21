"""
Comprehensive Unit Tests for the Local AI Model Integration Layer.
Validates:
1. Valid structured evidence handling
2. Missing / insufficient evidence (cold start)
3. High fatigue detection & intervention
4. High distraction & rapid context switching
5. Optimal flow state guidance
6. Fallback response & resiliency
7. Deterministic output reproducibility
8. Schema compliance & JSON serialization
9. Privacy-preserving sanitization (PII, URL, email stripping)
10. Prompt formatting & SLM response parsing
11. Pluggable on-device model registry & future Gemma/TinyLlama adapter
"""

import json
import unittest
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


class TestLocalAIModel(unittest.TestCase):
    def setUp(self):
        self.model = FallbackAIModel()

    # ------------------------------------------------------------------------
    # 1. Valid Evidence
    # ------------------------------------------------------------------------
    def test_valid_evidence_processing(self):
        """Test standard valid telemetry evidence correctly maps to structured coaching."""
        evidence = {
            "currentTask": "coding",
            "productivityScore": 72,
            "fatigue": 25,
            "fatigueLevel": "LOW",
            "distraction": 15,
            "contextSwitches": 1,
            "context": "Home Office",
            "peakWindow": "09:00 - 11:00",
            "isInPeakWindow": True,
            "prediction": 75,
            "riskLevel": "LOW",
            "confidence": "HIGH",
            "detectedTrigger": "NORMAL_PACING",
            "facts": ["Inside peak morning window", "Minimal distraction"]
        }
        resp = self.model.generate_coaching(evidence)

        self.assertIsInstance(resp, AIModelResponse)
        self.assertTrue(len(resp.message) > 10)
        self.assertTrue(len(resp.reason) > 10)
        self.assertTrue(len(resp.action) > 5)
        self.assertIn(resp.confidence, ["LOW", "MEDIUM", "HIGH"])
        self.assertTrue(resp.is_fallback)
        self.assertEqual(resp.provider, "deterministic-fallback-v1")

    # ------------------------------------------------------------------------
    # 2. Missing / Insufficient Evidence
    # ------------------------------------------------------------------------
    def test_missing_and_insufficient_evidence(self):
        """Test graceful cold-start handling with zero or sparse initial telemetry."""
        # A. Completely empty dict
        resp_empty = self.model.generate_coaching({})
        self.assertEqual(resp_empty.confidence, "LOW")
        self.assertIn("calibration", resp_empty.message.lower())
        self.assertIn("track at least 5 focus sessions", resp_empty.action.lower())

        # B. Explicit cold start input
        cold_input = AIModelInput(
            productivity_score=0,
            fatigue=0,
            context_switches=0,
            confidence="LOW",
            detected_trigger="CALIBRATING"
        )
        resp_cold = self.model.generate_coaching(cold_input)
        self.assertEqual(resp_cold.confidence, "LOW")
        self.assertIn("calibration", resp_cold.message.lower())

    # ------------------------------------------------------------------------
    # 3. High Fatigue
    # ------------------------------------------------------------------------
    def test_high_fatigue_intervention(self):
        """Test high fatigue triggers restorative recovery advice."""
        evidence = AIModelInput(
            current_task="coding",
            productivity_score=35,
            fatigue=85,
            fatigue_level="HIGH",
            context_switches=1,
            context="Home Office",
            risk_level="HIGH",
            confidence="HIGH",
            detected_trigger="HIGH_FATIGUE_STRAIN"
        )
        resp = self.model.generate_coaching(evidence)

        self.assertIn("fatigue", resp.message.lower())
        self.assertIn("break", resp.action.lower())
        self.assertEqual(resp.confidence, "HIGH")

    def test_excessive_screen_time_fatigue(self):
        """Test excessive continuous screen time produces physical reset coaching."""
        evidence = AIModelInput(
            current_task="writing",
            productivity_score=30,
            fatigue=75,
            context_switches=2,
            detected_trigger="EXCESSIVE_SCREEN_TIME"
        )
        resp = self.model.generate_coaching(evidence)
        self.assertIn("screen", resp.message.lower())
        self.assertIn("screen", resp.action.lower())

    # ------------------------------------------------------------------------
    # 4. High Distraction & Context Switching
    # ------------------------------------------------------------------------
    def test_high_distraction_and_context_switching(self):
        """Test high context switching triggers single-task focus advice."""
        evidence = AIModelInput(
            current_task="planning",
            productivity_score=40,
            fatigue=20,
            distraction=75,
            context_switches=8,
            detected_trigger="RAPID_CONTEXT_SWITCHING"
        )
        resp = self.model.generate_coaching(evidence)

        self.assertIn("switching", resp.message.lower())
        self.assertIn("notifications", resp.action.lower())
        self.assertEqual(resp.confidence, "HIGH")

    # ------------------------------------------------------------------------
    # 5. Prompt Exemplar Combination (High Fatigue + High Switching)
    # ------------------------------------------------------------------------
    def test_prompt_exemplar_combination(self):
        """
        Validates the exact example from the requirement:
        Evidence: fatigue=78, contextSwitches=7, risk=HIGH
        Fallback: "You're showing signs of fatigue and frequent context switching. Take a short break before continuing."
        """
        evidence = {
            "currentTask": "coding",
            "fatigue": 78,
            "contextSwitches": 7,
            "riskLevel": "HIGH",
            "confidence": "HIGH"
        }
        resp = self.model.generate_coaching(evidence)

        expected_msg = "You're showing signs of fatigue and frequent context switching. Take a short break before continuing."
        self.assertEqual(resp.message, expected_msg)
        self.assertIn("78/100", resp.reason)
        self.assertIn("7 context switches", resp.reason)
        self.assertIn("break", resp.action.lower())

    # ------------------------------------------------------------------------
    # 6. Optimal State
    # ------------------------------------------------------------------------
    def test_optimal_state_guidance(self):
        """Test optimal conditions protect focus momentum."""
        evidence = AIModelInput(
            current_task="coding",
            productivity_score=92,
            fatigue=10,
            distraction=5,
            context_switches=0,
            context="Home Office",
            is_in_peak_window=True,
            risk_level="LOW",
            confidence="HIGH"
        )
        resp = self.model.generate_coaching(evidence)

        self.assertIn("optimal", resp.message.lower())
        self.assertIn("momentum", resp.message.lower())
        self.assertIn("protect", resp.action.lower())
        self.assertEqual(resp.confidence, "HIGH")

    # ------------------------------------------------------------------------
    # 7. Suboptimal Context / Off-Peak Timing
    # ------------------------------------------------------------------------
    def test_vulnerable_context_coaching(self):
        """Test working in a vulnerable suboptimal context advises relocation."""
        evidence = AIModelInput(
            current_task="writing",
            productivity_score=40,
            context="Cafe",
            risk_level="HIGH",
            detected_trigger="VULNERABLE_TASK_CONTEXT"
        )
        resp = self.model.generate_coaching(evidence)

        self.assertIn("cafe", resp.message.lower())
        self.assertIn("relocate", resp.action.lower())

    # ------------------------------------------------------------------------
    # 8. Deterministic Output Reproducibility
    # ------------------------------------------------------------------------
    def test_deterministic_output(self):
        """Ensure identical inputs produce bit-for-bit identical coaching output every time."""
        evidence = AIModelInput(
            current_task="coding",
            productivity_score=55,
            fatigue=60,
            context_switches=4,
            context="Library",
            risk_level="MEDIUM"
        )
        resp1 = self.model.generate_coaching(evidence)
        resp2 = self.model.generate_coaching(evidence)

        self.assertEqual(resp1.message, resp2.message)
        self.assertEqual(resp1.reason, resp2.reason)
        self.assertEqual(resp1.action, resp2.action)
        self.assertEqual(resp1.confidence, resp2.confidence)
        self.assertEqual(resp1.provider, resp2.provider)

    # ------------------------------------------------------------------------
    # 9. Schema Compliance & Serialization
    # ------------------------------------------------------------------------
    def test_schema_and_serialization(self):
        """Verify AIModelInput and AIModelResponse serialize cleanly to match schema contracts."""
        inp = AIModelInput(
            current_task="coding",
            productivity_score=80,
            fatigue=15,
            context_switches=1,
            context="Home Office"
        )
        inp_dict = inp.to_dict(camel_case=True)
        self.assertIn("currentTask", inp_dict)
        self.assertIn("productivityScore", inp_dict)
        self.assertIn("contextSwitches", inp_dict)
        self.assertEqual(inp_dict["currentTask"], "coding")

        resp = self.model.generate_coaching(inp)
        resp_dict = resp.to_dict()
        required_keys = ["message", "reason", "action", "confidence", "provider", "isFallback"]
        for key in required_keys:
            self.assertIn(key, resp_dict)

        # JSON serialization check
        json_str = resp.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["message"], resp.message)

        # Dict subscripting check
        self.assertEqual(resp["message"], resp.message)
        self.assertEqual(resp.get("action"), resp.action)

    # ------------------------------------------------------------------------
    # 10. Privacy Enforcement (Sanitization of Personal Data)
    # ------------------------------------------------------------------------
    def test_privacy_preservation_and_sanitization(self):
        """Ensure raw PII, personal task titles, email, and URLs are stripped from AI input."""
        raw_evidence = {
            "currentTask": "Meeting with Alice about project https://secret.com/doc and email bob@iqoo.com",
            "productivityScore": 60,
            "fatigue": 20,
            "context": "Cafe near 123 Main Street at lat 37.7749",
            "facts": ["Visited https://confidential.internal for client #998877665544"]
        }
        clean_input = AIModelInput.from_dict(raw_evidence)

        # Task type must be sanitized to an approved category ("meeting")
        self.assertEqual(clean_input.current_task, "meeting")
        # URLs must be stripped from facts
        for f in clean_input.facts:
            self.assertNotIn("https://", f)
            self.assertNotIn("998877665544", f)

    # ------------------------------------------------------------------------
    # 11. Cross-Platform CamelCase API Parity
    # ------------------------------------------------------------------------
    def test_camel_case_api_alias(self):
        """Verify generateCoaching camelCase alias works identically to generate_coaching."""
        evidence = {"currentTask": "coding", "productivityScore": 85}
        resp1 = self.model.generate_coaching(evidence)
        resp2 = self.model.generateCoaching(evidence)
        self.assertEqual(resp1.message, resp2.message)

    # ------------------------------------------------------------------------
    # 12. Top-Level Convenience Helpers
    # ------------------------------------------------------------------------
    def test_top_level_convenience_function(self):
        """Verify module-level generate_coaching / generateCoaching helper."""
        resp = generate_coaching({"currentTask": "reading", "productivityScore": 75})
        self.assertIsInstance(resp, AIModelResponse)
        self.assertTrue(resp.is_fallback)

        resp2 = generateCoaching({"currentTask": "reading", "productivityScore": 75})
        self.assertEqual(resp.message, resp2.message)

    # ------------------------------------------------------------------------
    # 13. Prompt Formatting & SLM Response Parsing
    # ------------------------------------------------------------------------
    def test_prompt_formatting_and_parsing(self):
        """Test PromptFormatter constructs compact SLM prompts and parses JSON outputs."""
        evidence = AIModelInput(current_task="coding", productivity_score=80)
        prompt_standard = PromptFormatter.format_prompt(evidence, template="standard")
        self.assertIn("Telemetry Evidence:", prompt_standard)
        self.assertIn("Current Task: coding", prompt_standard)

        prompt_gemma = PromptFormatter.format_prompt(evidence, template="gemma")
        self.assertIn("<start_of_turn>user", prompt_gemma)
        self.assertIn("<start_of_turn>model", prompt_gemma)

        # Parsing valid JSON
        valid_json = json.dumps({
            "message": "You are coding with high efficiency. Maintain this rhythm.",
            "reason": "80/100 readiness in home office.",
            "action": "Continue uninterrupted for 30 minutes.",
            "confidence": "HIGH"
        })
        resp = PromptFormatter.parse_response(valid_json, fallback_model=self.model, evidence=evidence)
        self.assertFalse(resp.is_fallback)
        self.assertEqual(resp.action, "Continue uninterrupted for 30 minutes.")

        # Parsing markdown wrapped JSON (```json ... ```)
        wrapped_json = f"```json\n{valid_json}\n```"
        resp_wrapped = PromptFormatter.parse_response(wrapped_json, fallback_model=self.model, evidence=evidence)
        self.assertFalse(resp_wrapped.is_fallback)
        self.assertEqual(resp_wrapped.message, "You are coding with high efficiency. Maintain this rhythm.")

        # Resilient fallback on malformed JSON
        malformed = "This is not json at all!"
        resp_malformed = PromptFormatter.parse_response(malformed, fallback_model=self.model, evidence=evidence)
        self.assertTrue(resp_malformed.is_fallback)
        self.assertTrue(len(resp_malformed.message) > 5)

    # ------------------------------------------------------------------------
    # 14. On-Device SLM Adapter & Future Model Integration Point
    # ------------------------------------------------------------------------
    def test_on_device_slm_adapter_lifecycle(self):
        """
        Tests the BaseOnDeviceSLM adapter that represents the exact integration point
        where a future Gemma 2B or TinyLlama model will plug in.
        """
        class MockGemma2B(BaseOnDeviceSLM):
            def __init__(self, weights_loaded: bool = True):
                super().__init__(
                    model_name="gemma-2b-it-local",
                    model_path="/data/local/tmp/gemma-2b.bin" if weights_loaded else None,
                    template="gemma"
                )

            def execute_inference(self, prompt: str) -> str:
                return json.dumps({
                    "message": "Gemma says: Take a breath and focus on your coding sprint.",
                    "reason": "Telemetry indicates elevated friction.",
                    "action": "Take a 5-minute breather.",
                    "confidence": "HIGH"
                })

        # When model weights are loaded:
        active_model = MockGemma2B(weights_loaded=True)
        self.assertTrue(active_model.is_ready)
        resp_active = active_model.generate_coaching({"currentTask": "coding", "productivityScore": 50})
        self.assertFalse(resp_active.is_fallback)
        self.assertEqual(resp_active.provider, "gemma-2b-it-local")
        self.assertIn("Gemma says", resp_active.message)

        # When model weights are absent (unloaded): automatic seamless fallback!
        unloaded_model = MockGemma2B(weights_loaded=False)
        self.assertFalse(unloaded_model.is_ready)
        resp_fallback = unloaded_model.generate_coaching({"currentTask": "coding", "productivityScore": 50})
        self.assertTrue(resp_fallback.is_fallback)
        self.assertIn("fallback", resp_fallback.provider)

    # ------------------------------------------------------------------------
    # 15. Pluggable Model Registry
    # ------------------------------------------------------------------------
    def test_model_registry_factory(self):
        """Test model provider registration and factory lookup."""
        default_model = get_local_ai_model()
        self.assertIsInstance(default_model, FallbackAIModel)

        class CustomProvider(FallbackAIModel):
            @property
            def model_name(self) -> str:
                return "custom-test-provider"

        register_model_provider("custom", CustomProvider)
        custom_model = get_local_ai_model("custom")
        self.assertEqual(custom_model.model_name, "custom-test-provider")


if __name__ == "__main__":
    unittest.main()
