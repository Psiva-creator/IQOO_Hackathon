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

## 🔮 Predictive Productivity / "Should I do this task now?"

The engine exposes predictive readiness evaluation (`predict_task_readiness` in Python, `predictTaskReadiness` in Kotlin, or `taskPrediction` within `analyze()`), answering: **"Given my current state, context, and time of day, is now an optimal time to start this specific task?"**

### 1. Mathematical Scoring Formula ($0 \le S_{\text{predicted}} \le 100$)

$$\begin{aligned}
S_{\text{predicted}} &= \text{clamp}\Big(S_{\text{base}} + S_{\text{task}} + S_{\text{time}} + S_{\text{context}} - P_{\text{fatigue}} - P_{\text{distraction}},\, 0,\, 100\Big)
\end{aligned}$$

| Factor | Weight / Range | Description & Calculation |
|---|---|---|
| **$S_{\text{base}}$** | $20$ pts | Baseline focus readiness offset. |
| **$S_{\text{task}}$** | $0 - 35$ pts | $C_{\text{type}} \times 35.0$ where $C_{\text{type}}$ is historical completion rate for this task type. |
| **$S_{\text{time}}$** | $0 - 25$ pts | $H_{\text{rate}} \times 25.0$ based on success around `current_hour` (from heatmap or diurnal curve). |
| **$S_{\text{context}}$** | $0 - 20$ pts | $C_{\text{context}} \times 20.0$ based on user's completion rate in the active environment. |
| **$P_{\text{fatigue}}$** | $0 - 25$ pts | $(S_{\text{fatigue}} \times 0.15) + P_{\text{screen}}$ (penalizes high fatigue score and continuous screen $> 40\text{m}$). |
| **$P_{\text{distraction}}$** | $0 - 15$ pts | Penalizes vulnerable task types in suboptimal environments (e.g. writing in Cafe: $-12$ pts). |

### 2. Risk Levels & Thresholds
* **`LOW` Risk ($S_{\text{predicted}} \ge 70$):** High historical probability of focus; conditions optimal.
* **`MEDIUM` Risk ($45 \le S_{\text{predicted}} < 70$):** Moderate friction; suggests 25-minute capped focus sprint.
* **`HIGH` Risk ($S_{\text{predicted}} < 45$):** Severe failure/burnout probability; advises rescheduling to `bestAlternativeWindow`.

### 3. Confidence Stratification
* **`HIGH`**: User has $\ge 5$ total sessions and $\ge 3$ sessions for this specific task type.
* **`MEDIUM`**: User has $\ge 5$ total sessions and $\ge 1$ session for this specific task type.
* **`LOW`**: Insufficient sessions ($< 5$ total or $0$ for this task type). Returns baseline calibration estimate.

### 4. Output Contract
```json
{
  "taskType": "coding",
  "predictedScore": 42,
  "confidence": "HIGH",
  "riskLevel": "HIGH",
  "bestAlternativeWindow": "09:00 - 11:00",
  "reason": "Coding now has HIGH risk (42/100): hour (15:00) is outside your peak focus; fatigue is elevated (score: 90/100, 90m screen time). Your coding completion is significantly higher during 09:00 - 11:00.",
  "recommendation": "Consider postponing coding to Tomorrow morning (09:00 - 11:00) in Home Office. Take a 15-minute break now to recover cognitive energy."
}
```

---

## ⚖️ Limitations & Methodology

* **Deterministic Statistical/Heuristic Engine:** All profile attributes, recommendations, and predictions are derived via transparent mathematical heuristics (sliding temporal histograms, ratio drops, duration variance).
* **No Cloud AI / Zero Data Leakage:** This is **not** a cloud LLM or black-box neural network; it runs entirely within Android CPU processes with $< 20\text{ms}$ calculation latency.
* **Sample Size Sensitivity:** Profile conclusions are gated by sample count. When $< 5$ sessions exist, `confidence` drops to `LOW` and recommendations default to data collection calibration rather than false conclusions.

---

## 🧪 Verification

Run test suite:
```bash
python3 -m unittest test_engine.py -v
```
21 unit tests cover:
1. Backward compatibility for legacy contracts
2. Peak morning hour detection
3. Procrastination trigger detection
4. Confidence level tiers
5. Hourly heatmap generation
6. Insufficient data / cold start profiles
7. Strong morning & afternoon profiles
8. Task-type $\times$ time window correlation
9. Context-dependent performance ranking
10. Conflicting patterns & high-switching behavior
11. High fatigue detection & adaptive recommendations
12. Recommendation generation & priority sorting
13. **High prediction (optimal conditions)**
14. **Low prediction (suboptimal context & timing)**
15. **Insufficient data prediction (cold start, sparse, unseen task types)**
16. **Context change prediction (Home Office vs Cafe comparison)**
17. **Fatigue & screen strain impact on prediction**
18. **`analyze()` backward-compatible target task prediction**
19. **Module-level convenience prediction helper**

