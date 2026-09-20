"""
Office Kit Integration Bridge
Enables cross-device synchronization between the iQOO phone and laptop.
Serves a lightweight local HTTP dashboard and JSON sync endpoint for laptop viewing.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

PORT = 8089
LATEST_INSIGHTS = {
    "peakHour": "09:00 - 11:30 AM",
    "procrastinationTrigger": "Writing tasks scheduled after 3:00 PM",
    "bestContext": "Home Office (Focus completion 88%)",
    "recommendation": "Shift complex writing tasks to your morning peak block (9-11 AM)."
}

class OfficeKitBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/sync":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_INSIGHTS, indent=2).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>iQOO Office Kit — Companion Laptop View</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; margin: 0; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 16px; border-left: 6px solid #38bdf8; max-width: 650px; }}
        h1 {{ color: #38bdf8; }}
        .label {{ font-size: 0.85rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; }}
        .val {{ font-size: 1.25rem; font-weight: 600; margin-top: 4px; }}
    </style>
</head>
<body>
    <h1>📱 iQOO Office Kit Companion View</h1>
    <p>Live synced insights from iQOO 15 on-device engine:</p>
    <div class="card">
        <div class="label">Peak Focus Window</div>
        <div class="val">{LATEST_INSIGHTS['peakHour']}</div>
    </div>
    <div class="card" style="border-color: #f43f5e;">
        <div class="label">Procrastination Alert</div>
        <div class="val">{LATEST_INSIGHTS['procrastinationTrigger']}</div>
    </div>
    <div class="card" style="border-color: #10b981;">
        <div class="label">Optimal Context</div>
        <div class="val">{LATEST_INSIGHTS['bestContext']}</div>
    </div>
    <div class="card" style="border-color: #f59e0b;">
        <div class="label">Actionable Recommendation</div>
        <div class="val">{LATEST_INSIGHTS['recommendation']}</div>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/sync":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            global LATEST_INSIGHTS
            try:
                LATEST_INSIGHTS = json.loads(body.decode("utf-8"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "synchronized"}')
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

def run_bridge(port: int = PORT):
    server = HTTPServer(("0.0.0.0", port), OfficeKitBridgeHandler)
    print(f"Office Kit Bridge running at http://localhost:{port}/")
    print(f"API Sync Endpoint: http://localhost:{port}/api/sync")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    run_bridge()
