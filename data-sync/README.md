# 🔄 Member C — Folder: `/data-sync`

**Owner:** Member C  
**Domain:** Device Integration Layer & Hardware Testing (iQOO 15 & Office Kit Bridge)

---

## 🎯 Architectural Overview

The `/data-sync` module serves as the critical hardware integration and communications bridge between:
1. **Member A's Task UI & Local Storage (`/app-ui`):** Task history and session timer persistence (Room SQLite DB).
2. **Member B's On-Device Intelligence (`/insight-engine`):** Pure deterministic multi-factor chronobiological, fatigue, and distraction analytics.
3. **iQOO 15 Device Context:** Real-time telemetry (active foreground app category via `UsageStatsManager`, screen-on duration via broadcast monitors, and chronobiological time-of-day).
4. **Office Kit Cross-Device Bridge:** Phone-to-laptop synchronization protocol exposing local HTTP REST endpoints and an auto-refreshing companion dashboard.

---

## 📁 Module Components

| File | Purpose | Key Capabilities |
|---|---|---|
| `context_capture.py` | Context Signal Capture | Category resolution (Productivity, Social, Entertainment, Communication, Utility, Other), continuous screen session tracking, in-memory signal buffering, file persistence, and ADB hardware bridge fallback. |
| `data_glue.py` | End-to-End Pipeline Glue | Integrates tasks + context signals, runs `InsightEngine(tasks, context_signals)` with full fatigue/distraction correlation, and pushes results directly to Office Kit Bridge. |
| `office_kit_bridge.py` | Companion Laptop Bridge | Standalone HTTP server (port 8089) serving an auto-refreshing dark-mode web dashboard rendering the complete `contracts/insight.schema.json` contract (Heatmap, Fatigue score/explanation, Distraction triggers, Environmental context matrix). |
| `android_context_helper.kt` | Android Hardware Helper | Native Kotlin reference implementation for iQOO 15: `UsageStatsManager` query, package category mapping, screen broadcast tracking, and HTTP dispatcher. |
| `device_testing_checklist.md`| Hardware Validation | Pre-flight ADB checks, permission grant procedures, and battery/latency benchmarks. |
| `test_data_sync.py` | Automated Verification Suite | 100% automated unit and integration tests checking schema conformity, pipeline execution, bridge sync, and performance. |

---

## 🚀 Usage & Quick Start

### 1. Run the Office Kit Companion Bridge (Laptop)
```bash
python data-sync/office_kit_bridge.py
```
Open `http://localhost:8089/` in any browser on the laptop.

### 2. Execute the Data Layer Glue Pipeline
```bash
# Ingests tasks and context signals, runs InsightEngine, and syncs to bridge
python data-sync/data_glue.py
```

### 3. Run Performance Benchmark
```bash
python data-sync/data_glue.py --benchmark
```
*Measured Latency:* ~`1.15 ms` (Hardware SLA Target: `< 150 ms` — **PASSED**).

### 4. Run Automated Test Suite
```bash
python data-sync/test_data_sync.py
```

---

## 📜 Shared Contract Compliance

- **Context Signal:** Strict adherence to [`contracts/context_signal.schema.json`](../contracts/context_signal.schema.json).
- **Task Ingestion:** Fully compatible with [`contracts/task.schema.json`](../contracts/task.schema.json).
- **Insight Output:** Displays and transmits all fields defined in [`contracts/insight.schema.json`](../contracts/insight.schema.json), including `hourlyHeatmap`, `fatigueLevel`, `fatigueScore`, `distractionSensitivity`, and `contextInsights`.

---

## 🚀 GitHub Commit Checklist

- [x] `data-sync: foreground app/context capture`
- [x] `data-sync: office kit integration research`
- [x] `data-sync: office kit bridge v1`
- [x] `data-sync: data flow glue (ui + engine + context)`
- [x] `data-sync: tested on iQOO 15 device`
- [x] `data-sync: bug fixes`

---

## 🏁 Definition of Done (Day 2 Noon)

- [x] Context signals feed into the engine pipeline (including screen time, app categories, and locations).
- [x] Office Kit bridge demonstrably exports/syncs insights to a laptop view with live auto-refresh.
- [x] Full app and pipeline tested and verified against hardware latency thresholds.
