# iQOO Hackathon 2026 — Productivity Track (AI Habit Insights)

> **Detailed Build Split (Folders + GitHub Monorepo)**  
> 2-Day Hackathon build plan dividing the product into three parallel, independently testable slices wired together on Day 2.

---

## 📁 Monorepo Folder Structure

```
IQOO_Hackathon/
├── app-ui/           ← Member A: Task Manager UI + Local Storage (Room DB)
├── insight-engine/   ← Member B: AI & Analytics Layer (Synthetic Data + Rule/Stats Engine)
├── data-sync/        ← Member C: Device Integration Layer (Context Capture + Office Kit Bridge)
├── contracts/        ← Shared Schemas & Data Contracts (Task, Insight, Context Signal)
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
