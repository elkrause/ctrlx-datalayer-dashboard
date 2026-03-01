#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
ctrlX OS App: Data Layer Reader mit Web-Dashboard
Liest System-Metriken aus der ctrlX Data Layer und zeigt sie in einer Web-UI.
"""

import http.server
import json
import os
import signal
import socket
import threading
from datetime import datetime

import ctrlxdatalayer
from ctrlxdatalayer.variant import Result

# ---------------------------------------------------------------------------
# Shared state (thread-safe)
# ---------------------------------------------------------------------------

_metrics: dict = {
    "connected": False,
    "cpu_percent": None,
    "mem_used_percent": None,
    "mem_available_mb": None,
    "plc_counter": None,
    "last_updated": None,
}
_metrics_lock = threading.Lock()
_stop_event = threading.Event()

# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

def _handle_signal(signum, frame):
    _stop_event.set()

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGABRT, _handle_signal)

# ---------------------------------------------------------------------------
# ctrlX Data Layer connection
# ---------------------------------------------------------------------------

NODES_FLOAT = {
    "cpu_percent":      "framework/metrics/system/cpu-utilisation-percent",
    "mem_used_percent": "framework/metrics/system/memused-percent",
    "mem_available_mb": "framework/metrics/system/memavailable-mb",
}

NODES_INT = {
    "plc_counter": "plc/app/Application/sym/GVL/gCounter",
}


def _get_connection_string() -> str:
    """IPC auf Gerät, TCP im Dev-/Simulator-Modus."""
    if "SNAP" in os.environ:
        return "ipc://"
    ip       = os.environ.get("DATALAYER_HOST",     "10.0.2.2")
    user     = os.environ.get("DATALAYER_USER",     "boschrexroth")
    password = os.environ.get("DATALAYER_PASSWORD", "boschrexroth")
    ssl_port = os.environ.get("DATALAYER_SSL_PORT", "8443")
    return f"tcp://{user}:{password}@{ip}?sslport={ssl_port}"


def _datalayer_reader():
    """Hintergrund-Thread: liest Metriken alle 2 Sekunden."""
    conn_str = _get_connection_string()
    print(f"Data Layer: verbinde mit {conn_str}", flush=True)

    with ctrlxdatalayer.system.System("") as system:
        system.start(False)
        client = system.factory().create_client(conn_str)

        with client:
            while not _stop_event.is_set():
                connected = client.is_connected()
                update = {"connected": connected, "last_updated": datetime.now().isoformat()}

                if connected:
                    for key, node in NODES_FLOAT.items():
                        result, variant = client.read_sync(node)
                        update[key] = round(variant.get_float64(), 2) if result == Result.OK else None
                    for key, node in NODES_INT.items():
                        result, variant = client.read_sync(node)
                        update[key] = variant.get_int32() if result == Result.OK else None
                else:
                    for key in NODES_FLOAT:
                        update[key] = None
                    for key in NODES_INT:
                        update[key] = None

                with _metrics_lock:
                    _metrics.update(update)

                _stop_event.wait(2.0)

        system.stop(False)

# ---------------------------------------------------------------------------
# HTML-Dashboard
# ---------------------------------------------------------------------------

_SNAP_NAME = "ctrlx-datalayer-reader"

_HTML = f"""\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="/{_SNAP_NAME}/">
  <title>Michaels ctrlX Data Layer Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f1117; color: #e0e0e0;
      min-height: 100vh; padding: 32px 24px;
    }}
    header {{ margin-bottom: 28px; }}
    h1 {{ color: #00a8e0; font-size: 1.6rem; margin-bottom: 4px; }}
    .subtitle {{ color: #777; font-size: 0.85rem; }}
    .status-bar {{
      display: flex; align-items: center; gap: 8px;
      margin-bottom: 28px; font-size: 0.85rem;
    }}
    .dot {{
      width: 10px; height: 10px; border-radius: 50%;
      background: #555; flex-shrink: 0;
      transition: background 0.4s;
    }}
    .dot.ok   {{ background: #00c070; box-shadow: 0 0 6px #00c070; }}
    .dot.err  {{ background: #e04040; box-shadow: 0 0 6px #e04040; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #1c1f2b; border: 1px solid #2a2d3e;
      border-radius: 10px; padding: 20px;
    }}
    .label {{
      font-size: 0.75rem; text-transform: uppercase;
      letter-spacing: 0.06em; color: #777; margin-bottom: 6px;
    }}
    .value {{
      font-size: 2.2rem; font-weight: 700; color: #fff;
      margin-bottom: 12px; line-height: 1;
    }}
    .unit {{ font-size: 1rem; color: #888; font-weight: 400; }}
    .bar-bg {{
      height: 6px; background: #2a2d3e;
      border-radius: 3px; overflow: hidden;
    }}
    .bar {{
      height: 100%; border-radius: 3px;
      background: linear-gradient(90deg, #00a8e0, #0070c0);
      transition: width 0.6s ease, background 0.4s;
      width: 0%;
    }}
    .bar.warn   {{ background: linear-gradient(90deg, #f0a500, #e06000); }}
    .bar.danger {{ background: linear-gradient(90deg, #e04040, #a00000); }}
    .updated {{
      margin-top: 20px; font-size: 0.75rem; color: #444;
      text-align: right;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Michaels ctrlX Data Layer Dashboard</h1>
    <p class="subtitle">Echtzeit-Systemmetriken</p>
  </header>

  <div class="status-bar">
    <span class="dot" id="dot"></span>
    <span id="status">Verbinde&hellip;</span>
  </div>

  <div class="grid">
    <div class="card">
      <div class="label">CPU-Auslastung</div>
      <div class="value"><span id="cpu">--</span><span class="unit"> %</span></div>
      <div class="bar-bg"><div class="bar" id="cpu-bar"></div></div>
    </div>
    <div class="card">
      <div class="label">Arbeitsspeicher genutzt</div>
      <div class="value"><span id="mem-used">--</span><span class="unit"> %</span></div>
      <div class="bar-bg"><div class="bar" id="mem-bar"></div></div>
    </div>
    <div class="card">
      <div class="label">Arbeitsspeicher frei</div>
      <div class="value"><span id="mem-free">--</span><span class="unit"> MB</span></div>
    </div>
    <div class="card">
      <div class="label">PLC Zähler (GVL.gCounter)</div>
      <div class="value"><span id="plc-counter">--</span></div>
    </div>
  </div>

  <p class="updated" id="updated"></p>

  <script>
    function setBar(barEl, pct) {{
      barEl.style.width = Math.min(pct, 100) + '%';
      barEl.className = 'bar' +
        (pct > 90 ? ' danger' : pct > 70 ? ' warn' : '');
    }}

    async function refresh() {{
      try {{
        const r = await fetch('api/metrics');
        const d = await r.json();
        const dot = document.getElementById('dot');
        dot.className = 'dot ' + (d.connected ? 'ok' : 'err');
        document.getElementById('status').textContent =
          d.connected ? 'Verbunden' : 'Nicht verbunden';

        document.getElementById('cpu').textContent =
          d.cpu_percent !== null ? d.cpu_percent.toFixed(1) : '--';
        if (d.cpu_percent !== null)
          setBar(document.getElementById('cpu-bar'), d.cpu_percent);

        document.getElementById('mem-used').textContent =
          d.mem_used_percent !== null ? d.mem_used_percent.toFixed(1) : '--';
        if (d.mem_used_percent !== null)
          setBar(document.getElementById('mem-bar'), d.mem_used_percent);

        document.getElementById('mem-free').textContent =
          d.mem_available_mb !== null ? Math.round(d.mem_available_mb) : '--';

        document.getElementById('plc-counter').textContent =
          d.plc_counter !== null ? d.plc_counter : '--';

        if (d.last_updated) {{
          const t = new Date(d.last_updated);
          document.getElementById('updated').textContent =
            'Zuletzt: ' + t.toLocaleTimeString('de-DE', {{hour12: false}}) +
            '.' + String(t.getMilliseconds()).padStart(3, '0');
        }}
      }} catch (e) {{
        document.getElementById('status').textContent = 'Fehler: ' + e.message;
        document.getElementById('dot').className = 'dot err';
      }}
    }}

    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP-Server auf Unix-Socket
# ---------------------------------------------------------------------------

class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Kein Request-Log in der Konsole

    def do_GET(self):
        path = self.path.split("?")[0]
        # Präfix entfernen (ctrlX Reverse Proxy leitet mit Pfad weiter)
        if path.startswith(f"/{_SNAP_NAME}"):
            path = path[len(f"/{_SNAP_NAME}"):]
        path = path.rstrip("/") or "/"

        if path == "/":
            body = _HTML.encode("utf-8")
            self._respond(200, "text/html; charset=utf-8", body)
        elif path == "/api/metrics":
            with _metrics_lock:
                data = dict(_metrics)
            body = json.dumps(data).encode("utf-8")
            self._respond(200, "application/json", body)
        else:
            self.send_error(404)

    def _respond(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


class _UnixSocketHTTPServer(http.server.HTTPServer):
    address_family = socket.AF_UNIX

    def server_bind(self):
        if os.path.exists(self.server_address):
            os.unlink(self.server_address)
        super().server_bind()


def _run_http_server(socket_path: str):
    os.makedirs(os.path.dirname(socket_path), exist_ok=True)
    srv = _UnixSocketHTTPServer(socket_path, _Handler)
    srv.timeout = 1.0  # handle_request blockiert max. 1 s → Stop-Check möglich
    os.chmod(socket_path, 0o666)
    print(f"Web-Server lauscht auf {socket_path}", flush=True)
    while not _stop_event.is_set():
        srv.handle_request()
    srv.server_close()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    snap_data   = os.environ.get("SNAP_DATA", "/tmp")
    socket_path = os.path.join(snap_data, "package-run", _SNAP_NAME, "web.sock")

    # Data Layer Reader als Daemon-Thread starten
    dl_thread = threading.Thread(target=_datalayer_reader, daemon=True, name="datalayer")
    dl_thread.start()

    # HTTP-Server im Haupt-Thread (blockt bis Stop-Signal)
    _run_http_server(socket_path)

    print("Beendet.", flush=True)


if __name__ == "__main__":
    main()
