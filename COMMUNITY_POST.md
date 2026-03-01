# Session Summary & Community Post — ctrlX OS Python Web App (March 2026)

---

## Session Summary

### What Was Built

A minimal Python snap app for ctrlX OS that:
- Reads system metrics (CPU, RAM) and a PLC variable from the ctrlX Data Layer
- Serves a live web dashboard via a Unix socket
- Integrates with Device Admin (reverse proxy, overview tile)

Stack: Python 3.10 · ctrlX Data Layer SDK · `http.server` · Snapcraft · ctrlX OS

### What Was Solved This Session

| # | Problem | Resolution |
|---|---------|------------|
| 1 | Dashboard returned 404 | `proxyMapping` nested inside `services` (not root level) |
| 2 | Dashboard tile missing in ctrlX OS overview | Changed `menus.sidebar` → `menus.overview` |
| 3 | HTTP 401 / JS parse error after login | Removed overly broad `restricted` path |
| 4 | Snap interfaces not active after sideload | Connected slots manually via `snap connect` |
| 5 | Manifest changes not picked up | Added `sudo snap restart rexroth-deviceadmin` to workflow |
| 6 | No `curl` on ctrlX OS for debugging | Python one-liner to test Unix socket directly |

---

## Open Points

- [ ] **Translate `app/main.py` to English** — HTML labels, comments and print statements are still in German
- [ ] **Automated test on ctrlX Works** — no CI pipeline yet; build and test are fully manual
- [ ] **Error display in dashboard** — when a Data Layer node is unavailable the card just shows `--` without explanation
- [ ] **HTTPS / authentication** — dashboard is currently public (no `restricted`); evaluate if login protection is needed for production
- [ ] **Snap store publishing** — app is sideloaded only; not yet submitted to ctrlX Store
- [ ] **Dynamic node configuration** — node list is hardcoded; could be made configurable via a JSON file or environment variables
- [ ] **PLC variable type handling** — only `float64` and `int32` are supported; `string`, `bool` and array types are not yet handled

---

## Community Post — ctrlX OS Developer Community

**Title:** Building a Python Web Dashboard for ctrlX OS — Lessons Learned from a First Snap App

---

Hi everyone,

I recently built a small Python snap app for ctrlX OS that reads Data Layer
nodes and shows them in a live web dashboard embedded directly in the Device
Admin interface. It works, but it took a few non-obvious discoveries to get
there. Sharing them here so others don't have to go through the same trial and error.

**What the app does:**
- Reads `framework/metrics/system/cpu-utilisation-percent`, `memused-percent`,
  `memavailable-mb`, and a PLC variable (`plc/app/Application/sym/GVL/gCounter`)
- Serves an HTML dashboard via Unix socket → ctrlX reverse proxy
- Shows up as a tile on the ctrlX OS overview page

Source code: https://github.com/elkrause/ctrlx-datalayer-dashboard

---

### Lesson 1 — `proxyMapping` belongs inside `services`, not at root level

The v1.3 schema places `proxyMapping` at the root of the package manifest.
**Device Admin on ctrlX OS silently ignores it.** Use the older nested format:

```json
{
  "services": {
    "proxyMapping": [
      {
        "name": "my-app-web",
        "url": "^/my-app/(.*)$",
        "target": "unix://${SNAP_DATA}/package-run/my-app/web.sock/my-app/$1"
      }
    ]
  }
}
```

If your app returns 404 through the reverse proxy but works fine on the raw
socket, this is almost certainly the reason.

---

### Lesson 2 — `menus.sidebar` is not a valid menu type

There is no `sidebar` key in `menus`. The valid options are:

| Key        | Where it appears                          |
|------------|-------------------------------------------|
| `overview` | Tile on the ctrlX OS home/overview page   |
| `settings` | Entry in the device settings section      |
| `system`   | Entry in the system configuration section |

Use `menus.overview` to show your app as a tile on the main page.

---

### Lesson 3 — Be careful with `restricted`

Setting `"restricted": ["/my-app"]` protects the entire path — including the
HTML page itself. When an unauthenticated request hits the reverse proxy, it
returns an HTML error page, not JSON. If your frontend does `fetch().json()`,
it will throw `Unexpected end of JSON input` and appear as a JavaScript error.

**Recommendation:** Only restrict API paths if needed, e.g.:
```json
"restricted": ["/my-app/api"]
```
Or leave it out entirely for a local-only dashboard.

---

### Lesson 4 — Snap slots must be connected manually after sideload

Installing with `--dangerous` does not auto-connect content interface slots.
After a sideload you need to run these three commands:

```bash
snap connect my-app:datalayer rexroth-automationcore:datalayer
snap connect rexroth-deviceadmin:package-assets my-app:package-assets
snap connect rexroth-deviceadmin:package-run my-app:package-run
```

When installing through Device Admin (the `.snap` upload in the web UI),
this happens automatically.

---

### Lesson 5 — Restart Device Admin after manifest changes

When you install a new version of your snap with an updated package manifest,
Device Admin caches the old routing and menu configuration. Restart it to
pick up changes:

```bash
sudo snap restart rexroth-deviceadmin
```

This is only needed for manifest changes (proxy routes, menu entries).
Normal app restarts (`sudo snap restart my-app`) do not require it.

---

### Lesson 6 — Debugging the Unix socket without `curl`

`curl` is not installed on ctrlX OS. To test your Unix socket directly,
use this Python one-liner:

```bash
python3 -c "
import socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/var/snap/my-app/current/package-run/my-app/web.sock')
sock.send(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
print(sock.recv(4096).decode())
sock.close()
"
```

This lets you verify the app is responding before worrying about the reverse proxy.

---

### Bonus — Python architecture for the Unix socket HTTP server

For anyone wanting a minimal pattern: `http.server.HTTPServer` supports
`AF_UNIX` out of the box with a one-line subclass:

```python
import http.server, socket, os

class UnixHTTPServer(http.server.HTTPServer):
    address_family = socket.AF_UNIX

    def server_bind(self):
        if os.path.exists(self.server_address):
            os.unlink(self.server_address)
        super().server_bind()
```

No additional libraries needed.

---

Hope this saves someone a few hours. Happy to answer questions in the comments.

**Tags:** `python` `snap` `data-layer` `device-admin` `package-manifest` `web-dashboard`

---

*Built with: ctrlX OS · Python 3.10 · ctrlX Automation SDK · Snapcraft*
*Tested on: ctrlX CORE XM22 · ctrlX Works (simulation)*

---

## LinkedIn Post

---

I just shipped my first custom app for **Bosch Rexroth ctrlX OS** — and it was a great learning experience.

The app is a small Python snap that reads live system metrics and a PLC variable from the **ctrlX Data Layer** and displays them in a web dashboard, embedded directly in the Device Admin interface.

No third-party frameworks — just Python's built-in `http.server`, a Unix socket, and the ctrlX Automation SDK.

**What I learned the hard way:**

🔴 `proxyMapping` in the package manifest must be nested inside `services` — not at root level. The v1.3 schema shows it at root, but Device Admin silently ignores it there. This caused a 404 that took a while to track down.

🔴 There is no `menus.sidebar` in ctrlX OS. The correct key for an app tile on the overview page is `menus.overview`.

🔴 The `restricted` field in the manifest blocks everything under that path — including the HTML page itself. When an unauthenticated request hits the proxy, it returns an HTML error page, not JSON. If your frontend calls `fetch().json()`, you get `Unexpected end of JSON input`. Took me a moment to connect those dots.

🔴 After a sideload install (`--dangerous`), snap content interfaces are not connected automatically. Three manual `snap connect` commands are needed. When using Device Admin for upload, this happens automatically.

🔴 After updating the package manifest, Device Admin must be restarted (`sudo snap restart rexroth-deviceadmin`) — otherwise the old routing and menu config stay active.

🟢 No `curl` on ctrlX OS? No problem — a Python one-liner can test a Unix socket directly.

---

The full source, manifest, and snapcraft config are on GitHub if anyone wants a working reference for their own ctrlX OS Python app.

👉 https://github.com/elkrause/ctrlx-datalayer-dashboard

Happy to answer questions or compare notes with anyone else building on ctrlX OS.

#ctrlX #BoshRexroth #ctrlXOS #Python #IIoT #IndustrialAutomation #Snapcraft #DataLayer #EdgeComputing #OpenSource
