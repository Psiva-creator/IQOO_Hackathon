import unittest
from synthetic_generator import generate_synthetic_tasks
from engine import InsightEngine

class TestInsightEngine(unittest.TestCase):
    def setUp(self):
        self.tasks = generate_synthetic_tasks(days=7)
        self.engine = InsightEngine(self.tasks)

    def test_insight_structure(self):
        insights = self.engine.analyze()
        required_keys = ["peakHour", "procrastinationTrigger", "bestContext", "recommendation", "productivityScore", "confidenceLevel", "hourlyHeatmap"]
        for key in required_keys:
            self.assertIn(key, insights)

    def test_peak_hour_morning_detection(self):
        insights = self.engine.analyze()
        self.assertTrue("09:00" in insights["peakHour"] or "10:00" in insights["peakHour"])

    def test_procrastination_detection(self):
        insights = self.engine.analyze()
        self.assertIn("Writing", insights["procrastinationTrigger"])

    def test_confidence_level(self):
        insights = self.engine.analyze()
        # 42 synthetic tasks should yield "High" confidence
        self.assertEqual(insights["confidenceLevel"], "High")

    def test_hourly_heatmap(self):
        insights = self.engine.analyze()
        heatmap = insights["hourlyHeatmap"]
        self.assertEqual(len(heatmap), 24)
        # 9 AM should have high completion
        self.assertGreater(heatmap["9"], 50)

    def test_empty_tasks(self):
        empty_engine = InsightEngine([])
        insights = empty_engine.analyze()
        self.assertEqual(insights["confidenceLevel"], "Calibrating")
        self.assertEqual(insights["productivityScore"], 0)

if __name__ == "__main__":
    unittest.main()
