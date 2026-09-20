# 🧠 Member B — Folder: `/insight-engine`

**Owner:** Member B  
**Domain:** On-Device Analytics & Behavioral Intelligence Layer (Context-Aware Productivity, Fatigue & Adaptive Profiling Engine)

---

## 🎯 Architecture Overview

The `insight-engine` is a **100% on-device, zero-external-dependency** intelligence layer implemented in both **Python** (`engine.py` as reference) and **Kotlin** (`InsightEngine.kt` for direct Android integration in `app-ui`).

It analyzes historical task records alongside real-time device context signals to discover subconscious productivity habits, compute cognitive fatigue, identify distraction vulnerabilities, generate a **Personal Productivity Profile**, and synthesize **Ranked Adaptive Recommendations**.

---

## 👤 Personal Productivity Profile

The Personal Productivity Profile aggregates historical task and context signals into a unified behavioral blueprint:

### 1. Signals Used
* **Task Telemetry:** Start time (`createdAt`), completion state (`completedAt`), duration, task category (`coding`, `writing`, `meeting`, `planning`, etc.), location, and priority.
* **Device Context:** Active foreground app category (`Productivity`, `Social`, `Entertainment`, `Communication`), continuous `screenOnDuration`, and location switches.

### 2. Profile Components & Calculation Logic

| Field | Source / Calculation Method |
|---|---|
| `bestFocusWindow` | Sliding 2-hour window across 24h with the highest completed session volume and completion rate. |
| `bestTaskTypes` | Task categories with $\ge 2$ recorded sessions and $\ge 70\%$ completion rate, ordered by completion rate. |
| `bestContext` | Environment context ($c$) yielding the highest completion rate (minimum 2 sessions). |
| `weakestFocusWindow` | 2-hour window exhibiting the highest abandonment/failure rate ($\ge 30\%$ failure). |
| `peakProductivityScore` | Maximum focus completion efficiency ($0 - 100$) attained during peak hourly intervals. |
| `averageCompletionRate` | $\frac{\text{Total Completed Tasks}}{\text{Total Attempted Tasks}} \times 100$ |
| `fatiguePattern` | Explains when and why cognitive fatigue sets in (derived from duration degradation and screen strain). |
| `distractionPattern` | Identifies specific task categories and context combinations vulnerable to app switching. |
| `profileConfidence` | Stratified strictly by sample volume: `LOW` ($< 5$ sessions), `MEDIUM` ($5 - 15$), `HIGH` ($> 15$). |

### 3. Task-Type × Time Analysis (`taskTypeAnalysis`)
For each distinct task type, the engine computes:
* **Strongest Window:** 2-hour interval where this specific task type achieves highest completion.
* **Completion & Abandonment Rates:** $\frac{\text{Completed}}{\text{Total}}$ vs $\frac{\text{Failed}}{\text{Total}}$.
* **Average Duration:** Mean focus session length in seconds.
* **Productivity Score:** Normalized composite: $0.7 \times \text{CompletionRate} + 0.3 \times \min(1.0, \frac{\text{Duration}}{3600\text{s}}) \times 100$.

---

## 🔬 Cognitive Fatigue & Context Correlation

### 1. Fatigue Detection Formula ($0 \le S_{\text{fatigue}} \le 100$)
Calculated from four independent degradation factors:
1. **Screen & Continuous Duration Strain ($0 - 30$ pts):** Continuous `screenOnDuration` $\ge 45\text{m}$ ($+10$), $\ge 75\text{m}$ ($+20$), $\ge 120\text{m}$ ($+30$).
2. **Declining Completion Rate ($0 - 30$ pts):** Morning ($< 13:00$) vs afternoon ($\ge 13:00$) drop ($\ge 10\%: +10$, $\ge 20\%: +20$, $\ge 40\%: +30$).
3. **Session Duration Shrinkage ($0 - 20$ pts):** Afternoon session duration cut by $\ge 25\%$ ($+10$), $\ge 50\%$ ($+20$).
4. **Task & Context Switching ($0 - 20$ pts):** Non-productive signal ratio $\ge 15\%$ ($+10$), $\ge 35\%$ ($+20$) or frequent type switches.

**Classification:**
* **`HIGH`**: $S_{\text{fatigue}} \ge 65$
* **`MEDIUM`**: $35 \le S_{\text{fatigue}} < 65$
* **`LOW`**: $S_{\text{fatigue}} < 35$

---

## 🧭 Ranked Adaptive Recommendations (`adaptiveRecommendations`)

Rather than static templates, recommendations are generated and prioritized dynamically based on the user's computed profile:

1. **Candidate Formulation:**
   * **Peak Focus Window Protection (Weight: 95):** Directs the user's strongest task type to their optimal temporal and environmental block.
   * **Fatigue & Screen Pacing (Weight: 70–90):** Prescribes time-capped sessions and active breaks when fatigue score $\ge 35$.
   * **Context Optimization (Weight: 80):** Recommends shifting vulnerable tasks when an environment demonstrates $\ge 25\%$ higher completion than another.
   * **Distraction Barrier (Weight: 75):** Recommends Do Not Disturb rules targeting the specific app categories that intrude on work sessions.
2. **Priority Ranking:** Candidates are sorted by internal weight and returned as the **top 1–3 actionable interventions**, tagged with `HIGH`, `MEDIUM`, or `LOW` priority and impact.
3. **Backward Compatibility:** The advice and reason from the top-ranked recommendation populate the root `"recommendation"` field.

---

## 📥 Input & Output Example

### Output: Complete Synthesized Contract
```json
{
  "peakHour": "09:00 - 11:00 (Peak focus completion)",
  "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM (100% abandon rate)",
  "bestContext": "Home Office (100.0% completion across 21 sessions)",
  "recommendation": "Schedule demanding coding tasks between 09:00 - 11:00 in Home Office. Your coding completion rate reaches 100% in Home Office during this window.",
  "productivityScore": 66,
  "confidenceLevel": "High",
  "hourlyHeatmap": { "9": 100, "10": 100, "13": 100, "15": 0, "18": 100, ... },
  "fatigueLevel": "HIGH",
  "fatigueScore": 90,
  "explanation": "Fatigue is HIGH (score: 90/100). Completion rate drops by 50% in the afternoon; focus sessions shorten by 75%; continuous screen time exceeds 136 minutes.",
  "contextInsights": [
    { "context": "Home Office", "completionRate": 100.0, "totalTasks": 21, "completedTasks": 21, "status": "Optimal" },
    { "context": "Cafe", "completionRate": 0.0, "totalTasks": 14, "completedTasks": 0, "status": "Suboptimal" }
  ],
  "distractionSensitivity": {
    "level": "HIGH",
    "score": 60,
    "vulnerableCategories": ["writing"],
    "triggerAppCategories": ["Entertainment", "Social"],
    "summary": "HIGH sensitivity: Writing tasks show high abandonment when Entertainment, Social apps are accessed."
  },
  "productivityProfile": {
    "bestFocusWindow": "09:00 - 11:00",
    "bestTaskTypes": ["coding", "meeting", "planning"],
    "bestContext": "Home Office",
    "weakestFocusWindow": "14:00 - 16:00",
    "peakProductivityScore": 100,
    "averageCompletionRate": 66.7,
    "fatiguePattern": "Severe fatigue peaks after 14:00 (score: 90/100) after extended screen sessions.",
    "distractionPattern": "High vulnerability on writing when Entertainment, Social apps are accessed.",
    "profileConfidence": "HIGH",
    "taskTypeAnalysis": [
      {
        "taskType": "coding",
        "strongestWindow": "09:00 - 11:00",
        "completionRate": 100.0,
        "abandonmentRate": 0.0,
        "avgDuration": 3150.0,
        "productivityScore": 96,
        "totalSessions": 14
      },
      {
        "taskType": "writing",
        "strongestWindow": "Insufficient data",
        "completionRate": 0.0,
        "abandonmentRate": 100.0,
        "avgDuration": 225.0,
        "productivityScore": 2,
        "totalSessions": 14
      }
    ]
  },
  "adaptiveRecommendations": [
    {
      "title": "Protect Peak Coding Window",
      "advice": "Schedule demanding coding tasks between 09:00 - 11:00 in Home Office.",
      "reason": "Your coding completion rate reaches 100% in Home Office during this window.",
      "priority": "HIGH",
      "impact": "HIGH"
    },
    {
      "title": "Fatigue Break Pacing",
      "advice": "Cap afternoon focus sessions at 45 minutes and step away before 14:00.",
      "reason": "Severe fatigue peaks after 14:00 (score: 90/100) after extended screen sessions.",
      "priority": "HIGH",
      "impact": "HIGH"
    },
    {
      "title": "Shift Context for Vulnerable Tasks",
      "advice": "Relocate writing sessions from Cafe to Home Office.",
      "reason": "Completion rate is 100.0% in Home Office versus 0.0% in Cafe.",
      "priority": "MEDIUM",
      "impact": "HIGH"
    }
  ]
}
```

---

## ⚖️ Limitations & Methodology

* **Deterministic Statistical/Heuristic Engine:** All profile attributes and recommendations are derived via mathematical heuristics (sliding temporal histograms, ratio drops, duration variance).
* **No Cloud AI / Zero Data Leakage:** This is **not** a cloud LLM or black-box neural network; it runs entirely within Android CPU processes with $< 20\text{ms}$ calculation latency.
* **Sample Size Sensitivity:** Profile conclusions are gated by sample count. When $< 5$ sessions exist, `profileConfidence` drops to `LOW` and recommendations default to data collection pacing rather than false conclusions.

---

## 🧪 Verification

Run test suite:
```bash
python3 test_engine.py
```
14 unit tests cover backward compatibility, morning/afternoon peak detection, task-type analysis, context correlation, high fatigue, conflicting patterns, confidence tiers, and adaptive recommendation ranking.
