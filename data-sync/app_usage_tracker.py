"""
App Usage Tracker & Real-Time Timeline Engine
Monitors the connected Android/iQOO device via ADB or on-device events.
Captures foreground app transitions, calculates elapsed active duration,
filters transient system overlays, and maintains persistent chronological history.
"""

import os
import sys
import json
import time
import subprocess
import threading
from typing import Dict, Any, List, Optional, Tuple

# System packages and windows that must be ignored as non-user apps
SYSTEM_PACKAGES = {
    "com.android.systemui",
    "com.sec.android.app.launcher",
    "android",
    "com.google.android.apps.nexuslauncher",
    "com.samsung.android.app.telephonyui",
    "com.google.android.inputmethod.latin",
    "com.samsung.android.honeyboard"
}

SYSTEM_WINDOW_KEYWORDS = [
    "NotificationShade",
    "Keyguard",
    "StatusBar",
    "NavigationBar",
    "ScreenDecorOverlay",
    "EdgePanel",
    "SecFloatingIconView",
    "PipMenuActivity"
]

# Friendly display names for common Android apps
APP_NAMES = {
    # Productivity
    "com.android.chrome": "Chrome",
    "com.google.android.apps.docs": "Google Docs",
    "com.google.android.apps.docs.editors.sheets": "Google Sheets",
    "com.google.android.apps.docs.editors.slides": "Google Slides",
    "com.github.android": "GitHub",
    "com.microsoft.office.word": "Word",
    "com.microsoft.office.excel": "Excel",
    "com.slack": "Slack",
    "notion.id": "Notion",
    "com.todoist": "Todoist",
    "md.obsidian": "Obsidian",
    "com.termux": "Termux",
    "com.google.android.keep": "Google Keep",

    # Communication
    "org.telegram.messenger": "Telegram",
    "com.whatsapp": "WhatsApp",
    "com.google.android.gm": "Gmail",
    "com.microsoft.office.outlook": "Outlook",
    "com.google.android.apps.messaging": "Messages",
    "com.discord": "Discord",
    "us.zoom.videomeetings": "Zoom",
    "org.thoughtcrime.securesms": "Signal",

    # Social
    "com.instagram.android": "Instagram",
    "com.twitter.android": "Twitter/X",
    "com.facebook.katana": "Facebook",
    "com.reddit.frontpage": "Reddit",
    "com.linkedin.android": "LinkedIn",
    "com.zhiliaoapp.musically": "TikTok",
    "com.snapchat.android": "Snapchat",
    "com.threads.android": "Threads",

    # Entertainment
    "com.google.android.youtube": "YouTube",
    "com.netflix.mediaclient": "Netflix",
    "com.spotify.music": "Spotify",
    "tv.twitch.android.app": "Twitch",
    "com.amazon.avod.thirdpartyclient": "Prime Video",
    "com.disney.disneyplus": "Disney+",
    "com.supercell.clashroyale": "Clash Royale",

    # Utility / System
    "com.android.settings": "Settings",
    "com.android.calculator2": "Calculator",
    "com.sec.android.app.popupcalculator": "Calculator",
    "com.google.android.deskclock": "Clock",
    "com.sec.android.app.clockpackage": "Clock",
    "com.android.vending": "Google Play Store",
    "com.google.android.apps.nbu.files": "Files by Google"
}

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
    "com.sec.android.app.popupcalculator": "Utility",
    "com.google.android.deskclock": "Utility",
    "com.sec.android.app.clockpackage": "Utility",
    "com.android.vending": "Utility",
    "com.google.android.apps.nbu.files": "Utility"
}


def categorize_package_name(package_name: str) -> str:
    """Resolves package name to one of 6 contract-defined categories."""
    if not package_name:
        return "Other"
    if package_name in CATEGORIES:
        return CATEGORIES[package_name]
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



def resolve_app_name(package_name: str) -> str:
    """Translates package name to human-readable application title."""
    if not package_name:
        return "Unknown App"
    if package_name in APP_NAMES:
        return APP_NAMES[package_name]
    
    parts = package_name.split(".")
    raw = parts[-1] if parts else package_name
    return raw.replace("_", " ").title()


def format_duration(seconds: int) -> str:
    """Formats duration in seconds to human-readable strings like '25 min' or '45s'."""
    sec = max(0, int(seconds))
    if sec < 60:
        return f"{sec}s"
    mins = sec // 60
    rem_sec = sec % 60
    if rem_sec == 0 or mins >= 10:
        return f"{mins} min"
    return f"{mins}m {rem_sec}s"


def format_time_hh_mm(timestamp_ms: int) -> str:
    """Formats epoch timestamp in ms to local 'HH:MM' string."""
    t = time.localtime(timestamp_ms / 1000.0)
    return time.strftime("%H:%M", t)


class AppUsageRecord:
    """Represents a single continuous session spent in an application."""

    def __init__(
        self,
        package_name: str,
        app_name: str,
        app_category: str,
        start_time_ms: int,
        duration_seconds: int = 0
    ):
        self.package_name = package_name
        self.app_name = app_name
        self.app_category = app_category
        self.start_time_ms = int(start_time_ms)
        self.duration_seconds = max(0, int(duration_seconds))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.start_time_ms,
            "packageName": self.package_name,
            "appName": self.app_name,
            "appCategory": self.app_category,
            "durationSeconds": self.duration_seconds,
            "formattedTime": format_duration(self.duration_seconds),
            "timeStr": format_time_hh_mm(self.start_time_ms),
            "device": "LAPTOP"
        }


class AppUsageTracker:
    """
    Monitors Android foreground app transitions, calculates active elapsed duration,
    and maintains chronological app timeline and summary statistics.
    """

    def __init__(
        self,
        history_file: Any = "DEFAULT",
        min_session_seconds: int = 2,
        poll_interval: float = 1.0
    ):
        self.min_session_seconds = min_session_seconds
        self.poll_interval = poll_interval
        if history_file == "DEFAULT":
            self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_usage_history.json")
        else:
            self.history_file = history_file
        
        self.current_package: Optional[str] = None
        self.current_app_name: Optional[str] = None
        self.current_category: Optional[str] = None
        self.current_start_time: Optional[float] = None
        
        self.timeline: List[Dict[str, Any]] = []
        self._tracking_active = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Load persisted history if file configured
        if self.history_file:
            self.load_history()

    def categorize_package(self, package_name: str) -> str:
        """Categorizes package into contract-defined category buckets."""
        return categorize_package_name(package_name)

    def is_system_window(self, raw_line: str, package_name: Optional[str]) -> bool:
        """Detects whether a window or package belongs to system UI or launcher."""
        if not raw_line and not package_name:
            return True
        for kw in SYSTEM_WINDOW_KEYWORDS:
            if kw in (raw_line or ""):
                return True
        if package_name and package_name in SYSTEM_PACKAGES:
            return True
        return False

    def parse_focus_info(self, dumpsys_output: str) -> Tuple[Optional[str], bool, str]:
        """
        Parses dumpsys output to extract (package_name, is_system, raw_focus_line).
        """
        if not dumpsys_output:
            return None, True, ""
        
        focus_line = ""
        for line in dumpsys_output.splitlines():
            if "mCurrentFocus" in line:
                focus_line = line.strip()
                break
        
        # Check system markers in focus line
        for kw in SYSTEM_WINDOW_KEYWORDS:
            if kw in focus_line:
                return None, True, focus_line

        # Extract package with slash
        parts = focus_line.split()
        pkg = None
        for p in parts:
            if "/" in p:
                candidate = p.split("/")[0].replace("}", "").replace("{", "").strip()
                if "." in candidate and not candidate.startswith("/"):
                    pkg = candidate
                    break

        if not pkg:
            return None, True, focus_line

        if pkg in SYSTEM_PACKAGES:
            return pkg, True, focus_line

        return pkg, False, focus_line

    def record_transition(
        self,
        package_name: str,
        duration_seconds: int,
        timestamp_ms: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Manually or programmatically records an app session into the timeline.
        Ignores sessions shorter than min_session_seconds (default: 2s).
        """
        if duration_seconds < self.min_session_seconds:
            return None

        now_ms = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
        app_name = resolve_app_name(package_name)
        category = self.categorize_package(package_name)

        record = AppUsageRecord(
            package_name=package_name,
            app_name=app_name,
            app_category=category,
            start_time_ms=now_ms,
            duration_seconds=duration_seconds
        ).to_dict()

        with self._lock:
            self.timeline.append(record)
            self.save_history()

        return record

    def poll_once(self) -> Optional[str]:
        """
        Executes one instantaneous check against the connected Android device via ADB.
        Updates active duration and records transitions when the foreground app changes.
        """
        from context_capture import find_adb_path
        adb_bin = find_adb_path()
        try:
            cmd = [adb_bin, "shell", "dumpsys", "window"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            if proc.returncode != 0:
                return None
            dumpsys_out = proc.stdout
        except Exception:
            return None

        pkg, is_system, focus_line = self.parse_focus_info(dumpsys_out)
        now = time.time()

        with self._lock:
            if is_system or not pkg:
                # Switched to system overlay, home launcher, or locked screen
                if self.current_package is not None and self.current_start_time is not None:
                    elapsed = int(now - self.current_start_time)
                    if elapsed >= self.min_session_seconds:
                        self.record_transition(
                            package_name=self.current_package,
                            duration_seconds=elapsed,
                            timestamp_ms=int(self.current_start_time * 1000)
                        )
                    self.current_package = None
                    self.current_app_name = None
                    self.current_category = None
                    self.current_start_time = None
                return None

            # It's a genuine user app
            if pkg != self.current_package:
                # Transition occurred from a previous app
                if self.current_package is not None and self.current_start_time is not None:
                    elapsed = int(now - self.current_start_time)
                    if elapsed >= self.min_session_seconds:
                        self.record_transition(
                            package_name=self.current_package,
                            duration_seconds=elapsed,
                            timestamp_ms=int(self.current_start_time * 1000)
                        )

                # Initialize new app session
                self.current_package = pkg
                self.current_app_name = resolve_app_name(pkg)
                self.current_category = self.categorize_package(pkg)
                self.current_start_time = now

            return self.current_package

    def start_tracking(self):
        """Starts background monitoring thread polling approximately once per second."""
        if self._tracking_active:
            return
        self._tracking_active = True
        
        def _loop():
            while self._tracking_active:
                try:
                    self.poll_once()
                except Exception:
                    pass
                time.sleep(self.poll_interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_tracking(self):
        """Stops background thread and flushes active app session if duration >= 2s."""
        self._tracking_active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        with self._lock:
            if self.current_package is not None and self.current_start_time is not None:
                elapsed = int(time.time() - self.current_start_time)
                if elapsed >= self.min_session_seconds:
                    self.record_transition(
                        package_name=self.current_package,
                        duration_seconds=elapsed,
                        timestamp_ms=int(self.current_start_time * 1000)
                    )
                self.current_package = None
                self.current_start_time = None

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Returns chronological list of app usage transitions."""
        with self._lock:
            return list(self.timeline)

    def get_summary(self) -> List[Dict[str, Any]]:
        """
        Aggregates total duration spent in each app, sorted descending.
        Computes percentage share of total active time.
        """
        with self._lock:
            totals: Dict[str, Dict[str, Any]] = {}
            grand_total = 0

            for entry in self.timeline:
                app = entry["appName"]
                dur = entry["durationSeconds"]
                cat = entry["appCategory"]
                grand_total += dur

                if app not in totals:
                    totals[app] = {
                        "appName": app,
                        "category": cat,
                        "durationSeconds": 0
                    }
                totals[app]["durationSeconds"] += dur

            summary = list(totals.values())
            summary.sort(key=lambda x: x["durationSeconds"], reverse=True)

            for item in summary:
                item["formattedTime"] = format_duration(item["durationSeconds"])
                item["percentage"] = round((item["durationSeconds"] / grand_total * 100)) if grand_total > 0 else 0
                item["device"] = "LAPTOP"

            return summary

    def get_category_summary(self) -> Dict[str, int]:
        """Returns cumulative seconds per category."""
        with self._lock:
            cat_totals: Dict[str, int] = {}
            for entry in self.timeline:
                cat = entry["appCategory"]
                cat_totals[cat] = cat_totals.get(cat, 0) + entry["durationSeconds"]
            return cat_totals

    def get_app_usage_payload(self) -> Dict[str, Any]:
        """Bundles complete summary, category breakdown, and timeline for Office Kit synchronization."""
        with self._lock:
            summary = self.get_summary()
            timeline = []
            for entry in self.timeline:
                item = dict(entry)
                if "device" not in item:
                    item["device"] = "LAPTOP"
                timeline.append(item)
            categories = self.get_category_summary()
            total_sec = sum(item["durationSeconds"] for item in summary)
            return {
                "device": "LAPTOP",
                "summary": summary,
                "categoryBreakdown": categories,
                "timeline": timeline,
                "totalDurationSeconds": total_sec,
                "formattedTotal": format_duration(total_sec)
            }

    def save_history(self, file_path: Optional[str] = None):
        """Persists timeline to JSON file."""
        target = file_path or self.history_file
        if not target:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.timeline, f, indent=2)
        except Exception as e:
            pass

    def load_history(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Loads historical timeline from JSON file if available."""
        target = file_path or self.history_file
        if target and os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        with self._lock:
                            self.timeline = loaded
                        return loaded
            except Exception:
                pass
        return []

    def clear_history(self):
        """Resets in-memory timeline and clears the local history file."""
        with self._lock:
            self.timeline = []
            if self.history_file and os.path.exists(self.history_file):
                try:
                    os.remove(self.history_file)
                except Exception:
                    pass
