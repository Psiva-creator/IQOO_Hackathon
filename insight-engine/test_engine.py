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

    # 7. Real-Time AI Coach Tests
    def test_coach_normal_state(self):
        # Steady session in home office with moderate duration and zero switches
        now_ms = int(time.time() * 1000)
        ev = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=10,
            context="Home Office",
            screen_duration=1200,
            recent_activity=[],
            current_time=now_ms
        )
        self.assertIn(ev["state"], ["NORMAL", "OPTIMAL"])
        self.assertGreaterEqual(ev["score"], 60)
        self.assertTrue(ev["isInterventionSuppressed"])
        self.assertEqual(ev["suppressionReason"], "SEVERITY_BELOW_THRESHOLD")
        self.assertIsNone(ev["intervention"])
        self.assertEqual(ev["urgency"], "LOW")

    def test_coach_optimal_state(self):
        # Fresh user in peak morning focus window with minimal screen time and zero disruptions
        tasks = [
            {"id": f"t{i}", "title": f"Morning Coding {i}", "type": "coding", "createdAt": 10000000 + i*3600000, "completedAt": 10000000 + i*3600000 + 1800000, "duration": 1800, "location": "Home Office"}
            for i in range(5)
        ]
        eng = InsightEngine(tasks, [])
        ev = eng.evaluate_current_state(
            task_type="coding",
            current_hour=10,
            context="Home Office",
            screen_duration=600,
            recent_activity=[]
        )
        self.assertEqual(ev["state"], "OPTIMAL")
        self.assertGreaterEqual(ev["score"], 80)
        self.assertEqual(ev["trigger"], "SUSTAINED_OPTIMAL_FLOW")
        self.assertTrue(ev["isInterventionSuppressed"])
        self.assertIsNone(ev["intervention"])

    def test_coach_fatigue_state(self):
        # Excessive screen duration of 90 minutes (5400s) triggers fatigue intervention
        now_ms = int(time.time() * 1000)
        ev = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            recent_activity=[],
            current_time=now_ms
        )
        self.assertIn(ev["state"], ["AT_RISK", "RECOVERY"])
        self.assertIn(ev["trigger"], ["EXCESSIVE_SCREEN_TIME", "HIGH_FATIGUE_STRAIN"])
        self.assertFalse(ev["isInterventionSuppressed"])
        self.assertIsNotNone(ev["intervention"])
        self.assertTrue(any(word in ev["intervention"].lower() for word in ["screen", "fatigue", "break", "rest"]))

    def test_coach_distraction_state(self):
        # 7 rapid context switches in 10 minutes with 4 non-productive apps
        now_ms = int(time.time() * 1000)
        ev = self.engine.evaluate_current_state(
            task_type="writing",
            current_hour=15,
            context="Cafe",
            screen_duration=1800,
            recent_activity={"contextSwitches": 7, "nonProductiveAppCount": 4},
            current_time=now_ms
        )
        self.assertEqual(ev["state"], "AT_RISK")
        self.assertEqual(ev["trigger"], "RAPID_CONTEXT_SWITCHING")
        self.assertFalse(ev["isInterventionSuppressed"])
        self.assertEqual(ev["intervention"], "Take a 10-minute break, then start a 25-minute focused session.")

    def test_coach_insufficient_data(self):
        # Empty engine (< 5 sessions, LOW confidence)
        empty_engine = InsightEngine([], [])
        ev = empty_engine.evaluate_current_state(
            task_type="coding",
            current_hour=10,
            context="Home Office",
            screen_duration=600,
            recent_activity=[]
        )
        self.assertEqual(ev["confidence"], "LOW")
        self.assertTrue(ev["isInterventionSuppressed"])
        self.assertIn(ev["suppressionReason"], ["SEVERITY_BELOW_THRESHOLD", "LOW_CONFIDENCE"])
        self.assertIsNone(ev["intervention"])

    def test_coach_duplicate_intervention_suppression(self):
        now_ms = int(time.time() * 1000)
        # 1st call: fresh rapid context switching -> fires intervention
        ev1 = self.engine.evaluate_current_state(
            task_type="writing",
            current_hour=15,
            context="Cafe",
            screen_duration=1800,
            recent_activity={"contextSwitches": 7, "nonProductiveAppCount": 4},
            last_intervention_time=None,
            last_trigger=None,
            current_time=now_ms
        )
        self.assertFalse(ev1["isInterventionSuppressed"])
        self.assertIsNotNone(ev1["intervention"])
        self.assertEqual(ev1["trigger"], "RAPID_CONTEXT_SWITCHING")

        # 2nd call: same trigger 5 minutes later (300,000ms ago) -> duplicate suppressed
        ev2 = self.engine.evaluate_current_state(
            task_type="writing",
            current_hour=15,
            context="Cafe",
            screen_duration=1800,
            recent_activity={"contextSwitches": 7, "nonProductiveAppCount": 4},
            last_intervention_time=now_ms - 300000,
            last_trigger="RAPID_CONTEXT_SWITCHING",
            current_time=now_ms,
            cooldown_seconds=900
        )
        self.assertTrue(ev2["isInterventionSuppressed"])
        self.assertIn(ev2["suppressionReason"], ["DUPLICATE_TRIGGER", "COOLDOWN_ACTIVE"])
        self.assertIsNone(ev2["intervention"])

    def test_coach_cooldown(self):
        now_ms = int(time.time() * 1000)
        # Call 5 minutes after last intervention (900s / 15m cooldown)
        ev_cooldown = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            recent_activity=[],
            last_intervention_time=now_ms - 300000,
            last_trigger="RAPID_CONTEXT_SWITCHING",
            current_time=now_ms,
            cooldown_seconds=900
        )
        self.assertTrue(ev_cooldown["isInterventionSuppressed"])
        self.assertEqual(ev_cooldown["suppressionReason"], "COOLDOWN_ACTIVE")
        self.assertIsNone(ev_cooldown["intervention"])

        # Call after cooldown expired (16 minutes / 960,000ms later)
        ev_expired = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            recent_activity=[],
            last_intervention_time=now_ms - 960000,
            last_trigger="RAPID_CONTEXT_SWITCHING",
            current_time=now_ms,
            cooldown_seconds=900
        )
        self.assertFalse(ev_expired["isInterventionSuppressed"])
        self.assertIsNotNone(ev_expired["intervention"])

    def test_coach_confidence_threshold(self):
        # 2 tasks logged -> LOW confidence
        sparse_tasks = [
            {"id": "t1", "title": "Sparse 1", "type": "coding", "createdAt": 10000000, "completedAt": 10000000 + 1800000, "duration": 1800, "location": "Home Office"},
            {"id": "t2", "title": "Sparse 2", "type": "coding", "createdAt": 13600000, "completedAt": 13600000 + 1800000, "duration": 1800, "location": "Home Office"}
        ]
        sparse_engine = InsightEngine(sparse_tasks, [])
        # Working at 22:00 (off-peak) with normal screen duration
        ev = sparse_engine.evaluate_current_state(
            task_type="coding",
            current_hour=22,
            context="Home Office",
            screen_duration=900,
            recent_activity=[]
        )
        self.assertEqual(ev["confidence"], "LOW")
        # Pattern-based triggers are suppressed because confidence is LOW
        self.assertTrue(ev["isInterventionSuppressed"])
        self.assertIn(ev["suppressionReason"], ["LOW_CONFIDENCE", "SEVERITY_BELOW_THRESHOLD"])

    def test_coach_kotlin_python_parity_structure(self):
        from engine import evaluate_current_state
        res = evaluate_current_state(
            tasks=self.tasks,
            context_signals=self.signals,
            task_type="coding",
            current_hour=10,
            context="Home Office",
            screen_duration=1200
        )
        required_coach_keys = [
            "state", "score", "trigger", "evidence", "intervention",
            "urgency", "confidence", "isInterventionSuppressed", "suppressionReason",
            "structuredEvidence", "localModelPrompt", "fallbackMessage"
        ]
        for key in required_coach_keys:
            self.assertIn(key, res)
        self.assertIn(res["state"], ["OPTIMAL", "NORMAL", "AT_RISK", "RECOVERY"])
        self.assertIn(res["urgency"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertIn(res["confidence"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIsInstance(res["score"], int)
        self.assertIsInstance(res["evidence"], list)
        self.assertIsInstance(res["structuredEvidence"], dict)


import asyncio
import os
import sys

# Ensure ai_model is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai_model.base import LocalAIModel
from ai_model.models import AIModelInput, AIModelResponse
from engine import evaluate_and_coach, evaluate_and_coach_async, _sanitize_text, _sanitize_task_type, _sanitize_context


class MockLocalAIModel(LocalAIModel):
    """Mock Local AI Model implementation for testing SLM integration."""
    def __init__(
        self,
        model_name: str = "mock-slm-v1",
        simulated_message: str = "Mock SLM coaching: Pace your work and take a 5-minute break.",
        simulated_reason: str = "Elevated screen time detected by local model.",
        simulated_action: str = "Step away from screens.",
        should_raise: bool = False,
        simulate_delay: float = 0.0
    ):
        self._model_name = model_name
        self.simulated_message = simulated_message
        self.simulated_reason = simulated_reason
        self.simulated_action = simulated_action
        self.should_raise = should_raise
        self.simulate_delay = simulate_delay
        self.calls = 0
        self.received_inputs = []

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_fallback(self) -> bool:
        return False

    def generate_coaching(self, input_data):
        self.calls += 1
        self.received_inputs.append(input_data)
        if self.simulate_delay > 0:
            time.sleep(self.simulate_delay)
        if self.should_raise:
            raise RuntimeError("Mock local NPU model out-of-memory error")
        return AIModelResponse(
            message=self.simulated_message,
            reason=self.simulated_reason,
            action=self.simulated_action,
            confidence="HIGH",
            provider=self.model_name,
            is_fallback=False
        )


class TestLocalSLMIntegration(unittest.TestCase):
    def setUp(self):
        self.tasks, self.signals = generate_synthetic_tasks_and_signals(days=7)
        self.engine = InsightEngine(self.tasks, self.signals)

    def test_privacy_sanitizer_standalone_functions(self):
        # 1. URL redaction
        text_with_url = "Check dashboard at https://analytics.company.com/user/12345?secret=true"
        clean = _sanitize_text(text_with_url)
        self.assertNotIn("https://", clean)
        self.assertIn("[URL_REDACTED]", clean)

        # 2. Email redaction
        text_with_email = "Contact engineer at dev.alice@company.org regarding bug"
        clean_email = _sanitize_text(text_with_email)
        self.assertNotIn("dev.alice@company.org", clean_email)
        self.assertIn("[EMAIL_REDACTED]", clean_email)

        # 3. GPS coordinates
        text_with_gps = "User currently at 37.7749, -122.4194 in transit"
        clean_gps = _sanitize_text(text_with_gps)
        self.assertNotIn("37.7749", clean_gps)
        self.assertIn("[GPS_REDACTED]", clean_gps)

        # 4. Device ID / UUID
        text_with_uuid = "device id 123e4567-e89b-12d3-a456-426614174000 reporting"
        clean_uuid = _sanitize_text(text_with_uuid)
        self.assertNotIn("123e4567", clean_uuid)
        self.assertIn("[DEVICE_ID_REDACTED]", clean_uuid)

        # 5. Phone number
        text_with_phone = "Call 555-123-4567 or +1-800-555-0199 for sync"
        clean_phone = _sanitize_text(text_with_phone)
        self.assertNotIn("555-123-4567", clean_phone)
        self.assertIn("[PHONE_REDACTED]", clean_phone)

        # 6. Task type sanitization
        self.assertEqual(_sanitize_task_type("Coding: fix PR #42 at https://github.com"), "coding")
        self.assertEqual(_sanitize_task_type("Meeting with John Doe at john@corp.com"), "meeting")
        self.assertEqual(_sanitize_task_type("Deep personal writing notes"), "writing")
        self.assertEqual(_sanitize_task_type("Completely unknown title with secret PII"), "general")

        # 7. Context sanitization
        self.assertEqual(_sanitize_context("Home Office"), "Home Office")
        self.assertEqual(_sanitize_context("cafe"), "Cafe")
        self.assertEqual(_sanitize_context("37.7749, -122.4194"), "Home Office")
        self.assertEqual(_sanitize_context("Office https://maps.google.com/?q=office"), "Home Office")

    def test_evaluate_state_privacy_sanitization_end_to_end(self):
        # Pass dangerous PII in task_type, context, and verify structuredEvidence & prompt
        mock_model = MockLocalAIModel()
        ev = self.engine.evaluate_current_state(
            task_type="Secret client work with Alice (coding) at https://zoom.us/j/99999",
            current_hour=15,
            context="Private GPS: 37.7749, -122.4194 (Home Office)",
            screen_duration=5400,
            recent_activity=[],
            model=mock_model
        )

        # Model should be called because screen duration is high (AT_RISK)
        self.assertEqual(mock_model.calls, 1)

        # Verify taskType is safely mapped to allowed whitelist and redundant duplicate keys removed
        self.assertEqual(ev["structuredEvidence"]["currentTask"], "coding")
        self.assertNotIn("taskType", ev["structuredEvidence"])
        self.assertNotIn("https://", ev["structuredEvidence"]["currentTask"])
        self.assertNotIn("Alice", ev["structuredEvidence"]["currentTask"])

        # Verify context is safely mapped to standard title
        self.assertNotIn("37.7749", ev["structuredEvidence"]["context"])
        self.assertNotIn("GPS", ev["structuredEvidence"]["context"])

        # Verify prompt has no URLs or GPS
        self.assertNotIn("https://", ev["localModelPrompt"])
        self.assertNotIn("37.7749", ev["localModelPrompt"])
        self.assertNotIn("Alice", ev["localModelPrompt"])

        # Verify all facts are clean
        for fact in ev["structuredEvidence"]["facts"]:
            self.assertNotIn("https://", fact)
            self.assertNotIn("37.7749", fact)

    def test_slm_receives_complete_structured_evidence(self):
        mock_model = MockLocalAIModel(simulated_message="Local SLM: Take a break from coding.")
        ev = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=14,
            context="Home Office",
            screen_duration=6000,
            recent_activity={"contextSwitches": 7, "nonProductiveAppCount": 3},
            model=mock_model
        )

        self.assertEqual(mock_model.calls, 1)
        evidence = ev["structuredEvidence"]

        # Check the 14 canonical required fields for SLM consumption (matching AIModelInput contract)
        self.assertEqual(evidence["currentTask"], "coding")
        self.assertIsInstance(evidence["productivityScore"], int)
        self.assertIsInstance(evidence["fatigue"], int)
        self.assertIn(evidence["fatigueLevel"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIsInstance(evidence["distraction"], int)
        self.assertEqual(evidence["contextSwitches"], 7)
        self.assertEqual(evidence["context"], "Home Office")
        self.assertIn("peakWindow", evidence)
        self.assertIn("isInPeakWindow", evidence)
        self.assertIn("prediction", evidence)
        self.assertIn(evidence["riskLevel"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIn(evidence["confidence"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIsNotNone(evidence["detectedTrigger"])
        self.assertIsInstance(evidence["facts"], list)
        self.assertGreater(len(evidence["facts"]), 0)

        # Verify redundant duplicate fields were cleanly removed
        self.assertNotIn("taskType", evidence)
        self.assertNotIn("score", evidence)
        self.assertNotIn("fatigueScore", evidence)
        self.assertNotIn("distractionScore", evidence)
        self.assertNotIn("recentContextSwitches", evidence)
        self.assertNotIn("bestFocusWindow", evidence)
        self.assertNotIn("predictedScore", evidence)
        self.assertNotIn("trigger", evidence)

        # Verify AIModelInput parses this canonical structured evidence seamlessly
        ai_input = AIModelInput.from_evidence(evidence)
        self.assertEqual(ai_input.currentTask, "coding")
        self.assertEqual(ai_input.contextSwitches, 7)
        self.assertEqual(ai_input.context, "Home Office")

        # Verify intervention was replaced by SLM output
        self.assertEqual(ev["intervention"], "Local SLM: Take a break from coding.")
        self.assertEqual(ev["modelProvider"], "mock-slm-v1")
        self.assertEqual(ev["coachResponse"]["message"], "Local SLM: Take a break from coding.")


    def test_anti_spam_suppression_bypasses_slm_inference(self):
        mock_model = MockLocalAIModel()
        now_ms = int(time.time() * 1000)

        # Case 1: OPTIMAL state (score high, low screen duration) -> SEVERITY_BELOW_THRESHOLD
        ev_optimal = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=10,
            context="Home Office",
            screen_duration=900,
            recent_activity=[],
            model=mock_model
        )
        self.assertTrue(ev_optimal["isInterventionSuppressed"])
        self.assertEqual(ev_optimal["suppressionReason"], "SEVERITY_BELOW_THRESHOLD")
        self.assertIsNone(ev_optimal["intervention"])
        # SLM must NOT have been called!
        self.assertEqual(mock_model.calls, 0)
        self.assertIn("bypassed", ev_optimal["modelProvider"])

        # Case 2: Cooldown active (within 900s)
        ev_cooldown = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            recent_activity=[],
            last_intervention_time=now_ms - 300000, # 5m ago
            last_trigger="EXCESSIVE_SCREEN_TIME",
            current_time=now_ms,
            cooldown_seconds=900,
            model=mock_model
        )
        self.assertTrue(ev_cooldown["isInterventionSuppressed"])
        self.assertEqual(ev_cooldown["suppressionReason"], "COOLDOWN_ACTIVE")
        self.assertIsNone(ev_cooldown["intervention"])
        # SLM must still NOT have been called!
        self.assertEqual(mock_model.calls, 0)

        # Case 3: Duplicate trigger suppression
        ev_duplicate = self.engine.evaluate_current_state(
            task_type="writing",
            current_hour=15,
            context="Cafe",
            screen_duration=1800,
            recent_activity={"contextSwitches": 7, "nonProductiveAppCount": 4},
            last_intervention_time=now_ms - 400000,
            last_trigger="RAPID_CONTEXT_SWITCHING",
            current_time=now_ms,
            cooldown_seconds=900,
            model=mock_model
        )
        self.assertTrue(ev_duplicate["isInterventionSuppressed"])
        self.assertIn(ev_duplicate["suppressionReason"], ["DUPLICATE_TRIGGER", "COOLDOWN_ACTIVE"])
        self.assertIsNone(ev_duplicate["intervention"])
        self.assertEqual(mock_model.calls, 0)

    def test_slm_error_graceful_deterministic_fallback(self):
        failing_model = MockLocalAIModel(should_raise=True)
        ev = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400, # Trigger EXCESSIVE_SCREEN_TIME
            recent_activity=[],
            model=failing_model
        )

        # Model was called once and threw exception
        self.assertEqual(failing_model.calls, 1)

        # System must NOT crash and must cleanly use fallbackMessage
        self.assertFalse(ev["isInterventionSuppressed"])
        self.assertIsNotNone(ev["intervention"])
        self.assertEqual(ev["intervention"], ev["fallbackMessage"])
        self.assertTrue("fallback" in ev["modelProvider"].lower())
        self.assertTrue(ev["coachResponse"]["isFallback"])

    def test_async_evaluate_and_coach_non_blocking(self):
        mock_model = MockLocalAIModel(
            simulated_message="Async SLM: Smooth cognitive pacing.",
            simulate_delay=0.02
        )

        async def run_async_test():
            start_t = time.time()
            res = await self.engine.evaluate_and_coach_async(
                task_type="coding",
                current_hour=15,
                context="Home Office",
                screen_duration=5400,
                model=mock_model
            )
            elapsed = time.time() - start_t
            return res, elapsed

        res, elapsed = asyncio.run(run_async_test())
        self.assertEqual(mock_model.calls, 1)
        self.assertEqual(res["intervention"], "Async SLM: Smooth cognitive pacing.")
        self.assertGreaterEqual(elapsed, 0.02)
        self.assertIn("structuredEvidence", res)

    def test_module_level_evaluate_and_coach_aliases(self):
        mock_model = MockLocalAIModel(simulated_message="Module-level SLM coach.")
        res = evaluate_and_coach(
            tasks=self.tasks,
            context_signals=self.signals,
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            model=mock_model
        )
        self.assertEqual(mock_model.calls, 1)
        self.assertEqual(res["intervention"], "Module-level SLM coach.")
        self.assertEqual(res["modelProvider"], "mock-slm-v1")

    def test_privacy_ingress_predict_task_readiness(self):
        from engine import predict_task_readiness
        pred = predict_task_readiness(
            tasks=self.tasks,
            context_signals=self.signals,
            task_type="Secret client work with Dave (coding) at https://zoom.us",
            current_hour=10,
            current_context="37.7749,-122.4194 (Top Secret Lab)"
        )
        # Verify taskType is normalized
        self.assertEqual(pred["taskType"], "coding")
        self.assertNotIn("https://", pred["reason"])
        self.assertNotIn("Dave", pred["reason"])
        self.assertNotIn("37.7749", pred["reason"])

    def test_privacy_ingress_update_user_model(self):
        from engine import update_user_model
        dirty_task = {
            "id": "dirty-1",
            "title": "Private meeting with Alice at https://corp.internal/spec",
            "type": "Meeting at 37.7749,-122.4194 with bob@company.com",
            "createdAt": int(time.time() * 1000) - 3600000,
            "completedAt": int(time.time() * 1000),
            "duration": 3600,
            "location": "37.7749, -122.4194"
        }
        dirty_context = {
            "timestamp": int(time.time() * 1000),
            "appCategory": "Productivity",
            "location": "https://maps.google.com/?q=37.7749,-122.4194"
        }
        user_model = update_user_model(None, dirty_task, dirty_context)
        stored_task = user_model["tasks"][-1]
        self.assertEqual(stored_task["type"], "meeting")
        self.assertNotIn("https://", stored_task["title"])
        self.assertIn("[URL_REDACTED]", stored_task["title"])
        self.assertEqual(stored_task["location"], "Home Office")

    def test_local_ai_boundary_provider_independence(self):
        from ai_model.fallback import FallbackAIModel
        # 1. Deterministic Fallback provider
        fallback_model = FallbackAIModel()
        ev_fallback = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            model=fallback_model
        )
        self.assertFalse(ev_fallback["isInterventionSuppressed"])
        self.assertIsNotNone(ev_fallback["intervention"])
        self.assertIn("fallback", ev_fallback["modelProvider"].lower())

        # 2. Mock SLM provider
        mock_model = MockLocalAIModel(simulated_message="Mock provider coaching.")
        ev_mock = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            model=mock_model
        )
        self.assertEqual(mock_model.calls, 1)
        self.assertEqual(ev_mock["intervention"], "Mock provider coaching.")
        self.assertEqual(ev_mock["modelProvider"], "mock-slm-v1")

        # 3. None (built-in offline fallback)
        ev_none = self.engine.evaluate_current_state(
            task_type="coding",
            current_hour=15,
            context="Home Office",
            screen_duration=5400,
            model=None
        )
        self.assertFalse(ev_none["isInterventionSuppressed"])
        self.assertEqual(ev_none["intervention"], ev_none["fallbackMessage"])


if __name__ == "__main__":
    unittest.main()




