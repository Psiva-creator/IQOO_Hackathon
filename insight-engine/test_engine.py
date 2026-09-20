import unittest
import time
from datetime import datetime, timedelta
from synthetic_generator import generate_synthetic_tasks, generate_synthetic_tasks_and_signals
from engine import InsightEngine

class TestInsightEngine(unittest.TestCase):
    def setUp(self):
        self.tasks, self.signals = generate_synthetic_tasks_and_signals(days=7)
        self.engine = InsightEngine(self.tasks, self.signals)

    # 1. Existing tests and backward compatibility
    def test_insight_structure_backward_compatibility(self):
        standalone_engine = InsightEngine(self.tasks)
        insights = standalone_engine.analyze()
        required_keys = [
            "peakHour", "procrastinationTrigger", "bestContext", "recommendation",
            "productivityScore", "confidenceLevel", "hourlyHeatmap",
            "fatigueLevel", "fatigueScore", "explanation", "contextInsights", "distractionSensitivity",
            "productivityProfile", "adaptiveRecommendations"
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
        profile = insights["productivityProfile"]
        self.assertEqual(profile["profileConfidence"], "LOW")
        self.assertEqual(profile["bestFocusWindow"], "Insufficient Data")
        self.assertEqual(profile["bestTaskTypes"], [])
        self.assertEqual(profile["peakProductivityScore"], 0)
        self.assertEqual(insights["productivityScore"], 0)
        self.assertEqual(insights["fatigueLevel"], "LOW")
        self.assertEqual(len(insights["adaptiveRecommendations"]), 1)
        self.assertEqual(insights["adaptiveRecommendations"][0]["title"], "Calibrate Habit Profile")

    def test_confidence_calculation_tiers(self):
        # < 5 tasks -> LOW
        tasks_3 = [
            {"id": "1", "type": "coding", "createdAt": 1000, "completedAt": 2000, "duration": 1000, "location": "Home Office"},
            {"id": "2", "type": "coding", "createdAt": 3000, "completedAt": 4000, "duration": 1000, "location": "Home Office"},
            {"id": "3", "type": "coding", "createdAt": 5000, "completedAt": 6000, "duration": 1000, "location": "Home Office"}
        ]
        res_3 = InsightEngine(tasks_3).analyze()
        self.assertEqual(res_3["productivityProfile"]["profileConfidence"], "LOW")

        # 5 to 15 tasks -> MEDIUM
        tasks_8 = tasks_3 + [
            {"id": f"{i}", "type": "coding", "createdAt": i * 1000, "completedAt": (i + 1) * 1000, "duration": 1000, "location": "Home Office"}
            for i in range(4, 9)
        ]
        res_8 = InsightEngine(tasks_8).analyze()
        self.assertEqual(res_8["productivityProfile"]["profileConfidence"], "MEDIUM")

        # > 15 tasks -> HIGH
        res_42 = InsightEngine(self.tasks).analyze()
        self.assertEqual(res_42["productivityProfile"]["profileConfidence"], "HIGH")

    # 3. Strong morning productivity
    def test_strong_morning_productivity(self):
        insights = self.engine.analyze()
        profile = insights["productivityProfile"]
        self.assertTrue("09:00" in profile["bestFocusWindow"] or "10:00" in profile["bestFocusWindow"])
        self.assertIn("coding", profile["bestTaskTypes"])
        self.assertEqual(profile["bestContext"], "Home Office")

    # 4. Strong afternoon productivity
    def test_strong_afternoon_productivity(self):
        # Create user profile where morning tasks fail and afternoon tasks (14:00 - 16:00) succeed
        base = datetime(2026, 9, 15, 9, 0)
        tasks = []
        for day in range(6):
            d_time = base + timedelta(days=day)
            # Morning failure at 9:00 AM
            t_m = int(d_time.replace(hour=9).timestamp() * 1000)
            tasks.append({"id": f"m_{day}", "type": "writing", "createdAt": t_m, "completedAt": None, "duration": 300, "location": "Cafe"})
            # Afternoon success at 14:00 (2 PM)
            t_a1 = int(d_time.replace(hour=14).timestamp() * 1000)
            tasks.append({"id": f"a1_{day}", "type": "coding", "createdAt": t_a1, "completedAt": t_a1 + 3600000, "duration": 3600, "location": "Studio"})
            t_a2 = int(d_time.replace(hour=15).timestamp() * 1000)
            tasks.append({"id": f"a2_{day}", "type": "coding", "createdAt": t_a2, "completedAt": t_a2 + 3600000, "duration": 3600, "location": "Studio"})

        res = InsightEngine(tasks).analyze()
        profile = res["productivityProfile"]
        self.assertTrue("14:00" in profile["bestFocusWindow"] or "15:00" in profile["bestFocusWindow"])
        self.assertIn("coding", profile["bestTaskTypes"])
        self.assertEqual(profile["bestContext"], "Studio")

    # 5. Different optimal times for different task types
    def test_different_optimal_times_for_different_task_types(self):
        base = datetime(2026, 9, 15, 8, 0)
        tasks = []
        for day in range(5):
            d_time = base + timedelta(days=day)
            # Coding at 9 AM succeeds
            t_c = int(d_time.replace(hour=9).timestamp() * 1000)
            tasks.append({"id": f"c_{day}", "type": "coding", "createdAt": t_c, "completedAt": t_c + 3600000, "duration": 3600, "location": "Home Office"})
            # Writing at 11 AM succeeds
            t_w = int(d_time.replace(hour=11).timestamp() * 1000)
            tasks.append({"id": f"w_{day}", "type": "writing", "createdAt": t_w, "completedAt": t_w + 3600000, "duration": 3600, "location": "Home Office"})
            # Meetings at 16:00 (4 PM) succeeds
            t_m = int(d_time.replace(hour=16).timestamp() * 1000)
            tasks.append({"id": f"m_{day}", "type": "meeting", "createdAt": t_m, "completedAt": t_m + 1800000, "duration": 1800, "location": "Meeting Room"})

        res = InsightEngine(tasks).analyze()
        type_analysis = res["productivityProfile"]["taskTypeAnalysis"]
        c_stat = next(t for t in type_analysis if t["taskType"] == "coding")
        w_stat = next(t for t in type_analysis if t["taskType"] == "writing")
        m_stat = next(t for t in type_analysis if t["taskType"] == "meeting")

        self.assertTrue("09:00" in c_stat["strongestWindow"])
        self.assertTrue("11:00" in w_stat["strongestWindow"])
        self.assertTrue("16:00" in m_stat["strongestWindow"])

    # 6. Context-dependent productivity
    def test_context_dependent_productivity(self):
        tasks = [
            {"id": "1", "title": "T1", "type": "coding", "createdAt": 1000, "completedAt": 2000, "duration": 1000, "location": "Library", "priority": "high"},
            {"id": "2", "title": "T2", "type": "coding", "createdAt": 3000, "completedAt": 4000, "duration": 1000, "location": "Library", "priority": "high"},
            {"id": "3", "title": "T3", "type": "coding", "createdAt": 5000, "completedAt": 6000, "duration": 1000, "location": "Library", "priority": "high"},
            {"id": "4", "title": "T4", "type": "writing", "createdAt": 7000, "completedAt": None, "duration": 300, "location": "Lounge", "priority": "low"},
            {"id": "5", "title": "T5", "type": "writing", "createdAt": 9000, "completedAt": None, "duration": 200, "location": "Lounge", "priority": "low"}
        ]
        res = InsightEngine(tasks).analyze()
        profile = res["productivityProfile"]
        self.assertEqual(profile["bestContext"], "Library")
        self.assertEqual(res["contextInsights"][0]["context"], "Library")
        self.assertEqual(res["contextInsights"][0]["status"], "Optimal")
        self.assertEqual(res["contextInsights"][-1]["context"], "Lounge")
        self.assertEqual(res["contextInsights"][-1]["status"], "Suboptimal")

    # 7. Conflicting patterns (mixed success, high switching)
    def test_conflicting_patterns(self):
        base_ms = int(time.time() * 1000)
        conflicting_tasks = [
            {"id": "1", "type": "coding", "createdAt": base_ms, "completedAt": base_ms + 1000, "duration": 1000, "location": "Cafe"},
            {"id": "2", "type": "writing", "createdAt": base_ms + 1500, "completedAt": None, "duration": 500, "location": "Home Office"},
            {"id": "3", "type": "meeting", "createdAt": base_ms + 2500, "completedAt": base_ms + 3500, "duration": 1000, "location": "Cafe"},
            {"id": "4", "type": "planning", "createdAt": base_ms + 4000, "completedAt": None, "duration": 300, "location": "Home Office"},
            {"id": "5", "type": "coding", "createdAt": base_ms + 5000, "completedAt": base_ms + 6000, "duration": 1000, "location": "Home Office"},
            {"id": "6", "type": "writing", "createdAt": base_ms + 6500, "completedAt": base_ms + 7500, "duration": 1000, "location": "Cafe"}
        ]
        res = InsightEngine(conflicting_tasks).analyze()
        self.assertIsNotNone(res["productivityProfile"])
        self.assertTrue(len(res["adaptiveRecommendations"]) >= 1)
        self.assertIn(res["productivityProfile"]["profileConfidence"], ["MEDIUM", "HIGH"])

    # 8. High fatigue and adaptive recommendations
    def test_high_fatigue_adaptive_recommendation(self):
        t_morning = 1789271100000
        t_afternoon = 1789293600000
        fatigued_tasks = [
            {"id": "1", "type": "coding", "createdAt": t_morning, "completedAt": t_morning + 3600000, "duration": 3600, "location": "Home Office"},
            {"id": "2", "type": "coding", "createdAt": t_morning + 4000000, "completedAt": t_morning + 7600000, "duration": 3600, "location": "Home Office"},
            {"id": "3", "type": "coding", "createdAt": t_morning + 8000000, "completedAt": t_morning + 11600000, "duration": 3600, "location": "Home Office"},
            {"id": "4", "type": "writing", "createdAt": t_afternoon, "completedAt": None, "duration": 300, "location": "Cafe"},
            {"id": "5", "type": "writing", "createdAt": t_afternoon + 3600000, "completedAt": None, "duration": 200, "location": "Cafe"},
            {"id": "6", "type": "writing", "createdAt": t_afternoon + 7200000, "completedAt": None, "duration": 200, "location": "Cafe"}
        ]
        fatigued_signals = [
            {"timestamp": t_afternoon, "appCategory": "Social", "location": "Cafe", "screenOnDuration": 8500},
            {"timestamp": t_afternoon + 3600000, "appCategory": "Entertainment", "location": "Cafe", "screenOnDuration": 9200}
        ]
        res = InsightEngine(fatigued_tasks, fatigued_signals).analyze()
        self.assertEqual(res["fatigueLevel"], "HIGH")
        # Recommendation list should prioritize fatigue break pacing
        rec_titles = [r["title"] for r in res["adaptiveRecommendations"]]
        self.assertIn("Fatigue Break Pacing", rec_titles)

    # 9. Recommendation generation and ranking
    def test_recommendation_generation_and_ranking(self):
        res = self.engine.analyze()
        recs = res["adaptiveRecommendations"]
        self.assertTrue(1 <= len(recs) <= 3)
        for r in recs:
            self.assertTrue(len(r["title"]) > 0)
            self.assertTrue(len(r["advice"]) > 0)
            self.assertTrue(len(r["reason"]) > 0)
            self.assertIn(r["priority"], ["HIGH", "MEDIUM", "LOW"])
            self.assertIn(r["impact"], ["HIGH", "MEDIUM", "LOW"])
        # Top-level recommendation should match primary recommendation
        self.assertIn(recs[0]["advice"], res["recommendation"])

    # 10. Predictive Productivity / "Should I do this task now?" tests
    def test_high_prediction_optimal_conditions(self):
        # Coding in Home Office at 10:00 AM with fresh screen duration
        pred = self.engine.predict_task_readiness(
            task_type="coding",
            current_hour=10,
            current_context="Home Office",
            recent_screen_duration=600
        )
        self.assertEqual(pred["taskType"], "coding")
        self.assertGreaterEqual(pred["predictedScore"], 70)
        self.assertEqual(pred["riskLevel"], "LOW")
        self.assertEqual(pred["confidence"], "HIGH")
        self.assertIn("optimal", pred["reason"].lower())
        self.assertIn("Start coding now", pred["recommendation"])

    def test_low_prediction_suboptimal_conditions(self):
        # Writing in Cafe at 15:00 (3 PM) with prolonged screen duration
        pred = self.engine.predict_task_readiness(
            task_type="writing",
            current_hour=15,
            current_context="Cafe",
            recent_screen_duration=5400
        )
        self.assertEqual(pred["taskType"], "writing")
        self.assertLess(pred["predictedScore"], 45)
        self.assertEqual(pred["riskLevel"], "HIGH")
        self.assertIn("HIGH risk", pred["reason"])
        self.assertIn("09:00 - 11:00", pred["bestAlternativeWindow"])
        self.assertIn("postponing", pred["recommendation"].lower())

    def test_insufficient_data_prediction(self):
        # Case A: 0 tasks logged
        empty_engine = InsightEngine([], [])
        pred_empty = empty_engine.predict_task_readiness("coding")
        self.assertEqual(pred_empty["confidence"], "LOW")
        self.assertEqual(pred_empty["predictedScore"], 50)
        self.assertEqual(pred_empty["riskLevel"], "MEDIUM")
        self.assertIn("calibration", pred_empty["reason"].lower())

        # Case B: < 5 tasks logged
        sparse_tasks = [
            {"id": "1", "type": "coding", "createdAt": 1000, "completedAt": 2000, "duration": 1000, "location": "Home Office"},
            {"id": "2", "type": "coding", "createdAt": 3000, "completedAt": 4000, "duration": 1000, "location": "Home Office"}
        ]
        sparse_engine = InsightEngine(sparse_tasks)
        pred_sparse = sparse_engine.predict_task_readiness("coding")
        self.assertEqual(pred_sparse["confidence"], "LOW")

        # Case C: Unseen task type in established profile
        pred_unseen = self.engine.predict_task_readiness("robotics")
        self.assertEqual(pred_unseen["confidence"], "LOW")
        self.assertIn("No historical sessions recorded for 'robotics'", pred_unseen["reason"])

    def test_context_change_prediction(self):
        # Same task (writing) and hour (10 AM), comparing Home Office vs Cafe
        pred_office = self.engine.predict_task_readiness(
            task_type="writing",
            current_hour=10,
            current_context="Home Office",
            recent_screen_duration=600
        )
        pred_cafe = self.engine.predict_task_readiness(
            task_type="writing",
            current_hour=10,
            current_context="Cafe",
            recent_screen_duration=600
        )
        # Home Office completion rate is 100% vs Cafe 0% in synthetic dataset
        self.assertGreater(pred_office["predictedScore"], pred_cafe["predictedScore"])
        self.assertIn("Home Office", pred_office["recommendation"])

    def test_fatigue_impact_on_prediction(self):
        # Coding in Home Office at 10 AM (low fatigue, 10 min screen) vs
        # Coding in Home Office at 15:00 (afternoon slump, 90 min screen)
        pred_fresh = self.engine.predict_task_readiness(
            task_type="coding",
            current_hour=10,
            current_context="Home Office",
            recent_screen_duration=600
        )
        pred_fatigued = self.engine.predict_task_readiness(
            task_type="coding",
            current_hour=15,
            current_context="Home Office",
            recent_screen_duration=5400
        )
        self.assertGreater(pred_fresh["predictedScore"], pred_fatigued["predictedScore"])
        self.assertIn("fatigue", pred_fatigued["reason"].lower())

    def test_analyze_with_target_task_type(self):
        # analyze() without target_task_type preserves backward compatibility (no taskPrediction)
        res_standard = self.engine.analyze()
        self.assertNotIn("taskPrediction", res_standard)

        # analyze() with target_task_type populates taskPrediction
        res_with_target = self.engine.analyze(target_task_type="coding", current_hour=10)
        self.assertIn("taskPrediction", res_with_target)
        tp = res_with_target["taskPrediction"]
        self.assertEqual(tp["taskType"], "coding")
        self.assertIn("predictedScore", tp)
        self.assertIn("riskLevel", tp)
        self.assertIn("confidence", tp)

    def test_module_level_prediction_helper(self):
        from engine import predict_task_readiness
        pred = predict_task_readiness(
            tasks=self.tasks,
            context_signals=self.signals,
            task_type="coding",
            current_hour=10,
            current_context="Home Office"
        )
        self.assertEqual(pred["taskType"], "coding")
        self.assertGreaterEqual(pred["predictedScore"], 70)

if __name__ == "__main__":
    unittest.main()
