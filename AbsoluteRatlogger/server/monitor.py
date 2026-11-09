#!/usr/bin/env python3
"""
Monitor — live monitoring dashboard + web UI.
Shows active sessions, command history, real-time activity.
"""
import asyncio
import json
import time
from typing import Dict

class TerminalDashboard:
    """Terminal-based live dashboard."""
    def __init__(self, sessions: Dict, db):
        self.sessions = sessions
        self.db = db

    async def run(self):
        """Run the live terminal dashboard."""
        while True:
            self._render()
            await asyncio.sleep(2)

    def _render(self):
        """Render the dashboard."""
        # Clear screen
        print("\033[2J\033[H", end="")

        active = self.db.get_active_sessions()
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    AbsoluteRatlogger — Live Monitor                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ ID    Hostname            OS              User          IP            ║
╠══════════════════════════════════════════════════════════════════════╣""")
        if not active:
            print("║ (no active sessions)                                               ║")
        for s in active:
            line = f"║ {s['id']:<5} {s['hostname']:<20} {s['os']:<15} {s['user']:<13} {s['ip']:<15}║"
            print(line[:69] + " " * max(0, 69 - len(line)) + "║")
        print("""╠══════════════════════════════════════════════════════════════════════╣
║ Active: {active:<5}  Total: {total:<5}  Uptime: {uptime:<20}      ║
╚══════════════════════════════════════════════════════════════════════╝""".format(
            active=len(active), total=len(active), uptime=time.strftime("%H:%M:%S")
        ))


class WebDashboard:
    """Web-based monitoring dashboard."""
    def __init__(self, sessions: Dict, db, port: int):
        self.sessions = sessions
        self.db = db
        self.port = port

    async def run(self):
        """Run the web dashboard."""
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/api/sessions", self.api_sessions)
        app.router.add_get("/api/commands/{session_id}", self.api_commands)
        app.router.add_get("/api/stats", self.api_stats)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        print(f"[Web] Dashboard on http://0.0.0.0:{self.port}")

    async def index(self, request):
        from aiohttp import web
        html = """<!DOCTYPE html>
<html>
<head><title>AbsoluteRatlogger</title>
<style>
body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; margin: 20px; }
h1 { color: #00ff88; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #333; padding: 8px; text-align: left; }
th { background: #16213e; color: #00ff88; }
.session { background: #0f0f23; }
.active { color: #00ff88; }
.disconnected { color: #ff4444; }
#stats { margin: 20px 0; padding: 15px; background: #16213e; border-radius: 5px; }
</style>
</head>
<body>
<h1>AbsoluteRatlogger — C2 Dashboard</h1>
<div id="stats">Loading...</div>
<h2>Active Sessions</h2>
<table id="sessions"><tr><th>ID</th><th>Hostname</th><th>OS</th><th>User</th><th>IP</th><th>Status</th><th>Last Seen</th></tr></table>
<script>
async function update() {
    const stats = await fetch('/api/stats').then(r=>r.json());
    document.getElementById('stats').innerHTML = `Active: ${stats.active} | Total: ${stats.total} | Uptime: ${stats.uptime}`;

    const sessions = await fetch('/api/sessions').then(r=>r.json());
    let html = '<tr><th>ID</th><th>Hostname</th><th>OS</th><th>User</th><th>IP</th><th>Status</th><th>Last Seen</th></tr>';
    sessions.forEach(s => {
        html += `<tr class="session"><td>${s.id}</td><td>${s.hostname}</td><td>${s.os}</td><td>${s.user}</td><td>${s.ip}</td><td class="${s.status}">${s.status}</td><td>${s.last_seen}</td></tr>`;
    });
    document.getElementById('sessions').innerHTML = html;
}
update();
setInterval(update, 2000);
</script>
</body>
</html>"""
        from aiohttp import web
        return web.Response(text=html, content_type="text/html")

    async def api_sessions(self, request):
        from aiohttp import web
        sessions = self.db.get_active_sessions()
        return web.json_response(sessions)

    async def api_commands(self, request):
        from aiohttp import web
        sid = int(request.match_info["session_id"])
        cmds = self.db.get_command_history(sid)
        return web.json_response(cmds)

    async def api_stats(self, request):
        from aiohttp import web
        sessions = self.db.get_active_sessions()
        return web.json_response({
            "active": len([s for s in sessions if s.get("status") == "active"]),
            "total": len(sessions),
            "uptime": time.strftime("%H:%M:%S"),
        })
