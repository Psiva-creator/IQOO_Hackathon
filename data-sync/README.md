# 🔄 Member C — Folder: `/data-sync`

**Owner:** Member C  
**Domain:** Device Integration Layer & Hardware Testing (iQOO 15 & Office Kit Bridge)

---

## 🎯 What to Build

1. **Foreground App / Context Capture (`context_capture.py`)**
   - Collects on-device context signals: active app category (Productivity, Social, etc.), time of day, screen-on duration.
   - Leverages Android `UsageStatsManager` / device state sensors to detect when the user switches away or enters focus mode.

2. **Office Kit Integration (`office_kit_bridge.py`)**
   - Implements phone-to-laptop synchronization bridge (securing the 10% Office Kit score).
   - Exposes local HTTP / WebSocket bridge or file exchange to mirror generated insights to a companion laptop dashboard.

3. **Data Layer Glue (`data_glue.py`)**
   - Unifies Member A's stored tasks + Member B's analytics engine + live context signals into a single data pipeline.

4. **iQOO 15 Device Testing & Verification (`device_testing_checklist.md`)**
   - Performance profiling on actual iQOO 15 hardware (CPU, battery impact of foreground tracking).
   - Permission handling (`PACKAGE_USAGE_STATS`, notification listener).

---

## 🚀 GitHub Commit Checklist

- [ ] `data-sync: foreground app/context capture`
- [ ] `data-sync: office kit integration research`
- [ ] `data-sync: office kit bridge v1`
- [ ] `data-sync: data flow glue (ui + engine + context)`
- [ ] `data-sync: tested on iQOO 15 device`
- [ ] `data-sync: bug fixes`

---

## 🏁 Definition of Done (Day 2 Noon)

- Context signals feed into the engine pipeline.
- Office Kit bridge demonstrably exports/syncs insights to a laptop view.
- Full app tested on actual iQOO 15 hardware.
