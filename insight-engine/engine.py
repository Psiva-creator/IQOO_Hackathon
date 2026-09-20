"""
On-Device Habit & Productivity Insight Engine (Enhanced)
Analyzes task completions, timing histograms, failure rates, and environmental context
to generate 100% on-device personalized productivity intelligence.
"""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any

class InsightEngine:
    def __init__(self, tasks: List[Dict[str, Any]]):
        self.tasks = tasks

    def analyze(self) -> Dict[str, Any]:
        if not self.tasks:
            return {
                "peakHour": "Insufficient Data",
                "procrastinationTrigger": "No activity patterns detected yet",
                "bestContext": "Track at least 5 tasks to calibrate",
                "recommendation": "Start tracking daily focus blocks to activate personalized insights.",
                "productivityScore": 0,
                "confidenceLevel": "Calibrating",
                "hourlyHeatmap": {str(h): 0 for h in range(24)}
            }

        peak_hour = self._detect_peak_hour()
        procrastination = self._detect_procrastination_trigger()
        best_context = self._detect_best_context()
        recommendation = self._generate_recommendation(procrastination)
        score = self._calculate_productivity_score()
        confidence = self._calculate_confidence()
        heatmap = self._generate_hourly_heatmap()

        return {
            "peakHour": peak_hour,
            "procrastinationTrigger": procrastination,
            "bestContext": best_context,
            "recommendation": recommendation,
            "productivityScore": score,
            "confidenceLevel": confidence,
            "hourlyHeatmap": heatmap
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

    def _detect_best_context(self) -> str:
        loc_stats = defaultdict(lambda: {"total": 0, "completed": 0})
        for task in self.tasks:
            loc = task.get("location", "Home Office")
            loc_stats[loc]["total"] += 1
            if task.get("completedAt"):
                loc_stats[loc]["completed"] += 1

        best_loc = "Home Office"
        best_rate = 0.0
        for loc, stats in loc_stats.items():
            rate = stats["completed"] / stats["total"] if stats["total"] > 0 else 0
            if rate > best_rate and stats["total"] >= 2:
                best_rate = rate
                best_loc = loc

        return f"{best_loc} (Consistent {int(best_rate*100)}% session completion)"

    def _generate_recommendation(self, procrastination: str) -> str:
        if "Writing" in procrastination or "writing" in procrastination:
            return "Shift cognitive-heavy writing sessions to your morning peak block (09:00 - 11:00 AM) to avoid afternoon drop-off."
        elif "Coding" in procrastination or "coding" in procrastination:
            return "Break larger coding sessions into 30-minute focus sprints."
        return "Schedule high-priority deep work in your verified peak focus window."

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
