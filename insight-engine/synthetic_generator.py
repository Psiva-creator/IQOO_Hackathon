"""
Synthetic Task Data Generator for iQOO Productivity Track
Generates 5-7 days of realistic user task history with detectable patterns:
- Morning (09:00 - 11:30 AM): Coding clusters, high completion, long focus.
- Afternoon (after 03:00 PM): Writing sessions abandoned/delayed (procrastination trigger).
- Location: Home Office has highest focus efficiency.
"""

import json
import uuid
from datetime import datetime, timedelta

def generate_synthetic_tasks(days: int = 7) -> list:
    tasks = []
    base_date = datetime.now() - timedelta(days=days)

    task_templates = [
        # Morning Coding session (Consistent success)
        {"hour": 9, "minute": 15, "title": "Refactor Data Pipeline", "type": "coding", "loc": "Home Office", "priority": "high", "dur": 3600, "completed": True},
        {"hour": 10, "minute": 30, "title": "Implement Unit Tests", "type": "coding", "loc": "Home Office", "priority": "medium", "dur": 2700, "completed": True},
        # Mid-day Meeting
        {"hour": 13, "minute": 0, "title": "Sprint Sync", "type": "meeting", "loc": "Meeting Room", "priority": "medium", "dur": 1800, "completed": True},
        # Afternoon Writing session (Procrastination / Fail pattern)
        {"hour": 15, "minute": 30, "title": "Draft Technical Proposal", "type": "writing", "loc": "Cafe", "priority": "high", "dur": 900, "completed": False},
        {"hour": 16, "minute": 45, "title": "Documentation Updates", "type": "writing", "loc": "Cafe", "priority": "low", "dur": 600, "completed": False},
        # Evening Planning
        {"hour": 18, "minute": 0, "title": "Plan Tomorrow Goals", "type": "planning", "loc": "Home Office", "priority": "low", "dur": 900, "completed": True},
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

    return tasks

if __name__ == "__main__":
    synthetic_tasks = generate_synthetic_tasks(days=7)
    with open("sample_data.json", "w") as f:
        json.dump(synthetic_tasks, f, indent=2)
    print(f"Successfully generated {len(synthetic_tasks)} synthetic tasks in sample_data.json")
