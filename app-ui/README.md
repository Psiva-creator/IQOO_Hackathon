# 📱 Member A — Folder: `/app-ui`

**Owner:** Member A  
**Domain:** Task Manager UI + Local Storage (The User-Facing Layer)

---

## 🎯 What to Build

1. **Task Model + Room DB (Local SQLite)**
   - Fields: `id`, `title`, `type` (`coding`, `writing`, `meeting`, `reading`, `planning`, `exercise`, `other`), `createdAt`, `completedAt`, `duration`, `location`, `priority`.
   - Data Access Object (`TaskDao`) with queries to fetch tasks, insert completed sessions, and export for the insight engine.

2. **Task Start/Stop Screen**
   - User inputs task title or chooses type.
   - Live running stopwatch / timer displaying elapsed focus time.
   - "Stop Task" saves the session to Room DB with timestamp and duration.

3. **Task History Screen**
   - Recycler / LazyColumn listing completed tasks.
   - Filterable by date, type, or duration.

4. **Insights Display Screen (UI Shell)**
   - Card layout rendering Member B's engine output:
     - 🌟 Peak Productivity Window
     - ⚠️ Procrastination Trigger / Pattern
     - 📍 Optimal Focus Context
     - 💡 AI Recommendation Card

---

## 🚀 GitHub Commit Checklist

- [ ] `app-ui: project setup + Task model`
- [ ] `app-ui: start/stop task UI working`
- [ ] `app-ui: local DB persistence working`
- [ ] `app-ui: task history screen`
- [ ] `app-ui: insights display screen (shell)`
- [ ] `app-ui: polish + bug fixes`

---

## 🏁 Definition of Done (Day 2 Noon)

- App builds & installs cleanly on iQOO Android device.
- Task start/stop timer functions reliably and persists to Room DB.
- History screen lists completed sessions with accurate timestamps.
- Insights screen UI shell is ready to ingest JSON from Member B.
