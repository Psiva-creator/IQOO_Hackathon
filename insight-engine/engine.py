"""
On-Device Habit & Productivity Insight Engine
Context-Aware Productivity, Fatigue, Personal Productivity Profile & Adaptive Recommendations.
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
        total_tasks = len(self.tasks)
        confidence = self._calculate_confidence()

        if total_tasks == 0:
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
                ]
            }

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

        return {
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
            "adaptiveRecommendations": adaptive_recs
        }

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
        tasks_by_type = defaultdict(list)
        for task in self.tasks:
            t_type = task.get("type", "other")
            tasks_by_type[t_type].append(task)

        analysis_list = []
        for t_type, type_tasks in tasks_by_type.items():
            total = len(type_tasks)
            completed = sum(1 for t in type_tasks if t.get("completedAt"))
            failed = total - completed
            completion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0
            abandonment_rate = round((failed / total) * 100, 1) if total > 0 else 0.0
            avg_dur = round(sum(t.get("duration", 0) for t in type_tasks) / total, 1) if total > 0 else 0.0
            prod_score = int(round(completion_rate * 0.7 + min(1.0, avg_dur / 3600.0) * 30))
            prod_score = max(0, min(100, prod_score))

            # Detect strongest time window for this specific task type
            strongest_window = "Insufficient data"
            if total >= 2:
                hourly_success = defaultdict(lambda: {"attempts": 0, "completed": 0})
                for t in type_tasks:
                    h = datetime.fromtimestamp(t["createdAt"] / 1000).hour
                    hourly_success[h]["attempts"] += 1
                    if t.get("completedAt"):
                        hourly_success[h]["completed"] += 1

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
        best_ctx_name = context_insights[0]["context"] if context_insights else "Home Office"

        # 4. Weakest Focus Window
        weakest_window = self._detect_weakest_focus_window()

        # 5. Peak Productivity Score & Average Completion Rate
        peak_score = max(heatmap.values(), default=0)
        completed_count = sum(1 for t in self.tasks if t.get("completedAt"))
        avg_completion = round((completed_count / total) * 100, 1)

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
        completed = sum(1 for t in self.tasks if t.get("completedAt"))
        return max(0, min(100, int((completed / total) * 100)))

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
