# ctrlX Data Layer Dashboard

GitHub-Repo: https://github.com/elkrause/ctrlx-datalayer-dashboard

## Entwicklung

Änderungen immer in diesem Verzeichnis committen und zu GitHub pushen:

```bash
git add .
git commit -m "..."
git push origin main
```

## Projekt-Übersicht

Python-App für ctrlX OS, die Systemmetriken und PLC-Variablen
aus dem ctrlX Data Layer liest und in einem Web-Dashboard anzeigt.

- `app/main.py` — HTTP-Server, Data-Layer-Reader, HTML-Dashboard
- `snap/snapcraft.yaml` — ctrlX-Snap-Build-Konfiguration
- `configs/` — Package Manifest
- `requirements.txt` — Python-Abhängigkeiten

## Data-Layer-Nodes

| Key              | Node                                              | Typ     |
|------------------|---------------------------------------------------|---------|
| cpu_percent      | framework/metrics/system/cpu-utilisation-percent  | float64 |
| mem_used_percent | framework/metrics/system/memused-percent          | float64 |
| mem_available_mb | framework/metrics/system/memavailable-mb          | float64 |
| plc_counter      | plc/app/Application/sym/GVL/gCounter              | int32   |

---

## Learnings aus der Inbetriebnahme (März 2026)

### 1. Package Manifest: `proxyMapping` muss in `services` liegen

**Problem:** `proxyMapping` auf Root-Ebene (v1.3 Schema) → Reverse Proxy liefert 404.

**Ursache:** Device Admin auf ctrlX OS unterstützt nur das ältere Format mit
`services.proxyMapping`. Das v1.3 Schema mit Root-Level `proxyMapping` wird ignoriert.

**Fix:**
```json
{
  "services": {
    "proxyMapping": [{ ... }]
  }
}
```

### 2. `$schema`-Feld weglassen

Das `$schema`-Feld im Package Manifest führt zu keinem Fehler, aber alle
funktionierenden System-Apps haben es nicht. Zur Sicherheit weglassen.

### 3. `restricted`-Feld blockiert die gesamte App

**Problem:** `"restricted": ["/ctrlx-datalayer-reader"]` blockiert auch die
HTML-Seite → HTTP 401, JavaScript-Fehler `Unexpected end of JSON input`.

**Ursache:** Der Reverse Proxy gibt bei nicht-authentifizierten Requests eine
HTML-Fehlerseite zurück, kein JSON. `fetch().json()` schlägt dann fehl.

**Fix:** `restricted` komplett entfernen für ein öffentliches lokales Dashboard.
Nur API-Pfade einschränken wenn nötig: `"restricted": ["/app/api"]`.

### 4. `menus.sidebar` existiert nicht

**Problem:** `menus.sidebar` wird von ctrlX OS nicht erkannt → kein Menüeintrag.

**Gültige Menü-Typen:**
| Typ        | Verwendung                              |
|------------|-----------------------------------------|
| `overview` | Kachel auf der ctrlX OS Startseite      |
| `settings` | Eintrag im Einstellungsbereich          |
| `system`   | Eintrag im Systemkonfigurationsbereich  |

**Fix:** `menus.overview` verwenden für App-Dashboards.

### 5. Snap-Slots müssen manuell verbunden werden

Nach Installation mit `--dangerous` (sideload) müssen die Content-Interface-Slots
manuell verbunden werden:

```bash
snap connect ctrlx-datalayer-reader:datalayer rexroth-automationcore:datalayer
snap connect rexroth-deviceadmin:package-assets ctrlx-datalayer-reader:package-assets
snap connect rexroth-deviceadmin:package-run ctrlx-datalayer-reader:package-run
```

### 6. Device Admin nach Manifest-Änderung neu starten

Wenn das Package Manifest aktualisiert wurde (neuer Snap installiert), muss
Device Admin neu gestartet werden damit Proxy-Routing und Menüeinträge aktiv werden:

```bash
sudo snap restart rexroth-deviceadmin
```

### 7. `.deb`-Dateien nicht ins Git-Repo

Debian-Pakete (z.B. `ctrlx-datalayer-3.4.1.deb`) sind Build-Artefakte und
gehören nicht ins Repository. In `.gitignore` aufnehmen:

```
*.deb
*.deb.*
```

### 8. Debugging-Werkzeuge ohne `curl`

Da `curl` auf ctrlX OS nicht verfügbar ist, Unix-Socket direkt mit Python testen:

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
