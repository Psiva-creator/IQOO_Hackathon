"""
Foreground App / Context Capture Module
Simulates and bridges Android UsageStatsManager signals for on-device context awareness.
Collects: active app category, timestamp, location, and continuous screen-on duration.
"""

import time
from typing import Dict, Any

class ContextCapture:
    CATEGORIES = {
        "com.android.chrome": "Productivity",
        "com.github.android": "Productivity",
        "org.telegram.messenger": "Communication",
        "com.whatsapp": "Communication",
        "com.instagram.android": "Social",
        "com.google.android.youtube": "Entertainment",
        "com.google.android.apps.docs": "Productivity"
    }

    def __init__(self, location: str = "Home Office"):
        self.current_location = location
        self.screen_on_start = time.time()

    def capture_current_signal(self, package_name: str = "com.android.chrome") -> Dict[str, Any]:
        category = self.CATEGORIES.get(package_name, "Utility")
        now_ms = int(time.time() * 1000)
        screen_on_sec = int(time.time() - self.screen_on_start)

        return {
            "timestamp": now_ms,
            "appCategory": category,
            "location": self.current_location,
            "screenOnDuration": screen_on_sec
        }

    def reset_screen_session(self):
        self.screen_on_start = time.time()

if __name__ == "__main__":
    capture = ContextCapture(location="Home Office")
    print("Simulated Context Signal:")
    import json
    print(json.dumps(capture.capture_current_signal(), indent=2))
