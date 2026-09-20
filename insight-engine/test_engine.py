import unittest
import time
from synthetic_generator import generate_synthetic_tasks, generate_synthetic_tasks_and_signals
from engine import InsightEngine

class TestInsightEngine(unittest.TestCase):
    def setUp(self):
        self.tasks, self.signals = generate_synthetic_tasks_and_signals(days=7)
        self.engine = InsightEngine(self.tasks, self.signals)

    # 1. Existing tests and backward compatibility
    def test_insight_structure_backward_compatibility(self):
        # Engine called with ONLY tasks, preserving existing signature
        standalone_engine = InsightEngine(self.tasks)
        insights = standalone_engine.analyze()
        required_keys = [
            "peakHour", "procrastinationTrigger", "bestContext", "recommendation",
            "productivityScore", "confidenceLevel", "hourlyHeatmap",
            "fatigueLevel", "fatigueScore", "explanation", "contextInsights", "distractionSensitivity"
        ]
        for key in required_keys:
            self.assertIn(key, insights)
            self.assertIsNotNone(insights[key])

    def test_peak_hour_morning_detection(self):
        insights = self.engine.analyze()
        self.assertTrue("09:00" in insights["peakHour"] or "10:00" in insights["peakHour"])

    def test_procrastination_detection(self):
        insights = self.engine.analyze()
        self.assertIn("Writing", insights["procrastinationTrigger"])

    def test_confidence_level(self):
        insights = self.engine.analyze()
        self.assertEqual(insights["confidenceLevel"], "High")

    def test_hourly_heatmap(self):
        insights = self.engine.analyze()
        heatmap = insights["hourlyHeatmap"]
        self.assertEqual(len(heatmap), 24)
        self.assertGreater(heatmap["9"], 50)

    # 2. Insufficient data
    def test_insufficient_data(self):
        empty_engine = InsightEngine([], [])
        insights = empty_engine.analyze()
        self.assertEqual(insights["confidenceLevel"], "Calibrating")
        self.assertEqual(insights["productivityScore"], 0)
        self.assertEqual(insights["fatigueLevel"], "LOW")
        self.assertEqual(insights["fatigueScore"], 0)
        self.assertEqual(insights["contextInsights"], [])
        self.assertEqual(insights["distractionSensitivity"]["level"], "LOW")
        self.assertIn("Insufficient data", insights["explanation"])

    # 3. Normal productivity
    def test_normal_productivity(self):
        base_ms = int(time.time() * 1000)
        healthy_tasks = [
            {"id": "1", "title": "T1", "type": "coding", "createdAt": base_ms, "completedAt": base_ms + 1800000, "duration": 1800, "location": "Home Office", "priority": "high"},
            {"id": "2", "title": "T2", "type": "coding", "createdAt": base_ms + 2000000, "completedAt": base_ms + 3800000, "duration": 1800, "location": "Home Office", "priority": "high"},
            {"id": "3", "title": "T3", "type": "writing", "createdAt": base_ms + 4000000, "completedAt": base_ms + 5800000, "duration": 1800, "location": "Home Office", "priority": "medium"},
            {"id": "4", "title": "T4", "type": "planning", "createdAt": base_ms + 6000000, "completedAt": base_ms + 7800000, "duration": 1800, "location": "Home Office", "priority": "low"},
            {"id": "5", "title": "T5", "type": "coding", "createdAt": base_ms + 8000000, "completedAt": base_ms + 9800000, "duration": 1800, "location": "Home Office", "priority": "medium"}
        ]
        healthy_signals = [
            {"timestamp": base_ms, "appCategory": "Productivity", "location": "Home Office", "screenOnDuration": 1200},
            {"timestamp": base_ms + 4000000, "appCategory": "Productivity", "location": "Home Office", "screenOnDuration": 1500}
        ]
        engine = InsightEngine(healthy_tasks, healthy_signals)
        insights = engine.analyze()
        self.assertEqual(insights["fatigueLevel"], "LOW")
        self.assertEqual(insights["productivityScore"], 100)
        self.assertEqual(insights["contextInsights"][0]["status"], "Optimal")
        self.assertEqual(insights["contextInsights"][0]["completionRate"], 100.0)

    # 4. High fatigue detection
    def test_high_fatigue(self):
        # Morning tasks completed, afternoon tasks abandoned + excessive screen duration
        t_morning = 1789271100000 # 9 AM
        t_afternoon = 1789293600000 # 3:30 PM
        fatigued_tasks = [
            {"id": "1", "title": "M1", "type": "coding", "createdAt": t_morning, "completedAt": t_morning + 3600000, "duration": 3600, "location": "Home Office", "priority": "high"},
            {"id": "2", "title": "M2", "type": "coding", "createdAt": t_morning + 4000000, "completedAt": t_morning + 7600000, "duration": 3600, "location": "Home Office", "priority": "high"},
            {"id": "3", "title": "A1", "type": "writing", "createdAt": t_afternoon, "completedAt": None, "duration": 300, "location": "Cafe", "priority": "low"},
            {"id": "4", "title": "A2", "type": "writing", "createdAt": t_afternoon + 3600000, "completedAt": None, "duration": 200, "location": "Cafe", "priority": "low"}
        ]
        fatigued_signals = [
            {"timestamp": t_afternoon, "appCategory": "Social", "location": "Cafe", "screenOnDuration": 8500},
            {"timestamp": t_afternoon + 3600000, "appCategory": "Entertainment", "location": "Cafe", "screenOnDuration": 9200}
        ]
        engine = InsightEngine(fatigued_tasks, fatigued_signals)
        insights = engine.analyze()
        self.assertEqual(insights["fatigueLevel"], "HIGH")
        self.assertGreaterEqual(insights["fatigueScore"], 65)
        self.assertIn("Fatigue is HIGH", insights["explanation"])

    # 5. Context correlation with better and worse environments
    def test_low_completion_context(self):
        tasks = [
            {"id": "1", "title": "T1", "type": "coding", "createdAt": 1000, "completedAt": 2000, "duration": 1000, "location": "Home Office", "priority": "high"},
            {"id": "2", "title": "T2", "type": "coding", "createdAt": 3000, "completedAt": 4000, "duration": 1000, "location": "Home Office", "priority": "high"},
            {"id": "3", "title": "T3", "type": "coding", "createdAt": 5000, "completedAt": 6000, "duration": 1000, "location": "Home Office", "priority": "high"},
            {"id": "4", "title": "T4", "type": "writing", "createdAt": 7000, "completedAt": None, "duration": 300, "location": "Cafe", "priority": "low"},
            {"id": "5", "title": "T5", "type": "writing", "createdAt": 9000, "completedAt": None, "duration": 200, "location": "Cafe", "priority": "low"}
        ]
        engine = InsightEngine(tasks)
        insights = engine.analyze()
        ctx_list = insights["contextInsights"]
        self.assertEqual(len(ctx_list), 2)
        home = next(c for c in ctx_list if c["context"] == "Home Office")
        cafe = next(c for c in ctx_list if c["context"] == "Cafe")
        self.assertEqual(home["completionRate"], 100.0)
        self.assertEqual(home["status"], "Optimal")
        self.assertEqual(cafe["completionRate"], 0.0)
        self.assertEqual(cafe["status"], "Suboptimal")
        self.assertIn("Home Office", insights["bestContext"])

    # 6. Distraction-heavy context
    def test_distraction_heavy_context(self):
        tasks = [
            {"id": "1", "title": "W1", "type": "writing", "createdAt": 1000, "completedAt": None, "duration": 150, "location": "Cafe", "priority": "high"},
            {"id": "2", "title": "W2", "type": "writing", "createdAt": 2000, "completedAt": None, "duration": 120, "location": "Cafe", "priority": "medium"}
        ]
        signals = [
            {"timestamp": 1000, "appCategory": "Social", "location": "Cafe", "screenOnDuration": 4000},
            {"timestamp": 2000, "appCategory": "Entertainment", "location": "Cafe", "screenOnDuration": 5000}
        ]
        engine = InsightEngine(tasks, signals)
        insights = engine.analyze()
        distraction = insights["distractionSensitivity"]
        self.assertEqual(distraction["level"], "HIGH")
        self.assertIn("writing", distraction["vulnerableCategories"])
        self.assertIn("Social", distraction["triggerAppCategories"])
        self.assertIn("Entertainment", distraction["triggerAppCategories"])

    # 7. Missing and optional context fields
    def test_missing_optional_context_fields(self):
        malformed_tasks = [
            {"id": "1", "title": "No location", "type": "coding", "createdAt": 1789271100000, "completedAt": 1789274700000, "duration": 3600, "priority": "high"},
            {"id": "2", "title": "Empty loc", "type": "coding", "createdAt": 1789275600000, "completedAt": 1789278300000, "duration": 2700, "location": "", "priority": "medium"},
            {"id": "3", "title": "None completedAt", "type": "writing", "createdAt": 1789293600000, "completedAt": None, "duration": 400, "location": "Library", "priority": "low"}
        ]
        malformed_signals = [
            {"timestamp": 1789271100000, "appCategory": "Productivity"},
            {"timestamp": 1789293600000, "location": "Library"}
        ]
        engine = InsightEngine(malformed_tasks, malformed_signals)
        insights = engine.analyze()
        self.assertIsNotNone(insights["fatigueLevel"])
        self.assertIsNotNone(insights["recommendation"])
        self.assertTrue(len(insights["contextInsights"]) >= 1)

    # 8. Recommendation generation is explainable and dynamic
    def test_recommendation_generation(self):
        insights = self.engine.analyze()
        rec = insights["recommendation"]
        self.assertIsInstance(rec, str)
        self.assertTrue(len(rec) > 20)
        # Should cite actual computed task types, locations, and time window
        self.assertTrue("Home Office" in rec or "Cafe" in rec)
        self.assertTrue("coding" in rec.lower() or "writing" in rec.lower())

if __name__ == "__main__":
    unittest.main()
