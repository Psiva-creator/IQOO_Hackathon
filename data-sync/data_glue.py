"""
Data Layer Glue Module
Integrates:
1. Member A's stored task list
2. Member C's live context signals
3. Member B's insight analytics engine
4. Office Kit bridge sync export
"""

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "insight-engine")))
from engine import InsightEngine
from context_capture import ContextCapture

def run_pipeline(task_file_path: str = None) -> dict:
    if task_file_path and os.path.exists(task_file_path):
        with open(task_file_path) as f:
            tasks = json.load(f)
    else:
        # Fallback to sample data from insight-engine
        fallback = os.path.join(os.path.dirname(__file__), "..", "insight-engine", "sample_data.json")
        if os.path.exists(fallback):
            with open(fallback) as f:
                tasks = json.load(f)
        else:
            tasks = []

    # 1. Capture current device context
    capture = ContextCapture()
    current_context = capture.capture_current_signal()

    # 2. Run on-device insight engine
    engine = InsightEngine(tasks)
    insights = engine.analyze()

    # 3. Augment insights with live device context
    pipeline_result = {
        "insights": insights,
        "activeContext": current_context,
        "taskCount": len(tasks)
    }

    return pipeline_result

if __name__ == "__main__":
    result = run_pipeline()
    print("Pipeline Output (Glue Execution):")
    print(json.dumps(result, indent=2))
