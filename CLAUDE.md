# ctrlX Data Layer Dashboard

GitHub repo: https://github.com/elkrause/ctrlx-datalayer-dashboard

## Development

Always commit and push changes from this directory:

```bash
git add .
git commit -m "..."
git push origin main
```

## Project Overview

Python app for ctrlX OS that reads system metrics and PLC variables
from the ctrlX Data Layer and displays them in a web dashboard.

- `app/main.py` — HTTP server, Data Layer reader, HTML dashboard
- `snap/snapcraft.yaml` — ctrlX snap build configuration
- `configs/` — Package manifest
- `requirements.txt` — Python dependencies

## Data Layer Nodes

| Key              | Node                                              | Type    |
|------------------|---------------------------------------------------|---------|
| cpu_percent      | framework/metrics/system/cpu-utilisation-percent  | float64 |
| mem_used_percent | framework/metrics/system/memused-percent          | float64 |
| mem_available_mb | framework/metrics/system/memavailable-mb          | float64 |
| plc_counter      | plc/app/Application/sym/GVL/gCounter              | int32   |

---

## Key Learnings from Commissioning (March 2026)

### 1. `proxyMapping` must be nested inside `services`

**Problem:** `proxyMapping` at root level (v1.3 schema) → reverse proxy returns 404.

**Root cause:** Device Admin on ctrlX OS only supports the older format with
`services.proxyMapping`. Root-level `proxyMapping` from the v1.3 schema is silently ignored.

**Fix:**
```json
{
  "services": {
    "proxyMapping": [{ ... }]
  }
}
```

### 2. Omit the `$schema` field

The `$schema` field in the package manifest does not cause an error, but none of
the working system apps include it. Leave it out to be safe.

### 3. The `restricted` field blocks the entire app

**Problem:** `"restricted": ["/ctrlx-datalayer-reader"]` blocks the HTML page too
→ HTTP 401, JavaScript error `Unexpected end of JSON input`.

**Root cause:** The reverse proxy returns an HTML error page for unauthenticated
requests, not JSON. `fetch().json()` then fails to parse it.

**Fix:** Remove `restricted` entirely for a public local dashboard.
Only restrict API paths if needed: `"restricted": ["/app/api"]`.

### 4. `menus.sidebar` does not exist

**Problem:** `menus.sidebar` is not recognized by ctrlX OS → no menu entry appears.

**Valid menu types:**
| Type       | Usage                                        |
|------------|----------------------------------------------|
| `overview` | Tile on the ctrlX OS home/overview page      |
| `settings` | Entry in the device settings section         |
| `system`   | Entry in the system configuration section    |

**Fix:** Use `menus.overview` for app dashboards.

### 5. Snap slots must be connected manually after sideload

After installing with `--dangerous` (sideload), content interface slots
must be connected manually:

```bash
snap connect ctrlx-datalayer-reader:datalayer rexroth-automationcore:datalayer
snap connect rexroth-deviceadmin:package-assets ctrlx-datalayer-reader:package-assets
snap connect rexroth-deviceadmin:package-run ctrlx-datalayer-reader:package-run
```

### 6. Restart Device Admin after manifest changes

When the package manifest is updated (new snap installed), Device Admin must be
restarted for proxy routing and menu entries to take effect:

```bash
sudo snap restart rexroth-deviceadmin
```

### 7. Do not commit `.deb` files

Debian packages (e.g. `ctrlx-datalayer-3.4.1.deb`) are build artifacts and do
not belong in the repository. Add to `.gitignore`:

```
*.deb
*.deb.*
```

### 8. Debugging the socket without `curl`

Since `curl` is not available on ctrlX OS, test the Unix socket directly with Python:

```bash
python3 -c "
import socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/var/snap/<snap>/current/package-run/<snap>/web.sock')
sock.send(b'GET /path HTTP/1.0\r\nHost: localhost\r\n\r\n')
print(sock.recv(4096).decode())
sock.close()
"
```
