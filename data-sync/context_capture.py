"""
Foreground App / Context Capture Module
Simulates and bridges Android UsageStatsManager signals for on-device context awareness.
Collects: active app category, timestamp, location, and continuous screen-on duration.
Strictly adheres to contracts/context_signal.schema.json.
"""

import time
import json
import os
import subprocess
from typing import Dict, Any, List, Optional

try:
    from app_usage_tracker import AppUsageTracker, AppUsageRecord, resolve_app_name, APP_NAMES
except ImportError:
    from .app_usage_tracker import AppUsageTracker, AppUsageRecord, resolve_app_name, APP_NAMES

VALID_CATEGORIES = {"Productivity", "Social", "Entertainment", "Communication", "Utility", "Other"}


def parse_dumpsys_output(raw_output: str) -> Optional[str]:
    """
    Parses raw adb dumpsys (window/activity/usagestats) output to isolate the active foreground package name.
    Handles multiple Android system formats:
    - mCurrentFocus=Window{... u0 com.instagram.android/com.instagram.main.MainActivity}
    - mFocusedApp=ActivityRecord{... u0 com.google.android.youtube/...}
    - topResumedActivity=ActivityRecord{... com.android.chrome/...}
    """
    if not raw_output:
        return None
    for line in raw_output.splitlines():
        if any(marker in line for marker in ["mCurrentFocus", "mFocusedApp", "topResumedActivity", "ResumedActivity"]):
            parts = line.split()
            for part in parts:
                if "/" in part:
                    pkg = part.split("/")[0].replace("}", "").replace("{", "").strip()
                    if "." in pkg and not pkg.startswith("/"):
                        return pkg
    return None


def find_adb_path() -> str:
    """Finds adb executable from system PATH or standard WinGet/Android SDK directories."""
    import shutil
    import glob
    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb

    patterns = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.PlatformTools_*\platform-tools\adb.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        r"C:\platform-tools\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe"
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches and os.path.isfile(matches[0]):
            return matches[0]
    return "adb"


class ContextCapture:
    CATEGORIES = {
        # Productivity
        "com.android.chrome": "Productivity",
        "com.google.android.apps.docs": "Productivity",
        "com.google.android.apps.docs.editors.sheets": "Productivity",
        "com.google.android.apps.docs.editors.slides": "Productivity",
        "com.github.android": "Productivity",
        "com.microsoft.office.word": "Productivity",
        "com.microsoft.office.excel": "Productivity",
        "com.slack": "Productivity",
        "notion.id": "Productivity",
        "com.todoist": "Productivity",
        "md.obsidian": "Productivity",
        "com.termux": "Productivity",
        "com.google.android.keep": "Productivity",

        # Communication
        "org.telegram.messenger": "Communication",
        "com.whatsapp": "Communication",
        "com.google.android.gm": "Communication",
        "com.microsoft.office.outlook": "Communication",
        "com.google.android.apps.messaging": "Communication",
        "com.discord": "Communication",
        "us.zoom.videomeetings": "Communication",
        "org.thoughtcrime.securesms": "Communication",

        # Social
        "com.instagram.android": "Social",
        "com.twitter.android": "Social",
        "com.facebook.katana": "Social",
        "com.reddit.frontpage": "Social",
        "com.linkedin.android": "Social",
        "com.zhiliaoapp.musically": "Social",
        "com.snapchat.android": "Social",
        "com.threads.android": "Social",

        # Entertainment
        "com.google.android.youtube": "Entertainment",
        "com.netflix.mediaclient": "Entertainment",
        "com.spotify.music": "Entertainment",
        "tv.twitch.android.app": "Entertainment",
        "com.amazon.avod.thirdpartyclient": "Entertainment",
        "com.disney.disneyplus": "Entertainment",
        "com.supercell.clashroyale": "Entertainment",

        # Utility / System
        "com.android.settings": "Utility",
        "com.android.calculator2": "Utility",
        "com.google.android.deskclock": "Utility",
        "com.android.vending": "Utility",
        "com.google.android.apps.nbu.files": "Utility"
    }

    def __init__(self, location: str = "Home Office"):
        self.current_location = location or "Home Office"
        self.screen_on_start = time.time()
        self.signal_buffer: List[Dict[str, Any]] = []

    def categorize_package(self, package_name: str) -> str:
        """Resolves package name to one of 6 contract-defined categories."""
        if not package_name:
            return "Other"
        
        # 1. Exact match
        if package_name in self.CATEGORIES:
            return self.CATEGORIES[package_name]
        
        # 2. Heuristic fallback based on package naming conventions
        lower_pkg = package_name.lower()
        if any(w in lower_pkg for w in ["doc", "sheet", "code", "dev", "notes", "task", "git", "terminal", "edit"]):
            return "Productivity"
        if any(w in lower_pkg for w in ["chat", "mail", "talk", "message", "meet", "call"]):
            return "Communication"
        if any(w in lower_pkg for w in ["social", "insta", "tweet", "reddit", "feed"]):
            return "Social"
        if any(w in lower_pkg for w in ["game", "play", "video", "tube", "stream", "music", "tv"]):
            return "Entertainment"
        if any(w in lower_pkg for w in ["setting", "tool", "calc", "clock", "file", "system"]):
            return "Utility"
        
        return "Other"

    def capture_current_signal(self, package_name: str = "com.android.chrome", location: Optional[str] = None) -> Dict[str, Any]:
        """Captures an instantaneous ContextSignal conforming to contracts/context_signal.schema.json."""
        category = self.categorize_package(package_name)
        now_ms = int(time.time() * 1000)
        screen_on_sec = int(time.time() - self.screen_on_start)
        loc = (location.strip() if location and location.strip() else None) or self.current_location or "Home Office"

        signal = {
            "timestamp": now_ms,
            "appCategory": category,
            "location": loc,
            "screenOnDuration": max(0, screen_on_sec)
        }
        return signal

    def record_signal(
        self,
        package_name: str = "com.android.chrome",
        location: Optional[str] = None,
        screen_on_duration: Optional[int] = None,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Captures and appends a signal to the internal buffer."""
        signal = self.capture_current_signal(package_name=package_name, location=location)
        if screen_on_duration is not None:
            signal["screenOnDuration"] = max(0, int(screen_on_duration))
        if timestamp is not None:
            signal["timestamp"] = int(timestamp)

        self.signal_buffer.append(signal)
        return signal

    def get_signal_buffer(self) -> List[Dict[str, Any]]:
        """Returns the in-memory context signal history."""
        return list(self.signal_buffer)

    def load_signals_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Loads historical context signals from a JSON file into buffer."""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    self.signal_buffer.extend(loaded)
                    return loaded
        return []

    def export_signals_to_file(self, file_path: str) -> None:
        """Exports in-memory signal buffer to JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.signal_buffer, f, indent=2)

    def capture_from_adb(self, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Attempts to read real-time foreground application from an attached Android/iQOO device via ADB.
        Falls back smoothly to simulated Productivity signal if device is not connected.
        """
        package_name = "com.android.chrome"
        adb_bin = find_adb_path()
        try:
            cmd = [adb_bin, "shell", "dumpsys", "window", "displays"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            if proc.returncode == 0:
                parsed = parse_dumpsys_output(proc.stdout)
                if parsed:
                    package_name = parsed
        except Exception:
            # Fallback if adb is not found or device is disconnected
            package_name = "com.android.chrome"

        return self.record_signal(package_name=package_name, location=location)

    def reset_screen_session(self):
        """Resets the continuous screen-on timer baseline."""
        self.screen_on_start = time.time()

    @staticmethod
    def validate_signal(signal: Dict[str, Any]) -> bool:
        """Validates that a signal strictly adheres to contracts/context_signal.schema.json."""
        required = ["timestamp", "appCategory", "location", "screenOnDuration"]
        for k in required:
            if k not in signal:
                return False
        if not isinstance(signal["timestamp"], int):
            return False
        if signal["appCategory"] not in VALID_CATEGORIES:
            return False
        if not isinstance(signal["location"], str) or not signal["location"]:
            return False
        if not isinstance(signal["screenOnDuration"], (int, float)) or signal["screenOnDuration"] < 0:
            return False
        return True


if __name__ == "__main__":
    capture = ContextCapture(location="Home Office")
    print("Testing ContextCapture Module:")
    sig1 = capture.record_signal("com.android.chrome")
    sig2 = capture.record_signal("com.instagram.android", screen_on_duration=4800)
    print("Sample Signal (Simulated):")
    print(json.dumps(sig1, indent=2))
    print(f"Validation passed: {ContextCapture.validate_signal(sig1)}")
    print(f"Buffer size: {len(capture.get_signal_buffer())}")

    print("\nLive Device Telemetry (via ADB):")
    sig_live = capture.capture_from_adb()
    print(json.dumps(sig_live, indent=2))
    print(f"Live validation passed: {ContextCapture.validate_signal(sig_live)}")
