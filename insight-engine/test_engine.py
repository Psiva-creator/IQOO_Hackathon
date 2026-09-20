import unittest
from synthetic_generator import generate_synthetic_tasks
from engine import InsightEngine

class TestInsightEngine(unittest.TestCase):
    def setUp(self):
        self.tasks = generate_synthetic_tasks(days=7)
        self.engine = InsightEngine(self.tasks)

    def test_insight_structure(self):
        insights = self.engine.analyze()
        required_keys = ["peakHour", "procrastinationTrigger", "bestContext", "recommendation"]
        for key in required_keys:
            self.assertIn(key, insights)
            self.assertIsInstance(insights[key], str)
            self.assertTrue(len(insights[key]) > 0)

    def test_peak_hour_morning_detection(self):
        insights = self.engine.analyze()
        # Synthetic data has coding sessions at 09:15 and 10:30
        self.assertTrue("09:00" in insights["peakHour"] or "10:00" in insights["peakHour"])

    def test_procrastination_detection(self):
        insights = self.engine.analyze()
        # Synthetic data has writing tasks failing after 3 PM
        self.assertIn("Writing", insights["procrastinationTrigger"])

    def test_empty_tasks(self):
        empty_engine = InsightEngine([])
        insights = empty_engine.analyze()
        self.assertIn("Insufficient Data", insights["peakHour"])

if __name__ == "__main__":
    unittest.main()
