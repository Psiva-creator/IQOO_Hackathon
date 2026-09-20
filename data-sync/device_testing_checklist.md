# 📲 iQOO 15 Device Testing Checklist

**Owner:** Member C  
**Target Hardware:** iQOO 15

---

## 📋 Pre-Flight Checks

- [ ] USB Debugging enabled on iQOO 15
- [ ] Install Debug APK via ADB: `adb install -r app-ui/build/outputs/apk/debug/app-debug.apk`
- [ ] Grant necessary permissions:
  - `android.permission.PACKAGE_USAGE_STATS` (Special app access -> Usage Access)
  - Notifications & Alarm scheduling permissions

---

## 🧪 Test Scenarios

### 1. Task Timer & Persistence
- [ ] Start a 1-minute test task on iQOO 15 screen.
- [ ] Stop task, verify it appears in `TaskHistoryScreen`.
- [ ] Kill app process and restart: verify task history persists in Room DB.

### 2. Context Signal Accuracy
- [ ] Switch to a social or entertainment app for 30 seconds.
- [ ] Verify `ContextCapture` records category change without crashing in the background.
- [ ] Test battery/thermal impact: ensure background polling uses minimal CPU on iQOO 15.

### 3. On-Device Analytics Speed
- [ ] Ingest 50+ task records into `InsightEngine`.
- [ ] Measure calculation time on iQOO 15 hardware (target: `< 150ms`).

### 4. Office Kit Bridge
- [ ] Connect laptop and iQOO 15 to the same Wi-Fi / hotspot.
- [ ] Trigger export from phone to `http://<laptop-ip>:8089/api/sync`.
- [ ] Verify dashboard updates in real-time.
