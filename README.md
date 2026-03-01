# ctrlX Data Layer Dashboard

A **ctrlX OS snap app** written in Python that reads system metrics and PLC variables
from the [ctrlX Data Layer](https://community.boschrexroth.com/ctrlx-automation-how-tos-qmglrz33/post/faq-for-ctrlx-data-layer-6eqz3hmeXbBo5Gv)
and displays them in a live web dashboard embedded in the ctrlX OS interface.

## Dashboard

Once installed, the dashboard is accessible at:

```
https://<device-ip>/ctrlx-datalayer-reader
```

It is also registered on the ctrlX OS overview page via the package manifest.

## Data Layer Nodes

| Key              | Node                                              | Type    |
|------------------|---------------------------------------------------|---------|
| cpu_percent      | framework/metrics/system/cpu-utilisation-percent  | float64 |
| mem_used_percent | framework/metrics/system/memused-percent          | float64 |
| mem_available_mb | framework/metrics/system/memavailable-mb          | float64 |
| plc_counter      | plc/app/Application/sym/GVL/gCounter              | int32   |

Data is refreshed every 2 seconds via a JSON API endpoint.

---

## Project Structure

```
ctrlx-datalayer-dashboard/
├── app/
│   └── main.py                  # HTTP server, Data Layer reader, HTML dashboard
├── configs/
│   └── ctrlx-datalayer-reader.package-manifest.json  # ctrlX OS integration manifest
├── libs/
│   ├── libcomm_datalayer.so     # Bundled Data Layer shared library
│   └── libstdc++.so.6           # Bundled C++ runtime
├── snap/
│   └── snapcraft.yaml           # Snap packaging configuration
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Development Setup

### Prerequisites

- Python 3.10+
- [ctrlX Automation SDK](https://github.com/boschrexroth/ctrlx-automation-sdk)
- A ctrlX OS device or [ctrlX WORKS](https://www.ctrlx-os.com/en/download/) Engineering and App Building Environment

### Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run locally against ctrlX Works (default)

```bash
# ctrlX Works listens on 10.0.2.2 by default
python3 app/main.py
```

### Run against a physical ctrlX device

```bash
export DATALAYER_HOST=192.168.1.1
export DATALAYER_USER=boschrexroth
export DATALAYER_PASSWORD=boschrexroth
python3 app/main.py
```

---

## Build and Install

### Prerequisites

```bash
sudo snap install snapcraft --classic
sudo snap install lxd
sudo lxd init --auto
```

### Build the snap

```bash
snapcraft
```

This produces e.g. `ctrlx-datalayer-reader_1.0.3_amd64.snap`.

### Install via Device Admin (recommended)

Upload the `.snap` file through the ctrlX OS Device Admin web interface
under **Settings → Apps & Services → Install**.

### Install via CLI (sideload)

```bash
scp ctrlx-datalayer-reader_1.0.3_amd64.snap rexroot@<ctrlX-IP>:/tmp/
ssh rexroot@<ctrlX-IP>
sudo snap install /tmp/ctrlx-datalayer-reader_1.0.3_amd64.snap --dangerous

# Connect snap interfaces manually after sideload
snap connect ctrlx-datalayer-reader:datalayer rexroth-automationcore:datalayer
snap connect rexroth-deviceadmin:package-assets ctrlx-datalayer-reader:package-assets
snap connect rexroth-deviceadmin:package-run ctrlx-datalayer-reader:package-run

# Restart Device Admin to pick up the new manifest
sudo snap restart rexroth-deviceadmin
```

### Check logs

```bash
sudo snap logs ctrlx-datalayer-reader -f
```

---

## Customization

To read additional Data Layer nodes, add entries to `NODES_FLOAT` or `NODES_INT`
in `app/main.py` and extend the HTML dashboard accordingly.

```python
NODES_FLOAT = {
    "cpu_percent": "framework/metrics/system/cpu-utilisation-percent",
    # add more float nodes here
}

NODES_INT = {
    "plc_counter": "plc/app/Application/sym/GVL/gCounter",
    # add more int nodes here
}
```

---

## Resources

- [ctrlX Automation SDK on GitHub](https://github.com/boschrexroth/ctrlx-automation-sdk)
- [ctrlX OS Community](https://community.boschrexroth.com/ctrlx-automation-fievtt9z)
- [ctrlX OS Store](https://www.ctrlx-os.com/en/ctrlx-os-store/)
- [Snapcraft documentation](https://snapcraft.io/docs)
