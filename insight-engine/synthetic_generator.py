"""
Synthetic Task & Context Signal Data Generator for iQOO Productivity Track
Generates 5-7 days of realistic user task history and context signals with detectable patterns:
- Morning (09:00 - 11:30 AM): Coding clusters in Home Office, high completion, long focus.
- Afternoon (after 03:00 PM): Writing sessions in Cafe abandoned/delayed (procrastination trigger).
- Context Signals: Extended screen-on time (>2h) in afternoon + Social/Entertainment interruptions.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any

def generate_synthetic_tasks_and_signals(days: int = 7) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    tasks = []
    signals = []
    base_date = datetime.now() - timedelta(days=days)

    task_templates = [
        # Morning Coding session (Consistent success in Home Office)
        {"hour": 9, "minute": 15, "title": "Refactor Data Pipeline", "type": "coding", "loc": "Home Office", "priority": "high", "dur": 3600, "completed": True},
        {"hour": 10, "minute": 30, "title": "Implement Unit Tests", "type": "coding", "loc": "Home Office", "priority": "medium", "dur": 2700, "completed": True},
        # Mid-day Meeting
        {"hour": 13, "minute": 0, "title": "Sprint Sync", "type": "meeting", "loc": "Meeting Room", "priority": "medium", "dur": 1800, "completed": True},
        # Afternoon Writing session (Procrastination / Fail pattern in Cafe)
        {"hour": 15, "minute": 30, "title": "Draft Technical Proposal", "type": "writing", "loc": "Cafe", "priority": "high", "dur": 900, "completed": False},
        {"hour": 16, "minute": 45, "title": "Documentation Updates", "type": "writing", "loc": "Cafe", "priority": "low", "dur": 600, "completed": False},
        # Evening Planning
        {"hour": 18, "minute": 0, "title": "Plan Tomorrow Goals", "type": "planning", "loc": "Home Office", "priority": "low", "dur": 900, "completed": True},
    ]

    signal_templates = [
        # Morning: Productivity in Home Office, healthy screen pacing
        {"hour": 9, "minute": 0, "appCategory": "Productivity", "loc": "Home Office", "screenSec": 1800},
        {"hour": 10, "minute": 15, "appCategory": "Productivity", "loc": "Home Office", "screenSec": 3600},
        {"hour": 13, "minute": 0, "appCategory": "Communication", "loc": "Meeting Room", "screenSec": 2100},
        # Afternoon: Social / Entertainment intrusion + prolonged continuous screen strain
        {"hour": 15, "minute": 20, "appCategory": "Social", "loc": "Cafe", "screenSec": 7500},
        {"hour": 16, "minute": 40, "appCategory": "Entertainment", "loc": "Cafe", "screenSec": 8200},
        # Evening: Reset
        {"hour": 18, "minute": 0, "appCategory": "Productivity", "loc": "Home Office", "screenSec": 1200}
    ]

    for day_offset in range(days):
        current_day = base_date + timedelta(days=day_offset)

        for tpl in task_templates:
            created_dt = current_day.replace(hour=tpl["hour"], minute=tpl["minute"], second=0, microsecond=0)
            created_at = int(created_dt.timestamp() * 1000)
            completed_at = int((created_dt + timedelta(seconds=tpl["dur"])).timestamp() * 1000) if tpl["completed"] else None

            task = {
                "id": str(uuid.uuid4()),
                "title": f"{tpl['title']} (Day {day_offset + 1})",
                "type": tpl["type"],
                "createdAt": created_at,
                "completedAt": completed_at,
                "duration": tpl["dur"] if tpl["completed"] else int(tpl["dur"] * 0.3),
                "location": tpl["loc"],
                "priority": tpl["priority"]
            }
            tasks.append(task)

        for stpl in signal_templates:
            s_dt = current_day.replace(hour=stpl["hour"], minute=stpl["minute"], second=0, microsecond=0)
            signals.append({
                "timestamp": int(s_dt.timestamp() * 1000),
                "appCategory": stpl["appCategory"],
                "location": stpl["loc"],
                "screenOnDuration": stpl["screenSec"]
            })

    return tasks, signals

def generate_synthetic_tasks(days: int = 7) -> List[Dict[str, Any]]:
    tasks, _ = generate_synthetic_tasks_and_signals(days=days)
    return tasks

if __name__ == "__main__":
    import os
    tasks, signals = generate_synthetic_tasks_and_signals(days=7)
    base_dir = os.path.dirname(__file__)

    sample_tasks_path = os.path.join(base_dir, "sample_data.json")
    with open(sample_tasks_path, "w") as f:
        json.dump(tasks, f, indent=2)

    sample_signals_path = os.path.join(base_dir, "sample_context_signals.json")
    with open(sample_signals_path, "w") as f:
        json.dump(signals, f, indent=2)

    print(f"Successfully generated {len(tasks)} tasks and {len(signals)} context signals.")
