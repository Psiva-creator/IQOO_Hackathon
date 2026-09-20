# 🧠 Member B — Folder: `/insight-engine`

**Owner:** Member B  
**Domain:** AI & Analytics Layer (Intelligence Engine & Technical Depth)

---

## 🎯 What to Build

1. **Synthetic Task Data Generator (`synthetic_generator.py`)**
   - Generates 5–7 days of realistic task history with distinct patterns:
     - Morning (9:00 AM – 11:30 AM): High coding completion rate, long focus sessions.
     - Afternoon (after 3:00 PM): High drop-off/abandonment on writing tasks (procrastination trigger).
     - Context: "Home Office" yields 85%+ completion rates vs 40% in "Lounge/Cafe".

2. **On-Device Insight Engine (`engine.py`)**
   - **Input:** List of task objects conforming to `contracts/task.schema.json`.
   - **Analytical Logic:**
     - Computes completion probability & focus duration across 24 hours (binned into morning, afternoon, evening).
     - Detects failure/abandonment correlation across task types & times of day.
     - Evaluates environment contexts (e.g. location, screen sessions).
     - Generates rule-based algorithmic recommendations formatted per `contracts/insight.schema.json`.

3. **Output Contract (`contracts/insight.schema.json`)**
   ```json
   {
     "peakHour": "09:00 AM - 11:30 AM",
     "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM (70% incomplete)",
     "bestContext": "Home Office (Focus Session completion: 88%)",
     "recommendation": "Shift high-friction writing blocks to 09:00 AM before cognitive fatigue sets in."
   }
   ```

4. **Unit Tests (`test_engine.py`)**
   - Verifies peak hour detection, procrastination detection, and deterministic output schema adherence.

---

## 🚀 GitHub Commit Checklist

- [ ] `insight-engine: synthetic data generator`
- [ ] `insight-engine: analytics logic v1 (peak hour detection)`
- [ ] `insight-engine: procrastination + context detection`
- [ ] `insight-engine: recommendation output format`
- [ ] `insight-engine: tested against synthetic data`
- [ ] `insight-engine: integrated into app-ui`

---

## 🏁 Definition of Done (Day 2 Noon)

- Engine reliably turns any task history list into 2–3 accurate, demoable insights.
- JSON output strictly matches the contract for direct rendering in Member A's UI.
- All unit tests pass cleanly.
