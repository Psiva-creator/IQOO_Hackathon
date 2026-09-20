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

    # 6. Continuous Personalization / Online Learning Tests
    def test_online_learning_completed_task(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        initial_model = {
            "tasks": self.tasks,
            "contextSignals": self.signals
        }
        new_task = {
            "id": "new-comp-1",
            "title": "Optimizing DB Queries",
            "type": "coding",
            "createdAt": now_ms - 3600000,
            "completedAt": now_ms,
            "duration": 3600,
            "location": "Home Office",
            "priority": "HIGH",
            "predictedScore": 85
        }
        new_ctx = {
            "timestamp": now_ms,
            "appCategory": "Productivity",
            "location": "Home Office",
            "screenOnDuration": 1800
        }

        updated = update_user_model(initial_model, new_task, new_ctx)
        self.assertEqual(updated["taskCount"], len(self.tasks) + 1)
        self.assertEqual(len(updated["tasks"]), len(self.tasks) + 1)
        self.assertEqual(len(updated["contextSignals"]), len(self.signals) + 1)
        self.assertEqual(updated["predictionCalibration"]["lastActualOutcome"], "COMPLETED")
        self.assertEqual(updated["predictionCalibration"]["lastPredictionOutcome"], "ACCURATE")
        self.assertIn("productivityProfile", updated)

    def test_online_learning_abandoned_task(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        initial_model = {
            "tasks": self.tasks,
            "contextSignals": self.signals
        }
        new_task = {
            "id": "new-aband-1",
            "title": "Unfinished Spec Drafting",
            "type": "writing",
            "createdAt": now_ms - 1800000,
            "completedAt": None,
            "status": "abandoned",
            "duration": 1800,
            "location": "Cafe",
            "priority": "LOW",
            "predictedScore": 35
        }

        updated = update_user_model(initial_model, new_task)
        self.assertEqual(updated["predictionCalibration"]["lastActualOutcome"], "ABANDONED")
        # Score 35 (< 50) and abandoned -> accurate risk forecast
        self.assertEqual(updated["predictionCalibration"]["lastPredictionOutcome"], "ACCURATE")
        writing_stat = next(t for t in updated["taskTypeAnalysis"] if t["taskType"] == "writing")
        self.assertGreater(writing_stat["abandonmentRate"], 0)

    def test_online_learning_changing_peak_hours(self):
        from engine import update_user_model
        now_dt = datetime.now()
        # Seed 5 completed tasks at 09:00 AM (older)
        old_tasks = []
        base_time = now_dt.replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=5)
        for i in range(5):
            t_created = int((base_time + timedelta(days=i)).timestamp() * 1000)
            old_tasks.append({
                "id": f"old-{i}",
                "title": f"Morning session {i}",
                "type": "coding",
                "createdAt": t_created,
                "completedAt": t_created + 3600000,
                "duration": 3600,
                "location": "Home Office",
                "priority": "HIGH"
            })

        model = {"tasks": old_tasks, "contextSignals": []}
        eng_before = InsightEngine(old_tasks)
        self.assertIn("09:00", eng_before.analyze()["peakHour"])

        # Feed 6 new consecutive tasks in the late afternoon (16:00) with recent timestamps
        afternoon_time = now_dt.replace(hour=16, minute=0, second=0, microsecond=0)
        for i in range(6):
            t_created = int((afternoon_time + timedelta(days=i)).timestamp() * 1000)
            new_task = {
                "id": f"shift-pm-{i}",
                "title": f"Afternoon work {i}",
                "type": "coding",
                "createdAt": t_created,
                "completedAt": t_created + 3600000,
                "duration": 3600,
                "location": "Home Office",
                "priority": "MEDIUM"
            }
            model = update_user_model(model, new_task)

        # Recency weighting should shift peak window to 16:00
        self.assertIn("16:00", model["bestFocusWindow"])

    def test_online_learning_changing_context_preference(self):
        from engine import update_user_model
        now_dt = datetime.now()
        # Start with Home Office having 2 tasks
        tasks = [
            {
                "id": "h1",
                "title": "Home Task 1",
                "type": "coding",
                "createdAt": int((now_dt - timedelta(days=3)).timestamp() * 1000),
                "completedAt": int((now_dt - timedelta(days=3)).timestamp() * 1000) + 3600000,
                "duration": 3600,
                "location": "Home Office",
                "priority": "HIGH"
            },
            {
                "id": "h2",
                "title": "Home Task 2",
                "type": "coding",
                "createdAt": int((now_dt - timedelta(days=2)).timestamp() * 1000),
                "completedAt": None,
                "duration": 1800,
                "location": "Home Office",
                "priority": "HIGH"
            }
        ]
        model = {"tasks": tasks, "contextSignals": []}

        # User starts working at "Library" with 4 consecutive completed tasks
        for i in range(4):
            t_created = int((now_dt - timedelta(hours=10 - i*2)).timestamp() * 1000)
            new_task = {
                "id": f"lib-{i}",
                "title": f"Library Session {i}",
                "type": "coding",
                "createdAt": t_created,
                "completedAt": t_created + 3600000,
                "duration": 3600,
                "location": "Library",
                "priority": "HIGH"
            }
            model = update_user_model(model, new_task)

        # Library should become the bestContext (100% completion across 4 tasks)
        self.assertEqual(model["bestContext"], "Library")

    def test_online_learning_prediction_correct(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        # Task with predicted score 80 and completed -> accurate
        new_task = {
            "id": "pred-corr-1",
            "title": "Routine Coding",
            "type": "coding",
            "createdAt": now_ms - 3600000,
            "completedAt": now_ms,
            "duration": 3600,
            "location": "Home Office",
            "priority": "HIGH",
            "predictedScore": 80
        }
        model = update_user_model(None, new_task)
        calib = model["predictionCalibration"]
        self.assertEqual(calib["totalEvaluations"], 1)
        self.assertEqual(calib["accuratePredictions"], 1)
        self.assertEqual(calib["accuracyRate"], 100.0)
        self.assertEqual(calib["meanCalibrationError"], 20.0) # |80 - 100|
        self.assertEqual(calib["lastPredictionOutcome"], "ACCURATE")

    def test_online_learning_prediction_wrong(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        # Task with high predicted score 85 but abandoned -> inaccurate
        new_task = {
            "id": "pred-wrong-1",
            "title": "Failed Coding Block",
            "type": "coding",
            "createdAt": now_ms - 3600000,
            "completedAt": None,
            "duration": 1200,
            "location": "Cafe",
            "priority": "HIGH",
            "predictedScore": 85
        }
        model = update_user_model(None, new_task)
        calib = model["predictionCalibration"]
        self.assertEqual(calib["totalEvaluations"], 1)
        self.assertEqual(calib["accuratePredictions"], 0)
        self.assertEqual(calib["accuracyRate"], 0.0)
        self.assertEqual(calib["meanCalibrationError"], 85.0) # |85 - 0|
        self.assertEqual(calib["lastPredictionOutcome"], "INACCURATE")

    def test_online_learning_cold_start(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        first_task = {
            "id": "cold-1",
            "title": "First Ever Task",
            "type": "reading",
            "createdAt": now_ms - 1800000,
            "completedAt": now_ms,
            "duration": 1800,
            "location": "Library",
            "priority": "LOW"
        }
        # Passing None as previous_model
        model = update_user_model(None, first_task)
        self.assertIsNotNone(model)
        self.assertEqual(model["taskCount"], 1)
        self.assertEqual(model["profileConfidence"], "LOW")
        self.assertEqual(model["bestFocusWindow"], "Insufficient Data")
        self.assertEqual(model["predictionCalibration"]["totalEvaluations"], 0)

    def test_online_learning_repeated_updates(self):
        from engine import update_user_model
        now_ms = int(time.time() * 1000)
        model = None
        for i in range(10):
            task = {
                "id": f"seq-{i}",
                "title": f"Task {i}",
                "type": "coding" if i % 2 == 0 else "meeting",
                "createdAt": now_ms + i * 3600000,
                "completedAt": (now_ms + i * 3600000 + 1800000) if i % 3 != 0 else None,
                "duration": 1800,
                "location": "Home Office",
                "priority": "MEDIUM",
                "predictedScore": 70 if i % 3 != 0 else 30
            }
            model = update_user_model(model, task)

        self.assertEqual(model["taskCount"], 10)
        self.assertEqual(len(model["tasks"]), 10)
        calib = model["predictionCalibration"]
        self.assertEqual(calib["totalEvaluations"], 10)
        self.assertGreaterEqual(calib["accuracyRate"], 80.0)
        self.assertLessEqual(calib["meanCalibrationError"], 35.0)

if __name__ == "__main__":
    unittest.main()

