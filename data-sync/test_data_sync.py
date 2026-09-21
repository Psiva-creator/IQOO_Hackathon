"""
Comprehensive Unit & Integration Test Suite for /data-sync
Validates:
1. ContextCapture signal integrity & category detection
2. Schema conformity against contracts/context_signal.schema.json
3. DataGlue pipeline end-to-end integration with tasks + context signals
4. Schema conformity against contracts/insight.schema.json
5. Performance latency benchmarking (< 150ms)
6. Office Kit HTTP Bridge server (GET/POST /api/sync, /api/status, HTML dashboard)
"""

import unittest
import json
import os
import sys
import time
import threading
from http.server import HTTPServer
import urllib.request
import urllib.error

# Setup import paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
INSIGHT_ENGINE_DIR = os.path.join(ROOT_DIR, "insight-engine")

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
if INSIGHT_ENGINE_DIR not in sys.path:
    sys.path.append(INSIGHT_ENGINE_DIR)

from context_capture import ContextCapture, VALID_CATEGORIES, parse_dumpsys_output
from app_usage_tracker import AppUsageTracker, resolve_app_name, format_duration, AppUsageRecord
from data_glue import run_pipeline, resolve_task_data, resolve_context_signals, run_benchmark
import office_kit_bridge


class TestContextCapture(unittest.TestCase):

    def setUp(self):
        self.capture = ContextCapture(location="Home Office")

    def test_signal_structure_and_categories(self):
        signal = self.capture.capture_current_signal(package_name="com.android.chrome")
        self.assertIn("timestamp", signal)
        self.assertIn("appCategory", signal)
        self.assertIn("location", signal)
        self.assertIn("screenOnDuration", signal)
        self.assertIn(signal["appCategory"], VALID_CATEGORIES)
        self.assertEqual(signal["appCategory"], "Productivity")
        self.assertTrue(ContextCapture.validate_signal(signal))

    def test_category_mapping_heuristics(self):
        self.assertEqual(self.capture.categorize_package("com.whatsapp"), "Communication")
        self.assertEqual(self.capture.categorize_package("com.instagram.android"), "Social")
        self.assertEqual(self.capture.categorize_package("com.google.android.youtube"), "Entertainment")
        self.assertEqual(self.capture.categorize_package("com.android.settings"), "Utility")
        # Unknown package with heuristic keyword
        self.assertEqual(self.capture.categorize_package("com.mycorp.quickchat"), "Communication")
        self.assertEqual(self.capture.categorize_package("com.indie.gametube"), "Entertainment")
        self.assertEqual(self.capture.categorize_package("xyz.random.unknown"), "Other")

    def test_buffer_and_file_export(self):
        self.capture.record_signal("com.android.chrome", screen_on_duration=1200)
        self.capture.record_signal("com.whatsapp", screen_on_duration=600)
        buffer = self.capture.get_signal_buffer()
        self.assertEqual(len(buffer), 2)

        test_export_path = os.path.join(CURRENT_DIR, "_test_signals.json")
        try:
            self.capture.export_signals_to_file(test_export_path)
            self.assertTrue(os.path.exists(test_export_path))

            new_capture = ContextCapture()
            loaded = new_capture.load_signals_from_file(test_export_path)
            self.assertEqual(len(loaded), 2)
        finally:
            if os.path.exists(test_export_path):
                os.remove(test_export_path)

    def test_schema_compliance_with_contract_file(self):
        contract_path = os.path.join(ROOT_DIR, "contracts", "context_signal.schema.json")
        self.assertTrue(os.path.exists(contract_path), "Context signal contract schema must exist")
        with open(contract_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        signal = self.capture.capture_current_signal()
        for required_prop in schema.get("required", []):
            self.assertIn(required_prop, signal, f"Missing required contract property: {required_prop}")
        self.assertIn(signal["appCategory"], schema["properties"]["appCategory"]["enum"])

    def test_dumpsys_parser_with_sample_outputs(self):
        # Sample Android dumpsys window output format
        window_output = """
        WINDOW MANAGER WINDOWS (dumpsys window windows)
          mCurrentFocus=Window{8b792e8 u0 com.instagram.android/com.instagram.main.MainActivity}
          mFocusedApp=ActivityRecord{1e2a3b4 u0 com.instagram.android/.MainActivity t123}
        """
        self.assertEqual(parse_dumpsys_output(window_output), "com.instagram.android")

        activity_output = """
        Display #0 (activities from top to bottom):
          topResumedActivity=ActivityRecord{3c4d5e u0 com.google.android.youtube/com.google.android.youtube.HomeActivity t45}
        """
        self.assertEqual(parse_dumpsys_output(activity_output), "com.google.android.youtube")

        self.assertIsNone(parse_dumpsys_output(""))
        self.assertIsNone(parse_dumpsys_output("No focusable windows found"))

    def test_location_fallback_and_sanitization(self):
        sig_default = self.capture.capture_current_signal(location=None)
        self.assertEqual(sig_default["location"], "Home Office")

        sig_blank = self.capture.capture_current_signal(location="   ")
        self.assertEqual(sig_blank["location"], "Home Office")

        sig_custom = self.capture.capture_current_signal(location="Meeting Room B")
        self.assertEqual(sig_custom["location"], "Meeting Room B")

    def test_screen_duration_boundaries(self):
        sig = self.capture.record_signal("com.android.chrome", screen_on_duration=0)
        self.assertEqual(sig["screenOnDuration"], 0)
        self.assertTrue(ContextCapture.validate_signal(sig))

        sig_neg = self.capture.record_signal("com.android.chrome", screen_on_duration=-10)
        self.assertEqual(sig_neg["screenOnDuration"], 0)
        self.assertTrue(ContextCapture.validate_signal(sig_neg))


class TestDataGluePipeline(unittest.TestCase):

    def test_pipeline_execution_without_network(self):
        res = run_pipeline(sync_to_bridge=False)
        self.assertIn("insights", res)
        self.assertIn("activeContext", res)
        self.assertIn("taskCount", res)
        self.assertIn("signalCount", res)
        self.assertIn("latencyMs", res)

        insights = res["insights"]
        # Verify required contract fields
        self.assertIn("peakHour", insights)
        self.assertIn("procrastinationTrigger", insights)
        self.assertIn("bestContext", insights)
        self.assertIn("recommendation", insights)
        self.assertIn("productivityScore", insights)
        self.assertIn("fatigueLevel", insights)
        self.assertIn("distractionSensitivity", insights)
        self.assertIn("hourlyHeatmap", insights)
        self.assertIn("contextInsights", insights)

        # Value checks
        self.assertIn(insights["fatigueLevel"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIn(insights["confidenceLevel"], ["Calibrating", "Medium", "High"])
        self.assertTrue(0 <= insights["productivityScore"] <= 100)
        self.assertEqual(len(insights["hourlyHeatmap"]), 24)

    def test_pipeline_latency_target(self):
        bench = run_benchmark(iterations=10)
        self.assertLess(bench["avgMs"], 150.0, "Average latency must be well under 150ms")
        self.assertLess(bench["maxMs"], 150.0, "Max latency must be well under 150ms")

    def test_insight_contract_schema_compliance(self):
        contract_path = os.path.join(ROOT_DIR, "contracts", "insight.schema.json")
        self.assertTrue(os.path.exists(contract_path), "Insight schema contract file must exist")
        with open(contract_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        res = run_pipeline(sync_to_bridge=False)
        insights = res["insights"]

        for req in schema.get("required", []):
            self.assertIn(req, insights, f"Missing required property: {req}")

        # Validate contextInsights entries
        for ctx in insights.get("contextInsights", []):
            for ctx_req in ["context", "completionRate", "totalTasks", "completedTasks", "status"]:
                self.assertIn(ctx_req, ctx)
            self.assertIn(ctx["status"], ["Optimal", "Moderate", "Suboptimal"])


class TestOfficeKitBridge(unittest.TestCase):

    TEST_PORT = 8095
    server_thread = None
    httpd = None

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", cls.TEST_PORT), office_kit_bridge.OfficeKitBridgeHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        if cls.httpd:
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def test_bridge_get_dashboard_html(self):
        url = f"http://127.0.0.1:{self.TEST_PORT}/"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("iQOO Office Kit", content)
            self.assertIn("Companion Laptop View", content)
            self.assertIn("24-Hour Productivity Heatmap", content)

    def test_bridge_api_status(self):
        url = f"http://127.0.0.1:{self.TEST_PORT}/api/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "online")

    def test_bridge_sync_get_and_post(self):
        # 1. Test GET /api/sync
        url = f"http://127.0.0.1:{self.TEST_PORT}/api/sync"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("peakHour", data)
            self.assertIn("recommendation", data)

        # 2. Test POST /api/sync via push_to_bridge
        updated_payload = {
            "peakHour": "10:00 - 12:00 PM (Verified Focus)",
            "procrastinationTrigger": "Low energy after 4 PM",
            "bestContext": "Home Office (Focus Rate 95%)",
            "recommendation": "Maintain morning momentum.",
            "productivityScore": 92,
            "fatigueLevel": "LOW",
            "fatigueScore": 20
        }
        success = office_kit_bridge.push_to_bridge(updated_payload, host="127.0.0.1", port=self.TEST_PORT)
        self.assertTrue(success, "push_to_bridge should return True on success")

        # 3. Verify updated payload persists on server
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            latest = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(latest["peakHour"], "10:00 - 12:00 PM (Verified Focus)")
            self.assertEqual(latest["productivityScore"], 92)
            self.assertEqual(latest["fatigueLevel"], "LOW")


class TestAppUsageTracker(unittest.TestCase):

    def setUp(self):
        self.tracker = AppUsageTracker(history_file=None, min_session_seconds=2)

    def test_resolve_app_name(self):
        self.assertEqual(resolve_app_name("com.android.chrome"), "Chrome")
        self.assertEqual(resolve_app_name("com.google.android.youtube"), "YouTube")
        self.assertEqual(resolve_app_name("com.whatsapp"), "WhatsApp")
        self.assertEqual(resolve_app_name("com.instagram.android"), "Instagram")
        self.assertEqual(resolve_app_name("com.example.custom_reader"), "Custom Reader")

    def test_duration_formatting(self):
        self.assertEqual(format_duration(25), "25s")
        self.assertEqual(format_duration(60), "1 min")
        self.assertEqual(format_duration(1500), "25 min")
        self.assertEqual(format_duration(480), "8 min")

    def test_system_window_filtering(self):
        self.assertTrue(self.tracker.is_system_window("mCurrentFocus=Window{123 NotificationShade}", "com.android.systemui"))
        self.assertTrue(self.tracker.is_system_window("mCurrentFocus=Window{123 Keyguard}", "com.android.systemui"))
        self.assertTrue(self.tracker.is_system_window("mCurrentFocus=Window{123 StatusBar}", "com.android.systemui"))
        self.assertTrue(self.tracker.is_system_window("mCurrentFocus=Window{123 u0 com.sec.android.app.launcher/LauncherActivity}", "com.sec.android.app.launcher"))
        self.assertFalse(self.tracker.is_system_window("mCurrentFocus=Window{123 u0 com.android.chrome/Main}", "com.android.chrome"))

    def test_session_minimum_threshold(self):
        # 1 second session (< 2s) should be rejected
        res_short = self.tracker.record_transition("com.android.chrome", duration_seconds=1)
        self.assertIsNone(res_short)
        self.assertEqual(len(self.tracker.get_timeline()), 0)

        # 2 seconds session (>= 2s) should be accepted
        res_valid = self.tracker.record_transition("com.android.chrome", duration_seconds=2)
        self.assertIsNotNone(res_valid)
        self.assertEqual(len(self.tracker.get_timeline()), 1)

    def test_timeline_chronological_order(self):
        self.tracker.record_transition("com.android.chrome", duration_seconds=1500, timestamp_ms=1789980000000)
        self.tracker.record_transition("com.whatsapp", duration_seconds=720, timestamp_ms=1789981500000)
        self.tracker.record_transition("com.google.android.youtube", duration_seconds=1080, timestamp_ms=1789982220000)

        timeline = self.tracker.get_timeline()
        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[0]["appName"], "Chrome")
        self.assertEqual(timeline[1]["appName"], "WhatsApp")
        self.assertEqual(timeline[2]["appName"], "YouTube")

    def test_summary_aggregation_and_percentages(self):
        self.tracker.record_transition("com.android.chrome", duration_seconds=1500)
        self.tracker.record_transition("com.google.android.youtube", duration_seconds=1080)
        self.tracker.record_transition("com.android.chrome", duration_seconds=600)

        summary = self.tracker.get_summary()
        self.assertEqual(len(summary), 2)
        # Chrome should be first (1500 + 600 = 2100s)
        self.assertEqual(summary[0]["appName"], "Chrome")
        self.assertEqual(summary[0]["durationSeconds"], 2100)
        self.assertEqual(summary[0]["formattedTime"], "35 min")

        # YouTube should be second (1080s = 18 min)
        self.assertEqual(summary[1]["appName"], "YouTube")
        self.assertEqual(summary[1]["durationSeconds"], 1080)

        total_pct = sum(item["percentage"] for item in summary)
        self.assertAlmostEqual(total_pct, 100, delta=2)

    def test_tracker_persistence_save_and_load(self):
        temp_file = os.path.join(CURRENT_DIR, "_test_app_history.json")
        try:
            tracker1 = AppUsageTracker(history_file=temp_file)
            tracker1.record_transition("com.android.chrome", duration_seconds=300)
            tracker1.record_transition("com.spotify.music", duration_seconds=600)
            self.assertTrue(os.path.exists(temp_file))

            tracker2 = AppUsageTracker(history_file=temp_file)
            loaded_timeline = tracker2.get_timeline()
            self.assertEqual(len(loaded_timeline), 2)
            self.assertEqual(loaded_timeline[0]["appName"], "Chrome")
            self.assertEqual(loaded_timeline[1]["appName"], "Spotify")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_schema_compliance_with_contract_file(self):
        contract_path = os.path.join(ROOT_DIR, "contracts", "app_usage_record.schema.json")
        self.assertTrue(os.path.exists(contract_path), "App usage schema contract file must exist")
        with open(contract_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        record = self.tracker.record_transition("com.android.chrome", duration_seconds=120)
        for req in schema.get("required", []):
            self.assertIn(req, record, f"Missing required property: {req}")
        self.assertIn(record["appCategory"], schema["properties"]["appCategory"]["enum"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
