"""
On-Device Habit & Productivity Insight Engine
Context-Aware Productivity, Fatigue, Personal Productivity Profile & Adaptive Recommendations.
Pure statistical and heuristic analytics running 100% on-device.
"""

import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# Whitelist of allowed sanitized task types to ensure no raw personal notes leak
ALLOWED_TASK_TYPES = {
    "coding", "writing", "meeting", "reading", "planning",
    "exercise", "design", "research", "admin", "general"
}

# Whitelist of sanitized context locations
STANDARD_CONTEXTS = {
    "home office", "office", "cafe", "library", "meeting room",
    "transit", "home", "remote", "focus room"
}

def _sanitize_text(val: str, max_length: int = 120) -> str:
    """
    Strip potential PII, URLs, GPS coordinates, UUIDs, MAC addresses, phone numbers,
    and long numeric IDs from string values.
    """
    if not val:
        return ""
    # Strip URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "[URL_REDACTED]", str(val))
    # Strip email addresses
    cleaned = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_REDACTED]", cleaned)
    # Strip GPS coordinates (e.g. 37.7749, -122.4194)
    cleaned = re.sub(r"[-+]?\d{1,3}\.\d+,\s*[-+]?\d{1,3}\.\d+", "[GPS_REDACTED]", cleaned)
    # Strip UUIDs / device IDs
    cleaned = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "[DEVICE_ID_REDACTED]", cleaned)
    # Strip MAC addresses
    cleaned = re.sub(r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", "[DEVICE_ID_REDACTED]", cleaned)
    # Strip phone numbers
    cleaned = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]", cleaned)
    # Strip large digit sequences (>= 7 digits)
    cleaned = re.sub(r"\b\d{7,}\b", "[ID_REDACTED]", cleaned)
    return cleaned.strip()[:max_length]

def _sanitize_task_type(val: str) -> str:
    """
    Normalize raw task titles/notes strictly to privacy-safe categories.
    Raw task titles like 'Review PR #42 with Alice at https://github.com' are mapped
    to allowed categories ('coding') or 'general' so personal names/notes never leak.
    Clean single-word task category identifiers (e.g. 'robotics', 'coding') are preserved.
    """
    if not val:
        return "general"
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", " ", str(val)).lower()
    for allowed in ALLOWED_TASK_TYPES:
        if re.search(r"\b" + re.escape(allowed) + r"\b", clean):
            return allowed
    raw_stripped = str(val).strip().lower()
    if re.fullmatch(r"[a-z0-9_-]{1,24}", raw_stripped) and not any(ch.isdigit() for ch in raw_stripped[:3]):
        if not re.search(r"https?://|www\.|\@|[-+]?\d{1,3}\.\d+", raw_stripped):
            return raw_stripped
    return "general"

def _sanitize_context(val: str) -> str:
    """
    Normalize context location strictly to privacy-safe labels.
    GPS coordinates, URLs, or device IDs are purged and defaulted to 'Home Office'.
    """
    if not val:
        return "Home Office"
    clean = str(val).strip()
    if clean.lower() in STANDARD_CONTEXTS:
        return clean.title()
    # Check for GPS coordinates or URL leaks
    if re.search(r"[-+]?\d{1,3}\.\d+", clean) or re.search(r"https?://|www\.", clean):
        return "Home Office"
    sanitized = _sanitize_text(clean, max_length=30)
    return sanitized.title() if sanitized else "Home Office"


class InsightEngine:
    def __init__(
        self,
        tasks: List[Dict[str, Any]],
        context_signals: Optional[List[Dict[str, Any]]] = None,
        prediction_calibration: Optional[Dict[str, Any]] = None
    ):
        self.tasks = tasks or []
        self.context_signals = context_signals or []
        self.prediction_calibration = prediction_calibration or {
            "totalEvaluations": 0,
            "accuratePredictions": 0,
            "accuracyRate": 0.0,
            "meanCalibrationError": 0.0,
            "lastPredictionOutcome": "NONE",
            "lastPredictedScore": None,
            "lastActualOutcome": "NONE"
        }

    def _get_recency_weights(self) -> List[float]:
        n = len(self.tasks)
        if n <= 1:
            return [1.0] * n
        return [0.94 ** (n - 1 - i) for i in range(n)]

    def analyze(
        self,
        target_task_type: Optional[str] = None,
        current_hour: Optional[int] = None,
        current_context: Optional[str] = None,
        recent_screen_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        total_tasks = len(self.tasks)
        confidence = self._calculate_confidence()

        if total_tasks == 0:
            res = {
                "peakHour": "Insufficient Data",
                "procrastinationTrigger": "No activity patterns detected yet",
                "bestContext": "Track at least 5 tasks to calibrate",
                "recommendation": "Start tracking daily focus blocks to activate personalized insights.",
                "productivityScore": 0,
                "confidenceLevel": "Calibrating",
                "hourlyHeatmap": {str(h): 0 for h in range(24)},
                "fatigueLevel": "LOW",
                "fatigueScore": 0,
                "explanation": "Insufficient data: log at least 5 focus sessions to evaluate fatigue and context sensitivity.",
                "contextInsights": [],
                "distractionSensitivity": {
                    "level": "LOW",
                    "score": 0,
                    "vulnerableCategories": [],
                    "triggerAppCategories": [],
                    "summary": "Insufficient task and signal data to evaluate distraction sensitivity."
                },
                "productivityProfile": {
                    "bestFocusWindow": "Insufficient Data",
                    "bestTaskTypes": [],
                    "bestContext": "Track at least 5 tasks to calibrate",
                    "weakestFocusWindow": "Insufficient Data",
                    "peakProductivityScore": 0,
                    "averageCompletionRate": 0.0,
                    "fatiguePattern": "Insufficient sessions to detect fatigue onset",
                    "distractionPattern": "Insufficient sessions to detect distraction patterns",
                    "profileConfidence": "LOW",
                    "taskTypeAnalysis": []
                },
                "adaptiveRecommendations": [
                    {
                        "title": "Calibrate Habit Profile",
                        "advice": "Log at least 5 focus sessions across different hours to unlock adaptive coaching.",
                        "reason": "Current data volume is insufficient to generate statistically sound behavioral recommendations.",
                        "priority": "LOW",
                        "impact": "LOW"
                    }
                ],
                "predictionCalibration": self.prediction_calibration
            }
            if target_task_type is not None:
                res["taskPrediction"] = self.predict_task_readiness(
                    task_type=target_task_type,
                    current_hour=current_hour,
                    current_context=current_context,
                    recent_screen_duration=recent_screen_duration
                )
            return res

        peak_hour = self._detect_peak_hour()
        procrastination = self._detect_procrastination_trigger()
        context_insights = self._analyze_contexts()
        best_context_str = self._format_best_context(context_insights)
        fatigue = self._detect_fatigue()
        distraction = self._detect_distraction_sensitivity()
        score = self._calculate_productivity_score()
        heatmap = self._generate_hourly_heatmap()
        task_type_analysis = self._analyze_task_types()
        profile = self._build_productivity_profile(peak_hour, context_insights, fatigue, distraction, heatmap, task_type_analysis)
        adaptive_recs = self._generate_adaptive_recommendations(profile, context_insights, fatigue, distraction)

        # Top-level backward-compatible recommendation derived from primary adaptive recommendation
        primary_rec = adaptive_recs[0]
        top_recommendation = f"{primary_rec['advice']} {primary_rec['reason']}"

        result = {
            "peakHour": peak_hour,
            "procrastinationTrigger": procrastination,
            "bestContext": best_context_str,
            "recommendation": top_recommendation,
            "productivityScore": score,
            "confidenceLevel": confidence,
            "hourlyHeatmap": heatmap,
            "fatigueLevel": fatigue["level"],
            "fatigueScore": fatigue["score"],
            "explanation": fatigue["explanation"],
            "contextInsights": context_insights,
            "distractionSensitivity": distraction,
            "productivityProfile": profile,
            "adaptiveRecommendations": adaptive_recs,
            "predictionCalibration": self.prediction_calibration
        }

        if target_task_type is not None:
            result["taskPrediction"] = self.predict_task_readiness(
                task_type=target_task_type,
                current_hour=current_hour,
                current_context=current_context,
                recent_screen_duration=recent_screen_duration
            )

        return result

    def _calculate_confidence(self) -> str:
        total = len(self.tasks)
        if total < 5:
            return "Calibrating"
        elif total < 20:
            return "Medium"
        return "High"

    def _calculate_profile_confidence(self) -> str:
        total = len(self.tasks)
        if total < 5:
            return "LOW"
        elif total <= 15:
            return "MEDIUM"
        return "HIGH"

    def _detect_peak_hour(self) -> str:
        weights = self._get_recency_weights()
        hourly_completions = defaultdict(float)
        for i, task in enumerate(self.tasks):
            if task.get("completedAt"):
                dt = datetime.fromtimestamp(task["createdAt"] / 1000)
                hourly_completions[dt.hour] += weights[i]

        if not hourly_completions:
            return "09:00 - 11:00 AM"

        # 2-hour window (h, h+1) to match returned 2-hour span
        best_hour = max(range(24), key=lambda h: (hourly_completions[h] + hourly_completions[(h + 1) % 24], hourly_completions[h]))
        end_hour = (best_hour + 2) % 24
        return f"{best_hour:02d}:00 - {end_hour:02d}:00 (Peak focus completion)"

    def _detect_procrastination_trigger(self) -> str:
        type_stats = defaultdict(lambda: {"total": 0, "failed": 0, "after_3pm": 0})
        for task in self.tasks:
            t_type = task.get("type", "other")
            dt = datetime.fromtimestamp(task["createdAt"] / 1000)
            type_stats[t_type]["total"] += 1
            if not task.get("completedAt"):
                type_stats[t_type]["failed"] += 1
                if dt.hour >= 15:
                    type_stats[t_type]["after_3pm"] += 1

        worst_type = None
        max_failure_rate = 0.0
        for t_type, stats in type_stats.items():
            rate = stats["failed"] / stats["total"] if stats["total"] > 0 else 0
            if rate > max_failure_rate:
                max_failure_rate = rate
                worst_type = t_type

        if worst_type and max_failure_rate >= 0.4:
            return f"{worst_type.capitalize()} tasks scheduled after 3:00 PM ({int(max_failure_rate*100)}% abandon rate)"
        return "Low afternoon completion on complex non-routine tasks"

    def _analyze_contexts(self) -> List[Dict[str, Any]]:
        weights = self._get_recency_weights()
        context_map = defaultdict(lambda: {"total": 0, "completed": 0, "weighted_total": 0.0, "weighted_completed": 0.0, "durations": []})
        for i, task in enumerate(self.tasks):
            loc = task.get("location") or "Home Office"
            w = weights[i]
            context_map[loc]["total"] += 1
            context_map[loc]["weighted_total"] += w
            dur = task.get("duration", 0)
            context_map[loc]["durations"].append(dur)
            if task.get("completedAt"):
                context_map[loc]["completed"] += 1
                context_map[loc]["weighted_completed"] += w

        results = []
        for loc, stats in context_map.items():
            total = stats["total"]
            completed = stats["completed"]
            w_total = stats["weighted_total"]
            w_completed = stats["weighted_completed"]
            rate = round((w_completed / w_total) * 100, 1) if w_total > 0 else 0.0
            avg_dur = round(sum(stats["durations"]) / total, 1) if total > 0 else 0.0
            if rate >= 75.0:
                status = "Optimal"
            elif rate >= 50.0:
                status = "Moderate"
            else:
                status = "Suboptimal"

            results.append({
                "context": loc,
                "completionRate": rate,
                "totalTasks": total,
                "completedTasks": completed,
                "avgDuration": avg_dur,
                "status": status
            })

        results.sort(key=lambda x: (x["completionRate"], x["totalTasks"]), reverse=True)
        return results

    def _format_best_context(self, context_insights: List[Dict[str, Any]]) -> str:
        if not context_insights:
            return "Home Office (Consistent completion)"
        best = next((c for c in context_insights if c["totalTasks"] >= 2), context_insights[0])
        return f"{best['context']} ({best['completionRate']}% completion across {best['totalTasks']} sessions)"

    def _detect_fatigue(self) -> Dict[str, Any]:
        screen_pts = 0
        max_screen_sec = 0
        if self.context_signals:
            max_screen_sec = max((s.get("screenOnDuration", 0) for s in self.context_signals), default=0)
            avg_screen_sec = sum(s.get("screenOnDuration", 0) for s in self.context_signals) / len(self.context_signals)
            if max_screen_sec >= 7200 or avg_screen_sec >= 4500:
                screen_pts = 30
            elif max_screen_sec >= 4500 or avg_screen_sec >= 3000:
                screen_pts = 20
            elif max_screen_sec >= 2700:
                screen_pts = 10
        else:
            avg_task_dur = sum(t.get("duration", 0) for t in self.tasks) / len(self.tasks) if self.tasks else 0
            if avg_task_dur >= 3600:
                screen_pts = 20
            elif avg_task_dur >= 2400:
                screen_pts = 10
            elif avg_task_dur >= 1200:
                screen_pts = 5

        morning_tasks = [t for t in self.tasks if datetime.fromtimestamp(t["createdAt"] / 1000).hour < 13]
        afternoon_tasks = [t for t in self.tasks if datetime.fromtimestamp(t["createdAt"] / 1000).hour >= 13]

        completion_drop_pts = 0
        m_rate = 0.0
        a_rate = 0.0
        drop = 0.0
        if morning_tasks and afternoon_tasks:
            m_comp = sum(1 for t in morning_tasks if t.get("completedAt"))
            a_comp = sum(1 for t in afternoon_tasks if t.get("completedAt"))
            m_rate = m_comp / len(morning_tasks)
            a_rate = a_comp / len(afternoon_tasks)
            drop = m_rate - a_rate
            if drop >= 0.40:
                completion_drop_pts = 30
            elif drop >= 0.20:
                completion_drop_pts = 20
            elif drop >= 0.10:
                completion_drop_pts = 10

        duration_shrink_pts = 0
        m_dur = 0.0
        a_dur = 0.0
        if morning_tasks and afternoon_tasks:
            m_dur = sum(t.get("duration", 0) for t in morning_tasks) / len(morning_tasks)
            a_dur = sum(t.get("duration", 0) for t in afternoon_tasks) / len(afternoon_tasks)
            if m_dur > 0 and (a_dur / m_dur) <= 0.50:
                duration_shrink_pts = 20
            elif m_dur > 0 and (a_dur / m_dur) <= 0.75:
                duration_shrink_pts = 10

        switching_pts = 0
        non_prod_signals = 0
        if self.context_signals:
            non_prod_signals = sum(1 for s in self.context_signals if s.get("appCategory") in ["Social", "Entertainment"])
            non_prod_ratio = non_prod_signals / len(self.context_signals)
            if non_prod_ratio >= 0.35:
                switching_pts = 20
            elif non_prod_ratio >= 0.15:
                switching_pts = 10
        else:
            sorted_tasks = sorted(self.tasks, key=lambda t: t.get("createdAt", 0))
            switches = 0
            for i in range(1, len(sorted_tasks)):
                gap = (sorted_tasks[i].get("createdAt", 0) - sorted_tasks[i-1].get("createdAt", 0)) / 1000
                if gap < 2700 and sorted_tasks[i].get("type") != sorted_tasks[i-1].get("type"):
                    switches += 1
            if switches >= 4:
                switching_pts = 15
            elif switches >= 2:
                switching_pts = 10

        total_score = min(100, max(0, screen_pts + completion_drop_pts + duration_shrink_pts + switching_pts))
        if total_score >= 65:
            level = "HIGH"
        elif total_score >= 35:
            level = "MEDIUM"
        else:
            level = "LOW"

        explanations = []
        if drop >= 0.20:
            explanations.append(f"completion rate drops by {int(drop * 100)}% in the afternoon ({int(m_rate * 100)}% morning vs {int(a_rate * 100)}% afternoon)")
        if m_dur > 0 and (a_dur / m_dur) <= 0.75:
            explanations.append(f"focus sessions shorten by {int((1.0 - a_dur / m_dur) * 100)}% after mid-day")
        if max_screen_sec >= 4500:
            explanations.append(f"prolonged continuous screen time exceeds {max_screen_sec // 60} minutes")
        elif screen_pts >= 10:
            explanations.append("extended cumulative focus session duration detected")
        if non_prod_signals > 0:
            explanations.append(f"non-productive app category switches observed ({non_prod_signals} signals)")
        elif switching_pts >= 10:
            explanations.append("frequent consecutive task switching observed")

        if not explanations:
            explanation = f"Fatigue is {level} (score: {total_score}/100). Focus duration and completion rates remain stable across work blocks."
        else:
            explanation = f"Fatigue is {level} (score: {total_score}/100). " + "; ".join(explanations).capitalize() + "."

        return {
            "level": level,
            "score": total_score,
            "explanation": explanation
        }

    def _detect_distraction_sensitivity(self) -> Dict[str, Any]:
        type_failures = defaultdict(lambda: {"total": 0, "failed": 0})
        for task in self.tasks:
            t_type = task.get("type", "other")
            type_failures[t_type]["total"] += 1
            if not task.get("completedAt"):
                type_failures[t_type]["failed"] += 1

        vulnerable = []
        for t_type, stats in type_failures.items():
            if stats["total"] >= 2:
                fail_rate = stats["failed"] / stats["total"]
                if fail_rate >= 0.40:
                    vulnerable.append(t_type)

        trigger_categories = set()
        for s in self.context_signals:
            cat = s.get("appCategory")
            if cat in ["Social", "Entertainment", "Communication"]:
                trigger_categories.add(cat)

        total_tasks = len(self.tasks)
        failed_tasks = sum(1 for t in self.tasks if not t.get("completedAt"))
        fail_ratio = (failed_tasks / total_tasks) if total_tasks > 0 else 0.0

        score = int(fail_ratio * 60)
        if trigger_categories:
            score = min(100, score + 40)
        elif any("Cafe" in (t.get("location") or "") for t in self.tasks if not t.get("completedAt")):
            score = min(100, score + 25)

        if score >= 60:
            level = "HIGH"
        elif score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        triggers_list = sorted(list(trigger_categories))
        if vulnerable and triggers_list:
            summary = f"{level} sensitivity: {', '.join(vulnerable).capitalize()} tasks show high abandonment when {', '.join(triggers_list)} apps are accessed."
        elif vulnerable:
            summary = f"{level} sensitivity: {', '.join(vulnerable).capitalize()} tasks exhibit high abandon rates outside optimal focus contexts."
        else:
            summary = f"{level} sensitivity: low disruption from task switching and context changes."

        return {
            "level": level,
            "score": score,
            "vulnerableCategories": vulnerable,
            "triggerAppCategories": triggers_list,
            "summary": summary
        }

    def _analyze_task_types(self) -> List[Dict[str, Any]]:
        weights = self._get_recency_weights()
        tasks_by_type = defaultdict(list)
        weights_by_type = defaultdict(list)
        for i, task in enumerate(self.tasks):
            t_type = task.get("type", "other")
            tasks_by_type[t_type].append(task)
            weights_by_type[t_type].append(weights[i])

        analysis_list = []
        for t_type, type_tasks in tasks_by_type.items():
            t_weights = weights_by_type[t_type]
            total = len(type_tasks)
            w_total = sum(t_weights)
            w_completed = sum(w for t, w in zip(type_tasks, t_weights) if t.get("completedAt"))
            completed = sum(1 for t in type_tasks if t.get("completedAt"))
            failed = total - completed
            completion_rate = round((w_completed / w_total) * 100, 1) if w_total > 0 else 0.0
            abandonment_rate = round(((w_total - w_completed) / w_total) * 100, 1) if w_total > 0 else 0.0
            avg_dur = round(sum(t.get("duration", 0) for t in type_tasks) / total, 1) if total > 0 else 0.0
            prod_score = int(round(completion_rate * 0.7 + min(1.0, avg_dur / 3600.0) * 30))
            prod_score = max(0, min(100, prod_score))

            # Detect strongest time window for this specific task type with recency weights
            strongest_window = "Insufficient data"
            if total >= 2:
                hourly_success = defaultdict(lambda: {"attempts": 0.0, "completed": 0.0})
                for t, w in zip(type_tasks, t_weights):
                    h = datetime.fromtimestamp(t["createdAt"] / 1000).hour
                    hourly_success[h]["attempts"] += w
                    if t.get("completedAt"):
                        hourly_success[h]["completed"] += w

                best_hour = None
                best_hour_rate = -1.0
                for h in range(24):
                    # Check 2-hour sliding window (h, h+1)
                    attempts_in_window = hourly_success[h]["attempts"] + hourly_success[(h + 1) % 24]["attempts"]
                    comp_in_window = hourly_success[h]["completed"] + hourly_success[(h + 1) % 24]["completed"]
                    if attempts_in_window > 0 and comp_in_window > 0:
                        rate = comp_in_window / attempts_in_window
                        if rate > best_hour_rate or (rate == best_hour_rate and attempts_in_window > hourly_success[best_hour]["attempts"]):
                            best_hour_rate = rate
                            best_hour = h

                if best_hour is not None:
                    strongest_window = f"{best_hour:02d}:00 - {(best_hour + 2) % 24:02d}:00"

            analysis_list.append({
                "taskType": t_type,
                "strongestWindow": strongest_window,
                "completionRate": completion_rate,
                "abandonmentRate": abandonmentment_rate if 'abandonmentment_rate' in locals() else abandonment_rate,
                "avgDuration": avg_dur,
                "productivityScore": prod_score,
                "totalSessions": total
            })

        analysis_list.sort(key=lambda x: (x["completionRate"], x["totalSessions"]), reverse=True)
        return analysis_list

    def _detect_weakest_focus_window(self) -> str:
        hourly_stats = defaultdict(lambda: {"attempts": 0, "failed": 0})
        for task in self.tasks:
            h = datetime.fromtimestamp(task["createdAt"] / 1000).hour
            hourly_stats[h]["attempts"] += 1
            if not task.get("completedAt"):
                hourly_stats[h]["failed"] += 1

        worst_hour = None
        highest_fail_rate = 0.0

        for h in range(24):
            attempts_in_window = hourly_stats[h]["attempts"] + hourly_stats[(h + 1) % 24]["attempts"]
            failed_in_window = hourly_stats[h]["failed"] + hourly_stats[(h + 1) % 24]["failed"]
            if attempts_in_window >= 2:
                rate = failed_in_window / attempts_in_window
                if rate > highest_fail_rate:
                    highest_fail_rate = rate
                    worst_hour = h

        if worst_hour is not None and highest_fail_rate >= 0.30:
            return f"{worst_hour:02d}:00 - {(worst_hour + 2) % 24:02d}:00"
        return "None detected"

    def _build_productivity_profile(
        self,
        peak_hour: str,
        context_insights: List[Dict[str, Any]],
        fatigue: Dict[str, Any],
        distraction: Dict[str, Any],
        heatmap: Dict[str, int],
        task_type_analysis: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total = len(self.tasks)
        profile_conf = self._calculate_profile_confidence()

        if total < 5:
            return {
                "bestFocusWindow": "Insufficient Data",
                "bestTaskTypes": [],
                "bestContext": "Track at least 5 tasks to calibrate",
                "weakestFocusWindow": "Insufficient Data",
                "peakProductivityScore": 0,
                "averageCompletionRate": 0.0,
                "fatiguePattern": "Insufficient sessions to detect fatigue onset",
                "distractionPattern": "Insufficient sessions to detect distraction patterns",
                "profileConfidence": "LOW",
                "taskTypeAnalysis": task_type_analysis
            }

        # 1. Best Focus Window
        best_window = peak_hour.split("(")[0].strip()

        # 2. Best Task Types (completion rate >= 70% and >= 2 sessions)
        best_types = [t["taskType"] for t in task_type_analysis if t["completionRate"] >= 70.0 and t["totalSessions"] >= 2]

        # 3. Best Context
        best_ctx_name = next((c["context"] for c in context_insights if c["totalTasks"] >= 2 and c["status"] == "Optimal"), None) or (context_insights[0]["context"] if context_insights else "Home Office")

        # 4. Weakest Focus Window
        weakest_window = self._detect_weakest_focus_window()

        # 5. Peak Productivity Score & Average Completion Rate
        peak_score = max(heatmap.values(), default=0)
        weights = self._get_recency_weights()
        weighted_completed = sum(weights[i] for i, t in enumerate(self.tasks) if t.get("completedAt"))
        total_weight = sum(weights)
        avg_completion = round((weighted_completed / total_weight) * 100, 1) if total_weight > 0 else 0.0

        # 6. Fatigue Pattern
        if fatigue["score"] >= 65:
            fatigue_pattern = f"Severe fatigue peaks after {weakest_window.split(' - ')[0] if weakest_window != 'None detected' else '15:00'} (score: {fatigue['score']}/100) after extended screen sessions."
        elif fatigue["score"] >= 35:
            fatigue_pattern = f"Moderate fatigue appears in late afternoon (score: {fatigue['score']}/100) with focus durations shrinking."
        else:
            fatigue_pattern = "Stable energy profile across daytime work blocks with minimal session shrinkage."

        # 7. Distraction Pattern
        if distraction["vulnerableCategories"] and distraction["triggerAppCategories"]:
            distraction_pattern = f"High vulnerability on {', '.join(distraction['vulnerableCategories'])} when {', '.join(distraction['triggerAppCategories'])} apps are accessed."
        elif distraction["vulnerableCategories"]:
            distraction_pattern = f"{', '.join(distraction['vulnerableCategories']).capitalize()} tasks show elevated abandonment outside optimal environments."
        else:
            distraction_pattern = "Low distraction susceptibility across tracked contexts."

        return {
            "bestFocusWindow": best_window,
            "bestTaskTypes": best_types,
            "bestContext": best_ctx_name,
            "weakestFocusWindow": weakest_window,
            "peakProductivityScore": peak_score,
            "averageCompletionRate": avg_completion,
            "fatiguePattern": fatigue_pattern,
            "distractionPattern": distraction_pattern,
            "profileConfidence": profile_conf,
            "taskTypeAnalysis": task_type_analysis
        }

    def _generate_adaptive_recommendations(
        self,
        profile: Dict[str, Any],
        context_insights: List[Dict[str, Any]],
        fatigue: Dict[str, Any],
        distraction: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        candidates = []

        # Rec 1: Peak Focus Alignment
        if profile["bestFocusWindow"] != "Insufficient Data" and profile["bestTaskTypes"]:
            primary_type = profile["bestTaskTypes"][0]
            type_stat = next((t for t in profile["taskTypeAnalysis"] if t["taskType"] == primary_type), None)
            rate_str = f"{int(type_stat['completionRate'])}%" if type_stat else "peak"
            candidates.append({
                "weight": 95,
                "title": f"Protect Peak {primary_type.capitalize()} Window",
                "advice": f"Schedule demanding {primary_type} tasks between {profile['bestFocusWindow']} in {profile['bestContext']}.",
                "reason": f"Your {primary_type} completion rate reaches {rate_str} in {profile['bestContext']} during this window.",
                "priority": "HIGH",
                "impact": "HIGH"
            })

        # Rec 2: Fatigue & Screen Strain Mitigation
        if fatigue["score"] >= 35:
            weak_start = profile["weakestFocusWindow"].split(" - ")[0] if profile["weakestFocusWindow"] != "None detected" else "15:00"
            is_high = fatigue["score"] >= 65
            candidates.append({
                "weight": 90 if is_high else 70,
                "title": "Fatigue Break Pacing",
                "advice": f"Cap afternoon focus sessions at 45 minutes and step away before {weak_start}.",
                "reason": f"{profile['fatiguePattern']}",
                "priority": "HIGH" if is_high else "MEDIUM",
                "impact": "HIGH" if is_high else "MEDIUM"
            })

        # Rec 3: Context Optimization
        if len(context_insights) >= 2:
            best_c = context_insights[0]
            worst_c = context_insights[-1]
            if best_c["completionRate"] - worst_c["completionRate"] >= 25.0:
                vulnerable_type = distraction["vulnerableCategories"][0] if distraction["vulnerableCategories"] else "complex"
                candidates.append({
                    "weight": 80,
                    "title": "Shift Context for Vulnerable Tasks",
                    "advice": f"Relocate {vulnerable_type} sessions from {worst_c['context']} to {best_c['context']}.",
                    "reason": f"Completion rate is {best_c['completionRate']}% in {best_c['context']} versus {worst_c['completionRate']}% in {worst_c['context']}.",
                    "priority": "MEDIUM",
                    "impact": "HIGH" if (best_c["completionRate"] - worst_c["completionRate"]) >= 40.0 else "MEDIUM"
                })

        # Rec 4: Distraction Barrier
        if distraction["level"] in ["HIGH", "MEDIUM"] and distraction["triggerAppCategories"]:
            triggers = ", ".join(distraction["triggerAppCategories"])
            candidates.append({
                "weight": 75,
                "title": "Silence Interrupting App Categories",
                "advice": f"Enable Do Not Disturb to block {triggers} alerts during focus blocks.",
                "reason": f"{profile['distractionPattern']}",
                "priority": "MEDIUM",
                "impact": "MEDIUM"
            })

        if not candidates:
            candidates.append({
                "weight": 50,
                "title": "Maintain Rhythm",
                "advice": f"Continue consistent task tracking in your {profile['bestFocusWindow']} focus block.",
                "reason": "Current session distribution shows stable pacing and low distraction interference.",
                "priority": "LOW",
                "impact": "LOW"
            })

        candidates.sort(key=lambda x: x["weight"], reverse=True)
        # Return top 1-3 recommendations, dropping internal sort weight
        top_recs = []
        for c in candidates[:3]:
            top_recs.append({
                "title": c["title"],
                "advice": c["advice"],
                "reason": c["reason"],
                "priority": c["priority"],
                "impact": c["impact"]
            })
        return top_recs

    def _calculate_productivity_score(self) -> int:
        total = len(self.tasks)
        if total == 0:
            return 0
        weights = self._get_recency_weights()
        weighted_completed = sum(weights[i] for i, t in enumerate(self.tasks) if t.get("completedAt"))
        total_weight = sum(weights)
        return max(0, min(100, int((weighted_completed / total_weight) * 100)))

    def _generate_hourly_heatmap(self) -> Dict[str, int]:
        weights = self._get_recency_weights()
        heatmap = {}
        hour_buckets = defaultdict(lambda: {"attempts": 0.0, "completed": 0.0})
        for i, task in enumerate(self.tasks):
            dt = datetime.fromtimestamp(task["createdAt"] / 1000)
            h = dt.hour
            hour_buckets[h]["attempts"] += weights[i]
            if task.get("completedAt"):
                hour_buckets[h]["completed"] += weights[i]

        for h in range(24):
            b = hour_buckets[h]
            if b["attempts"] == 0:
                heatmap[str(h)] = 0
            else:
                heatmap[str(h)] = int((b["completed"] / b["attempts"]) * 100)
        return heatmap

    def predict_task_readiness(
        self,
        task_type: str,
        current_hour: Optional[int] = None,
        current_context: Optional[str] = None,
        recent_screen_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate predictive productivity: 'Should I do this task now?'
        Calculates a deterministic, explainable readiness score (0-100) based on
        task type historical performance, time-of-day alignment, context match,
        fatigue level, screen strain, and distraction vulnerability.
        """
        # Privacy sanitization of inputs
        task_type = _sanitize_task_type(task_type)
        if current_context is not None:
            current_context = _sanitize_context(current_context)

        # Resolve defaults
        if current_hour is None:
            if self.context_signals:
                current_hour = datetime.fromtimestamp(self.context_signals[-1]["timestamp"] / 1000).hour
            elif self.tasks:
                current_hour = datetime.fromtimestamp(self.tasks[-1]["createdAt"] / 1000).hour
            else:
                current_hour = datetime.now().hour

        if current_context is None:
            if self.context_signals:
                current_context = _sanitize_context(self.context_signals[-1].get("location") or "Home Office")
            elif self.tasks:
                current_context = _sanitize_context(self.tasks[-1].get("location") or "Home Office")
            else:
                current_context = "Home Office"


        if recent_screen_duration is None:
            if self.context_signals:
                recent_screen_duration = self.context_signals[-1].get("screenOnDuration", 0)
            else:
                recent_screen_duration = 0

        total_tasks = len(self.tasks)
        type_tasks = [t for t in self.tasks if t.get("type", "").lower() == task_type.lower()]
        total_type_tasks = len(type_tasks)

        # 1. Cold start / Insufficient data handling
        if total_tasks == 0:
            return {
                "taskType": task_type,
                "predictedScore": 50,
                "confidence": "LOW",
                "riskLevel": "MEDIUM",
                "bestAlternativeWindow": "09:00 - 11:00",
                "reason": f"No historical sessions logged. Calibration required to establish baseline readiness for {task_type}.",
                "recommendation": f"Start a 25-minute calibration block for {task_type} to establish baseline metrics."
            }

        if total_tasks < 5 or total_type_tasks == 0:
            completed_all = sum(1 for t in self.tasks if t.get("completedAt"))
            overall_rate = (completed_all / total_tasks) if total_tasks > 0 else 0.5
            provisional_score = max(35, min(65, int(overall_rate * 50 + 20)))
            risk_level = "LOW" if provisional_score >= 60 else ("HIGH" if provisional_score < 40 else "MEDIUM")
            best_window = "09:00 - 11:00"
            if total_type_tasks == 0:
                reason = f"No historical sessions recorded for '{task_type}'. Provisional score based on overall user completion rate ({int(overall_rate * 100)}%)."
                rec = f"Log at least 3 {task_type} sessions across different times to calibrate high-confidence predictions."
            else:
                reason = f"Insufficient sample size ({total_type_tasks} logged session{'s' if total_type_tasks > 1 else ''} for '{task_type}'). Baseline readiness estimate."
                rec = f"Continue tracking {task_type} sessions across various hours to establish personalized forecasts."

            return {
                "taskType": task_type,
                "predictedScore": provisional_score,
                "confidence": "LOW",
                "riskLevel": risk_level,
                "bestAlternativeWindow": best_window,
                "reason": reason,
                "recommendation": rec
            }

        # 2. Historical Task-Type Performance (0..35 points)
        type_completed = sum(1 for t in type_tasks if t.get("completedAt"))
        type_comp_rate = type_completed / total_type_tasks
        score_type = type_comp_rate * 35.0

        # 3. Time-of-Day Alignment (0..25 points)
        type_hour_tasks = [t for t in type_tasks if abs(datetime.fromtimestamp(t["createdAt"] / 1000).hour - current_hour) <= 1]
        if type_hour_tasks:
            hour_comp = sum(1 for t in type_hour_tasks if t.get("completedAt")) / len(type_hour_tasks)
            score_time = hour_comp * 25.0
        else:
            heatmap = self._generate_hourly_heatmap()
            hour_rate = heatmap.get(str(current_hour), 0) / 100.0
            hour_attempts = sum(1 for t in self.tasks if datetime.fromtimestamp(t["createdAt"] / 1000).hour == current_hour)
            if hour_attempts == 0:
                if 8 <= current_hour <= 12:
                    hour_rate = 0.8
                elif 13 <= current_hour <= 17:
                    hour_rate = 0.45
                elif 18 <= current_hour <= 21:
                    hour_rate = 0.65
                else:
                    hour_rate = 0.25
            score_time = hour_rate * 25.0

        # 4. Context Alignment (0..20 points)
        context_insights = self._analyze_contexts()
        matching_ctx = next((c for c in context_insights if c["context"].lower() == current_context.lower()), None)
        type_in_ctx = [t for t in type_tasks if (t.get("location") or "Home Office").lower() == current_context.lower()]
        if type_in_ctx:
            ctx_type_comp = sum(1 for t in type_in_ctx if t.get("completedAt")) / len(type_in_ctx)
            score_context = ctx_type_comp * 20.0
        elif matching_ctx:
            score_context = (matching_ctx["completionRate"] / 100.0) * 20.0
        else:
            score_context = 10.0

        # 5. Base Readiness Offset (20 points)
        score_base = 20.0

        # 6. Fatigue & Screen Strain Penalty (0..25 points)
        fatigue = self._detect_fatigue()
        fatigue_score_pts = (fatigue["score"] / 100.0) * 15.0
        screen_pts = 0.0
        if recent_screen_duration >= 5400:
            screen_pts = 10.0
        elif recent_screen_duration >= 3600:
            screen_pts = 7.0
        elif recent_screen_duration >= 2400:
            screen_pts = 4.0
        elif recent_screen_duration >= 1200:
            screen_pts = 2.0
        total_fatigue_penalty = min(25.0, fatigue_score_pts + screen_pts)

        # 7. Distraction & Context Vulnerability Penalty (0..15 points)
        distraction = self._detect_distraction_sensitivity()
        distraction_penalty = 0.0
        is_vulnerable = task_type.lower() in [v.lower() for v in distraction["vulnerableCategories"]]
        if is_vulnerable:
            if matching_ctx and matching_ctx["status"] == "Suboptimal":
                distraction_penalty += 12.0
            else:
                distraction_penalty += 6.0
        if distraction["level"] == "HIGH":
            distraction_penalty += 3.0
        total_distraction_penalty = min(15.0, distraction_penalty)

        # 8. Score Synthesis
        raw_score = score_base + score_type + score_time + score_context - total_fatigue_penalty - total_distraction_penalty
        predicted_score = int(round(max(0.0, min(100.0, raw_score))))

        # 9. Risk Level & Confidence
        if predicted_score >= 70:
            risk_level = "LOW"
        elif predicted_score >= 45:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        if total_type_tasks >= 3 and total_tasks >= 5:
            confidence = "HIGH"
        elif total_type_tasks >= 1 and total_tasks >= 5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # 10. Best Alternative Window
        task_types = self._analyze_task_types()
        type_stat = next((t for t in task_types if t["taskType"].lower() == task_type.lower()), None)
        if type_stat and type_stat["strongestWindow"] != "Insufficient data":
            best_window = type_stat["strongestWindow"]
        else:
            best_window = self._detect_peak_hour().split("(")[0].strip()

        # Determine alternative window string
        window_start = 9
        window_end = 11
        try:
            parts = best_window.split(" - ")
            window_start = int(parts[0].split(":")[0])
            window_end = int(parts[1].split(":")[0])
        except Exception:
            window_start = 9
            window_end = 11

        is_currently_in_best_window = (window_start <= current_hour < window_end) if window_start < window_end else (current_hour >= window_start or current_hour < window_end)

        if is_currently_in_best_window:
            if risk_level == "LOW":
                best_alt_window = f"Current window ({best_window}) is optimal"
            else:
                best_alt_window = f"Tomorrow morning ({best_window})"
        else:
            best_alt_window = best_window

        # 11. Explainable Reason
        positives = []
        negatives = []

        if type_comp_rate >= 0.75:
            positives.append(f"{task_type.capitalize()} completion is high ({int(type_comp_rate * 100)}%)")
        elif type_comp_rate <= 0.40:
            negatives.append(f"{task_type.capitalize()} completion is historically low ({int(type_comp_rate * 100)}%)")

        if score_time >= 18.0:
            positives.append(f"time-of-day alignment is optimal ({current_hour:02d}:00)")
        elif score_time <= 10.0:
            negatives.append(f"hour ({current_hour:02d}:00) is outside your peak focus")

        if score_context >= 15.0:
            positives.append(f"environment '{current_context}' is high-performing")
        elif matching_ctx and matching_ctx["status"] == "Suboptimal":
            negatives.append(f"environment '{current_context}' has high abandonment")

        if fatigue["score"] >= 35 or recent_screen_duration >= 3600:
            negatives.append(f"fatigue is elevated (score: {fatigue['score']}/100, {recent_screen_duration // 60}m screen time)")

        if is_vulnerable and (matching_ctx and matching_ctx["status"] == "Suboptimal"):
            negatives.append(f"{task_type} is highly vulnerable to distractions in {current_context}")

        if risk_level == "HIGH":
            reason = f"{task_type.capitalize()} now has HIGH risk ({predicted_score}/100): " + ("; ".join(negatives) if negatives else f"historical completion is significantly lower during this time and context") + f". Your {task_type} completion is significantly higher during {best_window}."
        elif risk_level == "MEDIUM":
            reason = f"{task_type.capitalize()} readiness is MODERATE ({predicted_score}/100): " + ("; ".join(positives[:1] + negatives[:2]) if (positives or negatives) else "balanced conditions with minor timing or fatigue friction") + "."
        else:
            reason = f"Optimal conditions for {task_type} ({predicted_score}/100): " + ("; ".join(positives) if positives else f"strong historical focus metrics in {current_context}") + "."

        # 12. Recommendation
        best_ctx_name = context_insights[0]["context"] if context_insights else "Home Office"
        if risk_level == "HIGH":
            recommendation = f"Consider postponing {task_type} to {best_alt_window} in {best_ctx_name}. Take a 15-minute break now to recover cognitive energy."
        elif risk_level == "MEDIUM":
            recommendation = f"Proceed with a focused 25-minute sprint for {task_type}. Minimize distractions and take a short recovery break afterward."
        else:
            recommendation = f"Start {task_type} now. You are in optimal conditions for sustained focus in {current_context}."

        return {
            "taskType": task_type,
            "predictedScore": predicted_score,
            "confidence": confidence,
            "riskLevel": risk_level,
            "bestAlternativeWindow": best_alt_window,
            "reason": reason,
            "recommendation": recommendation
        }

    def update_user_model(self, new_task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update current engine state with a new task outcome and context signal."""
        prev_model = {
            "tasks": self.tasks,
            "contextSignals": self.context_signals,
            "predictionCalibration": self.prediction_calibration
        }
        res = update_user_model(prev_model, new_task, context)
        self.tasks = res["tasks"]
        self.context_signals = res["contextSignals"]
        self.prediction_calibration = res["predictionCalibration"]
        return res

    updateUserModel = update_user_model

    def evaluate_current_state(
        self,
        task_type: str = "coding",
        current_hour: Optional[int] = None,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        screen_duration: int = 0,
        recent_activity: Optional[Union[List[Any], Dict[str, Any]]] = None,
        last_intervention_time: Optional[int] = None,
        last_trigger: Optional[str] = None,
        current_time: Optional[int] = None,
        cooldown_seconds: int = 900,
        model: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Real-Time AI Coach Evaluation.
        Evaluates current user state (OPTIMAL, NORMAL, AT_RISK, RECOVERY), identifies
        friction triggers, compiles privacy-sanitized structured evidence for local AI models,
        generates offline-ready coaching interventions, and applies anti-spam throttling.
        """
        if current_time is None:
            current_time = int(time.time() * 1000)

        # 0. Privacy Sanitization of Inputs
        task_type = _sanitize_task_type(task_type)

        # 1. Resolve Context
        if isinstance(context, dict):
            context_loc = _sanitize_context(context.get("location") or "Home Office")
            if screen_duration == 0:
                screen_duration = int(context.get("screenOnDuration", 0))
        elif isinstance(context, str):
            context_loc = _sanitize_context(context)
        elif self.context_signals:
            context_loc = _sanitize_context(self.context_signals[-1].get("location") or "Home Office")
            if screen_duration == 0:
                screen_duration = int(self.context_signals[-1].get("screenOnDuration", 0))
        elif self.tasks:
            context_loc = _sanitize_context(self.tasks[-1].get("location") or "Home Office")
        else:
            context_loc = "Home Office"

        # 2. Resolve Current Hour
        if current_hour is None:
            if isinstance(context, dict) and "timestamp" in context:
                current_hour = datetime.fromtimestamp(context["timestamp"] / 1000).hour
            elif self.context_signals:
                current_hour = datetime.fromtimestamp(self.context_signals[-1]["timestamp"] / 1000).hour
            elif self.tasks:
                current_hour = datetime.fromtimestamp(self.tasks[-1]["createdAt"] / 1000).hour
            else:
                current_hour = datetime.fromtimestamp(current_time / 1000).hour

        # 3. Analyze Recent Activity
        num_switches = 0
        non_prod_count = 0
        if isinstance(recent_activity, dict):
            num_switches = recent_activity.get("contextSwitches", recent_activity.get("switches", 0))
            non_prod_count = recent_activity.get("nonProductiveAppCount", recent_activity.get("nonProductiveSwitches", 0))
        elif isinstance(recent_activity, list):
            for i in range(len(recent_activity)):
                item = recent_activity[i]
                cat = item.get("appCategory") if isinstance(item, dict) else str(item)
                if cat in ["Social", "Entertainment", "Communication"]:
                    non_prod_count += 1
                if i > 0:
                    prev = recent_activity[i-1]
                    prev_cat = prev.get("appCategory") if isinstance(prev, dict) else str(prev)
                    if cat != prev_cat:
                        num_switches += 1
        elif self.context_signals:
            recent_slice = [
                s for s in self.context_signals[-10:]
                if abs(current_time - s.get("timestamp", 0)) <= 1800000
            ]
            for i in range(len(recent_slice)):
                item = recent_slice[i]
                cat = item.get("appCategory", "")
                if cat in ["Social", "Entertainment", "Communication"]:
                    non_prod_count += 1
                if i > 0 and cat != recent_slice[i-1].get("appCategory", ""):
                    num_switches += 1

        # 4. Profile & Baseline Analytics
        fatigue = self._detect_fatigue()
        distraction = self._detect_distraction_sensitivity()
        context_insights = self._analyze_contexts()
        heatmap = self._generate_hourly_heatmap()
        task_types = self._analyze_task_types()
        peak_hour_str = self._detect_peak_hour()
        profile = self._build_productivity_profile(peak_hour_str, context_insights, fatigue, distraction, heatmap, task_types)
        best_window = profile["bestFocusWindow"]
        weakest_window = profile["weakestFocusWindow"]
        best_context = profile["bestContext"]
        confidence = profile["profileConfidence"]

        # 5. Evaluate Telemetry & Compute Evidence
        evidence = []
        raw_score = 100
        screen_duration_min = screen_duration // 60

        flag_screen = "NONE"
        flag_switching = "NONE"
        flag_fatigue = "NONE"
        flag_window = "NONE"
        flag_context = "NONE"

        # A. Screen Time
        if screen_duration >= 7200: # 120m
            raw_score -= 40
            evidence.append(f"Continuous screen time exceeds {screen_duration_min} minutes (critical limit)")
            flag_screen = "CRITICAL"
        elif screen_duration >= 5400: # 90m
            raw_score -= 25
            evidence.append(f"Extended continuous screen time: {screen_duration_min} minutes without a break")
            flag_screen = "HIGH"
        elif screen_duration >= 2700: # 45m
            raw_score -= 15
            evidence.append(f"Continuous screen duration reaching {screen_duration_min} minutes")
            flag_screen = "MEDIUM"
        elif screen_duration >= 1800:
            raw_score -= 5
            evidence.append(f"Screen-on duration: {screen_duration_min} minutes")
            flag_screen = "LOW"

        # B. Switching & Non-productive apps
        if num_switches >= 6 or non_prod_count >= 4:
            raw_score -= 25
            evidence.append(f"{num_switches} context switches in recent activity with {non_prod_count} non-productive interruptions")
            flag_switching = "HIGH"
        elif num_switches >= 3 or non_prod_count >= 2:
            raw_score -= 15
            evidence.append(f"Frequent context switching detected ({num_switches} switches, {non_prod_count} non-productive signals)")
            flag_switching = "MEDIUM"
        elif non_prod_count >= 1 or num_switches >= 1:
            raw_score -= 5
            evidence.append(f"Minor context disruption observed ({non_prod_count} non-productive signals)")
            flag_switching = "LOW"

        # C. Fatigue State
        fatigue_score = fatigue.get("score", 0)
        if fatigue_score >= 65:
            raw_score -= 25
            evidence.append(f"Cognitive fatigue is elevated ({fatigue_score}/100, HIGH)")
            flag_fatigue = "HIGH"
        elif fatigue_score >= 35:
            raw_score -= 15
            evidence.append(f"Moderate fatigue accumulation ({fatigue_score}/100)")
            flag_fatigue = "MEDIUM"
        else:
            flag_fatigue = "LOW"

        # D. Time-of-Day Window
        try:
            parts = best_window.split(" - ")
            w_start = int(parts[0].split(":")[0])
            w_end = int(parts[1].split(":")[0])
            is_in_best_window = (w_start <= current_hour < w_end) if w_start < w_end else (current_hour >= w_start or current_hour < w_end)
        except Exception:
            is_in_best_window = (9 <= current_hour < 11)

        is_in_weakest_window = False
        if weakest_window not in ["None detected", "Insufficient Data"]:
            try:
                wparts = weakest_window.split(" - ")
                ww_start = int(wparts[0].split(":")[0])
                ww_end = int(wparts[1].split(":")[0])
                is_in_weakest_window = (ww_start <= current_hour < ww_end) if ww_start < ww_end else (current_hour >= ww_start or current_hour < ww_end)
            except Exception:
                is_in_weakest_window = False

        if is_in_weakest_window:
            raw_score -= 20
            evidence.append(f"Working at {current_hour:02d}:00 in your historically weakest window ({weakest_window})")
            flag_window = "WEAKEST"
        elif not is_in_best_window:
            raw_score -= 10
            evidence.append(f"Working at {current_hour:02d}:00 outside your peak focus window ({best_window})")
            flag_window = "OFF_PEAK"
        else:
            raw_score += 5
            evidence.append(f"Working at {current_hour:02d}:00 inside your peak focus window ({best_window})")
            flag_window = "PEAK"

        # E. Context & Vulnerable Task
        is_vulnerable = task_type.lower() in [v.lower() for v in distraction.get("vulnerableCategories", [])]
        matching_ctx = next((c for c in context_insights if c["context"].lower() == context_loc.lower()), None)

        if is_vulnerable and (matching_ctx and matching_ctx["status"] == "Suboptimal"):
            raw_score -= 20
            evidence.append(f"'{task_type.capitalize()}' is highly vulnerable in '{context_loc}' ({matching_ctx['completionRate']}% completion)")
            flag_context = "VULNERABLE_SUBOPTIMAL"
        elif matching_ctx and matching_ctx["status"] == "Suboptimal":
            raw_score -= 10
            evidence.append(f"Environment '{context_loc}' has historically low completion ({matching_ctx['completionRate']}%)")
            flag_context = "SUBOPTIMAL"
        elif matching_ctx and matching_ctx["status"] == "Optimal":
            raw_score += 5
            evidence.append(f"Environment '{context_loc}' is optimal ({matching_ctx['completionRate']}% completion)")
            flag_context = "OPTIMAL"
        else:
            flag_context = "NEUTRAL"

        # 6. Score & State Classification
        score = max(0, min(100, raw_score))

        if score >= 80 and flag_screen in ["NONE", "LOW"] and flag_fatigue == "LOW" and flag_switching in ["NONE", "LOW"]:
            state = "OPTIMAL"
            urgency = "LOW"
            trigger = "SUSTAINED_OPTIMAL_FLOW"
        elif score >= 60 and flag_screen != "CRITICAL" and flag_switching != "HIGH":
            state = "NORMAL"
            urgency = "LOW"
            trigger = "NORMAL_PACING"
        elif score >= 35 or flag_screen == "HIGH" or flag_switching == "HIGH" or flag_fatigue == "HIGH":
            state = "AT_RISK"
            urgency = "HIGH" if (score < 45 or flag_screen == "HIGH") else "MEDIUM"
            if flag_switching == "HIGH":
                trigger = "RAPID_CONTEXT_SWITCHING"
            elif flag_screen in ["HIGH", "CRITICAL"]:
                trigger = "EXCESSIVE_SCREEN_TIME"
            elif flag_fatigue == "HIGH":
                trigger = "HIGH_FATIGUE_STRAIN"
            elif flag_context == "VULNERABLE_SUBOPTIMAL":
                trigger = "VULNERABLE_TASK_CONTEXT"
            elif flag_window in ["WEAKEST", "OFF_PEAK"]:
                trigger = "OFF_PEAK_FRICTION"
            else:
                trigger = "PRODUCTIVITY_DROP"
        else:
            state = "RECOVERY"
            urgency = "CRITICAL" if (flag_screen == "CRITICAL" or score < 25) else "HIGH"
            if flag_screen == "CRITICAL":
                trigger = "EXCESSIVE_SCREEN_TIME"
            elif flag_fatigue == "HIGH":
                trigger = "HIGH_FATIGUE_STRAIN"
            elif flag_switching == "HIGH":
                trigger = "RAPID_CONTEXT_SWITCHING"
            else:
                trigger = "SEVERE_COGNITIVE_BURNOUT"

        # Sanitize all evidence strings
        evidence = [_sanitize_text(e) for e in evidence]

        # 7. Deterministic Fallback Coaching Message
        if state == "RECOVERY":
            if trigger == "EXCESSIVE_SCREEN_TIME":
                fallback_message = f"Immediate recovery needed: You have been on-screen for {screen_duration_min} minutes. Step away from all screens for a 15-minute physical reset."
            elif trigger == "HIGH_FATIGUE_STRAIN":
                fallback_message = f"Severe fatigue detected ({fatigue_score}/100). Step away from {task_type} for a 15-minute recovery walk before resuming."
            else:
                fallback_message = f"Cognitive energy depleted (score: {score}/100). Stop active tasks and take an immediate 15-minute recovery break."
        elif state == "AT_RISK":
            if trigger == "RAPID_CONTEXT_SWITCHING":
                fallback_message = "Take a 10-minute break, then start a 25-minute focused session."
            elif trigger == "EXCESSIVE_SCREEN_TIME":
                fallback_message = f"Take a 10-minute eye-rest break. Continuous screen time is at {screen_duration_min} minutes."
            elif trigger == "VULNERABLE_TASK_CONTEXT":
                fallback_message = f"Relocate your {task_type} session from {context_loc} to {best_context}, or shift to a structured planning task."
            elif trigger == "OFF_PEAK_FRICTION":
                fallback_message = f"Working outside your peak window. Cap this {task_type} block at 25 minutes and reschedule deep work to {best_window}."
            elif trigger == "HIGH_FATIGUE_STRAIN":
                fallback_message = f"Fatigue is rising ({fatigue_score}/100). Take a 10-minute recovery break to reset your focus."
            else:
                fallback_message = f"Focus slipping (score: {score}/100). Take a short 5-minute breather and mute non-essential notifications."
        elif state == "NORMAL":
            fallback_message = f"Pacing is steady (score: {score}/100). Continue your current {task_type} block in {context_loc}."
        else:
            fallback_message = f"Optimal flow state achieved (score: {score}/100). Maintain sustained focus in {context_loc}."

        # 8. Anti-Spam Suppression Rules
        is_suppressed = False
        suppression_reason = None

        # Severity threshold: suppress interventions if NORMAL or OPTIMAL
        if state in ["OPTIMAL", "NORMAL"]:
            is_suppressed = True
            suppression_reason = "SEVERITY_BELOW_THRESHOLD"

        # Confidence threshold: suppress pattern-based interventions on cold start / sparse data
        elif confidence == "LOW" and trigger in ["OFF_PEAK_FRICTION", "VULNERABLE_TASK_CONTEXT", "PRODUCTIVITY_DROP"]:
            is_suppressed = True
            suppression_reason = "LOW_CONFIDENCE"

        # Cooldown period: check if recent intervention was triggered within cooldown window
        elif last_intervention_time is not None and current_time is not None:
            elapsed_sec = (current_time - last_intervention_time) / 1000.0
            if elapsed_sec < cooldown_seconds and urgency != "CRITICAL":
                is_suppressed = True
                suppression_reason = "COOLDOWN_ACTIVE"

        # Duplicate-trigger suppression
        if not is_suppressed and last_trigger is not None and trigger == last_trigger:
            if last_intervention_time is not None and current_time is not None:
                elapsed_sec = (current_time - last_intervention_time) / 1000.0
                if elapsed_sec < (cooldown_seconds * 2) and urgency != "CRITICAL":
                    is_suppressed = True
                    suppression_reason = "DUPLICATE_TRIGGER"

        # 9. Final Intervention Message (Default Fallback)
        intervention = None if is_suppressed else fallback_message

        # 10. Canonical Minimal Structured Evidence Contract for Local AI Model
        structured_evidence = {
            "currentTask": task_type,
            "productivityScore": score,
            "fatigue": fatigue_score,
            "fatigueLevel": fatigue.get("level", "LOW"),
            "distraction": distraction.get("score", 0),
            "contextSwitches": num_switches,
            "context": context_loc,
            "peakWindow": best_window,
            "isInPeakWindow": (flag_window == "PEAK"),
            "prediction": score,
            "riskLevel": "HIGH" if score < 45 else ("MEDIUM" if score < 70 else "LOW"),
            "confidence": confidence,
            "detectedTrigger": trigger,
            "facts": [_sanitize_text(f) for f in evidence]
        }


        local_model_prompt = (
            f"System: You are an on-device personal productivity coach. Generate a 1-sentence supportive coaching intervention.\n"
            f"Context: State={state}, Score={score}/100, Trigger={trigger}, Urgency={urgency}, Confidence={confidence}.\n"
            f"Evidence: {'; '.join(structured_evidence['facts'][:3])}.\n"
            f"Coach:"
        )

        # 11. Local AI Model Integration (Deterministic Fallback or Local SLM)
        coach_response = None
        model_provider = None

        if model is not None:
            if is_suppressed:
                # Anti-spam throttling bypass: skip model inference to preserve device battery and CPU/NPU cycles
                model_provider = f"{getattr(model, 'model_name', 'local-slm')} (bypassed: intervention suppressed)"
            else:
                try:
                    # Model accepts either AIModelInput or structured evidence dict
                    if hasattr(model, "generate_coaching"):
                        resp = model.generate_coaching(structured_evidence)
                    elif hasattr(model, "generateCoaching"):
                        resp = model.generateCoaching(structured_evidence)
                    elif callable(model):
                        resp = model(structured_evidence)
                    else:
                        resp = None

                    if resp is not None:
                        # Extract coaching message from AIModelResponse or dict
                        if hasattr(resp, "message") and resp.message:
                            msg = str(resp.message).strip()
                        elif isinstance(resp, dict) and resp.get("message"):
                            msg = str(resp.get("message")).strip()
                        elif isinstance(resp, str) and resp.strip():
                            msg = resp.strip()
                        else:
                            msg = ""

                        if msg:
                            intervention = msg
                            coach_response = resp.to_dict() if hasattr(resp, "to_dict") else (resp if isinstance(resp, dict) else {"message": msg})
                            model_provider = getattr(resp, "provider", getattr(model, "model_name", "local-slm"))
                        else:
                            # Fallback if empty message
                            intervention = fallback_message
                            model_provider = f"{getattr(model, 'model_name', 'local-slm')} (empty output fallback)"
                except Exception as e:
                    # Graceful deterministic fallback on model error/timeout
                    intervention = fallback_message
                    coach_response = {"error": str(e), "isFallback": True}
                    model_provider = f"{getattr(model, 'model_name', 'local-slm')} (fallback on error: {str(e)[:50]})"

        result = {
            "state": state,
            "score": score,
            "trigger": trigger,
            "evidence": evidence,
            "intervention": intervention,
            "urgency": urgency,
            "confidence": confidence,
            "isInterventionSuppressed": is_suppressed,
            "suppressionReason": suppression_reason,
            "structuredEvidence": structured_evidence,
            "localModelPrompt": local_model_prompt,
            "fallbackMessage": fallback_message
        }
        if model is not None:
            result["coachResponse"] = coach_response
            result["modelProvider"] = model_provider

        return result

    async def evaluate_and_coach_async(
        self,
        task_type: str = "coding",
        current_hour: Optional[int] = None,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        screen_duration: int = 0,
        recent_activity: Optional[Union[List[Any], Dict[str, Any]]] = None,
        last_intervention_time: Optional[int] = None,
        last_trigger: Optional[str] = None,
        current_time: Optional[int] = None,
        cooldown_seconds: int = 900,
        model: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Asynchronous, non-blocking evaluation with Local AI Model integration.
        Offloads computation to a background thread so the caller's thread / event loop
        never blocks or freezes during SLM inference.
        """
        import asyncio
        return await asyncio.to_thread(
            self.evaluate_current_state,
            task_type=task_type,
            current_hour=current_hour,
            context=context,
            screen_duration=screen_duration,
            recent_activity=recent_activity,
            last_intervention_time=last_intervention_time,
            last_trigger=last_trigger,
            current_time=current_time,
            cooldown_seconds=cooldown_seconds,
            model=model
        )

    evaluate_and_coach = evaluate_current_state
    evaluateAndCoach = evaluate_current_state
    evaluateAndCoachAsync = evaluate_and_coach_async
    evaluateCurrentState = evaluate_current_state

def evaluate_current_state(
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Module-level convenience wrapper for evaluate_current_state.
    Supports flexible invocations:
      evaluate_current_state(tasks, context_signals, task_type, current_hour, ...)
      evaluate_current_state(task_type, current_hour, context, screen_duration, ...)
    """
    if len(args) >= 1 and isinstance(args[0], list):
        tasks = args[0]
        signals = args[1] if len(args) >= 2 and isinstance(args[1], list) else None
        remaining_args = args[2:]
        engine = InsightEngine(tasks, signals)
        return engine.evaluate_current_state(*remaining_args, **kwargs)
    else:
        tasks = kwargs.pop("tasks", [])
        signals = kwargs.pop("context_signals", [])
        engine = InsightEngine(tasks, signals)
        return engine.evaluate_current_state(*args, **kwargs)

evaluateCurrentState = evaluate_current_state
evaluate_and_coach = evaluate_current_state
evaluateAndCoach = evaluate_current_state

async def evaluate_and_coach_async(*args, **kwargs) -> Dict[str, Any]:
    """Module-level asynchronous wrapper for evaluate_and_coach."""
    import asyncio
    return await asyncio.to_thread(evaluate_current_state, *args, **kwargs)

evaluateAndCoachAsync = evaluate_and_coach_async

def predict_task_readiness(
    tasks: List[Dict[str, Any]],
    context_signals: Optional[List[Dict[str, Any]]] = None,
    task_type: str = "coding",
    current_hour: Optional[int] = None,
    current_context: Optional[str] = None,
    recent_screen_duration: Optional[int] = None
) -> Dict[str, Any]:
    """Module-level convenience wrapper for predict_task_readiness."""
    engine = InsightEngine(tasks, context_signals)
    return engine.predict_task_readiness(
        task_type=task_type,
        current_hour=current_hour,
        current_context=current_context,
        recent_screen_duration=recent_screen_duration
    )

def update_user_model(
    previous_model: Optional[Dict[str, Any]],
    new_task: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Continuous Personalization / Online Learning.
    Updates the on-device user model and productivity profile after each task
    outcome (completion or abandonment) with exponential recency weighting and
    prediction calibration tracking.
    """
    # 0. Privacy sanitization of incoming task and context
    sanitized_task = dict(new_task)
    if "type" in sanitized_task:
        sanitized_task["type"] = _sanitize_task_type(sanitized_task["type"])
    if "title" in sanitized_task:
        sanitized_task["title"] = _sanitize_text(sanitized_task["title"])
    if "location" in sanitized_task:
        sanitized_task["location"] = _sanitize_context(sanitized_task["location"])
    new_task = sanitized_task

    if context and isinstance(context, dict):
        sanitized_context = dict(context)
        if "location" in sanitized_context:
            sanitized_context["location"] = _sanitize_context(sanitized_context["location"])
        context = sanitized_context

    # 1. Extract previous state
    if previous_model is None or not isinstance(previous_model, dict):

        prev_tasks = []
        prev_signals = []
        prev_calib = {
            "totalEvaluations": 0,
            "accuratePredictions": 0,
            "accuracyRate": 0.0,
            "meanCalibrationError": 0.0,
            "lastPredictionOutcome": "NONE",
            "lastPredictedScore": None,
            "lastActualOutcome": "NONE"
        }
    else:
        prev_tasks = list(previous_model.get("tasks", []))
        prev_signals = list(previous_model.get("contextSignals", []))
        prev_calib = dict(previous_model.get("predictionCalibration", {
            "totalEvaluations": 0,
            "accuratePredictions": 0,
            "accuracyRate": 0.0,
            "meanCalibrationError": 0.0,
            "lastPredictionOutcome": "NONE",
            "lastPredictedScore": None,
            "lastActualOutcome": "NONE"
        }))

    # 2. Prediction vs Actual Outcome Tracking
    pred_score = None
    if "predictedScore" in new_task and new_task["predictedScore"] is not None:
        pred_score = int(new_task["predictedScore"])
    elif prev_tasks:
        prev_engine = InsightEngine(prev_tasks, prev_signals)
        t_type = new_task.get("type", "coding")
        t_hour = datetime.fromtimestamp(new_task["createdAt"] / 1000).hour if "createdAt" in new_task else datetime.now().hour
        t_loc = new_task.get("location") or (context.get("location") if context else "Home Office")
        t_screen = context.get("screenOnDuration", 0) if context else 0
        pred_res = prev_engine.predict_task_readiness(t_type, t_hour, t_loc, t_screen)
        pred_score = pred_res["predictedScore"]

    is_completed = (new_task.get("completedAt") is not None) and (new_task.get("status") != "abandoned")
    actual_score = 100 if is_completed else 0
    actual_outcome_str = "COMPLETED" if is_completed else "ABANDONED"

    if pred_score is not None:
        was_accurate = (pred_score >= 50 and is_completed) or (pred_score < 50 and not is_completed)
        outcome_str = "ACCURATE" if was_accurate else "INACCURATE"
        error = abs(pred_score - actual_score)

        tot_eval = prev_calib.get("totalEvaluations", 0) + 1
        acc_count = prev_calib.get("accuratePredictions", 0) + (1 if was_accurate else 0)
        acc_rate = round((acc_count / tot_eval) * 100.0, 1)
        prev_mean_err = prev_calib.get("meanCalibrationError", 0.0)
        new_mean_err = round(((prev_mean_err * (tot_eval - 1)) + error) / tot_eval, 1)

        new_calib = {
            "totalEvaluations": tot_eval,
            "accuratePredictions": acc_count,
            "accuracyRate": acc_rate,
            "meanCalibrationError": new_mean_err,
            "lastPredictionOutcome": outcome_str,
            "lastPredictedScore": pred_score,
            "lastActualOutcome": actual_outcome_str
        }
    else:
        new_calib = dict(prev_calib)
        new_calib["lastActualOutcome"] = actual_outcome_str

    # 3. Update task list and context signals
    updated_tasks = prev_tasks + [new_task]
    updated_signals = prev_signals + ([context] if context else [])

    # 4. Recompute profile with recency weighting
    engine = InsightEngine(updated_tasks, updated_signals, prediction_calibration=new_calib)
    insights = engine.analyze()
    profile = insights["productivityProfile"]

    # 5. Build and return comprehensive updated user model
    user_model = {
        "productivityProfile": profile,
        "predictionCalibration": new_calib,
        "adaptiveRecommendations": insights["adaptiveRecommendations"],
        "tasks": updated_tasks,
        "contextSignals": updated_signals,
        "taskCount": len(updated_tasks),
        "lastUpdated": int(time.time() * 1000),
        # Direct shortcuts for profile access
        "bestFocusWindow": profile["bestFocusWindow"],
        "bestTaskTypes": profile["bestTaskTypes"],
        "bestContext": profile["bestContext"],
        "weakestFocusWindow": profile["weakestFocusWindow"],
        "peakProductivityScore": profile["peakProductivityScore"],
        "averageCompletionRate": profile["averageCompletionRate"],
        "profileConfidence": profile["profileConfidence"],
        "taskTypeAnalysis": profile["taskTypeAnalysis"],
        "fatiguePattern": profile["fatiguePattern"],
        "distractionPattern": profile["distractionPattern"],
        "productivityScore": insights["productivityScore"],
        "confidenceLevel": insights["confidenceLevel"],
        "recommendation": insights["recommendation"],
        "fatigueLevel": insights["fatigueLevel"],
        "fatigueScore": insights["fatigueScore"],
        "explanation": insights["explanation"],
        "hourlyHeatmap": insights["hourlyHeatmap"],
        "contextInsights": insights["contextInsights"],
        "distractionSensitivity": insights["distractionSensitivity"]
    }
    return user_model

updateUserModel = update_user_model

if __name__ == "__main__":
    import json, os
    sample_file = os.path.join(os.path.dirname(__file__), "sample_data.json")
    signals_file = os.path.join(os.path.dirname(__file__), "sample_context_signals.json")

    tasks = []
    signals = []
    if os.path.exists(sample_file):
        with open(sample_file) as f:
            tasks = json.load(f)
    if os.path.exists(signals_file):
        with open(signals_file) as f:
            signals = json.load(f)

    engine = InsightEngine(tasks, signals)
    res = engine.analyze()
    print(json.dumps(res, indent=2))
