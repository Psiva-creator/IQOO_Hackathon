"""
Data Layer Glue Module
Integrates:
1. Member A's stored task list (Room DB export or demo_tasks.json)
2. Member C's live and historical context signals (context_capture.py or sample_context_signals.json)
3. Member B's insight analytics engine (InsightEngine with full multi-factor correlation)
4. Office Kit bridge cross-device synchronization export
"""

import sys
import os
import json
import time
import argparse
from typing import Dict, Any, List, Optional

# Add insight-engine and local data-sync to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INSIGHT_ENGINE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "insight-engine"))
APP_UI_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "app-ui"))

if INSIGHT_ENGINE_DIR not in sys.path:
    sys.path.append(INSIGHT_ENGINE_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from engine import InsightEngine
from context_capture import ContextCapture
from app_usage_tracker import AppUsageTracker
import office_kit_bridge


def resolve_task_data(task_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Resolves task records from user path, app-ui assets, or insight-engine samples."""
    candidate_paths = []
    if task_file_path:
        candidate_paths.append(task_file_path)
    
    # Priority fallbacks
    candidate_paths.extend([
        os.path.join(APP_UI_DIR, "src", "main", "assets", "demo_tasks.json"),
        os.path.join(INSIGHT_ENGINE_DIR, "sample_data.json")
    ])

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    if isinstance(tasks, list):
                        return tasks
            except Exception as e:
                print(f"Warning: Failed to load tasks from {path}: {e}")
    return []


def resolve_context_signals(signal_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Resolves context signals from user path, sample signals, or active capture buffer."""
    candidate_paths = []
    if signal_file_path:
        candidate_paths.append(signal_file_path)
    
    candidate_paths.extend([
        os.path.join(INSIGHT_ENGINE_DIR, "sample_context_signals.json")
    ])

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    signals = json.load(f)
                    if isinstance(signals, list):
                        return signals
            except Exception as e:
                print(f"Warning: Failed to load context signals from {path}: {e}")

    # Fallback to in-memory generator
    capture = ContextCapture()
    capture.record_signal("com.android.chrome", screen_on_duration=1800)
    capture.record_signal("com.whatsapp", screen_on_duration=2400)
    return capture.get_signal_buffer()


def resolve_app_usage_data(app_usage_path: Optional[str] = None) -> Dict[str, Any]:
    """Resolves app usage history and timeline from user path, live history, or sample file."""
    candidate_paths = []
    if app_usage_path:
        candidate_paths.append(app_usage_path)

    candidate_paths.extend([
        os.path.join(CURRENT_DIR, "app_usage_history.json"),
        os.path.join(CURRENT_DIR, "sample_app_usage.json")
    ])

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                tracker = AppUsageTracker(history_file=path)
                if tracker.timeline:
                    return tracker.get_app_usage_payload()
            except Exception as e:
                print(f"Warning: Failed to load app usage from {path}: {e}")

    # Fallback to in-memory generator
    tracker = AppUsageTracker(history_file=None)
    tracker.record_transition("com.android.chrome", duration_seconds=1500)
    tracker.record_transition("com.google.android.youtube", duration_seconds=1080)
    tracker.record_transition("com.whatsapp", duration_seconds=720)
    return tracker.get_app_usage_payload()


def run_pipeline(
    task_file_path: Optional[str] = None,
    signal_file_path: Optional[str] = None,
    app_usage_file_path: Optional[str] = None,
    sync_to_bridge: bool = True,
    bridge_host: str = "localhost",
    bridge_port: int = 8089
) -> Dict[str, Any]:
    """
    Executes the end-to-end data glue pipeline:
    1. Loads tasks and context signals
    2. Captures real-time device context
    3. Runs on-device InsightEngine with multi-factor fatigue & distraction correlation
    4. Automatically dispatches computed insights and app usage to Office Kit companion bridge
    """
    start_time = time.perf_counter()

    # 1. Ingest Task data
    tasks = resolve_task_data(task_file_path)

    # 2. Ingest Context Signal data
    context_signals = resolve_context_signals(signal_file_path)

    # 3. Capture current live device context snapshot
    capture = ContextCapture()
    current_context = capture.capture_current_signal()

    # 4. Run On-Device Insight Engine with BOTH tasks and context signals
    engine = InsightEngine(tasks=tasks, context_signals=context_signals)
    insights = engine.analyze()

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 5. Push to Office Kit Bridge if requested (including app usage & timeline)
    app_usage = resolve_app_usage_data(app_usage_file_path)
    synced = False
    if sync_to_bridge:
        sync_payload = dict(insights)
        if app_usage:
            sync_payload["appUsage"] = app_usage
        synced = office_kit_bridge.push_to_bridge(sync_payload, host=bridge_host, port=bridge_port)

    pipeline_result = {
        "insights": insights,
        "appUsage": app_usage,
        "activeContext": current_context,
        "taskCount": len(tasks),
        "signalCount": len(context_signals),
        "latencyMs": elapsed_ms,
        "syncedToBridge": synced
    }

    return pipeline_result


def run_benchmark(iterations: int = 10) -> Dict[str, float]:
    """Measures pipeline inference speed to guarantee compliance with < 150ms hardware budget."""
    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        run_pipeline(sync_to_bridge=False)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)
    min_ms = min(latencies)

    print(f"[PERF] Performance Benchmark ({iterations} iterations):")
    print(f"   Avg Latency: {avg_ms:.2f} ms")
    print(f"   Min Latency: {min_ms:.2f} ms")
    print(f"   Max Latency: {max_ms:.2f} ms")
    print(f"   Hardware Target (<150ms): {'PASSED' if max_ms < 150 else 'FAILED'}")

    return {"avgMs": avg_ms, "minMs": min_ms, "maxMs": max_ms}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="iQOO Hackathon Data Layer Glue Pipeline")
    parser.add_argument("--tasks", type=str, default=None, help="Path to task JSON file")
    parser.add_argument("--signals", type=str, default=None, help="Path to context signal JSON file")
    parser.add_argument("--no-sync", action="store_true", help="Disable Office Kit bridge push")
    parser.add_argument("--bridge-host", type=str, default="localhost", help="Office Kit bridge host")
    parser.add_argument("--bridge-port", type=int, default=8089, help="Office Kit bridge port")
    parser.add_argument("--benchmark", action="store_true", help="Run latency benchmark suite")

    args = parser.parse_args()

    if args.benchmark:
        run_benchmark(iterations=20)
    else:
        res = run_pipeline(
            task_file_path=args.tasks,
            signal_file_path=args.signals,
            sync_to_bridge=not args.no_sync,
            bridge_host=args.bridge_host,
            bridge_port=args.bridge_port
        )
        print("Pipeline Execution Complete:")
        print(json.dumps(res, indent=2))
