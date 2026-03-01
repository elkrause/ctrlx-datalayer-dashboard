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

Python/Flask-App für ctrlX OS, die Systemmetriken und PLC-Variablen
aus dem ctrlX Data Layer liest und in einem Web-Dashboard anzeigt.

- `app/main.py` — Flask-App, Data-Layer-Reader, HTML-Dashboard
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
