"""
On-Device Habit & Productivity Insight Engine
Context-Aware Productivity, Fatigue, and Distraction Detection.
Pure statistical and heuristic analytics running 100% on-device.
"""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

class InsightEngine:
    def __init__(self, tasks: List[Dict[str, Any]], context_signals: Optional[List[Dict[str, Any]]] = None):
        self.tasks = tasks or []
        self.context_signals = context_signals or []

    def analyze(self) -> Dict[str, Any]:
        if not self.tasks:
            return {
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
                }
            }

        peak_hour = self._detect_peak_hour()
        procrastination = self._detect_procrastination_trigger()
        context_insights = self._analyze_contexts()
        best_context_str = self._format_best_context(context_insights)
        fatigue = self._detect_fatigue()
        distraction = self._detect_distraction_sensitivity()
        score = self._calculate_productivity_score()
        confidence = self._calculate_confidence()
        heatmap = self._generate_hourly_heatmap()
        recommendation = self._generate_smart_recommendation(peak_hour, procrastination, context_insights, fatigue, distraction)

        return {
            "peakHour": peak_hour,
            "procrastinationTrigger": procrastination,
            "bestContext": best_context_str,
            "recommendation": recommendation,
            "productivityScore": score,
            "confidenceLevel": confidence,
            "hourlyHeatmap": heatmap,
            "fatigueLevel": fatigue["level"],
            "fatigueScore": fatigue["score"],
            "explanation": fatigue["explanation"],
            "contextInsights": context_insights,
            "distractionSensitivity": distraction
        }

    def _detect_peak_hour(self) -> str:
        hourly_completions = defaultdict(int)
        for task in self.tasks:
            if task.get("completedAt"):
                dt = datetime.fromtimestamp(task["createdAt"] / 1000)
                hourly_completions[dt.hour] += 1

        if not hourly_completions:
            return "09:00 - 11:00 AM"

        best_hour = max(hourly_completions.items(), key=lambda x: x[1])[0]
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
        context_map = defaultdict(lambda: {"total": 0, "completed": 0, "durations": []})
        for task in self.tasks:
            loc = task.get("location") or "Home Office"
            context_map[loc]["total"] += 1
            dur = task.get("duration", 0)
            context_map[loc]["durations"].append(dur)
            if task.get("completedAt"):
                context_map[loc]["completed"] += 1

        results = []
        for loc, stats in context_map.items():
            total = stats["total"]
            completed = stats["completed"]
            rate = round((completed / total) * 100, 1) if total > 0 else 0.0
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
        # Prefer context with at least 2 tasks
        best = next((c for c in context_insights if c["totalTasks"] >= 2), context_insights[0])
        return f"{best['context']} ({best['completionRate']}% completion across {best['totalTasks']} sessions)"

    def _detect_fatigue(self) -> Dict[str, Any]:
        # 1. Screen-On Duration Strain (0-30 pts)
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
            # Infer from task continuous load
            avg_task_dur = sum(t.get("duration", 0) for t in self.tasks) / len(self.tasks) if self.tasks else 0
            if avg_task_dur >= 3600:
                screen_pts = 20
            elif avg_task_dur >= 2400:
                screen_pts = 10
            elif avg_task_dur >= 1200:
                screen_pts = 5

        # 2. Declining Completion Rate: Morning vs Afternoon (0-30 pts)
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

        # 3. Session Duration Degradation (0-20 pts)
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

        # 4. Context/Task Switching & Distraction Intrusion (0-20 pts)
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
            # Check rapid task switching between different types (<45 mins)
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

        # Construct Explainable Summary
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

        # Distraction score calculation
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

    def _generate_smart_recommendation(
        self,
        peak_hour: str,
        procrastination: str,
        context_insights: List[Dict[str, Any]],
        fatigue: Dict[str, Any],
        distraction: Dict[str, Any]
    ) -> str:
        # Identify best completed task type
        type_rates = {}
        for task in self.tasks:
            t_type = task.get("type", "other")
            if t_type not in type_rates:
                type_rates[t_type] = {"total": 0, "completed": 0}
            type_rates[t_type]["total"] += 1
            if task.get("completedAt"):
                type_rates[t_type]["completed"] += 1

        priority_rank = {"coding": 0, "writing": 1, "planning": 2, "reading": 3, "meeting": 4, "exercise": 5, "other": 6}
        best_type = "coding"
        best_type_rate = -1
        for t, s in type_rates.items():
            if s["total"] >= 2:
                r = int((s["completed"] / s["total"]) * 100)
                if r > best_type_rate or (r == best_type_rate and priority_rank.get(t, 99) < priority_rank.get(best_type, 99)):
                    best_type_rate = r
                    best_type = t

        # Identify context metrics
        best_ctx = context_insights[0] if context_insights else {"context": "Home Office", "completionRate": 85.0}
        worst_ctx = context_insights[-1] if len(context_insights) > 1 else None

        parts = []
        # 1. Peak hour and strength
        peak_clean = peak_hour.split("(")[0].strip()
        parts.append(f"Your {best_type} completion rate peaks between {peak_clean} ({best_type_rate}% completion in {best_ctx['context']}).")

        # 2. Context & Procrastination finding
        if worst_ctx and worst_ctx["completionRate"] < best_ctx["completionRate"]:
            vulnerable_str = ", ".join(distraction["vulnerableCategories"]) if distraction["vulnerableCategories"] else "complex"
            parts.append(f"In contrast, {vulnerable_str} sessions drop to {worst_ctx['completionRate']}% completion in {worst_ctx['context']}.")

        # 3. Fatigue & Actionable Coaching
        if fatigue["score"] >= 65:
            parts.append(f"High afternoon fatigue (score: {fatigue['score']}/100) significantly degrades focus after extended screen sessions.")
            parts.append(f"Consider scheduling difficult {vulnerable_str if worst_ctx else best_type} tasks before 11:00 AM in {best_ctx['context']}, and limit continuous screen blocks to 45 minutes.")
        elif fatigue["score"] >= 35:
            parts.append(f"Moderate fatigue (score: {fatigue['score']}/100) sets in during late afternoon. Schedule high-priority deep work in {best_ctx['context']} during your morning peak.")
        else:
            parts.append(f"Maintain your consistent cadence by protecting your {peak_clean} block for high-priority initiatives.")

        return " ".join(parts)

    def _calculate_productivity_score(self) -> int:
        total = len(self.tasks)
        if total == 0:
            return 0
        completed = sum(1 for t in self.tasks if t.get("completedAt"))
        return max(0, min(100, int((completed / total) * 100)))

    def _calculate_confidence(self) -> str:
        total = len(self.tasks)
        if total < 5:
            return "Calibrating"
        elif total < 20:
            return "Medium"
        return "High"

    def _generate_hourly_heatmap(self) -> Dict[str, int]:
        heatmap = {}
        hour_buckets = defaultdict(lambda: {"attempts": 0, "completed": 0})
        for task in self.tasks:
            dt = datetime.fromtimestamp(task["createdAt"] / 1000)
            h = dt.hour
            hour_buckets[h]["attempts"] += 1
            if task.get("completedAt"):
                hour_buckets[h]["completed"] += 1

        for h in range(24):
            b = hour_buckets[h]
            if b["attempts"] == 0:
                heatmap[str(h)] = 0
            else:
                heatmap[str(h)] = int((b["completed"] / b["attempts"]) * 100)
        return heatmap

if __name__ == "__main__":
    import json, os
    sample_file = os.path.join(os.path.dirname(__file__), "sample_data.json")
    if os.path.exists(sample_file):
        with open(sample_file) as f:
            tasks = json.load(f)
    else:
        from synthetic_generator import generate_synthetic_tasks
        tasks = generate_synthetic_tasks(days=5)

    engine = InsightEngine(tasks)
    print(json.dumps(engine.analyze(), indent=2))
