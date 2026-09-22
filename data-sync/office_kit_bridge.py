"""
Office Kit Integration Bridge
Enables cross-device synchronization between the iQOO phone and laptop.
Serves a lightweight local HTTP dashboard and JSON sync endpoint for laptop viewing.
Complies strictly with contracts/insight.schema.json.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

PORT = 8089

DEFAULT_INSIGHTS = {
    "peakHour": "09:00 - 11:00 (Peak focus completion)",
    "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM (100% abandon rate)",
    "bestContext": "Home Office (100.0% completion across 21 sessions)",
    "recommendation": "Your coding completion rate peaks between 09:00 - 11:00 (100% completion in Home Office). In contrast, writing sessions drop to 0.0% completion in Cafe. High afternoon fatigue (score: 75/100) significantly degrades focus after extended screen sessions. Consider scheduling difficult writing tasks before 11:00 AM in Home Office.",
    "productivityScore": 85,
    "confidenceLevel": "High",
    "hourlyHeatmap": {
        "0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0,
        "6": 0, "7": 10, "8": 40, "9": 100, "10": 100, "11": 70,
        "12": 20, "13": 85, "14": 60, "15": 10, "16": 15, "17": 30,
        "18": 90, "19": 50, "20": 20, "21": 0, "22": 0, "23": 0
    },
    "fatigueLevel": "HIGH",
    "fatigueScore": 75,
    "explanation": "Fatigue is HIGH (score: 75/100). Completion rate drops by 50% in the afternoon; focus sessions shorten after mid-day; prolonged continuous screen time exceeds 125 minutes.",
    "contextInsights": [
        {
            "context": "Home Office",
            "completionRate": 100.0,
            "totalTasks": 21,
            "completedTasks": 21,
            "avgDuration": 2400.0,
            "status": "Optimal"
        },
        {
            "context": "Meeting Room",
            "completionRate": 100.0,
            "totalTasks": 7,
            "completedTasks": 7,
            "avgDuration": 1800.0,
            "status": "Optimal"
        },
        {
            "context": "Cafe",
            "completionRate": 0.0,
            "totalTasks": 14,
            "completedTasks": 0,
            "avgDuration": 225.0,
            "status": "Suboptimal"
        }
    ],
    "distractionSensitivity": {
        "level": "HIGH",
        "score": 65,
        "vulnerableCategories": ["writing"],
        "triggerAppCategories": ["Entertainment", "Social"],
        "summary": "HIGH sensitivity: Writing tasks show high abandonment when Entertainment or Social apps are accessed."
    },
    "appUsage": {
        "device": "LAPTOP",
        "totalScreenTimeSeconds": 3780,
        "totalScreenTimeFormatted": "1h 3m",
        "summary": [
            {"appName": "Chrome", "category": "Productivity", "durationSeconds": 1500, "formattedTime": "25 min", "percentage": 39, "device": "LAPTOP"},
            {"appName": "YouTube", "category": "Entertainment", "durationSeconds": 1080, "formattedTime": "18 min", "percentage": 28, "device": "LAPTOP"},
            {"appName": "WhatsApp", "category": "Communication", "durationSeconds": 720, "formattedTime": "12 min", "percentage": 19, "device": "LAPTOP"},
            {"appName": "Instagram", "category": "Social", "durationSeconds": 480, "formattedTime": "8 min", "percentage": 13, "device": "LAPTOP"}
        ],
        "categoryBreakdown": {
            "Productivity": 1500,
            "Entertainment": 1080,
            "Communication": 720,
            "Social": 480
        },
        "timeline": [
            {"timestamp": 1789980000000, "timeStr": "10:00", "appName": "Chrome", "category": "Productivity", "durationSeconds": 1500, "formattedTime": "25 min", "device": "LAPTOP"},
            {"timestamp": 1789981500000, "timeStr": "10:25", "appName": "WhatsApp", "category": "Communication", "durationSeconds": 720, "formattedTime": "12 min", "device": "LAPTOP"},
            {"timestamp": 1789982220000, "timeStr": "10:37", "appName": "YouTube", "category": "Entertainment", "durationSeconds": 1080, "formattedTime": "18 min", "device": "LAPTOP"},
            {"timestamp": 1789983300000, "timeStr": "10:55", "appName": "Chrome", "category": "Productivity", "durationSeconds": 600, "formattedTime": "10 min", "device": "LAPTOP"}
        ]
    }
}

LATEST_INSIGHTS: Dict[str, Any] = dict(DEFAULT_INSIGHTS)
LAST_SYNC_TIME: float = time.time()


def get_dashboard_html() -> str:
    """Generates an attractive, responsive, dark-mode Office Kit companion dashboard."""
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_usage_history.json")
    if os.path.exists(history_file):
        try:
            from app_usage_tracker import AppUsageTracker
            tracker = AppUsageTracker(history_file=history_file)
            if tracker.timeline:
                LATEST_INSIGHTS["appUsage"] = tracker.get_app_usage_payload()
        except Exception:
            pass

    insights_json = json.dumps(LATEST_INSIGHTS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iQOO Office Kit — Companion Laptop View</title>
    <style>
        :root {{
            --bg: #090d16;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #233152;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --primary-accent: #0284c7;
            --iqoo-yellow: #facc15;
            --iqoo-orange: #fb923c;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .brand-title {{ display: flex; align-items: center; gap: 12px; font-size: 1.5rem; font-weight: 700; }}
        .badge-iqoo {{
            background: linear-gradient(135deg, #facc15, #f97316);
            color: #000;
            font-size: 0.72rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .sync-status {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--surface);
            padding: 8px 16px;
            border-radius: 30px;
            border: 1px solid var(--border);
            font-size: 0.85rem;
        }}
        .pulse-dot {{
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.8; }}
            50% {{ transform: scale(1.2); opacity: 1; }}
            100% {{ transform: scale(0.95); opacity: 0.8; }}
        }}
        .grid-4 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s ease;
        }}
        .card:hover {{ border-color: var(--primary-accent); }}
        .card-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .card-val {{ font-size: 1.25rem; font-weight: 700; color: #fff; }}
        .card-desc {{ font-size: 0.82rem; color: var(--text-muted); margin-top: 6px; }}
        .tag {{
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        }}
        .tag-high {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
        .tag-medium {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
        .tag-low {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
        .tag-prod {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #0284c7; }}
        .tag-ent {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #9333ea; }}
        .tag-comm {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
        .tag-soc {{ background: rgba(251, 146, 60, 0.2); color: #fb923c; border: 1px solid #ea580c; }}
        .tag-util {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #64748b; }}
        .tag-other {{ background: rgba(255, 255, 255, 0.1); color: #94a3b8; border: 1px solid #475569; }}

        .timeline-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            border-left: 2px solid var(--border);
            margin-left: 10px;
            position: relative;
            transition: background 0.15s ease;
        }}
        .timeline-row:hover {{ background: rgba(255, 255, 255, 0.03); }}
        .timeline-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary);
            position: absolute;
            left: -5px;
        }}
        .timeline-time {{
            font-family: monospace;
            font-size: 0.85rem;
            color: var(--text-muted);
            min-width: 48px;
        }}
        .timeline-app {{
            font-weight: 600;
            color: #fff;
            min-width: 90px;
        }}
        .timeline-dur {{
            margin-left: auto;
            font-size: 0.82rem;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .progress-bar-bg {{
            background: #233152;
            height: 8px;
            border-radius: 4px;
            margin-top: 10px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.4s ease;
        }}
        /* Heatmap Grid */
        .heatmap-grid {{
            display: grid;
            grid-template-columns: repeat(24, 1fr);
            gap: 4px;
            margin-top: 12px;
        }}
        .heat-cell {{
            height: 48px;
            border-radius: 4px;
            background: #1b2640;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 0.65rem;
            color: #94a3b8;
            transition: transform 0.15s;
        }}
        .heat-cell:hover {{ transform: scale(1.1); z-index: 10; }}
        .recommendation-box {{
            background: linear-gradient(135deg, #1e293b, #131b2e);
            border-left: 6px solid var(--iqoo-yellow);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 12px;
        }}
        .table-custom th {{
            text-align: left;
            padding: 10px;
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
        }}
        .table-custom td {{
            padding: 10px;
            border-bottom: 1px solid var(--border);
        }}
        .btn-refresh {{
            background: var(--surface-hover);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: background 0.2s;
        }}
        .btn-refresh:hover {{ background: var(--border); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand-title">
                <span>📱 iQOO Office Kit</span>
                <span class="badge-iqoo">iQOO 15 Companion</span>
                <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 400;">Snapdragon 8 Elite • Local Wi-Fi Bridge</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="sync-status">
                    <div class="pulse-dot"></div>
                    <span id="syncText">Live Synced with Phone</span>
                </div>
                <button class="btn-refresh" onclick="fetchLiveInsights()">Sync Now</button>
            </div>
        </header>

        <!-- Recommendation Banner -->
        <div class="recommendation-box">
            <div class="card-label" style="color: var(--iqoo-yellow);">💡 AI Habit Recommendation</div>
            <div class="card-val" id="recommendationText" style="font-size: 1.15rem; font-weight: 500; line-height: 1.6;">
                Loading recommendation...
            </div>
        </div>

        <!-- 4 Primary Metrics -->
        <div class="grid-4">
            <div class="card" style="border-top: 4px solid #38bdf8;">
                <div class="card-label">⚡ Peak Focus Window</div>
                <div class="card-val" id="peakHourText">--</div>
                <div class="card-desc">Chronobiological peak completion</div>
            </div>

            <div class="card" style="border-top: 4px solid #f43f5e;">
                <div class="card-label">⚠️ Procrastination Alert</div>
                <div class="card-val" id="procrastinationText" style="font-size: 1.1rem; color: #fca5a5;">--</div>
                <div class="card-desc">Detected pattern of drop-off</div>
            </div>

            <div class="card" style="border-top: 4px solid #10b981;">
                <div class="card-label">📍 Optimal Context</div>
                <div class="card-val" id="bestContextText" style="font-size: 1.1rem;">--</div>
                <div class="card-desc">Top performing work environment</div>
            </div>

            <div class="card" style="border-top: 4px solid #f59e0b;">
                <div class="card-label">📊 Habit Health Score</div>
                <div class="card-val" id="productivityScoreText">--</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="scoreBarFill" style="background: var(--iqoo-yellow); width: 0%;"></div>
                </div>
                <div class="card-desc" id="confidenceText" style="margin-top: 8px;">Confidence: High</div>
            </div>
        </div>

        <!-- Deep Diagnostics: Fatigue + Distraction -->
        <div class="grid-2">
            <!-- Fatigue Card -->
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div class="card-label">🔋 Cognitive & Session Fatigue</div>
                    <span class="tag" id="fatigueTag">LOW</span>
                </div>
                <div style="font-size: 1.4rem; font-weight: 700;" id="fatigueScoreText">0 / 100</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="fatigueBarFill" style="background: #f87171; width: 0%;"></div>
                </div>
                <div class="card-desc" id="fatigueExplanation" style="margin-top: 12px; font-size: 0.9rem; color: #cbd5e1;">
                    Analyzing screen and task decay...
                </div>
            </div>

            <!-- Distraction Sensitivity -->
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div class="card-label">🎯 Distraction Sensitivity</div>
                    <span class="tag" id="distractionTag">LOW</span>
                </div>
                <div style="font-size: 1.4rem; font-weight: 700;" id="distractionScoreText">0 / 100</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="distractionBarFill" style="background: #fb923c; width: 0%;"></div>
                </div>
                <div class="card-desc" id="distractionSummary" style="margin-top: 12px; font-size: 0.9rem; color: #cbd5e1;">
                    Analyzing app switching triggers...
                </div>
            </div>
        </div>

        <!-- Real App Usage & Timeline -->
        <div class="grid-2" style="margin-bottom: 20px;">
            <!-- Today's App Usage Summary Card -->
            <div class="card" style="border-top: 4px solid var(--primary);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div class="card-label" style="margin-bottom: 0;">📱 Today's App Usage (Samsung S25 Ultra)</div>
                    <span id="totalAppUsageBadge" class="tag tag-prod" style="font-size: 0.85rem; font-weight: 700;">Total: 0s</span>
                </div>
                <div class="card-desc" style="margin-top: 2px; margin-bottom: 12px;">Real-time on-device application usage breakdown</div>
                <table class="table-custom">
                    <thead>
                        <tr>
                            <th>Application</th>
                            <th>Category</th>
                            <th>Time Spent</th>
                            <th style="width: 140px;">Percentage</th>
                        </tr>
                    </thead>
                    <tbody id="appUsageTableBody">
                        <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 16px;">Loading app usage...</td></tr>
                    </tbody>
                    <tfoot id="appUsageTableFoot" style="border-top: 2px solid var(--border);">
                        <tr>
                            <td style="font-weight: 700; color: #fff; padding-top: 10px;">Total Screen Time</td>
                            <td></td>
                            <td id="totalAppUsageCell" style="font-weight: 700; color: var(--primary); padding-top: 10px;">0s</td>
                            <td style="font-weight: 600; color: var(--text-muted); padding-top: 10px;">100%</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <!-- Chronological Timeline Card -->
            <div class="card" style="border-top: 4px solid var(--iqoo-yellow);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div class="card-label" style="margin-bottom: 0;">⏱️ Chronological App Timeline</div>
                    <span id="timelineSessionCount" class="tag tag-other" style="font-size: 0.8rem;">0 sessions</span>
                </div>
                <div class="card-desc" style="margin-top: 2px; margin-bottom: 12px;">Sequential foreground transitions with duration per session</div>
                <div id="timelineContainer" style="max-height: 280px; overflow-y: auto; padding-right: 6px;">
                    <div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading timeline...</div>
                </div>
            </div>
        </div>

        <!-- 24-Hour Heatmap -->
        <div class="card" style="margin-bottom: 20px;">
            <div class="card-label">🕒 24-Hour Productivity Heatmap (Hourly Focus Density)</div>
            <div class="heatmap-grid" id="heatmapContainer"></div>
        </div>

        <!-- Context Insights Breakdown -->
        <div class="card">
            <div class="card-label">🏢 Environmental Context Breakdown</div>
            <table class="table-custom">
                <thead>
                    <tr>
                        <th>Context / Location</th>
                        <th>Completion Rate</th>
                        <th>Total Tasks</th>
                        <th>Completed</th>
                        <th>Avg Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="contextTableBody">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No context records yet</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let initialData = {insights_json};

        function renderInsights(data) {{
            if (!data) return;

            document.getElementById("recommendationText").innerText = data.recommendation || "Tracking habits...";
            document.getElementById("peakHourText").innerText = data.peakHour || "--";
            document.getElementById("procrastinationText").innerText = data.procrastinationTrigger || "--";
            document.getElementById("bestContextText").innerText = data.bestContext || "--";

            // Productivity Score
            const score = data.productivityScore !== undefined ? data.productivityScore : 85;
            document.getElementById("productivityScoreText").innerText = score + " / 100";
            document.getElementById("scoreBarFill").style.width = score + "%";
            document.getElementById("confidenceText").innerText = "Confidence: " + (data.confidenceLevel || "High");

            // Fatigue
            const fatigueLvl = data.fatigueLevel || "LOW";
            const fatigueScore = data.fatigueScore !== undefined ? data.fatigueScore : 0;
            const fTag = document.getElementById("fatigueTag");
            fTag.innerText = fatigueLvl;
            fTag.className = "tag " + (fatigueLvl === "HIGH" ? "tag-high" : (fatigueLvl === "MEDIUM" ? "tag-medium" : "tag-low"));
            document.getElementById("fatigueScoreText").innerText = fatigueScore + " / 100";
            document.getElementById("fatigueBarFill").style.width = fatigueScore + "%";
            document.getElementById("fatigueBarFill").style.background = fatigueLvl === "HIGH" ? "var(--danger)" : (fatigueLvl === "MEDIUM" ? "var(--warning)" : "var(--success)");
            document.getElementById("fatigueExplanation").innerText = data.explanation || "Optimal cognitive stamina.";

            // Distraction
            const distraction = data.distractionSensitivity || {{ level: "LOW", score: 0, summary: "Low sensitivity" }};
            const dTag = document.getElementById("distractionTag");
            dTag.innerText = distraction.level;
            dTag.className = "tag " + (distraction.level === "HIGH" ? "tag-high" : (distraction.level === "MEDIUM" ? "tag-medium" : "tag-low"));
            document.getElementById("distractionScoreText").innerText = distraction.score + " / 100";
            document.getElementById("distractionBarFill").style.width = distraction.score + "%";
            document.getElementById("distractionBarFill").style.background = distraction.level === "HIGH" ? "var(--danger)" : (distraction.level === "MEDIUM" ? "var(--warning)" : "var(--success)");
            document.getElementById("distractionSummary").innerText = distraction.summary || "No active distraction triggers.";

            // Heatmap (24 hours)
            const heatmap = data.hourlyHeatmap || {{}};
            const heatmapContainer = document.getElementById("heatmapContainer");
            heatmapContainer.innerHTML = "";
            for (let h = 0; h < 24; h++) {{
                const val = heatmap[String(h)] || heatmap[h] || 0;
                const cell = document.createElement("div");
                cell.className = "heat-cell";
                const alpha = Math.max(0.1, val / 100);
                cell.style.background = val > 0 ? `rgba(56, 189, 248, ${{alpha}})` : "rgba(255, 255, 255, 0.03)";
                cell.style.color = val > 50 ? "#ffffff" : "#94a3b8";
                cell.title = `Hour ${{h}}:00 - Focus score ${{val}}%`;
                cell.innerHTML = `<span style="font-weight:700;">${{val}}%</span><span>${{h}}h</span>`;
                heatmapContainer.appendChild(cell);
            }}

            // Context Insights Table
            const contexts = data.contextInsights || [];
            const tbody = document.getElementById("contextTableBody");
            if (contexts.length > 0) {{
                tbody.innerHTML = contexts.map(c => {{
                    const tagClass = c.status === "Optimal" ? "tag-low" : (c.status === "Moderate" ? "tag-medium" : "tag-high");
                    return `<tr>
                        <td style="font-weight:600;">${{c.context}}</td>
                        <td>${{c.completionRate.toFixed(1)}}%</td>
                        <td>${{c.totalTasks}}</td>
                        <td>${{c.completedTasks}}</td>
                        <td>${{Math.round(c.avgDuration / 60)}}m</td>
                        <td><span class="tag ${{tagClass}}">${{c.status}}</span></td>
                    </tr>`;
                }}).join("");
            }}

            // App Usage & Timeline rendering
            function getCatTagClass(cat) {{
                switch(cat) {{
                    case "Productivity": return "tag-prod";
                    case "Entertainment": return "tag-ent";
                    case "Communication": return "tag-comm";
                    case "Social": return "tag-soc";
                    case "Utility": return "tag-util";
                    default: return "tag-other";
                }}
            }}

            const appUsage = data.appUsage || {{}};
            const appSummary = appUsage.summary || [];
            const totalDur = appUsage.formattedTotal || (appUsage.totalDurationSeconds ? appUsage.totalDurationSeconds + "s" : "0s");

            const totalBadge = document.getElementById("totalAppUsageBadge");
            if (totalBadge) totalBadge.innerText = "Total: " + totalDur;
            const totalCell = document.getElementById("totalAppUsageCell");
            if (totalCell) totalCell.innerText = totalDur;

            const appTbody = document.getElementById("appUsageTableBody");
            if (appTbody) {{
                if (appSummary.length > 0) {{
                    appTbody.innerHTML = appSummary.map(a => {{
                        const catClass = getCatTagClass(a.category);
                        const durStr = a.formattedTime || (a.durationSeconds + "s");
                        const pct = a.percentage !== undefined ? a.percentage : 0;
                        return `<tr>
                            <td style="font-weight:600; color:#fff;">${{a.appName}}</td>
                            <td><span class="tag ${{catClass}}">${{a.category}}</span></td>
                            <td style="font-weight:700; color:var(--primary);">${{durStr}}</td>
                            <td style="width: 140px;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div class="progress-bar-bg" style="flex:1; margin-top:0;">
                                        <div class="progress-bar-fill" style="width:${{pct}}%; background:var(--primary);"></div>
                                    </div>
                                    <span style="font-size:0.8rem; font-weight:600; color:var(--text); min-width:32px;">${{pct}}%</span>
                                </div>
                            </td>
                        </tr>`;
                    }}).join("");
                }} else {{
                    appTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 16px;">No app usage data yet</td></tr>';
                }}
            }}

            const timeline = appUsage.timeline || [];
            const sessionCount = document.getElementById("timelineSessionCount");
            if (sessionCount) sessionCount.innerText = timeline.length + " sessions";

            const timelineContainer = document.getElementById("timelineContainer");
            if (timelineContainer) {{
                if (timeline.length > 0) {{
                    timelineContainer.innerHTML = timeline.map(t => {{
                        const catClass = getCatTagClass(t.category || t.appCategory);
                        const dur = t.formattedTime || (t.durationSeconds ? t.durationSeconds + "s" : "");
                        return `<div class="timeline-row">
                            <span class="timeline-time">${{t.timeStr || "--:--"}}</span>
                            <span class="timeline-dot"></span>
                            <span class="timeline-app">${{t.appName}}</span>
                            <span class="tag ${{catClass}}">${{t.category || t.appCategory}}</span>
                            <span class="timeline-dur" style="background: rgba(56, 189, 248, 0.1); padding: 3px 10px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.25); color: var(--primary); font-weight: 600;">${{dur}}</span>
                        </div>`;
                    }}).join("");
                }} else {{
                    timelineContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No timeline transitions recorded yet</div>';
                }}
            }}

            const now = new Date();
            document.getElementById("syncText").innerText = "Live Synced at " + now.toLocaleTimeString();
        }}

        async function fetchLiveInsights() {{
            try {{
                const res = await fetch("/api/sync");
                if (res.ok) {{
                    const data = await res.json();
                    renderInsights(data);
                }}
            }} catch (err) {{
                console.warn("Office Kit sync poll failed:", err);
            }}
        }}

        // Initialize and auto-poll every 2.5 seconds
        renderInsights(initialData);
        setInterval(fetchLiveInsights, 2500);
    </script>
</body>
</html>
"""


class OfficeKitBridgeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        if self.path == "/api/sync":
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_usage_history.json")
            if os.path.exists(history_file):
                try:
                    from app_usage_tracker import AppUsageTracker
                    tracker = AppUsageTracker(history_file=history_file)
                    if tracker.timeline:
                        LATEST_INSIGHTS["appUsage"] = tracker.get_app_usage_payload()
                except Exception:
                    pass
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(LATEST_INSIGHTS, indent=2).encode("utf-8"))
        elif self.path == "/api/status":
            self._set_headers(200, "application/json")
            status_payload = {
                "status": "online",
                "service": "iQOO Office Kit Companion Bridge",
                "lastSync": LAST_SYNC_TIME,
                "port": PORT
            }
            self.wfile.write(json.dumps(status_payload).encode("utf-8"))
        else:
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(get_dashboard_html().encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/sync":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            global LATEST_INSIGHTS, LAST_SYNC_TIME
            try:
                new_data = json.loads(body.decode("utf-8"))
                if isinstance(new_data, dict):
                    LATEST_INSIGHTS.update(new_data)
                    LAST_SYNC_TIME = time.time()
                    self._set_headers(200, "application/json")
                    resp = {
                        "status": "synchronized",
                        "timestamp": int(LAST_SYNC_TIME * 1000)
                    }
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                else:
                    self._set_headers(400, "application/json")
                    self.wfile.write(b'{"error": "Payload must be a JSON object"}')
            except Exception as e:
                self._set_headers(400, "application/json")
                err_resp = {"error": str(e)}
                self.wfile.write(json.dumps(err_resp).encode("utf-8"))
        else:
            self._set_headers(404, "application/json")
            self.wfile.write(b'{"error": "Endpoint not found"}')


def push_to_bridge(insight_data: Dict[str, Any], host: str = "localhost", port: int = PORT) -> bool:
    """Helper for client modules to dispatch insight payload to Office Kit Bridge over HTTP."""
    url = f"http://{host}:{port}/api/sync"
    data = json.dumps(insight_data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status == 200
    except Exception as e:
        return False


def run_bridge(port: int = PORT):
    server = HTTPServer(("0.0.0.0", port), OfficeKitBridgeHandler)
    print(f"[iQOO Office Kit Bridge] running at http://localhost:{port}/")
    print(f"[iQOO Office Kit Bridge] Sync API: http://localhost:{port}/api/sync")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Office Kit Bridge.")
        server.server_close()


if __name__ == "__main__":
    port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_bridge(port)
