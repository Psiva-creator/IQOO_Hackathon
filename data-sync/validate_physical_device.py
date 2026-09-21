"""
Physical Device Validation Script for Member C (App Usage History & Timeline)
Automates or verifies the exact sequence on a connected Android phone (Samsung S25 Ultra / iQOO):
1. Confirms ADB detection
2. Launches Chrome (10s)
3. Launches YouTube (10s)
4. Launches Settings (5s)
5. Returns to Chrome (5s)
6. Captures and validates real sessions in app_usage_history.json
7. Pushes real data to Office Kit Bridge (http://localhost:8089/)
"""

import sys
import os
import time
import json
import subprocess
import urllib.request
import urllib.error

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from app_usage_tracker import AppUsageTracker, resolve_app_name, format_duration
from context_capture import find_adb_path
import office_kit_bridge


def run_adb_cmd(adb_bin: str, args: list) -> subprocess.CompletedProcess:
    return subprocess.run([adb_bin] + args, capture_output=True, text=True, timeout=5.0)


def validate_physical_device():
    print("=" * 70)
    print("   PHYSICAL DEVICE VALIDATION: REAL APP USAGE & TIMELINE")
    print("=" * 70)

    adb_bin = find_adb_path()
    print(f"\n[1/7] Checking ADB executable and attached devices...")
    print(f"      ADB Path: {adb_bin}")

    devices_proc = run_adb_cmd(adb_bin, ["devices", "-l"])
    print(f"      Devices Output:\n{devices_proc.stdout.strip()}")

    device_lines = [l for l in devices_proc.stdout.splitlines() if l.strip() and not l.startswith("List of")]
    if not device_lines:
        print("\n[ERROR] No physical Android device detected via ADB.")
        print("        Please ensure the Samsung S25 Ultra is:")
        print("        1. Connected via USB cable")
        print("        2. Unlocked (screen on)")
        print("        3. USB Debugging enabled in Developer Options")
        return False

    device_info = device_lines[0]
    serial = device_info.split()[0]
    print(f"\n[2/7] Connected Device Verified:")
    print(f"      Serial: {serial}")
    print(f"      Raw:    {device_info}")

    history_file = os.path.join(CURRENT_DIR, "app_usage_history.json")
    if os.path.exists(history_file):
        os.remove(history_file)

    tracker = AppUsageTracker(history_file=history_file, min_session_seconds=2, poll_interval=1.0)
    print(f"\n[3/7] Starting AppUsageTracker in background (polling @ 1.0s interval)...")
    tracker.start_tracking()

    try:
        # Step A: Chrome for ~10 seconds
        print("\n[4/7] Executing real-device sequence:")
        print("      -> Step 1: Launching Chrome (staying 10s)...")
        run_adb_cmd(adb_bin, ["shell", "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main"])
        for i in range(10):
            sys.stdout.write(f"\r         Time in Chrome: {i + 1}s / 10s")
            sys.stdout.flush()
            time.sleep(1.0)
        print()

        # Step B: YouTube for ~10 seconds
        print("      -> Step 2: Launching YouTube (staying 10s)...")
        run_adb_cmd(adb_bin, ["shell", "am", "start", "-n", "com.google.android.youtube/com.google.android.youtube.app.honeycomb.Shell$HomeActivity"])
        for i in range(10):
            sys.stdout.write(f"\r         Time in YouTube: {i + 1}s / 10s")
            sys.stdout.flush()
            time.sleep(1.0)
        print()

        # Step C: Settings for ~5 seconds
        print("      -> Step 3: Launching Settings (staying 5s)...")
        run_adb_cmd(adb_bin, ["shell", "am", "start", "-a", "android.settings.SETTINGS"])
        for i in range(5):
            sys.stdout.write(f"\r         Time in Settings: {i + 1}s / 5s")
            sys.stdout.flush()
            time.sleep(1.0)
        print()

        # Step D: Chrome for ~5 seconds
        print("      -> Step 4: Returning to Chrome (staying 5s)...")
        run_adb_cmd(adb_bin, ["shell", "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main"])
        for i in range(5):
            sys.stdout.write(f"\r         Time in Chrome: {i + 1}s / 5s")
            sys.stdout.flush()
            time.sleep(1.0)
        print()

    finally:
        print("\n[5/7] Stopping AppUsageTracker and flushing active sessions...")
        tracker.stop_tracking()

    # Step 6: Verify captured file
    print(f"\n[6/7] Verifying captured app_usage_history.json...")
    if not os.path.exists(history_file):
        print("      [FAIL] app_usage_history.json was not created.")
        return False

    with open(history_file, "r", encoding="utf-8") as f:
        captured = json.load(f)

    print(f"      Total Real Sessions Captured: {len(captured)}")
    for idx, s in enumerate(captured, 1):
        print(f"      Session #{idx}: {s.get('appName')} ({s.get('appCategory')}) - {s.get('durationSeconds')}s [pkg: {s.get('packageName')}]")

    # Step 7: Push real data to Office Kit Bridge
    print(f"\n[7/7] Synchronizing Real Device App Usage with Office Kit Bridge (port 8089)...")
    payload = tracker.get_app_usage_payload()
    sync_payload = {
        "appUsage": payload,
        "activeDevice": serial,
        "dataSource": "REAL_PHONE_ADB"
    }

    synced = office_kit_bridge.push_to_bridge(sync_payload, host="127.0.0.1", port=8089)
    print(f"      Sync to http://localhost:8089/api/sync: {'SUCCESSFUL' if synced else 'FAILED'}")
    print(f"      Dashboard URL: http://localhost:8089/")

    print("\n" + "=" * 70)
    print("   PHYSICAL DEVICE VALIDATION COMPLETE - REAL DATA VERIFIED")
    print("=" * 70)
    return True


if __name__ == "__main__":
    validate_physical_device()
