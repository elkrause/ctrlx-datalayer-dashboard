# ctrlX OS Data Layer Reader

A minimal **ctrlX OS Snap-Package App** in Python that reads system metrics from the
[ctrlX Data Layer](https://developer.community.boschrexroth.com/t5/Store-and-How-to/bg-p/how-to) and logs them periodically.

## What it reads

| Node | Description |
|------|-------------|
| `framework/metrics/system/cpu-utilisation-percent` | CPU utilization in % |
| `framework/metrics/system/memavailable-mb` | Available memory in MB |
| `framework/metrics/system/memused-percent` | Memory utilization in % |

Output appears every 2 seconds in the snap journal.

---

## Project structure

```
ctrlx-os-app/
├── app/
│   └── main.py                  # Main Python application
├── snap/
│   ├── snapcraft.yaml           # Snap packaging configuration
│   └── local/
│       └── packagemanifest.json # ctrlX Store metadata
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Development setup

### Prerequisites

- Python 3.10+
- [ctrlX Automation SDK](https://github.com/boschrexroth/ctrlx-automation-sdk)
- A ctrlX device or the ctrlX Works simulation

### Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run locally (against a ctrlX device or simulation)

```bash
export DATALAYER_HOST=192.168.1.1   # IP of your ctrlX device
export DATALAYER_USER=boschrexroth
export DATALAYER_PASSWORD=boschrexroth
python3 app/main.py
```

### Run against ctrlX Works (local simulation, default)

```bash
# ctrlX Works listens on 10.0.2.2:2069 by default
python3 app/main.py
```

---

## Build and install as snap

### Prerequisites

```bash
sudo snap install snapcraft --classic
sudo snap install lxd
sudo lxd init --auto
```

### Build

```bash
snapcraft
```

This creates a `.snap` file, e.g. `ctrlx-datalayer-reader_1.0.0_amd64.snap`.

### Install on ctrlX device

Transfer the `.snap` file to your ctrlX device and install it:

```bash
scp ctrlx-datalayer-reader_1.0.0_amd64.snap user@<ctrlX-IP>:/tmp/
ssh user@<ctrlX-IP>
sudo snap install /tmp/ctrlx-datalayer-reader_1.0.0_amd64.snap --dangerous
```

### Check logs

```bash
sudo snap logs ctrlx-datalayer-reader -f
```

---

## Customization

To read different Data Layer nodes, edit the `NODES_TO_READ` list in `app/main.py`:

```python
NODES_TO_READ = [
    "motion/axs/Axis_1/state/values/actual/pos",
    "plc/app/Application/sym/GVL/myVariable",
    # Add more nodes here...
]
```

Adjust the read interval with `READ_INTERVAL_SECONDS`.

---

## Resources

- [ctrlX Automation SDK on GitHub](https://github.com/boschrexroth/ctrlx-automation-sdk)
- [ctrlX Developer Community](https://developer.community.boschrexroth.com/)
- [ctrlX Store](https://apps.boschrexroth.com/)
- [Snapcraft documentation](https://snapcraft.io/docs)
