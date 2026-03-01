#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
ctrlX OS App: Data Layer Reader with Web Dashboard
Reads system metrics from the ctrlX Data Layer and displays them in a web UI.
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
    """Use IPC on device, TCP in dev/simulator mode."""
    if "SNAP" in os.environ:
        return "ipc://"
    ip       = os.environ.get("DATALAYER_HOST",     "10.0.2.2")
    user     = os.environ.get("DATALAYER_USER",     "boschrexroth")
    password = os.environ.get("DATALAYER_PASSWORD", "boschrexroth")
    ssl_port = os.environ.get("DATALAYER_SSL_PORT", "8443")
    return f"tcp://{user}:{password}@{ip}?sslport={ssl_port}"


def _datalayer_reader():
    """Background thread: reads metrics every 2 seconds."""
    conn_str = _get_connection_string()
    print(f"Data Layer: connecting to {conn_str}", flush=True)

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
# HTML Dashboard  — ctrlX OS design system
#   Colors : #005587 (Bosch Blue), #007bc0 (accent), #fafafa (background)
#   Font   : Bosch-Sans (falls back to system-ui)
#   Cards  : white, Material elevation shadow
#   Header : Bosch supergraphic gradient band + dark blue toolbar
# ---------------------------------------------------------------------------

_SNAP_NAME = "ctrlx-datalayer-reader"

_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="/{_SNAP_NAME}/">
  <title>ctrlX Data Layer Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Bosch-Sans', system-ui, -apple-system, sans-serif;
      background: #fafafa;
      color: rgba(0,0,0,.87);
      min-height: 100vh;
    }}

    /* Bosch supergraphic — decorative gradient band */
    .supergraphic {{
      height: 6px;
      background: linear-gradient(90deg, #005587 0%, #007bc0 55%, #7ebdff 100%);
    }}

    /* Toolbar */
    .toolbar {{
      background: #005587;
      color: #fff;
      padding: 0 24px;
      height: 56px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: 0 2px 4px -1px rgba(0,0,0,.2), 0 4px 5px 0 rgba(0,0,0,.14), 0 1px 10px 0 rgba(0,0,0,.12);
    }}
    .toolbar h1 {{
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      flex: 1;
    }}
    .toolbar .status-bar {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.8rem;
      opacity: .9;
    }}
    .dot {{
      width: 9px; height: 9px; border-radius: 50%;
      background: rgba(255,255,255,.4);
      flex-shrink: 0;
      transition: background 0.4s;
    }}
    .dot.ok  {{ background: #66bb6a; box-shadow: 0 0 5px #66bb6a; }}
    .dot.err {{ background: #ed0007; box-shadow: 0 0 5px #ed0007; }}

    /* Page content */
    .content {{
      padding: 24px;
      max-width: 960px;
    }}

    /* Card grid */
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }}

    /* Material card */
    .card {{
      background: #fff;
      border-radius: 4px;
      padding: 20px 20px 16px;
      box-shadow: 0 2px 1px -1px rgba(0,0,0,.2), 0 1px 1px 0 rgba(0,0,0,.14), 0 1px 3px 0 rgba(0,0,0,.12);
    }}
    .card-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: rgba(0,0,0,.54);
      margin-bottom: 8px;
    }}
    .card-value {{
      font-size: 2rem;
      font-weight: 700;
      color: #005587;
      line-height: 1;
      margin-bottom: 12px;
    }}
    .card-unit {{
      font-size: 1rem;
      color: rgba(0,0,0,.45);
      font-weight: 400;
    }}

    /* Progress track (Material style) */
    .progress-track {{
      height: 4px;
      background: #e0e0e0;
      border-radius: 2px;
      overflow: hidden;
    }}
    .progress-bar {{
      height: 100%;
      border-radius: 2px;
      background: #007bc0;
      transition: width 0.6s ease, background 0.4s;
      width: 0%;
    }}
    .progress-bar.warn   {{ background: #ffcf00; }}
    .progress-bar.danger {{ background: #ed0007; }}

    /* Footer timestamp */
    .footer {{
      margin-top: 20px;
      font-size: 0.72rem;
      color: rgba(0,0,0,.38);
      text-align: right;
    }}
  </style>
</head>
<body>
  <div class="supergraphic"></div>

  <div class="toolbar">
    <h1>ctrlX Data Layer Dashboard</h1>
    <div class="status-bar">
      <span class="dot" id="dot"></span>
      <span id="status">Connecting&hellip;</span>
    </div>
  </div>

  <div class="content">
    <div class="grid">
      <div class="card">
        <div class="card-label">CPU Usage</div>
        <div class="card-value"><span id="cpu">--</span><span class="card-unit"> %</span></div>
        <div class="progress-track"><div class="progress-bar" id="cpu-bar"></div></div>
      </div>
      <div class="card">
        <div class="card-label">Memory Used</div>
        <div class="card-value"><span id="mem-used">--</span><span class="card-unit"> %</span></div>
        <div class="progress-track"><div class="progress-bar" id="mem-bar"></div></div>
      </div>
      <div class="card">
        <div class="card-label">Memory Available</div>
        <div class="card-value"><span id="mem-free">--</span><span class="card-unit"> MB</span></div>
      </div>
      <div class="card">
        <div class="card-label">PLC Counter (GVL.gCounter)</div>
        <div class="card-value"><span id="plc-counter">--</span></div>
      </div>
    </div>
    <p class="footer" id="updated"></p>
  </div>

  <script>
    function setBar(el, pct) {{
      el.style.width = Math.min(pct, 100) + '%';
      el.className = 'progress-bar' +
        (pct > 90 ? ' danger' : pct > 70 ? ' warn' : '');
    }}

    async function refresh() {{
      try {{
        const r = await fetch('api/metrics');
        const d = await r.json();
        const dot = document.getElementById('dot');
        dot.className = 'dot ' + (d.connected ? 'ok' : 'err');
        document.getElementById('status').textContent =
          d.connected ? 'Connected' : 'Not connected';

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
            'Last updated: ' + t.toLocaleTimeString('en', {{hour12: false}}) +
            '.' + String(t.getMilliseconds()).padStart(3, '0');
        }}
      }} catch (e) {{
        document.getElementById('status').textContent = 'Error: ' + e.message;
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
# HTTP server on Unix socket
# ---------------------------------------------------------------------------

class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress per-request console output

    def do_GET(self):
        path = self.path.split("?")[0]
        # Strip snap prefix forwarded by the ctrlX reverse proxy
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
    srv.timeout = 1.0  # handle_request blocks at most 1 s so stop signal is checked
    os.chmod(socket_path, 0o666)
    print(f"Web server listening on {socket_path}", flush=True)
    while not _stop_event.is_set():
        srv.handle_request()
    srv.server_close()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    snap_data   = os.environ.get("SNAP_DATA", "/tmp")
    socket_path = os.path.join(snap_data, "package-run", _SNAP_NAME, "web.sock")

    # Start Data Layer reader as daemon thread
    dl_thread = threading.Thread(target=_datalayer_reader, daemon=True, name="datalayer")
    dl_thread.start()

    # Run HTTP server on main thread (blocks until stop signal)
    _run_http_server(socket_path)

    print("Stopped.", flush=True)


if __name__ == "__main__":
    main()
