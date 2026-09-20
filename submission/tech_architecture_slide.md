# 🧠 Slide 5 Content: On-Device Insight Engine Architecture

**Owner:** Member B  
**Deck Placement:** Slide 5 of 9 (The "How It Works" Technical Deep Dive)

---

## 🎯 Slide Title
**On-Device Habit Intelligence: Real-Time Pattern Recognition Without Cloud Privacy Leaks**

---

## 🏗️ Architecture & Pipeline Flow

```
┌────────────────────────┐      ┌─────────────────────────┐
│  Member A: Room DB     │      │   Member C: Context     │
│  (Tasks, Durations)    │      │   (UsageStats, Loc)     │
└───────────┬────────────┘      └────────────┬────────────┘
            │                                │
            └───────────────┬────────────────┘
                            ▼
      ┌───────────────────────────────────────────┐
      │       iQOO On-Device Insight Engine       │
      │   (Statistical & Heuristic Correlation)   │
      ├───────────────────────────────────────────┤
      │ • 24-Hour Binned Completion Density       │
      │ • Task-Type Abandonment & Fatigue Matrix  │
      │ • Context / Environmental Weighting       │
      │ • Sub-10ms Inference, Zero Battery Drain │
      └─────────────────────┬─────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────┐
      │   Actionable Output Contract (JSON)       │
      │   { PeakHour, Procrastination, Context }  │
      └─────────────────────┬─────────────────────┘
             ┌──────────────┴──────────────┐
             ▼                             ▼
   Member A: UI Insight Cards      Member C: Office Kit Sync
```

---

## 💡 Key Technical Highlights for Judges

1. **100% On-Device Privacy:**
   - Raw user tasks, calendar items, and screen times **never leave the iQOO 15 hardware**.
   - Zero API latency, zero subscription costs, works 100% offline.

2. **Multi-Factor Behavioral Correlation:**
   - **Chronobiological Alignment:** Identifies optimal focus blocks (e.g. 09:00–11:30 AM) using hourly density clustering.
   - **Procrastination Trigger Isolation:** Discovers disproportionate failure rates by correlating category vs. time of day (e.g. writing after 3 PM produces an 80% abandon rate).
   - **Context Sensitivity:** Evaluates completion success across environments (Home Office: 88% vs. Cafe: 35%).

3. **Production-Ready Data Contract:**
   - Strict JSON schema (`contracts/insight.schema.json`) guarantees instant UI decoupling and cross-device Office Kit rendering.

4. **Future ML Roadmap (Post-Hackathon):**
   - Seamless drop-in interface for on-device quantized Small Language Models (SLMs via MediaPipe / ONNX Runtime Mobile) for natural-language motivational dialogue.
