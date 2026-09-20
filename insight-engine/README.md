# 🧠 Member B — Folder: `/insight-engine`

**Owner:** Member B  
**Domain:** On-Device Analytics & Behavioral Intelligence Layer (Context-Aware Productivity & Fatigue Engine)

---

## 🎯 Architecture Overview

The `insight-engine` is a **100% on-device, zero-external-dependency** intelligence layer implemented in both **Python** (`engine.py` as reference) and **Kotlin** (`InsightEngine.kt` for direct Android integration in `app-ui`).

It analyzes historical task records alongside real-time device context signals to discover subconscious productivity habits, compute cognitive fatigue, identify distraction vulnerabilities, and generate explainable coaching recommendations.

---

## 🔬 Core Analytics & Formulas

### 1. Cognitive & Session Fatigue Detection (`fatigueLevel`, `fatigueScore`)
Calculates a quantified fatigue score ($0 \le S_{\text{fatigue}} \le 100$) combining four independent behavioral degradation factors:

1. **Screen & Continuous Duration Strain ($0 - 30$ pts):**
   * If context signals are present: Evaluates continuous `screenOnDuration`.
     * $\ge 7200\text{s}$ ($2\text{h}+$) or average $\ge 4500\text{s}$: $+30$ pts
     * $\ge 4500\text{s}$ ($75\text{m}+$) or average $\ge 3000\text{s}$: $+20$ pts
     * $\ge 2700\text{s}$ ($45\text{m}+$): $+10$ pts
   * If signals are absent: Inferred from average task duration ($\ge 60\text{m}: +20$ pts, $\ge 40\text{m}: +10$ pts).

2. **Declining Completion Rate ($0 - 30$ pts):**
   * Compares morning ($< 13:00$) vs afternoon ($\ge 13:00$) completion rates:
     $$\Delta_{\text{drop}} = \text{Rate}_{\text{morning}} - \text{Rate}_{\text{afternoon}}$$
     * $\Delta_{\text{drop}} \ge 0.40$: $+30$ pts
     * $\Delta_{\text{drop}} \ge 0.20$: $+20$ pts
     * $\Delta_{\text{drop}} \ge 0.10$: $+10$ pts

3. **Session Duration Shrinkage ($0 - 20$ pts):**
   * Compares average focus session length in the afternoon versus morning:
     $$\text{Ratio} = \frac{\bar{D}_{\text{afternoon}}}{\bar{D}_{\text{morning}}}$$
     * $\text{Ratio} \le 0.50$ (sessions cut in half or more): $+20$ pts
     * $\text{Ratio} \le 0.75$: $+10$ pts

4. **Task & Context Switching Load ($0 - 20$ pts):**
   * Ratio of non-productive context signals (`Social`, `Entertainment`) during focus windows:
     * $\ge 35\%$ non-productive signals: $+20$ pts
     * $\ge 15\%$ non-productive signals: $+10$ pts
   * Or rapid consecutive task type switches ($< 45$ min interval): $+10$ to $+15$ pts.

**Fatigue Classification:**
* **`HIGH`**: $S_{\text{fatigue}} \ge 65$
* **`MEDIUM`**: $35 \le S_{\text{fatigue}} < 65$
* **`LOW`**: $S_{\text{fatigue}} < 35$

---

### 2. Context Correlation (`contextInsights`)
Measures productivity variance across different environments (e.g., `Home Office`, `Cafe`, `Meeting Room`).

* **Completion Rate per Context:**
  $$\text{CompletionRate}(c) = \frac{\text{CompletedTasks}(c)}{\text{TotalTasks}(c)} \times 100$$
* **Context Status Classification:**
  * `Optimal`: $\ge 75.0\%$ completion
  * `Moderate`: $50.0\% - 74.9\%$ completion
  * `Suboptimal`: $< 50.0\%$ completion
* **Dynamic Best Context:** Ranks contexts by completion rate and session volume (minimum 2 tasks for statistical reliability).

---

### 3. Distraction Sensitivity (`distractionSensitivity`)
Correlates incomplete/abandoned tasks with active app categories (`Social`, `Entertainment`, `Communication`) and non-optimal contexts.

* Identifies **vulnerable task categories** where abandonment rate exceeds $40\%$ (e.g. `writing`).
* Isolates **trigger app categories** active during failure windows.
* Generates risk tiers: `HIGH`, `MEDIUM`, or `LOW`.

---

### 4. Smart Recommendation Generation (`recommendation`)
Generates explainable, actionable coaching text synthesized entirely from computed metrics:
* Cites the user's verified peak task type and window (e.g., `09:00 - 11:00 AM`).
* Directly contrasts optimal versus suboptimal contexts with calculated percentages.
* Injects personalized interventions based on the quantified fatigue score and distraction vulnerability.

---

## 📥 Input & Output Example

### Input: Tasks + Context Signals
```json
// Task Input Example
{
  "id": "task-01",
  "title": "Refactor Data Pipeline",
  "type": "coding",
  "createdAt": 1789271100000,
  "completedAt": 1789274700000,
  "duration": 3600,
  "location": "Home Office",
  "priority": "high"
}

// Context Signal Input Example
{
  "timestamp": 1789293600000,
  "appCategory": "Social",
  "location": "Cafe",
  "screenOnDuration": 7500
}
```

### Output: Synthesized Insight Contract
```json
{
  "peakHour": "09:00 - 11:00 (Peak focus completion)",
  "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM (100% abandon rate)",
  "bestContext": "Home Office (100.0% completion across 21 sessions)",
  "recommendation": "Your coding completion rate peaks between 09:00 - 11:00 (100% completion in Home Office). In contrast, writing sessions drop to 0.0% completion in Cafe. High afternoon fatigue (score: 75/100) significantly degrades focus after extended screen sessions. Consider scheduling difficult writing tasks before 11:00 AM in Home Office, and limit continuous screen blocks to 45 minutes.",
  "productivityScore": 66,
  "confidenceLevel": "High",
  "hourlyHeatmap": { "9": 100, "10": 100, "15": 0, "16": 0, ... },
  "fatigueLevel": "HIGH",
  "fatigueScore": 75,
  "explanation": "Fatigue is HIGH (score: 75/100). Completion rate drops by 50% in the afternoon (100% morning vs 50% afternoon); focus sessions shorten by 75% after mid-day; prolonged continuous screen time exceeds 125 minutes.",
  "contextInsights": [
    {
      "context": "Home Office",
      "completionRate": 100.0,
      "totalTasks": 21,
      "completedTasks": 21,
      "avgDuration": 2400.0,
      "status": "Optimal"
    },
    {
      "context": "Cafe",
      "completionRate": 0.0,
      "totalTasks": 14,
      "completedTasks": 0,
      "avgDuration": 225.0,
      "status": "Suboptimal"
    }
  ],
  "distractionSensitivity": {
    "level": "HIGH",
    "score": 60,
    "vulnerableCategories": ["writing"],
    "triggerAppCategories": ["Entertainment", "Social"],
    "summary": "HIGH sensitivity: Writing tasks show high abandonment when Entertainment, Social apps are accessed."
  }
}
```

---

## ⚖️ Limitations & Technical Integrity

* **Statistical & Heuristic Engine:** This intelligence engine relies on **deterministic statistical aggregation and heuristic correlation**, not a neural network or generative Large Language Model (LLM).
* **Advantages:**
  * Zero inference latency ($< 15\text{ms}$).
  * Zero battery and thermal drain on iQOO 15 hardware.
  * $100\%$ privacy: no raw telemetry or task notes ever leave the phone.
  * Fully deterministic and explainable: every recommendation links directly to an underlying mathematical calculation.
* **Roadmap / Stretch Goal:** In future iterations, this engine provides the structured numerical features to condition an on-device Small Language Model (e.g. Gemma-2B / MediaPipe) for conversational coaching.

---

## 🧪 Running Tests

```bash
cd insight-engine
python3 test_engine.py
```
All 12 test suites covering normal productivity, high fatigue, context correlation, distraction sensitivity, missing fields, and backward compatibility must pass with zero errors.
