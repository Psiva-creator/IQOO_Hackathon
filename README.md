# iQOO Hackathon 2026 — Productivity Track (AI Habit Insights)

> **Detailed Build Split (Folders + GitHub Monorepo)**  
> 2-Day Hackathon build plan dividing the product into three parallel, independently testable slices wired together on Day 2.

---

## 📁 Monorepo Folder Structure

```
IQOO_Hackathon/
├── app-ui/           ← Member A: Task Manager UI + Local Storage (Room DB) + Kotlin LocalAIModel
├── insight-engine/   ← Member B: AI & Analytics Layer (Synthetic Data + Rule/Stats Engine)
├── ai_model/         ← AI Model Integration Layer: Local Model Abstraction + Deterministic Fallback
├── data-sync/        ← Member C: Device Integration Layer (Context Capture + Office Kit Bridge)
├── contracts/        ← Shared Schemas & Data Contracts (Task, Insight, Context Signal, AI Model)
├── submission/       ← Shared (Day 2): PPT Skeleton, Demo Video Script & Deliverables
├── README.md         ← Project Architecture & Hackathon Roadmap
└── .gitignore
```

---

## 👥 Team Roles & Responsibilities

All three members build real, working components of the actual product. PPT and demo video are Day-2-afternoon shared tasks that everyone contributes to.

### 👤 Member A — Folder: `/app-ui`
**Owns:** Task Manager UI + Local Storage (The user-facing experience)
- **Task Model + Room DB (Local SQLite):** Fields: `id`, `title`, `type` (coding, writing, meeting, etc.), `createdAt`, `completedAt`, `duration`, `location`, `priority`.
- **Task Start/Stop Screen:** "Start Task" → pick type → timer runs → "Stop" → saved to DB.
- **Task History Screen:** Simple list of completed tasks (feeds the insight engine).
- **Insights Display Screen (UI Shell):** Cards/layout to display insights output by Member B's engine.
- **Definition of Done (Day 2 Noon):** App installs on iQOO phone, task start/stop works, history screen shows saved tasks, insights screen ready to receive data.

### 👤 Member B — Folder: `/insight-engine`
**Owns:** The AI/Analytics Layer (The "intelligence" and technical depth scoring driver)
- **Synthetic Task Data Generator:** Script producing 5–7 days of realistic fake tasks with discernible patterns (e.g. coding clusters 9–11 AM, writing drop-off after 3 PM).
- **On-Device Insight Engine:** Groups/averages completion by hour, task type, and location to detect peak productivity, procrastination triggers, and optimal contexts. Rule-based / statistical on-device analytics.
- **Insight Output Format:** Clean JSON data structure for Member A's UI to render.
- **Unit Tests & Sample Runs:** Verified against synthetic data before app wiring.
- **Definition of Done (Day 2 Noon):** Engine reliably turns task lists into 2–3 actionable, demoable insights.

### 👤 Member C — Folder: `/data-sync`
**Owns:** Device Integration Layer (Phone-first features & HackTracker scoring)
- **Foreground App / Context Capture:** On-device signal collection (active app category, time of day, screen-on duration).
- **Office Kit Integration (Bridge):** Phone-laptop bridge to sync and view insights on a laptop screen (contributes to 10% Office Kit score).
- **Data Layer Glue:** Connects Member A's stored tasks + Member B's engine + live context signals into a coherent pipeline.
- **Device Testing:** Validates performance, permissions, and execution on actual iQOO 15 hardware.
- **Definition of Done (Day 2 Noon):** Context signals feed into the engine; Office Kit bridge demonstrably works; app tested on iQOO hardware.

---

## 📜 Shared Data Contracts

Locked on Day 1 Morning so each member develops independently without blocking:

### 1. Task Format (Defined by Member A; Consumed by B & C)
```json
{
  "id": "uuid-string",
  "title": "Write API Documentation",
  "type": "writing",
  "createdAt": 1789910400000,
  "completedAt": 1789914000000,
  "duration": 3600,
  "location": "Home Office",
  "priority": "high"
}
```
*Types:* `coding`, `writing`, `meeting`, `reading`, `planning`, `exercise`

### 2. Insight Output Format (Defined by Member B; Consumed by A & C)
```json
{
  "peakHour": "09:00 - 11:00 AM",
  "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM",
  "bestContext": "Home Office (Focus Mode, screen sessions > 45m)",
  "recommendation": "Shift complex writing tasks to your morning peak block (9-11 AM)."
}
```

### 3. Context Signal Format (Defined by Member C; Consumed by B)
```json
{
  "timestamp": 1789910400000,
  "appCategory": "Productivity",
  "location": "Home Office",
  "screenOnDuration": 2700
}
```

### 4. Local AI Model Contract (Defined in `contracts/ai_model.schema.json`)
```json
// Input: Privacy-preserving structured evidence
{
  "currentTask": "coding",
  "productivityScore": 72,
  "fatigue": 78,
  "fatigueLevel": "HIGH",
  "distraction": 45,
  "contextSwitches": 7,
  "context": "Home Office",
  "peakWindow": "09:00 - 11:00",
  "isInPeakWindow": false,
  "prediction": 42,
  "riskLevel": "HIGH",
  "confidence": "HIGH",
  "detectedTrigger": "RAPID_CONTEXT_SWITCHING"
}

// Output: Natural-language coaching
{
  "message": "You're showing signs of fatigue and frequent context switching. Take a short break before continuing.",
  "reason": "Fatigue score is elevated (78/100) and 7 context switches were detected under HIGH risk.",
  "action": "Take a short 10-minute break before continuing.",
  "confidence": "HIGH",
  "provider": "deterministic-fallback-v1",
  "isFallback": true
}
```

---

## 🤖 Local AI Model Integration Layer

### 1. Architectural Pipeline
```
Raw Mobile Signals (App switches, Screen-on duration, Locations)
  ↓
Insight Engine (Statistical aggregation, Fatigue calculation, Calibration)
  ↓
Structured Evidence (AIModelInput — strictly anonymized, zero raw personal data)
  ↓
Local AI Model Layer (LocalAIModel interface)
  ├── FallbackAIModel (Deterministic offline heuristic coach — current active provider)
  └── Future: BaseOnDeviceSLM (Gemma 2B / TinyLlama 1.1B via MediaPipe GenAI / ONNX Runtime)
  ↓
Natural-Language Coaching (AIModelResponse: message, reason, action, confidence)
```

### 2. Privacy-Preserving Structured Evidence (`AIModelInput`)
The model **never receives unnecessary raw personal data**. All raw inputs (personal task titles, notes, full GPS coordinates, URLs, participant names, raw timestamps) are stripped and sanitized before reaching the model:
* `currentTask`: Normalized to generic categories (`coding`, `writing`, `meeting`, `planning`, etc.).
* `context`: Standardized location label (`Home Office`, `Office`, `Cafe`, `Library`).
* `productivityScore`, `fatigue`, `distraction`, `prediction`: Aggregated normalized metrics ($0-100$).
* `facts`: Anonymized operational telemetry observations.

### 3. Deterministic Offline Fallback Coach (`FallbackAIModel`)
Guarantees 100% offline, zero-dependency, reproducible execution even when no local small LLM is installed:
* **Exemplar Match:** `fatigue=78, contextSwitches=7, risk=HIGH` → *"You're showing signs of fatigue and frequent context switching. Take a short break before continuing."*
* **High Fatigue / Screen Strain:** Identifies continuous screen fatigue and prescribes 15-minute physical resets.
* **High Distraction:** Flags frequent context switches and recommends muting notifications for a 25-minute sprint.
* **Vulnerable Context:** Recommends relocating sessions when working in suboptimal environments.
* **Optimal Flow:** Protects sustained focus momentum during peak conditions.
* **Cold Start / Sparse Telemetry:** Provides gentle calibration guidance without making unfounded assumptions.

### 4. Exact Integration Point for Future On-Device Model
To plug in an actual small on-device model (e.g., **Gemma 2B** or **TinyLlama 1.1B**), no modifications are needed in the Insight Engine or UI layers:

1. **Python:** Subclass `BaseOnDeviceSLM` in `ai_model/registry.py`:
   ```python
   class GemmaLocalModel(BaseOnDeviceSLM):
       def execute_inference(self, prompt: str) -> str:
           # Plug in on-device runtime (e.g., llama.cpp, ONNX Runtime, MediaPipe)
           return self.engine.generate(prompt)

   # Register provider
   register_model_provider("gemma", GemmaLocalModel)
   ```
2. **Android / Kotlin:** Subclass `BaseOnDeviceSLM` in `com.iqoo.productivity.ai`:
   ```kotlin
   class MediaPipeGemmaModel(context: Context, modelPath: String) : BaseOnDeviceSLM("gemma-2b", modelPath) {
       private val llmInference = LlmInference.createFromOptions(context, options)
       override fun executeInference(prompt: String): String = llmInference.generateResponse(prompt)
   }
   ```
3. **Resilient Degradation:** `BaseOnDeviceSLM` handles prompt construction (`PromptFormatter`), JSON extraction, and automatically falls back to `FallbackAIModel` if weights are missing, the runtime times out, or output is malformed.

---

## ⏱️ Build Timeline (2 Days)

| Timeframe | Focus | Key Activities |
|---|---|---|
| **Day 1 Morning** | Scope Lock | 30-min team sync, lock contracts and interface boundaries |
| **Day 1 All Day** | Parallel Build | Each member builds their own folder slice independently |
| **Day 1 Evening** | Check-in Sync | Standalone progress verification, resolve blockers |
| **Day 2 Morning** | Integration | Wire UI + Insight Engine + Context Capture, resolve bugs |
| **Day 2 Noon** | Feature Freeze | Working stable build verified on iQOO 15 device |
| **Day 2 Afternoon**| Shared Deliverables | Screen recording (A), Voiceover / Tech script (B), PPT & Video edit (C) |
| **Day 2 Evening** | Submission | Final review and submission on `iqoo.reskilll.com` with buffer |
