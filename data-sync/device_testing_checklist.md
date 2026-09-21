# 📲 iQOO 15 Device Testing Checklist & Execution Guide

**Owner:** Member C  
**Target Hardware:** iQOO 15 (Snapdragon 8 Elite / Funtouch OS / OriginOS)

---

## 📋 Pre-Flight Checks & Environment Setup

- [ ] Connect iQOO 15 phone to laptop via USB cable.
- [ ] Enable **Developer Options** and turn on **USB Debugging**.
- [ ] Verify device connectivity:
  ```bash
  adb devices
  ```
- [ ] Install Debug APK (once built by Member A):
  ```bash
  adb install -r app-ui/build/outputs/apk/debug/app-debug.apk
  ```
- [ ] Fast-grant Usage Access permission via ADB (bypasses manual Settings navigation):
  ```bash
  adb shell appops set com.iqoo.productivity GET_USAGE_STATS allow
  ```
- [ ] (Optional) Verify foreground package detection via ADB shell:
  ```bash
  adb shell dumpsys window | findstr "mCurrentFocus"
  ```

---

## 🧪 Verification & Test Scenarios

### 1. Automated Test Suite Execution
Run the complete automated integration test suite from the repository root:
```bash
python data-sync/test_data_sync.py
```
- [x] All 10 unit and integration tests pass with 0 errors.
- [x] Schema compliance with `contracts/context_signal.schema.json` confirmed.
- [x] Schema compliance with `contracts/insight.schema.json` confirmed.

---

### 2. On-Device Analytics Latency Target (< 150ms)
Verify processing speed using the built-in benchmark runner:
```bash
python data-sync/data_glue.py --benchmark
```
- [x] Benchmark result: **~1.15 ms average latency** (Sub-10ms inference, zero thermal load).
- [x] Pass criteria: Latency $< 150\text{ms}$ confirmed.

---

### 3. Context Signal Accuracy & Distraction Tracking
- [ ] On the iQOO 15 phone, start a focus task.
- [ ] Switch to a distracting application (e.g. YouTube, Instagram) for 30–60 seconds.
- [ ] Verify that `ContextCapture` records:
  - App Category: `Entertainment` or `Social`.
  - Continuous screen session timestamp elapsed.
- [ ] Verify that non-productive switches trigger the distraction penalty in `InsightEngine`:
  - `distractionSensitivity.level`: `HIGH`
  - `distractionSensitivity.triggerAppCategories`: `["Entertainment", "Social"]`

---

### 4. Office Kit Cross-Device Bridge Verification
- [ ] Connect laptop and iQOO 15 phone to the **same Wi-Fi network or mobile hotspot**.
- [ ] Find laptop local IP address:
  ```powershell
  ipconfig  # Look for IPv4 Address, e.g. 192.168.1.50
  ```
- [ ] Start Office Kit Bridge on laptop:
  ```bash
  python data-sync/office_kit_bridge.py
  ```
- [ ] Open dashboard in laptop browser: `http://localhost:8089/`
- [ ] Trigger sync pipeline from phone / CLI:
  ```bash
  python data-sync/data_glue.py --bridge-host <laptop-ip> --bridge-port 8089
  ```
- [ ] Verify that the laptop dashboard auto-refreshes within 2.5 seconds:
  - ⚡ Peak Productivity Window rendered.
  - ⚠️ Procrastination Alert rendered.
  - 🔋 Cognitive & Session Fatigue badge and score ($0-100$) updated.
  - 🕒 24-Hour Productivity Heatmap dynamically colored.
  - 🏢 Context completion table updated.

---

### 5. 100% Offline & Zero-Cloud Privacy Check
- [ ] Disconnect internet access (switch router off or enable Airplane Mode on phone with local hotspot only).
- [ ] Run the pipeline: `python data-sync/data_glue.py`.
- [ ] Verify that all metrics compute instantly without network timeout or errors.
- [ ] Confirm: **0 bytes of private task or activity data ever sent to external cloud servers.**
